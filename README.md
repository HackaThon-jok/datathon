## Getting Started

**Analytics Engineer:** [Wentao Yan (@WentaoYan694)](https://github.com/WentaoYan694) — [contribution scope and PR #2](docs/CONTRIBUTIONS.md).

[Analytics acceptance status](docs/ANALYTICS_ACCEPTANCE.md)

> **Runnable analytics delivery:** [Local migration and Athena handoff](docs/ANALYTICS_HANDOFF.md), [source-to-target mapping](docs/SOURCE_TO_TARGET.md), and [AI conversion record](docs/AI_CONVERSION_LOG.md). The January single-store fixture is locally validated; region mapping and live Athena validation remain pending.

[English](README.md) · [简体中文](README_CN.md) · [Minimum Kanban](KANBAN.md) · [Interactive architecture diagram](doc/aws-python-architecture.html)

* Access to a Snowflake account with permission to create tables and Streamlit applications.
* A Snowflake virtual warehouse.
* The legacy sales CSV file containing seven source columns and two row identifiers.

### Step 1: Prepare the Snowflake Environment

Create the project database and the following schemas:

```sql
CREATE DATABASE IF NOT EXISTS DATATHON_DEV;

CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.RAW;
CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.STAGING;
CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.MART;
CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.VALIDATION;
```

Create the RAW table with seven VARCHAR source columns and two VARCHAR identifiers: `SOURCE_ROW_ID` and `INGEST_ROW_ID`.

### Step 2: Import Legacy Data

In Snowsight, upload `sales_dirty.csv` into `DATATHON_DEV.RAW.SALES_RAW`.

Skip the CSV header and verify that all nine columns are mapped correctly.

Confirm that the RAW table contains the expected source records before proceeding.

### Step 3: Run the Migration

Open a Snowflake SQL Worksheet and execute:

`sql/01_migration.sql`

The script creates the classified STAGING data, business-ready MART table, data quality reports and migration validation results.

### Step 4: Launch the Dashboard

Create a Streamlit in Snowflake application.

Copy the contents of `dashboard/streamlit_app.py` into the application editor and run the app using a role with access to the project database.

The dashboard displays migration statistics, data quality classifications, product sales, reconciliation checks and repair candidates.

### Step 5: Verify the Results

Execute the queries in `sql/02_demo_queries.sql` and compare the displayed results with the dashboard.

### Current Limitations

The current proof of concept uses a manually uploaded CSV. Automated S3-to-Snowflake ingestion is not part of the completed implementation.

Data repair candidates require human review and are not automatically applied to the source records.

The reported sales reconciliation validates accepted STAGING records against the MART results; full reconciliation with the original legacy Excel totals is a separate validation task.
