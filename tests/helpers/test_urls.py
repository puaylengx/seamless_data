"""ทดสอบ helpers.connect_db.urls — URL.create() แทน f-string ครอบ 3 โหมด: MSSQL, PostgreSQL ssh, PostgreSQL direct (G16)"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import URL

sys.path.append(str(Path(__file__).resolve().parents[2]))

from helpers.connect_db.urls import mssql_url, postgres_url

NASTY = "p@ss:w/rd%25?&#=ä"   # ทุกอักขระที่ f-string+quote() เคยเสี่ยงพัง


@pytest.fixture
def env(monkeypatch):
    for k in ("LOCAL_USERNAME", "LOCAL_PASSWORD", "LOCAL_HOST", "RESEARCH_DATABASE",
              "DB_USERNAME", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_CONNECTION_MODE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LOCAL_USERNAME", "research_user")
    monkeypatch.setenv("LOCAL_PASSWORD", NASTY)
    monkeypatch.setenv("LOCAL_HOST", "mssql.internal")
    monkeypatch.setenv("RESEARCH_DATABASE", "ResearchDB")
    monkeypatch.setenv("DB_USERNAME", "etl_writer")
    monkeypatch.setenv("DB_PASSWORD", NASTY)
    monkeypatch.setenv("DB_HOST", "pg.internal")
    monkeypatch.setenv("DB_PORT", "5433")


# ── โหมด 1: MSSQL ─────────────────────────────────────────────────────────────

def test_mssql_url_fields_and_driver(env):
    u = mssql_url()
    assert isinstance(u, URL)
    assert u.drivername == "mssql+pyodbc"
    assert (u.username, u.host, u.database) == ("research_user", "mssql.internal", "ResearchDB")
    assert u.password == NASTY                                  # ค่าดิบ ไม่ถูก quote ซ้อน
    assert u.query["driver"] == "ODBC Driver 17 for SQL Server"
    print("✅ MSSQL: fields ครบ, password ค่าดิบถูกต้อง")


def test_mssql_url_string_form_is_valid_and_matches_old_shape(env):
    s = mssql_url().render_as_string(hide_password=False)
    assert s.startswith("mssql+pyodbc://research_user:")
    assert s.endswith("@mssql.internal/ResearchDB?driver=ODBC+Driver+17+for+SQL+Server")
    # round-trip: parse กลับได้ password เดิม (นี่คือสิ่งที่ f-string + quote() ทำผิดได้)
    from sqlalchemy.engine import make_url
    assert make_url(s).password == NASTY


def test_mssql_url_repr_hides_password(env):
    assert NASTY not in str(mssql_url())
    assert NASTY not in repr(mssql_url())
    assert "***" in str(mssql_url())
    print("✅ str/repr ของ URL ซ่อน password (สิ่งที่โผล่ใน traceback/log)")


def test_mssql_url_driver_override(env):
    assert mssql_url(driver="ODBC Driver 18 for SQL Server").query["driver"] == "ODBC Driver 18 for SQL Server"


# ── โหมด 2: PostgreSQL ผ่าน SSH tunnel ───────────────────────────────────────

def test_postgres_url_ssh_uses_localhost_and_tunnel_port(env):
    u = postgres_url("zeal", mode="ssh", local_port=54321)
    assert u.drivername == "postgresql+psycopg2"
    assert (u.host, u.port, u.database, u.username) == ("127.0.0.1", 54321, "zeal", "etl_writer")
    assert u.password == NASTY
    print("✅ ssh: 127.0.0.1 + local_bind_port ไม่ใช่ DB_HOST")


def test_postgres_url_ssh_requires_local_port(env):
    with pytest.raises(ValueError, match="local_port"):
        postgres_url("zeal", mode="ssh")


# ── โหมด 3: PostgreSQL direct ─────────────────────────────────────────────────

def test_postgres_url_direct_uses_db_host_port(env):
    u = postgres_url("ic_finance", mode="direct")
    assert (u.host, u.port, u.database) == ("pg.internal", 5433, "ic_finance")
    print("✅ direct: DB_HOST/DB_PORT")


def test_postgres_url_mode_from_env_and_defaults(env, monkeypatch):
    monkeypatch.setenv("DB_CONNECTION_MODE", "direct")
    monkeypatch.delenv("DB_HOST")
    monkeypatch.delenv("DB_PORT")
    u = postgres_url("ic_finance")
    assert (u.host, u.port) == ("localhost", 5432)
    monkeypatch.setenv("DB_CONNECTION_MODE", "ssh")
    assert postgres_url("x", local_port=1).host == "127.0.0.1"


def test_postgres_url_rejects_unknown_mode(env):
    with pytest.raises(ValueError, match="DB_CONNECTION_MODE"):
        postgres_url("x", mode="tcp")


def test_postgres_url_repr_hides_password(env):
    assert NASTY not in str(postgres_url("x", mode="direct"))
