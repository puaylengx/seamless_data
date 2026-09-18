from __future__ import annotations

import logging

import pandas as pd

from src.finance.master.loader import _TABLE_COLUMNS

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2

# column แรกของแต่ละ master = business key (…_id) ที่ต้องไม่ว่างและไม่ซ้ำ (G11 / เตรียม PK ใน G5)
KEY_COLUMNS: dict[str, str] = {table: cols[0] for table, cols in _TABLE_COLUMNS.items()}
# master_gl มี key ผสม (group_id + gl_id): gl_id คือตัวที่ต้องไม่ซ้ำ
KEY_COLUMNS["master_gl"] = "gl_id"

VALID_STATUS = {"active", "inactive"}


class MasterValidator:
    """ตรวจ master DataFrame หลัง MasterTransformer — read-only, เดิมไม่มี validator เลย (pipeline pattern ข้อ 3)"""

    def __init__(self, df: pd.DataFrame, table_name: str):
        if table_name not in KEY_COLUMNS:
            raise ValueError(f"ไม่รู้จัก table '{table_name}'\nที่รองรับ: {list(KEY_COLUMNS)}")
        self.df = df
        self.table_name = table_name
        self.key = KEY_COLUMNS[table_name]
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def _rows(self, mask: pd.Series) -> list:
        return (self.df.index[mask] + _EXCEL_ROW_OFFSET).tolist()

    def validate_expected_columns(self) -> "MasterValidator":
        """column ที่ loader จะ insert ต้องมีครบ (ยกเว้น status ที่ transformer เติมให้)"""
        expected = [c for c in _TABLE_COLUMNS[self.table_name] if c != "status"]
        missing = [c for c in expected if c not in self.df.columns]
        if missing:
            self.errors.append(f"{self.table_name}: column หาย {missing}")
        return self

    def validate_key_not_null(self) -> "MasterValidator":
        if self.key not in self.df.columns:
            return self
        mask = self.df[self.key].isna() | (self.df[self.key].astype(str).str.strip() == "")
        if mask.any():
            self.errors.append(f"{self.table_name}: '{self.key}' ว่าง {int(mask.sum())} แถว ที่ Excel rows: {self._rows(mask)[:10]}")
        return self

    def validate_key_unique(self) -> "MasterValidator":
        """key ซ้ำ = โหลดแล้ว join กับ erp จะขยายแถว (double count) → error"""
        if self.key not in self.df.columns:
            return self
        key = self.df[self.key].astype(str).str.strip()
        dup = key.duplicated(keep=False) & self.df[self.key].notna()
        if dup.any():
            self.errors.append(
                f"{self.table_name}: '{self.key}' ซ้ำ {int(dup.sum())} แถว "
                f"(ค่าซ้ำ: {sorted(key[dup].unique().tolist())[:5]}) ที่ Excel rows: {self._rows(dup)[:10]}"
            )
        return self

    def validate_status(self) -> "MasterValidator":
        """status นอก {active, inactive} → warning (ยังไม่มีนิยามจากฝ่ายการเงินว่ามีค่าอื่นได้ไหม)"""
        if "status" not in self.df.columns:
            return self
        bad = ~self.df["status"].astype(str).str.strip().str.lower().isin(VALID_STATUS)
        if bad.any():
            self.warnings.append(
                f"{self.table_name}: status นอก {sorted(VALID_STATUS)} {int(bad.sum())} แถว ที่ Excel rows: {self._rows(bad)[:10]}"
            )
        return self

    def run(self) -> dict:
        self.errors.clear()
        self.warnings.clear()
        self.validate_expected_columns().validate_key_not_null().validate_key_unique().validate_status()
        for w in self.warnings:
            logger.warning("⚠️ %s", w)
        for e in self.errors:
            logger.error("❌ %s", e)
        return {"passed": not self.errors, "errors": self.errors.copy(), "warnings": self.warnings.copy()}
