# Solution Architect / Team Lead

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md) · [Architecture diagram](../aws-python-architecture.html)

> **Stack:** Python + DuckDB locally; containerized Python/FastAPI on Amazon ECS Fargate online, with Amazon S3, AWS Glue Data Catalog and Amazon Athena for the AWS data path.

## Ownership

Own scope, architecture, named ownership, cross-role contracts and the evidence-based release decision. Coordinate the whole migration without absorbing every implementation task. The Data Analyst owns business definitions, the Data Scientist owns independent validation, and a named Python-capable contributor owns the API/UI.

## Phase 1 — Local Prototype

**Tasks**

- Confirm the source, legacy report logic, monthly-sales-by-region definition and MVP boundary.
- Define the Python package boundary, DuckDB local flow, data zones, run states and role handoffs.
- Require one local command, one configuration convention and an independent validation gate.
- Assign named owners for AWS, ingestion, modelling, validation, API/UI and release approval.

**Evidence and exit criteria**

- Approved local architecture, ownership matrix and acceptance checklist.
- DuckDB run produces the candidate KPI and validation report from a controlled snapshot.

## Phase 2 — AWS MVP

**Tasks**

- Approve the ECR → ECS Fargate runtime and the S3 → Glue Catalog → Athena → Validation Gate → published view → FastAPI data flow.
- Define local/AWS contracts for schema, row count, KPI, batch_id, run_id and query outputs.
- Lead the end-to-end integration test and block publication when critical checks fail.
- Confirm the dashboard role can read only the published Athena surface.

**Evidence and exit criteria**

- Reviewed AWS architecture, integration evidence and release decision record.
- DuckDB and Athena reconcile; a failed candidate leaves the last validated version available.

## Phase 3 — Production-ready

**Tasks**

- Approve EventBridge/Step Functions orchestration, CloudWatch monitoring, Secrets Manager and IaC boundaries.
- Define rollback, recovery time, data retention, change approval and incident ownership.
- Exercise a failed run, credential rotation and published-version recovery.

**Evidence and exit criteria**

- Versioned architecture decisions, recovery runbook and completed failure/restore exercise.
- Team can rebuild the controlled environment and explain remaining risks and costs.

## Inputs and handoffs

- Inputs: source/KPI definition, data-size estimate, AWS constraints, role capacity and validation evidence.
- Outputs: approved contracts and owners → all roles; published-view contract → API/UI owner; release decision → team.

## Shared acceptance rules

- Python is the common implementation base; DuckDB is local validation, not the online warehouse.
- Athena candidate data becomes published only after independent checks and explicit approval.
- AI output requires human review and cannot be its own independent ground truth.
- Phase 1 and Phase 2 are the MVP; Phase 3 must not delay the working demo.
