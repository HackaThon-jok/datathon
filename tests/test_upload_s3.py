"""
AWS-007 上传逻辑的测试：用 moto 模拟 S3，不需要真实 AWS 账号或网络。
"""
import os
import subprocess
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
BUCKET = "test-bucket"


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    """在临时目录跑一遍 1–2 月，产生要上传的文件"""
    data = tmp_path_factory.mktemp("upload") / "data"
    files = [str(BASE_DIR / "data" / "grouth_truth" / f"2026-{m}.xlsx") for m in (1, 2)]
    subprocess.run([sys.executable, str(BASE_DIR / "src" / "pipeline.py"), "--source", *files],
                   env={**os.environ, "DATA_DIR": str(data)}, check=True, capture_output=True)
    return data


@pytest.fixture
def mod(data_dir, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    import importlib
    import upload_s3
    return importlib.reload(upload_s3)


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def test_plan_follows_readme_layout(mod):
    keys = [k for _, k in mod.plan_uploads("monthly_sales")]
    assert any(k.startswith("raw/monthly_sales/b_") and k.endswith("/manifest.json") for k in keys)
    assert any(k.startswith("raw/monthly_sales/b_") and k.endswith("/source.xlsx") for k in keys)
    assert any(k.startswith("staging/monthly_sales/batch_id=b_") for k in keys)
    assert any(k.startswith("mart/monthly_sales/candidate/run_id=") for k in keys)
    assert not any("published" in k for k in keys)


def test_dry_run_writes_nothing(mod, s3):
    report = mod.upload(mod.plan_uploads("monthly_sales"), BUCKET, s3, dry_run=True)
    assert {r["status"] for r in report} == {"DRY_RUN"}
    assert s3.list_objects_v2(Bucket=BUCKET).get("KeyCount", 0) == 0


def test_upload_then_rerun_is_idempotent(mod, s3):
    plan = mod.plan_uploads("monthly_sales")
    first = mod.upload(plan, BUCKET, s3, dry_run=False)
    assert {r["status"] for r in first} == {"UPLOADED"}
    assert {r["encryption"] for r in first} == {"AES256"}
    assert s3.list_objects_v2(Bucket=BUCKET)["KeyCount"] == len(plan)

    second = mod.upload(plan, BUCKET, s3, dry_run=False)
    assert {r["status"] for r in second} == {"SKIPPED_IDENTICAL"}
    assert s3.list_objects_v2(Bucket=BUCKET)["KeyCount"] == len(plan)


def test_never_overwrites_different_content(mod, s3):
    plan = mod.plan_uploads("monthly_sales")
    local, key = plan[0]
    s3.put_object(Bucket=BUCKET, Key=key, Body=b"someone else's content",
                  ChecksumAlgorithm="SHA256")
    with pytest.raises(mod.ImmutableConflict):
        mod.upload([(local, key)], BUCKET, s3, dry_run=False)
    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    assert body == b"someone else's content"
