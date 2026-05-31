"""ทดสอบ ErpValidator และ convert_amount"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance.transformer import ErpTransformer
from src.finance.validator import ErpValidator, NULLABLE_COLUMNS


# ── helpers ───────────────────────────────────────────────────────────────────

def _valid_df() -> pd.DataFrame:
    return pd.DataFrame({
        # bigint NOT NULL
        "fiscal_year":  pd.array([2025], dtype="Int64"),
        "fiscal_month": pd.array([3],    dtype="Int64"),
        "trimester":    pd.array([1],    dtype="Int64"),
        "day":          pd.array([3],    dtype="Int64"),
        "month":        pd.array([12],   dtype="Int64"),
        "year":         pd.array([2024], dtype="Int64"),
        "doc_no":       pd.array([3000028712], dtype="Int64"),
        # date NOT NULL
        "doc_date":     ["2024-12-03"],
        # text NOT NULL
        "funds_ctr":    ["3001"],
        "cost_ctr_id":  ["C3001000"],
        "gl_id":        ["5302050010"],
        "gl_description": ["ค่าเบี้ยประกัน"],
        "details":      ["คชจ.ประชุม"],
        # decimal NOT NULL
        "amount":       [1108.00],
        # nullable
        "cost_owner":       [pd.NA],
        "cost_note":        [pd.NA],
        "io_goods":         [pd.NA],
        "io_work":          ["Z30000000000"],
        "io_activity":      [pd.NA],
        "io_project":       [pd.NA],
        "order_description":[pd.NA],
        "hr_ot":            [pd.NA],
        "mu_strategy":      [pd.NA],
        "ic_strategy":      [pd.NA],
    })


# ── convert_amount ────────────────────────────────────────────────────────────

def test_convert_amount_basic():
    df = pd.DataFrame({"amount": ["1108.00", "500.5", "250"]})
    result = ErpTransformer(df).convert_amount().df
    assert result["amount"].iloc[0] == 1108.00
    assert result["amount"].iloc[1] == 500.50
    assert result["amount"].iloc[2] == 250.00
    print("✅ convert_amount: แปลงตัวเลขพื้นฐาน")


def test_convert_amount_with_comma():
    df = pd.DataFrame({"amount": [" 1,108.00 ", "2,500.75", " 300 "]})
    result = ErpTransformer(df).convert_amount().df
    assert result["amount"].iloc[0] == 1108.00
    assert result["amount"].iloc[1] == 2500.75
    print("✅ convert_amount: รองรับ comma และ whitespace")


def test_convert_amount_rounding():
    df = pd.DataFrame({"amount": ["1.999", "2.555", "3.004"]})
    result = ErpTransformer(df).convert_amount().df
    assert result["amount"].iloc[0] == 2.00
    assert result["amount"].iloc[1] == 2.56
    assert result["amount"].iloc[2] == 3.00
    print("✅ convert_amount: ปัดทศนิยม 2 ตำแหน่ง")


# ── ErpValidator ──────────────────────────────────────────────────────────────

def test_validate_pass():
    result = ErpValidator(_valid_df()).run()
    assert result["passed"], f"ควรผ่าน แต่มี errors: {result['errors']}"
    print("✅ validate: ข้อมูลครบถ้วนผ่าน validation")


def test_validate_required_column_missing():
    df = _valid_df()
    df["doc_no"] = pd.NA  # required column ว่าง
    result = ErpValidator(df).run()
    assert not result["passed"]
    assert any("doc_no" in e for e in result["errors"])
    print("✅ validate: ตรวจพบ required column ว่าง")


def test_validate_nullable_allowed():
    df = _valid_df()
    # nullable columns ว่างได้ทั้งหมด
    for col in NULLABLE_COLUMNS:
        if col in df.columns:
            df[col] = pd.NA
    result = ErpValidator(df).run()
    assert result["passed"], f"nullable columns ว่างได้ แต่มี errors: {result['errors']}"
    print("✅ validate: nullable columns ว่างได้")


def test_validate_doc_date_invalid():
    df = _valid_df()
    df["doc_date"] = "03.12.2024"  # รูปแบบผิด
    result = ErpValidator(df).run()
    assert not result["passed"]
    assert any("doc_date" in e for e in result["errors"])
    print("✅ validate: ตรวจพบ doc_date รูปแบบผิด")


def test_validate_amount_invalid():
    df = _valid_df()
    df["amount"] = pd.NA
    result = ErpValidator(df).run()
    assert not result["passed"]
    assert any("amount" in e for e in result["errors"])
    print("✅ validate: ตรวจพบ amount ว่าง")


def test_fiscal_month_calculation():
    df = pd.DataFrame({
        "month": ["10", "11", "12", "1", "2", "9"],
    })
    result = ErpTransformer(df).convert_bigint_columns().add_fiscal_month().df
    expected = [1, 2, 3, 4, 5, 12]
    actual = result["fiscal_month"].tolist()
    assert actual == expected, f"ได้: {actual}"
    print("✅ fiscal_month คำนวณถูกต้อง:", dict(zip(df["month"].tolist(), actual)))


def test_convert_bigint_columns():
    df = pd.DataFrame({
        "fiscal_year": ["2025"], "fiscal_month": ["3"],
        "trimester": ["1"], "day": ["3"], "month": ["12"],
        "year": ["2024"], "doc_no": ["3000028712"],
    })
    result = ErpTransformer(df).convert_bigint_columns().df
    for col in ["fiscal_year", "fiscal_month", "trimester", "day", "month", "year", "doc_no"]:
        if col in result.columns:
            assert str(result[col].dtype) == "Int64", f"{col} ต้องเป็น Int64"
    print("✅ bigint columns แปลงเป็น Int64 ถูกต้อง")


def test_convert_numeric_columns():
    df = pd.DataFrame({"mu_strategy": ["1.5", pd.NA], "ic_strategy": ["2", "3.14"]})
    result = ErpTransformer(df).convert_numeric_columns().df
    assert result["mu_strategy"].iloc[0] == 1.5
    assert pd.isna(result["mu_strategy"].iloc[1])
    assert result["ic_strategy"].iloc[1] == 3.14
    print("✅ numeric columns (mu/ic_strategy) แปลงถูกต้อง")


def test_validate_bigint_invalid():
    df = _valid_df().copy()
    df["doc_no"] = pd.NA
    result = ErpValidator(df).run()
    assert not result["passed"]
    assert any("doc_no" in e for e in result["errors"])
    print("✅ validate: ตรวจพบ bigint column ว่าง")


def test_validate_order_description_nullable():
    df = _valid_df().copy()
    df["order_description"] = pd.NA
    result = ErpValidator(df).run()
    assert result["passed"], f"order_description ว่างได้ แต่มี errors: {result['errors']}"
    print("✅ validate: order_description ว่างได้")


if __name__ == "__main__":
    test_convert_amount_basic()
    test_convert_amount_with_comma()
    test_convert_amount_rounding()
    test_fiscal_month_calculation()
    test_convert_bigint_columns()
    test_convert_numeric_columns()
    test_validate_pass()
    test_validate_required_column_missing()
    test_validate_nullable_allowed()
    test_validate_doc_date_invalid()
    test_validate_amount_invalid()
    test_validate_bigint_invalid()
    test_validate_order_description_nullable()
    print("\nAll tests passed")
