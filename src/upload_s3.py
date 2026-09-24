"""
AWS-007：把本地 pipeline 的输出上传到 S3（RAW 源文件 + manifest、STAGING / MART Parquet）。

先演练（不连 AWS，不需要权限）：
    python src/upload_s3.py --bucket <bucket> --dry-run
真正上传：
    python src/upload_s3.py --bucket <bucket> --profile datathon-de --region <region>

规则（README 第 4 节）：
  raw/<dataset>/<batch_id>/source.xlsx|csv, manifest.json      不可变
  staging/<dataset>/batch_id=<batch_id>/*.parquet
  mart/<dataset>/candidate/run_id=<run_id>/*.parquet          只传 VALIDATED 的运行
  - 同一个 key 已存在且内容相同 → 跳过；内容不同 → 报错，绝不覆盖
  - 每个文件带 SHA-256 校验和，并要求服务器端加密（SSE-S3）
  - 只对临时网络故障做有限重试（boto3 standard 模式，最多 5 次）
"""
import argparse
import base64
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))


class ImmutableConflict(Exception):
    """S3 上已有同名文件，但内容不同"""


def sha256_b64(path):
    """S3 使用 base64 编码的 SHA-256"""
    return base64.b64encode(hashlib.sha256(Path(path).read_bytes()).digest()).decode()


def validated_runs():
    """从 run_log.csv 找出最终状态是 VALIDATED 的 run_id"""
    log = DATA / "runs" / "run_log.csv"
    if not log.exists():
        return set()
    with open(log) as f:
        return {r["run_id"] for r in csv.DictReader(f) if r["state"] == "VALIDATED"}


def plan_uploads(dataset, include_csv_sources=False):
    """列出要上传的 (本地文件, S3 key)。不连 AWS。"""
    plan = []
    batches = []

    # RAW：原样的源文件 + manifest
    for manifest in sorted((DATA / "raw").glob("*/manifest.json")):
        info = json.loads(manifest.read_text())
        if info.get("source_format", "csv") != "xlsx" and not include_csv_sources:
            continue                      # 默认只传真实 Excel；测试用的脏 CSV 需要显式加参数
        batch = info["batch_id"]
        batches.append(batch)
        for f in sorted(manifest.parent.iterdir()):
            plan.append((f, f"raw/{dataset}/{batch}/{f.name}"))

    # STAGING：只传上面选中的批次
    for batch in batches:
        for f in sorted((DATA / "staging" / f"batch_id={batch}").glob("*.parquet")):
            plan.append((f, f"staging/{dataset}/batch_id={batch}/{f.name}"))

    # MART candidate：只传 VALIDATED 且属于选中批次的运行
    ok_runs = validated_runs()
    for run_dir in sorted((DATA / "mart" / "candidate").glob("run_id=*")):
        run_id = run_dir.name.split("=", 1)[1]
        if run_id not in ok_runs:
            continue
        fact = run_dir / "fact_monthly_sales.parquet"
        if not fact.exists():
            continue
        import duckdb
        run_batches = {r[0] for r in duckdb.sql(
            f"SELECT DISTINCT batch_id FROM '{fact}'").fetchall()}
        if not run_batches & set(batches):
            continue
        for f in sorted(run_dir.glob("*.parquet")):
            plan.append((f, f"mart/{dataset}/candidate/run_id={run_id}/{f.name}"))
    return plan


def upload(plan, bucket, s3, dry_run):
    """逐个上传；返回报告行。"""
    report = []
    for local, key in plan:
        checksum = sha256_b64(local)
        row = {"local_file": str(local.relative_to(DATA.parent)), "s3_uri": f"s3://{bucket}/{key}",
               "size_bytes": local.stat().st_size, "sha256_b64": checksum}
        if dry_run:
            report.append({**row, "status": "DRY_RUN", "encryption": ""})
            continue

        # 已存在？→ 比较校验和
        try:
            head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
            if head.get("ChecksumSHA256") == checksum:
                report.append({**row, "status": "SKIPPED_IDENTICAL",
                               "encryption": head.get("ServerSideEncryption", "")})
                continue
            raise ImmutableConflict(f"{key} 已存在但内容不同，拒绝覆盖")
        except s3.exceptions.ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                raise

        with open(local, "rb") as body:
            s3.put_object(Bucket=bucket, Key=key, Body=body,
                          ChecksumAlgorithm="SHA256", ChecksumSHA256=checksum,
                          ServerSideEncryption="AES256")
        # 上传后再读一次元数据，确认校验和与加密都生效
        head = s3.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
        if head.get("ChecksumSHA256") != checksum:
            raise RuntimeError(f"{key} 上传后校验和不一致")
        report.append({**row, "status": "UPLOADED",
                       "encryption": head.get("ServerSideEncryption", "")})
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bucket", required=True)
    p.add_argument("--dataset", default="monthly_sales")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.add_argument("--dry-run", action="store_true", help="只列出计划，不连接 AWS")
    p.add_argument("--include-csv-sources", action="store_true",
                   help="同时上传 CSV 源（例如测试用的 sales_dirty.csv）")
    args = p.parse_args()

    plan = plan_uploads(args.dataset, args.include_csv_sources)
    if not plan:
        sys.exit("没有可上传的文件：先运行 python src/pipeline.py --source data/grouth_truth/2026-[1-4].xlsx")

    s3 = None
    if not args.dry_run:
        import boto3
        from botocore.config import Config
        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        s3 = session.client("s3", config=Config(retries={"mode": "standard", "max_attempts": 5}))

    report = upload(plan, args.bucket, s3, args.dry_run)

    out = DATA / "runs" / f"upload_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0]))
        w.writeheader()
        w.writerows(report)

    for r in report:
        print(f"{r['status']:<18} {r['size_bytes']:>8}  {r['s3_uri']}")
    counts = {}
    for r in report:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"\n汇总: {counts}")
    print(f"报告: {out.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
