"""Explicit local and Athena schema contracts for the report migration."""

import hashlib
import json
from pathlib import Path

SCHEMAS = {
    "staging_sales": [
        ("month", "DATE"),
        ("store", "VARCHAR"),
        ("region", "VARCHAR"),
        ("item_code", "VARCHAR"),
        ("item_label", "VARCHAR"),
        ("orders", "BIGINT"),
        ("quantity", "BIGINT"),
        ("sales_amount", "DECIMAL(18,2)"),
        ("batch_id", "VARCHAR"),
        ("source_row_id", "BIGINT"),
        ("ingest_row_id", "BIGINT"),
    ],
    "mart_monthly_store": [
        ("month", "DATE"),
        ("store", "VARCHAR"),
        ("region", "VARCHAR"),
        ("batch_id", "VARCHAR"),
        ("detail_rows", "BIGINT"),
        ("orders", "BIGINT"),
        ("quantity", "BIGINT"),
        ("sales_amount", "DECIMAL(18,2)"),
    ],
    "mart_monthly_region": [
        ("month", "DATE"),
        ("region", "VARCHAR"),
        ("batch_id", "VARCHAR"),
        ("detail_rows", "BIGINT"),
        ("orders", "BIGINT"),
        ("quantity", "BIGINT"),
        ("sales_amount", "DECIMAL(18,2)"),
    ],
    "baseline": [
        ("month", "DATE"),
        ("store", "VARCHAR"),
        ("orders", "BIGINT"),
        ("quantity", "BIGINT"),
        ("sales_amount", "DECIMAL(18,2)"),
    ],
}


def inspect_schemas(connection):
    results = []
    for name, expected in SCHEMAS.items():
        actual = [
            (row[0], row[1])
            for row in connection.execute(f"DESCRIBE {name}").fetchall()
        ]
        results.append(
            dict(
                table=name, passed=actual == expected, expected=expected, actual=actual
            )
        )
    return results


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_run(folder):
    folder = Path(folder)
    report = json.loads((folder / "validation.json").read_text())
    if (
        report.get("status") != "PASS"
        or not report.get("checks")
        or not all(c["passed"] for c in report["checks"])
    ):
        raise ValueError("Refusing publication of a failed local run")
    required = {
        "staging_sales.parquet",
        "mart_monthly_store.parquet",
        "baseline.parquet",
    }
    hashes = report.get("output_sha256", {})
    if not required.issubset(hashes):
        raise ValueError("Missing required output checksums")
    for name, expected in hashes.items():
        if (
            Path(name).name != name
            or not (folder / name).is_file()
            or sha256(folder / name) != expected
        ):
            raise ValueError("Output checksum mismatch: rerun local validation")
    return report
