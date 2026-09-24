"""
1–4 月真实 Excel：每个月都要 VALIDATED，且 MART 金额等于同月价格类型报表的 Total。
"""
import csv
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
MONTH_FILES = sorted((BASE_DIR / "data" / "grouth_truth").glob("2026-[0-9].xlsx"))


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    data = tmp_path_factory.mktemp("months") / "data"
    env = {**os.environ, "DATA_DIR": str(data)}
    subprocess.run([sys.executable, str(BASE_DIR / "src" / "pipeline.py"),
                    "--source", *map(str, MONTH_FILES)],
                   env=env, check=True, capture_output=True)
    return data


def test_four_months_found():
    assert len(MONTH_FILES) == 4


def test_every_month_validated(data_dir):
    with open(data_dir / "runs" / "run_log.csv") as f:
        final = [r["state"] for r in csv.DictReader(f) if r["state"] in ("VALIDATED", "FAILED")]
    assert final == ["VALIDATED"] * 4


@pytest.mark.parametrize("month_file", MONTH_FILES, ids=lambda p: p.stem)
def test_month_amount_matches_price_report(data_dir, month_file):
    price = pd.read_excel(month_file.with_name(month_file.stem + "p.xlsx"), header=None)
    expected = round(float(price[price[0] == "Total"].iloc[0, 3]), 2)
    month = pd.read_excel(month_file, header=None, nrows=1).iloc[0, 1]
    actual = duckdb.sql(f"""
        SELECT ROUND(SUM(amount), 2)
        FROM '{data_dir}/mart/candidate/*/fact_monthly_sales.parquet'
        WHERE strftime(report_month, '%B %Y') = '{month}'
    """).fetchone()[0]
    assert actual == expected
