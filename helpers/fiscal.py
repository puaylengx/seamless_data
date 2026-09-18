"""
นิยามปีงบประมาณ (fiscal year) ขององค์กร — **ที่เดียว** ใช้ร่วมกันทั้ง finance และ research (G15)

นิยาม: ปีงบประมาณเริ่ม 1 ตุลาคม
  - ต.ค.–ธ.ค. ของปีปฏิทิน Y  → ปีงบ Y+1, fiscal_month 1–3
  - ม.ค.–ก.ย. ของปีปฏิทิน Y  → ปีงบ Y,   fiscal_month 4–12
  ตัวอย่าง: 3 ธ.ค. 2024 → fiscal_year 2025, fiscal_month 3

เดิม logic นี้ implement แยกกัน 2 ที่และบังเอิญตรงกัน:
  - finance  ErpTransformer.add_fiscal_month:  ((month + 2) % 12) + 1
  - research get_clean_budget_year:            year + 1 if month >= 10 else year
ถ้าองค์กรเปลี่ยนรอบปีงบ แก้ FISCAL_YEAR_START_MONTH ที่นี่ที่เดียว (และ Metric Dictionary — G12)

พฤติกรรมเมื่อค่าว่าง (คงของเดิมทุกกรณี):
  - month ว่าง → fiscal_month ว่าง (NA)
  - month ว่างแต่ year มี → fiscal_year = year (research เดิม: NaN >= 10 เป็น False → ใช้ปีปฏิทิน)
  - year ว่าง → fiscal_year ว่าง (NA)
"""
from __future__ import annotations

import pandas as pd

FISCAL_YEAR_START_MONTH = 10  # ตุลาคม


def fiscal_month(month: pd.Series) -> pd.Series:
    """เดือนปฏิทิน (1–12) → เดือนปีงบ (1–12); ว่าง → NA. คืน Int64"""
    m = pd.to_numeric(month, errors="coerce")
    return ((m - FISCAL_YEAR_START_MONTH) % 12 + 1).astype("Int64")


def fiscal_year(year: pd.Series, month: pd.Series) -> pd.Series:
    """ปีปฏิทิน + เดือน → ปีงบ; เดือนว่าง → ใช้ปีปฏิทิน; ปีว่าง → NA. คืน Int64"""
    y = pd.to_numeric(year, errors="coerce")
    m = pd.to_numeric(month, errors="coerce")
    rollover = (m >= FISCAL_YEAR_START_MONTH).fillna(False).astype(int)
    return (y + rollover).astype("Int64")


def fiscal_year_from_date(dates: pd.Series) -> pd.Series:
    """วันที่ (datetime หรือ string parse ได้) → ปีงบ; parse ไม่ได้ → NA. คืน Int64"""
    dt = pd.to_datetime(dates, errors="coerce")
    return fiscal_year(dt.dt.year, dt.dt.month)
