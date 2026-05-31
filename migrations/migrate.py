"""
รัน migration SQL files เข้า database
ใช้: python migrations/migrate.py [finance|all]
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from helpers.connect_db import connect_to_db, close_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent


def run_sql_file(cur, sql_file: Path) -> None:
    sql = sql_file.read_text(encoding="utf-8")
    cur.execute(sql)
    print(f"  ✅ {sql_file.name}")


def migrate(section: str = "all") -> None:
    if section == "all":
        folders = sorted(MIGRATIONS_DIR.iterdir())
        folders = [f for f in folders if f.is_dir()]
    else:
        folders = [MIGRATIONS_DIR / section]
        if not folders[0].exists():
            print(f"❌ ไม่พบ folder: {folders[0]}")
            sys.exit(1)

    conn, tunnel = None, None
    try:
        conn, tunnel = connect_to_db()
        conn.autocommit = False

        for folder in folders:
            sql_files = sorted(folder.glob("*.sql"))
            if not sql_files:
                continue

            print(f"\n── {folder.name} ──────────────────────")
            with conn.cursor() as cur:
                for sql_file in sql_files:
                    run_sql_file(cur, sql_file)

        conn.commit()
        print("\n✅ Migration สำเร็จ")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Migration ล้มเหลว: {e}")
        raise

    finally:
        close_connection(conn, tunnel)


if __name__ == "__main__":
    section = sys.argv[1] if len(sys.argv) > 1 else "all"
    migrate(section)
