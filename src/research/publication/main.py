"""
Publication pipeline
  template  — raw Excel → draft template for review
  pipeline  — processed template → export Excel + upload (via .env flags)
  upload    — processed template → MSSQL
  upload_bq — processed template → BigQuery
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from helpers.logger import get_styled_logger
from src.research.publication.extractor import read_raw, read_reviewed_template
from src.research.publication.transformer import build_publication_template, coerce_and_clean
from src.research.publication.validator import validate_publication
from src.research.publication.loader import (
    MERGE_KEYS,
    YEAR_COL,
    _RENAME_MAP,
    _prepare_df,
    bq_summary,
    export_to_excel,
    load_to_bigquery,
    load_to_mssql,
    mssql_summary,
)
from src.research.reconcile import compare, compare_destinations, summarize

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR      = PROJECT_ROOT / "logs" / "research" / "publication" / "check_value"
TEMPLATE_DIR = PROJECT_ROOT / "data" / "research" / "publication" / "02_template"
EXPORT_DIR   = PROJECT_ROOT / "data" / "research" / "publication" / "03_export"

LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_styled_logger(
    name=__name__,
    log_dir=LOG_DIR,
    log_filename=f"check_value_{datetime.now():%Y-%m-%d}.log",
    log_level=logging.INFO,
)

def run_template(input_path: str) -> Path:
    """extract (raw) → transform (draft template) → เขียนไฟล์ให้ฝ่ายวิจัย review — ไม่แตะ DB"""
    logger.info("=" * 20 + " Start template " + "=" * 20)
    logger.info("Input: %s", input_path)

    raw_data = read_raw(input_path)
    df_final = build_publication_template(raw_data, rename_map=_RENAME_MAP)
    logger.info("Built template: %d rows × %d columns", len(df_final), len(df_final.columns))

    output_path = TEMPLATE_DIR / f"draft_publications_template_{datetime.today():%Y-%m-%d}.xlsx"
    df_final.to_excel(output_path, index=False)
    logger.info("✅ Exported draft template to %s", output_path)
    return output_path


def _load_reviewed_template(input_path: str) -> pd.DataFrame:
    """
    extract (reviewed template) → coerce_and_clean → validate — ใช้ร่วมกันทุกคำสั่งที่ตามด้วย export/upload
    validate ไม่ผ่าน → sys.exit(1) ไม่เขียนข้อมูลเข้าปลายทางใดๆ (pattern เดียวกับ track_evaluation)
    """
    df = read_reviewed_template(input_path)
    df = coerce_and_clean(df)
    if not validate_publication(df):
        logger.error("❌ Validation failed. ยกเลิก")
        sys.exit(1)
    logger.info("✅ Validation passed")
    return df


def reconcile(df: pd.DataFrame, *, mssql: bool, bq: bool) -> bool:
    """
    G4 — หลัง upload เทียบสิ่งที่เตรียมเขียน (prepared df) กับปลายทางที่เปิดใช้ทีละปี
    และถ้าเขียนทั้ง MSSQL + BigQuery เทียบสอง DB ต่อกันด้วย
    คืน True เมื่อตรงกันหมด — ไม่ raise เพราะ source of truth ยังรอ PD-4 (log WARNING ให้คนตัดสิน)
    """
    expected = summarize(_prepare_df(df), YEAR_COL, MERGE_KEYS, label="prepared")
    years = expected.years
    logger.info("--- Reconcile (%d ปี: %s) ---", len(years), years)

    ok = True
    summaries = []
    for enabled, name, fetch in ((mssql, "MSSQL", mssql_summary), (bq, "BigQuery", bq_summary)):
        if not enabled:
            continue
        try:
            actual = fetch(years)
        except Exception:
            logger.exception("reconcile: อ่านสรุปจาก %s ไม่สำเร็จ — ข้าม (ข้อมูลถูกเขียนไปแล้ว ต้องตรวจเอง)", name)
            ok = False
            continue
        ok = compare(expected, actual).ok and ok
        summaries.append(actual)

    if len(summaries) == 2:
        ok = compare_destinations(summaries[0], summaries[1]).ok and ok
    return ok


def run_upload(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload → MSSQL " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = _load_reviewed_template(input_path)
    load_to_mssql(df)
    reconcile(df, mssql=True, bq=False)
    logger.info("🏁 Upload MSSQL complete")


def run_upload_bq(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload → BigQuery " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = _load_reviewed_template(input_path)
    load_to_bigquery(df)
    reconcile(df, mssql=False, bq=True)
    logger.info("🏁 Upload BigQuery complete")


def run_export(input_path: str) -> Path:
    logger.info("=" * 20 + " Start export → Excel " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = _load_reviewed_template(input_path)
    output_path = EXPORT_DIR / f"publications_export_{datetime.now():%Y-%m-%d_%H-%M-%S}.xlsx"
    result = export_to_excel(df, output_path)
    logger.info("🏁 Export complete: %s", result)
    return result


def _env_flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() == "true"


def run_pipeline(input_path: str) -> None:
    """
    Orchestrator หลัก — load และ validate ครั้งเดียว แล้วตัดสินใจจาก .env:
      - Export Excel เสมอ (default)
      - PUBLICATION_UPLOAD_MSSQL=true  → upload ไป MSSQL ด้วย
      - PUBLICATION_UPLOAD_BQ=true     → upload ไป BigQuery ด้วย
    """
    upload_mssql = _env_flag("PUBLICATION_UPLOAD_MSSQL")
    upload_bq = _env_flag("PUBLICATION_UPLOAD_BQ")

    logger.info("=" * 20 + " Start pipeline " + "=" * 20)
    logger.info("  PUBLICATION_UPLOAD_MSSQL = %s", upload_mssql)
    logger.info("  PUBLICATION_UPLOAD_BQ    = %s", upload_bq)
    logger.info("Input: %s", input_path)

    df = _load_reviewed_template(input_path)

    # 1. Export Excel เสมอ
    output_path = EXPORT_DIR / f"publications_export_{datetime.now():%Y-%m-%d_%H-%M-%S}.xlsx"
    export_to_excel(df, output_path)

    # 2. Upload MSSQL (opt-in)
    if upload_mssql:
        logger.info("--- Upload → MSSQL ---")
        load_to_mssql(df)
    else:
        logger.info("⏭️  MSSQL upload skipped (PUBLICATION_UPLOAD_MSSQL=false)")

    # 3. Upload BigQuery (opt-in)
    if upload_bq:
        logger.info("--- Upload → BigQuery ---")
        load_to_bigquery(df)
    else:
        logger.info("⏭️  BigQuery upload skipped (PUBLICATION_UPLOAD_BQ=false)")

    # 4. Reconcile ปลายทางที่เขียนจริง (G4)
    if upload_mssql or upload_bq:
        reconcile(df, mssql=upload_mssql, bq=upload_bq)

    logger.info("🏁 Pipeline complete")


_COMMANDS = {
    "template": run_template,
    "pipeline": run_pipeline,
    "export": run_export,
    "upload": run_upload,
    "upload_bq": run_upload_bq,
}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        cmds = " | ".join(_COMMANDS)
        print(f"Usage: python main.py <{cmds}> <input_excel_path>")
        sys.exit(1)
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd not in _COMMANDS:
        print(f"Unknown command: '{cmd}'. Available: {list(_COMMANDS)}")
        sys.exit(1)
    _COMMANDS[cmd](path)
