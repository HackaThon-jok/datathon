# Data Scientist / Independent Validation Owner

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md) · [Architecture diagram](../aws-python-architecture.html)

> **Stack:** Python + DuckDB locally; containerized Python/FastAPI on Amazon ECS Fargate online, with Amazon S3, AWS Glue Data Catalog and Amazon Athena for the AWS data path.

## Ownership

Own independent data-quality, reconciliation and anomaly evidence. Do not reuse the transformation under test as the only validator, and do not approve unexplained critical differences.

## Phase 1 — Local Prototype

**Tasks**

- Create Python tests for schema, required fields, uniqueness, valid dates/amounts and source-to-RAW totals.
- Compare DuckDB month × region KPI output with the Data Analyst baseline using tolerances approved by the business owner.
- Classify differences as source issue, definition mismatch, transformation defect or expected rounding.
- Keep validation code and expected results separate from the AI-generated migration logic.

**Evidence and exit criteria**

- Local quality report, grouped reconciliation and documented exception list.
- No unexplained critical difference remains before AWS publication begins.

## Phase 2 — AWS MVP

**Tasks**

- Run equivalent checks against the Athena candidate using the same snapshot and contracts.
- Compare DuckDB and Athena schema, row count, null/duplicate measures and month × region KPI.
- Produce a signed release recommendation: PASS, PASS WITH ACCEPTED EXCEPTIONS, or FAIL.
- Verify a failed candidate does not change the published Athena view.

**Evidence and exit criteria**

- Reproducible DuckDB/Athena reconciliation report and release recommendation.
- Every accepted difference has an owner, explanation and approval; FAIL blocks publication.

## Phase 3 — Production-ready

**Tasks**

- Add monitored data-quality trends, drift checks and anomaly triage for meaningful fields.
- Integrate validation status and metrics with Step Functions/CloudWatch.
- Evaluate AI conversion quality on a scoped reviewed sample; add ML only if it supports a clear migration decision.

**Evidence and exit criteria**

- Alert thresholds, triage runbook, false-positive review and drift/anomaly test evidence.
- Monitoring detects an injected quality failure and routes it to the named owner.

## Inputs and handoffs

- Inputs: independent KPI baseline → Data Analyst; RAW/candidate data and lineage → Data Engineer/Analytics Engineer.
- Outputs: quality report, exceptions and release recommendation → Architect; displayable validation status → API/UI owner.

## Shared acceptance rules

- Validation remains independent of AI-generated transformation logic.
- Local and AWS checks use the same documented business contract.
- Critical failures block publication but preserve evidence and the previous good version.
- Phase 3 anomaly/ML work is optional after deterministic validation works.
