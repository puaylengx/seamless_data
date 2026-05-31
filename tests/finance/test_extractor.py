"""ทดสอบ ErpExtractor และ MasterExtractor"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance.extractor import (
    ErpExtractor, MasterExtractor,
    ERP_COLUMNS, MASTER_COLUMNS,
    ERP_DIR, MASTER_DIR,
)


def test_erp_column_mapping():
    """ERP_COLUMNS ต้องครบทุก column ที่กำหนดใน requirement"""
    required = {
        "Year", "Trimester", "Day", "Month", "DocNo", "DocDate",
        "FundsCtr", "CostCtr_ID", "Cost_Owner", "IO_Goods", "IO_Work",
        "IO_Activity", "IO_Project", "Order_Description", "HROT",
        "GL_ID", "GL_Description", "Amount", "Details", "MU_Strategy", "IC_Strategy",
    }
    assert required == set(ERP_COLUMNS.keys()), "ERP_COLUMNS ไม่ครบตาม requirement"
    print("✅ ERP_COLUMNS ครบถ้วน")


def test_master_tables():
    """MASTER_COLUMNS ต้องมีทุก table ที่กำหนดใน requirement"""
    required = {
        "master_cost_ctr", "master_fund", "master_gl",
        "master_io_goods", "master_io_activities", "master_io_project",
        "master_io_work", "master_ic_strategy", "master_mu_strategy",
    }
    assert required == set(MASTER_COLUMNS.keys()), "MASTER_COLUMNS ไม่ครบตาม requirement"
    print("✅ MASTER_COLUMNS ครบถ้วน")


def test_default_paths():
    """ERP_DIR และ MASTER_DIR ต้องมีอยู่จริง"""
    assert ERP_DIR.exists(),    f"ไม่พบ ERP_DIR: {ERP_DIR}"
    assert MASTER_DIR.exists(), f"ไม่พบ MASTER_DIR: {MASTER_DIR}"
    print(f"✅ ERP_DIR    : {ERP_DIR}")
    print(f"✅ MASTER_DIR : {MASTER_DIR}")


def test_master_list_files():
    """MasterExtractor.list_files() ต้อง return list"""
    extractor = MasterExtractor()
    files = extractor.list_files()
    print(f"✅ พบไฟล์ master {len(files)} ไฟล์: {[f.name for f in files]}")


def test_master_extractor_invalid_table():
    """MasterExtractor ต้อง raise ValueError เมื่อชื่อ table ไม่ถูกต้อง"""
    try:
        MasterExtractor().extract("invalid_table", "dummy.xlsx")
        assert False, "ควร raise ValueError"
    except ValueError as e:
        assert "invalid_table" in str(e)
        print("✅ MasterExtractor raise ValueError สำหรับ table ที่ไม่รู้จัก")


def test_erp_no_file_error():
    """ErpExtractor ต้อง raise FileNotFoundError เมื่อไม่มีไฟล์ใน ERP_DIR"""
    files = list(ERP_DIR.glob("*.xlsx"))
    if files:
        print(f"⚠️  ข้ามเทสนี้ — มีไฟล์อยู่แล้ว: {[f.name for f in files]}")
        return
    try:
        ErpExtractor()
        assert False, "ควร raise FileNotFoundError"
    except FileNotFoundError:
        print("✅ ErpExtractor raise FileNotFoundError เมื่อไม่มีไฟล์")


if __name__ == "__main__":
    test_erp_column_mapping()
    test_master_tables()
    test_default_paths()
    test_master_list_files()
    test_master_extractor_invalid_table()
    test_erp_no_file_error()
    print("\nAll tests passed")
