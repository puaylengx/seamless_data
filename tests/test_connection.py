"""ทดสอบการเชื่อมต่อฐานข้อมูล"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import psycopg2.extras
from helpers.connect_db import connect_to_db, close_connection


def test_connection():
    conn, tunnel = None, None
    try:
        conn, tunnel = connect_to_db()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT version();")
            print(f"Version  : {cur.fetchone()['version']}")

            cur.execute("SELECT current_database();")
            print(f"Database : {cur.fetchone()['current_database']}")

        return True

    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        return False

    finally:
        close_connection(conn, tunnel)


if __name__ == "__main__":
    sys.exit(0 if test_connection() else 1)
