"""ทดสอบ migrations/migrate.py — discovery, tracking table, checksum guard, dry-run rollback (G6) — ไม่ต่อ DB

หมายเหตุ: โฟลเดอร์นี้ตั้งใจไม่มี __init__.py (เหมือน tests/helpers) — ถ้ามี pytest จะมอง tests/migrations
เป็น package ชื่อ "migrations" แล้วบัง migrations/ ของจริงที่ project root
"""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from migrations.migrate import (
    PG_SECTIONS,
    TRACKING_TABLE,
    Migration,
    MigrationError,
    apply,
    discover,
    plan,
    status,
)


# ── fakes ─────────────────────────────────────────────────────────────────────

class _Cursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        self.conn.sql.append((sql.strip(), params))
        if sql.strip().startswith("INSERT INTO schema_migrations"):
            self.conn.rows_inserted.append(params)
        if "boom" in sql:
            raise RuntimeError("syntax error near boom")

    def fetchall(self):
        return list(self.conn.applied.items())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Conn:
    def __init__(self, applied=None):
        self.applied = applied or {}
        self.sql = []
        self.rows_inserted = []
        self.autocommit = None
        self.committed = self.rolled_back = False

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "finance").mkdir()
    (tmp_path / "finance" / "001_a.sql").write_text("CREATE TABLE a (id int);", encoding="utf-8")
    (tmp_path / "finance" / "002_b.sql").write_text("CREATE TABLE b (id int);", encoding="utf-8")
    (tmp_path / "research" / "bigquery").mkdir(parents=True)
    (tmp_path / "research" / "bigquery" / "001_bq.sql").write_text("CREATE TABLE `p.d.t` (x INT64);", encoding="utf-8")
    return tmp_path


# ── discover ──────────────────────────────────────────────────────────────────

def test_discover_only_pg_sections_sorted_with_checksum(repo):
    ms = discover("all", root=repo)
    assert [m.id for m in ms] == ["finance/001_a", "finance/002_b"]     # research/* ไม่ถูกหยิบ
    assert all(len(m.checksum) == 64 for m in ms)
    print("✅ discover: เฉพาะ PG section เรียงตามชื่อ")


def test_discover_rejects_non_pg_section(repo):
    with pytest.raises(MigrationError, match="research/bigquery"):
        discover("research", root=repo)
    assert PG_SECTIONS == ["finance"]


def test_discover_missing_folder(tmp_path):
    with pytest.raises(MigrationError, match="ไม่พบ folder"):
        discover("finance", root=tmp_path)


def test_real_repo_migrations_are_discoverable():
    ms = discover("all")
    assert [m.id for m in ms][:2] == ["finance/001_create_erp_2025", "finance/002_create_master_tables"]


# ── plan ──────────────────────────────────────────────────────────────────────

def _m(i, checksum="c"):
    return Migration(id=i, path=Path(i), checksum=checksum)


def test_plan_skips_applied_and_keeps_order():
    ms = [_m("finance/001", "x"), _m("finance/002", "y"), _m("finance/003", "z")]
    assert [m.id for m in plan(ms, {"finance/001": "x"})] == ["finance/002", "finance/003"]


def test_plan_refuses_modified_applied_migration():
    with pytest.raises(MigrationError, match="ห้ามแก้ migration"):
        plan([_m("finance/001", "new")], {"finance/001": "old"})
    print("✅ checksum guard: แก้ไฟล์ที่ apply แล้ว → หยุด")


# ── apply ─────────────────────────────────────────────────────────────────────

def test_apply_creates_tracking_runs_pending_and_commits(repo):
    conn = _Conn(applied={"finance/001_a": discover("all", root=repo)[0].checksum})
    done = apply(conn, discover("all", root=repo), dry_run=False, applied_by="tester")
    assert [m.id for m in done] == ["finance/002_b"]
    assert conn.autocommit is False and conn.committed and not conn.rolled_back
    assert conn.sql[0][0].startswith(f"CREATE TABLE IF NOT EXISTS {TRACKING_TABLE}")
    assert any(s == "CREATE TABLE b (id int);" for s, _ in conn.sql)
    assert not any(s == "CREATE TABLE a (id int);" for s, _ in conn.sql)      # applied แล้ว ไม่รันซ้ำ
    assert conn.rows_inserted == [("finance/002_b", done[0].checksum, "tester")]
    print("✅ apply: สร้าง tracking, รันเฉพาะ pending, บันทึก, commit")


def test_apply_dry_run_executes_everything_then_rolls_back(repo):
    conn = _Conn()
    done = apply(conn, discover("all", root=repo), dry_run=True, applied_by=None)
    assert len(done) == 2
    assert any(s == "CREATE TABLE a (id int);" for s, _ in conn.sql)         # รันจริงเพื่อจับ error
    assert conn.rolled_back and not conn.committed
    print("✅ dry-run: รันทุกไฟล์แล้ว rollback ไม่ commit")


def test_apply_failure_rolls_back_everything(repo):
    (repo / "finance" / "003_bad.sql").write_text("CREATE TABLE boom (id int);", encoding="utf-8")
    conn = _Conn()
    with pytest.raises(RuntimeError, match="boom"):
        apply(conn, discover("all", root=repo), dry_run=False, applied_by=None)
    assert conn.rolled_back and not conn.committed
    print("✅ ล้มกลางทาง → rollback ทั้งชุด")


def test_apply_refuses_when_applied_file_changed(repo):
    conn = _Conn(applied={"finance/001_a": "stale-checksum"})
    with pytest.raises(MigrationError):
        apply(conn, discover("all", root=repo), dry_run=False, applied_by=None)
    assert conn.rolled_back


# ── status ────────────────────────────────────────────────────────────────────

def test_status_reads_only_and_rolls_back(repo, caplog):
    import logging
    ms = discover("all", root=repo)
    conn = _Conn(applied={"finance/001_a": ms[0].checksum, "finance/002_b": "changed"})
    with caplog.at_level(logging.INFO, logger="migrations.migrate"):
        status(conn, ms)
    assert conn.rolled_back and not conn.committed
    assert "finance/001_a" in caplog.text and "applied" in caplog.text
    assert "APPLIED BUT FILE CHANGED" in caplog.text
    assert not any(s.startswith("INSERT") for s, _ in conn.sql)
