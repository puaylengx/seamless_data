"""
Track evaluation pipeline
  template  — raw Excel → draft template for review
  pipeline  — processed template → upload (via .env flags; validate fail → exit 1)
  export    — processed template → final Excel
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
from src.research.track_evaluation.extractor import read_raw, read_reviewed_template
from src.research.track_evaluation.transformer import build_track_template, coerce_and_clean
from src.research.track_evaluation.validator import validate_track_evaluation
from src.research.track_evaluation.loader import (
    MERGE_KEYS,
    YEAR_COL,
    bq_summary,
    export_to_excel,
    load_to_bigquery,
    load_to_mssql,
    mssql_summary,
    prepare_for_load,
)
from src.research.reconcile import compare, compare_destinations, summarize

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR      = PROJECT_ROOT / "logs" / "research" / "track_evaluation"
TEMPLATE_DIR = PROJECT_ROOT / "data" / "research" / "track_evaluation" / "02_template"
EXPORT_DIR   = PROJECT_ROOT / "data" / "research" / "track_evaluation" / "03_export"

LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_styled_logger(
    name=__name__,
    log_dir=LOG_DIR,
    log_filename=f"track_evaluation_{datetime.now():%Y-%m-%d_%H-%M-%S}.log",
    log_level=logging.INFO,
)


def run_template(input_path: str) -> Path:
    logger.info("=" * 20 + " Start template mapping " + "=" * 20)
    logger.info("Input: %s", input_path)

    data = read_raw(input_path)
    df_template = build_track_template(data)

    output_path = (
        TEMPLATE_DIR / f"draft_track_evaluation_template_{datetime.today():%Y-%m-%d_%H-%M-%S}.xlsx"
    )
    df_template.to_excel(output_path, index=False)
    logger.info("✅ Saved template to %s", output_path)
    return output_path


def _load_reviewed_template(input_path: str) -> pd.DataFrame:
    """
    อ่าน reviewed template → rename เป็นชื่อ DB → coerce_and_clean → validate
    ใช้ร่วมกันทั้ง MSSQL และ BigQuery เพื่อให้สองปลายทางได้ข้อมูลชุดเดียวกัน
    validate ไม่ผ่าน → sys.exit(1) ไม่เขียนข้อมูลเข้าปลายทางใดๆ
    """
    df = read_reviewed_template(input_path)
    df = coerce_and_clean(df)

    if not validate_track_evaluation(df):
        logger.error("❌ Validation failed. ยกเลิกการเขียนข้อมูลลงฐานข้อมูล")
        sys.exit(1)
    logger.info("✅ Validation passed")
    return df


def reconcile(df: pd.DataFrame, *, mssql: bool, bq: bool) -> bool:
    """
    G4 — หลัง upload เทียบ prepared df กับปลายทางที่เปิดใช้ทีละปี และเทียบ MSSQL ⇄ BigQuery เมื่อเขียนทั้งคู่
    คืน True เมื่อตรงกันหมด — ไม่ raise (source of truth รอ PD-4) แค่ log WARNING ให้คนตัดสิน
    """
    expected = summarize(prepare_for_load(df), YEAR_COL, MERGE_KEYS, label="prepared")
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


def run_export(input_path: str) -> Path:
    logger.info("=" * 20 + " Start export → Excel " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows", len(df))
    if not validate_track_evaluation(df):
        logger.warning("⚠️ Validation พบข้อผิดพลาดบางส่วน")
    output_path = EXPORT_DIR / f"track_evaluation_export_{datetime.now():%Y-%m-%d_%H-%M-%S}.xlsx"
    result = export_to_excel(df, output_path)
    logger.info("🏁 Export complete: %s", result)
    return result


def _env_flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() == "true"


def run_upload_bq(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload → BigQuery " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = _load_reviewed_template(input_path)
    load_to_bigquery(df)
    reconcile(df, mssql=False, bq=True)
    logger.info("🏁 Upload BigQuery complete")


def run_pipeline(input_path: str) -> None:
    """
    Orchestrator — load และ validate ครั้งเดียว แล้วตัดสินใจจาก .env:
      - Upload MSSQL ถ้า TRACK_EVAL_UPLOAD_MSSQL=true
      - Upload BigQuery ถ้า TRACK_EVAL_UPLOAD_BQ=true
      - default (false/false) → log เท่านั้น ไม่แตะ DB
    """
    upload_mssql = _env_flag("TRACK_EVAL_UPLOAD_MSSQL")
    upload_bq = _env_flag("TRACK_EVAL_UPLOAD_BQ")

    logger.info("=" * 20 + " Start pipeline " + "=" * 20)
    logger.info("  TRACK_EVAL_UPLOAD_MSSQL = %s", upload_mssql)
    logger.info("  TRACK_EVAL_UPLOAD_BQ    = %s", upload_bq)
    logger.info("Input: %s", input_path)

    if not upload_mssql and not upload_bq:
        logger.info("⏭️  ทั้ง MSSQL และ BigQuery ถูก skip (flags = false)")
        logger.info("   ตั้งค่าใน .env เพื่อ upload")
        logger.info("🏁 Pipeline complete")
        return

    # อ่าน + validate ครั้งเดียว แล้วเขียนทั้งสองปลายทางจาก DataFrame ชุดเดียวกัน
    df = _load_reviewed_template(input_path)

    if upload_mssql:
        logger.info("--- Upload → MSSQL ---")
        load_to_mssql(df)

    if upload_bq:
        logger.info("--- Upload → BigQuery ---")
        load_to_bigquery(df)

    # Reconcile ปลายทางที่เขียนจริง + MSSQL ⇄ BigQuery ถ้าเขียนทั้งคู่ (G4)
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
    command, path = sys.argv[1], sys.argv[2]
    if command not in _COMMANDS:
        print(f"Unknown command: '{command}'. Available: {list(_COMMANDS)}")
        sys.exit(1)
    _COMMANDS[command](path)
