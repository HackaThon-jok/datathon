# Data Scientist — Responsibilities and Tiered Delivery Requirements

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md)

> **Project:** Datathon Use Case 4 — AI-Assisted Legacy System Migration  
> **Stack:** Python + SQL + Amazon S3 + Snowflake + Streamlit (no mandatory Java, Spring Boot or separate API).  
> **Status:** Requirements and acceptance criteria, not a claim of implementation.

## 1. Role ownership and boundaries

**Mission:** Independently assess input quality, reconcile source versus candidate results, and supply the evidence used by the validation gate.

**Boundary:** Own independent data checks and discrepancy analysis, not KPI redefinition or unrecorded fixes in ingestion. Machine learning is optional and never a prerequisite for migration correctness.

## 2. Skill levels and delivery policy

**Minimum** is mandatory MVP work and suits contributors completing scoped tasks with guidance; **Standard** includes Minimum and suits independent implementation/testing; **Advanced** includes both and suits contributors handling automation, recovery and complex design. Levels guide allocation, not personal ranking.

### Minimum Delivery

**Experience fit:** Can independently profile a dataset and compare source records and one documented KPI.

**Project tasks:**

- Profile missing values, duplicate candidate keys, unexpected types, invalid dates/amounts and source-file completeness; avoid marking valid returns as errors by default.
- Compare original source row count and loaded RAW count, documenting intentionally rejected rows and remaining gaps.
- Independently recompute one monthly-sales KPI using the analyst-approved source definition and compare with candidate MART.
- Record pass/fail and reasons; report unexplained critical mismatches to the Architect instead of labelling them successful.

**Required artifacts:**

- `docs/data-quality-report.md` with field-level issues, source references and counts.
- `docs/validation-report.md` with source/RAW counts, one KPI comparison and an explicit decision.

**Acceptance criteria:**

- A second person can reproduce the source count and selected KPI using documented formulas and sources.
- A critical count/KPI discrepancy blocks approval unless explained and signed off under explicit rules.

### Standard Delivery

**Experience fit:** Can automate independent, grouped reconciliation and design meaningful quality gates.

**Project tasks:**

- Write Python/SQL validation checks for required fields, uniqueness, date/amount validity and source-to-target totals, independent of AI conversion code.
- Compare month × region and available product categories; detect offsetting differences hidden by matching grand totals.
- Classify discrepancies as source-data defects, mapping/aggregation errors, load problems or business-rule differences; assign a resolution owner.
- Produce a machine-readable pass/fail result for the validation gate and test that a failed candidate remains unpublished.

**Required artifacts:**

- `src/validate.py` and/or `sql/tests/` with repeatable total and grouped reconciliation.
- Discrepancy register plus a recorded blocked-publication test.

**Acceptance criteria:**

- Independent checks catch a planted month/region misallocation even when the overall sales total is unchanged.
- Only checks that actually passed are marked passed; failures remain traceable to batch and source.

### Advanced Delivery

**Experience fit:** Can assess model/conversion quality across multiple runs and detect changing source-data behaviour.

**Project tasks:**

- Measure first-pass AI SQL equivalence on a fixed, enumerated set of conversions; state sample size, test dimensions and uncertainty.
- Design reference-data drift and schema/quality anomaly checks with appropriately scoped thresholds and false-alarm review.
- Run a fault/incorrect-query experiment demonstrating that an invalid batch is quarantined while the previous published KPI remains visible.
- Optionally demonstrate demand forecasting or near-expiry alerts only if real source features support a meaningful evaluation.

**Required artifacts:**

- Scoped AI evaluation and drift/failure test evidence.
- Documented exception review and optional ML experiment with stated limitations.

**Acceptance criteria:**

- Conversion accuracy claims identify exactly which cases and denominator were evaluated, with independent ground truth.
- Fault-injection evidence demonstrates a blocked invalid release without retroactively editing source KPI rules.

## 3. Inputs and handoffs

**Inputs required from others:**

- Original source snapshot, source counts, RAW batch records → Data Engineer.
- Agreed KPI baseline → Data Analyst; candidate MART SQL/results and AI log → Analytics Engineer.

**Outputs and recipients:**

- Pass/fail checks, discrepancy details and independent reconciliation → Architect and SQL/data owners.
- Approved validation status and clearly scoped caveats → Streamlit owner (via publication gate).

## 4. Shared project acceptance constraints

- Preserve lineage for source snapshots, run batches and transformations; do not silently drop invalid records.
- Publish a candidate MART only after independent KPI and critical quality checks pass; a failed run must not replace a prior validated version.
- Human-review AI-generated SQL and test only in DEV/candidate data; do not use the same AI output as the sole independent ground truth.
- Streamlit reads only published data; if none has passed validation, show "No validated data available."
- Do not mark proposed features, unexecuted tests or optional Advanced work as completed.
