import duckdb

con = duckdb.connect()
con.sql("""
    CREATE VIEW raw AS
    SELECT * FROM read_csv('data/legacy_dirty/sales_dirty.csv', all_varchar = true)
""")

print("1) 总行数")
print(con.sql("SELECT COUNT(*) AS n_rows FROM raw"))

print("2) 前 8 行长什么样")
print(con.sql("SELECT raw_col_1, raw_col_2, raw_col_3, raw_col_4, source_row_id FROM raw LIMIT 8"))

print("3) 重复出现的 source_row_id")
print(con.sql("""
    SELECT source_row_id, COUNT(*) AS n
    FROM raw GROUP BY source_row_id HAVING COUNT(*) > 1
    ORDER BY CAST(source_row_id AS INT)
"""))

print("4) Order 列不是数字的行（缺失或非法）")
print(con.sql("""
    SELECT source_row_id, raw_col_1, raw_col_2
    FROM raw
    WHERE CAST(source_row_id AS INT) > 2
      AND TRY_CAST(raw_col_2 AS DOUBLE) IS NULL
"""))
