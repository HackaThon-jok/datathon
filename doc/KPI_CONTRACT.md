# KPI Contract: Monthly Net Sales by Region

[English](KPI_CONTRACT.md) · [简体中文](KPI_CONTRACT_CN.md) · [Project overview](../README.md)

> **Status:** Approved for the Phase 1 local prototype on 2026-09-24.

## Purpose

Define one deterministic business result for local Python and DuckDB development. The same contract will later be used to reconcile AWS results, but AWS deployment is outside Phase 1.

## Metric

| Field | Definition |
|---|---|
| Name | Monthly Net Sales by Region |
| Grain | One row per calendar month and region |
| Measure | Sum of valid detail-row `Total Price` values |
| Currency | NZD |
| Rounding | Sum full-precision values, then round the monthly result to two decimal places |
| Month | Read from the report period heading, such as `January 2026` |
| Region | Read from the location heading after the final ` - `, such as `Central` from `Kea Wellness - Central` |

## Authoritative Phase 1 inputs

- Clean positive fixtures: `data/grouth_truth/2026-1.xlsx` through `2026-4.xlsx`.
- Negative quality fixture: `data/legacy_dirty/sales_dirty.csv`.
- Injected-error evidence: `data/corruption_manifest/corruption_log.csv`.
- Run metadata: `data/validation/run_metadata.csv`.

The directory name `grouth_truth` is retained during Phase 1 to avoid an unrelated file move. It may be corrected later with all references updated together.

## Source interpretation

| Source field | Meaning | Phase 1 use |
|---|---|---|
| Column A / `raw_col_1` | Location heading, product, discount, freight or total label | Classify the row and extract the region |
| Column B / `raw_col_2` | Order count | Retain for audit; not part of the KPI calculation |
| Column C / `raw_col_3` | Product quantity | Retain for audit; validate as numeric where required |
| Column D / `raw_col_4` | Total Price | Authoritative KPI amount |
| Columns E–G / `raw_col_5`–`raw_col_7` | Duplicated report totals | Exclude from the KPI calculation |
| `source_row_id` | Stable row identity from the source snapshot | Deduplication and lineage |
| `ingest_row_id` | Identity of the ingested record | Ingestion audit only |

## Row rules

1. Exclude the report title/metric header rows.
2. Use the location summary row to obtain the business/location and region, but never add its amount to the KPI.
3. Include valid detail rows between the location summary and final `Total` row.
4. Include product, discount, e-wallet adjustment, free-gift adjustment and freight rows. Negative and zero values remain valid when supplied by the source.
5. Exclude the final `Total` row from aggregation; use it only as a reconciliation control.
6. Use Column D / `raw_col_4` only. Do not add the duplicated totals in Columns E–G.
7. For repeated `source_row_id` values, accept the first otherwise-valid occurrence and reject later occurrences as duplicates.
8. Reject detail rows with a missing or non-numeric KPI amount. Do not silently convert them to zero or infer a replacement.
9. Retain rejected rows with `run_id`, row identity and a specific rejection reason.

## Validation scenarios

### Clean baseline must pass

| Month | Region | Detail rows | Expected net sales (NZD) |
|---|---|---:|---:|
| January 2026 | Central | 362 | 89,312.44 |
| February 2026 | Central | 153 | 51,778.37 |
| March 2026 | Central | 201 | 79,635.52 |
| April 2026 | Central | 194 | 81,426.50 |
| **Total** | | **910** | **302,152.83** |

For every clean workbook, the sum of detail-row Column D values must equal both the location summary and final report total with a tolerance of NZD 0.01.

### Dirty fixture must fail safely

The supplied corruption manifest contains 24 injected issues:

- 10 missing values.
- 7 invalid numeric values.
- 7 duplicate rows.

The local validation command must detect and report these issue categories. A failed candidate may be inspected, but it must not be marked validated or replace a previously validated MART result.

## Required DuckDB outputs

| Object | Minimum content |
|---|---|
| `raw.sales_raw` | Source columns, `source_row_id`, `ingest_row_id`, `run_id` and source name |
| `staging.sales_clean` | Parsed month, business/location, region, detail label, numeric amount and lineage fields |
| `staging.sales_rejected` | Rejected row, rejection reason and lineage fields |
| `mart.monthly_sales_by_region` | `month`, `region`, `total_sales`, `source_row_count`, `run_id` and validation status |
| `validation.run_results` | Check name, expected value, actual value, status and run ID |

## Phase 1 acceptance

- One local command rebuilds the DuckDB database from controlled fixtures.
- All four clean baselines match this contract.
- The dirty fixture exposes the documented issues and returns a failed validation status.
- Automated tests cover row classification, numeric parsing, deduplication, rejection, aggregation and reconciliation.
- FastAPI exposes the latest local KPI and validation status without requiring AWS credentials.
- The README documents the exact local rerun and test commands.

## Out of scope for Phase 1

- Docker, ECR and ECS deployment.
- S3, Glue and Athena integration.
- Streamlit and production authentication.
- Scheduling, infrastructure as code, monitoring and recovery automation.

