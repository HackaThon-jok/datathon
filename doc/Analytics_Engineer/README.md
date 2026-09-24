# Analytics Engineer

[English](README.md) · [简体中文](README_CN.md) · [Project overview](../../README.md) · [Architecture diagram](../aws-python-architecture.html)

> **Stack:** Python + DuckDB locally; containerized Python/FastAPI on Amazon ECS Fargate online, with Amazon S3, AWS Glue Data Catalog and Amazon Athena for the AWS data path.

## Ownership

Own reviewable transformations from RAW through STAGING to candidate MART, including the AI-assisted conversion record. Do not redefine business KPIs or approve your own output as the independent baseline.

## Phase 1 — Local Prototype

**Tasks**

- Preserve one real legacy SQL/report definition and use AI to draft an equivalent Python/SQL transformation.
- Human-review joins, NULLs, dates, currency, returns, grouping and destructive operations.
- Build DuckDB STAGING and candidate MART models using documented source-to-target mappings.
- Add local tests for grain, uniqueness, required fields, duplicate handling and the selected KPI.

**Evidence and exit criteria**

- Original logic, prompt/model, AI output, human edits, reviewer and test result are recorded.
- DuckDB candidate MART matches the independently supplied KPI baseline or documents every difference.

## Phase 2 — AWS MVP

**Tasks**

- Port the approved model to Athena using portable SQL plus small, documented dialect adapters where required.
- Materialise or expose isolated candidate data without changing the published view.
- Compare DuckDB and Athena schema, row count and month × region KPI using the same fixture/snapshot.
- Publish only through the controlled view/version switch after validation approval.

**Evidence and exit criteria**

- Versioned Athena SQL, mapping document and local/cloud contract-test results.
- Candidate failure cannot alter the published query result.

## Phase 3 — Production-ready

**Tasks**

- Add reusable model conventions, lineage, partition strategy and Athena scan-cost optimization.
- Test schema evolution, late-arriving data and model replay.
- Use AI-generated test ideas only as reviewed drafts; preserve deterministic expected outcomes.

**Evidence and exit criteria**

- Model documentation, lineage, performance/cost evidence and recovery tests are maintained.
- A model change can be reviewed, tested, deployed and rolled back without corrupting the published result.

## Inputs and handoffs

- Inputs: RAW/STAGING schema and lineage → Data Engineer; KPI definitions and baseline → Data Analyst.
- Outputs: candidate MART, SQL/Python artifacts, mapping and AI conversion record → Data Scientist and Architect.

## Shared acceptance rules

- DuckDB and Athena may use small syntax adapters, but their data contracts and business results must agree.
- AI output is always reviewed and tested.
- Candidate and published data remain separate.
- Phase 3 optimization follows correctness, not the reverse.
