"""ทดสอบ _prepare_df ของ publication loader — ขั้นเตรียมข้อมูลก่อน MSSQL/BigQuery/Excel (G1)

ไม่แตะ load_to_mssql / load_to_bigquery (ต้องต่อระบบจริง)
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.loader import _RENAME_MAP, _REQUIRED_COLS, _STR_COLS, _prepare_df


def _template_row(**overrides) -> pd.DataFrame:
    d = {c: 0 for c in _REQUIRED_COLS}
    d.update({c: "x" for c in _STR_COLS})
    d.update({
        "product_code": "P-001", "publication_month": 3, "publication_year": 2024,
        "publication_calendar_year": 2024, "publication_budget_year": 2024,
        "effective_date": "2024-03-31",
    })
    d.update(overrides)
    return pd.DataFrame([d])


def test_rename_map_targets_are_snake_case_db_columns():
    assert set(_RENAME_MAP.values()) <= set(_REQUIRED_COLS)
    assert all(v == v.lower() and "-" not in v and "." not in v for v in _RENAME_MAP.values())
    print("✅ _RENAME_MAP → ชื่อ DB snake_case ทั้งหมด")


def test_prepare_renames_template_headers_and_orders_columns():
    df = _template_row().rename(columns={"scopus_q1": "Scopus_Q1", "wos_sc": "WoS_SC"})
    out = _prepare_df(df)
    assert list(out.columns) == _REQUIRED_COLS
    assert out["scopus_q1"].iloc[0] == 0


def test_prepare_raises_on_missing_required_column():
    with pytest.raises(ValueError, match="title"):
        _prepare_df(_template_row().drop(columns=["title"]))
    print("✅ column หาย → ValueError ระบุชื่อ")


def test_prepare_dtypes():
    out = _prepare_df(_template_row(volume=None, sdg3=None))
    assert str(out["publication_month"].dtype) == "Int64"
    assert str(out["title"].dtype) == "string"
    assert out["effective_date"].iloc[0] == date(2024, 3, 31)
    assert out["volume"].iloc[0] is None or pd.isna(out["volume"].iloc[0])
    print("✅ Int64 / string / date และ null → None")


def test_prepare_does_not_mutate_input():
    src = _template_row()
    snap = src.copy(deep=True)
    _prepare_df(src)
    pd.testing.assert_frame_equal(src, snap)
