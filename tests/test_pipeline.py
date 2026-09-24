"""
自动测试：Schema、必填字段、行数、KPI、重跑幂等性（README 第 7 节）。

运行：python -m pytest -v
每个测试都在临时文件夹里重新跑一遍，不会碰你 data/ 下的真实输出。
"""
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE = BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv"

EXPECTED = {             # 独立基准：来自 2026-1p.xlsx 的 Total 行
    "amount": 89312.44,
    "orders": 542,
    "qty": 2395,
}


def run(script, **env):
    full_env = {**os.environ, **{k: str(v) for k, v in env.items()}}
    subprocess.run([sys.executable, str(BASE_DIR / "src" / script)],
                   env=full_env, check=True, capture_output=True)


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    """在临时目录跑 transform + mart，返回输出目录"""
    tmp = tmp_path_factory.mktemp("run")
    staging, mart = tmp / "staging", tmp / "mart"
    run("transform.py", RAW_CSV=SOURCE, STAGING_DIR=staging)
    run("mart.py", RAW_CSV=SOURCE, STAGING_DIR=staging, MART_DIR=mart,
        BATCH_ID="test", RUN_ID="test")
    return {"staging": staging, "mart": mart}


def q(sql):
    return duckdb.sql(sql).fetchall()


# ---------------- Schema ----------------
def test_fact_schema(out):
    cols = [c[0] for c in duckdb.sql(
        f"DESCRIBE SELECT * FROM '{out['mart']}/fact_monthly_sales.parquet'").fetchall()]
    for required in ["report_month", "item_code", "line_type", "orders", "qty",
                     "amount", "has_dq_issue", "batch_id", "run_id"]:
        assert required in cols, f"缺少列 {required}"


# ---------------- 必填字段 ----------------
def test_required_fields_not_null(out):
    n = q(f"""SELECT COUNT(*) FROM '{out['mart']}/fact_monthly_sales.parquet'
              WHERE item_code IS NULL OR item_code = '' OR line_type = 'unknown'
                 OR report_month IS NULL""")[0][0]
    assert n == 0


def test_product_key_unique(out):
    total, distinct = q(f"""SELECT COUNT(*), COUNT(DISTINCT item_code)
                            FROM '{out['mart']}/dim_product.parquet'""")[0]
    assert total == distinct


# ---------------- 行数 ----------------
def test_row_counts(out):
    assert q(f"SELECT COUNT(*) FROM '{out['mart']}/fact_monthly_sales.parquet'")[0][0] == 362
    assert q(f"SELECT COUNT(*) FROM '{out['staging']}/dq_issues.parquet'")[0][0] == 24


# ---------------- KPI ----------------
def test_amount_matches_baseline(out):
    amount = q(f"SELECT ROUND(SUM(amount), 2) FROM '{out['mart']}/fact_monthly_sales.parquet'")[0][0]
    assert amount == EXPECTED["amount"]


def test_report_total_matches_baseline(out):
    row = q(f"""SELECT orders, qty, amount FROM '{out['mart']}/report_totals.parquet'
                WHERE row_type = 'store_total'""")[0]
    assert row == (EXPECTED["orders"], EXPECTED["qty"], EXPECTED["amount"])


# ---------------- 重跑幂等 ----------------
def test_rerun_is_idempotent(out):
    before = q(f"SELECT COUNT(*) FROM '{out['staging']}/sales_lines.parquet'")[0][0]
    run("transform.py", RAW_CSV=SOURCE, STAGING_DIR=out["staging"])
    after = q(f"SELECT COUNT(*) FROM '{out['staging']}/sales_lines.parquet'")[0][0]
    assert before == after
