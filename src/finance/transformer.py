import pandas as pd

_NULL_VALUES = {"null", "none", "n/a", "na", "nan", "-", ""}


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

    def normalize(self) -> "ErpTransformer":
        """strip whitespace และแปลง NULL/N/A/n/a → pd.NA ทุก text column"""
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            self.df[col] = (
                self.df[col]
                .astype(str)
                .str.strip()
                .apply(lambda v: pd.NA if v.lower() in _NULL_VALUES else v)
            )
        return self

    def run(self) -> pd.DataFrame:
        """รัน transformation ตามลำดับที่ถูกต้อง"""
        return (
            self.normalize()                    # 1. normalize ก่อนเสมอ
                .rename_year_to_fiscal_year()   # 2. rename year → fiscal_year
                .convert_doc_date()             # 3. แปลง doc_date
                .add_year_from_doc_date()       # 4. เพิ่ม year จาก doc_date
                .df
        )
