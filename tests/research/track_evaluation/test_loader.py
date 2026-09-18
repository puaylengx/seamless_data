"""ทดสอบ prepare_for_load (shared MSSQL/BigQuery prep) และ summary fetchers ของ track_evaluation (G4) — ไม่ต่อ DB"""
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

import src.research.track_evaluation.loader as loader_mod
from src.research.track_evaluation.loader import MERGE_KEYS, _for_pyodbc, bq_summary, mssql_summary, prepare_for_load
from src.research.track_evaluation.transformer import coerce_and_clean


def _cleaned(**overrides) -> pd.DataFrame:
    base = {
        "product_code": ["  P-001 "], "rc_meeting": ["RC3"], "publication_month": ["March"],
        "order_num": ["3"], "publication_year": ["2026"], "publication_date": ["2026-03-15"],
        "firstname": ["A"], "lastname": ["B"], "rank": ["Lecturer"], "division": [" "],
        "description": ["d"], "weight": ["1.0"], "quality": ["0.755"], "corresponding": ["yes"],
        "contribution": [None], "score": ["0.3775"], "reward": [None], "title": ["T"], "source": ["J"],
    }
    base.update(overrides)
    return coerce_and_clean(pd.DataFrame(base))


# ── prepare_for_load ──────────────────────────────────────────────────────────

def test_prepare_strips_text_and_blank_becomes_null_keeping_string_dtype():
    out = prepare_for_load(_cleaned())
    assert out["product_code"].iloc[0] == "P-001"
    assert pd.isna(out["division"].iloc[0])
    assert str(out["product_code"].dtype) == "string"       # typed เหมือน BigQuery path เดิม
    print("✅ text strip, ว่าง → null, dtype string คงไว้")


def test_prepare_numeric_and_date_types_are_typed():
    out = prepare_for_load(_cleaned())
    assert str(out["order_num"].dtype) == "Int64" and out["order_num"].iloc[0] == 3
    assert str(out["publication_year"].dtype) == "Int64" and out["publication_year"].iloc[0] == 2026
    assert out["reward"].iloc[0] == 0                       # reward ว่าง → 0 มาจาก coerce_and_clean (PD-2)
    assert pd.isna(out["contribution"].iloc[0])             # float ว่าง → NaN (typed)
    assert out["quality"].iloc[0] == 0.76
    assert out["publication_date"].iloc[0] == date(2026, 3, 15)


def test_prepare_returns_new_frame():
    src = _cleaned()
    snap = src.copy(deep=True)
    prepare_for_load(src)
    pd.testing.assert_frame_equal(src, snap)


def test_for_pyodbc_turns_every_null_into_none_mssql_only():
    out = _for_pyodbc(prepare_for_load(_cleaned()))
    row = out.iloc[0].tolist()
    assert out["division"].iloc[0] is None and out["contribution"].iloc[0] is None
    assert not any(v is not None and pd.isna(v) for v in row)   # ไม่มี NaN/NA เหลือ
    assert out["product_code"].iloc[0] == "P-001" and out["order_num"].iloc[0] == 3
    print("✅ MSSQL path: null ทุกตัว → None, ค่าเท่ากับ prepare_for_load")


def test_load_to_mssql_goes_through_prepare_for_load(monkeypatch):
    """MSSQL path ต้องเรียก prepare_for_load ตัวเดียวกับ BigQuery (หัวใจของ G4) — หยุดก่อนสร้าง engine"""
    calls = []

    def _spy(df):
        calls.append(len(df))
        return df

    monkeypatch.setattr(loader_mod, "prepare_for_load", _spy)

    def _no_engine():
        raise RuntimeError("stop before DB")
    monkeypatch.setattr(loader_mod, "_mssql_engine", _no_engine)

    try:
        loader_mod.load_to_mssql(_cleaned())
    except RuntimeError as e:
        assert "stop before DB" in str(e)
    assert calls == [1]


def test_load_to_bigquery_refuses_without_service_account_key(monkeypatch, tmp_path):
    # G17: ตรวจ config ก่อนสร้าง client — key ไม่พบ → MissingConfigError (เดิม FileNotFoundError) บอก path ที่หา
    from helpers.connect_db.config import MissingConfigError
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(tmp_path / "missing.json"))
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("GCP_DATASET_ID", "d")
    try:
        loader_mod.load_to_bigquery(_cleaned())
        raise AssertionError("ควร raise MissingConfigError")
    except MissingConfigError as e:
        assert "missing.json" in str(e) and "GOOGLE_APPLICATION_CREDENTIALS" in str(e)


# ── summaries via fake engine / client ───────────────────────────────────────

class _FakeConn:
    def __init__(self, rows_by_kind):
        self.rows_by_kind = rows_by_kind
        self.sql = []

    def execute(self, stmt):
        sql = str(stmt)
        self.sql.append(sql)
        rows = self.rows_by_kind["distinct" if "DISTINCT" in sql else "rows"]
        class R:
            def fetchall(self_inner): return rows
        return R()


class _FakeEngine:
    def __init__(self, conn): self.conn = conn
    @contextmanager
    def connect(self):
        yield self.conn


def test_mssql_summary_uses_bracket_quoted_target_and_merge_keys(monkeypatch):
    monkeypatch.setenv("SCHEMA_DEFAULT", "dbo")
    monkeypatch.setenv("TRACK_EVALUATION", "track_evaluation")
    conn = _FakeConn({"rows": [(2026, 5)], "distinct": [(2026, 4)]})
    s = mssql_summary([2026], engine=_FakeEngine(conn))
    assert s.label == "MSSQL" and s.per_year == {2026: 5} and s.distinct_per_year == {2026: 4}
    assert "[dbo].[track_evaluation]" in conn.sql[0]
    assert all(k in conn.sql[1] for k in MERGE_KEYS)
    print("✅ mssql_summary: quote แบบ MSSQL + ใช้ MERGE_KEYS")


class _FakeBQ:
    def __init__(self):
        self.sql = []

    def query(self, sql):
        self.sql.append(sql)
        rows = [{"y": 2026, "d": 4}] if "DISTINCT" in sql else [{"y": 2026, "n": 4}]
        class J:
            def result(self_inner): return rows
        return J()


def test_bq_summary_uses_backtick_prod_table(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proj")
    monkeypatch.setenv("GCP_DATASET_ID", "Research")
    monkeypatch.delenv("GCP_TRACK_EVAL_TABLE_NAME", raising=False)
    bq = _FakeBQ()
    s = bq_summary([2026], client=bq)
    assert s.label == "BigQuery" and s.per_year == {2026: 4}
    assert "`proj.Research.track_evaluation`" in bq.sql[0]
