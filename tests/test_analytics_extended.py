import contextlib
import csv
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import duckdb

from analytics.athena import build
from analytics.contracts import SCHEMAS, inspect_schemas
from analytics.pipeline import FIELDS, extract_workbook, number, run
from analytics.release import publish
from test_analytics import MigrationFixture, SOURCE, DIRTY


class AdditionalMigrationTests(MigrationFixture):
    def csv_input(self, rows=None, fields=FIELDS):
        path = self.folder / "input.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows or self.rows)
        return path

    def test_schema_change_rejected_with_failure_evidence_and_no_release(self):
        self.execute(SOURCE)
        before = (self.folder / "output/published.json").read_bytes()
        changed = self.csv_input(fields=FIELDS + ["new_unknown_column"])
        report, folder = self.execute(changed)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["error_type"], "ValueError")
        self.assertTrue((folder / "validation.json").is_file())
        self.assertEqual((self.folder / "output/published.json").read_bytes(), before)

    def test_duplicate_csv_headers_rejected(self):
        path = self.csv_input(fields=FIELDS + ["raw_col_1"])
        report, _ = self.execute(path)
        self.assertEqual(report["status"], "FAIL")

    def test_valid_but_wrong_summary_cannot_pass(self):
        self.rows[-1]["raw_col_4"] = "123.45"
        report, _ = self.execute(self.csv_input())
        self.assertEqual(report["status"], "FAIL")
        check = next(
            c for c in report["checks"] if c["check"] == "source_total_sales_amount"
        )
        self.assertFalse(check["passed"])

    def test_explicit_regional_contract_and_no_fabricated_region(self):
        with contextlib.redirect_stdout(io.StringIO()):
            absent, _ = run(
                SOURCE, SOURCE, self.folder / "regional", require_region=True
            )
            mapped, folder = run(
                SOURCE,
                SOURCE,
                self.folder / "regional",
                region_map={"Kea Wellness - Central": "SYNTHETIC_TEST_REGION"},
                require_region=True,
            )
        self.assertEqual(absent["status"], "FAIL")
        self.assertEqual(mapped["status"], "PASS")
        con = duckdb.connect()
        result = con.execute(
            "SELECT region,orders,quantity,sales_amount FROM read_parquet(?)",
            [str(folder / "mart_monthly_region.parquet")],
        ).fetchone()
        self.assertEqual(
            result, ("SYNTHETIC_TEST_REGION", 542, 2395, Decimal("89312.44"))
        )
        con.close()

    def test_late_corrected_snapshot_replay_and_rollback(self):
        first, first_dir = self.execute(SOURCE)
        bad, _ = self.execute(DIRTY)
        corrected, new_dir = self.execute(SOURCE)
        self.assertEqual(bad["status"], "FAIL")
        self.assertEqual(first["batch_id"], corrected["batch_id"])
        self.assertNotEqual(first["run_id"], corrected["run_id"])
        self.assertEqual(first["detail_rows"], corrected["detail_rows"])
        self.assertEqual(
            json.loads((self.folder / "output/published.json").read_text())["run_id"],
            corrected["run_id"],
        )
        publish(self.folder / "output", first_dir, action="rollback")
        self.assertEqual(
            json.loads((self.folder / "output/published.json").read_text())["run_id"],
            first["run_id"],
        )
        self.assertEqual(
            len(list((self.folder / "output/release-history").glob("*.json"))), 3
        )

    def test_failed_or_tampered_version_cannot_be_rollback_target(self):
        self.execute(SOURCE)
        before = (self.folder / "output/published.json").read_bytes()
        _, bad_dir = self.execute(DIRTY)
        with self.assertRaises(ValueError):
            publish(self.folder / "output", bad_dir, action="rollback")
        _, good_dir = self.execute(SOURCE, publish=False)
        (good_dir / "baseline.parquet").write_bytes(b"broken")
        with self.assertRaises(ValueError):
            publish(self.folder / "output", good_dir, action="rollback")
        self.assertEqual((self.folder / "output/published.json").read_bytes(), before)

    def test_out_of_range_values_are_explicitly_invalid(self):
        self.assertIsNone(number(str(2**63), integer=True))
        self.assertIsNone(number("10000000000000000.00"))
        self.assertEqual(number("0"), Decimal("0.00"))

    def test_reordered_or_missing_columns_fail_closed(self):
        for fields in (list(reversed(FIELDS)), FIELDS[:-1]):
            report, _ = self.execute(self.csv_input(fields=fields))
            self.assertEqual(report["status"], "FAIL")

    def test_full_local_schema_check_detects_type_drift(self):
        _, folder = self.execute(SOURCE)
        con = duckdb.connect(str(folder / "migration.duckdb"))
        self.assertTrue(all(s["passed"] for s in inspect_schemas(con)))
        con.execute("ALTER TABLE staging_sales ALTER orders TYPE VARCHAR")
        self.assertFalse(
            next(s for s in inspect_schemas(con) if s["table"] == "staging_sales")[
                "passed"
            ]
        )
        con.close()

    def test_athena_schema_query_detects_type_and_extra_column_changes(self):
        _, folder = self.execute(SOURCE)
        with contextlib.redirect_stdout(io.StringIO()):
            out, names = build(folder, "migration_demo", "s3://example-bucket/checks")
        con = duckdb.connect()
        con.execute("CREATE SCHEMA migration_demo")
        for key, file in [
            ("staging_sales", "staging_sales"),
            ("local_mart", "mart_monthly_store"),
            ("baseline", "baseline"),
        ]:
            con.execute(
                f"CREATE TABLE {names[key]} AS SELECT * FROM read_parquet(?)",
                [str(folder / (file + ".parquet"))],
            )
        con.execute((out / "02_candidate.sql").read_text())
        query = (out / "05_validate_schema.sql").read_text()
        self.assertEqual(con.execute(query).fetchone()[0], 0)
        con.execute(f'ALTER TABLE {names["baseline"]} ALTER orders TYPE VARCHAR')
        self.assertGreater(con.execute(query).fetchone()[0], 0)
        con.execute(f'ALTER TABLE {names["baseline"]} ALTER orders TYPE BIGINT')
        con.execute(f'ALTER TABLE {names["baseline"]} ADD unexpected VARCHAR')
        self.assertGreater(con.execute(query).fetchone()[0], 0)
        con.close()

    def test_regional_athena_sql_uses_explicit_mapping(self):
        with contextlib.redirect_stdout(io.StringIO()):
            _, folder = run(
                SOURCE,
                SOURCE,
                self.folder / "regional",
                region_map={"Kea Wellness - Central": "SYNTHETIC_TEST_REGION"},
                require_region=True,
            )
            out, names = build(folder, "migration_demo", "s3://example-bucket/checks")
        con = duckdb.connect()
        con.execute("CREATE SCHEMA migration_demo")
        for key, file in [
            ("staging_sales", "staging_sales"),
            ("local_mart", "mart_monthly_store"),
            ("baseline", "baseline"),
            ("local_region", "mart_monthly_region"),
        ]:
            con.execute(
                f"CREATE TABLE {names[key]} AS SELECT * FROM read_parquet(?)",
                [str(folder / (file + ".parquet"))],
            )
        con.execute((out / "02_candidate.sql").read_text())
        for file in [
            "03_validate.sql",
            "03b_validate_region.sql",
            "05_validate_schema.sql",
        ]:
            self.assertEqual(
                con.execute((out / file).read_text()).fetchone()[0], 0, file
            )
        self.assertGreater(
            con.execute((out / "06_failure_probe.sql").read_text()).fetchone()[0], 0
        )
        con.close()
