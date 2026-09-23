# Cloud Engineer

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md) · [Architecture diagram](../aws-python-architecture.html)

> **Stack:** Python + DuckDB locally; Amazon S3 + AWS Glue Data Catalog + Amazon Athena + Streamlit on AWS online.

## Ownership

Own AWS foundations, IAM, cost controls, deployment paths and cloud-operability handoffs. Do not own KPI definitions, transformation correctness or dashboard business design.

## Phase 1 — Local Prototype

**Tasks**

- Confirm the AWS account, Region, service quotas, budget and resource naming convention.
- Design least-privilege roles for pipeline write, Athena development, Streamlit read-only access and administration.
- Document local AWS credential-chain usage without storing access keys in the repository.
- Define S3 prefixes, Glue database/table names, Athena workgroup and App Runner/ECR names.

**Evidence and exit criteria**

- Reviewed resource plan, IAM matrix, budget owner and safe local configuration guide.
- No secret or sensitive dataset is committed to Git.

## Phase 2 — AWS MVP

**Tasks**

- Create encrypted, non-public S3 storage for RAW/STAGING/MART and Athena results.
- Configure Glue Data Catalog, Athena workgroup limits, query-result location and scoped IAM roles.
- Provide ECR and App Runner deployment for Streamlit with read-only Athena/S3 permissions.
- Enable AWS Budgets and document teardown plus connection troubleshooting.

**Evidence and exit criteria**

- Data Engineer can write only the agreed prefixes and query the development workgroup.
- Streamlit can query the published view but cannot alter RAW, STAGING or MART.
- A negative-permission test and a successful end-to-end connection test are recorded.

## Phase 3 — Production-ready

**Tasks**

- Define resources with reviewed IaC and separate development from published access.
- Configure EventBridge, Step Functions, CloudWatch logs/alarms and Secrets Manager where secrets are unavoidable.
- Exercise access revocation, credential rotation, S3 object recovery and environment recreation.

**Evidence and exit criteria**

- IaC, monitoring dashboard/alarms, cost controls and recovery runbook are versioned.
- Another authorised member can recreate the non-secret environment and complete a recovery exercise.

## Inputs and handoffs

- Inputs: data size/format, pipeline actions, dashboard query contract, budget and retention requirements.
- Outputs: S3 prefixes, Glue database, Athena workgroup and IAM roles → Data Engineer; App Runner/ECR and read-only role → Streamlit owner; cost/security status → Team Lead.

## Shared acceptance rules

- Online services stay within AWS; DuckDB remains a local pre-online test dependency.
- Public S3 access is blocked and data is encrypted.
- Athena scan cost is constrained with workgroups, Parquet and partitioning.
- Proposed Phase 3 controls are not labelled complete until exercised.
