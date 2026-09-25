"""
Snowflake 加载逻辑的测试：用一个"假的" cursor 记录 SQL，不需要真实 Snowflake。
检查：会建表/stage、每批 PUT + COPY、已加载的批次会跳过、行数不对会 FAILED、只加载验证通过的批次。
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
import load_snowflake as ls  # noqa: E402


class FakeCursor:
    def __init__(self, already_loaded=(), loaded_rows=None):
        self.sql = []
        self.already_loaded = set(already_loaded)
        self.loaded_rows = loaded_rows or {}
        self._next = None

    def execute(self, sql, params=None):
        self.sql.append(sql)
        if "FROM DATATHON_DEV.RAW.LOAD_MANIFEST WHERE BATCH_ID" in sql:
            self._next = (1 if params[0] in self.already_loaded else 0,)
        elif "FROM DATATHON_DEV.RAW.SALES_RAW_BATCHES WHERE BATCH_ID" in sql:
            self._next = (self.loaded_rows.get(params[0], 0),)

    def fetchone(self):
        return self._next


def batch(bid="b_test", rows=10):
    return {"batch_id": bid, "source_file": "x.xlsx", "source_format": "xlsx",
            "sha256": "abc", "row_count": rows, "csv": Path("/tmp/x/source.csv")}


def test_setup_then_put_and_copy():
    cur = FakeCursor(loaded_rows={"b_test": 10})
    res = ls.run(cur, [batch()])
    assert res == [("b_test", "LOADED", 10)]
    joined = "\n".join(cur.sql)
    assert "CREATE STAGE IF NOT EXISTS DATATHON_DEV.RAW.LOAD_STAGE" in joined
    # 不写死 /tmp：Mac 上 /tmp 会被解析成 /private/tmp
    put = next(x for x in cur.sql if x.startswith("PUT"))
    assert put.startswith("PUT 'file:///") and "/x/source.csv' @DATATHON_DEV.RAW.LOAD_STAGE/b_test/" in put
    assert "COPY INTO DATATHON_DEV.RAW.SALES_RAW_BATCHES" in joined
    assert "SKIP_HEADER = 1" in joined


def test_never_touches_team_table():
    cur = FakeCursor(loaded_rows={"b_test": 10})
    ls.run(cur, [batch()])
    assert not any("RAW.SALES_RAW " in s or s.rstrip().endswith("RAW.SALES_RAW") for s in cur.sql)
    assert not any(s.lstrip().upper().startswith(("DROP", "DELETE", "TRUNCATE")) for s in cur.sql)


def test_already_loaded_batch_is_skipped():
    cur = FakeCursor(already_loaded={"b_test"})
    res = ls.run(cur, [batch()])
    assert res == [("b_test", "SKIPPED_ALREADY_LOADED", None)]
    assert not any(s.startswith("PUT") or "COPY INTO" in s for s in cur.sql)


def test_row_count_mismatch_fails_and_stops():
    cur = FakeCursor(loaded_rows={"b_1": 9, "b_2": 10})
    res = ls.run(cur, [batch("b_1", 10), batch("b_2", 10)])
    assert res == [("b_1", "FAILED", 9)]


def test_manifest_row_recorded():
    cur = FakeCursor(loaded_rows={"b_test": 10})
    ls.run(cur, [batch()])
    assert any(s.lstrip().startswith("INSERT INTO DATATHON_DEV.RAW.LOAD_MANIFEST") for s in cur.sql)


def test_only_validated_batches_are_loaded(tmp_path, monkeypatch):
    import importlib
    import json
    data = tmp_path / "data"
    for bid in ("b_good", "b_bad"):
        d = data / "raw" / bid
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(
            {"batch_id": bid, "source_file": f"{bid}.csv", "sha256": "x", "row_count": 1}))
    (data / "runs").mkdir()
    (data / "runs" / "run_log.csv").write_text(
        "run_id,batch_id,state,timestamp_utc,detail\n"
        "r1,b_good,VALIDATED,t,PASS\n"
        "r2,b_bad,FAILED,t,error\n")
    monkeypatch.setenv("DATA_DIR", str(data))
    mod = importlib.reload(ls)
    assert [b["batch_id"] for b in mod.local_batches()] == ["b_good"]
