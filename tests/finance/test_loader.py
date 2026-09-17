"""ทดสอบว่า ErpLoader / MasterLoader เรียก guard กลาง (helpers.replace_guard) ถูกจุด (G2) — ไม่ต่อ DB จริง

พฤติกรรมของ guard เอง (ค่าไหนผ่าน/ไม่ผ่าน) ทดสอบที่ tests/helpers/test_replace_guard.py"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

import src.finance.loader as erp_loader_mod
import src.finance.master.loader as master_loader_mod
from src.finance.loader import ErpLoader
from src.finance.master.loader import MasterLoader


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture
def no_db(monkeypatch):
    """ถ้า loader พยายามเปิด connection ให้ test fail ทันที"""
    def _boom(*_a, **_k):
        raise AssertionError("ห้ามเปิด DB connection ใน test นี้")
    monkeypatch.setattr(erp_loader_mod, "connect_to_db", _boom)
    monkeypatch.setattr(master_loader_mod, "connect_to_db", _boom)


@pytest.fixture
def replace_blocked(monkeypatch):
    monkeypatch.delenv("ALLOW_REPLACE", raising=False)


def _erp_df() -> pd.DataFrame:
    return pd.DataFrame({"doc_no": [1], "gl_id": ["5"], "amount": [1.0]})


def _master_df() -> pd.DataFrame:
    return pd.DataFrame({"fund_id": ["F1"], "fund_description": ["x"], "status": ["active"]})


# ── ErpLoader ─────────────────────────────────────────────────────────────────

def test_erp_replace_blocked_before_touching_db(no_db, replace_blocked):
    with pytest.raises(RuntimeError, match="ALLOW_REPLACE"):
        ErpLoader().load(_erp_df(), mode="replace")
    print("✅ ErpLoader replace ถูกบล็อกก่อนเปิด connection")


def test_erp_replace_blocked_when_flag_false(no_db, monkeypatch):
    monkeypatch.setenv("ALLOW_REPLACE", "false")
    with pytest.raises(RuntimeError, match="ALLOW_REPLACE"):
        ErpLoader().load(_erp_df(), mode="replace")


def test_erp_append_not_affected_by_guard(no_db, replace_blocked):
    # append ต้องผ่าน guard ไปถึงขั้นเปิด connection (ซึ่ง fixture ทำให้ fail แบบ AssertionError)
    with pytest.raises(AssertionError, match="ห้ามเปิด DB connection"):
        ErpLoader().load(_erp_df(), mode="append")
    print("✅ append ไม่ถูก guard")


def test_erp_replace_passes_guard_when_allowed(no_db, monkeypatch):
    monkeypatch.setenv("ALLOW_REPLACE", "true")
    with pytest.raises(AssertionError, match="ห้ามเปิด DB connection"):
        ErpLoader().load(_erp_df(), mode="replace")
    print("✅ ALLOW_REPLACE=true → replace ผ่าน guard")


def test_erp_invalid_mode_still_value_error(no_db, replace_blocked):
    with pytest.raises(ValueError):
        ErpLoader().load(_erp_df(), mode="upsert")


# ── MasterLoader ──────────────────────────────────────────────────────────────

def test_master_replace_blocked_before_touching_db(no_db, replace_blocked):
    with pytest.raises(RuntimeError, match="master_fund"):
        MasterLoader().load(_master_df(), table_name="master_fund", mode="replace")
    print("✅ MasterLoader replace ถูกบล็อกก่อนเปิด connection")


def test_master_default_mode_is_replace_and_blocked(no_db, replace_blocked):
    # default ของ master คือ replace → ต้อง opt-in ด้วยเช่นกัน
    with pytest.raises(RuntimeError, match="ALLOW_REPLACE"):
        MasterLoader().load(_master_df(), table_name="master_fund")


def test_master_append_not_affected_by_guard(no_db, replace_blocked):
    with pytest.raises(AssertionError, match="ห้ามเปิด DB connection"):
        MasterLoader().load(_master_df(), table_name="master_fund", mode="append")


def test_master_unknown_table_checked_before_guard(no_db, replace_blocked):
    with pytest.raises(ValueError, match="ไม่รู้จัก table"):
        MasterLoader().load(_master_df(), table_name="nope", mode="replace")
