"""ทดสอบ ALLOW_REPLACE guard และ default insert mode ของ zeal_data loader (G2) — ไม่ต่อ DB จริง"""
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[3]))

import src.aditayathorn.zeal_data.ingest.loader as loader_mod
from src.aditayathorn.zeal_data.ingest.loader import (
    ensure_replace_allowed,
    load_all,
    replace_allowed,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def no_db(monkeypatch):
    """ถ้า loader พยายามเปิด engine/SSH tunnel ให้ test fail ทันที"""
    @contextmanager
    def _boom(*_a, **_k):
        raise AssertionError("ห้ามเปิด DB connection ใน test นี้")
        yield  # pragma: no cover
    monkeypatch.setattr(loader_mod, "_engine_session", _boom)


@pytest.fixture
def base_env(monkeypatch):
    monkeypatch.setenv("ZEAL_DB_NAME", "zeal_test")
    monkeypatch.delenv("ZEAL_INSERT_MODE", raising=False)
    monkeypatch.delenv("ALLOW_REPLACE", raising=False)


@pytest.fixture
def captured_to_sql(monkeypatch):
    """แทน DataFrame.to_sql เพื่อดูว่า loader ส่ง if_exists อะไร โดยไม่แตะ DB"""
    calls = []

    def _fake_to_sql(self, **kwargs):
        calls.append(kwargs)

    @contextmanager
    def _fake_engine(_db):
        yield object()

    monkeypatch.setattr(pd.DataFrame, "to_sql", _fake_to_sql)
    monkeypatch.setattr(loader_mod, "_engine_session", _fake_engine)
    return calls


def _tables() -> dict[str, pd.DataFrame]:
    return {"Customer": pd.DataFrame({"id": [1]})}


# ── replace_allowed ───────────────────────────────────────────────────────────

def test_replace_allowed_default_false(base_env):
    assert replace_allowed() is False


@pytest.mark.parametrize("value", ["false", "0", "yes", ""])
def test_replace_allowed_rejects_non_true(monkeypatch, value):
    monkeypatch.setenv("ALLOW_REPLACE", value)
    assert replace_allowed() is False


@pytest.mark.parametrize("value", ["true", "TRUE", " True "])
def test_replace_allowed_accepts_true(monkeypatch, value):
    monkeypatch.setenv("ALLOW_REPLACE", value)
    assert replace_allowed() is True


def test_ensure_replace_allowed_message(base_env):
    with pytest.raises(RuntimeError) as exc:
        ensure_replace_allowed("zeal_test.public.*")
    assert "zeal_test.public.*" in str(exc.value)
    assert "ALLOW_REPLACE" in str(exc.value)


# ── load_all ──────────────────────────────────────────────────────────────────

def test_default_insert_mode_is_append(base_env, captured_to_sql):
    load_all(_tables())
    assert len(captured_to_sql) == 1
    assert captured_to_sql[0]["if_exists"] == "append"
    print("✅ ZEAL_INSERT_MODE ไม่ตั้ง → append")


def test_replace_blocked_before_engine(base_env, no_db, monkeypatch):
    monkeypatch.setenv("ZEAL_INSERT_MODE", "replace")
    with pytest.raises(RuntimeError, match="ALLOW_REPLACE"):
        load_all(_tables())
    print("✅ replace ถูกบล็อกก่อนเปิด engine")


def test_replace_blocked_when_flag_false(base_env, no_db, monkeypatch):
    monkeypatch.setenv("ZEAL_INSERT_MODE", "replace")
    monkeypatch.setenv("ALLOW_REPLACE", "false")
    with pytest.raises(RuntimeError, match="ALLOW_REPLACE"):
        load_all(_tables())


def test_replace_passes_guard_when_allowed(base_env, captured_to_sql, monkeypatch):
    monkeypatch.setenv("ZEAL_INSERT_MODE", "replace")
    monkeypatch.setenv("ALLOW_REPLACE", "true")
    load_all(_tables())
    assert captured_to_sql[0]["if_exists"] == "replace"
    print("✅ ALLOW_REPLACE=true → replace ผ่าน")


def test_append_not_affected_by_guard(base_env, captured_to_sql, monkeypatch):
    monkeypatch.setenv("ZEAL_INSERT_MODE", "append")
    load_all(_tables())
    assert captured_to_sql[0]["if_exists"] == "append"


def test_invalid_mode_still_value_error(base_env, no_db, monkeypatch):
    monkeypatch.setenv("ZEAL_INSERT_MODE", "upsert")
    with pytest.raises(ValueError, match="ZEAL_INSERT_MODE"):
        load_all(_tables())


def test_missing_db_name_checked_first(no_db, monkeypatch):
    monkeypatch.delenv("ZEAL_DB_NAME", raising=False)
    with pytest.raises(ValueError, match="ZEAL_DB_NAME"):
        load_all(_tables())


def test_table_name_sanitized_in_to_sql(base_env, captured_to_sql):
    load_all({"Order Detail-2024": pd.DataFrame({"a": [1]})})
    assert captured_to_sql[0]["name"] == "order_detail_2024"
