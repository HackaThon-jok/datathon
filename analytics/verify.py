"""Run the local acceptance suite, refresh demo evidence and archive example SQL."""

import contextlib
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from analytics.athena import build
from analytics.contracts import sha256
from analytics.demo import main as demo


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/evidence"
    evidence.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"), pattern="test_analytics*.py"
    )
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    summary = dict(
        time_utc=datetime.now(timezone.utc).isoformat(),
        tests_run=result.testsRun,
        passed=result.wasSuccessful(),
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        live_aws_tested=False,
        code_sha256={
            str(p.relative_to(root)): sha256(p)
            for directory in ("analytics", "tests")
            for p in (root / directory).glob("*.py")
        },
    )
    (evidence / "test-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (evidence / "test-results.txt").write_text(output.getvalue())
    print(output.getvalue())
    if not result.wasSuccessful():
        raise SystemExit(1)
    demo()
    pointer = json.loads((root / "artifacts/analytics/published.json").read_text())
    run_dir = Path(pointer["path"])
    sql_dir, _ = build(run_dir, "migration_demo", "s3://example-bucket/analytics")
    archived = evidence / "athena-example"
    archived.mkdir(exist_ok=True)
    for path in list(sql_dir.glob("*.sql")) + [sql_dir / "handoff.json"]:
        (archived / path.name).write_bytes(path.read_bytes())
    (archived / "README.md").write_text("""# Generated SQL example

Generated from the locally validated clean run. `migration_demo` and `s3://example-bucket/analytics` are example resources, not a deployment. These scripts have not been executed in AWS. Generate a new bundle with actual database and S3 settings for live use.

The SQL is versioned here for inspection. Actual execution IDs, statistics and results must be collected separately with `analytics.cloud_validate`. `04_publish_after_review.sql` is never executed by the collector.
""")
    (evidence / "schema-contract.json").write_bytes(
        (run_dir / "schema-contract.json").read_bytes()
    )
    print(
        f"LOCAL ACCEPTANCE PASS: {result.testsRun} tests; clean/dirty demo; versioned example SQL. Live AWS still pending."
    )


if __name__ == "__main__":
    main()
