
-- ============================================================
-- DATATHON 2026
-- Use Case 4: AI-Assisted Legacy System Migration
--
-- Project:
-- Legacy Sales Report Migration to Snowflake
--
-- Architecture:
-- Legacy Excel / CSV
--        |
--        v
-- Snowflake RAW
--        |
--        v
-- Snowflake STAGING
--        |
--        +--------> VALIDATION
--        |
--        v
-- Snowflake MART
--
-- Purpose:
-- 1. Inspect the imported legacy sales data.
-- 2. Identify valid product records and data quality issues.
-- 3. Convert legacy report rows into structured business data.
-- 4. Generate product-level sales information.
-- 5. Validate the migration results.
--
-- IMPORTANT:
-- The source CSV must already be loaded into RAW.SALES_RAW.
--
-- This script rebuilds the derived STAGING, MART and
-- VALIDATION tables. It does not modify RAW.SALES_RAW.
--
-- Rebuilding derived tables is suitable for the current PoC.
-- A production migration should introduce batch tracking,
-- incremental processing and historical data retention.
-- ============================================================


-- ============================================================
-- STEP 0: SET SNOWFLAKE CONTEXT
-- ============================================================

USE ROLE ACCOUNTADMIN;

USE WAREHOUSE DATATHON_WH;

USE DATABASE DATATHON_DEV;

USE SCHEMA RAW;


-- ============================================================
-- STEP 1: INSPECT LEGACY RAW DATA
-- ============================================================

-- The original Excel report was converted into a CSV file.
--
-- RAW_COL_1 to RAW_COL_7 preserve the seven original
-- columns from the legacy report.
--
-- SOURCE_ROW_ID identifies the original source row.
-- INGEST_ROW_ID identifies the imported record.
--
-- All original data columns are stored as VARCHAR to prevent
-- invalid source values from causing import failures.


-- 1.1 Check the total number of imported records.

SELECT
    COUNT(*) AS TOTAL_ROWS

FROM DATATHON_DEV.RAW.SALES_RAW;


-- 1.2 Inspect representative source records.
--
-- The legacy report contains:
-- - Report headers
-- - Store-level summary rows
-- - Product-level sales records
-- - Potentially invalid or duplicated records
--
-- Records are ordered by INGEST_ROW_ID to approximate
-- their original CSV order.

SELECT
    RAW_COL_1,
    RAW_COL_2,
    RAW_COL_3,
    RAW_COL_4,
    RAW_COL_5,
    RAW_COL_6,
    RAW_COL_7,
    SOURCE_ROW_ID,
    INGEST_ROW_ID

FROM DATATHON_DEV.RAW.SALES_RAW

ORDER BY
    TRY_TO_NUMBER(INGEST_ROW_ID),
    INGEST_ROW_ID

LIMIT 30;


-- ============================================================
-- STEP 2: RAW DATA QUALITY ASSESSMENT
-- ============================================================

-- Create a dedicated schema for migration validation.
--
-- Validation results are stored separately from the
-- original data and business-ready tables.

CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.VALIDATION;


-- 2.1 Generate an initial data quality report.
--
-- This report checks:
-- - Total imported records
-- - Missing ingestion identifiers
-- - Repeated ingestion identifiers
-- - Missing source identifiers
-- - Repeated source identifiers
-- - Completely empty source records
--
-- Important:
-- A repeated SOURCE_ROW_ID may indicate an injected duplicate,
-- but it does not prove that two business records are identical.
--
-- Missing identifiers are reported separately from repeated
-- identifiers to avoid mixing two different quality issues.

CREATE OR REPLACE TABLE
DATATHON_DEV.VALIDATION.RAW_QUALITY_REPORT AS

SELECT

    COUNT(*) AS TOTAL_ROWS,

    -- Records without an ingestion identifier.

    COUNT_IF(
        INGEST_ROW_ID IS NULL
    ) AS MISSING_INGEST_IDS,

    -- Additional occurrences of non-null ingestion IDs.

    COUNT(INGEST_ROW_ID)
        - COUNT(DISTINCT INGEST_ROW_ID)
        AS DUPLICATE_INGEST_IDS,

    -- Records without an original source identifier.

    COUNT_IF(
        SOURCE_ROW_ID IS NULL
    ) AS MISSING_SOURCE_IDS,

    -- Additional occurrences of non-null source IDs.

    COUNT(SOURCE_ROW_ID)
        - COUNT(DISTINCT SOURCE_ROW_ID)
        AS REPEATED_SOURCE_IDS,

    -- Records where all seven original columns are NULL.

    COUNT_IF(

        RAW_COL_1 IS NULL
        AND RAW_COL_2 IS NULL
        AND RAW_COL_3 IS NULL
        AND RAW_COL_4 IS NULL
        AND RAW_COL_5 IS NULL
        AND RAW_COL_6 IS NULL
        AND RAW_COL_7 IS NULL

    ) AS EMPTY_SOURCE_RECORDS

FROM DATATHON_DEV.RAW.SALES_RAW;


-- 2.2 Review the initial quality report.

SELECT *
FROM DATATHON_DEV.VALIDATION.RAW_QUALITY_REPORT;


-- ============================================================
-- STEP 3: LEGACY FIELD MAPPING AND DATA CLASSIFICATION
-- ============================================================

-- Create the STAGING schema.
--
-- STAGING transforms the original report into a structured
-- representation while preserving the original source values.

CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.STAGING;


-- Legacy field mapping:
--
-- RAW_COL_1 -> Product description / report label
--
-- January 2026:
-- RAW_COL_2 -> Order count
-- RAW_COL_3 -> Product quantity
-- RAW_COL_4 -> Total price
--
-- Reported Total:
-- RAW_COL_5 -> Order count
-- RAW_COL_6 -> Product quantity
-- RAW_COL_7 -> Total price
--
-- The mapping is based on the observed report headers.
--
-- IMPORTANT BUSINESS ASSUMPTION:
-- The current PoC checks whether January values match
-- the reported Total values.
--
-- This rule is valid only if the original report covers
-- January alone, or the business owner confirms that
-- both sets of values should be identical.
--
-- Until that assumption is confirmed, a mismatch should
-- be treated as requiring review, not conclusive evidence
-- of an incorrect source record.


-- 3.1 Create the classified STAGING table.
--
-- This transformation:
-- - Preserves original source fields.
-- - Extracts SKU identifiers.
-- - Safely converts numeric values.
-- - Identifies repeated source identifiers.
-- - Classifies product and non-product records.
-- - Flags invalid values and period-total mismatches.
--
-- TRY_TO_NUMBER / TRY_TO_DECIMAL return NULL for
-- values that cannot be converted.
--
-- This allows the migration to identify invalid records
-- without failing the entire transformation.


CREATE OR REPLACE TABLE
DATATHON_DEV.STAGING.SALES_CLASSIFIED AS

WITH parsed AS (

    SELECT

        -- Preserve source traceability.

        SOURCE_ROW_ID,
        INGEST_ROW_ID,


        -- Preserve the original legacy report fields.

        RAW_COL_1 AS RAW_DESCRIPTION,

        RAW_COL_2,
        RAW_COL_3,
        RAW_COL_4,
        RAW_COL_5,
        RAW_COL_6,
        RAW_COL_7,


        -- Extract a product SKU from labels such as:
        -- [SKU1115] [Brand] Product description

        REGEXP_SUBSTR(
            RAW_COL_1,
            'SKU[0-9]+'
        ) AS SKU,


        -- Convert January 2026 report metrics.

        TRY_TO_NUMBER(
            RAW_COL_2, 18, 0
        ) AS JAN_ORDER_COUNT,

        TRY_TO_NUMBER(
            RAW_COL_3, 18, 0
        ) AS JAN_PRODUCT_QUANTITY,

        TRY_TO_DECIMAL(
            RAW_COL_4, 18, 2
        ) AS JAN_TOTAL_PRICE,


        -- Convert the reported Total metrics.

        TRY_TO_NUMBER(
            RAW_COL_5, 18, 0
        ) AS REPORTED_TOTAL_ORDER_COUNT,

        TRY_TO_NUMBER(
            RAW_COL_6, 18, 0
        ) AS REPORTED_TOTAL_QUANTITY,

        TRY_TO_DECIMAL(
            RAW_COL_7, 18, 2
        ) AS REPORTED_TOTAL_PRICE,


        -- Identify repeated source identifiers.
        --
        -- The first occurrence is retained as the candidate
        -- original record.
        --
        -- Later occurrences are flagged for review.
        --
        -- This is a PoC deduplication assumption and should
        -- not be treated as a universal business rule.

        ROW_NUMBER() OVER (

            PARTITION BY SOURCE_ROW_ID

            ORDER BY
                TRY_TO_NUMBER(INGEST_ROW_ID),
                INGEST_ROW_ID

        ) AS SOURCE_OCCURRENCE


    FROM DATATHON_DEV.RAW.SALES_RAW

),

classified AS (

    SELECT

        *,

        CASE

            -- Report headings, store summaries and other
            -- non-product rows are excluded from the
            -- product-level MART.

            WHEN LEFT(
                TRIM(COALESCE(RAW_DESCRIPTION, '')),
                4
            ) <> '[SKU'

                THEN 'NON_PRODUCT'


            -- Repeated source identifiers require review.
            --
            -- This classification does not establish that
            -- the full business records are identical.

            WHEN SOURCE_OCCURRENCE > 1

                THEN 'DUPLICATE_SOURCE_ID'


            -- Product-like rows without an extractable SKU
            -- cannot be mapped reliably.

            WHEN SKU IS NULL

                THEN 'INVALID_SKU'


            -- A failed numeric conversion produces NULL.
            --
            -- These rows are not silently repaired or
            -- included in the validated MART.

            WHEN JAN_ORDER_COUNT IS NULL
              OR JAN_PRODUCT_QUANTITY IS NULL
              OR JAN_TOTAL_PRICE IS NULL

              OR REPORTED_TOTAL_ORDER_COUNT IS NULL
              OR REPORTED_TOTAL_QUANTITY IS NULL
              OR REPORTED_TOTAL_PRICE IS NULL

                THEN 'INVALID_NUMERIC'


            -- Negative order counts, product quantities,
            -- and sales prices are flagged for review.

            WHEN JAN_ORDER_COUNT < 0
              OR JAN_PRODUCT_QUANTITY < 0
              OR JAN_TOTAL_PRICE < 0

              OR REPORTED_TOTAL_ORDER_COUNT < 0
              OR REPORTED_TOTAL_QUANTITY < 0
              OR REPORTED_TOTAL_PRICE < 0

                THEN 'NEGATIVE_VALUE'


            -- Flag disagreements between January and
            -- the reported Total.
            --
            -- This rule depends on the business assumption
            -- documented above.

            WHEN JAN_ORDER_COUNT
                    <> REPORTED_TOTAL_ORDER_COUNT

              OR JAN_PRODUCT_QUANTITY
                    <> REPORTED_TOTAL_QUANTITY

              OR JAN_TOTAL_PRICE
                    <> REPORTED_TOTAL_PRICE

                THEN 'PERIOD_TOTAL_MISMATCH'


            -- Records that pass the current PoC rules.

            ELSE 'VALID'

        END AS VALIDATION_STATUS

    FROM parsed

)

SELECT *
FROM classified;


-- ============================================================
-- STEP 4: REVIEW STAGING RESULTS
-- ============================================================

-- 4.1 Count records by validation status.
--
-- Each record is assigned exactly one primary status.
--
-- The order of CASE conditions determines which status
-- is assigned when a record has multiple issues.
--
-- Therefore, the status counts are not independent
-- counts of every possible data quality issue.

SELECT

    VALIDATION_STATUS,

    COUNT(*) AS ROW_COUNT

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

GROUP BY VALIDATION_STATUS

ORDER BY ROW_COUNT DESC;


-- 4.2 Inspect records with invalid numeric values.
--
-- This query helps identify cases where the January
-- value is invalid but the corresponding Total value
-- may still be readable.
--
-- A readable Total value is not automatically accepted
-- as a replacement for the invalid January value.

SELECT

    SOURCE_ROW_ID,
    INGEST_ROW_ID,

    SKU,
    RAW_DESCRIPTION,

    RAW_COL_3 AS ORIGINAL_JAN_QUANTITY,
    RAW_COL_6 AS ORIGINAL_TOTAL_QUANTITY,

    JAN_PRODUCT_QUANTITY,
    REPORTED_TOTAL_QUANTITY,

    VALIDATION_STATUS

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

WHERE VALIDATION_STATUS = 'INVALID_NUMERIC'

ORDER BY
    TRY_TO_NUMBER(INGEST_ROW_ID),
    INGEST_ROW_ID;


-- ============================================================
-- STEP 5: CREATE THE BUSINESS-READY MART
-- ============================================================

-- MART stores structured data that can be consumed
-- by analytical queries, dashboards and downstream APIs.
--
-- The current MVP produces one product-level sales table.
--
-- Only records with VALIDATION_STATUS = 'VALID'
-- are included.
--
-- Invalid, duplicate-source and non-product records
-- remain available in STAGING for further investigation.
--
-- IMPORTANT:
-- The resulting sales amount represents the accepted
-- product records, not necessarily the complete original
-- Excel report total.
--
-- SKU-level reported order counts must not be interpreted
-- as a deduplicated count of all store orders.


CREATE SCHEMA IF NOT EXISTS DATATHON_DEV.MART;


CREATE OR REPLACE TABLE
DATATHON_DEV.MART.PRODUCT_SALES AS

SELECT

    SKU,

    -- Preserve a representative product description.

    MAX(RAW_DESCRIPTION)
        AS PRODUCT_DESCRIPTION,


    -- Aggregate the accepted source metrics.

    SUM(JAN_ORDER_COUNT)
        AS REPORTED_ORDER_COUNT,

    SUM(JAN_PRODUCT_QUANTITY)
        AS PRODUCT_QUANTITY,

    ROUND(
        SUM(JAN_TOTAL_PRICE),
        2
    ) AS TOTAL_SALES_AMOUNT,


    -- Number of accepted source records contributing
    -- to each SKU-level result.

    COUNT(*)
        AS SOURCE_RECORD_COUNT

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

WHERE VALIDATION_STATUS = 'VALID'

GROUP BY SKU;


-- 5.1 Inspect the business-ready product sales data.

SELECT

    SKU,
    PRODUCT_DESCRIPTION,
    REPORTED_ORDER_COUNT,
    PRODUCT_QUANTITY,
    TOTAL_SALES_AMOUNT,
    SOURCE_RECORD_COUNT

FROM DATATHON_DEV.MART.PRODUCT_SALES

ORDER BY TOTAL_SALES_AMOUNT DESC

LIMIT 10;


-- ============================================================
-- STEP 6: MIGRATION VALIDATION AND RECONCILIATION
-- ============================================================

-- This report checks whether:
--
-- 1. All RAW records are represented in STAGING.
--
-- 2. Every STAGING record is assigned a validation status.
--
-- 3. The accepted STAGING sales amount matches the
--    corresponding aggregated MART sales amount.
--
-- IMPORTANT:
-- Matching STAGING and MART totals verifies internal
-- transformation consistency.
--
-- It does not prove that the complete legacy Excel
-- report has been reconciled.
--
-- A separate source-to-target reconciliation is needed
-- to account for excluded invalid records, non-product
-- rows and the original report's published totals.


CREATE OR REPLACE TABLE
DATATHON_DEV.VALIDATION.MIGRATION_REPORT AS

WITH raw_summary AS (

    SELECT

        COUNT(*) AS RAW_ROWS

    FROM DATATHON_DEV.RAW.SALES_RAW

),

staging_summary AS (

    SELECT

        COUNT(*) AS STAGING_ROWS,


        -- Accepted product records.

        COUNT_IF(
            VALIDATION_STATUS = 'VALID'
        ) AS VALID_ROWS,


        -- Records excluded or flagged by the current rules.

        COUNT_IF(
            VALIDATION_STATUS = 'INVALID_NUMERIC'
        ) AS INVALID_NUMERIC_ROWS,

        COUNT_IF(
            VALIDATION_STATUS = 'DUPLICATE_SOURCE_ID'
        ) AS DUPLICATE_SOURCE_ROWS,

        COUNT_IF(
            VALIDATION_STATUS = 'NON_PRODUCT'
        ) AS NON_PRODUCT_ROWS,

        COUNT_IF(
            VALIDATION_STATUS = 'INVALID_SKU'
        ) AS INVALID_SKU_ROWS,

        COUNT_IF(
            VALIDATION_STATUS = 'NEGATIVE_VALUE'
        ) AS NEGATIVE_VALUE_ROWS,

        COUNT_IF(
            VALIDATION_STATUS = 'PERIOD_TOTAL_MISMATCH'
        ) AS PERIOD_TOTAL_MISMATCH_ROWS,


        -- All statuses not included in the accepted
        -- product record group.

        COUNT_IF(
            VALIDATION_STATUS <> 'VALID'
        ) AS EXCLUDED_ROWS,


        -- Accepted sales amount calculated directly
        -- from the classified source records.

        SUM(

            CASE

                WHEN VALIDATION_STATUS = 'VALID'

                    THEN JAN_TOTAL_PRICE

                ELSE 0

            END

        ) AS VALID_SOURCE_SALES

    FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

),

mart_summary AS (

    SELECT

        COUNT(*) AS MART_PRODUCT_COUNT,

        COALESCE(
            SUM(TOTAL_SALES_AMOUNT),
            0
        ) AS MART_TOTAL_SALES

    FROM DATATHON_DEV.MART.PRODUCT_SALES

)

SELECT

    -- Source and target record counts.

    r.RAW_ROWS,

    s.STAGING_ROWS,

    s.VALID_ROWS,

    s.EXCLUDED_ROWS,


    -- Data quality breakdown.

    s.INVALID_NUMERIC_ROWS,

    s.DUPLICATE_SOURCE_ROWS,

    s.NON_PRODUCT_ROWS,

    s.INVALID_SKU_ROWS,

    s.NEGATIVE_VALUE_ROWS,

    s.PERIOD_TOTAL_MISMATCH_ROWS,


    -- Final business-ready dataset.

    m.MART_PRODUCT_COUNT,


    -- Reconciliation amounts.

    ROUND(
        s.VALID_SOURCE_SALES,
        2
    ) AS VALID_SOURCE_SALES,

    ROUND(
        m.MART_TOTAL_SALES,
        2
    ) AS MART_TOTAL_SALES,


    -- Validation 1:
    -- All RAW records are represented in STAGING.

    r.RAW_ROWS = s.STAGING_ROWS

        AS RAW_TO_STAGING_ROW_COUNT_MATCH,


    -- Validation 2:
    -- Accepted and excluded records account for
    -- all STAGING records.

    s.STAGING_ROWS =
        s.VALID_ROWS + s.EXCLUDED_ROWS

        AS ALL_ROWS_CLASSIFIED,


    -- Validation 3:
    -- Accepted source sales match MART sales.

    ABS(

        COALESCE(s.VALID_SOURCE_SALES, 0)
        -
        COALESCE(m.MART_TOTAL_SALES, 0)

    ) < 0.005

        AS VALID_SALES_RECONCILED

FROM raw_summary r

CROSS JOIN staging_summary s

CROSS JOIN mart_summary m;


-- 6.1 Review the migration validation report.

SELECT *
FROM DATATHON_DEV.VALIDATION.MIGRATION_REPORT;


-- ============================================================
-- STEP 7: AI-ASSISTED DATA REPAIR CANDIDATES
-- ============================================================

-- AI can assist with identifying possible mappings and
-- proposing repair candidates for problematic records.
--
-- However, AI-generated suggestions must be reviewed
-- against the original legacy report and business rules.
--
-- Example:
--
-- A January quantity may contain an invalid string,
-- while the reported Total quantity contains a valid number.
--
-- AI may propose using the reported Total as a candidate
-- replacement for the invalid January value.
--
-- This replacement is valid only when the relevant
-- reporting-period assumption has been confirmed.
--
-- The current step creates repair candidates for review.
-- It does not overwrite RAW, STAGING or MART records.
--
-- The SQL below implements a deterministic candidate rule.
-- To demonstrate AI-assisted migration, separately retain
-- the actual AI prompt, AI response and human review record.
--
-- Do not describe a candidate as AI-approved unless it
-- was genuinely produced and reviewed through that process.


CREATE OR REPLACE TABLE
DATATHON_DEV.VALIDATION.REPAIR_CANDIDATES AS

SELECT

    SOURCE_ROW_ID,
    INGEST_ROW_ID,

    SKU,
    RAW_DESCRIPTION,


    -- Original source values.

    RAW_COL_3 AS ORIGINAL_JAN_QUANTITY,

    RAW_COL_6 AS ORIGINAL_TOTAL_QUANTITY,


    -- Suggested replacement value.
    --
    -- This is a candidate only, not an approved correction.

    REPORTED_TOTAL_QUANTITY
        AS SUGGESTED_JAN_QUANTITY,


    -- Determine whether the current record contains
    -- a plausible repair candidate.

    CASE

        WHEN
            JAN_PRODUCT_QUANTITY IS NULL

            AND REPORTED_TOTAL_QUANTITY IS NOT NULL

            AND REPORTED_TOTAL_QUANTITY >= 0

            AND RAW_COL_3 IS NOT NULL

        THEN 'POSSIBLE_REPAIR_REQUIRES_REVIEW'

        ELSE 'MANUAL_REVIEW_REQUIRED'

    END AS REPAIR_STATUS,


    -- Record the assumption that must be verified
    -- before applying any suggested correction.

    'Verify that January quantity should equal the reported total quantity before applying this candidate.'

        AS REPAIR_ASSUMPTION

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

WHERE VALIDATION_STATUS = 'INVALID_NUMERIC';


-- 7.1 Review potential data repair candidates.

SELECT *

FROM DATATHON_DEV.VALIDATION.REPAIR_CANDIDATES

ORDER BY
    TRY_TO_NUMBER(INGEST_ROW_ID),
    INGEST_ROW_ID;
