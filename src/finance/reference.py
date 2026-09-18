"""
Reference sets จาก master data สำหรับ consistency check ของ ERP (G13 — DAMA "consistency")

erp column → (master table, key column) — ตรงกับ MasterValidator.KEY_COLUMNS
สร้างจากไฟล์ master ใน data/finance/clean/master/ ผ่าน extractor+transformer เดิม (ไม่แตะ DB)
หรือส่ง dict เข้ามาเองจากแหล่งอื่น (เช่น query master table) ก็ได้ — validator รับ dict[str, set[str]]
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import pandas as pd

from src.finance.extractor import MASTER_DIR, MasterExtractor
from src.finance.master.transformer import MasterTransformer
from src.finance.master.validator import KEY_COLUMNS

logger = logging.getLogger(__name__)

# erp_2025 column → master table (key = KEY_COLUMNS[table])
# ไม่มี funds_ctr: ตรวจไฟล์จริง 2026-09-18 พบ erp.funds_ctr = 4 หลัก (3000–3008) แต่ master_fund.fund_id = 8 หลัก
# (10101001…) → คนละระบบรหัส (SAP Fund ≠ Funds Center) ไม่ใช่รหัสใหม่ — รอ Finance บอกว่า funds_ctr ควรเทียบกับ master ไหน (PD-12)
ERP_REFERENCES: dict[str, str] = {
    "cost_ctr_id": "master_cost_ctr",
    "gl_id":       "master_gl",
    "io_goods":    "master_io_goods",
    "io_work":     "master_io_work",
    "io_activity": "master_io_activities",
    "io_project":  "master_io_project",
    "ic_strategy": "master_ic_strategy",   # NUMERIC ใน erp vs TEXT ใน master (G10) → เทียบหลัง normalize
    "mu_strategy": "master_mu_strategy",
}

_DATE_IN_NAME = re.compile(r"(\d{8})")


def normalize_key(s: pd.Series) -> pd.Series:
    """ให้ '3.0' / 3 / ' 3 ' เทียบกับ '3' ได้ — ใช้ทั้งฝั่ง erp และ master"""
    out = s.astype("string").str.strip()
    return out.str.replace(r"\.0+$", "", regex=True)


def master_as_of(filename: str) -> date | None:
    """วันที่จากชื่อไฟล์ master (เช่น Master_GL_20230531.xlsx → 2023-05-31) — ใช้วัด timeliness"""
    m = _DATE_IN_NAME.search(Path(filename).stem)
    if not m:
        return None
    try:
        return pd.to_datetime(m.group(1), format="%Y%m%d").date()
    except ValueError:
        return None


def load_master_reference(master_files: dict[str, str], data_dir: str | Path | None = None) -> tuple[dict[str, set[str]], dict[str, date | None]]:
    """
    อ่านไฟล์ master (table → filename) → ({erp_column: set(keys)}, {erp_column: as_of date})
    ไฟล์ไหนไม่มี → ข้าม column นั้น (log) เพื่อให้ validator ยังรันได้บนเครื่องที่ไม่มี master ครบ
    """
    extractor = MasterExtractor(data_dir or MASTER_DIR)
    refs: dict[str, set[str]] = {}
    as_of: dict[str, date | None] = {}
    for erp_col, table in ERP_REFERENCES.items():
        fname = master_files.get(table)
        if not fname or not (extractor.data_dir / fname).exists():
            logger.warning("reference: ไม่มีไฟล์ master ของ %s (%s) — ข้าม check '%s'", table, fname, erp_col)
            continue
        df = MasterTransformer(extractor.extract(table, fname)).run()
        refs[erp_col] = set(normalize_key(df[KEY_COLUMNS[table]]).dropna().tolist())
        as_of[erp_col] = master_as_of(fname)
    return refs, as_of
