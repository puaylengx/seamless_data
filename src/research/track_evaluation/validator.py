import logging
import pandas as pd

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2
_NON_NULLABLE = ["rank", "description", "product_code", "firstname", "lastname", "title"]
_NUMERIC_COLS = ["weight", "quality", "contribution", "score", "reward"]


def _rows(df: pd.DataFrame, mask: pd.Series) -> list:
    return (df.index[mask] + _EXCEL_ROW_OFFSET).tolist()


def validate_track_evaluation(df: pd.DataFrame) -> bool:
    """
    ตรวจสอบ DataFrame หลังผ่าน transformer.coerce_and_clean() แล้ว

    อ่านอย่างเดียว — ไม่แก้ค่าใน df ที่รับเข้ามา (การแปลง/เติมค่าทั้งหมด
    อยู่ใน transformer.coerce_and_clean เท่านั้น ตามกติกา validation อยู่จุดเดียว)
    """
    ok = True

    # 1. non-null text columns
    for col in _NON_NULLABLE:
        if col not in df.columns:
            logger.warning("Column '%s' ไม่พบใน DataFrame — ข้ามตรวจสอบ", col)
            continue
        mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        if mask.any():
            logger.warning("Column '%s' มีค่า null/ว่าง ที่ Excel rows: %s", col, _rows(df, mask))
            ok = False

    # 2. order_num 1–12
    if "order_num" in df.columns:
        order_num = pd.to_numeric(df["order_num"], errors="coerce")
        mask = order_num.isna() | ~order_num.between(1, 12)
        if mask.any():
            logger.warning("order_num ไม่อยู่ในช่วง 1–12 ที่ Excel rows: %s", _rows(df, mask))
            ok = False

    # 3. publication_year > 0
    if "publication_year" in df.columns:
        year = pd.to_numeric(df["publication_year"], errors="coerce")
        mask = year.isna() | (year <= 0)
        if mask.any():
            logger.warning("publication_year ไม่ใช่ค่าบวก ที่ Excel rows: %s", _rows(df, mask))
            ok = False

    # 4. publication_date → date
    if "publication_date" in df.columns:
        parsed = pd.to_datetime(df["publication_date"], errors="coerce")
        mask = parsed.isna()
        if mask.any():
            logger.warning("publication_date แปลงเป็นวันที่ไม่ได้ ที่ Excel rows: %s", _rows(df, mask))
            ok = False
        else:
            logger.info("✅ publication_date แปลงเป็นวันที่สำเร็จทั้งหมด")

    # 5. corresponding → Yes / No / blank
    if "corresponding" in df.columns:
        normalized = df["corresponding"].fillna("").astype(str).str.strip().str.title()
        invalid_mask = ~normalized.isin(["", "Yes", "No"])
        if invalid_mask.any():
            logger.warning(
                "Column 'corresponding' มีค่าที่ไม่ใช่ Yes/No ที่ Excel rows: %s",
                _rows(df, invalid_mask),
            )
            ok = False

    # 6. numeric decimal columns — ค่าที่มีอยู่ต้องเป็นตัวเลข
    for col in _NUMERIC_COLS:
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        bad = numeric.isna() & df[col].notna()
        if bad.any():
            logger.warning("Column '%s' มีค่า non-numeric ที่ Excel rows: %s", col, _rows(df, bad))
            ok = False

    return ok
