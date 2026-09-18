import logging
import pandas as pd

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2  # header row 1, data starts at row 2

_NON_NULLABLE = [
    "rank", "product_code", "firstname", "lastname", "title",
]

_FLAG_COLS = [
    "wos_with_jif_p90", "wos_with_jif", "wos_sc", "wos_ss", "wos_ah", "wos_es",
    "scopus_sjr_10", "scopus_q1", "scopus_q2", "scopus_q3", "scopus_q4", "scopus_no_q",
    "sense_abc",  # Fix: was missing from backup's excel_to_mssql.py
    "eric", "math_sci_net", "pubmed", "jstor", "project_muse", "other_inter",
    "tci_group1", "tci_group2", "national_journal",
]

_SDG_COLS = [f"sdg{i}" for i in range(1, 18)]

_YEAR_COLS = ["publication_year", "publication_calendar_year", "publication_budget_year"]

# ช่วงปีที่เป็นไปได้ (G21): get_clean_year ลบทุกอักขระที่ไม่ใช่ตัวเลข → "2023 (RC3)" กลายเป็น 20233 เงียบๆ
# range check จับเคสนั้นได้โดยไม่ต้องรอนิยามจาก Research (PD-8 ยังถามต่อว่า Year มี suffix ได้ไหม)
YEAR_MIN, YEAR_MAX = 2000, 2100


def validate_publication(df: pd.DataFrame) -> bool:
    """
    ตรวจ DataFrame หลัง transformer.coerce_and_clean() แล้ว — **อ่านอย่างเดียว ไม่แก้ df** (G11, pattern เดียวกับ G3)
    การเติม publication_month จาก effective_date ย้ายไป transformer แล้ว; ที่นี่แค่ตรวจว่าค่าอยู่ใน 1–12
    """
    ok = True

    for col in _NON_NULLABLE:
        mask = df[col].isna()
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.error("Column '%s' มีค่า null ที่ Excel rows: %s", col, rows)
            ok = False

    month = pd.to_numeric(df["publication_month"], errors="coerce")
    mask_bad = month.isna() | ~month.between(1, 12)
    if mask_bad.any():
        rows = (df.index[mask_bad] + _EXCEL_ROW_OFFSET).tolist()
        logger.warning("publication_month ไม่อยู่ใน 1–12 %d แถว ที่ Excel rows: %s", int(mask_bad.sum()), rows)
        ok = False

    for col in _YEAR_COLS:
        year = pd.to_numeric(df[col], errors="coerce")
        mask = year.isna() | ~year.between(YEAR_MIN, YEAR_MAX)
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            bad = year[mask].dropna().astype(int).unique().tolist()[:5]
            logger.warning(
                "Column '%s' ไม่อยู่ในช่วง %d–%d หรือว่าง ที่ Excel rows: %s (ค่าที่พบ เช่น %s)",
                col, YEAR_MIN, YEAR_MAX, rows, bad,
            )
            ok = False

    for col in _FLAG_COLS:
        if col not in df.columns:
            logger.warning("Column '%s' ไม่พบใน DataFrame — ข้ามตรวจสอบ", col)
            continue
        mask = ~df[col].isin([0, 1])
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' มีค่าไม่ใช่ 0/1 ที่ Excel rows: %s", col, rows)
            ok = False

    for col in _SDG_COLS:
        if col not in df.columns:
            logger.warning("Column '%s' ไม่พบใน DataFrame — ข้ามตรวจสอบ", col)
            continue
        non_null = df[col].dropna()
        mask = ~non_null.isin([0, 1])
        if mask.any():
            rows = (non_null.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' มีค่าไม่ใช่ 0/1/null ที่ Excel rows: %s", col, rows)
            ok = False

    invalid_rows = []
    for idx, val in df["effective_date"].items():
        if pd.isna(val):
            continue
        try:
            pd.to_datetime(val, errors="raise")
        except Exception:
            invalid_rows.append(idx + _EXCEL_ROW_OFFSET)
    if invalid_rows:
        logger.warning("effective_date แปลงเป็น date ไม่ได้ที่ Excel rows: %s", invalid_rows)
        ok = False
    else:
        logger.info("effective_date ตรวจสอบผ่านทั้งหมด %d แถว", len(df))

    return ok
