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
from src.research.publication.transformer import (
    get_parse_database_data,
    get_rank,
    get_group_rank,
    get_clean_budget_year,
    get_clean_publication_month,
    get_clean_year,
    get_format_effective_date,
    get_national_international,
    get_extract_sdg_values,
)
from src.research.publication.validator import validate_publication
from src.research.publication.loader import load_to_mssql, load_to_bigquery, export_to_excel, _RENAME_MAP

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

_DB_KEYS = [
    "WoS_with_JIF-P90", "WoS_with_JIF", "WoS_SC", "WoS_SS", "WoS_AH", "WoS_ES",
    "Scopus_SJR-10", "Scopus_Q1", "Scopus_Q2", "Scopus_Q3", "Scopus_Q4", "Scopus_No_Q",
    "SENSE_ABC", "ERIC", "MathSciNet", "Pubmed", "JSTOR", "Project_Muse",
    "Other_Inter.Databases", "TCI_Group1", "TCI_Group2", "National_Journal", "Field",
]

_COLUMN_ORDER = [
    "rank", "group_rank", "description",
    "Database (WoS, Scopus, TCI)",
    "wos_with_jif_p90", "wos_with_jif", "wos_sc", "wos_ss", "wos_ah", "wos_es",
    "scopus_sjr_10", "scopus_q1", "scopus_q2", "scopus_q3", "scopus_q4", "scopus_no_q",
    "sense_abc", "eric", "math_sci_net", "pubmed", "jstor", "project_muse",
    "other_inter", "tci_group1", "tci_group2", "national_journal", "field",
    "division", "product_code", "firstname", "lastname", "title", "source",
    "volume", "issue", "pages",
    "publication_month", "publication_year", "publication_calendar_year",
    "publication_budget_year", "effective_date", "national_international",
] + [f"sdg{i}" for i in range(1, 18)]


def _process_database(raw_data: pd.DataFrame) -> pd.DataFrame:
    parsed_db = get_parse_database_data(raw_data.copy())
    logger.info("Parsed Database (WoS, Scopus, TCI) column")

    df = pd.DataFrame()
    df["Database (WoS, Scopus, TCI)"] = raw_data["Database (WoS, Scopus, TCI)"]
    for k in _DB_KEYS:
        df[k] = parsed_db.get(k, None)

    return df


def _process_clean(raw_data: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame()
    df["rank"] = get_rank(raw_data)
    df["group_rank"] = get_group_rank(raw_data)
    df["publication_month"] = get_clean_publication_month(raw_data)
    df["publication_year"] = get_clean_year(raw_data)
    df["publication_calendar_year"] = get_clean_year(raw_data)
    df["publication_budget_year"] = get_clean_budget_year(raw_data)
    df["effective_date"] = get_format_effective_date(raw_data)
    df["national_international"] = get_national_international(raw_data)

    sdg_df = raw_data["SDGs Goal"].apply(
        lambda x: pd.Series(get_extract_sdg_values(x) if pd.notna(x) else {})
    )
    return pd.concat([df, sdg_df], axis=1)


def run_template(input_path: str) -> Path:
    logger.info("=" * 20 + " Start template " + "=" * 20)
    logger.info("Input: %s", input_path)

    raw_data = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows from source file", len(raw_data))

    db_data = _process_database(raw_data)
    clean_data = _process_clean(raw_data)

    template = pd.DataFrame({
        "description": raw_data["Description"],
        "division": raw_data["Division"],
        "product_code": raw_data["Product Code"],
        "firstname": raw_data["Firstname"],
        "lastname": raw_data["Lastname"],
        "title": raw_data["Title"],
        "source": raw_data["Journal/Conference/Source"],
        "volume": raw_data["Volume"] if "Volume" in raw_data.columns else None,
        "issue": raw_data["Issue"] if "Issue" in raw_data.columns else None,
        "pages": raw_data["Pages"] if "Pages" in raw_data.columns else None,
    })

    template = template.reset_index(drop=True)
    db_data = db_data.reset_index(drop=True)
    clean_data = clean_data.reset_index(drop=True)

    df_combined = pd.concat([template, db_data, clean_data], axis=1)
    df_combined = df_combined.rename(columns=_RENAME_MAP)

    for col in _COLUMN_ORDER:
        if col not in df_combined.columns:
            df_combined[col] = None
    df_final = df_combined[_COLUMN_ORDER]

    logger.info("Built template: %d rows × %d columns", len(df_final), len(df_final.columns))

    output_path = TEMPLATE_DIR / f"draft_publications_template_{datetime.today():%Y-%m-%d}.xlsx"
    df_final.to_excel(output_path, index=False)
    logger.info("✅ Exported draft template to %s", output_path)

    return output_path


def run_upload(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload → MSSQL " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows", len(df))
    if not validate_publication(df):
        logger.error("❌ Validation failed. ยกเลิกการเขียนข้อมูลลงฐานข้อมูล")
        sys.exit(1)
    logger.info("✅ Validation passed")
    load_to_mssql(df)
    logger.info("🏁 Upload MSSQL complete")


def run_upload_bq(input_path: str) -> None:
    logger.info("=" * 20 + " Start upload → BigQuery " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows", len(df))
    if not validate_publication(df):
        logger.error("❌ Validation failed. ยกเลิกการ upload")
        sys.exit(1)
    logger.info("✅ Validation passed")
    load_to_bigquery(df)
    logger.info("🏁 Upload BigQuery complete")


def run_export(input_path: str) -> Path:
    logger.info("=" * 20 + " Start export → Excel " + "=" * 20)
    logger.info("Input: %s", input_path)
    df = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows", len(df))
    if not validate_publication(df):
        logger.error("❌ Validation failed. ยกเลิกการ export")
        sys.exit(1)
    logger.info("✅ Validation passed")
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

    df = pd.read_excel(input_path, engine="openpyxl")
    logger.info("Read %d rows", len(df))

    if not validate_publication(df):
        logger.error("❌ Validation failed.")
        sys.exit(1)
    logger.info("✅ Validation passed")

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
