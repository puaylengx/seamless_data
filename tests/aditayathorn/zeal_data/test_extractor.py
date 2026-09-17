"""ทดสอบ zeal_data extractor — อ่าน .mdb ผ่าน mdb-tools (G1)

mock subprocess.run ทั้งหมด: ไม่ต้องมี mdb-tools ในเครื่อง/CI และไม่แตะไฟล์ .mdb จริง
"""
import logging
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3]))

import src.aditayathorn.zeal_data.ingest.extractor as ex


class _Completed:
    def __init__(self, stdout="", stderr=""):
        self.stdout, self.stderr, self.returncode = stdout, stderr, 0


@pytest.fixture
def fake_mdb(monkeypatch, tmp_path):
    """สร้างไฟล์ .mdb ปลอม + จำลอง mdb-tables / mdb-export ตาม table ที่กำหนด"""
    mdb = tmp_path / "Data.mdb"
    mdb.write_bytes(b"")
    state = {"tables": [], "export": {}, "calls": []}

    def _run(cmd, **kwargs):
        state["calls"].append(cmd)
        if cmd[0] == "mdb-tables":
            return _Completed(stdout="\n".join(state["tables"]) + "\n")
        if cmd[0] == "mdb-export":
            table = cmd[2]
            out = state["export"][table]
            if isinstance(out, Exception):
                raise out
            return _Completed(stdout=out)
        raise AssertionError(f"unexpected command {cmd}")

    monkeypatch.setattr(ex.subprocess, "run", _run)
    state["path"] = mdb
    return state


# ── list_tables ───────────────────────────────────────────────────────────────

def test_list_tables_parses_one_per_line_and_drops_blanks(fake_mdb):
    fake_mdb["tables"] = ["Customer", "Order Detail", ""]
    assert ex.list_tables(fake_mdb["path"]) == ["Customer", "Order Detail"]
    assert fake_mdb["calls"][0][:2] == ["mdb-tables", "-1"]
    print("✅ list_tables: 1 ชื่อต่อบรรทัด, ตัดบรรทัดว่าง")


# ── read_table ────────────────────────────────────────────────────────────────

def test_read_table_lowercases_columns(fake_mdb):
    fake_mdb["export"] = {"Customer": "ID,Customer Name,Amount\n1,ACME,10.5\n"}
    df = ex.read_table(fake_mdb["path"], "Customer")
    assert list(df.columns) == ["id", "customer name", "amount"]
    assert len(df) == 1 and df["amount"].iloc[0] == 10.5
    assert fake_mdb["calls"][-1] == ["mdb-export", str(fake_mdb["path"]), "Customer"]
    print("✅ read_table: column → lowercase (กัน quoted identifier ใน PostgreSQL)")


# ── extract_all ───────────────────────────────────────────────────────────────

def test_extract_all_missing_file_raises_before_calling_mdb_tools(fake_mdb, tmp_path):
    with pytest.raises(FileNotFoundError):
        ex.extract_all(tmp_path / "nope.mdb")
    assert fake_mdb["calls"] == []


def test_extract_all_skips_empty_tables(fake_mdb, caplog):
    fake_mdb["tables"] = ["Customer", "Empty"]
    fake_mdb["export"] = {"Customer": "id\n1\n", "Empty": "id\n"}
    with caplog.at_level(logging.WARNING, logger="src.aditayathorn.zeal_data.ingest.extractor"):
        result = ex.extract_all(fake_mdb["path"])
    assert list(result) == ["Customer"]
    assert "Empty" in caplog.text
    print("✅ extract_all: ตารางว่างถูกข้ามพร้อม warning")


def test_extract_all_logs_and_continues_on_export_error(fake_mdb, caplog):
    fake_mdb["tables"] = ["Broken", "Customer"]
    fake_mdb["export"] = {
        "Broken": subprocess.CalledProcessError(1, ["mdb-export"], stderr="corrupt page"),
        "Customer": "id\n1\n",
    }
    with caplog.at_level(logging.ERROR, logger="src.aditayathorn.zeal_data.ingest.extractor"):
        result = ex.extract_all(fake_mdb["path"])
    assert list(result) == ["Customer"]
    assert "Broken" in caplog.text and "corrupt page" in caplog.text
    print("✅ extract_all: ตารางที่ export พังถูก log แล้วไปต่อ ไม่ล้มทั้ง run")


def test_extract_all_preserves_original_table_names_as_keys(fake_mdb):
    fake_mdb["tables"] = ["Order Detail"]
    fake_mdb["export"] = {"Order Detail": "ID\n1\n"}
    result = ex.extract_all(fake_mdb["path"])
    # ชื่อเดิมคงไว้ — loader._sanitize_name เป็นคนแปลงเป็น snake_case
    assert list(result) == ["Order Detail"]
    assert list(result["Order Detail"].columns) == ["id"]
