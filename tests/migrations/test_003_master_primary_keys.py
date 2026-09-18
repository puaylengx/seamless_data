"""ตรวจ migration 003 (G5) ให้สอดคล้องกับ MasterValidator.KEY_COLUMNS และ loader._TABLE_COLUMNS — ไม่ต่อ DB"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from migrations.migrate import discover
from src.finance.master.loader import _TABLE_COLUMNS
from src.finance.master.validator import KEY_COLUMNS

SQL = (Path(__file__).resolve().parents[2] / "migrations" / "finance" / "003_add_master_primary_keys.sql").read_text(encoding="utf-8")


def test_003_is_discovered_after_002():
    ids = [m.id for m in discover("finance")]
    assert ids[-1] == "finance/003_add_master_primary_keys"
    assert ids.index("finance/002_create_master_tables") < ids.index("finance/003_add_master_primary_keys")


def test_every_master_table_gets_pk_on_its_validator_key():
    pks = dict(re.findall(r"ALTER TABLE (\w+) ADD CONSTRAINT \w+ PRIMARY KEY \((\w+)\);", SQL))
    assert pks == KEY_COLUMNS, {"missing": set(KEY_COLUMNS) - set(pks), "extra": set(pks) - set(KEY_COLUMNS)}
    print("✅ PK ครบทุก master table และตรงกับ KEY_COLUMNS ของ MasterValidator")


def test_dedupe_only_removes_exact_duplicates_over_all_loader_columns():
    """DELETE ต้องเทียบทุก business column ของ loader (IS NOT DISTINCT FROM) — ไม่ใช่แค่ key — จึงลบเฉพาะแถวที่เหมือนกันจริง"""
    for table, cols in _TABLE_COLUMNS.items():
        m = re.search(rf"DELETE FROM {table} a USING {table} b\s+WHERE(.*?);", SQL, re.S)
        assert m, f"no dedupe for {table}"
        body = m.group(1)
        assert "a.ctid < b.ctid" in body
        key = KEY_COLUMNS[table]
        assert f"a.{key} = b.{key}" in body
        for col in cols:
            if col == key:
                continue
            assert f"a.{col}" in body and "IS NOT DISTINCT FROM" in body, f"{table}: {col} not compared"
        # ลำดับ: dedupe ก่อน ADD PRIMARY KEY ของตารางเดียวกัน
        assert SQL.index(m.group(0)) < SQL.index(f"ALTER TABLE {table} ADD CONSTRAINT")
    print("✅ dedupe เทียบครบทุก column, มาก่อน PK")


def test_no_erp_changes_in_003():
    assert "erp_2025" not in SQL.replace("-- ไม่รวม erp_2025", "")   # แค่ comment เท่านั้น (PD-3)
