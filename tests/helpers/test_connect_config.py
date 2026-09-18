"""ทดสอบ helpers.connect_db.config + factories — ไม่มี infra fallback, error บอกชื่อ env var ครบ (G17) — ไม่ต่อ network"""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

import helpers.connect_db.connection as conn_mod
from helpers.connect_db.bigquery import bigquery_tables
from helpers.connect_db.config import (
    ENV_EXAMPLE_HINT,
    MissingConfigError,
    bigquery_config,
    mssql_config,
    postgres_config,
    require,
)
from helpers.connect_db.mssql import mssql_engine, mssql_target

PG_VARS = ["DB_CONNECTION_MODE", "DB_USERNAME", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME",
           "SSH_HOST", "SSH_PORT", "SSH_USERNAME", "SSH_PKEY", "SSH_PKEY_PASSWORD", "SSH_PASSWORD"]
MSSQL_VARS = ["LOCAL_HOST", "LOCAL_USERNAME", "LOCAL_PASSWORD", "RESEARCH_DATABASE", "SCHEMA_DEFAULT", "MSSQL_ODBC_DRIVER",
              "PUBLICATION_TABLE", "TRACK_EVALUATION"]
BQ_VARS = ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT_ID", "GCP_DATASET_ID", "GCP_PUBLICATION_STAGING_TABLE", "GCP_PUBLICATION_TABLE_NAME"]


@pytest.fixture
def clean_env(monkeypatch):
    """จำลองเครื่องใหม่ที่ยังไม่ได้ copy .env.example → .env"""
    for k in PG_VARS + MSSQL_VARS + BQ_VARS:
        monkeypatch.delenv(k, raising=False)


def _set(monkeypatch, **kv):
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


# ── require / error message ───────────────────────────────────────────────────

def test_missing_vars_listed_all_at_once_with_fix_hint(clean_env):
    with pytest.raises(MissingConfigError) as exc:
        require(["DB_USERNAME", "DB_PASSWORD", "DB_HOST"], "PostgreSQL direct")
    msg = str(exc.value)
    assert "PostgreSQL direct" in msg
    assert "3 ตัว" in msg and "DB_USERNAME, DB_PASSWORD, DB_HOST" in msg      # ครบทุกตัว ไม่ใช่ทีละตัว
    assert ".env.example" in msg and ENV_EXAMPLE_HINT in msg                 # บอกวิธีแก้
    assert exc.value.missing == ["DB_USERNAME", "DB_PASSWORD", "DB_HOST"]
    print("✅ error บอกชื่อ env var ที่ขาดทั้งหมด + วิธีแก้")


def test_blank_value_counts_as_missing(monkeypatch, clean_env):
    monkeypatch.setenv("DB_HOST", "   ")
    with pytest.raises(MissingConfigError, match="DB_HOST"):
        require(["DB_HOST"], "x")


# ── postgres_config: no infra fallbacks ───────────────────────────────────────

def test_ssh_mode_requires_ssh_host_no_192_168_fallback(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="ssh", DB_USERNAME="u", DB_PASSWORD="p", DB_HOST="db", DB_NAME="n", SSH_USERNAME="s", SSH_PASSWORD="x")
    with pytest.raises(MissingConfigError) as exc:
        postgres_config()
    assert exc.value.missing == ["SSH_HOST"]
    assert "192.168" not in str(exc.value)
    print("✅ ssh: ไม่มี fallback 192.168.64.2 — ต้องตั้ง SSH_HOST")


def test_ssh_mode_requires_pkey_or_password(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="ssh", DB_USERNAME="u", DB_PASSWORD="p", DB_HOST="db", DB_NAME="n", SSH_HOST="h", SSH_USERNAME="s")
    with pytest.raises(MissingConfigError, match="SSH_PKEY หรือ SSH_PASSWORD"):
        postgres_config()


def test_direct_mode_requires_db_host_no_localhost_fallback(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="direct", DB_USERNAME="u", DB_PASSWORD="p")
    with pytest.raises(MissingConfigError) as exc:
        postgres_config()
    assert set(exc.value.missing) == {"DB_HOST", "DB_NAME"}
    print("✅ direct: ไม่มี fallback localhost/ic_finance — ต้องตั้ง DB_HOST, DB_NAME")


def test_db_name_argument_replaces_env_requirement(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="direct", DB_USERNAME="u", DB_PASSWORD="p", DB_HOST="db")
    cfg = postgres_config("zeal")
    assert cfg["database"] == "zeal" and cfg["port"] == 5432                 # protocol default คงไว้


def test_protocol_defaults_and_full_ssh_config(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="ssh", DB_USERNAME="u", DB_PASSWORD="p", DB_HOST="10.0.0.5", DB_NAME="n",
         SSH_HOST="bastion", SSH_USERNAME="s", SSH_PKEY="~/.ssh/id", DB_PORT="5433")
    cfg = postgres_config()
    assert (cfg["mode"], cfg["ssh_host"], cfg["ssh_port"], cfg["host"], cfg["port"]) == ("ssh", "bastion", 22, "10.0.0.5", 5433)
    assert cfg["ssh_pkey"] == "~/.ssh/id" and cfg["ssh_password"] is None


def test_invalid_mode_rejected(monkeypatch, clean_env):
    _set(monkeypatch, DB_CONNECTION_MODE="tcp")
    with pytest.raises(MissingConfigError, match="DB_CONNECTION_MODE"):
        postgres_config()


def test_connect_to_db_fails_before_any_network_call(monkeypatch, clean_env):
    def _boom(*a, **k):
        raise AssertionError("ห้ามแตะ network เมื่อ config ไม่ครบ")
    monkeypatch.setattr(conn_mod.psycopg2, "connect", _boom)
    monkeypatch.setattr(conn_mod.sshtunnel, "SSHTunnelForwarder", _boom)
    with pytest.raises(MissingConfigError):
        conn_mod.connect_to_db()
    print("✅ connect_to_db: MissingConfigError ก่อนเปิด socket ใดๆ")


# ── mssql / bigquery ──────────────────────────────────────────────────────────

def test_mssql_config_and_engine_use_env_driver(monkeypatch, clean_env):
    _set(monkeypatch, LOCAL_HOST="h", LOCAL_USERNAME="u", LOCAL_PASSWORD="p", RESEARCH_DATABASE="R", SCHEMA_DEFAULT="dbo",
         MSSQL_ODBC_DRIVER="ODBC Driver 18 for SQL Server", PUBLICATION_TABLE="publications")
    assert mssql_config()["driver"] == "ODBC Driver 18 for SQL Server"
    eng = mssql_engine()                                                       # สร้าง engine ไม่เปิด connection
    assert eng.url.query["driver"] == "ODBC Driver 18 for SQL Server"
    assert mssql_target("PUBLICATION_TABLE") == ("dbo", "publications")


def test_mssql_default_driver_is_17_and_missing_vars_listed(monkeypatch, clean_env):
    _set(monkeypatch, LOCAL_HOST="h", LOCAL_USERNAME="u", LOCAL_PASSWORD="p", RESEARCH_DATABASE="R", SCHEMA_DEFAULT="dbo")
    assert mssql_config()["driver"] == "ODBC Driver 17 for SQL Server"        # behavior เดิมเมื่อไม่ตั้ง
    monkeypatch.delenv("LOCAL_PASSWORD")
    with pytest.raises(MissingConfigError, match="LOCAL_PASSWORD"):
        mssql_config()


def test_bigquery_config_expands_home_and_checks_file(monkeypatch, clean_env, tmp_path):
    key = tmp_path / "sa.json"
    key.write_text("{}")
    monkeypatch.setenv("HOME", str(tmp_path))
    _set(monkeypatch, GOOGLE_APPLICATION_CREDENTIALS="~/sa.json", GCP_PROJECT_ID="proj", GCP_DATASET_ID="Research")
    cfg = bigquery_config()
    assert cfg["key_path"] == str(key)
    assert bigquery_tables("GCP_PUBLICATION_STAGING_TABLE", "publication_staging", "GCP_PUBLICATION_TABLE_NAME", "publications") == (
        "proj.Research.publication_staging", "proj.Research.publications")
    print("✅ bigquery: ~ ขยายได้, ชื่อตารางประกอบจาก env")


def test_bigquery_missing_key_file_names_path(monkeypatch, clean_env, tmp_path):
    _set(monkeypatch, GOOGLE_APPLICATION_CREDENTIALS=str(tmp_path / "nope.json"), GCP_PROJECT_ID="p", GCP_DATASET_ID="d")
    with pytest.raises(MissingConfigError) as exc:
        bigquery_config()
    assert "nope.json" in str(exc.value) and "นอก repo" in str(exc.value)
