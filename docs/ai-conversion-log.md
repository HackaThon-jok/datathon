# AI Conversion Log — DATA-002 Local Pipeline

| Field | Value |
|---|---|
| Card | DATA-002 — one local command creates RAW/STAGING/MART and validation evidence |
| Date | 2026-09-24 |
| AI tool / model | Claude (Anthropic), via Claude Cowork |
| Author / operator | xiangru-he (Data Engineer) |
| Human reviewer | xiangru-he; team review via Pull Request |

## 1. Legacy input (unchanged)

- `data/legacy_dirty/sales_dirty.csv` — January 2026 legacy sales report (373 rows, SHA-256 `d7cd179c3fa2…`), derived from `data/grouth_truth/2026-1.xlsx` with 24 injected errors recorded in `data/corruption_manifest/corruption_log.csv`.
- Report layout: two header rows, one store summary row, item rows, one Total row. Item text encodes several fields, e.g. `[SKU1141] [Ambervale]Immune Support Milk Powder (900g){Express Freight}`.

## 2. What the AI was asked to do

1. Turn the report layout into one row per item, separating header, store-total and grand-total rows.
2. Parse the item text into `item_code`, `brand`, `item_name`, `variant` and classify `line_type` (product / discount / freight / gift / wallet).
3. Detect duplicates, missing values and invalid numbers **without silently repairing them**.
4. Build a validation step against independent baselines, a one-command pipeline with batch/run lineage, a MART star schema and automated tests.

## 3. AI-generated output

| File | Content |
|---|---|
| `src/transform.py` | Row typing, de-duplication by `source_row_id`, regex parsing, `TRY_CAST` numeric conversion, `dq_issues` table |
| `src/validate.py` | Check A: detected issues vs corruption log; Check B: reconciliation vs store total and `2026-1p.xlsx` |
| `src/mart.py` | `dim_product`, `fact_monthly_sales`, `report_totals` |
| `src/pipeline.py` | SHA-256 batch_id, run_id, immutable RAW + manifest, append-only run log, FAILED handling |
| `tests/test_pipeline.py` | Schema, required fields, row counts, KPI, rerun idempotency |

Key parsing rules (DuckDB SQL):

```sql
regexp_extract(raw_col_1, '^\[([^\]]+)\]', 1)                          -- item_code
regexp_extract(raw_col_1, '^\[[^\]]+\]\s*\[([^\]]+)\]', 1)             -- brand
regexp_extract(raw_col_1, '\{([^}]*)\}$', 1)                           -- variant
```

## 4. Human review — findings and edits

| # | Finding | Action |
|---|---|---|
| 1 | Sample printout showed `SKU1177` twice: the query omitted the `copy_no = 1` filter, so a duplicate row was displayed. Parquet output was already correct. | Fixed the print query |
| 2 | `requirements.txt` had no trailing newline; appending a package would corrupt the last line. | Appended with a leading newline |
| 3 | Pinned `numpy==2.5.3` requires Python ≥ 3.12; install fails on 3.11. | Documented Python ≥ 3.12 |
| 4 | Business rule check: the planned KPI is "monthly sales by **region**", but the data contains a single store and no region field. | Raised to Data Analyst / Solution Architect (DATA-001) |
| 5 | Design decision: missing `orders` values could be copied from the mirrored Total columns, but this is only valid for single-month reports. | Not repaired; kept as NULL + `has_dq_issue` flag |

## 5. Test evidence

| Check | Result |
|---|---|
| Issue detection vs corruption log | 24 / 24 found, 0 false positives (precision 100%, recall 100%) |
| Amount: detail sum vs store total vs price-type report | 89,312.44 = 89,312.44 = 89,312.44 — PASS |
| Orders / qty | Gap of 14 / 49 equals exactly the original values of the corrupted cells — PASS WITH ACCEPTED EXCEPTIONS |
| Rerun of the same batch | 364 staging rows before and after — no duplication |
| Missing source file | Run recorded as FAILED; earlier runs preserved |
| `python -m pytest -v` | 7 passed |

## 6. Limitations

- Only January 2026 has a dirty test file; February–April are not yet ingested.
- The baseline is the legacy report itself; no transaction-level source is available.
- AWS path (S3 / Glue / Athena) is covered by AWS-007 and DATA-003, not by this card.
