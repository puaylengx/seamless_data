"""ทดสอบ publication extractor — read_raw ตรวจ column บังคับ, read_reviewed_template rename ชื่อเก่า (G11)"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.publication.extractor import RAW_REQUIRED_COLUMNS, read_raw, read_reviewed_template


def _write(tmp_path, df, name="in.xlsx"):
    p = tmp_path / name
    df.to_excel(p, index=False)
    return p


def test_read_raw_ok_and_strips_headers(tmp_path):
    df = pd.DataFrame({f" {c} ": ["x"] for c in RAW_REQUIRED_COLUMNS})
    out = read_raw(_write(tmp_path, df))
    assert list(out.columns) == RAW_REQUIRED_COLUMNS and len(out) == 1
    print("✅ read_raw: strip header, column ครบ")


def test_read_raw_reports_all_missing_columns_at_once(tmp_path):
    df = pd.DataFrame({c: ["x"] for c in RAW_REQUIRED_COLUMNS if c not in ("Title", "SDGs Goal")})
    with pytest.raises(ValueError) as exc:
        read_raw(_write(tmp_path, df))
    assert "Title" in str(exc.value) and "SDGs Goal" in str(exc.value)


def test_read_reviewed_template_renames_legacy_flag_headers(tmp_path):
    df = pd.DataFrame({"WoS_SC": [1], "Scopus_Q1": [0], "product_code": ["P"]})
    out = read_reviewed_template(_write(tmp_path, df))
    assert list(out.columns) == ["wos_sc", "scopus_q1", "product_code"]
    print("✅ read_reviewed_template: header รุ่นเก่า → snake_case")
