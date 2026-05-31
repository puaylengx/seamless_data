"""ทดสอบ ErpTransformer"""
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance.transformer import ErpTransformer


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "year":     ["2025", "2025", "2024"],
        "month":    ["12",   "1",    "9"],
        "doc_date": ["03.12.2024", "15.01.2025", "30.09.2024"],
        "doc_no":   ["3000028712", "3000028800", "3000028500"],
        "amount":   ["1108.00", "500.00", "250.00"],
    })


def test_normalize():
    df = pd.DataFrame({
        "col_a": ["  hello  ", "NULL",  "N/A", "n/a", "nan", "None", "-", "  ", "value"],
        "col_b": ["  world  ", "none",  "NA",  " - ", " ",   "NaN",  "",  "ok", "  x  "],
    })
    result = ErpTransformer(df).normalize().df

    # strip whitespace
    assert result["col_a"].iloc[0] == "hello",  "ต้อง strip whitespace"
    assert result["col_b"].iloc[0] == "world",  "ต้อง strip whitespace"
    assert result["col_b"].iloc[-1] == "x",     "ต้อง strip whitespace"

    # NULL values → pd.NA
    null_inputs_a = ["NULL", "N/A", "n/a", "nan", "None", "-", "  "]
    for i, val in enumerate(null_inputs_a, start=1):
        assert pd.isna(result["col_a"].iloc[i]), f"'{val}' ต้องเป็น NA แต่ได้: {result['col_a'].iloc[i]}"

    # ค่าปกติต้องคงไว้
    assert result["col_a"].iloc[-1] == "value", "ค่าปกติต้องไม่เปลี่ยน"

    print("✅ normalize: strip whitespace และแปลง NULL/N/A → pd.NA ถูกต้อง")


def test_rename_year_to_fiscal_year():
    df = ErpTransformer(_sample_df()).rename_year_to_fiscal_year().df
    assert "fiscal_year" in df.columns, "ต้องมี column fiscal_year"
    assert "year" not in df.columns,    "ต้องไม่มี column year หลัง rename"
    print("✅ rename year → fiscal_year")


def test_convert_doc_date():
    df = ErpTransformer(_sample_df()).convert_doc_date().df
    assert df["doc_date"].iloc[0] == "2024-12-03", f"ได้: {df['doc_date'].iloc[0]}"
    assert df["doc_date"].iloc[1] == "2025-01-15", f"ได้: {df['doc_date'].iloc[1]}"
    assert df["doc_date"].iloc[2] == "2024-09-30", f"ได้: {df['doc_date'].iloc[2]}"
    print("✅ doc_date แปลงเป็น yyyy-mm-dd ถูกต้อง")


def test_add_year_from_doc_date():
    df = (
        ErpTransformer(_sample_df())
        .convert_doc_date()
        .add_year_from_doc_date()
        .df
    )
    assert int(df["year"].iloc[0]) == 2024, f"ได้: {df['year'].iloc[0]}"
    assert int(df["year"].iloc[1]) == 2025, f"ได้: {df['year'].iloc[1]}"
    print("✅ year ดึงจาก doc_date ถูกต้อง")


def test_run_full_pipeline():
    df = ErpTransformer(_sample_df()).run()

    # fiscal_year มาจาก Excel column year
    assert "fiscal_year" in df.columns
    assert int(df["fiscal_year"].iloc[0]) == 2025

    # doc_date แปลงแล้ว
    assert df["doc_date"].iloc[0] == "2024-12-03"

    # year ใหม่มาจาก doc_date
    assert "year" in df.columns
    assert int(df["year"].iloc[0]) == 2024

    print("✅ run() ครบทุก transformation")
    print(df[["fiscal_year", "doc_date", "year"]].to_string(index=False))


if __name__ == "__main__":
    test_normalize()
    test_rename_year_to_fiscal_year()
    test_convert_doc_date()
    test_add_year_from_doc_date()
    test_run_full_pipeline()
    print("\nAll tests passed")
