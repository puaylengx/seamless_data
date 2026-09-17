"""ทดสอบ helpers.replace_guard — guard กลางของ destructive replace mode (G2)"""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from helpers.replace_guard import ENV_VAR, ensure_replace_allowed


def test_blocked_when_env_not_set(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    with pytest.raises(RuntimeError) as exc:
        ensure_replace_allowed('TRUNCATE "public"."erp_2025"')
    msg = str(exc.value)
    assert 'TRUNCATE "public"."erp_2025"' in msg   # บอกว่าจะลบอะไร
    assert ENV_VAR in msg                           # บอกวิธีแก้
    assert "<ไม่ได้ตั้ง>" in msg
    print("✅ ไม่ตั้ง ALLOW_REPLACE → บล็อก พร้อมบอก context")


@pytest.mark.parametrize("value", ["false", "False", "0", "yes", "on", "", "  "])
def test_blocked_for_any_value_other_than_true(monkeypatch, value):
    monkeypatch.setenv(ENV_VAR, value)
    with pytest.raises(RuntimeError, match="replace mode ถูกบล็อก"):
        ensure_replace_allowed("x")


@pytest.mark.parametrize("value", ["true", "TRUE", "True", "  true  "])
def test_allowed_only_for_true_case_insensitive(monkeypatch, value):
    monkeypatch.setenv(ENV_VAR, value)
    ensure_replace_allowed("x")  # ต้องไม่ raise


def test_error_shows_current_wrong_value(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "yes")
    with pytest.raises(RuntimeError, match="'yes'"):
        ensure_replace_allowed("x")
    print("✅ ข้อความ error โชว์ค่าปัจจุบันที่ตั้งผิด")
