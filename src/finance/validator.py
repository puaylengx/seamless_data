from __future__ import annotations

import pandas as pd

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

    def run(self) -> dict:
        """รัน validation ทั้งหมด คืน dict สรุปผล"""
        self.errors.clear()
        self.validate_required_columns()
        self.validate_doc_date_format()
        self.validate_bigint_columns()
        self.validate_amount()

        passed = len(self.errors) == 0
        return {
            "passed": passed,
            "errors": self.errors.copy(),
        }
