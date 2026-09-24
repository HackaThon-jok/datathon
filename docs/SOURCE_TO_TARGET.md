# January report source-to-target mapping

Scope: first sheet of `data/grouth_truth/2026-1.xlsx`, or its nine-column CSV representation. Grain: one retained physical detail row per source file. Key: source-file checksum (batch_id) + source_row_id. No transactional uniqueness is inferred from SKU.

| Source | Target | Rule |
|---|---|---|
| First row, raw_col_2 | month DATE | Parse English month/year; first day is a reporting-month key, not transaction date |
| Third row, raw_col_1 | store | Store heading inherited by all detail rows; multiple-store layouts rejected |
| Explicit optional JSON map | region | NULL when missing; never infer geography from store name |
| Detail raw_col_1 | item_code / item_label | Extract first bracketed code; preserve full label; non-bracketed detail fails validation |
| Detail raw_col_2 | orders BIGINT | Integer only; missing/invalid becomes NULL plus blocking issue |
| Detail raw_col_3 | quantity BIGINT | Same rule; negatives retained |
| Detail raw_col_4 | sales_amount DECIMAL(18,2) | Decimal parse, per-row half-up rounding; invalid values block |
| raw_col_5..7 | retained in RAW only | Report Total columns are not added to monthly columns |
| source_row_id / ingest_row_id | BIGINT lineage columns | Order by source_row_id; identical source copies deduplicated; conflicting copies block |
| Input bytes SHA-256 | batch_id | First 16 hex characters; full checksum in validation.json |

Headers (rows 1-2), store summary (row 3), final Total are excluded from detail aggregation. Summary numeric fields are still checked for invalid values. Interior discount/freight/wallet/gift lines are retained, including negatives and zero.

MART grain: month × store × region × batch_id. SUM orders, quantity and amount; count detail rows. January expected detail count is 362. The independent expected aggregate is read from the legacy Excel Total row and checked against its store summary, not computed with the candidate transformation.

Deduplication uses physical source identity, not equal item labels. Two different source rows with the same SKU are preserved. This dataset's duplicates retain source_row_id and allocate new ingest_row_id. Missing source IDs, wrong headers or unsupported report structure stop the run; partial output remains candidate-only and the published pointer is unchanged.


## Explicit contracts and regional model

`analytics/contracts.py` defines every output column, its order and exact DuckDB type. Every run verifies all four schemas; the Athena bundle compares `information_schema.columns` to the equivalent expected names, ordinals and types. Extra or changed source CSV columns require a new contract rather than silent acceptance.

When an explicit store-to-region mapping is complete, `mart_monthly_region` groups by month × region × batch_id and checks its totals against the original report. Without a complete mapping this table is empty. `--require-region` makes missing mapping a blocking condition. This does not expand the single-store input-layout scope.

Amounts must fit DECIMAL(18,2), and order/quantity values must fit signed BIGINT. Non-finite, fractional integer and overflowing values are recorded as invalid. Source store/Total values are also checked against the independent baseline, including numeric-but-incorrect summaries.
