# Cloud Engineer — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Provide a secure, cost-aware S3 and Snowflake development environment that the data pipeline can actually use.

**Boundary:** Own cloud infrastructure, access and connection handoffs; do not take ownership of KPI definitions, business SQL correctness or Streamlit UI. A separate backend server is not required.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can configure basic cloud resources with guided use of AWS and Snowflake consoles.

**Project tasks:**

- Create one project S3 bucket/prefix and a Snowflake DEV database/warehouse; confirm event and account constraints first.
- Configure scoped IAM permissions, Snowflake storage integration and an external stage that can list/read the designated raw prefix.
- Give each contributor the minimum access needed; ensure no passwords, keys or patient/customer data are committed to GitHub.

**Required artifacts:**

- `infra/setup.md` — resource names, safe configuration procedure and permission handoff (no secrets).
- Evidence that an authorised test file in S3 can be read through the Snowflake external stage.

**Acceptance criteria:**

- Data Engineer can reach the agreed S3 location and Snowflake stage with assigned access.
- The environment works without publishing credentials in the repository.

### Standard Delivery

**Experience fit:** Can independently manage access, environment consistency and basic cloud operability.

**Project tasks:**

- Separate DEV from published-data access where feasible; give Streamlit a read-only identity limited to the published MART query surface.
- Set AWS budget alerts, an appropriate Snowflake warehouse with auto-suspend, and a written cost owner/check schedule.
- Document access revocation, object retention/versioning options, connection troubleshooting and a safe environment recreation procedure.
- Collect access/load errors and service-availability evidence sufficient for the pipeline owner to distinguish transient failures from permission errors.

**Required artifacts:**

- `infra/access-matrix.md`, cost-control instructions and repeatable DEV setup steps.
- Read-only dashboard identity and one documented negative-permission test.

**Acceptance criteria:**

- A dashboard credential cannot write RAW, STAGING or MART and can read only approved published objects.
- Another member can reproduce the environment using documentation without sharing personal admin credentials.

### Advanced Delivery

**Experience fit:** Can deliver reproducible cloud infrastructure and operational recovery controls.

**Project tasks:**

- Express agreed infrastructure in Terraform or an equivalent reviewed IaC approach; avoid unapproved destructive changes.
- Configure targeted monitoring/alerts for failed loads, unauthorised access and material cloud cost changes.
- Exercise credential rotation, source-object recovery and access restoration; explain limitations of S3 versioning and warehouse recovery separately.

**Required artifacts:**

- Reviewed IaC plus a monitoring and recovery runbook.
- Recorded failure/restore exercise and cost/security risk assessment.

**Acceptance criteria:**

- An authorised member can recreate the non-secret configuration and verify the S3-to-Snowflake path.
- Relevant alerts and recovery procedures have been exercised with evidence, not merely listed as future work.

## 3. Inputs and handoffs

**Inputs required from others:**

- Proposed data flow, estimated dataset size, cloud budget and team access requirements.
- Required source file format and Snowflake RAW load plan from Data Engineer.

**Outputs and recipients:**

- Bucket/prefix, storage integration, external stage and scoped access instructions → Data Engineer.
- Read-only published-MART access configuration → Streamlit owner; resource/cost status → Team Lead.

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
