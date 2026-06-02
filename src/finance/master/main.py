"""
Finance Master ETL
extract → transform → load สำหรับ master tables ทั้งหมด
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.finance.extractor import MasterExtractor
from src.finance.master import MasterTransformer, MasterLoader

# mapping: table_name → ชื่อไฟล์ Excel
MASTER_FILES: dict[str, str] = {
    "master_cost_ctr":      "Master_CostCtr_20240605.xlsx",
    "master_fund":          "Master_FUND_20221118.xlsx",
    "master_gl":            "Master_GL_20230531.xlsx",
    "master_io_goods":      "Master_IO_Goods_20230531.xlsx",
    "master_io_activities": "Master_IO_Activity_20230531.xlsx",
    "master_io_project":    "Master_IO_Project_20230531.xlsx",
    "master_io_work":       "Master_IO_Work_20230531.xlsx",
    "master_ic_strategy":   "Master_IC_Strategy_20230531.xlsx",
    "master_mu_strategy":   "Master_MU_Strategy_20230531.xlsx",
}


def run(table_name: str = "all", mode: str = "replace") -> list[dict]:
    extractor = MasterExtractor()
    loader    = MasterLoader()

    targets = (
        {table_name: MASTER_FILES[table_name]}
        if table_name != "all"
        else MASTER_FILES
    )

    if table_name != "all" and table_name not in MASTER_FILES:
        print(f"❌ ไม่รู้จัก table '{table_name}'\nที่รองรับ: {list(MASTER_FILES)}")
        sys.exit(1)

    results = []
    for tbl, file_name in targets.items():
        print(f"\n── {tbl} ──────────────────────────────────")

        # 1. Extract
        df = extractor.extract(table_name=tbl, file_path=file_name)
        print(f"   extracted : {len(df):,} rows")

        # 2. Transform
        df = MasterTransformer(df).run()
        print(f"   columns   : {df.columns.tolist()}")

        # 3. Load
        result = loader.load(df, table_name=tbl, mode=mode)
        print(f"   ✅ inserted {result['rows_inserted']:,} rows → {tbl}")

        results.append(result)

    return results


if __name__ == "__main__":
    table_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    mode       = sys.argv[2] if len(sys.argv) > 2 else "replace"
    run(table_name=table_name, mode=mode)
