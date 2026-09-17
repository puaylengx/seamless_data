"""ทดสอบ validate_publication — gate ก่อน export/upload MSSQL/BigQuery (G1)"""
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.validator import _FLAG_COLS, _SDG_COLS, validate_publication


def _row(**overrides) -> pd.DataFrame:
    """แถวเดียวหลัง template (ชื่อ column snake_case) ที่ควร validate ผ่าน"""
    d = {
        "rank": "Lecturer", "group_rank": "Lecturer", "description": "Journal",
        "product_code": "P-001", "firstname": "Somchai", "lastname": "Jaidee", "title": "A paper",
        "field": "", "division": "Science", "source": "J", "volume": None, "issue": None, "pages": None,
        "publication_month": 3, "publication_year": 2024, "publication_calendar_year": 2024,
        "publication_budget_year": 2024, "effective_date": "2024-03-31",
        "national_international": "International",
    }
    d.update({c: 0 for c in _FLAG_COLS})
    d.update({c: 0 for c in _SDG_COLS})
    d.update(overrides)
    return pd.DataFrame([d])


# ── happy path ────────────────────────────────────────────────────────────────

def test_valid_row_passes():
    assert validate_publication(_row()) is True
    print("✅ แถวถูกต้องผ่าน")


def test_sdg_null_is_allowed_flags_are_not():
    assert validate_publication(_row(sdg3=None)) is True
    assert validate_publication(_row(scopus_q1=None)) is False


# ── required text ─────────────────────────────────────────────────────────────

def test_null_required_text_fails():
    for col in ("rank", "product_code", "firstname", "lastname", "title"):
        assert validate_publication(_row(**{col: None})) is False, col
    print("✅ text บังคับว่าง → fail ครบ 5 column")


# ── month ─────────────────────────────────────────────────────────────────────

def test_invalid_month_is_recovered_from_effective_date():
    # behavior ปัจจุบัน: เดือนผิด แต่มี effective_date → เติมจากวันที่แล้วผ่าน (และ mutate df)
    df = _row(publication_month=13, effective_date="2024-03-31")
    assert validate_publication(df) is True
    assert df["publication_month"].iloc[0] == 3
    print("✅ month 13 + effective_date → เติมเป็น 3 แล้วผ่าน (behavior เดิม)")


def test_invalid_month_without_effective_date_fails():
    assert validate_publication(_row(publication_month=None, effective_date=None)) is False
    assert validate_publication(_row(publication_month=0, effective_date=None)) is False


# ── years ─────────────────────────────────────────────────────────────────────

def test_non_positive_or_missing_year_fails():
    for col in ("publication_year", "publication_calendar_year", "publication_budget_year"):
        assert validate_publication(_row(**{col: 0})) is False, col
        assert validate_publication(_row(**{col: None})) is False, col


# ── 0/1 flags ─────────────────────────────────────────────────────────────────

def test_flag_columns_must_be_zero_or_one():
    assert validate_publication(_row(scopus_q1=2)) is False
    assert validate_publication(_row(tci_group1=1)) is True
    assert validate_publication(_row(sdg7=2)) is False


def test_missing_flag_column_is_skipped_with_warning(caplog):
    df = _row().drop(columns=["sense_abc"])
    with caplog.at_level(logging.WARNING, logger="src.research.publication.validator"):
        assert validate_publication(df) is True
    assert "sense_abc" in caplog.text


# ── effective_date ────────────────────────────────────────────────────────────

def test_unparseable_effective_date_fails_but_null_is_allowed():
    assert validate_publication(_row(effective_date="31/31/2024")) is False
    assert validate_publication(_row(effective_date=None)) is True


# ── row reporting ─────────────────────────────────────────────────────────────

def test_bad_rows_reported_as_excel_row_numbers(caplog):
    df = pd.concat([_row(), _row(title=None)], ignore_index=True)
    with caplog.at_level(logging.ERROR, logger="src.research.publication.validator"):
        assert validate_publication(df) is False
    assert "Excel rows: [3]" in caplog.text  # index 1 + header offset 2
    print("✅ รายงานเลขแถว Excel")
