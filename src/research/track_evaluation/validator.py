import logging
import pandas as pd

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2
_NON_NULLABLE = ["rank", "description", "product_code", "firstname", "lastname", "title"]
_NUMERIC_COLS = ["weight", "quality", "contribution", "score", "reward"]


def validate_track_evaluation(df: pd.DataFrame) -> bool:
    ok = True

    # 1. non-null text columns
    for col in _NON_NULLABLE:
        if col not in df.columns:
            logger.warning("Column '%s' ไม่พบใน DataFrame — ข้ามตรวจสอบ", col)
            continue
        mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' มีค่า null/ว่าง ที่ Excel rows: %s", col, rows)
            ok = False

    # 2. order_num 1–12
    if "order_num" in df.columns:
        df["order_num"] = pd.to_numeric(df["order_num"], errors="coerce")
        mask = df["order_num"].isna() | ~df["order_num"].between(1, 12)
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("order_num ไม่อยู่ในช่วง 1–12 ที่ Excel rows: %s", rows)
            ok = False

    # 3. publication_year > 0
    if "publication_year" in df.columns:
        df["publication_year"] = pd.to_numeric(df["publication_year"], errors="coerce")
        mask = df["publication_year"].isna() | (df["publication_year"] <= 0)
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("publication_year ไม่ใช่ค่าบวก ที่ Excel rows: %s", rows)
            ok = False

    # 4. publication_date → date
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.date
        mask = df["publication_date"].isna()
        if mask.any():
            rows = (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("publication_date แปลงเป็นวันที่ไม่ได้ ที่ Excel rows: %s", rows)
            ok = False
        else:
            logger.info("✅ publication_date แปลงเป็นวันที่สำเร็จทั้งหมด")

    # 5. corresponding → Yes / No / blank
    if "corresponding" in df.columns:
        df["corresponding"] = (
            df["corresponding"].fillna("").astype(str).str.strip().str.title()
        )
        invalid_mask = ~df["corresponding"].isin(["", "Yes", "No"])
        if invalid_mask.any():
            rows = (df.index[invalid_mask] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning(
                "Column 'corresponding' มีค่าที่ไม่ใช่ Yes/No ที่ Excel rows: %s", rows
            )
            ok = False

    # 6. numeric decimal columns
    for col in _NUMERIC_COLS:
        if col not in df.columns:
            continue
        was_not_null = df[col].notna()  # capture before coercion
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if col == "reward":
            df[col] = df[col].fillna(0)
        # non-numeric values: were not null but became null after coercion
        bad = df[col].isna() & was_not_null
        if bad.any():
            rows = (df.index[bad] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' มีค่า non-numeric ที่ Excel rows: %s", col, rows)
            ok = False

    return ok
