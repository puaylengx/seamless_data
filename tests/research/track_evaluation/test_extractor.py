"""ทดสอบ track_evaluation extractor (G11)"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.research.track_evaluation.extractor import RAW_REQUIRED_COLUMNS, read_raw, read_reviewed_template
from src.research.track_evaluation.transformer import UPLOAD_COLUMNS


def _write(tmp_path, df):
    p = tmp_path / "in.xlsx"
    df.to_excel(p, index=False)
    return p


def test_read_reviewed_template_selects_and_renames_upload_columns(tmp_path):
    df = pd.DataFrame({**{c: ["x"] for c in UPLOAD_COLUMNS}, "Extra column": ["ignored"]})
    out = read_reviewed_template(_write(tmp_path, df))
    assert list(out.columns) == list(UPLOAD_COLUMNS.values())   # เฉพาะ 19 column, ชื่อ DB, ลำดับตาม mapping
    print("✅ read_reviewed_template: usecols + rename เหมือน main เดิม")


def test_read_reviewed_template_missing_column_raises(tmp_path):
    df = pd.DataFrame({c: ["x"] for c in UPLOAD_COLUMNS if c != "SCORE"})
    with pytest.raises(ValueError, match="SCORE"):
        read_reviewed_template(_write(tmp_path, df))


def test_read_raw_checks_required_columns(tmp_path):
    ok = read_raw(_write(tmp_path, pd.DataFrame({c: ["x"] for c in RAW_REQUIRED_COLUMNS})))
    assert len(ok) == 1
    with pytest.raises(ValueError, match="Weight"):
        read_raw(_write(tmp_path, pd.DataFrame({c: ["x"] for c in RAW_REQUIRED_COLUMNS if c != "Weight"})))
