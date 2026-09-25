"""
把本地 pipeline 的 RAW 批次装进 Snowflake（DATATHON_DEV.RAW）。

先演练（不连接 Snowflake）：
    python src/load_snowflake.py --dry-run
真正加载：
    python src/load_snowflake.py

连接信息从 .env 读取（.env 已被 git 忽略，绝不提交）：
    SNOWFLAKE_ACCOUNT=lnngkqb-qs06919
    SNOWFLAKE_USER=...
    SNOWFLAKE_PASSWORD=...
    SNOWFLAKE_ROLE=DATATHON_LOADER
    SNOWFLAKE_WAREHOUSE=DATATHON_WH
    SNOWFLAKE_AUTHENTICATOR=          # 可选，例如账号要求 MFA 时

设计：
  - 不动队友 SQL 读取的 RAW.SALES_RAW
  - 所有批次追加进 RAW.SALES_RAW_BATCHES（原 9 列 + BATCH_ID / SOURCE_FILE / LOADED_AT）
  - 每个批次在 RAW.LOAD_MANIFEST 记一行：SHA-256、预期行数、实际行数、状态
  - 同一个 batch_id 已经 LOADED → 跳过（重跑不重复）
  - 加载后核对行数；对不上 → 记为 FAILED 并退出
  - 不在日志里打印任何源数据内容
"""
import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB, SCHEMA = "DATATHON_DEV", "RAW"
STAGE = f"{DB}.{SCHEMA}.LOAD_STAGE"
TARGET = f"{DB}.{SCHEMA}.SALES_RAW_BATCHES"
MANIFEST = f"{DB}.{SCHEMA}.LOAD_MANIFEST"
RAW_COLS = [f"RAW_COL_{i}" for i in range(1, 8)] + ["SOURCE_ROW_ID", "INGEST_ROW_ID"]

SETUP_SQL = [
    f"CREATE STAGE IF NOT EXISTS {STAGE}",
    f"""CREATE TABLE IF NOT EXISTS {TARGET} (
        {", ".join(c + " VARCHAR" for c in RAW_COLS)},
        BATCH_ID VARCHAR, SOURCE_FILE VARCHAR, LOADED_AT TIMESTAMP_LTZ)""",
    f"""CREATE TABLE IF NOT EXISTS {MANIFEST} (
        BATCH_ID VARCHAR, SOURCE_FILE VARCHAR, SOURCE_FORMAT VARCHAR, SHA256 VARCHAR,
        EXPECTED_ROWS NUMBER, LOADED_ROWS NUMBER, STATUS VARCHAR,
        LOADED_BY VARCHAR, LOADED_AT TIMESTAMP_LTZ)""",
]


def validated_batches():
    """从 run_log.csv 找出至少有一次 VALIDATED 运行的 batch_id"""
    import csv
    log = DATA / "runs" / "run_log.csv"
    if not log.exists():
        return set()
    with open(log) as f:
        return {r["batch_id"] for r in csv.DictReader(f) if r["state"] == "VALIDATED"}


def local_batches(only=None):
    """读取 data/raw/<batch_id>/manifest.json；只返回验证通过的批次"""
    ok = validated_batches()
    out = []
    for m in sorted((DATA / "raw").glob("*/manifest.json")):
        info = json.loads(m.read_text())
        if info["batch_id"] not in ok:
            continue                      # 失败的批次（例如格式错误的文件）不加载
        if only and info["batch_id"] not in only:
            continue
        info["csv"] = m.parent / "source.csv"
        out.append(info)
    return out


def load_sql(b):
    """一个批次的 PUT + COPY INTO 语句"""
    stage_path = f"@{STAGE}/{b['batch_id']}/"
    put = (f"PUT 'file://{b['csv'].resolve()}' {stage_path} "
           f"AUTO_COMPRESS=TRUE OVERWRITE=FALSE")
    select = ", ".join(f"${i}" for i in range(1, 10))
    copy = f"""COPY INTO {TARGET} ({", ".join(RAW_COLS)}, BATCH_ID, SOURCE_FILE, LOADED_AT)
        FROM (SELECT {select}, '{b['batch_id']}', '{b['source_file']}', CURRENT_TIMESTAMP()
              FROM {stage_path})
        FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                       EMPTY_FIELD_AS_NULL = TRUE)
        ON_ERROR = ABORT_STATEMENT"""
    return put, copy


def connect():
    import snowflake.connector
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    need = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [k for k in need if not os.getenv(k)]
    if missing:
        sys.exit(f".env 缺少: {', '.join(missing)}")
    kw = dict(account=os.getenv("SNOWFLAKE_ACCOUNT"), user=os.getenv("SNOWFLAKE_USER"),
              password=os.getenv("SNOWFLAKE_PASSWORD"),
              role=os.getenv("SNOWFLAKE_ROLE", "DATATHON_LOADER"),
              warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "DATATHON_WH"),
              database=DB, schema=SCHEMA)
    if os.getenv("SNOWFLAKE_AUTHENTICATOR"):
        kw["authenticator"] = os.getenv("SNOWFLAKE_AUTHENTICATOR")
    return snowflake.connector.connect(**kw)


def run(cur, batches):
    """真正执行；返回每个批次的结果"""
    for sql in SETUP_SQL:
        cur.execute(sql)
    results = []
    for b in batches:
        bid = b["batch_id"]
        cur.execute(f"SELECT COUNT(*) FROM {MANIFEST} WHERE BATCH_ID = %s AND STATUS = 'LOADED'",
                    (bid,))
        if cur.fetchone()[0] > 0:
            results.append((bid, "SKIPPED_ALREADY_LOADED", None))
            continue

        put, copy = load_sql(b)
        cur.execute(put)
        cur.execute(copy)
        cur.execute(f"SELECT COUNT(*) FROM {TARGET} WHERE BATCH_ID = %s", (bid,))
        loaded = cur.fetchone()[0]
        status = "LOADED" if loaded == b["row_count"] else "FAILED"
        cur.execute(f"""INSERT INTO {MANIFEST}
            SELECT %s, %s, %s, %s, %s, %s, %s, CURRENT_USER(), CURRENT_TIMESTAMP()""",
                    (bid, b["source_file"], b.get("source_format", "csv"), b["sha256"],
                     b["row_count"], loaded, status))
        results.append((bid, status, loaded))
        if status == "FAILED":
            break
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="只打印要执行的 SQL，不连接 Snowflake")
    p.add_argument("--batch", nargs="*", help="只加载这些 batch_id（默认全部）")
    args = p.parse_args()

    batches = local_batches(args.batch)
    if not batches:
        sys.exit("没有本地批次：先运行 python src/pipeline.py --source data/grouth_truth/2026-[1-4].xlsx")

    if args.dry_run:
        for sql in SETUP_SQL:
            print(sql.split("(")[0].strip() + " …")
        for b in batches:
            put, copy = load_sql(b)
            print(f"\n-- {b['batch_id']}  {b['source_file']}  预期 {b['row_count']} 行")
            print(put)
            print(copy.splitlines()[0] + " …")
        print(f"\n共 {len(batches)} 个批次（DRY RUN，未连接 Snowflake）")
        return

    conn = connect()
    try:
        results = run(conn.cursor(), batches)
    finally:
        conn.close()
    for bid, status, n in results:
        print(f"{status:<24} {bid}  {'' if n is None else f'{n} 行'}")
    if any(s == "FAILED" for _, s, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
