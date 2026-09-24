
import streamlit as st
import pandas as pd 
from snowflake.snowpark.context import get_active_session


# ============================================================
# DATATHON 2026
# AI-Assisted Legacy System Migration Dashboard
#
# Data source:
# DATATHON_DEV.RAW
# DATATHON_DEV.STAGING
# DATATHON_DEV.MART
# DATATHON_DEV.VALIDATION
#
# This application reads previously generated migration
# results. It does not modify source or business data.
# ============================================================


st.set_page_config(
    page_title="Datathon Migration Dashboard",
    layout="wide"
)


# ------------------------------------------------------------
# 1. Establish Snowflake session
# ------------------------------------------------------------

session = get_active_session()

st.title("AI-Assisted Legacy Data Migration")

st.caption(
    "Legacy Excel → Snowflake RAW → STAGING → MART → VALIDATION"
)


# ------------------------------------------------------------
# 2. Load migration results
# ------------------------------------------------------------

@st.cache_data(ttl=60)
def load_quality_data():

    return session.sql("""
        SELECT
            VALIDATION_STATUS,
            COUNT(*) AS RECORD_COUNT

        FROM DATATHON_DEV.STAGING.SALES_CLASSIFIED

        GROUP BY VALIDATION_STATUS

        ORDER BY RECORD_COUNT DESC
    """).to_pandas()


@st.cache_data(ttl=60)
def load_migration_report():

    return session.sql("""
        SELECT *

        FROM DATATHON_DEV.VALIDATION.MIGRATION_REPORT
    """).to_pandas()


@st.cache_data(ttl=60)
def load_product_sales():

    return session.sql("""
        SELECT
            SKU,
            PRODUCT_DESCRIPTION,
            REPORTED_ORDER_COUNT,
            PRODUCT_QUANTITY,
            TOTAL_SALES_AMOUNT

        FROM DATATHON_DEV.MART.PRODUCT_SALES

        ORDER BY TOTAL_SALES_AMOUNT DESC
    """).to_pandas()


@st.cache_data(ttl=60)
def load_repair_candidates():

    return session.sql("""
        SELECT
            SOURCE_ROW_ID,
            SKU,
            ORIGINAL_JAN_QUANTITY,
            ORIGINAL_TOTAL_QUANTITY,
            SUGGESTED_JAN_QUANTITY,
            REPAIR_STATUS

        FROM DATATHON_DEV.VALIDATION.REPAIR_CANDIDATES

        ORDER BY TRY_TO_NUMBER(INGEST_ROW_ID)
    """).to_pandas()


quality_df = load_quality_data()

report_df = load_migration_report()

product_df = load_product_sales()

repair_df = load_repair_candidates()


# ------------------------------------------------------------
# 3. Overall migration status
# ------------------------------------------------------------

st.header("Migration Overview")

if report_df.empty:

    st.warning("Migration report is not available.")

    st.stop()


report = report_df.iloc[0]

raw_rows = int(report["RAW_ROWS"])

valid_rows = int(report["VALID_ROWS"])

excluded_rows = int(report["EXCLUDED_ROWS"])

mart_product_count = int(report["MART_PRODUCT_COUNT"])


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "RAW Records",
    raw_rows
)

col2.metric(
    "Accepted Product Records",
    valid_rows
)

col3.metric(
    "Flagged / Excluded Records",
    excluded_rows
)

col4.metric(
    "MART Products",
    mart_product_count
)


# ------------------------------------------------------------
# 4. Data quality results
# ------------------------------------------------------------

st.header("Data Quality Assessment")

left, right = st.columns([1, 1])

with left:

    st.subheader("Record Classification")

    st.bar_chart(
        quality_df.set_index("VALIDATION_STATUS")[
            "RECORD_COUNT"
        ]
    )


with right:

    st.subheader("Classification Details")

    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True
    )


# ------------------------------------------------------------
# 5. Business-ready sales data
# ------------------------------------------------------------

st.header("Migrated Product Sales")

st.caption(
    "Sales amounts include accepted product records only. "
    "They are not the complete legacy report total."
)

top_products = product_df.head(10)

st.subheader("Top 10 Products by Accepted Sales")

st.bar_chart(
    top_products.set_index("SKU")[
        "TOTAL_SALES_AMOUNT"
    ]
)

st.subheader("Product Sales Table")

st.dataframe(
    product_df,
    use_container_width=True,
    hide_index=True
)



# ============================================================
# 6. MIGRATION VALIDATION
# ============================================================

st.header("Migration Validation")


def show_check(label, passed):
    """
    Display whether a migration validation check passed.
    """

    if pd.isna(passed):
        st.warning(f"{label}: NOT AVAILABLE")

    elif bool(passed):
        st.success(f"{label}: PASS")

    else:
        st.error(f"{label}: FAIL")


show_check(
    "RAW to STAGING row count",
    report["RAW_TO_STAGING_ROW_COUNT_MATCH"]
)

show_check(
    "All STAGING records classified",
    report["ALL_ROWS_CLASSIFIED"]
)

show_check(
    "Accepted sales reconciled with MART",
    report["VALID_SALES_RECONCILED"]
)


with st.expander("View Migration Report"):
    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True
    )

# ------------------------------------------------------------
# 7. AI-assisted repair candidates
# ------------------------------------------------------------

st.header("Data Repair Review")

st.info(
    "Repair candidates are suggestions only. "
    "No source records are automatically overwritten."
)

st.dataframe(
    repair_df,
    use_container_width=True,
    hide_index=True
)


# ------------------------------------------------------------
# 8. Limitations
# ------------------------------------------------------------

st.header("Current MVP Limitations")

st.write(
    "The MVP uses a manually uploaded CSV rather than "
    "an automated S3-to-Snowflake ingestion pipeline."
)

st.write(
    "Records with invalid values are flagged for review "
    "and excluded from the accepted product sales MART."
)

st.write(
    "The migration validation checks internal consistency. "
    "Full reconciliation against the original Excel report "
    "requires additional business-level validation."
)

st.write(
    "AI-generated repair suggestions require human review "
    "before they can be applied."
)