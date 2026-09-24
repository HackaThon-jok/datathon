"""Run read-only Athena checks and archive their SQL, results and execution IDs.

Requires existing uploaded data and catalog objects. Never creates or publishes views.
"""

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from analytics.contracts import sha256, verify_run


def execute(
    client,
    sql,
    database,
    workgroup,
    evidence_file,
    result_location=None,
    timeout_seconds=180,
    sleep=time.sleep,
    clock=time.monotonic,
):
    arguments = dict(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup,
        ResultReuseConfiguration={"ResultReuseByAgeConfiguration": {"Enabled": False}},
    )
    if result_location:
        arguments["ResultConfiguration"] = {"OutputLocation": result_location}
    query_id = client.start_query_execution(**arguments)["QueryExecutionId"]
    evidence = dict(query_id=query_id, state="SUBMITTED", sql=sql)
    evidence_file = Path(evidence_file)
    evidence_file.write_text(json.dumps(evidence, indent=2) + "\n")
    deadline = clock() + timeout_seconds
    while True:
        execution = client.get_query_execution(QueryExecutionId=query_id)[
            "QueryExecution"
        ]
        status = execution["Status"]["State"]
        evidence.update(
            state=status,
            statistics=execution.get("Statistics", {}),
            engine=execution.get("EngineVersion", {}),
        )
        evidence_file.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
        if status in ("FAILED", "CANCELLED"):
            evidence["failure_reason"] = execution["Status"].get(
                "StateChangeReason", ""
            )
            evidence_file.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
            raise ValueError(f"Athena query {query_id} ended in {status}")
        if status == "SUCCEEDED":
            break
        if clock() >= deadline:
            client.stop_query_execution(QueryExecutionId=query_id)
            evidence["state"] = "TIMEOUT_CANCEL_REQUESTED"
            evidence_file.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
            raise TimeoutError(
                f"Athena query {query_id} exceeded timeout; cancellation requested"
            )
        sleep(1)
    values = []
    token = None
    columns = None
    while True:
        params = {"QueryExecutionId": query_id, "MaxResults": 1000}
        if token:
            params["NextToken"] = token
        page = client.get_query_results(**params)
        result = page["ResultSet"]
        rows = result["Rows"]
        if columns is None:
            columns = [c["Name"] for c in result["ResultSetMetadata"]["ColumnInfo"]]
            rows = rows[
                1:
            ]  # Athena SELECT result header occurs only on the first page.
        values.extend([[c.get("VarCharValue") for c in row["Data"]] for row in rows])
        token = page.get("NextToken")
        if not token:
            break
    evidence.update(columns=columns, rows=values)
    evidence_file.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    return evidence


def failure_count(result):
    if (
        result["columns"] != ["failures"]
        or len(result["rows"]) != 1
        or len(result["rows"][0]) != 1
    ):
        raise ValueError("Unexpected validation result shape")
    value = int(result["rows"][0][0])
    if value < 0:
        raise ValueError("Negative failure count")
    return value


def collect(
    client, handoff_dir, workgroup, result_location=None, check_published=False
):
    folder = Path(handoff_dir)
    report = verify_run(folder.parent)
    handoff = json.loads((folder / "handoff.json").read_text())
    if handoff["run_id"] != report["run_id"]:
        raise ValueError("Handoff belongs to a different run")
    required = ["03_validate.sql", "05_validate_schema.sql", "06_failure_probe.sql"]
    if handoff["region_ready"]:
        required.append("03b_validate_region.sql")
    if check_published:
        required.append("07_published_snapshot.sql")
    for name in required:
        if sha256(folder / name) != handoff["sql_sha256"].get(name):
            raise ValueError("SQL checksum mismatch: regenerate handoff")
    out = folder.parent / "cloud-evidence" / uuid.uuid4().hex[:12]
    out.mkdir(parents=True)
    # Archive the exact scripts and local evidence, including unexecuted publication SQL.
    for path in folder.glob("*.sql"):
        (out / path.name).write_bytes(path.read_bytes())
    (out / "handoff.json").write_bytes((folder / "handoff.json").read_bytes())
    (out / "local-validation.json").write_bytes(
        (folder.parent / "validation.json").read_bytes()
    )
    summary = dict(
        run_id=report["run_id"],
        created_utc=datetime.now(timezone.utc).isoformat(),
        status="IN_PROGRESS",
        workgroup=workgroup,
        published=False,
        published_snapshot_checked=check_published,
        checks=[],
    )

    def save():
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    def query(name, label):
        return execute(
            client,
            (folder / name).read_text(),
            handoff["database"],
            workgroup,
            out / (label + ".json"),
            result_location,
        )

    save()
    try:
        before = (
            query("07_published_snapshot.sql", "published-before")
            if check_published
            else None
        )
        for name in ["05_validate_schema.sql", "03_validate.sql"] + (
            ["03b_validate_region.sql"] if handoff["region_ready"] else []
        ):
            result = query(name, Path(name).stem)
            failures = failure_count(result)
            summary["checks"].append(
                dict(
                    name=name,
                    query_id=result["query_id"],
                    failures=failures,
                    passed=failures == 0,
                )
            )
        probe = query("06_failure_probe.sql", "failure-probe")
        detected = failure_count(probe) > 0
        summary["checks"].append(
            dict(
                name="altered_amount_detected",
                query_id=probe["query_id"],
                passed=detected,
            )
        )
        if check_published:
            after = query("07_published_snapshot.sql", "published-after")
            same = (
                bool(before["rows"])
                and before["columns"] == after["columns"]
                and before["rows"] == after["rows"]
            )
            summary["checks"].append(
                dict(
                    name="published_result_unchanged",
                    passed=same,
                    before_query_id=before["query_id"],
                    after_query_id=after["query_id"],
                )
            )
        summary["status"] = (
            "PASS" if all(c["passed"] for c in summary["checks"]) else "FAIL"
        )
    except Exception as exc:
        summary.update(status="FAIL", error_type=type(exc).__name__, error=str(exc))
    save()
    print(
        json.dumps(
            dict(status=summary["status"], evidence=str(out), published=False), indent=2
        )
    )
    return summary, out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff-dir", required=True)
    p.add_argument("--workgroup", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--result-location")
    p.add_argument("--check-published", action="store_true")
    args = p.parse_args()
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "athena",
        region_name=args.region,
        config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 3}),
    )
    result, _ = collect(
        client,
        args.handoff_dir,
        args.workgroup,
        args.result_location,
        args.check_published,
    )
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
