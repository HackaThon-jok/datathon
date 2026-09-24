# Snowflake CI/CD MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one GitHub Actions workflow that validates Snowflake SQL and Streamlit changes on pull requests and deploys both to `DATATHON_DEV` after successful validation on `main`.

**Architecture:** A standard-library Python policy checker and external parsers form a non-mutating CI job. A dependent CD job obtains a short-lived GitHub OIDC token, runs the repeatable derived-table migration, runs Snowflake Scripting assertions, and deploys the warehouse-runtime Streamlit app last.

**Tech Stack:** GitHub Actions, Snowflake CLI 3.23.0, GitHub OIDC, Snowflake SQL/Scripting, SQLFluff Snowflake dialect, Python 3.12, Streamlit in Snowflake warehouse runtime.

**Spec:** `docs/superpowers/specs/2026-09-25-snowflake-cicd-design.md`

## Global Constraints

- Deploy only to `DATATHON_DEV`; do not create a production environment.
- Authenticate only with `DATATHON_GITHUB_CI` through GitHub OIDC and the `SNOWFLAKE_ACCOUNT` repository secret.
- Never put a password, private key, `ACCOUNTADMIN`, AWS credential, or source-row value in GitHub configuration or logs.
- Never modify or replace `DATATHON_DEV.RAW.SALES_RAW` or `DATATHON_DEV.RAW.DATATHON_S3_STAGE`.
- Pull-request CI must not connect to or modify Snowflake.
- Streamlit must use warehouse runtime explicitly and retain `get_active_session()`.
- The existing Python/DuckDB pipeline is outside this plan.

## Review Focus

- A conflict marker in any deployable SQL or dashboard file must fail CI before Snowflake authentication.
- Administrative/destructive SQL with mixed case or extra whitespace must be rejected.
- A missing or empty RAW table must make the Snowflake smoke test fail with a non-zero command status.
- A false or NULL reconciliation flag must make the Snowflake smoke test fail.
- A manual workflow run from a non-`main` branch must run CI but must not deploy.

---

### Task 1: Add the repository deployment-policy checker

**Files:**
- Create: `scripts/check_snowflake_deploy.py`
- Create: `tests/test_snowflake_deploy.py`

**Interfaces:**
- Consumes: repository-relative paths supplied as positional CLI arguments.
- Produces: exit code `0` when every file is safe; exit code `1` plus `path: message` diagnostics when a conflict marker or prohibited SQL statement is found.

- [ ] **Step 1: Write failing standard-library unit tests**


```python
def test_rejects_mixed_case_accountadmin(tmp_path):
    sql = tmp_path / "deploy.sql"
    sql.write_text("Use   Role accountadmin;\n", encoding="utf-8")
    assert check_files([sql]) == [f"{sql}: prohibited SQL: USE ROLE ACCOUNTADMIN"]

def test_rejects_conflict_marker_in_dashboard(tmp_path):
    app = tmp_path / "streamlit_app.py"
    app.write_text("<<<<<<< HEAD\n", encoding="utf-8")
    assert check_files([app]) == [f"{app}: unresolved merge conflict marker: <<<<<<<"]
```

- [ ] **Step 2: Run the tests and verify the expected import failure**

Run: `python -m unittest tests/test_snowflake_deploy.py -v`

Expected: FAIL because `scripts.check_snowflake_deploy` does not exist.

- [ ] **Step 3: Implement the minimal checker**

Use `pathlib`, `re`, and `sys` only. Remove `--` line comments before applying case-insensitive regular expressions so explanatory comments can name prohibited statements without failing. Do not remove executable text or block comments.

```python
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
PROHIBITED_SQL = {
    "USE ROLE ACCOUNTADMIN": re.compile(r"\bUSE\s+ROLE\s+ACCOUNTADMIN\b", re.I),
    "DROP DATABASE": re.compile(r"\bDROP\s+DATABASE\b", re.I),
    "DROP SCHEMA": re.compile(r"\bDROP\s+SCHEMA\b", re.I),
}
```

- [ ] **Step 4: Run checker tests**

Run: `python -m unittest tests/test_snowflake_deploy.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Run the checker against current deployment files**

Run: `python scripts/check_snowflake_deploy.py sql/datathon_migration.sql dashboard/streamlit_app.py`

Expected: FAIL and identify the current executable `USE ROLE ACCOUNTADMIN` statement. This is the regression proof for Task 2.

- [ ] **Step 6: Commit the checker**

```bash
git add scripts/check_snowflake_deploy.py tests/test_snowflake_deploy.py
git commit -m "test: enforce Snowflake deployment policy"
```

### Task 2: Make SQL deployable and add Snowflake smoke assertions

**Files:**
- Modify: `sql/datathon_migration.sql:46`
- Create: `sql/smoke_test.sql`
- Modify: `tests/test_snowflake_deploy.py`

**Interfaces:**
- Consumes: preloaded `DATATHON_DEV.RAW.SALES_RAW` and service-user defaults `DATATHON_CICD_ROLE`/`DATATHON_WH`.
- Produces: rerunnable derived tables plus a Snowflake CLI failure when required counts or reconciliation checks are invalid.

- [ ] **Step 1: Extend policy tests for the concrete SQL files**

Add a test that resolves the repository root and asserts `check_files()` returns no violations for `sql/datathon_migration.sql` and `sql/smoke_test.sql`.

```python
def test_committed_snowflake_sql_passes_policy():
    root = Path(__file__).resolve().parents[1]
    assert check_files([
        root / "sql/datathon_migration.sql",
        root / "sql/smoke_test.sql",
    ]) == []
```

- [ ] **Step 2: Run the concrete-file test and verify failure**

Run: `python -m unittest tests.test_snowflake_deploy.SnowflakeDeployPolicyTests.test_committed_snowflake_sql_passes_policy -v`

Expected: FAIL because the migration still selects `ACCOUNTADMIN` and the smoke-test file is absent.

- [ ] **Step 3: Remove administrative role selection from migration SQL**

Delete `USE ROLE ACCOUNTADMIN;`. Retain `USE WAREHOUSE DATATHON_WH`, `USE DATABASE DATATHON_DEV`, and `USE SCHEMA RAW`. Do not change RAW objects or current transformation behavior in this task.

- [ ] **Step 4: Add executable smoke-test assertions**

Create a Snowflake Scripting block with declared exceptions and `SELECT ... INTO` checks:

```sql
EXECUTE IMMEDIATE $$
DECLARE
    EMPTY_RAW EXCEPTION (-20001, 'RAW.SALES_RAW is empty.');
    EMPTY_STAGING EXCEPTION (-20002, 'STAGING.SALES_CLASSIFIED is empty.');
    EMPTY_MART EXCEPTION (-20003, 'MART.PRODUCT_SALES is empty.');
    BAD_RECONCILIATION EXCEPTION (-20004, 'Migration reconciliation failed.');
    RAW_ROWS NUMBER;
    STAGING_ROWS NUMBER;
    MART_ROWS NUMBER;
    FAILED_CHECKS NUMBER;
BEGIN
    SELECT COUNT(*) INTO :RAW_ROWS FROM DATATHON_DEV.RAW.SALES_RAW;
    IF (RAW_ROWS = 0) THEN RAISE EMPTY_RAW; END IF;

    SELECT COUNT(*) INTO :STAGING_ROWS FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED;
    IF (STAGING_ROWS = 0) THEN RAISE EMPTY_STAGING; END IF;

    SELECT COUNT(*) INTO :MART_ROWS FROM DATATHON_DEV.MART.PRODUCT_SALES;
    IF (MART_ROWS = 0) THEN RAISE EMPTY_MART; END IF;

    SELECT COUNT_IF(
        NOT COALESCE(RAW_TO_STAGING_ROW_COUNT_MATCH, FALSE)
        OR NOT COALESCE(ALL_ROWS_CLASSIFIED, FALSE)
        OR NOT COALESCE(VALID_SALES_RECONCILED, FALSE)
    ) INTO :FAILED_CHECKS
    FROM DATATHON_DEV.VALIDATION.MIGRATION_REPORT;

    IF (FAILED_CHECKS > 0) THEN RAISE BAD_RECONCILIATION; END IF;
    RETURN 'Snowflake migration smoke tests passed.';
END;
$$;
```

- [ ] **Step 5: Run policy and Python syntax tests**

Run: `python -m unittest tests/test_snowflake_deploy.py -v`

Expected: PASS.

Run: `python scripts/check_snowflake_deploy.py sql/datathon_migration.sql sql/smoke_test.sql dashboard/streamlit_app.py`

Expected: exit code `0`.

- [ ] **Step 6: Commit deployable SQL**

```bash
git add sql/datathon_migration.sql sql/smoke_test.sql tests/test_snowflake_deploy.py
git commit -m "feat: add guarded Snowflake SQL deployment"
```

### Task 3: Define the Streamlit in Snowflake project

**Files:**
- Create: `dashboard/snowflake.yml`
- Create: `dashboard/environment.yml`
- Create: `tests/test_streamlit_project.py`

**Interfaces:**
- Consumes: Snowflake CLI project schema version 2 and the existing `dashboard/streamlit_app.py`.
- Produces: warehouse-runtime object `DATATHON_DEV.APP.DATATHON_MIGRATION_DASHBOARD` using internal stage `DATATHON_DEV.APP.DATATHON_STREAMLIT_STAGE` and `DATATHON_WH`.

- [ ] **Step 1: Write failing file-contract tests**

Use `unittest` and text/JSON-safe assertions without importing the Streamlit application (which requires an active Snowflake session). Verify that the project file names the database, schema, identifier, stage, warehouse, explicit warehouse runtime, entry point, and both artifacts. Verify that `environment.yml` pins Python 3.11, Streamlit 1.52.2, pandas 2.*, and includes `snowflake-snowpark-python`.

- [ ] **Step 2: Run tests and verify missing-file failures**

Run: `python -m unittest tests/test_streamlit_project.py -v`

Expected: FAIL because both configuration files are absent.

- [ ] **Step 3: Add `dashboard/snowflake.yml`**

```yaml
definition_version: 2
entities:
  datathon_dashboard:
    type: streamlit
    identifier:
      name: DATATHON_MIGRATION_DASHBOARD
      database: DATATHON_DEV
      schema: APP
    stage: DATATHON_DEV.APP.DATATHON_STREAMLIT_STAGE
    query_warehouse: DATATHON_WH
    runtime_name: SYSTEM$WAREHOUSE_RUNTIME
    main_file: streamlit_app.py
    artifacts:
      - streamlit_app.py
      - environment.yml
```

- [ ] **Step 4: Add `dashboard/environment.yml`**

```yaml
name: datathon-streamlit
channels:
  - snowflake
dependencies:
  - python=3.11
  - streamlit=1.52.2
  - pandas=2.*
  - snowflake-snowpark-python
```

- [ ] **Step 5: Run local configuration tests and compile app source**

Run: `python -m unittest tests/test_streamlit_project.py -v`

Expected: PASS.

Run: `python -m py_compile dashboard/streamlit_app.py`

Expected: exit code `0`.

- [ ] **Step 6: Commit Streamlit project configuration**

```bash
git add dashboard/snowflake.yml dashboard/environment.yml tests/test_streamlit_project.py
git commit -m "feat: define Snowflake Streamlit deployment"
```

### Task 4: Replace the connection probe with combined CI/CD

**Files:**
- Delete: `.github/workflows/snowflake-connection.yml`
- Create: `.github/workflows/snowflake.yml`
- Create: `tests/test_snowflake_workflow.py`

**Interfaces:**
- Consumes: repository files from Tasks 1-3 and GitHub secret `SNOWFLAKE_ACCOUNT`.
- Produces: `ci` job for pull requests/pushes/manual runs and dependent `deploy-dev` job for `main` pushes/manual runs from `main`.

- [ ] **Step 1: Write failing workflow-contract tests**

Using `unittest`, read the workflow as text and assert it contains:

- `pull_request`, `push`, and `workflow_dispatch` triggers;
- `actions/checkout@v7`;
- an explicit `ci` job without `id-token: write`;
- `deploy-dev` with `needs: ci` and an `if` expression limited to `refs/heads/main`;
- `snowflakedb/snowflake-actions@v3`, `use-oidc: true`, and `SNOWFLAKE_ACCOUNT`;
- ordered commands for migration, smoke test, Streamlit deployment, and `DESC STREAMLIT`.

- [ ] **Step 2: Run tests and verify missing-workflow failure**

Run: `python -m unittest tests/test_snowflake_workflow.py -v`

Expected: FAIL because `.github/workflows/snowflake.yml` does not exist.

- [ ] **Step 3: Create the combined workflow**

Define path filters for `.github/workflows/snowflake.yml`, `sql/**`, `dashboard/**`, `scripts/check_snowflake_deploy.py`, and the three CI/CD test files. Give the workflow top-level `contents: read`; grant `id-token: write` only inside `deploy-dev`.

The CI job installs Python 3.12, SQLFluff, `check-jsonschema`, and Snowflake CLI. It runs:

```bash
python -m unittest tests/test_snowflake_deploy.py tests/test_streamlit_project.py tests/test_snowflake_workflow.py -v
python scripts/check_snowflake_deploy.py sql/datathon_migration.sql sql/smoke_test.sql dashboard/streamlit_app.py
sqlfluff parse --dialect snowflake sql/datathon_migration.sql sql/smoke_test.sql
python -m py_compile dashboard/streamlit_app.py
snow helpers generate-project-schema --definition-version 2 --output-file /tmp/snowflake-project-schema.json --format JSON
check-jsonschema --schemafile /tmp/snowflake-project-schema.json dashboard/snowflake.yml
```

The CD job authenticates through OIDC, then runs in this order:

```bash
snow connection test -x
snow sql -f sql/datathon_migration.sql -x
snow sql -f sql/smoke_test.sql -x
snow streamlit deploy datathon_dashboard --project dashboard --replace --prune -x
snow sql -q "DESC STREAMLIT DATATHON_DEV.APP.DATATHON_MIGRATION_DASHBOARD;" -x
```

- [ ] **Step 4: Remove the superseded connection-only workflow**

Delete `.github/workflows/snowflake-connection.yml` so there is one authoritative Snowflake workflow.

- [ ] **Step 5: Run workflow contract and all focused tests**

Run: `python -m unittest tests/test_snowflake_deploy.py tests/test_streamlit_project.py tests/test_snowflake_workflow.py -v`

Expected: PASS.

- [ ] **Step 6: Commit combined CI/CD**

```bash
git add .github/workflows/snowflake.yml tests/test_snowflake_workflow.py
git add -u .github/workflows/snowflake-connection.yml
git commit -m "ci: deploy Snowflake model and dashboard"
```

### Task 5: Verify locally, push, and observe the real deployment

**Files:**
- Modify only files required by failures found in this task.

**Interfaces:**
- Consumes: complete CI/CD implementation and configured GitHub/Snowflake OIDC environment.
- Produces: passing local checks, a pushed `main` commit, and a successful GitHub `deploy-dev` job.

- [ ] **Step 1: Run the full focused local verification**

```bash
git diff --check
python -m unittest tests/test_snowflake_deploy.py tests/test_streamlit_project.py tests/test_snowflake_workflow.py -v
python scripts/check_snowflake_deploy.py sql/datathon_migration.sql sql/smoke_test.sql dashboard/streamlit_app.py
python -m py_compile dashboard/streamlit_app.py
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run external parsers when available locally**

```bash
sqlfluff parse --dialect snowflake sql/datathon_migration.sql sql/smoke_test.sql
snow helpers generate-project-schema --definition-version 2 --output-file /tmp/snowflake-project-schema.json --format JSON
check-jsonschema --schemafile /tmp/snowflake-project-schema.json dashboard/snowflake.yml
```

Expected: all commands exit `0`. If tools are unavailable locally, do not install them silently; record that GitHub CI is the first execution environment for these checks.

- [ ] **Step 3: Inspect the final diff and history**

Run: `git status --short && git diff --stat HEAD~4..HEAD && git log --oneline -6`

Expected: only planned Snowflake CI/CD files changed and no uncommitted files remain.

- [ ] **Step 4: Push `main`**

Run: `git push origin main`

Expected: GitHub accepts the commits and starts `Snowflake CI/CD`.

- [ ] **Step 5: Verify GitHub execution**

In GitHub Actions, confirm `ci` passes before `deploy-dev`, then inspect the deployment steps. Do not paste secrets; paste only an error step if one fails.

- [ ] **Step 6: Verify Snowflake objects**

Run in Snowsight:

```sql
USE ROLE DATATHON_CICD_ROLE;
SELECT * FROM DATATHON_DEV.VALIDATION.MIGRATION_REPORT;
DESC STREAMLIT DATATHON_DEV.APP.DATATHON_MIGRATION_DASHBOARD;
```

Expected: all three reconciliation flags are `TRUE` and the Streamlit object exists in `DATATHON_DEV.APP`.
