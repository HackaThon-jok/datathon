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

## All months (real legacy Excel)

```bash
python src/pipeline.py --source data/grouth_truth/2026-[1-4].xlsx
```

- `.xlsx` sources are copied unchanged to `data/raw/<batch_id>/source.xlsx` and converted to `source.csv` by `src/extract.py` (text only, no interpretation).
- Each month is validated against the price-type report of the **same month** (`2026-Np.xlsx`); a missing baseline fails the run.
- The injected-error answer file is only used for `data/legacy_dirty/sales_dirty.csv` (or `--truth-log`).
- ⚠️ Candidate MART folders accumulate across runs. Consumers must read the **published** version (RELEASE-001), not all candidates, or months will be double-counted.

## Upload to S3 (AWS-007)

Requires an AWS CLI profile for your IAM user (never commit keys). Bucket `dsc-datathon-storage` is in `ap-southeast-6`.

```bash
python src/upload_s3.py --bucket dsc-datathon-storage --dry-run          # plan only, no AWS calls
python src/upload_s3.py --bucket dsc-datathon-storage --profile <profile> --region ap-southeast-6
```

| S3 prefix | Content |
|---|---|
| `raw/monthly_sales/<batch_id>/` | Original source file, extracted `source.csv`, `manifest.json` |
| `staging/monthly_sales/batch_id=<batch_id>/` | `sales_lines.parquet`, `dq_issues.parquet` |
| `mart/monthly_sales/candidate/run_id=<run_id>/` | Candidate MART Parquet (VALIDATED runs only) |

- Every object is uploaded with a SHA-256 checksum and SSE-S3 (AES256), then read back to verify both.
- An existing key with the same checksum is skipped; a different checksum stops the run — objects are never overwritten.
- IAM needed: `s3:ListBucket`, `s3:PutObject`, `s3:GetObject` on the prefixes above (no delete).
- Evidence: `docs/evidence/aws-007-upload-report.csv` (44 objects; a rerun skips all 44).

## Load RAW into Snowflake

Create a local `.env` (git-ignored — check with `git check-ignore .env`):

```
SNOWFLAKE_ACCOUNT=lnngkqb-qs06919
SNOWFLAKE_USER=<user>
SNOWFLAKE_PASSWORD=<password>
SNOWFLAKE_ROLE=DATA_LOADER
SNOWFLAKE_WAREHOUSE=DATATHON_WH
```

```bash
python src/load_snowflake.py --dry-run                 # print the SQL plan, no connection
python src/load_snowflake.py                           # load all VALIDATED batches
python src/load_snowflake.py --batch b_12f3b639b7ab    # load one batch
```

| Snowflake object | Content |
|---|---|
| `DATATHON_DEV.RAW.SALES_RAW_BATCHES` | Original 9 RAW columns + `BATCH_ID`, `SOURCE_FILE`, `LOADED_AT`; one row per source row |
| `DATATHON_DEV.RAW.LOAD_MANIFEST` | One row per batch: SHA-256, expected vs loaded rows, `LOADED`/`FAILED`, user, time |
| `DATATHON_DEV.RAW.LOAD_STAGE` | Internal stage used by `PUT` |

- Only batches with a VALIDATED pipeline run are loaded; failed batches (e.g. malformed files) are skipped.
- A batch already `LOADED` in the manifest is skipped, so reruns never duplicate rows.
- Row counts are checked after `COPY INTO`; a mismatch is recorded as `FAILED` and stops the run.
- `RAW.SALES_RAW` (read by `sql/datathon_migration.sql`) is **not** touched. Filter `SALES_RAW_BATCHES` by `BATCH_ID` or `SOURCE_FILE` to select a month.
- Role `DATA_LOADER` needs: USAGE on `DATATHON_WH`, `DATATHON_DEV`, `DATATHON_DEV.RAW`; CREATE TABLE and CREATE STAGE on `DATATHON_DEV.RAW`. `ANALYST` has SELECT on both new tables.
- Current load: 5 batches (Jan–Apr 2026 + `sales_dirty.csv`), 1,299 rows, all `LOADED` with matching counts.
