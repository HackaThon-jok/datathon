"""
STAGING 层：把 legacy 报表 CSV 变成一行一条记录的干净表。

运行：python scripts/staging.py
输出：data/staging/sales_lines.parquet   干净的明细行
      data/staging/dq_issues.parquet     检测到的数据质量问题
"""
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_CSV = BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv"
OUT_DIR = BASE_DIR / "data" / "staging"
OUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()

# 第 1 步：原样读入（全部当文本，不做任何解释）
con.execute("""
    CREATE TABLE raw AS
    SELECT *,
           CAST(source_row_id AS INT) AS src_id,
           CAST(ingest_row_id AS INT) AS ing_id
    FROM read_csv(?, all_varchar = true)
""", [str(RAW_CSV)])

# 第 2 步：给每一行打上"行类型"
con.execute("""
    CREATE TABLE typed AS
    SELECT *,
        CASE
            WHEN src_id <= 2              THEN 'header'
            WHEN raw_col_1 = 'Total'      THEN 'grand_total'
            WHEN raw_col_1 NOT LIKE '[%'  THEN 'store_total'
            ELSE 'line'
        END AS row_type
    FROM raw
""")

# 第 3 步：去重 —— 同一个 source_row_id 只保留第一次出现的那行
con.execute("""
    CREATE TABLE dedup AS
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY src_id ORDER BY ing_id) AS copy_no
    FROM typed
""")

# 第 4 步：解析商品名 + 数值转换
#   "[SKU1141] [Ambervale]Immune Support Milk Powder (900g){Express Freight}"
#     code=SKU1141  brand=Ambervale  name=Immune Support...(900g)  variant=Express Freight
con.execute(r"""
    CREATE TABLE parsed AS
    SELECT
        src_id AS source_row_id,
        ing_id AS ingest_row_id,
        row_type,
        copy_no,
        raw_col_1 AS raw_item,
        regexp_extract(raw_col_1, '^\[([^\]]+)\]', 1)                          AS item_code,
        NULLIF(regexp_extract(raw_col_1, '^\[[^\]]+\]\s*\[([^\]]+)\]', 1), '') AS brand,
        trim(regexp_replace(
            regexp_replace(raw_col_1, '^\[[^\]]+\]\s*(\[[^\]]+\])?', ''),
            '\{[^}]*\}$', ''))                                                AS item_name,
        NULLIF(regexp_extract(raw_col_1, '\{([^}]*)\}$', 1), '')               AS variant,
        CASE
            WHEN raw_col_1 LIKE '[SKU%'      THEN 'product'
            WHEN raw_col_1 LIKE '[DIS%'      THEN 'discount'
            WHEN raw_col_1 LIKE '[IFFSHIP%'  THEN 'freight'
            WHEN raw_col_1 LIKE '[FREEGIFT%' THEN 'gift'
            WHEN raw_col_1 LIKE '[EWALLET%'  THEN 'wallet'
            ELSE 'unknown'
        END AS line_type,
        raw_col_2, raw_col_3, raw_col_4,
        TRY_CAST(raw_col_2 AS INT)              AS orders,
        TRY_CAST(raw_col_3 AS INT)              AS qty,
        ROUND(TRY_CAST(raw_col_4 AS DOUBLE), 2) AS amount
    FROM dedup
    WHERE row_type <> 'header'
""")

# 第 5 步：把所有问题记进 dq_issues（不偷偷修改数据）
con.execute("""
    CREATE TABLE dq_issues AS
    SELECT source_row_id, ingest_row_id, 'duplicate_row' AS issue_type,
           '<ROW>' AS field, NULL AS raw_value
    FROM parsed WHERE copy_no > 1
    UNION ALL
    SELECT source_row_id, ingest_row_id,
           CASE WHEN raw_col_2 IS NULL THEN 'missing_value' ELSE 'invalid_numeric' END,
           'raw_col_2', raw_col_2
    FROM parsed WHERE copy_no = 1 AND orders IS NULL
    UNION ALL
    SELECT source_row_id, ingest_row_id,
           CASE WHEN raw_col_3 IS NULL THEN 'missing_value' ELSE 'invalid_numeric' END,
           'raw_col_3', raw_col_3
    FROM parsed WHERE copy_no = 1 AND qty IS NULL
    UNION ALL
    SELECT source_row_id, ingest_row_id,
           CASE WHEN raw_col_4 IS NULL THEN 'missing_value' ELSE 'invalid_numeric' END,
           'raw_col_4', raw_col_4
    FROM parsed WHERE copy_no = 1 AND amount IS NULL
""")

# 第 6 步：输出 Parquet
con.execute(f"""
    COPY (SELECT * EXCLUDE (raw_col_2, raw_col_3, raw_col_4)
          FROM parsed WHERE copy_no = 1 ORDER BY source_row_id)
    TO '{OUT_DIR / "sales_lines.parquet"}' (FORMAT PARQUET)
""")
con.execute(f"""
    COPY (SELECT * FROM dq_issues ORDER BY issue_type, source_row_id)
    TO '{OUT_DIR / "dq_issues.parquet"}' (FORMAT PARQUET)
""")

# 打印摘要
print("行类型统计（去重后）:")
print(con.sql("SELECT row_type, line_type, COUNT(*) AS n FROM parsed WHERE copy_no = 1 GROUP BY ALL ORDER BY n DESC"))
print("解析示例:")
print(con.sql("SELECT item_code, brand, item_name, variant, line_type FROM parsed WHERE copy_no = 1 AND (variant IS NOT NULL OR line_type <> 'product') LIMIT 6"))
print("检测到的问题:")
print(con.sql("SELECT issue_type, field, COUNT(*) AS n FROM dq_issues GROUP BY ALL ORDER BY n DESC"))
print(f"已写出: {OUT_DIR}")
