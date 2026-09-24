AI-Assisted Migration Review

Project: Legacy Sales Report Migration to Snowflake
Use Case: AI-Assisted System Migration
Review scope: Legacy field mapping, Snowflake transformation SQL, data quality classification, business assumptions, and migration validation
Review status: AI recommendations provided; implementation and business-rule approval remain subject to human review.

1. Executive Summary

The current proof of concept demonstrates a working migration from a legacy Excel sales report to structured Snowflake tables.

The implemented pipeline preserves source records in RAW.SALES_RAW, classifies records in STAGING.SALES_CLASSIFIED, aggregates accepted product records in MART.PRODUCT_SALES, and produces validation results in VALIDATION.MIGRATION_REPORT.

Based on the Snowflake results provided during this review, the initial classification produced:

Classification

	

Records




Valid product records

	

339




Invalid numeric records

	

16




Non-product records

	

13




Duplicate source ID records

	

5




Total

	

373

These are observed results of the current classification rules, not proof that every record has been assigned the correct business meaning.

Overall review finding: The existing pipeline is a credible migration PoC. Its main remaining risks concern report-level business context, duplicate handling, period-total assumptions, and reconciliation against the original legacy report. The recommendations below aim to improve auditability without changing the original RAW data.

2. Legacy-to-Snowflake Field Mapping
2.1 Mapping supported by the supplied evidence

The first two rows of the imported report identify two metric groups: January 2026 and Total. Both contain Order, Product Quantity, and Total Price.

The following mapping is supported by those headers and by the SQL currently implemented:

Legacy source

	

Snowflake target

	

Conversion




RAW_COL_1

	

RAW_DESCRIPTION

	

Preserve as text




SKU embedded in RAW_COL_1

	

SKU

	

Extract SKU followed by digits




RAW_COL_2 — January Order

	

JAN_ORDER_COUNT

	

Convert to integer




RAW_COL_3 — January Product Quantity

	

JAN_PRODUCT_QUANTITY

	

Convert to integer




RAW_COL_4 — January Total Price

	

JAN_TOTAL_PRICE

	

Convert to decimal




RAW_COL_5 — Total Order

	

REPORTED_TOTAL_ORDER_COUNT

	

Convert to integer




RAW_COL_6 — Total Product Quantity

	

REPORTED_TOTAL_QUANTITY

	

Convert to integer




RAW_COL_7 — Total Price

	

REPORTED_TOTAL_PRICE

	

Convert to decimal




SOURCE_ROW_ID

	

SOURCE_ROW_ID

	

Preserve source lineage




INGEST_ROW_ID

	

INGEST_ROW_ID

	

Preserve ingestion lineage

Human review required: Confirm that the January and Total columns have these meanings throughout the entire source report, not merely in its opening section.

2.2 Unresolved source structure

The legacy report also contains non-product rows, including a store-level summary visible near the beginning of the imported data.

The current transformation identifies product rows but does not preserve their store context as a separate field. Consequently, MART.PRODUCT_SALES aggregates records by SKU without distinguishing stores.

It has not yet been established whether the same SKU can occur under multiple store sections or whether the report contains multiple reporting periods.

Recommendation: Preserve report context in the target model before presenting the MART as a complete business-level migration. If store context cannot be reliably reconstructed within the Datathon timeframe, describe the existing MART as an accepted-record SKU summary, not a complete store-level sales model.

3. Review of the Current Migration Logic

Review area

	

Observed implementation

	

Risk and recommended action




RAW preservation

	

Source columns remain VARCHAR

	

Appropriate for retaining invalid text values. Continue treating RAW as immutable during transformation.




Product identification

	

Rows beginning with [SKU are classified as product candidates

	

Suitable for the observed format, but assumes all product rows use that prefix. Inspect any unrecognised row patterns.




Numeric conversion

	

Uses TRY_TO_NUMBER and TRY_TO_DECIMAL

	

Conversion failures become NULL, allowing records to be flagged. Add checks for fractional counts and negative values.




Duplicate handling

	

Later occurrences of a SOURCE_ROW_ID are flagged

	

Repeated source IDs are evidence of a lineage collision, not necessarily identical business records. Compare source contents before approving removal.




Period-total comparison

	

January metrics are compared with Total metrics

	

Requires confirmation that January and Total should match for every relevant record.




MART aggregation

	

Groups accepted records by SKU

	

May combine records from different stores or sections. Define the intended aggregation grain explicitly.




Reconciliation

	

Compares accepted STAGING sales with MART sales

	

Demonstrates internal consistency, not complete reconciliation with the legacy Excel report.




AI repair candidates

	

Suggests Total Quantity as a possible replacement for an invalid January Quantity

	

The candidate is not a verified correction. Retain manual-review status until the reporting-period assumption is confirmed.

Finding A — Duplicate-source handling needs stronger evidence

The RAW quality report previously showed 7 additional occurrences of source identifiers, while the STAGING classification showed 5 records with DUPLICATE_SOURCE_ID status.

These results are not necessarily contradictory. The current CASE statement classifies non-product rows before checking duplicate source IDs. A repeated source ID on a non-product row will therefore receive NON_PRODUCT, not DUPLICATE_SOURCE_ID.

This means that validation-status counts are mutually exclusive primary classifications, not complete counts of every data quality issue.

Recommended SQL — audit all repeated source identifiers independently:

-- AI recommendation:
-- Audit source-ID collisions independently of the primary
-- validation status. Do not automatically delete the records.

SELECT
    SOURCE_ROW_ID,
    COUNT(*) AS RECORD_COUNT,
    COUNT(DISTINCT INGEST_ROW_ID) AS DISTINCT_INGEST_IDS,
    COUNT_IF(
        VALIDATION_STATUS = 'DUPLICATE_SOURCE_ID'
    ) AS CLASSIFIED_DUPLICATE_ROWS,
    COUNT_IF(
        VALIDATION_STATUS = 'NON_PRODUCT'
    ) AS CLASSIFIED_NON_PRODUCT_ROWS
FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED
WHERE SOURCE_ROW_ID IS NOT NULL
GROUP BY SOURCE_ROW_ID
HAVING COUNT(*) > 1
ORDER BY RECORD_COUNT DESC, SOURCE_ROW_ID;

Human approval required: Determine whether repeated source identifiers represent deliberately injected duplicates, legitimate repeated report rows, or an issue in source-ID generation.

Until that review is complete, describe the current rule as source-ID-based duplicate screening.

Finding B — The period-total comparison is conditional

The current SQL flags a row when:

JAN_PRODUCT_QUANTITY <> REPORTED_TOTAL_QUANTITY

Equivalent comparisons are made for order counts and sales amounts.

The opening report section shows January 2026 and Total as separate groups. It does not, by itself, prove that their values must always be identical across the entire report.

Recommended adjustment: Use a review-oriented status until the business rule is confirmed.

-- Use this status when the relationship between
-- January and Total has not been formally confirmed.

WHEN JAN_ORDER_COUNT <> REPORTED_TOTAL_ORDER_COUNT
  OR JAN_PRODUCT_QUANTITY <> REPORTED_TOTAL_QUANTITY
  OR JAN_TOTAL_PRICE <> REPORTED_TOTAL_PRICE

    THEN 'PERIOD_TOTAL_REVIEW'

Changing the label does not resolve the underlying uncertainty; it makes that uncertainty visible to downstream users.

If the original report documentation confirms that Total must equal January, the existing PERIOD_TOTAL_MISMATCH status can be retained as a data quality failure.

Finding C — The target data model needs an explicit grain

The current MART groups records by SKU:

GROUP BY SKU

This produces one row per SKU across all accepted source records.

That is a valid technical aggregation, but the business interpretation needs to be documented. In particular, summing product-level reported order counts does not necessarily produce the number of distinct customer orders.

Recommended data model statement:

Each row in MART.PRODUCT_SALES represents one SKU aggregated across all source records accepted by the current validation rules. Store-level attribution, distinct-order counting, and full-report sales reconciliation are outside the validated scope of this initial MART.

If the team confirms that store identifiers can be derived reliably, extend the model to include STORE_ID or STORE_NAME and group by both store and SKU.

4. Recommended SQL Improvements

The following changes are targeted improvements to the current implementation. They do not require replacing the entire migration script.

4.1 Add independent data quality flags

The existing VALIDATION_STATUS provides one primary reason for each record's classification. A record may nevertheless contain multiple issues.

A separate quality-flags view makes those issues independently inspectable.

CREATE OR REPLACE VIEW
DATATHON_DEV.VALIDATION.SALES_QUALITY_FLAGS AS

SELECT
    SOURCE_ROW_ID,
    INGEST_ROW_ID,
    SKU,
    RAW_DESCRIPTION,
    VALIDATION_STATUS,

    -- Non-product records, such as headers and summaries.
    NOT STARTSWITH(
        TRIM(COALESCE(RAW_DESCRIPTION, '')),
        '[SKU'
    ) AS IS_NON_PRODUCT,

    -- Identify source-ID collisions without relying
    -- on the order of the primary CASE statement.
    SOURCE_ROW_ID IS NOT NULL
        AND COUNT(*) OVER (
            PARTITION BY SOURCE_ROW_ID
        ) > 1 AS HAS_REPEATED_SOURCE_ID,

    -- Failed conversion of January quantity.
    RAW_COL_3 IS NOT NULL
        AND JAN_PRODUCT_QUANTITY IS NULL
        AS HAS_INVALID_JAN_QUANTITY,

    -- Negative values are invalid under the current
    -- non-negative sales-metrics assumption.
    JAN_ORDER_COUNT < 0
        OR JAN_PRODUCT_QUANTITY < 0
        OR JAN_TOTAL_PRICE < 0
        OR REPORTED_TOTAL_ORDER_COUNT < 0
        OR REPORTED_TOTAL_QUANTITY < 0
        OR REPORTED_TOTAL_PRICE < 0
        AS HAS_NEGATIVE_METRIC,

    -- This flag identifies a difference, not necessarily
    -- a confirmed business error.
    COALESCE(
        JAN_ORDER_COUNT <> REPORTED_TOTAL_ORDER_COUNT
        OR JAN_PRODUCT_QUANTITY <> REPORTED_TOTAL_QUANTITY
        OR JAN_TOTAL_PRICE <> REPORTED_TOTAL_PRICE,
        FALSE
    ) AS HAS_PERIOD_TOTAL_DIFFERENCE

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED;

This view supplements the existing primary classification. It does not change which records enter MART.

Expected benefit: A repeated source identifier with an invalid quantity can be identified as having both issues, even if the primary VALIDATION_STATUS shows only one.

4.2 Restrict repair candidates to the actual issue being reviewed

The current repair-candidate table includes all INVALID_NUMERIC records, even where the failed conversion occurred in a different numeric field.

For the January Quantity example, a more precise candidate-selection query is:

CREATE OR REPLACE VIEW
DATATHON_DEV.VALIDATION.JAN_QUANTITY_REPAIR_REVIEW AS

SELECT
    SOURCE_ROW_ID,
    INGEST_ROW_ID,
    SKU,
    RAW_DESCRIPTION,

    RAW_COL_3 AS ORIGINAL_JAN_QUANTITY,
    RAW_COL_6 AS ORIGINAL_TOTAL_QUANTITY,

    REPORTED_TOTAL_QUANTITY
        AS SUGGESTED_JAN_QUANTITY,

    'PENDING_BUSINESS_REVIEW'
        AS REVIEW_STATUS,

    'Confirm the reporting-period relationship '
    || 'before treating Total Quantity as January Quantity.'
        AS REVIEW_REASON

FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

WHERE VALIDATION_STATUS = 'INVALID_NUMERIC'

  AND JAN_PRODUCT_QUANTITY IS NULL

  AND RAW_COL_3 IS NOT NULL

  AND REPORTED_TOTAL_QUANTITY IS NOT NULL

  AND REPORTED_TOTAL_QUANTITY >= 0;

This creates a narrower, more explainable review queue.

Important: The SQL does not establish that the suggested quantity is correct. It also does not demonstrate that an AI model independently discovered the repair rule; the view is a deterministic implementation of a proposed review rule.

4.3 Strengthen the accepted-record reconciliation

The existing report checks whether accepted STAGING sales equal MART sales. That is useful, but the reconciliation should also compare the accepted quantity and source-record contributions.

SELECT
    s.VALID_SOURCE_RECORDS,
    m.MART_SOURCE_RECORDS,

    s.VALID_SOURCE_QUANTITY,
    m.MART_PRODUCT_QUANTITY,

    s.VALID_SOURCE_SALES,
    m.MART_TOTAL_SALES,

    s.VALID_SOURCE_RECORDS = m.MART_SOURCE_RECORDS
        AS RECORD_CONTRIBUTION_MATCH,

    s.VALID_SOURCE_QUANTITY = m.MART_PRODUCT_QUANTITY
        AS PRODUCT_QUANTITY_MATCH,

    ABS(
        s.VALID_SOURCE_SALES - m.MART_TOTAL_SALES
    ) < 0.005
        AS ACCEPTED_SALES_MATCH

FROM (
    SELECT
        COUNT(*) AS VALID_SOURCE_RECORDS,
        COALESCE(SUM(JAN_PRODUCT_QUANTITY), 0)
            AS VALID_SOURCE_QUANTITY,
        COALESCE(SUM(JAN_TOTAL_PRICE), 0)
            AS VALID_SOURCE_SALES
    FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED
    WHERE VALIDATION_STATUS = 'VALID'
) s

CROSS JOIN (
    SELECT
        COALESCE(SUM(SOURCE_RECORD_COUNT), 0)
            AS MART_SOURCE_RECORDS,
        COALESCE(SUM(PRODUCT_QUANTITY), 0)
            AS MART_PRODUCT_QUANTITY,
        COALESCE(SUM(TOTAL_SALES_AMOUNT), 0)
            AS MART_TOTAL_SALES
    FROM DATATHON_DEV.MART.PRODUCT_SALES
) m;

Interpretation: Passing these checks demonstrates that the accepted STAGING records have been aggregated consistently into MART. It does not establish whether records excluded by the classification rules should have been included, or whether the original Excel's published totals match the migrated output.

5. Business Assumptions Requiring Human Confirmation

Assumption

	

Current evidence

	

Required confirmation




January equals Total

	

The opening report rows show matching values, and the current SQL compares the groups

	

Confirm the reporting period and whether equality is an actual business rule




[SKU...] identifies all product rows

	

Visible product records follow this pattern

	

Inspect the full legacy report for other product-row formats




Repeated SOURCE_ROW_ID indicates an injected duplicate

	

RAW contains repeated source IDs

	

Compare original source records and the dirty-data generation manifest




Counts must be non-negative integers

	

Current model treats orders and quantities as counts

	

Confirm how returns, cancellations, corrections, and fractional quantities should be represented




Price values can be represented to two decimal places

	

Current SQL uses TRY_TO_DECIMAL(..., 18, 2)

	

Confirm currency, rounding rules, and whether source prices have greater precision




SKU is sufficient for aggregation

	

Current MART groups by SKU

	

Confirm whether SKU records from different stores or report sections may be combined




Non-product rows can be excluded from the product MART

	

Current logic excludes headers and summary rows

	

Preserve store summaries separately if they are needed for complete source-to-target reconciliation




Total Quantity can repair invalid January Quantity

	

Some rows contain an invalid January value and a readable Total value

	

Verify period semantics against the original Excel before approving any replacement

No missing business rules should be inferred from numeric similarity alone.

6. Proposed Human Review and Approval Record

The following is a proposed review log. The decisions in this table are recommendations, not a record of human approvals already completed. The project owner should replace each pending status after reviewing the original report and executing the relevant SQL.

AI recommendation

	

Proposed human decision

	

Reason

	

Status




Preserve all original source columns in RAW

	

Retain

	

Supports traceability and reprocessing

	

Pending confirmation




Extract SKU from product descriptions

	

Retain after checking full-report coverage

	

Produces a structured product identifier

	

Pending confirmation




Audit repeated source IDs separately from primary status

	

Implement

	

Prevents classification precedence from hiding additional issues

	

Pending implementation




Replace invalid January Quantity using Total Quantity

	

Do not apply automatically

	

Period equivalence has not been established

	

Pending business review




Rename unconfirmed period-total failures as review cases

	

Consider

	

Separates observed differences from confirmed business errors

	

Pending business review




Add quantity and record-contribution reconciliation

	

Implement

	

Strengthens internal transformation testing

	

Pending implementation




Extend MART to store-level aggregation

	

Defer unless store attribution is verified

	

Prevents unsupported store assignments

	

Pending source analysis

Evidence to retain in GitHub

For an auditable AI-assisted migration record, retain the actual AI review request, this AI-generated response, any SQL changes adopted from it, and the Snowflake execution results.

Do not describe a suggested modification as implemented, tested, or human-approved until those steps have actually occurred.

7. Final Assessment and Limitations

The existing Snowflake PoC demonstrates that a legacy sales report can be imported, classified, transformed into a structured product-level dataset, and exposed through a Streamlit dashboard.

The review identifies four material limitations that should be disclosed in the final presentation: store and reporting-period context are not fully established; duplicate detection currently relies on source identifiers; accepted-record reconciliation does not cover the complete legacy report; and repair candidates must not be applied without human confirmation.

This AI review contributes field-mapping analysis, identifies conversion risks, proposes SQL improvements, and documents business assumptions requiring approval. Its outputs are recommendations for the migration process, not independent proof that the source data or resulting business figures are correct.