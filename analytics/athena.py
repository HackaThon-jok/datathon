"""Generate a run-specific Athena handoff; makes no AWS calls."""

import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path
from analytics.contracts import SCHEMAS, verify_run, sha256


def build(run_dir, database, s3_prefix):
    folder = Path(run_dir)
    report = verify_run(folder)
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,99}", database):
        raise ValueError("Use a lowercase SQL database identifier")
    if not re.fullmatch(r"s3://[a-z0-9.-]+/[A-Za-z0-9_/-]+", s3_prefix):
        raise ValueError("Use an S3 prefix with a bucket and simple path")
    suffix = "r_" + re.sub("[^a-z0-9_]", "_", report["run_id"].lower())
    root = s3_prefix.rstrip("/") + "/" + report["run_id"]
    names = {
        name: f"{database}.{name}_{suffix}"
        for name in (
            "staging_sales",
            "local_mart",
            "baseline",
            "candidate",
            "local_region",
            "candidate_region",
        )
    }
    out = folder / "athena"
    out.mkdir(exist_ok=True)
    specs = {
        "staging_sales": (
            "staging_sales.parquet",
            "month date, store string, region string, item_code string, item_label string, orders bigint, quantity bigint, sales_amount decimal(18,2), batch_id string, source_row_id bigint, ingest_row_id bigint",
        ),
        "local_mart": (
            "mart_monthly_store.parquet",
            "month date, store string, region string, batch_id string, detail_rows bigint, orders bigint, quantity bigint, sales_amount decimal(18,2)",
        ),
        "baseline": (
            "baseline.parquet",
            "month date, store string, orders bigint, quantity bigint, sales_amount decimal(18,2)",
        ),
    }
    if report["region_ready"]:
        specs["local_region"] = (
            "mart_monthly_region.parquet",
            "month date, region string, batch_id string, detail_rows bigint, orders bigint, quantity bigint, sales_amount decimal(18,2)",
        )
    ddl = []
    uploads = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "# Run from repository root with AWS CLI credentials configured by your cloud engineer.",
    ]
    for key, (filename, schema) in specs.items():
        ddl.append(
            f"CREATE EXTERNAL TABLE {names[key]} ({schema})\nSTORED AS PARQUET LOCATION '{root}/{key}/';"
        )
        uploads.append(
            f'aws s3 cp {shlex.quote(str((folder/filename).resolve()))} {shlex.quote(root+"/"+key+"/"+filename)}'
        )
    candidate = f"""CREATE VIEW {names['candidate']} AS
SELECT month, store, region, batch_id, COUNT(*) AS detail_rows,
       CAST(SUM(orders) AS BIGINT) AS orders, CAST(SUM(quantity) AS BIGINT) AS quantity,
       CAST(SUM(sales_amount) AS DECIMAL(18,2)) AS sales_amount
FROM {names['staging_sales']}
GROUP BY month, store, region, batch_id;"""
    query = f"""-- Must return failures = 0. Save the Athena QueryExecutionId and result.
WITH differences AS (
 SELECT * FROM {names['candidate']} EXCEPT SELECT * FROM {names['local_mart']}
), reverse_differences AS (
 SELECT * FROM {names['local_mart']} EXCEPT SELECT * FROM {names['candidate']}
), baseline_differences AS (
 SELECT month,store,orders,quantity,sales_amount FROM {names['candidate']}
 EXCEPT SELECT * FROM {names['baseline']}
), reverse_baseline_differences AS (
 SELECT * FROM {names['baseline']}
 EXCEPT SELECT month,store,orders,quantity,sales_amount FROM {names['candidate']}
)
SELECT
 (SELECT COUNT(*) FROM differences) +
 (SELECT COUNT(*) FROM reverse_differences) +
 (SELECT COUNT(*) FROM baseline_differences) +
 (SELECT COUNT(*) FROM reverse_baseline_differences) +
 (SELECT COUNT(*) FROM {names['staging_sales']} WHERE orders IS NULL OR quantity IS NULL OR sales_amount IS NULL OR item_code IS NULL) +
 (SELECT COUNT(*) - COUNT(DISTINCT source_row_id) FROM {names['staging_sales']}) +
 CASE WHEN (SELECT COUNT(*) FROM {names['staging_sales']}) = {report['detail_rows']} THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM {names['candidate']}) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM {names['local_mart']}) = 1 THEN 0 ELSE 1 END +
 CASE WHEN (SELECT COUNT(*) FROM {names['baseline']}) = 1 THEN 0 ELSE 1 END
 AS failures;"""
    expected_schemas = {
        "staging_sales": SCHEMAS["staging_sales"],
        "local_mart": SCHEMAS["mart_monthly_store"],
        "baseline": SCHEMAS["baseline"],
        "candidate": SCHEMAS["mart_monthly_store"],
    }
    if report["region_ready"]:
        expected_schemas.update(
            local_region=SCHEMAS["mart_monthly_region"],
            candidate_region=SCHEMAS["mart_monthly_region"],
        )
        candidate += f"""\nCREATE VIEW {names['candidate_region']} AS
SELECT month, region, batch_id, COUNT(*) AS detail_rows,
       CAST(SUM(orders) AS BIGINT) AS orders, CAST(SUM(quantity) AS BIGINT) AS quantity,
       CAST(SUM(sales_amount) AS DECIMAL(18,2)) AS sales_amount
FROM {names['staging_sales']} GROUP BY month, region, batch_id;"""
        regional_query = f"""WITH forward_diff AS (
SELECT * FROM {names['candidate_region']} EXCEPT SELECT * FROM {names['local_region']}
), reverse_diff AS (
SELECT * FROM {names['local_region']} EXCEPT SELECT * FROM {names['candidate_region']}
)
SELECT (SELECT COUNT(*) FROM forward_diff) + (SELECT COUNT(*) FROM reverse_diff) +
(SELECT COUNT(*) FROM {names['staging_sales']} WHERE region IS NULL) +
CASE WHEN (SELECT COUNT(*) FROM {names['candidate_region']}) = 1 THEN 0 ELSE 1 END +
CASE WHEN (SELECT COUNT(*) FROM {names['local_region']}) = 1 THEN 0 ELSE 1 END AS failures;"""
        (out / "03b_validate_region.sql").write_text(regional_query + "\n")
    expected_rows = []
    for key, schema in expected_schemas.items():
        table = names[key].split(".")[1]
        for ordinal, (column, kind) in enumerate(schema, 1):
            expected_rows.append(
                f"('{database}', '{table}', '{column}', '{kind.lower()}', {ordinal})"
            )
    tables = ", ".join("'" + names[key].split(".")[1] + "'" for key in expected_schemas)
    schema_query = f"""WITH expected(table_schema,table_name,column_name,data_type,ordinal_position) AS (
VALUES {', '.join(expected_rows)}
), actual AS (
SELECT table_schema, table_name, column_name, lower(replace(data_type, ' ', '')) AS data_type, ordinal_position
FROM information_schema.columns WHERE table_schema = '{database}' AND table_name IN ({tables})
), missing_or_changed AS (
SELECT * FROM expected EXCEPT SELECT * FROM actual
), unexpected AS (
SELECT * FROM actual EXCEPT SELECT * FROM expected
)
SELECT (SELECT COUNT(*) FROM missing_or_changed) + (SELECT COUNT(*) FROM unexpected) AS failures;"""
    (out / "05_validate_schema.sql").write_text(schema_query + "\n")
    probe = f"""-- Read-only fault injection: this deliberately altered amount must be rejected.
WITH bad_candidate AS (
SELECT month,store,orders,quantity,CAST(sales_amount + 1 AS DECIMAL(18,2)) AS sales_amount
FROM {names['candidate']}
), differences AS (
SELECT * FROM bad_candidate EXCEPT SELECT * FROM {names['baseline']}
)
SELECT COUNT(*) AS failures FROM differences;"""
    (out / "06_failure_probe.sql").write_text(probe + "\n")
    (out / "07_published_snapshot.sql").write_text(
        f"SELECT * FROM {database}.published_monthly_store ORDER BY month,store,batch_id;\n"
    )
    (out / "01_tables.sql").write_text("\n\n".join(ddl) + "\n")
    (out / "02_candidate.sql").write_text(candidate + "\n")
    (out / "03_validate.sql").write_text(query + "\n")
    (out / "04_publish_after_review.sql").write_text(
        f"""-- RUN ONLY AFTER parity AND schema checks return failures=0 and team reviewer approves this run.
-- Keep the prior published view unchanged if any check fails.
CREATE OR REPLACE VIEW {database}.published_monthly_store AS
SELECT * FROM {names['candidate']};
"""
    )
    if report["region_ready"]:
        with (out / "04_publish_after_review.sql").open("a") as stream:
            stream.write(
                f"\n-- Separate regional view; the two view updates are not a transaction.\nCREATE OR REPLACE VIEW {database}.published_monthly_region AS SELECT * FROM {names['candidate_region']};\n"
            )
    (out / "upload.sh").write_text("\n".join(uploads) + "\n")
    (out / "handoff.json").write_text(
        json.dumps(
            dict(
                sql_sha256={f.name: sha256(f) for f in out.glob("*.sql")},
                output_sha256=report["output_sha256"],
                region_ready=report["region_ready"],
                expected_schemas={
                    key: (
                        SCHEMAS["mart_monthly_region"]
                        if key in ("local_region", "candidate_region")
                        else expected_schemas[key]
                    )
                    for key in expected_schemas
                },
                run_id=report["run_id"],
                s3_prefix=root,
                database=database,
                tables=names,
                aws_executed=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print(out)
    return out, names


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--s3-prefix", required=True)
    a = p.parse_args()
    build(a.run_dir, a.database, a.s3_prefix)


if __name__ == "__main__":
    main()
