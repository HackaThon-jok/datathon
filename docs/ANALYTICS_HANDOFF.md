# Analytics migration: run and handoff

The current implementation covers the first worksheet of `data/grouth_truth/2026-1.xlsx`: one month and one store. It produces a locally validated model and generates run-specific Athena SQL. Region mapping, live Athena validation and business sign-off remain pending.

## Local run

From the repository root, using Python 3.13:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analytics.txt
.venv/bin/python -m unittest discover -s tests -p 'test_analytics.py' -v
.venv/bin/python -m analytics.demo
```

On Windows, use `.venv\Scripts\python.exe`. AWS credentials are not needed. This module does not use the repository's legacy `start.sh`.

The demo must finish with `DEMO PASS`. It runs a clean case followed by an intentionally failing dirty case, then checks that the failed candidate did not change the local published pointer.

| Input | Raw rows | Retained detail rows | Order-column sum | Quantity | Amount | Validation |
|---|---:|---:|---:|---:|---:|---|
| Original Excel | 366 | 362 | 542 | 2395 | 89312.44 | PASS |
| Dirty CSV after deduplication | 373 | 362 | 528 | 2346 | 89312.44 | FAIL |

The dirty fixture contains seven duplicate source rows, ten missing order values and seven invalid quantity values. One missing value is in the final summary row, which is audited even though it is excluded from aggregation. Matching revenue alone does not satisfy the validation contract.

## Outputs

Each execution creates `artifacts/analytics/runs/<run_id>/`:

| File | Contents |
|---|---|
| `raw.csv` | Source fields and physical row identifiers |
| `migration.duckdb` | Staging, candidate mart and baseline tables |
| `staging_sales.parquet` | Typed detail records |
| `mart_monthly_store.parquet` / `.csv` | Monthly store aggregate |
| `baseline.parquet` | Totals read directly from the legacy workbook |
| `validation.json` | Checks, issues, input/output checksums and run status |

`artifacts/analytics/published.json` points to the latest successful local publication. Failed candidates remain available for inspection. This pointer does not publish to AWS. `docs/evidence/` contains captured demo results; rerunning the demo updates their run IDs and timestamps.

## Athena handoff

The cloud owner supplies an existing Glue database, S3 prefix, AWS identity and Athena workgroup. Replace the placeholders below before running:

```bash
.venv/bin/python -m analytics.athena \
  --run-dir artifacts/analytics/runs/<successful-run-id> \
  --database <existing-glue-database> \
  --s3-prefix s3://<bucket>/analytics
```

The generator rejects failed local runs and Parquet files whose checksums no longer match the validation report. It makes no AWS calls.

1. Review and run the generated `athena/upload.sh` using the configured AWS identity. It puts the three Parquet schemas in separate S3 directories. The script contains local absolute paths; regenerate it when moving to another machine.
2. In Athena Engine 3, run each statement in `01_tables.sql` separately, then run `02_candidate.sql`. Tables and candidate views have run-specific names.
3. Run `03_validate.sql`. It must return `failures = 0`. This checks cloud/local aggregate parity, legacy totals, required values, source-row uniqueness, detail counts and result-group counts.
4. Save the QueryExecutionId, result, run ID and reviewer decision. Only after approval, run `04_publish_after_review.sql`. On failure, leave the existing published view unchanged.

The cloud release procedure is manual, not an IAM-enforced automated gate. Candidate aggregation and parity queries have been tested locally in DuckDB against Parquet, including a modified-amount failure case. Live Athena execution remains unverified.

AWS references: [CREATE TABLE](https://docs.aws.amazon.com/athena/latest/ug/create-table.html) and [Parquet SerDe](https://docs.aws.amazon.com/athena/latest/ug/parquet-serde.html).

## Integration contract

After cloud approval, API consumers can read `published_monthly_store` with columns:

```text
month, store, region, batch_id, detail_rows, orders, quantity, sales_amount
```

`region` is currently NULL and should be shown as unmapped. A local consumer should read the mart referenced by the published pointer, not the newest candidate directory.

The data engineer can supply a local CSV matching the existing RAW schema. Each input must represent one report with source row numbers starting at 1 and continuing without gaps; duplicate copies may have new ingest IDs. No changes to `scripts/ingest.py` are required.

The validation owner should independently inspect the original workbook's store and Total rows, rerun the checks, and review the treatment of discounts, freight and wallet entries. See [source-to-target mapping](SOURCE_TO_TARGET.md) and [AI conversion record](AI_CONVERSION_LOG.md).

## Assumptions and limitations

- Only the January single-store, seven-column layout is validated. Other monthly and `p` files are outside this delivery's tested scope.
- Adjustment, gift, freight and wallet entries retain their original values to reproduce the legacy report. This is provisional report logic, not a newly approved accounting policy.
- `orders` is the sum of the report's Order column, not a distinct transaction count. Currency and tax treatment are unconfirmed.
- Missing values remain NULL and block validation. Clean reference data is not used to repair dirty inputs.
- Amounts use per-detail two-decimal ROUND_HALF_UP rounding. Negative integer order/quantity values are retained; any additional business restrictions require an agreed rule.
- Region mapping, human review, live cloud checks and final business approval must be recorded before claiming those milestones complete.
