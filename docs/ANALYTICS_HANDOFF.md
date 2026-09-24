# Analytics migration: run and handoff

The current implementation covers the first worksheet of `data/grouth_truth/2026-1.xlsx`: one month and one store. It produces a locally validated model and generates run-specific Athena SQL. Region mapping, live Athena validation and business sign-off remain pending.

## Local run

From the repository root, using Python 3.13:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analytics.txt
.venv/bin/python -m analytics.verify
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
| `mart_monthly_region.parquet` | Regional aggregate only when every row has an explicit mapping; otherwise empty |
| `schema-contract.json` | Field names, order and types, with pass/fail per table |
| `source.*` / `reference.xlsx` | Preserved input and independent baseline snapshots |
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
3. Run `03_validate.sql` and `05_validate_schema.sql`. Both must return `failures = 0`. If region mapping is complete, also run `03b_validate_region.sql`. This checks cloud/local aggregate parity, legacy totals, required values, source-row uniqueness, detail counts and result-group counts.
4. Run `06_failure_probe.sql`; the deliberately altered amount must produce a nonzero failure count. It does not modify any table or view. Save the QueryExecutionId, result, run ID and reviewer decision. Only after approval, run `04_publish_after_review.sql`. On failure, leave the existing published view unchanged.

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

## Evidence collection after cloud setup

Install the optional SDK and run the collector after uploading Parquet and creating the candidate objects. Replace the example variables with the actual environment values:

```bash
.venv/bin/python -m pip install -r requirements-analytics-aws.txt
.venv/bin/python -m analytics.cloud_validate \
  --handoff-dir artifacts/analytics/runs/<run-id>/athena \
  --workgroup <workgroup> \
  --region <aws-region>
```

If the workgroup does not provide a results location, add `--result-location s3://<bucket>/<results-prefix>/`. If a published store view already exists, add `--check-published` to compare its results before and after the read-only fault probe. Without that flag, no claim of observed cloud published-result stability is made.

This command executes only the generated validation SELECT queries, never the DDL or publication SQL. Athena queries can incur scan charges. It disables result reuse, archives the exact SQL and local validation, and records query IDs, results, actual scan bytes, duration and failures under `cloud-evidence/<attempt-id>/`. Timeout requests cancellation and preserves the query ID. A failed check exits nonzero. The failed candidate scenario is a read-only altered-result probe; it does not prove that IAM prevents an operator from manually publishing an invalid candidate.

The collector has been tested with simulated AWS client responses. Those tests are not live cloud evidence. SDK/API references: [query execution](https://docs.aws.amazon.com/boto3/latest/reference/services/athena/client/get_query_execution.html), [query results](https://docs.aws.amazon.com/boto3/latest/reference/services/athena/client/get_query_results.html), [catalog columns](https://docs.aws.amazon.com/athena/latest/ug/querying-glue-catalog-listing-columns.html).

## Regions, replay and local rollback

To require a regional result, supply `--region-map <mapping.json> --require-region` to `analytics.pipeline`. The JSON is a store-name-to-region-name object; use an approved real mapping, not the synthetic label in tests. Both local and cloud regional sums have tests. Without a mapping, region is NULL, the region mart is empty, and store-level reporting remains explicitly scoped.

A late corrected source is processed as a new complete snapshot, never appended to old rows. Preserve the original failed run. To restore an earlier verified local version:

```bash
.venv/bin/python -m analytics.release --output artifacts/analytics --run-id <previous-passing-run-id>
```

Rollback validates checksums before switching and writes a release-history event. It cannot target failed or modified runs. This command does not restore any AWS view. See [acceptance status](ANALYTICS_ACCEPTANCE.md) for the remaining production and team dependencies.
