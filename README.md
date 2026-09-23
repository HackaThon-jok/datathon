# Datathon Use Case 4 | AI-Assisted Legacy System Migration

[English](README.md) · [简体中文](README_CN.md) · [Interactive architecture diagram](doc/aws-python-architecture.html)

> **Status:** Target architecture and delivery plan; a listed item is not complete until its acceptance evidence exists.
>
> **Direction:** Python is the common development base, DuckDB supports local testing, and the online platform runs entirely on AWS.
>
> **Core stack:** Python + DuckDB (local) + Amazon S3 + AWS Glue Data Catalog + Amazon Athena + Streamlit on AWS App Runner.

## 1. Goal and scope

The goal is a verifiable migration of legacy health-supplies sales data and reporting, including an AI-assisted conversion example and independent reconciliation. The MVP produces monthly sales by region from one confirmed source dataset.

The same three delivery phases apply to the project and every role:

| Phase | Purpose | Exit condition |
|---|---|---|
| **Phase 1 — Local Prototype** | Build and test quickly with Python and DuckDB | A repeatable local run produces the agreed KPI and validation report |
| **Phase 2 — AWS MVP** | Publish the validated flow on S3, Glue and Athena; serve it through Streamlit | DuckDB and Athena outputs reconcile and the AWS dashboard reads only validated data |
| **Phase 3 — Production-ready** | Add automation, observability, recovery, security and IaC | Scheduled runs, failure recovery, monitoring and deployment controls are exercised |

Phase 1 and Phase 2 are required for the datathon MVP. Phase 3 is an extension, not a reason to delay a working end-to-end result.

## 2. Architecture

Open the [interactive architecture diagram](doc/aws-python-architecture.html) for theme switching, search, tracing and export. Its editable source is [doc/aws-python-architecture.json](doc/aws-python-architecture.json).

The main data path is:

    Legacy database / Excel
      → Python extraction, transformation, manifest and validation
      → DuckDB local tests
      → Amazon S3 RAW / STAGING / MART Parquet
      → AWS Glue Data Catalog
      → Amazon Athena candidate MART
      → Validation Gate comparing DuckDB and Athena
      → Published Athena view
      → Streamlit on AWS App Runner

Phase 3 adds EventBridge, Step Functions, CloudWatch, IAM, Secrets Manager and infrastructure as code around this path.

### Component boundaries

| Component | Responsibility | Boundary |
|---|---|---|
| Python package | Extraction, transformations, manifests, validation and orchestration entry points | Business logic must not live only inside Streamlit |
| DuckDB | Fast local SQL execution and pre-online contract tests | It is not the online production query service |
| Amazon S3 | Immutable source snapshots and versioned RAW/STAGING/MART Parquet data | Do not overwrite historical source evidence |
| AWS Glue Data Catalog | Table, schema and partition metadata | It does not transform or validate business results |
| Amazon Athena | Online candidate and published query surfaces | Candidate output is not published until validation passes |
| Streamlit on App Runner | Read-only dashboard and migration status | It reads only the published Athena surface |
| AWS operations services | Scheduling, workflow state, logs, secrets and infrastructure definition | Added in Phase 3 after the AWS MVP works |

## 3. Local-to-AWS development contract

The repository uses one Python package and explicit configuration profiles rather than separate local and cloud implementations:

- **local:** local fixtures or approved snapshots, DuckDB and local artifact paths.
- **aws-dev:** S3, Glue and Athena candidate tables, with credentials supplied by the AWS SDK credential chain.
- **aws-prod:** published resources and read-only dashboard access; introduced only with Phase 3 controls.

Transformations should use a portable SQL subset where practical. When DuckDB and Athena syntax must differ, keep small engine-specific SQL adapters and test them against the same input, schema, row-count and KPI contracts. Matching query text is not required; matching agreed results is.

No AWS access key, secret, connection string or personal/health data belongs in Git. Use environment configuration locally and IAM roles plus AWS Secrets Manager online.

## 4. Data zones, lineage and release

Recommended S3 layout:

    s3://<project-bucket>/raw/<dataset>/<batch_id>/source.<csv|parquet>
    s3://<project-bucket>/raw/<dataset>/<batch_id>/manifest.json
    s3://<project-bucket>/staging/<dataset>/batch_id=<batch_id>/*.parquet
    s3://<project-bucket>/mart/<dataset>/candidate/run_id=<run_id>/*.parquet
    s3://<project-bucket>/mart/<dataset>/published/version=<version>/*.parquet
    s3://<project-bucket>/athena-results/

Each run receives a unique run_id; each source snapshot has a batch_id, stable source identifier or SHA-256 hash, row count, extraction time and S3 key. Use these states consistently:

    PENDING → INGESTING → TRANSFORMING → VALIDATING → PUBLISHED
                   ↘ FAILED ←───────────────────↙

A retry creates a new run record and never erases the failed evidence. Publication changes a controlled view or version pointer only after critical checks and owner approval. A failed candidate cannot replace the last validated version.

## 5. AI-assisted conversion and validation

1. Preserve the original SQL or human-approved report definition, source schema and business rules.
2. Use AI to draft Python/SQL transformations and source-to-target mappings.
3. Human-review joins, NULLs, dates, currencies, returns, grouping, permissions and destructive operations.
4. Run the draft first against controlled local DuckDB data.
5. Run the approved AWS form against an isolated Athena candidate dataset.
6. Compare source counts, required fields, monthly/region KPI values and documented quality rules.
7. Record the prompt/model, generated output, human edits, test evidence and reviewer.

AI-generated migration logic cannot also be the only ground truth. The independent baseline must come from the legacy report or a separately computed, business-approved result.

## 6. Roles and phase ownership

Every linked role has a separate English and Chinese README using the same three phases.

| Role | Phase 1 — Local Prototype | Phase 2 — AWS MVP | Phase 3 — Production-ready |
|---|---|---|---|
| [Solution Architect](doc/Solution_Architect/README.md) | Scope, contracts and local architecture | AWS integration and release gate | Automated governance and recovery |
| [Cloud Engineer](doc/Cloud_Engineer/README.md) | AWS account, naming and access plan | S3, Glue, Athena, ECR/App Runner and IAM | IaC, monitoring, secrets and recovery |
| [Data Engineer](doc/Data_Engineer/README.md) | Python extraction, DuckDB load and manifest | S3 Parquet ingestion and catalog registration | Scheduled, idempotent and recoverable ingestion |
| [Analytics Engineer](doc/Analytics_Engineer/README.md) | Reviewed AI conversion and local MART | Athena candidate/published models and parity tests | Reusable models, lineage and optimization |
| [Data Analyst](doc/Data_analyst/README.md) | KPI definition, baseline and dashboard contract | Streamlit implementation and business sign-off | Operational and decision-support views |
| [Data Scientist](doc/Data_Scientist/README.md) | Local quality and reconciliation tests | Independent DuckDB/Athena validation | Drift, anomaly and validation monitoring |

### Handoffs

    Cloud Engineer → Data Engineer: S3 prefixes, Glue database, Athena workgroup and IAM role
    Data Engineer → Analytics Engineer: RAW/STAGING schema, batch/run metadata and counts
    Data Analyst → Analytics Engineer / Data Scientist: KPI definition and independent baseline
    Analytics Engineer → Data Scientist: candidate MART, conversion record and query artifacts
    Data Scientist → Solution Architect: validation report, exceptions and release recommendation
    Solution Architect → Streamlit owner: approved published view and display contract

## 7. MVP acceptance

- [ ] Confirm one usable source, the monthly-sales-by-region definition and a source/legacy baseline.
- [ ] A clean local Python command creates the DuckDB RAW/STAGING/MART result.
- [ ] Local tests cover schema, required fields, row counts and the agreed KPI.
- [ ] Preserve the source snapshot and manifest in S3; publish Parquet data with batch/run lineage.
- [ ] Register the AWS tables in Glue Data Catalog and query the candidate MART in Athena.
- [ ] Reconcile DuckDB and Athena by schema, row count and month × region KPI.
- [ ] Preserve one real AI conversion example, human review and test evidence.
- [ ] Publish only the validated Athena view; retain the last good version after failure.
- [ ] Streamlit runs on AWS, shows KPI/filter/freshness/validation state and uses read-only IAM access.
- [ ] Document local rerun, AWS rerun, limitations and an end-to-end demo.

## 8. Proposed repository structure

    datathon/
    ├── README.md / README_CN.md
    ├── doc/
    │   ├── aws-python-architecture.{html,json}
    │   └── <Role>/{README.md,README_CN.md}
    ├── data/fixtures/
    ├── src/{extract,transform,ingest,pipeline,validate}.py
    ├── sql/{common,duckdb,athena}/
    ├── tests/{unit,contract,integration}/
    ├── dashboard/app.py
    ├── docs/{data-dictionary,source-to-target,ai-conversion-log,validation-report}.md
    └── infra/

## 9. Cost and security guardrails

- Use least-privilege IAM roles, separate write and read-only paths, encrypted S3 buckets and blocked public access.
- Use Athena workgroup limits, compressed partitioned Parquet and lifecycle policies to control scan/storage cost.
- Configure AWS Budgets before creating online resources.
- Use synthetic or de-identified data unless explicit authority and privacy controls exist.
- Treat App Runner, Athena and pipeline logs as potentially sensitive; avoid logging raw records or secrets.

**Still to verify:** actual source schema, available legacy SQL/report definitions, AWS account/service limits, budget, team ownership and event deadline.
