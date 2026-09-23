# Data Engineer

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md) · [Architecture diagram](../aws-python-architecture.html)

> **Stack:** Python + DuckDB locally; Amazon S3 + AWS Glue Data Catalog + Amazon Athena + Streamlit on AWS online.

## Ownership

Own source inspection, extraction, file formats, manifests, batch lineage and safe ingestion. Preserve source exceptions; do not change KPI logic merely to make reconciliation pass.

## Phase 1 — Local Prototype

**Tasks**

- Inspect real source sheets/tables and record columns, inferred types, row counts and anomalies.
- Build Python extraction and ingestion commands that load an unchanged snapshot into DuckDB RAW.
- Create batch_id, run_id, SHA-256 and a manifest containing expected row count and source identity.
- Produce local RAW/STAGING Parquet fixtures without embedding machine-specific paths or credentials.

**Evidence and exit criteria**

- Reproducible Python command, manifest and source-to-DuckDB count report.
- Re-running the same batch does not double the local business result.

## Phase 2 — AWS MVP

**Tasks**

- Upload immutable source files and manifests to the agreed S3 RAW prefix.
- Write typed, compressed Parquet to STAGING/MART candidate prefixes with batch/run metadata.
- Register or update Glue Catalog metadata and verify Athena can query the candidate data.
- Classify malformed data separately from transient AWS errors; use bounded retry only for transient failures.

**Evidence and exit criteria**

- Source → S3 → Glue → Athena lineage, row counts and rejected-record evidence are reproducible.
- An identical-batch rerun is non-duplicating and a malformed file becomes FAILED rather than silently passing.

## Phase 3 — Production-ready

**Tasks**

- Containerise the same Python package for AWS execution and expose clear phase entry points.
- Add EventBridge/Step Functions scheduling, checkpoints and recovery for interrupted runs.
- Support schema evolution, replay and incremental loading only when stable source keys/watermarks exist.
- Emit structured CloudWatch metrics and alerts without logging sensitive records.

**Evidence and exit criteria**

- Scheduled run, replay, partial-failure recovery and schema-change tests are recorded.
- Recovery does not overwrite or duplicate the last published dataset.

## Inputs and handoffs

- Inputs: verified source and columns → Data Analyst/Architect; S3, Glue, Athena and IAM configuration → Cloud Engineer.
- Outputs: schemas, Parquet locations, batch/run IDs, counts and errors → Analytics Engineer/Data Scientist; rerun evidence → Architect.

## Shared acceptance rules

- Use Python for repeatable pipeline entry points and DuckDB for local validation.
- Keep RAW immutable and track every transformation to candidate output.
- RAW loaded does not mean PUBLISHED; the independent validation gate decides release.
- Do not introduce Phase 3 complexity before the Phase 2 path works.
