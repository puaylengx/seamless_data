import io
import logging
import subprocess
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def list_tables(mdb_path: str | Path) -> list[str]:
    """คืน list ชื่อตารางทั้งหมดใน .mdb ไฟล์"""
    result = subprocess.run(
        ["mdb-tables", "-1", str(mdb_path)],
        capture_output=True, text=True, check=True,
    )
    return [t for t in result.stdout.strip().split("\n") if t]


def read_table(mdb_path: str | Path, table_name: str) -> pd.DataFrame:
    """อ่านตารางเดียวจาก .mdb เป็น DataFrame"""
    result = subprocess.run(
        ["mdb-export", str(mdb_path), table_name],
        capture_output=True, text=True, check=True,
    )
    df = pd.read_csv(io.StringIO(result.stdout))
    df.columns = df.columns.str.lower()
    return df


def extract_all(mdb_path: str | Path) -> dict[str, pd.DataFrame]:
    """
    อ่านทุกตารางใน .mdb และคืน dict {table_name: DataFrame}
    ข้ามตารางที่ว่างเปล่าหรืออ่านไม่สำเร็จ
    """
    mdb_path = Path(mdb_path)
    if not mdb_path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ .mdb: {mdb_path}")

    tables = list_tables(mdb_path)
    logger.info("พบ %d ตาราง ใน %s", len(tables), mdb_path.name)

    result = {}
    for table in tables:
        try:
            df = read_table(mdb_path, table)
            if df.empty:
                logger.warning("ตาราง '%s' ว่างเปล่า — ข้าม", table)
                continue
            logger.info("  %-30s %d แถว × %d คอลัมน์", table, len(df), len(df.columns))
            result[table] = df
        except subprocess.CalledProcessError as e:
            logger.error("อ่านตาราง '%s' ไม่สำเร็จ: %s", table, e.stderr.strip())

    return result
