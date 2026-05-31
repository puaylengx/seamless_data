"""
Finance ETL — ERP 2025
extract → transform → validate → load
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.finance import ErpExtractor, ErpTransformer, ErpValidator, ErpLoader


def run(mode: str = "append") -> dict:
    # 1. Extract
    print("── Extract ──────────────────────────────")
    df = ErpExtractor().extract()
    print(f"   {len(df):,} rows extracted")

    # 2. Transform
    print("── Transform ────────────────────────────")
    df = ErpTransformer(df).run()
    print(f"   columns: {df.columns.tolist()}")

    # 3. Validate
    print("── Validate ─────────────────────────────")
    result = ErpValidator(df).run()
    if not result["passed"]:
        print("   ❌ Validation failed:")
        for e in result["errors"]:
            print(f"      - {e}")
        sys.exit(1)
    print("   ✅ Validation passed")

    # 4. Load
    print(f"── Load ({mode}) ──────────────────────────")
    loader = ErpLoader()
    load_result = loader.load(df, mode=mode)
    print(f"   ✅ Inserted {load_result['rows_inserted']:,} rows → erp_2025")
    if loader.created_by:
        print(f"   created_by: {loader.created_by}")

    return {**result, **load_result}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "append"
    run(mode=mode)
