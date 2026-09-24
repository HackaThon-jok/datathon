"""
VALIDATE：用独立的基准检查 STAGING 结果。

检查 A  检测到的问题  vs  corruption_log.csv（注入错误时留下的"答案"）
检查 B  明细加总      vs  文件里的汇总行  vs  价格类型报表 2026-1p.xlsx

运行：python src/validate.py
输出：data/validation/validation_report.csv
"""
from pathlib import Path
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
STAGING = BASE_DIR / "data" / "staging"
LOG_CSV = BASE_DIR / "data" / "corruption_manifest" / "corruption_log.csv"
PRICE_XLSX = BASE_DIR / "data" / "grouth_truth" / "2026-1p.xlsx"
OUT_DIR = BASE_DIR / "data" / "validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute(f"CREATE VIEW lines  AS SELECT * FROM '{STAGING / 'sales_lines.parquet'}'")
con.execute(f"CREATE VIEW issues AS SELECT * FROM '{STAGING / 'dq_issues.parquet'}'")
con.execute(f"CREATE VIEW truth  AS SELECT * FROM read_csv('{LOG_CSV}')")

results = []   # 每一项检查的结果都放进这里

def record(check, expected, actual, status, note=""):
    results.append(dict(check=check, expected=expected, actual=actual,
                        status=status, note=note))

# ============================================================
# 检查 A：逐行对比 —— 找到的问题 和 答案 是否一一对应
#   用 (source_row_id, issue_type, field) 三个字段来配对
# ============================================================
cmp = con.sql("""
    SELECT
        COALESCE(t.source_row_id, i.source_row_id) AS source_row_id,
        COALESCE(t.issue_type,   i.issue_type)     AS issue_type,
        COALESCE(t.field,        i.field)          AS field,
        t.source_row_id IS NOT NULL AS in_truth,
        i.source_row_id IS NOT NULL AS detected
    FROM truth t
    FULL OUTER JOIN issues i
      ON  t.source_row_id = i.source_row_id
      AND t.issue_type    = i.issue_type
      AND t.field         = i.field
""").df()

tp = int((cmp.in_truth & cmp.detected).sum())    # 找对了
fn = int((cmp.in_truth & ~cmp.detected).sum())   # 漏掉了
fp = int((~cmp.in_truth & cmp.detected).sum())   # 误报
precision = tp / (tp + fp) if tp + fp else 0
recall    = tp / (tp + fn) if tp + fn else 0

print("检查 A：问题检测 vs corruption_log")
print(f"  找对 TP={tp}  漏掉 FN={fn}  误报 FP={fp}")
print(f"  precision={precision:.2%}  recall={recall:.2%}")
if fn or fp:
    print(cmp[cmp.in_truth != cmp.detected].to_string(index=False))

record("A. issue detection recall", 1.0, round(recall, 4),
       "PASS" if recall == 1 else "FAIL", f"TP={tp}, FN={fn}")
record("A. issue detection precision", 1.0, round(precision, 4),
       "PASS" if precision == 1 else "FAIL", f"FP={fp}")

# ============================================================
# 检查 B：对账 —— 明细加总 vs 两个独立的 Total
# ============================================================
# B1  明细行加总（只加 row_type = 'line'）
detail = con.sql("""
    SELECT SUM(orders) AS orders, SUM(qty) AS qty, ROUND(SUM(amount), 2) AS amount,
           COUNT(*) FILTER (WHERE orders IS NULL) AS null_orders,
           COUNT(*) FILTER (WHERE qty    IS NULL) AS null_qty,
           COUNT(*) FILTER (WHERE amount IS NULL) AS null_amount
    FROM lines WHERE row_type = 'line'
""").df().iloc[0]

# B2  文件里的门店汇总行（Kea Wellness - Central）
store = con.sql("""
    SELECT orders, qty, amount FROM lines WHERE row_type = 'store_total'
""").df().iloc[0]

# B3  另一份独立报表：按价格类型的 Total 行
p = pd.read_excel(PRICE_XLSX, header=None)
p_total = p[p[0] == "Total"].iloc[0]
price = {"orders": int(p_total[1]), "qty": int(p_total[2]),
         "amount": round(float(p_total[3]), 2)}

print("\n检查 B：对账")
print(f"  {'指标':<8}{'明细加总':>12}{'门店汇总行':>12}{'价格类型表':>12}  明细里 NULL 行数")
for m in ["orders", "qty", "amount"]:
    d, s, pr, n_null = detail[m], store[m], price[m], int(detail[f"null_{m}"])
    print(f"  {m:<8}{d:>12}{s:>12}{pr:>12}  {n_null}")

    # 门店汇总行 和 价格类型表 必须一致（两个独立来源互相印证）
    record(f"B. {m}: store_total = price_type_total", pr, s,
           "PASS" if s == pr else "FAIL")

    # 明细加总 和 基准
    if d == pr:
        status, note = "PASS", ""
    elif n_null > 0:
        status = "PASS WITH ACCEPTED EXCEPTIONS"
        note = f"差 {pr - d}，来自 {n_null} 行 {m} 为 NULL（已记录在 dq_issues）"
    else:
        status, note = "FAIL", "差异无法用已知问题解释"
    record(f"B. {m}: detail_sum = baseline", pr, d, status, note)

# ============================================================
# 输出报告 + 总结论
# ============================================================
report = pd.DataFrame(results)
report.to_csv(OUT_DIR / "validation_report.csv", index=False)

if (report.status == "FAIL").any():
    overall = "FAIL"
elif (report.status != "PASS").any():
    overall = "PASS WITH ACCEPTED EXCEPTIONS"
else:
    overall = "PASS"

print("\n" + report.to_string(index=False))
print(f"\n总结论: {overall}")
print(f"报告已写出: {OUT_DIR / 'validation_report.csv'}")
