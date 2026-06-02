from __future__ import annotations

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from helpers.connect_db import connect_to_db, close_connection

load_dotenv(override=True)

SCHEMA = "public"

# columns ที่ insert ต่อ table (ไม่รวม DB-managed: created_at, updated_at)
_TABLE_COLUMNS: dict[str, list[str]] = {
    "master_cost_ctr": [
        "cost_center_id", "cost_center_description",
        "cost_center_eng", "cost_center_th", "status",
    ],
    "master_fund": [
        "fund_id", "fund_description", "status",
    ],
    "master_gl": [
        "group_id", "gl_id", "gl_description", "group_description", "status",
    ],
    "master_io_goods": [
        "io_good_id", "io_good_description", "status",
    ],
    "master_io_activities": [
        "io_activity_id", "io_activity_description", "status",
    ],
    "master_io_project": [
        "io_project_id", "io_project_description",
        "cost_center_id", "ic_strategy_id", "mu_strategy_id", "status",
    ],
    "master_io_work": [
        "io_work_id", "io_work_description", "status",
    ],
    "master_ic_strategy": [
        "ic_strategy_id", "start_year", "end_year",
        "name_en", "ic_strategy_description", "status",
    ],
    "master_mu_strategy": [
        "mu_strategy_id", "start_year", "end_year",
        "name_en", "mu_strategy_description", "status",
    ],
}


class MasterLoader:
    """Load master DataFrame เข้า PostgreSQL"""

    def __init__(self, database_name: str = None, created_by: str = None):
        self.database_name = database_name
        self.created_by = created_by or os.getenv("CREATED_BY")

    def load(self, df: pd.DataFrame, table_name: str, mode: str = "replace") -> dict:
        """
        Insert ข้อมูล master เข้า DB

        Args:
            df:         DataFrame หลังผ่าน MasterTransformer แล้ว
            table_name: ชื่อ table เช่น "master_gl"
            mode:       "replace" — ล้างแล้ว insert ใหม่ (default สำหรับ master)
                        "append"  — เพิ่มต่อท้าย
        """
        if table_name not in _TABLE_COLUMNS:
            raise ValueError(f"ไม่รู้จัก table '{table_name}'\nที่รองรับ: {list(_TABLE_COLUMNS)}")
        if mode not in ("append", "replace"):
            raise ValueError(f"mode ต้องเป็น 'append' หรือ 'replace'")

        cols = [c for c in _TABLE_COLUMNS[table_name] if c in df.columns]
        if self.created_by is not None:
            cols = cols + ["created_by"]

        rows = self._prepare_rows(df, cols, created_by=self.created_by)

        conn, tunnel = None, None
        try:
            conn, tunnel = connect_to_db(self.database_name)
            conn.autocommit = False

            with conn.cursor() as cur:
                if mode == "replace":
                    cur.execute(f'TRUNCATE TABLE "{SCHEMA}"."{table_name}"')

                col_sql = ", ".join(f'"{c}"' for c in cols)
                sql = f'INSERT INTO "{SCHEMA}"."{table_name}" ({col_sql}) VALUES %s'
                execute_values(cur, sql, rows, page_size=1000)

            conn.commit()
            return {
                "table": table_name,
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
            if isinstance(v, np.integer):
                return int(v)
            if isinstance(v, np.floating):
                return float(v)
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
