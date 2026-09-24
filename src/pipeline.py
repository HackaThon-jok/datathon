"""
一条命令跑完本地 pipeline：RAW → STAGING → VALIDATE

运行：python src/pipeline.py
      python src/pipeline.py --source 其他文件.csv

每次运行：
  - 生成新的 run_id（每次都不同）
  - batch_id 由源文件内容的 SHA-256 决定（同一个文件 = 同一个 batch）
  - 每个状态变化都追加一行到 data/runs/run_log.csv（失败证据永不删除）

输出位置：
  data/raw/<batch_id>/source.csv + manifest.json        不可变，已存在就不再覆盖
  data/staging/batch_id=<batch_id>/*.parquet            同一批次重跑 = 覆盖，不会翻倍
  data/validation/run_id=<run_id>/validation_report.csv 每次运行单独保存
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from extract import xlsx_to_raw_csv

BASE_DIR = Path(__file__).resolve().parents[1]
# 输出目录；测试时可以用环境变量 DATA_DIR 指向临时文件夹
DATA = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
RUN_LOG = DATA / "runs" / "run_log.csv"
DEFAULT_SOURCE = BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv"
DEFAULT_TRUTH_LOG = BASE_DIR / "data" / "corruption_manifest" / "corruption_log.csv"
BASELINE_DIR = BASE_DIR / "data" / "grouth_truth"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def log_state(run_id, batch_id, state, detail=""):
    """追加一行到 run_log.csv —— 只追加，从不修改旧记录"""
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not RUN_LOG.exists()
    with open(RUN_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["run_id", "batch_id", "state", "timestamp_utc", "detail"])
        w.writerow([run_id, batch_id, state, now(), detail])
    print(f"[{state:<12}] {detail}")


def row_lineage(raw_file, staging_dir, mart_dir, out_file):
    """源文件 → STAGING → MART 每一步的行数，并检查能否对上"""
    con = duckdb.connect()
    one = lambda sql: con.execute(sql).fetchone()[0]
    source = one(f"SELECT COUNT(*) FROM read_csv('{raw_file}', all_varchar=true)")
    header = one(f"SELECT COUNT(*) FROM read_csv('{raw_file}', all_varchar=true) "
                 "WHERE CAST(source_row_id AS INT) <= 2")
    dups = one(f"SELECT COUNT(*) FROM '{staging_dir}/dq_issues.parquet' "
               "WHERE issue_type = 'duplicate_row'")
    staging = one(f"SELECT COUNT(*) FROM '{staging_dir}/sales_lines.parquet'")
    fact = one(f"SELECT COUNT(*) FROM '{mart_dir}/fact_monthly_sales.parquet'")
    totals = one(f"SELECT COUNT(*) FROM '{mart_dir}/report_totals.parquet'")

    rows = [
        ("1 source file (RAW)", source, ""),
        ("2 - header rows", -header, "report layout, not data"),
        ("3 - duplicate rows", -dups, "logged in dq_issues"),
        ("4 = STAGING sales_lines", staging, "expected = 1 + 2 + 3"),
        ("5 MART fact_monthly_sales", fact, "item lines"),
        ("6 MART report_totals", totals, "store total + grand total"),
    ]
    with open(out_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "rows", "note"])
        w.writerows(rows)
    for step, n, note in rows:
        print(f"    {step:<28}{n:>6}  {note}")

    if source - header - dups != staging:
        raise RuntimeError(f"行数对不上: {source} - {header} - {dups} != {staging}")
    if fact + totals != staging:
        raise RuntimeError(f"行数对不上: MART {fact} + {totals} != STAGING {staging}")


def run_step(script, env_extra):
    """运行 src/ 下的某个脚本；失败就抛出异常"""
    env = {**os.environ, **{k: str(v) for k, v in env_extra.items()}}
    result = subprocess.run([sys.executable, str(BASE_DIR / "src" / script)],
                            env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{script} 失败:\n{result.stdout[-800:]}\n{result.stderr[-800:]}")
    return result.stdout


def find_price_report(raw_csv):
    """按报表月份（第一行的 "February 2026"）找到同月的价格类型报表 *p.xlsx"""
    month = duckdb.execute(
        "SELECT raw_col_2 FROM read_csv(?, all_varchar = true) WHERE source_row_id = '1'",
        [str(raw_csv)]).fetchone()[0]
    for f in sorted(BASELINE_DIR.glob("*p.xlsx")):
        if pd.read_excel(f, header=None, nrows=1).iloc[0, 1] == month:
            return month, f
    return month, None


def run_one(source, truth_log):
    """处理一个源文件（CSV 或 Excel）。成功返回 True，失败返回 False。"""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    batch_id = "unknown"
    log_state(run_id, batch_id, "PENDING", f"source={source.name}")

    try:
        # ---------------- INGESTING：RAW + manifest ----------------
        if not source.is_file():
            raise FileNotFoundError(f"找不到源文件: {source}")
        checksum = sha256_of(source)
        batch_id = "b_" + checksum[:12]
        log_state(run_id, batch_id, "INGESTING", f"sha256={checksum[:12]}…")

        raw_dir = DATA / "raw" / batch_id
        original = raw_dir / f"source{source.suffix.lower()}"   # 原样保存的源文件
        raw_file = raw_dir / "source.csv"                        # pipeline 读取的 RAW CSV
        manifest_file = raw_dir / "manifest.json"

        if original.exists():
            # 不可变：同一批次已经存在，就不再覆盖
            if sha256_of(original) != checksum:
                raise RuntimeError("RAW 快照被改动过！与 batch_id 不一致")
            print(f"    RAW 已存在，跳过: {raw_dir.relative_to(DATA.parent)}")
        else:
            raw_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, original)
            if source.suffix.lower() == ".xlsx":
                xlsx_to_raw_csv(original, raw_file)              # Excel → RAW CSV（不改内容）
            row_count = duckdb.sql(
                f"SELECT COUNT(*) FROM read_csv('{raw_file}', all_varchar=true)"
            ).fetchone()[0]
            manifest = {
                "batch_id": batch_id,
                "source_file": source.name,
                "source_format": source.suffix.lower().lstrip("."),
                "sha256": checksum,
                "raw_csv_sha256": sha256_of(raw_file),
                "row_count": row_count,
                "size_bytes": original.stat().st_size,
                "extracted_at_utc": now(),
                "first_run_id": run_id,
            }
            manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
            print(f"    已写出 RAW 快照和 manifest: {raw_dir.relative_to(DATA.parent)}")

        # ---------------- TRANSFORMING：STAGING + MART ----------------
        staging_dir = DATA / "staging" / f"batch_id={batch_id}"
        log_state(run_id, batch_id, "TRANSFORMING", str(staging_dir.relative_to(DATA.parent)))
        run_step("transform.py", {"RAW_CSV": raw_file, "STAGING_DIR": staging_dir})

        # MART 候选版本：每次运行单独一个目录（README 第 4 节 candidate/run_id=...）
        mart_dir = DATA / "mart" / "candidate" / f"run_id={run_id}"
        run_step("mart.py", {"RAW_CSV": raw_file, "STAGING_DIR": staging_dir,
                             "MART_DIR": mart_dir, "BATCH_ID": batch_id, "RUN_ID": run_id})

        # ---------------- VALIDATING ----------------
        month, price_xlsx = find_price_report(raw_file)
        validation_dir = DATA / "validation" / f"run_id={run_id}"
        log_state(run_id, batch_id, "VALIDATING",
                  f"{month}; baseline={price_xlsx.name if price_xlsx else 'MISSING'}")
        run_step("validate.py", {"STAGING_DIR": staging_dir, "VALIDATION_DIR": validation_dir,
                                 "PRICE_XLSX": price_xlsx or "",
                                 "TRUTH_LOG": truth_log or ""})
        overall = (validation_dir / "overall.txt").read_text()
        row_lineage(raw_file, staging_dir, mart_dir, validation_dir / "row_lineage.csv")

        # 发布（PUBLISHED）由 RELEASE-001 负责，这里只给出"可以发布"的结论
        log_state(run_id, batch_id, "VALIDATED", overall)
        print(f"✅ run {run_id} 完成，结论: {overall}\n")
        return True

    except Exception as e:
        # 记录哪一步失败 + 具体的错误原因
        msg = [x.strip() for x in str(e).splitlines() if x.strip()]
        reason = next((x for x in reversed(msg) if "Error" in x), msg[-1])
        log_state(run_id, batch_id, "FAILED", " | ".join(dict.fromkeys([msg[0], reason])))
        print(f"❌ run {run_id} 失败，详情见 {RUN_LOG.relative_to(DATA.parent)}\n")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", nargs="+", default=[str(DEFAULT_SOURCE)],
                        help="一个或多个源文件（.csv 或 .xlsx）")
    parser.add_argument("--truth-log", default=None,
                        help="注入错误的答案文件；默认只对 sales_dirty.csv 使用")
    args = parser.parse_args()

    results = []
    for src in args.source:
        source = Path(src).resolve()
        truth = args.truth_log or (str(DEFAULT_TRUTH_LOG) if source == DEFAULT_SOURCE else None)
        results.append((source.name, run_one(source, truth)))

    print("汇总:")
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    sys.exit(0 if all(ok for _, ok in results) else 1)


if __name__ == "__main__":
    main()
