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


def validate_publication(df: pd.DataFrame) -> bool:
    ok = True

    for col in _NON_NULLABLE:
        mask = df[col].isna()
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.error("Column '%s' มีค่า null ที่ Excel rows: %s", col, rows)
            ok = False

    mask_bad = df["publication_month"].isna() | ~df["publication_month"].between(1, 12)
    if mask_bad.any():
        rows = (df.index[mask_bad] + _EXCEL_ROW_OFFSET).tolist()
        logger.info(
            "publication_month ไม่อยู่ใน 1–12 ที่ Excel rows: %s → ใช้ effective_date แทน", rows
        )
        df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce")
        fillable = mask_bad & df["effective_date"].notna()
        df.loc[fillable, "publication_month"] = df.loc[fillable, "effective_date"].dt.month
        still_bad = df["publication_month"].isna() | ~df["publication_month"].between(1, 12)
        if still_bad.any():
            rows2 = (df.index[still_bad] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning(
                "ยังมี publication_month ที่ไม่ถูกต้อง %d แถว: %s", still_bad.sum(), rows2
            )
            ok = False

    for col in _YEAR_COLS:
        mask = df[col].isna() | (df[col].astype(float) <= 0)
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' ไม่ใช่ positive int ที่ Excel rows: %s", col, rows)
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
