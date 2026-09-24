# Snowflake CI/CD MVP Design

## Objective

Deliver the current datathon MVP to `DATATHON_DEV` through one GitHub Actions workflow. Pull requests run non-mutating CI checks. A push to `main` runs the same checks and, only after they pass, deploys the Snowflake SQL model and Streamlit application through Snowflake CLI using the already verified GitHub OIDC identity.

Python and DuckDB validation remain in the repository but are outside this delivery slice and do not block Snowflake deployment.

## Environments and authentication

- GitHub repository: `HackaThon-jok/datathon`.
- Target environment: `DATATHON_DEV` only.
- Deployment user: `DATATHON_GITHUB_CI`.
- Deployment role: `DATATHON_CICD_ROLE`.
- Query warehouse: `DATATHON_WH`.
- Authentication: GitHub OIDC workload identity; GitHub stores only `SNOWFLAKE_ACCOUNT`.
- No password, private key, `ACCOUNTADMIN`, or AWS credentials are stored in GitHub.

Production promotion and a separate production service user are intentionally excluded from this MVP.

## Repository layout

- `.github/workflows/snowflake.yml`: combined CI and CD workflow.
- `sql/datathon_migration.sql`: repeatable deployment of derived `STAGING`, `MART`, and `VALIDATION` objects. It reads but never modifies `RAW.SALES_RAW`.
- `sql/smoke_test.sql`: post-deployment assertions that fail the workflow when required source or derived data is missing or reconciliation fails.
- `dashboard/snowflake.yml`: Snowflake CLI definition for the Streamlit object in `DATATHON_DEV.APP`.
- `dashboard/environment.yml`: warehouse-runtime Python dependencies.
- `dashboard/streamlit_app.py`: application entry point.

The one-time creation of roles, users, database, warehouse, and ownership grants stays outside the automated deployment because those operations require administrative authority.

## Workflow behavior

The workflow runs on pull requests that change Snowflake SQL, dashboard files, or the workflow itself; it also runs on pushes to `main` for the same paths and supports manual execution.

### CI job

CI has read-only repository permissions and does not request an OIDC token. It:

1. checks out the repository;
2. rejects conflict markers and administrative/destructive statements in deployable SQL;
3. parses the Snowflake SQL with SQLFluff's Snowflake dialect;
4. compiles the Streamlit Python source;
5. validates the committed Streamlit project definition against the Snowflake CLI project schema.

CI failure prevents CD.

### CD job

CD runs only for `main` pushes or an explicit manual run. It depends on successful CI and receives `contents: read` plus `id-token: write` permissions. It:

1. checks out the exact tested commit;
2. installs Snowflake CLI using Snowflake's maintained GitHub Action;
3. authenticates with OIDC and tests the connection;
4. executes `sql/datathon_migration.sql` using the service user's default role and warehouse;
5. executes `sql/smoke_test.sql` and stops on failure;
6. deploys `dashboard/streamlit_app.py` with `snow streamlit deploy --replace --prune`;
7. performs a final query confirming the Streamlit object exists.

The Streamlit application is deployed only after the SQL model passes smoke tests, so a failed data deployment cannot replace the currently deployed dashboard code.

## SQL deployment rules

- Deployable SQL must not contain `USE ROLE ACCOUNTADMIN`, `DROP DATABASE`, or `DROP SCHEMA`.
- The migration is rerunnable against the same RAW snapshot.
- `RAW.SALES_RAW` and `RAW.DATATHON_S3_STAGE` are never recreated, truncated, or dropped.
- Derived objects may use `CREATE OR REPLACE` because `DATATHON_CICD_ROLE` owns the `STAGING`, `MART`, and `VALIDATION` schemas and their current tables.
- Every object reference is fully qualified with `DATATHON_DEV` to prevent deployment into an accidental database.

## Streamlit deployment

The app explicitly uses Snowflake warehouse runtime because it already obtains its session through `get_active_session()`. The CLI project creates or replaces `DATATHON_DEV.APP.DATATHON_MIGRATION_DASHBOARD`, stores source files in an internal stage managed within `APP`, and uses `DATATHON_WH` for queries.

Only `streamlit`, `pandas`, and `snowflake-snowpark-python` are declared as application dependencies. Application source contains no credentials.

## Validation and failure behavior

The smoke test checks that:

- `RAW.SALES_RAW` is non-empty;
- required derived tables exist and are non-empty;
- `VALIDATION.MIGRATION_REPORT` contains a successful result according to the columns produced by the existing migration;
- the Streamlit object exists after deployment.

Any command returning a non-zero status fails the GitHub job. There is no automatic rollback of recreated tables in this MVP; the dashboard deploy is ordered last to avoid publishing app code against a failed model. Versioned data publishing and rollback are Phase 3 work.

## Acceptance criteria

1. A pull request changing SQL or dashboard code runs CI without connecting to or modifying Snowflake.
2. A failing CI check prevents deployment.
3. A successful push to `main` authenticates without passwords or private keys.
4. The workflow deploys derived Snowflake objects and passes smoke tests.
5. The workflow deploys `DATATHON_DEV.APP.DATATHON_MIGRATION_DASHBOARD`.
6. A rerun of the same commit completes successfully.
7. GitHub logs contain no Snowflake password, private key, AWS key, or source-row data.
