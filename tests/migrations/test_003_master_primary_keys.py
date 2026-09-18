"""ตรวจ migration 003 (G5) ให้สอดคล้องกับ MasterValidator.KEY_COLUMNS และ loader._TABLE_COLUMNS — ไม่ต่อ DB"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from migrations.migrate import discover
from src.finance.master.loader import _TABLE_COLUMNS
from src.finance.master.validator import KEY_COLUMNS

_MIG = Path(__file__).resolve().parents[2] / "migrations" / "finance"
SQL = (_MIG / "003_add_master_primary_keys.sql").read_text(encoding="utf-8")
SQL_004 = (_MIG / "004_dedupe_io_goods.sql").read_text(encoding="utf-8")


def test_003_is_discovered_after_002_and_before_004():
    ids = [m.id for m in discover("finance")]
    assert ids.index("finance/002_create_master_tables") < ids.index("finance/003_add_master_primary_keys") < ids.index("finance/004_dedupe_io_goods")


def test_every_master_table_gets_pk_on_its_validator_key():
    pks = dict(re.findall(r"ALTER TABLE\s+(\w+)\s+ADD CONSTRAINT\s+\w+\s+PRIMARY KEY\s*\((\w+)\);", SQL))
    assert pks == KEY_COLUMNS, {"missing": set(KEY_COLUMNS) - set(pks), "extra": set(pks) - set(KEY_COLUMNS)}
    print("✅ PK ครบทุก master table และตรงกับ KEY_COLUMNS ของ MasterValidator")


def test_003_adds_constraints_only_no_data_change():
    """003 = ตรวจจับ ไม่ใช่แก้ไข — ห้ามมี DELETE/UPDATE/INSERT/DROP/TRUNCATE"""
    code = "\n".join(line for line in SQL.splitlines() if not line.strip().startswith("--"))
    for kw in ("DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE"):
        assert kw not in code.upper(), kw
    assert code.upper().count("ALTER TABLE") == len(KEY_COLUMNS)
    print("✅ 003: ADD PRIMARY KEY อย่างเดียว")


def test_004_is_manual_and_dedupes_exact_duplicates_only():
    """004 ลบเฉพาะแถว io_goods ที่เหมือนกันทุก loader column และต้องมี manual marker + guard PD-11"""
    from migrations.migrate import MANUAL_MARKER
    assert MANUAL_MARKER in SQL_004 and "PD-11" in SQL_004
    m = re.search(r"DELETE FROM master_io_goods a USING master_io_goods b\s+WHERE(.*?);", SQL_004, re.S)
    assert m and "a.ctid < b.ctid" in m.group(1)
    for col in _TABLE_COLUMNS["master_io_goods"]:
        assert f"a.{col}" in m.group(1), col
    code = "\n".join(line for line in SQL_004.splitlines() if not line.strip().startswith("--"))
    assert code.upper().count("DELETE FROM") == 1 and "master_io_goods" in code
    assert not re.search(r"\b(master_fund|master_gl|master_cost_ctr|erp_2025)\b", code)
    print("✅ 004: manual, io_goods เท่านั้น, exact duplicate เท่านั้น")


def test_no_erp_changes_in_003():
    assert "erp_2025" not in SQL.replace("-- ไม่รวม erp_2025", "")   # แค่ comment เท่านั้น (PD-3)
