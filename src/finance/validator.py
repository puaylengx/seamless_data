from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from helpers.fiscal import fiscal_month, fiscal_year_from_date
from src.finance.reference import normalize_key

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

    # timeliness thresholds (G13) — master เก่ากว่านี้ = เตือน; ยังไม่มีนิยาม SLA จากทีม → ค่าเริ่มต้นอธิบายได้
    MASTER_MAX_AGE_DAYS = 365
    DATA_MAX_AGE_DAYS = 120

    def __init__(
        self,
        df: pd.DataFrame,
        reference: dict[str, set[str]] | None = None,
        reference_as_of: dict[str, date | None] | None = None,
        strict_reference: bool = False,
        today: date | None = None,
    ):
        self.df = df
        self.errors: list[str] = []
        self.warnings: list[str] = []   # ตรวจพบแต่ยังไม่ block (advisory) — fiscal cross-check, referential, timeliness
        self.reference = reference or {}
        self.reference_as_of = reference_as_of or {}
        self.strict_reference = strict_reference   # True → ค่าที่ไม่อยู่ใน master เป็น error (เปิดเมื่อ master ครบ/ทันสมัย)
        self.today = today or date.today()

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

    def validate_referential(self) -> "ErpValidator":
        """
        Consistency (G13): ค่าใน erp column ต้องมีอยู่ใน master ที่อ้างถึง (funds_ctr → master_fund ฯลฯ)

        default = WARNING เพราะ master files ปัจจุบัน (2022–2024) เก่ากว่า ERP 2025 — รหัสใหม่ที่ยังไม่อยู่ใน master
        เป็นเรื่องคาดหมายจนกว่า Finance จะส่งไฟล์ใหม่ (G13 ส่วน 🔒) · strict_reference=True → error
        """
        for col, valid in self.reference.items():
            if col not in self.df.columns or not valid:
                continue
            values = normalize_key(self.df[col])
            present = values.notna() & (values != "")
            missing = present & ~values.isin(valid)
            if not missing.any():
                continue
            unknown = sorted(values[missing].unique().tolist())
            rows = (self.df.index[missing] + _EXCEL_ROW_OFFSET).tolist()
            msg = (
                f"'{col}' มีค่าที่ไม่อยู่ใน master {int(missing.sum())} แถว "
                f"({len(unknown)} รหัส เช่น {unknown[:5]}) ที่ Excel rows: {rows[:10]}{' …' if len(rows) > 10 else ''}"
            )
            if self.strict_reference:
                self.errors.append(msg)
            else:
                self.warnings.append(msg)
                logger.warning("⚠️ %s", msg)
        return self

    def validate_timeliness(self) -> "ErpValidator":
        """
        Timeliness (G13): (1) ข้อมูลล่าสุดในไฟล์เก่าแค่ไหนเทียบวันนี้ (2) master ที่ใช้เทียบเก่ากว่า threshold ไหม
        รายงานเป็น warning — ไม่มี SLA ที่ตกลงกัน (threshold เป็นค่าเริ่มต้นใน class)
        """
        if "doc_date" in self.df.columns:
            parsed = pd.to_datetime(self.df["doc_date"], format="%Y-%m-%d", errors="coerce")
            if parsed.notna().any():
                latest = parsed.max().date()
                age = (self.today - latest).days
                if age > self.DATA_MAX_AGE_DAYS:
                    msg = f"doc_date ล่าสุดในไฟล์คือ {latest} ({age} วันก่อน) — เกิน {self.DATA_MAX_AGE_DAYS} วัน ข้อมูลอาจไม่ใช่รอบล่าสุด"
                    self.warnings.append(msg)
                    logger.warning("⚠️ %s", msg)
        stale = []
        for col, as_of in self.reference_as_of.items():
            if as_of and (self.today - as_of).days > self.MASTER_MAX_AGE_DAYS:
                stale.append(f"{col} (master as of {as_of}, {(self.today - as_of).days} วัน)")
        if stale:
            msg = f"master ที่ใช้เทียบเก่ากว่า {self.MASTER_MAX_AGE_DAYS} วัน: {', '.join(stale)} — รอไฟล์ใหม่จาก Finance (G13)"
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
        self.validate_referential()
        self.validate_timeliness()

        passed = len(self.errors) == 0
        return {
            "passed": passed,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
        }
