import pandas as pd

_NULL_VALUES = {"null", "none", "n/a", "na", "nan", "-", ""}

# bigint columns ตาม schema
_BIGINT_COLS = ["fiscal_year", "fiscal_month", "trimester", "day", "month", "year", "doc_no"]

# numeric (float, nullable) ตาม schema
_NUMERIC_COLS = ["mu_strategy", "ic_strategy"]


class ErpTransformer:
    """Transform ERP DataFrame หลังจาก extract"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def convert_doc_date(self) -> "ErpTransformer":
        """แปลง doc_date จาก dd.mm.yyyy → yyyy-mm-dd"""
        dt = pd.to_datetime(self.df["doc_date"], format="%d.%m.%Y", errors="coerce")

        # fallback กรณีรูปแบบอื่น เช่น datetime จาก Excel
        missing = dt.isna()
        if missing.any():
            dt[missing] = pd.to_datetime(self.df.loc[missing, "doc_date"], errors="coerce")

        self.df["doc_date"] = dt.dt.strftime("%Y-%m-%d")
        return self

    def add_year_from_doc_date(self) -> "ErpTransformer":
        """เพิ่ม column year โดยดึงปีจาก doc_date (ต้อง convert_doc_date ก่อน)"""
        self.df["year"] = pd.to_datetime(
            self.df["doc_date"], format="%Y-%m-%d", errors="coerce"
        ).dt.year.astype("Int64")
        return self

    def rename_year_to_fiscal_year(self) -> "ErpTransformer":
        """เปลี่ยนชื่อ column year (จาก Excel) เป็น fiscal_year"""
        if "year" in self.df.columns:
            self.df = self.df.rename(columns={"year": "fiscal_year"})
        return self

    def convert_amount(self) -> "ErpTransformer":
        """แปลง amount เป็น float ทศนิยม 2 ตำแหน่ง (รองรับ string มี comma เช่น '1,108.00')"""
        s = self.df["amount"].astype(str).str.replace(",", "", regex=False).str.strip()
        self.df["amount"] = pd.to_numeric(s, errors="coerce").round(2)
        return self

    def normalize(self) -> "ErpTransformer":
        """strip whitespace และแปลง NULL/N/A/n/a → pd.NA ทุก text column"""
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            self.df[col] = (
                self.df[col]
                .astype(str)
                .str.strip()
                .apply(lambda v: pd.NA if not isinstance(v, str) or v.lower() in _NULL_VALUES else v)
            )
        return self

    def add_fiscal_month(self) -> "ErpTransformer":
        """เพิ่ม column fiscal_month คำนวณจาก month (ต้อง convert_bigint_columns ก่อน)
        ปีงบประมาณเริ่ม ต.ค. → fiscal_month 1 .. ก.ย. → fiscal_month 12
        สูตร: ((month + 2) % 12) + 1
        """
        if "month" not in self.df.columns:
            return self
        self.df["fiscal_month"] = (
            (pd.to_numeric(self.df["month"], errors="coerce") + 2) % 12 + 1
        ).astype("Int64")
        return self

    def convert_bigint_columns(self) -> "ErpTransformer":
        """แปลง bigint columns เป็น Int64 (nullable integer)"""
        for col in _BIGINT_COLS:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(
                    self.df[col], errors="coerce"
                ).astype("Int64")
        return self

    def convert_numeric_columns(self) -> "ErpTransformer":
        """แปลง numeric columns (mu_strategy, ic_strategy) เป็น float"""
        for col in _NUMERIC_COLS:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
        return self

    def run(self) -> pd.DataFrame:
        """รัน transformation ตามลำดับที่ถูกต้อง"""
        return (
            self.normalize()                    # 1. normalize ก่อนเสมอ
                .rename_year_to_fiscal_year()   # 2. rename year → fiscal_year
                .convert_doc_date()             # 3. แปลง doc_date
                .add_year_from_doc_date()       # 4. เพิ่ม year จาก doc_date
                .convert_amount()               # 5. แปลง amount เป็น float 2dp
                .convert_bigint_columns()       # 6. แปลง bigint columns เป็น Int64
                .add_fiscal_month()             # 7. คำนวณ fiscal_month
                .convert_numeric_columns()      # 8. แปลง mu/ic_strategy เป็น float
                .df
        )
