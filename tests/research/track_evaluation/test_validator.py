"""ทดสอบ validate_track_evaluation — read-only, จับค่าผิดได้ครบ (G3)"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.track_evaluation.transformer import coerce_and_clean
from src.research.track_evaluation.validator import validate_track_evaluation


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean_valid(**overrides) -> pd.DataFrame:
    """DataFrame ที่ผ่าน coerce_and_clean แล้ว และควร validate ผ่าน"""
    base = {
        "product_code": ["P-001"],
        "rc_meeting": ["RC3-2026"],
        "publication_month": ["March"],
        "order_num": [3],
        "publication_year": [2026],
        "publication_date": ["2026-03-15"],
        "firstname": ["Somchai"],
        "lastname": ["Jaidee"],
        "rank": ["Lecturer"],
        "division": ["Science"],
        "description": ["Journal article"],
        "weight": [1.0],
        "quality": [0.76],
        "corresponding": ["yes"],
        "contribution": [0.5],
        "score": [0.38],
        "reward": [5000],
        "title": ["A paper"],
        "source": ["Some Journal"],
    }
    base.update(overrides)
    return coerce_and_clean(pd.DataFrame(base))


# ── happy path ────────────────────────────────────────────────────────────────

def test_valid_dataframe_passes():
    assert validate_track_evaluation(_clean_valid()) is True
    print("✅ ข้อมูลถูกต้องผ่าน validate")


# ── ห้าม mutate ───────────────────────────────────────────────────────────────

def test_validator_does_not_mutate_input():
    # ใช้ df ดิบที่ยังไม่ coerce เพื่อให้เห็นชัดว่าถ้า validator แปลงค่าจะถูกจับได้
    raw = pd.DataFrame({
        "product_code": ["P-1"], "rank": ["Lecturer"], "description": ["d"],
        "firstname": ["a"], "lastname": ["b"], "title": ["t"],
        "order_num": ["3"], "publication_year": ["2026"],
        "publication_date": ["2026-03-15"], "corresponding": ["yes"],
        "weight": ["1.0"], "quality": ["x"], "contribution": [None],
        "score": ["0.5"], "reward": [None],
    })
    snapshot = raw.copy(deep=True)
    validate_track_evaluation(raw)
    pd.testing.assert_frame_equal(raw, snapshot)
    assert raw["corresponding"].iloc[0] == "yes"     # ไม่ถูก title-case
    assert raw["reward"].iloc[0] is None             # ไม่ถูก fillna(0)
    assert not pd.api.types.is_numeric_dtype(raw["order_num"])  # ไม่ถูก to_numeric
    print("✅ validator ไม่แก้ DataFrame ที่รับเข้ามา")


# ── invalid cases ต้อง fail ───────────────────────────────────────────────────

def test_null_required_text_fails():
    assert validate_track_evaluation(_clean_valid(title=[None])) is False
    assert validate_track_evaluation(_clean_valid(product_code=["   "])) is False
    print("✅ text บังคับว่าง → fail")


def test_order_num_out_of_range_fails():
    assert validate_track_evaluation(_clean_valid(order_num=[13])) is False
    assert validate_track_evaluation(_clean_valid(order_num=[0])) is False
    print("✅ order_num นอก 1–12 → fail")


def test_order_num_missing_and_undeducible_fails():
    df = _clean_valid(order_num=[None], publication_date=["garbage"])
    assert validate_track_evaluation(df) is False
    print("✅ order_num ว่างและเดาจากวันที่ไม่ได้ → fail")


def test_publication_year_non_positive_fails():
    assert validate_track_evaluation(_clean_valid(publication_year=[0])) is False
    assert validate_track_evaluation(_clean_valid(publication_year=[-1])) is False
    print("✅ publication_year ≤ 0 → fail")


def test_invalid_publication_date_fails():
    assert validate_track_evaluation(_clean_valid(publication_date=["31/31/2026"])) is False
    print("✅ publication_date แปลงไม่ได้ → fail")


def test_corresponding_other_than_yes_no_blank_fails():
    assert validate_track_evaluation(_clean_valid(corresponding=["maybe"])) is False
    assert validate_track_evaluation(_clean_valid(corresponding=[""])) is True
    assert validate_track_evaluation(_clean_valid(corresponding=["NO"])) is True
    print("✅ corresponding ต้องเป็น Yes/No/ว่าง")


def test_non_numeric_in_uncleaned_numeric_column_fails():
    # เรียก validator ตรงกับ df ที่ยังไม่ผ่าน coerce (กันคนเรียกผิดลำดับ)
    df = pd.DataFrame({
        "product_code": ["P"], "rank": ["r"], "description": ["d"],
        "firstname": ["a"], "lastname": ["b"], "title": ["t"],
        "score": ["abc"],
    })
    assert validate_track_evaluation(df) is False
    print("✅ numeric column มีค่า non-numeric → fail")


def test_missing_optional_columns_are_skipped_not_failed():
    df = pd.DataFrame({
        "product_code": ["P"], "rank": ["r"], "description": ["d"],
        "firstname": ["a"], "lastname": ["b"], "title": ["t"],
    })
    assert validate_track_evaluation(df) is True
    print("✅ column optional ที่ไม่มี → ข้าม")


def test_bad_row_numbers_reported_as_excel_rows(caplog):
    import logging
    df = _clean_valid()
    df = pd.concat([df, df], ignore_index=True)
    df.loc[1, "title"] = None
    with caplog.at_level(logging.WARNING, logger="src.research.track_evaluation.validator"):
        validate_track_evaluation(df)
    assert "Excel rows: [3]" in caplog.text   # index 1 + offset 2
    print("✅ รายงานเลขแถวแบบ Excel (header=1)")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn) and name != "test_bad_row_numbers_reported_as_excel_rows":
            fn()
    print("\n🎉 ทุก test ผ่าน (ยกเว้น caplog test ที่ต้องรันผ่าน pytest)")
