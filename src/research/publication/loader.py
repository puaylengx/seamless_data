import logging
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_RENAME_MAP = {
    "WoS_with_JIF-P90": "wos_with_jif_p90",
    "WoS_with_JIF": "wos_with_jif",
    "WoS_SC": "wos_sc",
    "WoS_SS": "wos_ss",
    "WoS_AH": "wos_ah",
    "WoS_ES": "wos_es",
    "Scopus_SJR-10": "scopus_sjr_10",
    "Scopus_Q1": "scopus_q1",
    "Scopus_Q2": "scopus_q2",
    "Scopus_Q3": "scopus_q3",
    "Scopus_Q4": "scopus_q4",
    "Scopus_No_Q": "scopus_no_q",
    "SENSE_ABC": "sense_abc",
    "ERIC": "eric",
    "MathSciNet": "math_sci_net",
    "Pubmed": "pubmed",
    "JSTOR": "jstor",
    "Project_Muse": "project_muse",
    "Other_Inter.Databases": "other_inter",
    "TCI_Group1": "tci_group1",
    "TCI_Group2": "tci_group2",
    "National_Journal": "national_journal",
    "Field": "field",
}

_REQUIRED_COLS = [
    "rank", "group_rank", "description",
    "wos_with_jif_p90", "wos_with_jif", "wos_sc", "wos_ss", "wos_ah", "wos_es",
    "scopus_sjr_10", "scopus_q1", "scopus_q2", "scopus_q3", "scopus_q4", "scopus_no_q",
    "sense_abc", "eric", "math_sci_net", "pubmed", "jstor", "project_muse",
    "other_inter", "tci_group1", "tci_group2", "national_journal",
    "product_code", "firstname", "lastname", "title", "field", "division", "source",
    "publication_month", "publication_year", "publication_calendar_year",
    "publication_budget_year", "effective_date", "national_international",
] + [f"sdg{i}" for i in range(1, 18)]

_STR_COLS = [
    "rank", "group_rank", "description", "product_code", "firstname", "lastname",
    "title", "field", "division", "source", "national_international",
]


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=_RENAME_MAP)
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"คอลัมน์หายไปจาก DataFrame: {missing}")
    df = df[_REQUIRED_COLS].copy()

    dtype_map = {c: "Int64" for c in df.columns if c not in _STR_COLS + ["effective_date"]}
    dtype_map.update({c: "string" for c in _STR_COLS})
    dtype_map["effective_date"] = "datetime64[ns]"
    df = df.astype(dtype_map, errors="ignore")
    df = df.where(pd.notnull(df), None)
    df["effective_date"] = pd.to_datetime(df["effective_date"], errors="coerce").dt.date
    return df


def load_to_mssql(df: pd.DataFrame) -> None:
    df = _prepare_df(df)
    conn_str = (
        f"mssql+pyodbc://{os.getenv('LOCAL_USERNAME')}:"
        f"{quote(os.getenv('LOCAL_PASSWORD'))}@"
        f"{os.getenv('LOCAL_HOST')}/{os.getenv('RESEARCH_DATABASE')}?"
        "driver=ODBC+Driver+17+for+SQL+Server"
    )
    engine = create_engine(conn_str)
    table = os.getenv("PUBLICATION_TABLE")
    schema = os.getenv("SCHEMA_DEFAULT")

    try:
        df.to_sql(name=table, con=engine, schema=schema, index=False,
                  if_exists="append", chunksize=1000)
        logger.info("✅ Insert สำเร็จ %d แถว → %s.%s", len(df), schema, table)
    except SQLAlchemyError:
        logger.exception("SQLAlchemyError ขณะ insert publication")
        raise


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
        f"{os.getenv('GCP_PUBLICATION_STAGING_TABLE', 'publication_staging')}"
    )
    prod_table = (
        f"{project_id}.{dataset_id}."
        f"{os.getenv('GCP_PUBLICATION_TABLE_NAME', 'publications')}"
    )

    df = _prepare_df(df)
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

    merge_keys = ["product_code", "publication_year", "publication_month", "firstname", "lastname", "title"]
    update_columns = [c for c in prod_columns if c not in merge_keys]
    update_set = ",\n    ".join(f"{c} = S.{c}" for c in update_columns)
    merge_sql = f"""
    MERGE `{prod_table}` T
    USING `{staging_table}` S
    ON T.product_code = S.product_code
       AND T.publication_year = S.publication_year
       AND T.publication_month = S.publication_month
       AND T.firstname = S.firstname
       AND T.lastname = S.lastname
       AND T.title = S.title
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
    df = _prepare_df(df)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="publications")
        ws = writer.sheets["publications"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    logger.info("✅ Export สำเร็จ: %s", output_path)
    return output_path
