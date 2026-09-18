"""
Track evaluation extractor — อ่านไฟล์ Excel 2 แบบ (G11)

  read_raw()               ไฟล์ต้นทาง (01_raw) → column ที่ build_track_template ใช้ต้องครบ
  read_reviewed_template() template ที่ review แล้ว (02_template) → เลือกเฉพาะ UPLOAD_COLUMNS แล้ว rename เป็นชื่อ DB
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.research.track_evaluation.transformer import UPLOAD_COLUMNS

logger = logging.getLogger(__name__)

RAW_REQUIRED_COLUMNS: list[str] = [
    "Product Code", "RC Meeting", "Firstname", "Lastname", "Rank", "Division", "Description",
    "Weight", "Quality", "Corresponding", "Contribution", "SCORE", "REWARD", "Title",
    "Journal/Conference/Source", "Year", "Month", "Online Date", "Publication Date",
]


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_raw(path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
    df = _strip_columns(pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl"))
    missing = [c for c in RAW_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"ไฟล์ต้นทางขาด column ที่จำเป็น: {missing}")
    logger.info("Read %d rows from source file %s", len(df), Path(path).name)
    return df.reset_index(drop=True)


def read_reviewed_template(path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """อ่านเฉพาะ column ใน UPLOAD_COLUMNS (เหมือน usecols เดิม) แล้ว rename → ชื่อ DB; column หาย → ValueError"""
    df = _strip_columns(pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl"))
    missing = [c for c in UPLOAD_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"template ขาด column ที่จำเป็น: {missing}")
    df = df[list(UPLOAD_COLUMNS)].rename(columns=UPLOAD_COLUMNS)
    logger.info("Read %d rows × %d columns from reviewed template %s", len(df), len(df.columns), Path(path).name)
    return df.reset_index(drop=True)
