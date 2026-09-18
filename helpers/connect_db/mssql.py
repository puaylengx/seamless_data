"""MSSQL (research) — engine factory ตัวเดียวสำหรับ publication และ track_evaluation (G17)"""
from __future__ import annotations

from sqlalchemy import create_engine

from helpers.connect_db.config import mssql_config
from helpers.connect_db.urls import mssql_url


def mssql_engine(**engine_kwargs):
    """
    SQLAlchemy engine จาก .env (LOCAL_HOST/LOCAL_USERNAME/LOCAL_PASSWORD/RESEARCH_DATABASE)
    driver จาก MSSQL_ODBC_DRIVER (default "ODBC Driver 17 for SQL Server") — เปลี่ยนได้โดยไม่แก้โค้ด
    ขาด env → MissingConfigError ก่อนสร้าง engine
    """
    cfg = mssql_config()
    return create_engine(mssql_url(driver=cfg["driver"]), **engine_kwargs)


def mssql_target(table_env: str) -> tuple[str, str]:
    """(schema, table) จาก .env — table_env เช่น "PUBLICATION_TABLE" หรือ "TRACK_EVALUATION" """
    from helpers.connect_db.config import require

    cfg = require(["SCHEMA_DEFAULT", table_env], f"MSSQL target ({table_env})")
    return cfg["SCHEMA_DEFAULT"], cfg[table_env]
