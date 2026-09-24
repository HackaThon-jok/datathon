"""AWS client simulations test collector behavior; they are not cloud evidence."""

import contextlib
import io
import json
from pathlib import Path
from analytics.athena import build
from analytics.cloud_validate import collect, execute
from test_analytics import MigrationFixture, SOURCE


class FakeAthena:
    def __init__(self, parity_fail=False, query_fail=False, changed_snapshot=False):
        self.queries = {}
        self.parity_fail = parity_fail
        self.query_fail = query_fail
        self.changed_snapshot = changed_snapshot
        self.snapshot_count = 0
        self.cancelled = []

    def start_query_execution(self, **kwargs):
        identifier = str(len(self.queries) + 1)
        self.queries[identifier] = kwargs
        return {"QueryExecutionId": identifier}

    def get_query_execution(self, QueryExecutionId):
        return {
            "QueryExecution": {
                "Status": {
                    "State": "FAILED" if self.query_fail else "SUCCEEDED",
                    "StateChangeReason": "Simulated test failure",
                },
                "Statistics": {
                    "DataScannedInBytes": 100,
                    "EngineExecutionTimeInMillis": 5,
                },
                "EngineVersion": {"EffectiveEngineVersion": "SIMULATED"},
            }
        }

    def get_query_results(self, QueryExecutionId, **kwargs):
        sql = self.queries[QueryExecutionId]["QueryString"]
        if "ORDER BY month,store,batch_id" in sql:
            self.snapshot_count += 1
            names = ["store", "sales_amount"]
            data = [
                "Fixture Store",
                "1" if self.changed_snapshot and self.snapshot_count > 1 else "0",
            ]
        else:
            names = ["failures"]
            data = [
                (
                    "1"
                    if (
                        "bad_candidate AS" in sql
                        or self.parity_fail
                        and "reverse_baseline_differences" in sql
                    )
                    else "0"
                )
            ]
        return {
            "ResultSet": {
                "ResultSetMetadata": {"ColumnInfo": [{"Name": n} for n in names]},
                "Rows": [
                    {"Data": [{"VarCharValue": n} for n in names]},
                    {"Data": [{"VarCharValue": n} for n in data]},
                ],
            }
        }

    def stop_query_execution(self, QueryExecutionId):
        self.cancelled.append(QueryExecutionId)


class CloudEvidenceTests(MigrationFixture):
    def handoff(self):
        _, folder = self.execute(SOURCE)
        with contextlib.redirect_stdout(io.StringIO()):
            out, _ = build(folder, "migration_demo", "s3://example-bucket/analytics")
        return out

    def test_archives_exact_sql_queries_statistics_and_snapshot_comparison(self):
        out = self.handoff()
        client = FakeAthena()
        with contextlib.redirect_stdout(io.StringIO()):
            summary, evidence = collect(client, out, "test", check_published=True)
        self.assertEqual(summary["status"], "PASS")
        self.assertFalse(summary["published"])
        self.assertTrue(summary["published_snapshot_checked"])
        self.assertEqual(
            (evidence / "03_validate.sql").read_bytes(),
            (out / "03_validate.sql").read_bytes(),
        )
        query = json.loads((evidence / "03_validate.json").read_text())
        self.assertEqual(query["statistics"]["DataScannedInBytes"], 100)
        self.assertTrue(
            all("CREATE" not in q["QueryString"] for q in client.queries.values())
        )
        self.assertTrue(
            all(
                q["ResultReuseConfiguration"]["ResultReuseByAgeConfiguration"][
                    "Enabled"
                ]
                is False
                for q in client.queries.values()
            )
        )

    def test_failed_parity_cannot_return_pass(self):
        with contextlib.redirect_stdout(io.StringIO()):
            summary, _ = collect(FakeAthena(parity_fail=True), self.handoff(), "test")
        self.assertEqual(summary["status"], "FAIL")

    def test_changed_published_snapshot_is_reported(self):
        with contextlib.redirect_stdout(io.StringIO()):
            summary, _ = collect(
                FakeAthena(changed_snapshot=True),
                self.handoff(),
                "test",
                check_published=True,
            )
        self.assertEqual(summary["status"], "FAIL")
        self.assertFalse(summary["checks"][-1]["passed"])

    def test_failed_aws_query_preserves_query_id_and_failure(self):
        with contextlib.redirect_stdout(io.StringIO()):
            summary, out = collect(FakeAthena(query_fail=True), self.handoff(), "test")
        self.assertEqual(summary["status"], "FAIL")
        query = json.loads((out / "05_validate_schema.json").read_text())
        self.assertEqual(query["state"], "FAILED")
        self.assertEqual(query["query_id"], "1")

    def test_edited_sql_rejected_before_any_request(self):
        out = self.handoff()
        (out / "03_validate.sql").write_text("SELECT 0 AS failures;")
        client = FakeAthena()
        with self.assertRaisesRegex(ValueError, "SQL checksum mismatch"):
            collect(client, out, "test")
        self.assertEqual(client.queries, {})

    def test_timeout_requests_cancellation_and_keeps_receipt(self):
        client = FakeAthena()
        client.get_query_execution = lambda **kwargs: {
            "QueryExecution": {"Status": {"State": "RUNNING"}}
        }
        ticks = iter([0, 1])
        path = self.folder / "query.json"
        with self.assertRaises(TimeoutError):
            execute(
                client,
                "SELECT 0 AS failures",
                "db",
                "wg",
                path,
                timeout_seconds=0,
                clock=lambda: next(ticks),
                sleep=lambda _: None,
            )
        self.assertEqual(client.cancelled, ["1"])
        self.assertEqual(
            json.loads(path.read_text())["state"], "TIMEOUT_CANCEL_REQUESTED"
        )

    def test_result_pagination_preserves_data_rows(self):
        client = FakeAthena()

        def pages(**kwargs):
            metadata = {"ColumnInfo": [{"Name": "value"}]}
            if "NextToken" in kwargs:
                return {
                    "ResultSet": {
                        "ResultSetMetadata": metadata,
                        "Rows": [{"Data": [{"VarCharValue": "b"}]}],
                    }
                }
            return {
                "ResultSet": {
                    "ResultSetMetadata": metadata,
                    "Rows": [
                        {"Data": [{"VarCharValue": "value"}]},
                        {"Data": [{"VarCharValue": "a"}]},
                    ],
                },
                "NextToken": "next",
            }

        client.get_query_results = pages
        result = execute(client, "SELECT value", "db", "wg", self.folder / "query.json")
        self.assertEqual(result["rows"], [["a"], ["b"]])
