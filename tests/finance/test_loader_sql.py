"""ยืนยันว่า finance loaders ใช้ DML เท่านั้น (DELETE FROM ไม่ใช่ TRUNCATE) — G7 least privilege — ไม่ต่อ DB"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

import src.finance.loader as erp_mod
import src.finance.master.loader as master_mod
from src.finance.loader import ErpLoader
from src.finance.master.loader import MasterLoader


class _Cursor:
    def __init__(self, log):
        self._log = log

    def execute(self, sql, *_):
        self._log.append(sql)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Conn:
    def __init__(self):
        self.sql: list[str] = []
        self.autocommit = None
        self.committed = self.rolled_back = False
    def cursor(self):
        return _Cursor(self.sql)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def fake_db(monkeypatch):
    conn = _Conn()
    for mod in (erp_mod, master_mod):
        monkeypatch.setattr(mod, "connect_to_db", lambda *_a, **_k: (conn, None))
        monkeypatch.setattr(mod, "close_connection", lambda *_a, **_k: None)
        monkeypatch.setattr(mod, "execute_values", lambda cur, sql, rows, **_k: conn.sql.append(sql))
    monkeypatch.setenv("ALLOW_REPLACE", "true")
    return conn


def _ddl(sql_list):
    return [s for s in sql_list if any(k in s.upper() for k in ("TRUNCATE", "DROP ", "CREATE ", "ALTER "))]


def test_erp_replace_uses_delete_not_truncate(fake_db):
    ErpLoader(created_by="t").load(pd.DataFrame({"doc_no": [1], "gl_id": ["5"], "amount": [1.0]}), mode="replace")
    assert fake_db.sql[0] == 'DELETE FROM "public"."erp_2025"'
    assert fake_db.sql[1].startswith('INSERT INTO "public"."erp_2025"')
    assert _ddl(fake_db.sql) == []
    assert fake_db.committed and fake_db.autocommit is False   # DELETE + INSERT อยู่ใน transaction เดียว
    print("✅ ErpLoader replace: DELETE FROM → INSERT ใน transaction เดียว ไม่มี DDL")


def test_erp_append_issues_insert_only(fake_db):
    ErpLoader(created_by="t").load(pd.DataFrame({"doc_no": [1], "gl_id": ["5"], "amount": [1.0]}), mode="append")
    assert len(fake_db.sql) == 1 and fake_db.sql[0].startswith("INSERT INTO")


def test_master_replace_uses_delete_not_truncate(fake_db):
    MasterLoader(created_by="t").load(pd.DataFrame({"fund_id": ["F1"], "status": ["active"]}), table_name="master_fund", mode="replace")
    assert fake_db.sql[0] == 'DELETE FROM "public"."master_fund"'
    assert _ddl(fake_db.sql) == []
    print("✅ MasterLoader replace: DELETE FROM ไม่มี DDL")


def test_no_truncate_anywhere_in_finance_loaders():
    for f in (Path(erp_mod.__file__), Path(master_mod.__file__)):
        code = "\n".join(line for line in f.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("#"))
        assert "TRUNCATE" not in code, f.name
