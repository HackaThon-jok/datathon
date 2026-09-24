"""Run both scenarios; expected dirty failure is a successful demonstration."""

import json
from pathlib import Path
from analytics.pipeline import run


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "artifacts/analytics"
    baseline = root / "data/grouth_truth/2026-1.xlsx"
    clean, clean_dir = run(baseline, baseline, out, publish=True)
    if clean["status"] != "PASS":
        raise SystemExit("Clean demonstration failed")
    before = (out / "published.json").read_bytes()
    dirty, dirty_dir = run(
        root / "data/legacy_dirty/sales_dirty.csv", baseline, out, publish=True
    )
    if dirty["status"] != "FAIL" or before != (out / "published.json").read_bytes():
        raise SystemExit("Failure isolation demonstration failed")
    evidence = root / "docs/evidence"
    evidence.mkdir(exist_ok=True)
    for name, report in [("clean", clean), ("dirty", dirty)]:
        (evidence / (name + "-validation.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )
    (evidence / "monthly-store.csv").write_bytes(
        (clean_dir / "mart_monthly_store.csv").read_bytes()
    )
    print(
        "DEMO PASS: clean report matched; dirty candidate blocked; published pointer unchanged."
    )
    print("For Athena, use the clean run directory above, not the dirty candidate.")


if __name__ == "__main__":
    main()
