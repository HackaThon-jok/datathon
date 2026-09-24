"""
失败路径测试：格式错误或缺失的源文件必须得到 FAILED，而不是悄悄通过。

每个测试都用临时的 DATA_DIR，不会碰你 data/ 下的真实输出。
"""
import csv
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def run_pipeline(tmp_path, source):
    env = {**os.environ, "DATA_DIR": str(tmp_path / "data")}
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "src" / "pipeline.py"), "--source", str(source)],
        env=env, capture_output=True, text=True)
    with open(tmp_path / "data" / "runs" / "run_log.csv") as f:
        states = [row["state"] for row in csv.DictReader(f)]
    return result.returncode, states


def test_missing_file_fails(tmp_path):
    code, states = run_pipeline(tmp_path, tmp_path / "does_not_exist.csv")
    assert code == 1
    assert states[-1] == "FAILED"


def test_wrong_columns_fails(tmp_path):
    bad = tmp_path / "wrong_columns.csv"
    bad.write_text("name,price\nfish oil,12.5\nhoney,30\n")
    code, states = run_pipeline(tmp_path, bad)
    assert code == 1
    assert states[-1] == "FAILED"


def test_empty_file_fails(tmp_path):
    bad = tmp_path / "empty.csv"
    bad.write_text("")
    code, states = run_pipeline(tmp_path, bad)
    assert code == 1
    assert states[-1] == "FAILED"


def test_good_file_passes_and_writes_lineage(tmp_path):
    good = BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv"
    code, states = run_pipeline(tmp_path, good)
    assert code == 0
    assert states[-1] == "VALIDATED"
    lineage = list((tmp_path / "data" / "validation").glob("run_id=*/row_lineage.csv"))
    assert len(lineage) == 1
