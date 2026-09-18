"""ทดสอบ consistency + timeliness ของ ErpValidator และ reference sets จาก master (G13) — ไม่ต่อ DB"""
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance.master.validator import KEY_COLUMNS
from src.finance.reference import ERP_REFERENCES, load_master_reference, master_as_of, normalize_key
from src.finance.validator import ErpValidator
from tests.finance.test_validator import _valid_df

TODAY = date(2025, 1, 15)   # doc_date ใน _valid_df = 2024-12-03 → 43 วัน (ไม่เตือน)


# ── reference module ──────────────────────────────────────────────────────────

def test_erp_references_point_to_known_master_tables():
    assert set(ERP_REFERENCES.values()) <= set(KEY_COLUMNS)
    assert ERP_REFERENCES["gl_id"] == "master_gl"
    assert "funds_ctr" not in ERP_REFERENCES      # คนละระบบรหัสกับ master_fund — รอ PD-12 ไม่เดา


def test_normalize_key_makes_numeric_and_text_ids_comparable():
    # erp: ic_strategy NUMERIC (3.0) · master: ic_strategy_id TEXT ("3") — G10 type mismatch
    out = normalize_key(pd.Series([3.0, "3", " 3 ", "03", None, 10]))
    assert out.tolist()[:4] == ["3", "3", "3", "03"] and pd.isna(out.iloc[4]) and out.iloc[5] == "10"


def test_master_as_of_from_filename():
    assert master_as_of("Master_GL_20230531.xlsx") == date(2023, 5, 31)
    assert master_as_of("Master_CostCtr_20240605.xlsx") == date(2024, 6, 5)
    assert master_as_of("Master_NoDate.xlsx") is None


def test_load_master_reference_from_files(tmp_path, caplog):
    pd.DataFrame({"Fund_Id": ["3001", "3002 "], "Fund_Description": ["a", "b"]}).to_excel(tmp_path / "Master_FUND_20221118.xlsx", index=False)
    pd.DataFrame({"Group": ["G"], "Id": [5302050010], "Description": ["d"], "Group_Description": ["g"]}).to_excel(tmp_path / "Master_GL_20230531.xlsx", index=False)
    pd.DataFrame({"CostCtr_Id": ["C3001000 ", "C3001003"], "CostCtr_Description": ["a", "b"]}).to_excel(tmp_path / "Master_CostCtr_20240605.xlsx", index=False)
    files = {"master_cost_ctr": "Master_CostCtr_20240605.xlsx", "master_gl": "Master_GL_20230531.xlsx", "master_io_work": "missing.xlsx"}
    with caplog.at_level(logging.WARNING, logger="src.finance.reference"):
        refs, as_of = load_master_reference(files, data_dir=tmp_path)
    assert refs["cost_ctr_id"] == {"C3001000", "C3001003"} and refs["gl_id"] == {"5302050010"}
    assert "io_work" not in refs and "ข้าม check 'io_work'" in caplog.text
    assert as_of["cost_ctr_id"] == date(2024, 6, 5)
    print("✅ reference จากไฟล์ master: normalize key, ข้ามไฟล์ที่ไม่มี")


# ── validate_referential ──────────────────────────────────────────────────────

def _refs(**overrides):
    base = {"funds_ctr": {"3001"}, "cost_ctr_id": {"C3001000"}, "gl_id": {"5302050010"}, "io_work": {"Z30000000000"}}
    base.update(overrides)
    return base


def test_referential_passes_when_all_values_known():
    r = ErpValidator(_valid_df(), reference=_refs(), today=TODAY).run()
    assert r["passed"] and r["warnings"] == []


def test_unknown_code_is_warning_by_default_with_rows_and_samples(caplog):
    df = pd.concat([_valid_df(), _valid_df()], ignore_index=True)
    df.loc[1, "gl_id"] = "9999999999"
    with caplog.at_level(logging.WARNING, logger="src.finance.validator"):
        r = ErpValidator(df, reference=_refs(), today=TODAY).run()
    assert r["passed"] is True                                   # advisory — master อาจเก่ากว่า ERP
    assert len(r["warnings"]) == 1
    assert "'gl_id'" in r["warnings"][0] and "9999999999" in r["warnings"][0] and "Excel rows: [3]" in r["warnings"][0]
    print("✅ รหัสไม่อยู่ใน master → WARNING (ไม่ block)")


def test_strict_reference_turns_unknown_code_into_error():
    df = _valid_df()
    df["gl_id"] = ["9999999999"]
    r = ErpValidator(df, reference=_refs(), strict_reference=True, today=TODAY).run()
    assert r["passed"] is False and any("'gl_id'" in e for e in r["errors"])


def test_null_and_blank_values_are_not_checked_against_master():
    df = _valid_df()
    df["io_goods"] = [pd.NA]                                       # nullable column ว่าง → ไม่ใช่ referential error
    r = ErpValidator(df, reference=_refs(io_goods={"G1"}), today=TODAY).run()
    assert r["warnings"] == []


def test_numeric_strategy_matches_text_master_key():
    df = _valid_df()
    df["ic_strategy"] = [3.0]
    r = ErpValidator(df, reference=_refs(ic_strategy={"3"}), today=TODAY).run()
    assert r["warnings"] == []
    df["ic_strategy"] = [4.0]
    r = ErpValidator(df, reference=_refs(ic_strategy={"3"}), today=TODAY).run()
    assert any("'ic_strategy'" in w for w in r["warnings"])
    print("✅ NUMERIC 3.0 เทียบ TEXT '3' ได้ (G10 mismatch ไม่ทำให้เตือนผิด)")


def test_columns_without_reference_are_skipped():
    r = ErpValidator(_valid_df(), reference={"nope": {"x"}}, today=TODAY).run()
    assert r["warnings"] == []


# ── validate_timeliness ───────────────────────────────────────────────────────

def test_stale_data_and_stale_master_are_warnings():
    df = _valid_df()                                               # doc_date 2024-12-03
    r = ErpValidator(df, reference=_refs(), reference_as_of={"gl_id": date(2023, 5, 31)}, today=date(2026, 9, 18)).run()
    assert r["passed"] is True
    assert any("doc_date ล่าสุด" in w and "2024-12-03" in w for w in r["warnings"])
    assert any("master ที่ใช้เทียบเก่ากว่า 365 วัน" in w and "gl_id" in w for w in r["warnings"])
    print("✅ timeliness: ข้อมูลเก่า + master เก่า → WARNING")


def test_fresh_data_and_master_do_not_warn():
    r = ErpValidator(_valid_df(), reference=_refs(), reference_as_of={"gl_id": date(2024, 12, 1)}, today=TODAY).run()
    assert r["warnings"] == []
