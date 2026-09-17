import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.transformer import (  # noqa: F401 — re-export shared functions
    get_rank,
    get_parse_database_data,
    get_clean_publication_month,
    get_clean_publication_day,
    get_clean_publication_name_month,
    get_clean_year,
    get_format_effective_date,
)

import pandas as pd

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2  # header row 1, data starts at row 2

# ── column mapping: reviewed template (Excel) → DB ────────────────────────────
# ใช้ร่วมกันทั้ง upload MSSQL และ upload BigQuery — แก้ที่เดียว

UPLOAD_COLUMNS: dict[str, str] = {
    "Product Code":      "product_code",
    "RC Meeting":        "rc_meeting",
    "Publication_month": "publication_month",
    "orderNum":          "order_num",
    "Publication_year":  "publication_year",
    "PublicationDate":   "publication_date",
    "Firstname":         "firstname",
    "Lastname":          "lastname",
    "Rank":              "rank",
    "Division":          "division",
    "Description":       "description",
    "Weight":            "weight",
    "Quality":           "quality",
    "Corresponding":     "corresponding",
    "Contribution":      "contribution",
    "SCORE":             "score",
    "REWARD":            "reward",
    "Title":             "title",
    "Source":            "source",
}

_DECIMAL_COLS = ["weight", "quality", "contribution", "score"]
_NUMERIC_COLS = _DECIMAL_COLS + ["reward"]


def build_track_template(df_data: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame()
    df["Product Code"] = df_data["Product Code"]
    df["RC Meeting"] = df_data["RC Meeting"]
    df["Publication_month"] = get_clean_publication_name_month(df_data)
    df["orderNum"] = get_clean_publication_month(df_data)
    df["Publication_year"] = get_clean_year(df_data)
    df["PublicationDate"] = get_format_effective_date(df_data)
    df["Firstname"] = df_data["Firstname"]
    df["Lastname"] = df_data["Lastname"]
    df["Rank"] = get_rank(df_data)
    df["Division"] = df_data["Division"]
    df["Description"] = df_data["Description"]
    df["Weight"] = df_data["Weight"]
    df["Quality"] = df_data["Quality"]
    df["Corresponding"] = df_data["Corresponding"]
    df["Contribution"] = df_data["Contribution"]
    df["SCORE"] = df_data["SCORE"]
    df["REWARD"] = df_data["REWARD"]
    df["Title"] = df_data["Title"]
    df["Source"] = df_data["Journal/Conference/Source"]
    return df


def _is_blank(s: pd.Series) -> pd.Series:
    return s.isna() | (s.astype(str).str.strip() == "")


def coerce_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    รวม transformation ทั้งหมดของ reviewed template (หลัง rename เป็นชื่อ DB แล้ว)
    ไว้จุดเดียว ก่อนส่งให้ validator / loader — คืน DataFrame ใหม่ ไม่แก้ตัวที่รับเข้ามา

    เดิม logic เหล่านี้กระจายอยู่ใน main.run_upload (เฉพาะ MSSQL) และ validator
    (mutate df ทั้งสอง path) ทำให้ MSSQL กับ BigQuery ได้ค่าต่างกัน

    ลำดับ (คง behavior เดิมทุกจุด):
      1. publication_date → datetime
      2. เติม publication_year / publication_month (ชื่อเดือนอังกฤษ) / order_num
         จาก publication_date เฉพาะแถวที่ว่าง — ไม่ทับค่าที่มีอยู่
      3. numeric columns → float; weight/quality/contribution/score ปัดทศนิยม 2 ตำแหน่ง
      4. reward ว่าง/parse ไม่ได้ → 0
      5. corresponding → Title-case ("yes" → "Yes"), ว่าง → ""
      6. publication_date → date (python date object)
    """
    df = df.copy()

    # 1–2. publication_date และการเติมค่าจากวันที่
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce")

        if "publication_year" in df.columns:
            mask = _is_blank(df["publication_year"])
            # pandas ≥ 3 อ่าน column ที่มีแต่ string เป็น dtype "str" ซึ่งรับ int ไม่ได้
            # → เปิดเป็น object ก่อนเติม (to_numeric ด้านล่างจะแปลงกลับเป็นตัวเลข)
            df["publication_year"] = df["publication_year"].astype(object)
            df.loc[mask, "publication_year"] = df.loc[mask, "publication_date"].dt.year
            logger.info("เติม publication_year จาก publication_date แล้ว %d แถว", int(mask.sum()))

        if "publication_month" in df.columns:
            mask = _is_blank(df["publication_month"])
            df.loc[mask, "publication_month"] = df.loc[mask, "publication_date"].dt.strftime("%B")
            logger.info("เติม publication_month จาก publication_date แล้ว %d แถว", int(mask.sum()))

        if "order_num" in df.columns:
            mask = df["order_num"].isna()
            df["order_num"] = df["order_num"].astype(object)
            df.loc[mask, "order_num"] = df.loc[mask, "publication_date"].dt.month
            logger.info("เติม order_num จาก publication_date แล้ว %d แถว", int(mask.sum()))

    # 3–4. numeric columns
    for col in _NUMERIC_COLS:
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        lost = numeric.isna() & df[col].notna()
        if lost.any():
            # ค่าที่ไม่ใช่ตัวเลข (เช่น "N/A") จะกลายเป็น NULL — บันทึกไว้ให้ตรวจย้อนหลัง
            rows = (df.index[lost] + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' มีค่า non-numeric → NULL ที่ Excel rows: %s", col, rows)
        if col in _DECIMAL_COLS:
            numeric = numeric.round(2)
        if col == "reward":
            # TODO(PD-2): reward ว่าง/parse ไม่ได้ = 0 เป็น behavior เดิม
            # ยังรอ Domain Expert Research ยืนยันว่าควรเป็น 0 หรือควร reject แถว
            numeric = numeric.fillna(0)
        df[col] = numeric

    for col in ("order_num", "publication_year"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. corresponding
    if "corresponding" in df.columns:
        df["corresponding"] = (
            df["corresponding"].fillna("").astype(str).str.strip().str.title()
        )

    # 6. publication_date → date object (รูปแบบที่ loader MSSQL/BQ รับ)
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.date

    return df
