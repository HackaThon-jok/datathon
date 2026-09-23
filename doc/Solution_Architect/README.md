# Solution Architect / Team Lead — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Own scope, architecture, named ownership, integration and the evidence-based release decision for the end-to-end migration.

**Boundary:** Coordinate rather than automatically implement every module. Data Analyst owns business definitions; Data Scientist owns independent checks; a named Python-capable person must own Streamlit implementation. No mandatory Java or separate REST API.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can explain a simple data flow, coordinate dependent tasks and distinguish proposed features from delivered evidence.

**Project tasks:**

- Confirm one source dataset, available legacy SQL/report logic and one monthly-sales-by-region KPI; record unknowns rather than inventing columns.
- Draw the Python → S3 → Snowflake RAW/STAGING/candidate MART → validation gate → published MART → Streamlit flow and document AI review and independent baseline as side paths.
- Assign named owners for AWS, ingestion, modelling, KPI rules, independent validation, Streamlit coding and release approval.
- Define the first MART query fields and filters, a minimum acceptance checklist and one end-to-end demo route.

**Required artifacts:**

- `docs/architecture.md` — diagram, MVP boundary, assumptions and why Python/SQL was selected.
- `docs/ownership.md` and `docs/acceptance.md` — accountable people, handoffs, checks and evidence links.

**Acceptance criteria:**

- Every mandatory task and the Streamlit implementation have an owner; no Java/API delivery is accidentally retained as mandatory.
- A reviewer can trace the selected source KPI through ingestion, SQL, validation and the published dashboard result.

### Standard Delivery

**Experience fit:** Can define inter-component contracts and design safe failure handling across the migration stages.

**Project tasks:**

- Specify source identity, batch/run IDs, schema, business grain, expected outputs and the handoff format for each stage.
- Design the run-state model, bounded retries, idempotent reruns, candidate/published separation and a manual or automated release approval path.
- Define least-privilege access, secret handling, cost ownership and read-only Streamlit access to published data.
- Lead one integration test covering successful publication and one failed KPI check that must not change published data.

**Required artifacts:**

- `docs/data-contracts.md` and `docs/integration-test-plan.md` with precise field/filter and failure semantics.
- Run-state/release design, risk register and recorded integration test evidence.

**Acceptance criteria:**

- The team can implement against agreed contracts without guessing who owns quality checks or publishing.
- An intentionally failed candidate remains unpublished and the last successful result stays accessible or the UI states none exists.

### Advanced Delivery

**Experience fit:** Can reason about recoverability, operational trade-offs and reproducible migration governance.

**Project tasks:**

- Design versioned publication, atomic reader switching or an equivalent controlled pointer, and tested rollback of a faulty release.
- Run failure-injection exercises for source schema drift, duplicated batches, interrupted loads and conflicting KPI definitions; assign incident owners.
- Document a constrained AI conversion workflow with reviewed SQL, DEV-only execution and independent acceptance criteria.
- Prepare a reusable migration playbook with measured effort/cost assumptions and known limitations.

**Required artifacts:**

- `docs/migration-playbook.md`, release/rollback checklist and failure-drill evidence.
- Decision log documenting cost, security, AI approvals and residual risks.

**Acceptance criteria:**

- A released bad version can be rolled back without silently rewriting the independent baseline.
- Another team member can repeat the documented recovery and explain which steps remain manual.

## 3. Inputs and handoffs

**Inputs required from others:**

- Event brief, verified source files and available original reporting logic.
- Team availability/skills, cloud access and the independent baseline proposed by the analyst.

**Outputs and recipients:**

- Agreed diagram, responsibilities and secure access boundaries → all contributors.
- Data contracts, release rules and demo acceptance criteria → ingestion, SQL, validation and Streamlit owners.

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
