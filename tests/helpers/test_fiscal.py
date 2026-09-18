"""ทดสอบ helpers/fiscal.py — นิยามปีงบเดียว (เริ่ม ต.ค.) ที่ finance และ research ใช้ร่วมกัน (G15)"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from helpers.fiscal import FISCAL_YEAR_START_MONTH, fiscal_month, fiscal_year, fiscal_year_from_date


def test_start_month_is_october():
    assert FISCAL_YEAR_START_MONTH == 10


# ── fiscal_month ──────────────────────────────────────────────────────────────

def test_fiscal_month_full_table():
    months = pd.Series(range(1, 13))
    #                         ม.ค. ก.พ. มี.ค. เม.ย. พ.ค. มิ.ย. ก.ค. ส.ค. ก.ย. ต.ค. พ.ย. ธ.ค.
    assert fiscal_month(months).tolist() == [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
    print("✅ fiscal_month: ต.ค.=1 … ก.ย.=12")


def test_fiscal_month_equals_legacy_finance_formula():
    # สูตรเดิมใน ErpTransformer.add_fiscal_month: ((month + 2) % 12) + 1 — ต้องได้ผลเท่ากันทุกเดือน
    months = pd.Series(range(1, 13))
    legacy = ((months + 2) % 12 + 1).astype("Int64")
    pd.testing.assert_series_equal(fiscal_month(months), legacy, check_names=False)


def test_fiscal_month_null_and_strings():
    out = fiscal_month(pd.Series(["12", None, "abc", 10]))
    assert str(out.dtype) == "Int64"
    assert out.tolist()[0] == 3 and out.tolist()[3] == 1
    assert out.isna().tolist() == [False, True, True, False]


# ── fiscal_year ───────────────────────────────────────────────────────────────

def test_fiscal_year_rolls_over_from_october():
    year = pd.Series([2024] * 4)
    month = pd.Series([9, 10, 12, 1])
    assert fiscal_year(year, month).tolist() == [2024, 2025, 2025, 2024]
    print("✅ fiscal_year: ก.ย. 2024 → 2024, ต.ค.–ธ.ค. 2024 → 2025")


def test_fiscal_year_equals_legacy_research_formula():
    # สูตรเดิมใน get_clean_budget_year: np.where(month >= 10, year + 1, year) — รวมเคส month NaN → year
    import numpy as np
    year = pd.to_numeric(pd.Series([2023, 2023, 2023, 2023]), errors="coerce")
    month = pd.Series([3.0, 10.0, np.nan, 11.0])
    legacy = pd.Series(np.where(month >= 10, year + 1, year)).astype("Int64")
    pd.testing.assert_series_equal(fiscal_year(year, month), legacy, check_names=False)


def test_fiscal_year_missing_month_uses_calendar_year_missing_year_is_na():
    out = fiscal_year(pd.Series([2024, None]), pd.Series([None, 11]))
    assert out.tolist()[0] == 2024
    assert pd.isna(out.tolist()[1])
    assert str(out.dtype) == "Int64"


def test_fiscal_year_preserves_index():
    idx = [10, 20, 30]
    out = fiscal_year(pd.Series([2024] * 3, index=idx), pd.Series([1, 10, 12], index=idx))
    assert out.index.tolist() == idx


# ── fiscal_year_from_date ─────────────────────────────────────────────────────

def test_fiscal_year_from_date():
    dates = pd.Series(["2024-12-03", "2024-09-30", "2025-01-15", "not-a-date", None])
    out = fiscal_year_from_date(dates)
    assert out.tolist()[:3] == [2025, 2024, 2025]
    assert out.isna().tolist()[3:] == [True, True]
    print("✅ fiscal_year_from_date: 2024-12-03 → 2025")


def test_finance_and_research_agree_on_every_month():
    # นิยามเดียวจริง: research (year+month) กับ finance (date) ต้องให้ปีงบเดียวกันทุกเดือนของปี
    dates = pd.Series(pd.date_range("2024-01-15", periods=12, freq="MS"))
    via_date = fiscal_year_from_date(dates)
    via_parts = fiscal_year(dates.dt.year, dates.dt.month)
    pd.testing.assert_series_equal(via_date, via_parts, check_names=False)
