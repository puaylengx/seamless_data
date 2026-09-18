"""
Publication extractor — อ่านไฟล์ Excel 2 แบบ (G11: pattern extractor → transformer → validator → loader)

  read_raw()               ไฟล์ต้นทางจากฝ่ายวิจัย (01_raw)  → ตรวจว่ามี column ที่ transformer ต้องใช้ครบ
  read_reviewed_template() template ที่ฝ่ายวิจัย review แล้ว (02_template) → ชื่อ column snake_case ตาม DB
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# column ที่ transformer.build_publication_template อ่านจากไฟล์ต้นทาง (explicit ไม่เดาจาก index)
RAW_REQUIRED_COLUMNS: list[str] = [
    "Description", "Division", "Product Code", "Firstname", "Lastname", "Title",
    "Journal/Conference/Source", "Rank", "Year", "Month", "Online Date", "Publication Date",
    "Database (WoS, Scopus, TCI)", "SDGs Goal",
    'Other Classification ("A"-Excellent, International-Very Good, National-Good)',
]
RAW_OPTIONAL_COLUMNS: list[str] = ["Volume", "Issue", "Pages"]


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_raw(path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """อ่านไฟล์ต้นทาง — raise ValueError ถ้า column บังคับหาย (บอกชื่อครบ ไม่ล้มทีละอันตอน transform)"""
    df = _strip_columns(pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl"))
    missing = [c for c in RAW_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"ไฟล์ต้นทางขาด column ที่จำเป็น: {missing}")
    logger.info("Read %d rows from source file %s", len(df), Path(path).name)
    return df.reset_index(drop=True)


def read_reviewed_template(path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """อ่าน template ที่ review แล้ว (column snake_case) — rename ชื่อเก่า (WoS_SC …) ให้ด้วยเผื่อ template รุ่นก่อน"""
    from src.research.publication.loader import _RENAME_MAP  # local import: loader ดึง sqlalchemy/bigquery

    df = _strip_columns(pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl"))
    df = df.rename(columns=_RENAME_MAP)
    logger.info("Read %d rows from reviewed template %s", len(df), Path(path).name)
    return df.reset_index(drop=True)
