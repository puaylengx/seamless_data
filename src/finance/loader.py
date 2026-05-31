from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from helpers.connect_db import connect_to_db, close_connection

load_dotenv(override=True)

# columns จาก DataFrame ที่ insert เข้า DB
_DB_COLUMNS = [
    "fiscal_year", "fiscal_month", "trimester", "day", "month", "year",
    "doc_no", "doc_date", "funds_ctr", "cost_ctr_id", "cost_owner", "cost_note",
    "io_goods", "io_work", "io_activity", "io_project", "order_description",
    "hr_ot", "gl_id", "gl_description", "amount", "details",
    "mu_strategy", "ic_strategy",
]

TABLE  = "erp_2025"
SCHEMA = "public"


class ErpLoader:
    """Load ERP DataFrame เข้าตาราง erp_2025 ใน PostgreSQL"""

    def __init__(self, database_name: str = None, created_by: str = None):
        self.database_name = database_name  # None → ใช้ DB_NAME จาก .env
        self.created_by = created_by or os.getenv("CREATED_BY")

    def load(self, df: pd.DataFrame, mode: str = "append") -> dict:
        """
        Insert ข้อมูลเข้า erp_2025

        Args:
            df:         DataFrame หลังผ่าน transform และ validate แล้ว
            mode:       "append"  — เพิ่มข้อมูลต่อท้าย (default)
                        "replace" — ล้างตารางแล้ว insert ใหม่ทั้งหมด

        Returns:
            {"rows_inserted": int, "mode": str, "created_by": str | None}
        """
        if mode not in ("append", "replace"):
            raise ValueError(f"mode ต้องเป็น 'append' หรือ 'replace' ได้รับ: '{mode}'")

        cols = [c for c in _DB_COLUMNS if c in df.columns]
        if self.created_by is not None:
            cols = cols + ["created_by"]

        rows = self._prepare_rows(df, cols, created_by=self.created_by)

        conn, tunnel = None, None
        try:
            conn, tunnel = connect_to_db(self.database_name)
            conn.autocommit = False

            with conn.cursor() as cur:
                if mode == "replace":
                    cur.execute(f'TRUNCATE TABLE "{SCHEMA}"."{TABLE}"')

                col_sql = ", ".join(f'"{c}"' for c in cols)
                sql = f'INSERT INTO "{SCHEMA}"."{TABLE}" ({col_sql}) VALUES %s'
                execute_values(cur, sql, rows, page_size=2000)

            conn.commit()
            return {
                "rows_inserted": len(rows),
                "mode": mode,
                "created_by": self.created_by,
            }

        except Exception:
            if conn:
                conn.rollback()
            raise

        finally:
            close_connection(conn, tunnel)

    @staticmethod
    def _prepare_rows(
        df: pd.DataFrame,
        cols: list[str],
        created_by: str | None = None,
    ) -> list[tuple]:
        """แปลง DataFrame → list of tuples
        - NA/NaN → None
        - numpy/pandas scalar → Python native type (int, float, str)
        - ถ้ามี created_by จะ append ต่อท้ายทุก row
        """
        import numpy as np

        def _to_python(v):
            if v is None:
                return None
            if isinstance(v, float) and pd.isna(v):
                return None
            try:
                if pd.isna(v):
                    return None
            except (TypeError, ValueError):
                pass
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v)
            if isinstance(v, (np.bool_,)):
                return bool(v)
            return v

        data_cols = [c for c in cols if c != "created_by"]
        data = df[data_cols].copy()

        rows = []
        for row in data.itertuples(index=False, name=None):
            values = tuple(_to_python(v) for v in row)
            if created_by is not None:
                values = values + (created_by,)
            rows.append(values)

        return rows
