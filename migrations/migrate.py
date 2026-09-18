"""
รัน migration SQL files เข้า PostgreSQL พร้อมบันทึกว่าไฟล์ไหน apply ไปแล้ว (G6)

ใช้:
  python migrations/migrate.py                 # ทุก section ของ PostgreSQL
  python migrations/migrate.py finance         # เฉพาะ section
  python migrations/migrate.py --dry-run       # รันจริงใน transaction แล้ว ROLLBACK — ไม่เปลี่ยน DB
  python migrations/migrate.py --status        # แสดงว่าไฟล์ไหน applied/pending ไม่แตะ DB นอกจากอ่าน schema_migrations

กติกา (team-project-instructions ข้อ 5 / Data Architect):
  - ทุก schema change = ไฟล์ migration ใหม่เท่านั้น ห้ามแก้ไฟล์ที่ apply แล้ว
    → ถ้า checksum ของไฟล์ที่ apply แล้วเปลี่ยน สคริปต์จะหยุดทันที
  - migration ทั้งหมดของหนึ่งรอบอยู่ใน transaction เดียว (PostgreSQL รองรับ DDL แบบ transactional)
    ล้มตรงไหน → rollback ทั้งหมด ไม่มีสถานะครึ่งๆ กลางๆ
  - ตาราง schema_migrations ถูกสร้างอัตโนมัติครั้งแรก

โครงสร้าง:
  migrations/<section>/NNN_*.sql          → PostgreSQL, รันด้วยสคริปต์นี้ (section ใน PG_SECTIONS เท่านั้น)
  migrations/research/bigquery/*.sql      → BigQuery DDL (บันทึกเป็น source of truth — รันผ่าน bq/console)
  migrations/research/mssql/*.sql         → MSSQL DDL (reverse-engineered — รันผ่าน SSMS/sqlcmd)
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from helpers.connect_db import close_connection, connect_to_db
from helpers.logger import get_styled_logger

MIGRATIONS_DIR = Path(__file__).resolve().parent

# section ที่เป็น PostgreSQL และรันด้วยสคริปต์นี้ — research/* เป็น BigQuery/MSSQL ห้ามรันที่นี่
PG_SECTIONS = ["finance"]

TRACKING_TABLE = "schema_migrations"
_CREATE_TRACKING = f"""
CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
  id          TEXT        PRIMARY KEY,           -- "<section>/<file stem>" เช่น finance/001_create_erp_2025
  checksum    TEXT        NOT NULL,              -- sha256 ของไฟล์ตอน apply
  applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  applied_by  TEXT
)
"""

logger = get_styled_logger(
    name=__name__,
    log_dir=MIGRATIONS_DIR.parent / "logs" / "migrations",
    log_filename=f"migrate_{datetime.now():%Y-%m-%d}.log",
    log_level=logging.INFO,
)


@dataclass(frozen=True)
class Migration:
    id: str          # finance/001_create_erp_2025
    path: Path
    checksum: str

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


class MigrationError(RuntimeError):
    pass


# ── discovery ─────────────────────────────────────────────────────────────────

def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover(section: str = "all", root: Path = MIGRATIONS_DIR) -> list[Migration]:
    """หาไฟล์ migration ของ PostgreSQL เรียงตามชื่อไฟล์ (NNN_ prefix) ภายใน section"""
    sections = PG_SECTIONS if section == "all" else [section]
    if section != "all" and section not in PG_SECTIONS:
        raise MigrationError(
            f"'{section}' ไม่ใช่ section ของ PostgreSQL (รองรับ: {PG_SECTIONS}) — "
            "research/bigquery และ research/mssql รันผ่านเครื่องมือของปลายทางนั้น"
        )
    found: list[Migration] = []
    for sec in sections:
        folder = root / sec
        if not folder.is_dir():
            raise MigrationError(f"ไม่พบ folder: {folder}")
        for f in sorted(folder.glob("*.sql")):
            found.append(Migration(id=f"{sec}/{f.stem}", path=f, checksum=_checksum(f)))
    return found


# ── tracking ──────────────────────────────────────────────────────────────────

def applied_migrations(cur) -> dict[str, str]:
    """{id: checksum} ของ migration ที่ apply แล้ว — สร้างตาราง tracking ถ้ายังไม่มี"""
    cur.execute(_CREATE_TRACKING)
    cur.execute(f"SELECT id, checksum FROM {TRACKING_TABLE}")
    return {row[0]: row[1] for row in cur.fetchall()}


def plan(migrations: list[Migration], applied: dict[str, str]) -> list[Migration]:
    """คืนเฉพาะที่ยังไม่ apply; raise ถ้าไฟล์ที่ apply แล้วถูกแก้ (ห้ามแก้ migration เก่า)"""
    pending = []
    for m in migrations:
        if m.id in applied:
            if applied[m.id] != m.checksum:
                raise MigrationError(
                    f"{m.id} ถูก apply ไปแล้วแต่เนื้อหาไฟล์เปลี่ยน (checksum ไม่ตรง) — "
                    "ห้ามแก้ migration ที่รันเข้า DB แล้ว ให้สร้างไฟล์ใหม่แทน"
                )
            continue
        pending.append(m)
    return pending


# ── apply ─────────────────────────────────────────────────────────────────────

def apply(conn, migrations: list[Migration], *, dry_run: bool, applied_by: str | None) -> list[Migration]:
    """
    รัน migration ที่ pending ทั้งหมดใน transaction เดียว
    dry_run=True → รันทุกไฟล์จริง (จับ syntax/dependency error ได้) แล้ว ROLLBACK ไม่ COMMIT
    คืน list ที่รัน (หรือจะรัน)
    """
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            applied = applied_migrations(cur)
            pending = plan(migrations, applied)
            logger.info("applied แล้ว %d · pending %d%s", len(applied), len(pending), " (DRY RUN)" if dry_run else "")
            for m in pending:
                logger.info("  ▶ %s", m.id)
                cur.execute(m.sql)
                cur.execute(
                    f"INSERT INTO {TRACKING_TABLE} (id, checksum, applied_by) VALUES (%s, %s, %s)",
                    (m.id, m.checksum, applied_by),
                )
        if dry_run:
            conn.rollback()
            logger.info("↩️  DRY RUN: rollback แล้ว — DB ไม่เปลี่ยน (%d ไฟล์รันผ่าน)", len(pending))
        else:
            conn.commit()
            logger.info("✅ Migration สำเร็จ — apply %d ไฟล์", len(pending))
        return pending
    except Exception:
        conn.rollback()
        logger.exception("❌ Migration ล้มเหลว — rollback ทั้งหมดแล้ว")
        raise


def status(conn, migrations: list[Migration]) -> None:
    conn.autocommit = False
    with conn.cursor() as cur:
        applied = applied_migrations(cur)
    conn.rollback()  # CREATE TABLE IF NOT EXISTS ของ tracking ไม่ต้องคงไว้ในโหมด status
    for m in migrations:
        if m.id not in applied:
            mark = "pending"
        elif applied[m.id] == m.checksum:
            mark = "applied"
        else:
            mark = "APPLIED BUT FILE CHANGED ⚠️"
        logger.info("  %-40s %s", m.id, mark)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _use_migration_credentials() -> None:
    """ถ้าตั้ง MIGRATION_DB_USERNAME/PASSWORD (role schema_owner — docs/db-roles.md) ให้ใช้แทน user ของ pipeline"""
    user = os.getenv("MIGRATION_DB_USERNAME")
    if user:
        os.environ["DB_USERNAME"] = user
        os.environ["DB_PASSWORD"] = os.getenv("MIGRATION_DB_PASSWORD", "")
        logger.info("ใช้ MIGRATION_DB_USERNAME แทน DB_USERNAME")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL migrations with tracking")
    parser.add_argument("section", nargs="?", default="all", help=f"หนึ่งใน {PG_SECTIONS} หรือ all")
    parser.add_argument("--dry-run", action="store_true", help="รันใน transaction แล้ว rollback")
    parser.add_argument("--status", action="store_true", help="แสดง applied/pending เท่านั้น")
    args = parser.parse_args(argv)

    try:
        migrations = discover(args.section)
    except MigrationError as e:
        logger.error("❌ %s", e)
        return 1

    _use_migration_credentials()
    conn, tunnel = None, None
    try:
        conn, tunnel = connect_to_db()
        if args.status:
            status(conn, migrations)
        else:
            apply(conn, migrations, dry_run=args.dry_run, applied_by=os.getenv("CREATED_BY"))
        return 0
    except MigrationError as e:
        logger.error("❌ %s", e)
        return 1
    finally:
        close_connection(conn, tunnel)


if __name__ == "__main__":
    sys.exit(main())
