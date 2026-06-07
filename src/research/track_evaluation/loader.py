import logging
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import DECIMAL, NVARCHAR, Integer, Date

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2

_DTYPE_MAP = {
    "weight": DECIMAL(10, 2),
    "quality": DECIMAL(10, 2),
    "contribution": DECIMAL(10, 2),
    "score": DECIMAL(10, 2),
    "reward": Integer(),
    "publication_year": Integer(),
    "order_num": Integer(),
    "publication_date": Date(),
    "product_code": NVARCHAR(50),
    "firstname": NVARCHAR(100),
    "lastname": NVARCHAR(100),
    "rank": NVARCHAR(100),
    "division": NVARCHAR(200),
    "description": NVARCHAR(500),
    "corresponding": NVARCHAR(10),
    "title": NVARCHAR(500),
    "source": NVARCHAR(255),
}

_TEXT_COLS = [
    "product_code", "rc_meeting", "publication_month", "firstname",
    "lastname", "rank", "division", "description", "corresponding", "title", "source",
]


def check_string_lengths(df: pd.DataFrame, engine, schema: str, table: str) -> list:
    insp = inspect(engine)
    try:
        cols = insp.get_columns(table, schema=schema)
    except Exception as e:
        logger.error("ไม่สามารถอ่านโครงสร้างตาราง %s.%s: %s", schema, table, e)
        return []

    varchar_cols = {
        c["name"]: c["type"].length
        for c in cols
        if hasattr(c["type"], "length") and c["type"].length
    }

    errors = []
    for col, max_len in varchar_cols.items():
        if col not in df.columns:
            continue
        series = df[col].dropna().astype(str)
        over = series.apply(len) > max_len
        if over.any():
            rows = (series[over].index + _EXCEL_ROW_OFFSET).tolist()
            logger.warning("Column '%s' ความยาวเกิน %d ที่ Excel rows: %s", col, max_len, rows)
            errors.append((col, max_len, rows))
    return errors


def load_to_mssql(df: pd.DataFrame) -> None:
    for col in _TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    conn_str = (
        f"mssql+pyodbc://{os.getenv('LOCAL_USERNAME')}:{quote(os.getenv('LOCAL_PASSWORD'))}@"
        f"{os.getenv('LOCAL_HOST')}/{os.getenv('RESEARCH_DATABASE')}?"
        "driver=ODBC+Driver+17+for+SQL+Server"
    )
    engine = create_engine(conn_str, fast_executemany=True)
    logger.info("เชื่อมต่อฐานข้อมูลสำเร็จ")

    schema = os.getenv("SCHEMA_DEFAULT")
    table = os.getenv("TRACK_EVALUATION")

    errors = check_string_lengths(df, engine, schema=schema, table=table)
    if errors:
        for col, max_len, rows in errors:
            logger.error("- %s เกิน %d ตัวอักษร ที่ Excel rows: %s", col, max_len, rows)
        raise ValueError("พบข้อความยาวเกินกำหนด ยกเลิกการเขียนข้อมูลลงฐานข้อมูล")

    df = df.map(lambda x: None if (pd.isna(x) or (isinstance(x, str) and x.strip() == "")) else x)

    try:
        df.to_sql(
            name=table,
            con=engine,
            schema=schema,
            index=False,
            if_exists="append",
            chunksize=1000,
            dtype=_DTYPE_MAP,
        )
        logger.info("✅ Insert สำเร็จ %d แถว → %s.%s", len(df), schema, table)
    except SQLAlchemyError:
        logger.exception("SQLAlchemyError ขณะ insert track_evaluation")
        raise


# merge keys สำหรับ UPSERT ไปยัง BigQuery
_BQ_MERGE_KEYS = [
    "product_code", "publication_year", "order_num", "firstname", "lastname", "title",
]

_BQ_STR_COLS = [
    "product_code", "rc_meeting", "publication_month", "firstname", "lastname",
    "rank", "division", "description", "corresponding", "title", "source",
]

_BQ_INT_COLS = ["order_num", "publication_year", "reward"]
_BQ_FLOAT_COLS = ["weight", "quality", "contribution", "score"]


def _prepare_bq_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in _BQ_STR_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string")
    for col in _BQ_INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in _BQ_FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.date
    return df.where(pd.notnull(df), None)


def load_to_bigquery(df: pd.DataFrame) -> None:
    from google.cloud import bigquery

    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(f"ไม่พบไฟล์คีย์ Service Account: {key_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("GCP_DATASET_ID")
    staging_table = (
        f"{project_id}.{dataset_id}."
        f"{os.getenv('GCP_TRACK_EVAL_STAGING_TABLE', 'track_evaluation_staging')}"
    )
    prod_table = (
        f"{project_id}.{dataset_id}."
        f"{os.getenv('GCP_TRACK_EVAL_TABLE_NAME', 'track_evaluation')}"
    )

    df = _prepare_bq_df(df)
    bq = bigquery.Client(project=project_id)
    logger.info("✅ BigQuery client initialized for project %s", project_id)

    prod_schema = bq.get_table(prod_table).schema
    prod_columns = [c.name for c in prod_schema]
    df = df[[c for c in df.columns if c in prod_columns]]

    job_config = bigquery.LoadJobConfig(
        schema=prod_schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
    )
    load_job = bq.load_table_from_dataframe(df, staging_table, job_config=job_config)
    load_job.result()
    logger.info("✅ Loaded %d rows into %s", load_job.output_rows, staging_table)

    update_columns = [c for c in prod_columns if c not in _BQ_MERGE_KEYS]
    update_set = ",\n    ".join(f"{c} = S.{c}" for c in update_columns)
    on_clause = "\n       AND ".join(f"T.{k} = S.{k}" for k in _BQ_MERGE_KEYS)
    merge_sql = f"""
    MERGE `{prod_table}` T
    USING `{staging_table}` S
    ON {on_clause}
    WHEN MATCHED THEN
      UPDATE SET
        {update_set}
    WHEN NOT MATCHED THEN
      INSERT ({', '.join(prod_columns)})
      VALUES ({', '.join(f'S.{c}' for c in prod_columns)})
    """
    merge_job = bq.query(merge_sql)
    merge_job.result()
    logger.info("✅ Merge to %s completed", prod_table)


def export_to_excel(df: pd.DataFrame, output_path: Path) -> Path:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="track_evaluation")
        ws = writer.sheets["track_evaluation"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    logger.info("✅ Export สำเร็จ: %s", output_path)
    return output_path
