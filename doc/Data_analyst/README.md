# Data Analyst — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Define the business meaning of the migrated report, independently calculate the legacy baseline, and specify or implement an understandable Streamlit dashboard.

**Boundary:** Own KPI semantics and business sign-off. Streamlit coding is assigned to a named person—this may be the analyst if they can code Python, but a wireframe alone is not a working UI. Independent technical reconciliation belongs to Data Scientist.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can inspect available source data, define a single reproducible KPI and specify a minimal user-facing report.

**Project tasks:**

- Inspect actual source columns and define sales amount, reporting month/timezone, region, currency, returns and missing-value rules without inventing unavailable attributes.
- Compute and save a source/legacy baseline independently of the Snowflake candidate MART.
- Specify one Streamlit KPI card, month/region filters, one chart, freshness label and a visible published-batch/validation status.
- Agree with the Team Lead who codes Streamlit and give them the required published MART fields and display semantics.

**Required artifacts:**

- `docs/data-dictionary.md` and `docs/legacy-baseline.md` with source reference, metric formula, assumptions and computed value.
- `docs/dashboard-spec.md` or an equivalent wireframe with a named Streamlit implementer and acceptance cases.

**Acceptance criteria:**

- A second person can reproduce the baseline from the cited source and defined date/currency/return rules.
- The named UI developer can build a basic dashboard without guessing field names, KPI meaning or permitted data status.

### Standard Delivery

**Experience fit:** Can translate business rules into reproducible analytics and implement or test a dependable Streamlit experience.

**Project tasks:**

- Expand KPI definitions to permitted dimensions, return categories, time boundaries and excluded records; maintain a versioned baseline.
- Work with the named Streamlit owner to implement filters, chart labels, empty/loading/error states, and clearly separated current published versus failed latest run.
- Compare old/new reports by month and region and write business acceptance tests for returns, missing region and no-sales periods.
- Ensure Streamlit uses a read-only published MART query; never surface candidate or failed batch totals as verified KPIs.

**Required artifacts:**

- Versioned KPI dictionary and side-by-side old/new report comparison.
- Tested Streamlit MVP (if assigned) or documented UI tests signed off against the named implementer’s work.

**Acceptance criteria:**

- Filters and display agree with the KPI baseline and published MART under the same business rules.
- The UI labels stale/failed/empty states honestly and does not silently substitute the newest unverified candidate.

### Advanced Delivery

**Experience fit:** Can design business-facing migration-readiness reporting and assess the impact of data discrepancies.

**Project tasks:**

- Design drill-down into supported dimensions, validation trends, last successful batch and unresolved exception counts.
- Define business materiality thresholds separately from hard technical data-integrity gates; document approvals for any changed KPI definition.
- Lead a stakeholder walkthrough of known reporting limitations, freshness SLAs and fallback to prior validated/legacy reporting.

**Required artifacts:**

- Migration-readiness dashboard or specification and stakeholder review evidence.
- Metric change log, discrepancy impact notes and freshness/acceptance policy.

**Acceptance criteria:**

- Users can distinguish passed, blocked and stale data without concealment of unresolved differences.
- Business rule changes require versioned sign-off rather than retroactively changing the independent baseline.

## 3. Inputs and handoffs

**Inputs required from others:**

- Actual source columns, old reports and business context.
- Published MART query surface and validation status → Analytics Engineer, Data Scientist and Architect.

**Outputs and recipients:**

- KPI dictionary and baseline → Analytics Engineer and Data Scientist.
- Streamlit specification, required columns/filters, business acceptance → named UI owner and Architect.

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
