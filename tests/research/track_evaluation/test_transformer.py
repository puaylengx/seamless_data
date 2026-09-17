"""ทดสอบ coerce_and_clean — transformation ของ reviewed template อยู่จุดเดียว (G3)"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.track_evaluation.transformer import UPLOAD_COLUMNS, coerce_and_clean


# ── helpers ───────────────────────────────────────────────────────────────────

def _df(**overrides) -> pd.DataFrame:
    """แถวเดียวที่ครบทุก column หลัง rename แล้ว — override ได้ทีละ field"""
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
        "weight": ["1.0"],
        "quality": ["0.755"],
        "corresponding": ["yes"],
        "contribution": ["0.5"],
        "score": ["0.3775"],
        "reward": ["5000"],
        "title": ["A paper"],
        "source": ["Some Journal"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ── column mapping ────────────────────────────────────────────────────────────

def test_upload_columns_is_explicit_and_snake_case():
    assert len(UPLOAD_COLUMNS) == 19
    assert all(v == v.lower() and " " not in v for v in UPLOAD_COLUMNS.values())
    assert UPLOAD_COLUMNS["Product Code"] == "product_code"
    assert UPLOAD_COLUMNS["SCORE"] == "score"
    print("✅ UPLOAD_COLUMNS explicit + snake_case")


# ── ไม่ mutate input ──────────────────────────────────────────────────────────

def test_returns_new_dataframe_and_leaves_input_untouched():
    src = _df(reward=[None], corresponding=["yes"])
    snapshot = src.copy(deep=True)
    out = coerce_and_clean(src)
    assert out is not src
    pd.testing.assert_frame_equal(src, snapshot)
    print("✅ ไม่แก้ DataFrame ต้นทาง")


# ── fill จาก publication_date ─────────────────────────────────────────────────

def test_fills_year_month_order_num_from_publication_date():
    out = coerce_and_clean(_df(
        publication_year=[None], publication_month=[None], order_num=[None],
        publication_date=["2025-11-20"],
    ))
    assert out["publication_year"].iloc[0] == 2025
    assert out["publication_month"].iloc[0] == "November"
    assert out["order_num"].iloc[0] == 11
    print("✅ เติม year/month/order_num จาก publication_date")


def test_fills_blank_string_year_and_month_too():
    out = coerce_and_clean(_df(
        publication_year=["  "], publication_month=[""], publication_date=["2024-02-01"],
    ))
    assert out["publication_year"].iloc[0] == 2024
    assert out["publication_month"].iloc[0] == "February"
    print("✅ blank string ถือว่าว่าง เติมจากวันที่")


def test_does_not_overwrite_existing_values():
    out = coerce_and_clean(_df(
        publication_year=[2023], publication_month=["January"], order_num=[1],
        publication_date=["2025-11-20"],  # ต่างจากค่าที่มีอยู่
    ))
    assert out["publication_year"].iloc[0] == 2023
    assert out["publication_month"].iloc[0] == "January"
    assert out["order_num"].iloc[0] == 1
    print("✅ ไม่ทับค่าที่มีอยู่แล้ว")


def test_unparseable_date_leaves_fields_missing():
    out = coerce_and_clean(_df(
        publication_year=[None], order_num=[None], publication_date=["not-a-date"],
    ))
    assert pd.isna(out["publication_year"].iloc[0])
    assert pd.isna(out["order_num"].iloc[0])
    assert pd.isna(out["publication_date"].iloc[0])
    print("✅ วันที่ parse ไม่ได้ → ค่าที่เติมไม่ได้คง NaN (ให้ validator จับ)")


def test_publication_date_becomes_python_date():
    out = coerce_and_clean(_df(publication_date=["2026-03-15 10:30:00"]))
    assert out["publication_date"].iloc[0] == date(2026, 3, 15)
    print("✅ publication_date → date object")


# ── numeric ───────────────────────────────────────────────────────────────────

def test_decimal_columns_rounded_to_2dp():
    out = coerce_and_clean(_df(weight=["1.0"], quality=["0.755"], contribution=["0.5"], score=["0.3775"]))
    assert out["weight"].iloc[0] == 1.0
    assert out["quality"].iloc[0] == 0.76
    assert out["contribution"].iloc[0] == 0.5
    assert out["score"].iloc[0] == 0.38
    print("✅ weight/quality/contribution/score ปัด 2 ตำแหน่ง")


def test_reward_non_numeric_or_blank_becomes_zero():
    out = coerce_and_clean(pd.concat([
        _df(reward=["N/A"]), _df(reward=[None]), _df(reward=[""]), _df(reward=["1500"]),
    ], ignore_index=True))
    assert out["reward"].tolist() == [0, 0, 0, 1500]
    print("✅ reward non-numeric/ว่าง → 0 (behavior เดิม, รอ PD-2)")


def test_non_numeric_score_becomes_nan_not_zero():
    out = coerce_and_clean(_df(score=["abc"]))
    assert pd.isna(out["score"].iloc[0])
    print("✅ score non-numeric → NaN (ไม่ใช่ 0)")


def test_order_num_and_year_coerced_to_numeric():
    out = coerce_and_clean(_df(order_num=["7"], publication_year=["2022"]))
    assert out["order_num"].iloc[0] == 7
    assert out["publication_year"].iloc[0] == 2022
    assert np.issubdtype(out["order_num"].dtype, np.number)
    print("✅ order_num/publication_year เป็นตัวเลข")


# ── corresponding ─────────────────────────────────────────────────────────────

def test_corresponding_normalized_to_title_case():
    out = coerce_and_clean(pd.concat([
        _df(corresponding=["yes"]), _df(corresponding=[" NO "]),
        _df(corresponding=[None]), _df(corresponding=["Yes"]),
    ], ignore_index=True))
    assert out["corresponding"].tolist() == ["Yes", "No", "", "Yes"]
    print("✅ corresponding → Yes/No/'' ")


# ── missing optional columns ──────────────────────────────────────────────────

def test_works_when_optional_columns_absent():
    df = pd.DataFrame({"product_code": ["P-1"], "title": ["t"]})
    out = coerce_and_clean(df)
    assert list(out.columns) == ["product_code", "title"]
    print("✅ column ที่ไม่มี → ข้าม ไม่ error")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\n🎉 ทุก test ผ่าน")
