from __future__ import annotations

import logging

import pandas as pd

from helpers.fiscal import fiscal_month, fiscal_year_from_date

logger = logging.getLogger(__name__)

_EXCEL_ROW_OFFSET = 2  # header row 1, data starts at row 2

# nullable columns ตาม schema (ไม่มี NOT NULL)
NULLABLE_COLUMNS = {
    "cost_owner",
    "cost_note",
    "io_goods",
    "io_work",
    "io_activity",
    "io_project",
    "order_description",
    "hr_ot",
    "mu_strategy",
    "ic_strategy",
    # DB-managed — ไม่ validate
    "created_at", "updated_at", "updated_by", "created_by",
}

# bigint columns ตาม schema
_BIGINT_COLS = {"fiscal_year", "fiscal_month", "trimester", "day", "month", "year", "doc_no"}


class ErpValidator:
    """ตรวจสอบความถูกต้องของ ERP DataFrame หลังจาก transform"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.errors: list[str] = []
        self.warnings: list[str] = []   # ตรวจพบแต่ยังไม่ block (advisory) — ดู validate_fiscal_year_vs_doc_date

    def validate_required_columns(self) -> "ErpValidator":
        """column ที่ไม่ได้อยู่ใน NULLABLE_COLUMNS ต้องมีข้อมูลครบ ไม่มี NA"""
        required_cols = [c for c in self.df.columns if c not in NULLABLE_COLUMNS]

        for col in required_cols:
            null_count = int(self.df[col].isna().sum())
            if null_count > 0:
                self.errors.append(f"'{col}' มีค่าว่าง {null_count} แถว")

        return self

    def validate_doc_date_format(self) -> "ErpValidator":
        """doc_date ต้องอยู่ในรูปแบบ yyyy-mm-dd และแปลงเป็นวันที่ได้"""
        if "doc_date" not in self.df.columns:
            self.errors.append("ไม่พบ column 'doc_date'")
            return self

        parsed = pd.to_datetime(self.df["doc_date"], format="%Y-%m-%d", errors="coerce")
        invalid_count = int(parsed.isna().sum())

        if invalid_count > 0:
            bad_rows = self.df.loc[parsed.isna(), "doc_date"].head(5).tolist()
            self.errors.append(
                f"'doc_date' มีรูปแบบไม่ถูกต้อง {invalid_count} แถว "
                f"(ตัวอย่าง: {bad_rows})"
            )

        return self

    def validate_bigint_columns(self) -> "ErpValidator":
        """bigint columns ต้องเป็น integer ทั้งหมด ไม่มี NA"""
        for col in _BIGINT_COLS:
            if col not in self.df.columns:
                self.errors.append(f"ไม่พบ column '{col}'")
                continue

            null_count = int(self.df[col].isna().sum())
            if null_count > 0:
                self.errors.append(f"'{col}' (bigint) มีค่าว่าง {null_count} แถว")
                continue

            numeric = pd.to_numeric(self.df[col], errors="coerce")
            bad = int(numeric.isna().sum())
            if bad > 0:
                self.errors.append(f"'{col}' (bigint) มีค่าที่ไม่ใช่ integer {bad} แถว")

        return self

    def validate_amount(self) -> "ErpValidator":
        """amount ต้องเป็น decimal 2dp และไม่เป็น NA"""
        if "amount" not in self.df.columns:
            self.errors.append("ไม่พบ column 'amount'")
            return self

        null_count = int(self.df["amount"].isna().sum())
        if null_count > 0:
            self.errors.append(f"'amount' มีค่าว่าง {null_count} แถว")
            return self

        numeric = pd.to_numeric(self.df["amount"], errors="coerce")
        bad = int(numeric.isna().sum())
        if bad > 0:
            self.errors.append(f"'amount' มีค่าที่ไม่ใช่ตัวเลข {bad} แถว")

        return self

    def validate_fiscal_year_vs_doc_date(self) -> "ErpValidator":
        """
        Cross-check (G15): fiscal_year / fiscal_month ที่มากับไฟล์ Excel ต้องตรงกับที่ derive จาก doc_date
        ตามนิยามเดียวใน helpers/fiscal.py (ปีงบเริ่ม ต.ค.)

        ยังเป็น **WARNING ไม่ใช่ error** — ของใหม่ที่ไม่เคยตรวจมาก่อน ยังไม่รู้ว่าข้อมูลจริงมี mismatch
        บ่อยแค่ไหน (เช่น ฝ่ายการเงินอาจ post ย้อนงวดโดยตั้งใจ) → เก็บสถิติจาก log ก่อน ค่อยตัดสินว่าจะ fail-fast
        """
        if "doc_date" not in self.df.columns:
            return self
        parsed = pd.to_datetime(self.df["doc_date"], format="%Y-%m-%d", errors="coerce")
        checks = (
            ("fiscal_year", fiscal_year_from_date(parsed)),
            ("fiscal_month", fiscal_month(parsed.dt.month)),
        )
        for col, expected in checks:
            if col not in self.df.columns:
                continue
            actual = pd.to_numeric(self.df[col], errors="coerce").astype("Int64")
            comparable = actual.notna() & expected.notna()
            mismatch = comparable & (actual != expected)
            if not mismatch.any():
                continue
            rows = (self.df.index[mismatch] + _EXCEL_ROW_OFFSET).tolist()
            sample = rows[:10]
            msg = (
                f"'{col}' จาก Excel ไม่ตรงกับที่คำนวณจาก doc_date {int(mismatch.sum())} แถว "
                f"(จาก {int(comparable.sum())} ที่เทียบได้) ที่ Excel rows: {sample}{' …' if len(rows) > 10 else ''}"
            )
            self.warnings.append(msg)
            logger.warning("⚠️ %s", msg)
        return self

    def run(self) -> dict:
        """รัน validation ทั้งหมด คืน dict สรุปผล — errors block การ load, warnings แค่รายงาน"""
        self.errors.clear()
        self.warnings.clear()
        self.validate_required_columns()
        self.validate_doc_date_format()
        self.validate_bigint_columns()
        self.validate_amount()
        self.validate_fiscal_year_vs_doc_date()

        passed = len(self.errors) == 0
        return {
            "passed": passed,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
        }
