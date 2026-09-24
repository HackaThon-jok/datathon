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

BASE_DIR = Path(__file__).resolve().parents[1]
DATA = BASE_DIR / "data"
RUN_LOG = DATA / "runs" / "run_log.csv"
DEFAULT_SOURCE = DATA / "legacy_dirty" / "sales_dirty.csv"


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


def run_step(script, env_extra):
    """运行 src/ 下的某个脚本；失败就抛出异常"""
    env = {**os.environ, **{k: str(v) for k, v in env_extra.items()}}
    result = subprocess.run([sys.executable, str(BASE_DIR / "src" / script)],
                            env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{script} 失败:\n{result.stdout[-800:]}\n{result.stderr[-800:]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    args = parser.parse_args()
    source = Path(args.source).resolve()

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
        raw_file = raw_dir / "source.csv"
        manifest_file = raw_dir / "manifest.json"

        if raw_file.exists():
            # 不可变：同一批次已经存在，就不再覆盖
            if sha256_of(raw_file) != checksum:
                raise RuntimeError("RAW 快照被改动过！与 batch_id 不一致")
            print(f"    RAW 已存在，跳过复制: {raw_file.relative_to(BASE_DIR)}")
        else:
            raw_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, raw_file)
            row_count = duckdb.sql(
                f"SELECT COUNT(*) FROM read_csv('{raw_file}', all_varchar=true)"
            ).fetchone()[0]
            manifest = {
                "batch_id": batch_id,
                "source_file": source.name,
                "sha256": checksum,
                "row_count": row_count,
                "size_bytes": raw_file.stat().st_size,
                "extracted_at_utc": now(),
                "first_run_id": run_id,
            }
            manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
            print(f"    已写出 RAW 快照和 manifest: {raw_dir.relative_to(BASE_DIR)}")

        # ---------------- TRANSFORMING：STAGING ----------------
        staging_dir = DATA / "staging" / f"batch_id={batch_id}"
        log_state(run_id, batch_id, "TRANSFORMING", str(staging_dir.relative_to(BASE_DIR)))
        run_step("transform.py", {"RAW_CSV": raw_file, "STAGING_DIR": staging_dir})

        # MART 候选版本：每次运行单独一个目录（README 第 4 节 candidate/run_id=...）
        mart_dir = DATA / "mart" / "candidate" / f"run_id={run_id}"
        run_step("mart.py", {"RAW_CSV": raw_file, "STAGING_DIR": staging_dir,
                             "MART_DIR": mart_dir, "BATCH_ID": batch_id, "RUN_ID": run_id})

        # ---------------- VALIDATING ----------------
        validation_dir = DATA / "validation" / f"run_id={run_id}"
        log_state(run_id, batch_id, "VALIDATING", str(validation_dir.relative_to(BASE_DIR)))
        run_step("validate.py", {"STAGING_DIR": staging_dir, "VALIDATION_DIR": validation_dir})
        overall = (validation_dir / "overall.txt").read_text()

        # 发布（PUBLISHED）由 RELEASE-001 负责，这里只给出"可以发布"的结论
        log_state(run_id, batch_id, "VALIDATED", overall)
        print(f"\n✅ run {run_id} 完成，结论: {overall}")

    except Exception as e:
        log_state(run_id, batch_id, "FAILED", str(e).splitlines()[0])
        print(f"\n❌ run {run_id} 失败，详情见 {RUN_LOG.relative_to(BASE_DIR)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
