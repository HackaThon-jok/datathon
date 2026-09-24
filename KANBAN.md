# Minimum Runnable Kanban

[English](KANBAN.md) · [简体中文](KANBAN_CN.md) · [Project overview](README.md)

> **Goal:** expose the existing Python/FastAPI service from Amazon ECS Fargate, using an immutable image in Amazon ECR, while preserving DuckDB as the local pre-online test engine.
>
> **Update rule:** move a card to **Done** only when the listed evidence exists. Keep only one or two cards in **In Progress**.

## Definition of Done

A task is Done when its implementation, verification command/output and relevant documentation are available to the team. Creating a resource or file without testing it is not Done.

## Done

| ID | Phase | Minimum task | Owner | Evidence |
|---|---|---|---|---|
| AWS-001 | 1 | Create the non-root `datathon-architect` user and enable MFA | Cloud Engineer | Console access shows MFA enabled |
| AWS-002 | 1 | Authenticate the local AWS CLI as `datathon-architect` | Cloud Engineer | `sts get-caller-identity` returns account `045740834598` and the expected user ARN |
| AWS-003 | 1 | Verify the default VPC, public subnets and active internet gateway route in `us-east-1` | Cloud Engineer | VPC, six public subnets and active `0.0.0.0/0` route recorded |
| AWS-004 | 1 | Create immutable encrypted ECR repository `datathon-api` | Cloud Engineer | Repository URI, `IMMUTABLE` and `AES256` recorded |
| DEV-001 | 1 | Verify the local Docker daemon and ECR login | API Owner | Docker reports Linux/x86_64 and ECR login succeeds |
| APP-001 | 1 | Run the local FastAPI service with DuckDB | API Owner | `/health`, `/data-profile` and `/sample` return successfully |
| DOC-001 | 1 | Align all README files to Python/DuckDB locally and ECR/ECS Fargate online | Solution Architect | English and Chinese README pairs use the same three phases |

## In Progress

| ID | Phase | Minimum task | Owner | Acceptance evidence |
|---|---|---|---|---|
| APP-002 | 2 | Complete `Dockerfile` and `.dockerignore` for the FastAPI service | API Owner | Both files are non-empty; image build succeeds |
| TEAM-001 | 1 | Align owners, MVP boundary and acceptance criteria with the team | Solution Architect | Named owner beside every Ready card; meeting decision recorded |

## Ready — First Online Runnable Version

Complete these cards from top to bottom.

| Order | ID | Phase | Minimum task | Owner | Acceptance evidence |
|---:|---|---|---|---|---|
| 1 | REPO-001 | 1 | Remove/ignore `.DS_Store`, the empty `history_database` file and the duplicate `.Dockerignore` filename | API Owner | `git status --short` contains no accidental local artifacts |
| 2 | APP-003 | 2 | Build the Linux/amd64 image with a unique version tag | API Owner | `docker build` completes and the image tag is recorded |
| 3 | APP-004 | 2 | Run the container locally on port 8080 | API Owner | Container `/health`, `/data-profile` and `/sample` checks pass |
| 4 | AWS-005 | 2 | Push the immutable versioned image to `datathon-api` in ECR | Cloud Engineer | ECR `describe-images` returns the expected tag and digest |
| 5 | IAM-001 | 2 | Create scoped ECS task execution and infrastructure roles | Cloud Engineer | Trust policies and required permissions are reviewed; no user access key is used |
| 6 | AWS-006 | 2 | Create the ECS Express Mode/Fargate service in `us-east-1` | Cloud Engineer | Service is stable and runs the expected image digest |
| 7 | TEST-001 | 2 | Test the public AWS health and data-profile endpoints | API Owner | Public `/health` returns 200 and `/data-profile` returns the expected controlled dataset count |
| 8 | DOC-002 | 2 | Record the deployment URL, image tag/digest, commands, cost assumptions and teardown steps | Solution Architect | Another team member can reproduce or remove the MVP from the documentation |

## Ready — Complete AWS Data MVP

These tasks follow the first successful online endpoint; they must not block it.

| Order | ID | Phase | Minimum task | Owner | Acceptance evidence |
|---:|---|---|---|---|---|
| 1 | DATA-001 | 1 | Confirm the monthly-sales-by-region definition and independent baseline | Data Analyst | Approved KPI definition and baseline file |
| 2 | DATA-002 | 1 | Make one local command create RAW/STAGING/MART outputs and validation evidence | Data Engineer | Repeatable command and non-duplicating rerun result |
| 3 | AWS-007 | 2 | Store immutable source/manifest and Parquet outputs in private encrypted S3 prefixes | Data Engineer | S3 keys, checksum, row counts and encryption evidence |
| 4 | IAM-002 | 2 | Grant the ECS task role only the required S3/Athena/Glue access | Cloud Engineer | Positive and negative permission tests |
| 5 | DATA-003 | 2 | Register candidate tables in Glue and query them through a bounded Athena workgroup | Data Engineer | Successful query and controlled result location/scan limit |
| 6 | VAL-001 | 2 | Reconcile DuckDB and Athena schema, row count and KPI | Data Scientist | PASS, PASS WITH ACCEPTED EXCEPTIONS, or FAIL report |
| 7 | RELEASE-001 | 2 | Publish only the validated view/version | Solution Architect | Failed candidate cannot replace the last validated result |
| 8 | UI-001 | 2 | Decide whether Streamlit is required for the datathon demo | Data Analyst | Explicit include/defer decision; if included, UI reads only validated data |
| 9 | DOC-003 | 2 | Update the architecture diagram to match the verified ECS and AWS data flow | Solution Architect | Diagram and README describe the same deployed components |

## Blocked / Decisions Needed

| ID | Decision | Owner | Unblock condition |
|---|---|---|---|
| DEC-001 | Is Streamlit required for the MVP demo, or is FastAPI plus `/docs` sufficient? | Team | Team records one choice before UI work begins |
| DEC-002 | Who owns API, AWS deployment, data pipeline, validation and release approval? | Solution Architect | One named person per responsibility |
| DEC-003 | What budget alert threshold and teardown date apply to the AWS MVP? | Account owner | Amount, notification recipient and teardown date recorded |

## Phase 3 Parking Lot — Not Required for Minimum Runnable

- Infrastructure as code and separate environments.
- CI/CD, image vulnerability gates and automated rollback.
- EventBridge/Step Functions scheduling and replay.
- CloudWatch dashboards, alarms and operational runbooks.
- Secrets rotation, incident exercises and recovery testing.

