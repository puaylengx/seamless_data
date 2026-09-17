import logging
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import DECIMAL, NVARCHAR, Integer, Date

from src.research.reconcile import Summary, fetch_summary_sql

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2

# key ที่ระบุ "รายการประเมินเดียวกัน" — ใช้ทั้ง BigQuery MERGE และ reconciliation distinct count
MERGE_KEYS = ["product_code", "publication_year", "order_num", "firstname", "lastname", "title"]
YEAR_COL = "publication_year"

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


_INT_COLS = ["order_num", "publication_year", "reward"]
_FLOAT_COLS = ["weight", "quality", "contribution", "score"]


def prepare_for_load(df: pd.DataFrame) -> pd.DataFrame:
    """
    เตรียม DataFrame (หลัง coerce_and_clean + validate) ให้พร้อมเขียน — **ตัวเดียวสำหรับทั้ง MSSQL และ BigQuery** (G4)

    เดิม MSSQL ทำ strip/blank→None inline ส่วน BigQuery มี prep แยกของตัวเอง (ไม่ strip) → สอง DB ได้ค่าต่างกัน
      - text: strip whitespace, ค่าว่าง → null  (dtype "string" — เหมือน BigQuery path เดิม)
      - int:  order_num / publication_year / reward → Int64 (nullable)
      - float: weight / quality / contribution / score
      - publication_date → date object
    คืน DataFrame ใหม่ ไม่แก้ตัวที่รับเข้ามา — **คง typed dtypes ไว้** เพราะ BigQuery load ผ่าน pyarrow
    รับ Int64/string อยู่แล้ว (พฤติกรรมเดิมที่พิสูจน์แล้วบน prod); MSSQL path แปลงเป็น object/None เองใน
    _for_pyodbc() ก่อนส่ง psycopg2/pyodbc (ทำเฉพาะที่นั่น ไม่ใช่ที่นี่ — ตัดสินใจ 2026-09-17 ใน PR #9)
    """
    df = df.copy()
    for col in _TEXT_COLS:
        if col in df.columns:
            stripped = df[col].astype("string").str.strip()
            df[col] = stripped.mask(stripped == "", pd.NA)
    for col in _INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in _FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="coerce").dt.date
    return df


def _for_pyodbc(df: pd.DataFrame) -> pd.DataFrame:
    """MSSQL เท่านั้น: ทุก null → None และ dtype → object ให้ pyodbc/to_sql รับได้ (พฤติกรรมเดิมของ MSSQL path)"""
    return df.astype(object).where(pd.notnull(df), None)


def _mssql_engine():
    conn_str = (
        f"mssql+pyodbc://{os.getenv('LOCAL_USERNAME')}:{quote(os.getenv('LOCAL_PASSWORD'))}@"
        f"{os.getenv('LOCAL_HOST')}/{os.getenv('RESEARCH_DATABASE')}?"
        "driver=ODBC+Driver+17+for+SQL+Server"
    )
    return create_engine(conn_str, fast_executemany=True)


def _mssql_target() -> tuple[str, str]:
    return os.getenv("SCHEMA_DEFAULT"), os.getenv("TRACK_EVALUATION")


def _bq_tables() -> tuple[str, str]:
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("GCP_DATASET_ID")
    staging = f"{project_id}.{dataset_id}.{os.getenv('GCP_TRACK_EVAL_STAGING_TABLE', 'track_evaluation_staging')}"
    prod = f"{project_id}.{dataset_id}.{os.getenv('GCP_TRACK_EVAL_TABLE_NAME', 'track_evaluation')}"
    return staging, prod


def load_to_mssql(df: pd.DataFrame) -> None:
    df = _for_pyodbc(prepare_for_load(df))
    engine = _mssql_engine()
    logger.info("เชื่อมต่อฐานข้อมูลสำเร็จ")

    schema, table = _mssql_target()

    errors = check_string_lengths(df, engine, schema=schema, table=table)
    if errors:
        for col, max_len, rows in errors:
            logger.error("- %s เกิน %d ตัวอักษร ที่ Excel rows: %s", col, max_len, rows)
        raise ValueError("พบข้อความยาวเกินกำหนด ยกเลิกการเขียนข้อมูลลงฐานข้อมูล")

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


def load_to_bigquery(df: pd.DataFrame) -> None:
    from google.cloud import bigquery

    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(f"ไม่พบไฟล์คีย์ Service Account: {key_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

    project_id = os.getenv("GCP_PROJECT_ID")
    staging_table, prod_table = _bq_tables()

    df = prepare_for_load(df)
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

    update_columns = [c for c in prod_columns if c not in MERGE_KEYS]
    update_set = ",\n    ".join(f"{c} = S.{c}" for c in update_columns)
    on_clause = "\n       AND ".join(f"T.{k} = S.{k}" for k in MERGE_KEYS)
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


# ── reconciliation (G4) ───────────────────────────────────────────────────────

def mssql_summary(years: list[int], engine=None) -> Summary:
    """สรุปแถว/ปี ใน MSSQL จริงสำหรับปีที่เพิ่ง upload — engine ส่งมาได้เพื่อ test"""
    engine = engine or _mssql_engine()
    schema, table = _mssql_target()
    with engine.connect() as conn:
        return fetch_summary_sql(
            execute=lambda sql: conn.execute(text(sql)).fetchall(),
            table_fqn=f"[{schema}].[{table}]",
            year_col=YEAR_COL, key_cols=MERGE_KEYS, years=years, label="MSSQL",
        )


def bq_summary(years: list[int], client=None) -> Summary:
    """สรุปแถว/ปี ใน BigQuery prod table จริง — client ส่งมาได้เพื่อ test"""
    if client is None:
        from google.cloud import bigquery
        client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
    _, prod_table = _bq_tables()
    return fetch_summary_sql(
        execute=lambda sql: [tuple(r.values()) for r in client.query(sql).result()],
        table_fqn=f"`{prod_table}`",
        year_col=YEAR_COL, key_cols=MERGE_KEYS, years=years, label="BigQuery",
    )


def export_to_excel(df: pd.DataFrame, output_path: Path) -> Path:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="track_evaluation")
        ws = writer.sheets["track_evaluation"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    logger.info("✅ Export สำเร็จ: %s", output_path)
    return output_path
