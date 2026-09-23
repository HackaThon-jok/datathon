# Analytics Engineer — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Convert real legacy reporting logic with AI assistance and create transparent, tested Snowflake STAGING and candidate MART transformations.

**Boundary:** Own SQL semantics, transformations and conversion records; Data Analyst approves business definitions and Data Scientist independently tests target results. Do not execute unreviewed AI SQL against published data.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can read a source query/report definition, adapt SQL in DEV and explain the resulting KPI grain.

**Project tasks:**

- Inventory at least one real legacy query or original reporting transformation; if none exists, clearly label the limitation rather than fabricating legacy SQL.
- Use AI to draft an equivalent Snowflake query; manually review joins, NULLs, dates, currency, returns and grouping.
- Build one STAGING transformation and an isolated candidate MART computing the agreed monthly-sales-by-region KPI; preserve RAW.
- Record the original logic, AI prompt/output, human changes and test outcome before handing the result to Data Scientist.

**Required artifacts:**

- `sql/legacy/`, `sql/staging/`, `sql/mart/` and `docs/source-to-target.md`.
- `docs/ai-conversion-log.md` with a human-reviewed conversion example and candidate KPI query.

**Acceptance criteria:**

- The reviewed SQL executes in DEV/candidate data and the KPI respects documented source definitions.
- The conversion log distinguishes actual old SQL from reconstructed report logic and does not claim untested equivalence.

### Standard Delivery

**Experience fit:** Can independently maintain reusable analytical models and detect common SQL transformation errors.

**Project tasks:**

- Document source-to-target type, key and business-grain mappings and each rule for rejected/changed records.
- Add executable tests for unique grain, non-null critical fields, valid values, joins and aggregation invariants; use dbt only if helpful.
- Support group-level month × region reconciliation and resolve or explicitly record mismatches found by independent validation.
- Keep candidate transformations separate from published objects; promote only after required checks and documented approval.

**Required artifacts:**

- Tested, versioned staging/mart SQL, mapping dictionary and test result log.
- Expanded AI conversion/review log and grouped-KPI comparison support.

**Acceptance criteria:**

- Critical tests pass or produce explicit blocking failures; no silent filtering masks a mismatch.
- Data Scientist can independently reproduce monthly/regional candidate figures from the documented SQL and mappings.

### Advanced Delivery

**Experience fit:** Can design governed SQL promotion and assess a reproducible AI conversion workflow.

**Project tasks:**

- Detect upstream schema/grain changes, preserve source-to-MART lineage and document affected downstream metrics.
- Prototype an assistant that proposes SQL and draft tests but requires human approval and only runs accepted statements in DEV.
- Measure first-pass conversion correctness and review effort over a clearly enumerated set of real transformations with a stated denominator.
- Document SQL/model rollback and publication compatibility checks.

**Required artifacts:**

- Lineage and compatibility checks, controlled AI conversion prototype or reproducible workflow.
- Scoped AI evaluation and model release/rollback evidence.

**Acceptance criteria:**

- No AI-generated query is promoted merely because it executes; source KPI comparison and approval are required.
- Evaluation metrics, lineage and rollback steps can be reproduced from stored evidence.

## 3. Inputs and handoffs

**Inputs required from others:**

- RAW schema and batch/source metadata → Data Engineer.
- Original report/SQL, KPI formula and independent baseline → Data Analyst.

**Outputs and recipients:**

- Reviewed SQL, field mapping, STAGING and candidate MART → Data Scientist and Streamlit owner after release.
- Transformation tests, AI prompt/edit log and discrepancy explanations → Solution Architect.

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
