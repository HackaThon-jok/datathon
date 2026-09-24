import contextlib
import csv
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import duckdb

from analytics.pipeline import extract_workbook, number, run, transform

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/grouth_truth/2026-1.xlsx"
DIRTY = ROOT / "data/legacy_dirty/sales_dirty.csv"


class MigrationFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        fixture = self.folder / "fixture.csv"
        extract_workbook(SOURCE, fixture)
        with fixture.open(newline="") as stream:
            self.rows = list(csv.DictReader(stream))

    def tearDown(self):
        self.tmp.cleanup()

    def execute(self, source, publish=True):
        with contextlib.redirect_stdout(io.StringIO()):
            return run(source, SOURCE, self.folder / "output", publish=publish)


class MigrationTests(MigrationFixture):
    def test_clean_matches_original_report_and_parquet_contract(self):
        report, folder = self.execute(SOURCE)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["detail_rows"], 362)
        self.assertFalse(report["region_ready"])
        con = duckdb.connect()
        result = con.execute(
            "SELECT orders,quantity,sales_amount FROM read_parquet(?)",
            [str(folder / "mart_monthly_store.parquet")],
        ).fetchone()
        self.assertEqual(result, (542, 2395, Decimal("89312.44")))
        types = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(folder / "mart_monthly_store.parquet")],
        ).fetchall()
        self.assertEqual(dict((r[0], r[1]) for r in types)["orders"], "BIGINT")
        con.close()

    def test_dirty_detected_and_failed_run_cannot_replace_published(self):
        clean, _ = self.execute(SOURCE)
        pointer = self.folder / "output/published.json"
        before = pointer.read_bytes()
        dirty, _ = self.execute(DIRTY)
        self.assertEqual(dirty["status"], "FAIL")
        self.assertEqual(dirty["removed_duplicates"], 7)
        self.assertEqual(
            sum(i["code"] == "INVALID_OR_MISSING_NUMBER" for i in dirty["issues"]), 17
        )
        self.assertEqual(pointer.read_bytes(), before)
        self.assertFalse(dirty["published"])
        self.assertNotEqual(clean["run_id"], dirty["run_id"])

    def test_repeated_runs_do_not_append_business_rows(self):
        first, _ = self.execute(SOURCE)
        second, _ = self.execute(SOURCE)
        self.assertEqual(first["checks"], second["checks"])
        self.assertEqual(first["detail_rows"], second["detail_rows"])
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_conflicting_duplicate_is_not_silently_accepted(self):
        copy = dict(self.rows[3], raw_col_4="999.00", ingest_row_id="999")
        _, issues = transform(self.rows + [copy], "batch")
        self.assertTrue(
            any(
                i["code"] == "CONFLICTING_DUPLICATE" and i["severity"] == "ERROR"
                for i in issues
            )
        )

    def test_identical_duplicate_preserves_amount_and_discount_lines(self):
        copy = dict(self.rows[3], ingest_row_id="999")
        staged, issues = transform(self.rows + [copy], "batch")
        self.assertEqual(sum(r[7] for r in staged), Decimal("89312.44"))
        self.assertEqual(len(staged), 362)
        self.assertTrue(any(r[7] < 0 for r in staged))
        self.assertTrue(any(i["code"] == "DUPLICATE_SOURCE_ROW" for i in issues))

    def test_shuffled_input_uses_source_order_not_arrival_order(self):
        a, _ = transform(self.rows, "batch")
        b, _ = transform(list(reversed(self.rows)), "batch")
        self.assertEqual(a, b)

    def test_missing_source_row_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing source rows"):
            transform(self.rows[:10] + self.rows[11:], "batch")

    def test_unknown_detail_cannot_publish(self):
        self.rows[3]["raw_col_1"] = "Another store heading"
        _, issues = transform(self.rows, "batch")
        self.assertTrue(any(i["code"] == "UNSUPPORTED_DETAIL_ROW" for i in issues))

    def test_explicit_region_mapping_only(self):
        staged, _ = transform(
            self.rows, "batch", {"Kea Wellness - Central": "TEST REGION"}
        )
        self.assertTrue(all(r[2] == "TEST REGION" for r in staged))

    def test_numeric_edges(self):
        for value in ("", "INVALID_VALUE", "NaN", "Infinity"):
            self.assertIsNone(number(value))
        self.assertIsNone(number("1.5", integer=True))
        self.assertEqual(number("-446.44"), Decimal("-446.44"))
        self.assertEqual(number("1,234.565"), Decimal("1234.57"))


class AthenaHandoffTests(MigrationFixture):
    def test_cloud_query_parity_and_corruption_detection_locally(self):
        from analytics.athena import build

        _, folder = self.execute(SOURCE)
        with contextlib.redirect_stdout(io.StringIO()):
            out, names = build(
                folder, "migration_demo", "s3://example-bucket/migration"
            )
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
        query = (out / "03_validate.sql").read_text()
        self.assertEqual(con.execute(query).fetchone()[0], 0)
        con.execute(
            f"UPDATE {names['staging_sales']} SET sales_amount = sales_amount + 1 WHERE source_row_id=4"
        )
        self.assertGreater(con.execute(query).fetchone()[0], 0)
        con.close()

    def test_changed_parquet_cannot_reuse_validation(self):
        from analytics.athena import build

        _, folder = self.execute(SOURCE)
        (folder / "staging_sales.parquet").write_bytes(b"changed after validation")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            build(folder, "migration_demo", "s3://example-bucket/migration")

    def test_failed_run_cannot_generate_cloud_publication_sql(self):
        from analytics.athena import build

        _, folder = self.execute(DIRTY)
        with self.assertRaisesRegex(ValueError, "failed local run"):
            build(folder, "migration_demo", "s3://example-bucket/migration")


if __name__ == "__main__":
    unittest.main()
