import pandas as pd

_NULL_VALUES = {"null", "none", "n/a", "na", "nan", "-", ""}


class MasterTransformer:
    """Transform master DataFrame หลังจาก extract"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def normalize(self) -> "MasterTransformer":
        """strip whitespace และแปลง null-like → pd.NA ทุก text column"""
        for col in self.df.select_dtypes(include=["object", "string"]).columns:
            self.df[col] = (
                self.df[col]
                .astype(str)
                .str.strip()
                .apply(lambda v: pd.NA if not isinstance(v, str) or v.lower() in _NULL_VALUES else v)
            )
        return self

    def add_status(self, default: str = "active") -> "MasterTransformer":
        """เพิ่ม column status ถ้ายังไม่มี"""
        if "status" not in self.df.columns:
            self.df["status"] = default
        else:
            self.df["status"] = self.df["status"].fillna(default)
        return self

    def run(self) -> pd.DataFrame:
        return (
            self.normalize()
                .add_status()
                .df
        )
