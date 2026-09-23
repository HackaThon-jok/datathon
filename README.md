# Datathon Use Case 4: AI-Assisted System Migration, Role Plan

**Project:** Migrate a legacy local database of health-supplies sales data to a modern cloud platform (Snowflake on AWS)

**Team roles:** Solution Designer · Cloud Engineer · Data Engineer · Analytics Engineer · Data Analyst · Data Scientist

---

## Brief Summary

**Problem:** Many organisations still run legacy reporting and data systems that need to move to modern cloud platforms.

**Challenge:** Design an AI-assisted migration process that converts a simple legacy solution into a modern Snowflake-based architecture while maintaining governance and quality.

**Expected outcomes.** Teams should:

1. Analyse legacy assets
2. Design a target-state architecture
3. Demonstrate AI-assisted conversion or mapping
4. Implement validation and testing
5. Generate migration documentation

**Success looks like:** an organisation can migrate faster while staying confident in the accuracy and governance of the result.

> **Platform note:** The brief names **Snowflake** as the target. Our approach is **Snowflake on AWS**: data lands in Amazon S3 and is loaded into Snowflake through an external stage or Snowpipe. *(To confirm with the organisers: would a pure-AWS stack such as Redshift or Athena also be accepted?)*

---

## Phase 1: Basic (MVP, a working end-to-end flow)

| Role | r** | Define scope: migrate one legacy report (e.g. "monthly health-supplies sales by region"). Draw the current-state and target-state architecture (legacy DB → S3 → Snowflake → BI). Set naming conventions. | Architecture diagram v1, scope statement |
| **Cloud Engineer** | Set up the AWS account, S3 bucket and IAM roles. Create the Snowflake account, storage integration and external stage. Create basic roles (admin / dev / read-only). | Working cloud environment |
| **Data Engineer** | Export the legacy tables to CSV/Parquet and upload them to S3. Load them into the Snowflake RAW layer with `COPY INTO`. | Populated RAW layer |
| **Analytics Engineer** | Inventory the legacy assets: tables, views, stored procedures and report SQL. Use AI (e.g. Claude or Snowflake Cortex) to translate 1–2 pieces of legacy SQL into Snowflake SQL. | Legacy asset inventory, first converted SQL |
| **Data Analyst** | Clarify the business definitions: how sales are calculated, whether returns count, which date drives reporting. Choose 3–5 key KPIs as the validation baseline and record their values from the legacy system. | KPI definitions, legacy baseline figures |
| **Data Scientist** | Profile the data: missing values, outliers, duplicates, inconsistent date formats. Check health-supplies fields closely: batch/expiry, SKU, store. | Data quality report |

**Minimum validation:** row counts, total sales and each KPI must match between the legacy system and Snowflake.

---

## Phase 2: Standard (a proper process and a documented AI workflow)

| Role | Tasks | Deliverable |
|---|---|---|
| **Solution Designer** | Finalise the layers: RAW → STAGING → MART, with a star schema (`fact_sales`, `dim_product`, `dim_store`, `dim_date`). Document the **AI workflow**: AI generates → human reviews → tests pass. Define the governance approach. | Target architecture v2, AI workflow diagram |
| **Cloud Engineer** | Separate environments (DEV and PROD databases). Automate incremental ingestion with Snowpipe or scheduled tasks. Configure warehouse sizing and auto-suspend to control cost. | Automated ingestion |
| **Data Engineer** | Turn the manual loads into a repeatable pipeline (Snowflake Tasks/Streams or Airflow). Handle incremental loads and schema changes. | Re-runnable pipeline |
| **Analytics Engineer** | Build staging and mart models in **dbt**. **Convert the legacy SQL in bulk with AI**, recording for each piece the prompt, the AI output and the human edits. Add dbt tests: `not_null`, `unique`, `relationships`, `accepted_values`. | dbt project,ck it side by side against the old one: figures, filters and aggregations. | Legacy vs new report comparison |
| **Data Scientist** | Design **systematic reconciliation**: compare by dimension (region × month × category), not just totals. Measure AI conversion accuracy: the share of SQL that was correct on the first pass and the number of edits needed. | Reconciliation report, AI accuracy metrics |

**Documentation:** a data dictionary and a source-to-target mapping (legacy field → new field → transformation logic).

---

## Phase 3: Advanced (differentiators)

| Role | Tasks | Deliverable |
|---|---|---|
| **Solution Designer** | Write a reusable **migration playbook** that other organisations could follow. Add a risk and rollback plan. Estimate ROI: person-hours saved by AI acceleration. | Playbook, ROI slide |
| **Cloud Engineer** | Manage infrastructure as code (Terraform). Add monitoring and cost alerts. Set up CI/CD, e.g. GitHub Actions running the dbt tests automatically. | IaC, CI/CD pipeline |
| **Data Engineer** | Build an **AI migration agent**: it takes legacy SQL, converts it, runs it in DEV, compares the results with the legacy output, and flags mismatches for human review. | Semi-automated migration tool |
| **Analytics Engineer** | Use AI to generate dbt documentation and test cases. Show lineage (dbt docs or Snowflake lineage). | Auto-generated docs, lineage graph |
| **Data Analysality scores. | Executive dashboard |
| **Data Scientist** | Demo one use case on the migrated data, such as health-supplies demand forecasting or near-expiry stock alerts, using Snowpark or Cortex ML. Add data drift and anomaly detection. | ML use-case demo |

**Governance (bonus):** if the data contains customer or patient information, apply masking policies, row access policies and PII tags. Health-related data in New Zealand may fall under the **Privacy Act 2020** and the **Health Information Privacy Code**. *(Confirm with the organisers which of these apply.)*

---

## How the Phases Map to the Expected Outcomes

| Expected outcome | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| 1. Analyse legacy assets | Asset inventory, data profiling | — | — |
| 2. Target-state architecture | Architecture v1 | Layered architecture v2 + governance | IaC, playbook |
| 3. AI-assisted conversion | 1–2 SQL translations | Bulk conversion with log | AI migration agent |
| 4. Validation & testing | Row counts + KPI match | dbt tests + dimensional reconciliation | CI/CD, drift detection |
| 5. Migration documentation | Scope statement | Data dictionary, source-to-target mapping | Auto-generated docs, lineage, playbook |

---

## Prioritisation

- **Must have:** all of Phase 1.
- **Should have:** from Phase 2, the AI conversion log and the reconciliation/validation work. Together with Phase 1, these cover the core of what the brief asks for.
- **Nice to have:** one or two Phase 3 items, e.g. the AI migration agent or the migration dashboard.

> **Note:** The five expected outcomes ae-phase split, specific tools (dbt, Terraform, Snowpipe, etc.), the ML demo and the ROI slide are suggestions; adjust them to fit the time available and the team's skills.
