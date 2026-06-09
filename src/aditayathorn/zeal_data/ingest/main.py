"""
Zeal Data — ingest pipeline
  list  — แสดง table names + row counts จาก .mdb
  load  — extract ทุกตารางจาก .mdb แล้ว insert เข้า PostgreSQL
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.append(str(Path(__file__).resolve().parents[4]))

from helpers.find_project_root import find_project_root
from helpers.logger import get_styled_logger
from src.aditayathorn.zeal_data.ingest.extractor import extract_all, list_tables
from src.aditayathorn.zeal_data.ingest.loader import load_all

PROJECT_ROOT = find_project_root(Path(__file__))
LOG_DIR = PROJECT_ROOT / "logs" / "aditayathorn" / "zeal_data"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = get_styled_logger(
    name=__name__,
    log_dir=LOG_DIR,
    log_filename=f"zeal_ingest_{datetime.now():%Y-%m-%d}.log",
    log_level=logging.INFO,
)


def _resolve_mdb_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env_path = os.getenv("ZEAL_MDB_PATH")
    if env_path:
        p = Path(env_path)
        return p if p.is_absolute() else PROJECT_ROOT / p
    raise ValueError(
        "ระบุ path ของ .mdb ไม่ได้ — ใส่ argument หรือตั้งค่า ZEAL_MDB_PATH ใน .env"
    )


def run_list(mdb_path_arg: str | None = None) -> None:
    logger.info("=" * 20 + " List tables " + "=" * 20)
    mdb_path = _resolve_mdb_path(mdb_path_arg)
    logger.info("File: %s", mdb_path)
    tables = list_tables(mdb_path)
    logger.info("พบ %d ตาราง:", len(tables))
    for t in tables:
        logger.info("  - %s", t)


def run_load(mdb_path_arg: str | None = None) -> None:
    logger.info("=" * 20 + " Start load → PostgreSQL " + "=" * 20)
    mdb_path = _resolve_mdb_path(mdb_path_arg)
    logger.info("File: %s", mdb_path)

    tables = extract_all(mdb_path)
    if not tables:
        logger.warning("ไม่มีตารางที่โหลดได้ — ยกเลิก")
        sys.exit(1)

    logger.info("Extract สำเร็จ %d ตาราง — เริ่ม load", len(tables))
    load_all(tables)
    logger.info("🏁 Load complete")


_COMMANDS = {
    "list": run_list,
    "load": run_load,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmds = " | ".join(_COMMANDS)
        print(f"Usage: python main.py <{cmds}> [mdb_path]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd not in _COMMANDS:
        print(f"Unknown command: '{cmd}'. Available: {list(_COMMANDS)}")
        sys.exit(1)
    path_arg = sys.argv[2] if len(sys.argv) > 2 else None
    _COMMANDS[cmd](path_arg)
