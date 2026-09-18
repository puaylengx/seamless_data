"""ทดสอบ MasterValidator — master tables เดิมไม่มี validator เลย (G11)"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance.master.loader import _TABLE_COLUMNS
from src.finance.master.validator import KEY_COLUMNS, MasterValidator


def _fund(**o):
    d = {"fund_id": ["F1", "F2"], "fund_description": ["a", "b"], "status": ["active", "active"]}
    d.update(o)
    return pd.DataFrame(d)


def test_key_columns_cover_every_master_table():
    assert set(KEY_COLUMNS) == set(_TABLE_COLUMNS)
    assert KEY_COLUMNS["master_gl"] == "gl_id" and KEY_COLUMNS["master_cost_ctr"] == "cost_center_id"


def test_valid_master_passes():
    r = MasterValidator(_fund(), "master_fund").run()
    assert r == {"passed": True, "errors": [], "warnings": []}
    print("✅ master ถูกต้องผ่าน")


def test_unknown_table_rejected():
    with pytest.raises(ValueError, match="ไม่รู้จัก table"):
        MasterValidator(_fund(), "master_nope")


def test_duplicate_key_fails_with_rows():
    r = MasterValidator(_fund(fund_id=["F1", "F1"]), "master_fund").run()
    assert not r["passed"]
    assert any("ซ้ำ 2 แถว" in e and "Excel rows: [2, 3]" in e for e in r["errors"])
    print("✅ key ซ้ำ → fail (กัน double count ตอน join)")


def test_blank_key_fails():
    r = MasterValidator(_fund(fund_id=["F1", "  "]), "master_fund").run()
    assert not r["passed"] and any("ว่าง 1 แถว" in e for e in r["errors"])


def test_missing_expected_column_fails_but_status_optional():
    r = MasterValidator(_fund().drop(columns=["fund_description"]), "master_fund").run()
    assert not r["passed"] and any("column หาย ['fund_description']" in e for e in r["errors"])
    r2 = MasterValidator(_fund().drop(columns=["status"]), "master_fund").run()
    assert r2["passed"]                                  # status เติมโดย transformer ไม่บังคับที่นี่


def test_unknown_status_is_warning_not_error():
    r = MasterValidator(_fund(status=["active", "retired"]), "master_fund").run()
    assert r["passed"] and len(r["warnings"]) == 1 and "retired" not in r["errors"]
    print("✅ status แปลก → warning เท่านั้น")


def test_status_domain_matches_real_master_files():
    # ค่าที่พบจริง (G5 ตรวจไฟล์ 2026-09-18): io_work ใช้ use/cancel, strategies ใช้ 0/1 — ต้องไม่เตือน
    from src.finance.master.validator import valid_status
    work = pd.DataFrame({"io_work_id": ["W1", "W2"], "io_work_description": ["a", "b"], "status": ["use", "cancel"]})
    assert MasterValidator(work, "master_io_work").run()["warnings"] == []
    strat = pd.DataFrame({"ic_strategy_id": ["S1"], "start_year": [2020], "end_year": [2024], "name_en": ["x"],
                          "ic_strategy_description": ["d"], "status": ["1"]})
    assert MasterValidator(strat, "master_ic_strategy").run()["warnings"] == []
    assert valid_status("master_fund") == {"active", "inactive"}
    assert MasterValidator(_fund(status=["use", "active"]), "master_fund").run()["warnings"] != []
    print("✅ status domain ต่อตารางตรงข้อมูลจริง")


def test_validator_does_not_mutate():
    df = _fund(fund_id=["F1", "F1"], status=["x", None])
    snap = df.copy(deep=True)
    MasterValidator(df, "master_fund").run()
    pd.testing.assert_frame_equal(df, snap)
