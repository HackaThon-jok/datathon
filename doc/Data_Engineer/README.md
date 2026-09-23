# Data Engineer — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Move a verified source snapshot through Python and S3 into Snowflake RAW with traceable batches and safe rerun behaviour.

**Boundary:** Own extraction, format checks, ingestion and batch metadata; do not silently change KPI calculations or discard source exceptions just to make reconciliation pass.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can use Python to inspect/export a dataset and run a simple documented Snowflake load.

**Project tasks:**

- Inspect actual source sheets/tables; record source row count, columns, types and anomalies without assuming names.
- Use Python to export one confirmed dataset as CSV or Parquet and store an unchanged source snapshot and a small batch manifest in S3.
- Create/load one Snowflake RAW table through the configured stage and `COPY INTO`; log import outcome and rejected or missing rows.
- Before a rerun, check whether the same file/batch was loaded and avoid blindly appending it again.

**Required artifacts:**

- `src/extract.py`, `src/ingest.py` (or equally reproducible scripts) and `sql/raw/` load definition.
- Source-to-RAW count report, source path/hash and minimal batch/load log.

**Acceptance criteria:**

- One source file passes through S3 into RAW and the team can reproduce the load.
- Any source/load count mismatch is explained; a simple rerun does not double published business totals.

### Standard Delivery

**Experience fit:** Can build a repeatable ingestion pipeline that distinguishes data problems from transient infrastructure failures.

**Project tasks:**

- Assign `batch_id` and unique `run_id`; record file hash, S3 key, times, status, expected/loaded/rejected counts and error category.
- Implement and test an idempotent strategy for rerunning an identical batch, such as tracked load history plus explicit batch replacement/merge rules.
- Retry only transient connection/upload failures with bounded attempts and backoff; quarantine malformed files/rows for review.
- Emit consistent ingestion status/metadata for validation and publication; never mark a batch PUBLISHED merely because RAW loaded.

**Required artifacts:**

- `src/pipeline.py` ingestion stages and an auditable load-manifest/run-log table or equivalent store.
- Evidence from an identical-batch rerun and one simulated transient/data-error case.

**Acceptance criteria:**

- Two executions on the same source batch yield no additional business records.
- A malformed file is recorded as failed/rejected instead of silently passing; a transient outage has bounded retry behaviour.

### Advanced Delivery

**Experience fit:** Can operate change-aware, incremental ingestion and recover safely from a partial pipeline execution.

**Project tasks:**

- Implement incremental ingestion using a stable source key, watermark/change marker and an explicit late-arrival policy only if the source supports them.
- Implement stage-level checkpoints and recover an interrupted run without overwriting the previously published MART.
- Add automated scheduling, metrics/alerts for repeated failures, and tests for schema evolution and batch replay.

**Required artifacts:**

- Incremental/restore runbook and automated pipeline configuration.
- Evidence of replay, partial-failure recovery and schema-change handling.

**Acceptance criteria:**

- An interrupted or repeated batch can be recovered without duplicate published results.
- Incremental behaviour and late-arrival limitations are explained and tested on actual supported source fields.

## 3. Inputs and handoffs

**Inputs required from others:**

- Verified workbook/table and agreed source columns → Data Analyst and Solution Architect.
- S3 location, external stage, DEV credentials and permissions → Cloud Engineer.

**Outputs and recipients:**

- RAW table/schema, source file ID, batch/run ID, source/import counts and errors → Analytics Engineer and Data Scientist.
- Safe rerun instructions and ingestion evidence → Solution Architect.

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
