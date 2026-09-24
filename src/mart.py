"""
MART 层：给分析和 Athena 用的星型模型（候选版本 candidate）。

  dim_product         一行 = 一个 item_code（商品 / 折扣 / 运费 ...）
  fact_monthly_sales  一行 = 一个月 × 一个 item_code
  report_totals       报表自带的汇总行（门店汇总 + Total），给对账用

运行：通常由 pipeline.py 调用
"""
import os
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_CSV = Path(os.getenv("RAW_CSV", BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv"))
STAGING_DIR = Path(os.getenv("STAGING_DIR", BASE_DIR / "data" / "staging"))
MART_DIR = Path(os.getenv("MART_DIR", BASE_DIR / "data" / "mart" / "candidate" / "manual"))
BATCH_ID = os.getenv("BATCH_ID", "manual")
RUN_ID = os.getenv("RUN_ID", "manual")
MART_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute(f"CREATE VIEW lines  AS SELECT * FROM '{STAGING_DIR / 'sales_lines.parquet'}'")
con.execute(f"CREATE VIEW issues AS SELECT * FROM '{STAGING_DIR / 'dq_issues.parquet'}'")

# 报表月份：来自原始文件第一行的 "January 2026"
month_text = con.execute(
    "SELECT raw_col_2 FROM read_csv(?, all_varchar = true) WHERE source_row_id = '1'",
    [str(RAW_CSV)],
).fetchone()[0]
report_month = con.execute("SELECT strptime(?, '%B %Y')::DATE", [month_text]).fetchone()[0]
print(f"报表月份: {month_text} → {report_month}")

# dim_product
con.execute("""
    CREATE TABLE dim_product AS
    SELECT DISTINCT item_code, brand, item_name, variant, line_type
    FROM lines
    WHERE row_type = 'line'
""")

# fact_monthly_sales —— NULL 的值保持 NULL，并打上 has_dq_issue 标记
con.execute(f"""
    CREATE TABLE fact_monthly_sales AS
    SELECT
        DATE '{report_month}'  AS report_month,
        l.item_code,
        l.line_type,
        l.orders,
        l.qty,
        l.amount,
        EXISTS (SELECT 1 FROM issues i
                WHERE i.source_row_id = l.source_row_id
                  AND i.issue_type <> 'duplicate_row') AS has_dq_issue,
        l.source_row_id,
        '{BATCH_ID}' AS batch_id,
        '{RUN_ID}'   AS run_id
    FROM lines l
    WHERE l.row_type = 'line'
""")

# report_totals —— 报表自己的汇总行，不混进 fact
con.execute(f"""
    CREATE TABLE report_totals AS
    SELECT DATE '{report_month}' AS report_month, row_type, raw_item AS label,
           orders, qty, amount, '{BATCH_ID}' AS batch_id, '{RUN_ID}' AS run_id
    FROM lines
    WHERE row_type IN ('store_total', 'grand_total')
""")

for table in ["dim_product", "fact_monthly_sales", "report_totals"]:
    con.execute(f"COPY {table} TO '{MART_DIR / (table + '.parquet')}' (FORMAT PARQUET)")
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table:<20} {n:>4} 行")

print("按 line_type 汇总:")
print(con.sql("""
    SELECT line_type, COUNT(*) AS n_items, SUM(qty) AS qty, ROUND(SUM(amount), 2) AS amount
    FROM fact_monthly_sales GROUP BY 1 ORDER BY amount DESC
"""))
print(f"已写出: {MART_DIR}")
