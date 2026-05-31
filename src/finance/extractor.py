from pathlib import Path

import pandas as pd

# ── default data paths ────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).resolve().parents[2]
ERP_DIR    = BASE_DIR / "data" / "finance" / "clean" / "erp"
MASTER_DIR = BASE_DIR / "data" / "finance" / "clean" / "master"

# ── column mapping: Excel → DB ────────────────────────────────────────────────

ERP_COLUMNS: dict[str, str] = {
    "Year":              "year",
    "Trimester":         "trimester",
    "Day":               "day",
    "Month":             "month",
    "DocNo":             "doc_no",
    "DocDate":           "doc_date",
    "FundsCtr":          "funds_ctr",
    "CostCtr_ID":        "cost_ctr_id",
    "Cost_Owner":        "cost_owner",
    "IO_Goods":          "io_goods",
    "IO_Work":           "io_work",
    "IO_Activity":       "io_activity",
    "IO_Project":        "io_project",
    "Order_Description": "order_description",
    "HROT":              "hr_ot",
    "GL_ID":             "gl_id",
    "GL_Description":    "gl_description",
    "Amount":            "amount",
    "Details":           "details",
    "MU_Strategy":       "mu_strategy",
    "IC_Strategy":       "ic_strategy",
}

MASTER_COLUMNS: dict[str, dict[str, str]] = {
    "master_cost_ctr": {
        "CostCtr_Id":          "cost_center_id",
        "CostCtr_Description": "cost_center_description",
        "CostCtr_Eng":         "cost_center_eng",
        "CostCtr_TH":          "cost_center_th",
    },
    "master_fund": {
        "Fund_Id":          "fund_id",
        "Fund_Description": "fund_description",
    },
    "master_gl": {
        "Group":             "group_id",
        "Id":                "gl_id",
        "Description":       "gl_description",
        "Group_Description": "group_description",
    },
    "master_io_goods": {
        "IO_Goods_Id":          "io_good_id",
        "IO_Goods_Description": "io_good_description",
    },
    "master_io_activities": {
        "IO_Activity_Id":          "io_activity_id",
        "IO_Activity_Description": "io_activity_description",
    },
    "master_io_project": {
        "IO_Project":             "io_project_id",
        "IO_Project_Description": "io_project_description",
        "CostCtr":                "cost_center_id",
        "ID_ICST":                "ic_strategy_id",
        "ID_MUST":                "mu_strategy_id",
    },
    "master_io_work": {
        "IO_Work_Id":          "io_work_id",
        "IO_Work_Description": "io_work_description",
    },
    "master_ic_strategy": {
        "ID_ICST":     "ic_strategy_id",
        "Year_start":  "start_year",
        "Year_end":    "end_year",
        "Name":        "name_en",
        "Description": "ic_strategy_description",
    },
    "master_mu_strategy": {
        "ID_MUST":     "mu_strategy_id",
        "Year_start":  "start_year",
        "Year_end":    "end_year",
        "Name":        "name_en",
        "Description": "mu_strategy_description",
    },
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip() for c in df.columns]
    return df


# ── extractors ────────────────────────────────────────────────────────────────

class ErpExtractor:
    """อ่านไฟล์ Excel จาก data/finance/clean/erp/ และ rename column เป็น DB format

    file_path=None → ค้นหา .xlsx ใน ERP_DIR อัตโนมัติ (ต้องมี 1 ไฟล์เท่านั้น)
    """

    REQUIRED_COLUMNS = {"DocNo", "GL_ID", "Amount"}

    def __init__(self, file_path: str | Path | None = None, sheet_name: int | str = 0):
        if file_path is None:
            file_path = self._find_file()
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name

    def extract(self) -> pd.DataFrame:
        df = pd.read_excel(self.file_path, sheet_name=self.sheet_name, dtype=str, engine="openpyxl")
        df = _strip_columns(df)
        self._validate_columns(df)
        df = df.rename(columns=ERP_COLUMNS)
        return df.reset_index(drop=True)

    @staticmethod
    def _find_file() -> Path:
        files = sorted(ERP_DIR.glob("*.xlsx"))
        if not files:
            raise FileNotFoundError(f"ไม่พบไฟล์ .xlsx ใน {ERP_DIR}")
        if len(files) > 1:
            raise ValueError(
                f"พบหลายไฟล์ใน {ERP_DIR}: {[f.name for f in files]}\n"
                f"กรุณาระบุ file_path โดยตรง"
            )
        return files[0]

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"ไม่พบ column ที่จำเป็น: {missing}")


class MasterExtractor:
    """อ่านไฟล์ Excel จาก data/finance/clean/master/ และ rename column เป็น DB format

    master มีหลายไฟล์ แต่ละไฟล์ตรงกับ 1 table
    ใช้ list_files() เพื่อดูไฟล์ที่มีอยู่
    """

    TABLES = list(MASTER_COLUMNS.keys())

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else MASTER_DIR

    def list_files(self) -> list[Path]:
        """แสดงรายชื่อไฟล์ .xlsx ทั้งหมดใน master directory"""
        return sorted(self.data_dir.glob("*.xlsx"))

    def extract(self, table_name: str, file_path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
        """
        อ่านไฟล์ master และ rename column

        Args:
            table_name: ชื่อ table เช่น "master_gl", "master_fund"
            file_path:  ชื่อไฟล์ (เช่น "Master_GL_20230531.xlsx")
                        หรือ full path ก็ได้
        """
        if table_name not in MASTER_COLUMNS:
            raise ValueError(f"ไม่รู้จัก table '{table_name}'\nที่รองรับ: {self.TABLES}")

        path = Path(file_path)
        if not path.is_absolute():
            path = self.data_dir / path

        df = pd.read_excel(path, sheet_name=sheet_name, dtype=str, engine="openpyxl")
        df = _strip_columns(df)
        df = df.rename(columns=MASTER_COLUMNS[table_name])
        df = df.dropna(how="all")
        return df.reset_index(drop=True)
