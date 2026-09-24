# Local Data Pipeline (DATA-002)

## Setup (once)

Requires **Python ≥ 3.12**.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python src/pipeline.py                     # RAW → STAGING → MART → VALIDATE
python src/pipeline.py --source other.csv  # another source file
python -m pytest -v                        # automated tests
```

## Outputs (git-ignored, regenerated on every run)

| Path | Content | Rerun behaviour |
|---|---|---|
| `data/raw/<batch_id>/source.csv`, `manifest.json` | Immutable source snapshot + SHA-256, row count, time | Never overwritten |
| `data/staging/batch_id=<batch_id>/sales_lines.parquet` | One row per report line, parsed fields | Overwritten for the same batch (no duplication) |
| `data/staging/batch_id=<batch_id>/dq_issues.parquet` | Duplicates, missing and invalid values | Overwritten for the same batch |
| `data/mart/candidate/run_id=<run_id>/` | `dim_product`, `fact_monthly_sales`, `report_totals` | New folder per run |
| `data/validation/run_id=<run_id>/validation_report.csv` | PASS / PASS WITH ACCEPTED EXCEPTIONS / FAIL | New folder per run |
| `data/runs/run_log.csv` | PENDING → INGESTING → TRANSFORMING → VALIDATING → VALIDATED / FAILED | Append-only |

`batch_id` = `b_` + first 12 characters of the source SHA-256, so the same file always maps to the same batch.

## Handoff to Analytics Engineer / Data Scientist

- MART grain: one row per `report_month` × `item_code`.
- `has_dq_issue = true` marks rows whose `orders` or `qty` is NULL because of a source error.
- Report summary rows live in `report_totals`, never in the fact table.

## Source profile

```bash
python src/profile_sources.py   # regenerates docs/source-profile.md from data/grouth_truth/
```

## Row lineage

Every successful run writes `data/validation/run_id=<run_id>/row_lineage.csv`:
source rows − header rows − duplicates = STAGING rows = MART fact rows + report total rows.
A mismatch fails the run.

## Failure handling

Missing, empty or wrongly structured source files end in state `FAILED`, with the failing step and error recorded in `data/runs/run_log.csv` (covered by `tests/test_failures.py`).
