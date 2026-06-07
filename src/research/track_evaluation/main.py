"""
Track evaluation pipeline
  template  — raw Excel → draft template for review
  pipeline  — processed template → upload (via .env flags)
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
from src.research.track_evaluation.transformer import build_track_template
from src.research.track_evaluation.validator import validate_track_evaluation
from src.research.track_evaluation.loader import load_to_mssql, load_to_bigquery, export_to_excel

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

    data = pd.read_excel(input_path)
    logger.info("Loaded %d rows", len(data))

    df_template = build_track_template(data)

    output_path = (
        TEMPLATE_DIR / f"draft_track_evaluation_template_{datetime.today():%Y-%m-%d_%H-%M-%S}.xlsx"
    )
    df_template.to_excel(output_path, index=False)
    logger.info("✅ Saved template to %s", output_path)
    return output_path


def run_upload(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload " + "=" * 20)
    logger.info("Input: %s", input_path)

    df = pd.read_excel(
        input_path,
        usecols=[
            "Product Code", "RC Meeting", "Publication_month", "orderNum",
            "Publication_year", "PublicationDate", "Firstname", "Lastname",
            "Rank", "Division", "Description", "Weight", "Quality",
            "Corresponding", "Contribution", "SCORE", "REWARD", "Title", "Source",
        ],
    )
    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))

    df.rename(
        columns={
            "Product Code": "product_code",
            "RC Meeting": "rc_meeting",
            "Publication_month": "publication_month",
            "orderNum": "order_num",
            "Publication_year": "publication_year",
            "PublicationDate": "publication_date",
            "Firstname": "firstname",
            "Lastname": "lastname",
            "Rank": "rank",
            "Division": "division",
            "Description": "description",
            "Weight": "weight",
            "Quality": "quality",
            "Corresponding": "corresponding",
            "Contribution": "contribution",
            "SCORE": "score",
            "REWARD": "reward",
            "Title": "title",
            "Source": "source",
        },
        inplace=True,
    )

    # fill missing month/year/order_num from publication_date
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce")

        if "publication_year" in df.columns:
            mask = df["publication_year"].isna() | (df["publication_year"].astype(str).str.strip() == "")
            df.loc[mask, "publication_year"] = df.loc[mask, "publication_date"].dt.year
            logger.info("เติม publication_year จาก publication_date แล้ว %d แถว", mask.sum())

        if "publication_month" in df.columns:
            mask = df["publication_month"].isna() | (df["publication_month"].astype(str).str.strip() == "")
            df.loc[mask, "publication_month"] = df.loc[mask, "publication_date"].dt.strftime("%B")
            logger.info("เติม publication_month จาก publication_date แล้ว %d แถว", mask.sum())

        if "order_num" in df.columns:
            mask = df["order_num"].isna()
            df.loc[mask, "order_num"] = df.loc[mask, "publication_date"].dt.month
            logger.info("เติม order_num จาก publication_date แล้ว %d แถว", mask.sum())

    # round decimal columns to 2 places
    for col in ["weight", "quality", "contribution", "score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").apply(
                lambda x: round(x, 2) if pd.notnull(x) else None
            )

    if not validate_track_evaluation(df):
        logger.warning("⚠️ Validation พบข้อผิดพลาดบางส่วน แต่ยังดำเนินการ insert ต่อ")

    load_to_mssql(df)
    logger.info("🏁 Upload complete")


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

    df = pd.read_excel(
        input_path,
        usecols=[
            "Product Code", "RC Meeting", "Publication_month", "orderNum",
            "Publication_year", "PublicationDate", "Firstname", "Lastname",
            "Rank", "Division", "Description", "Weight", "Quality",
            "Corresponding", "Contribution", "SCORE", "REWARD", "Title", "Source",
        ],
    )
    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))

    df.rename(
        columns={
            "Product Code": "product_code", "RC Meeting": "rc_meeting",
            "Publication_month": "publication_month", "orderNum": "order_num",
            "Publication_year": "publication_year", "PublicationDate": "publication_date",
            "Firstname": "firstname", "Lastname": "lastname", "Rank": "rank",
            "Division": "division", "Description": "description", "Weight": "weight",
            "Quality": "quality", "Corresponding": "corresponding",
            "Contribution": "contribution", "SCORE": "score", "REWARD": "reward",
            "Title": "title", "Source": "source",
        },
        inplace=True,
    )

    if not validate_track_evaluation(df):
        logger.warning("⚠️ Validation พบข้อผิดพลาดบางส่วน แต่ยังดำเนินการ upload ต่อ")

    load_to_bigquery(df)
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

    if upload_mssql:
        run_upload(input_path)

    if upload_bq:
        run_upload_bq(input_path)


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
