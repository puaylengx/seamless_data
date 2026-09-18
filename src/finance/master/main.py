"""
Finance Master ETL
extract → transform → validate → load สำหรับ master tables ทั้งหมด
"""
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from helpers.logger import get_styled_logger
from src.finance.extractor import MasterExtractor
from src.finance.master import MasterLoader, MasterTransformer, MasterValidator
from src.finance.master.files import MASTER_FILES

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs" / "finance"

logger = get_styled_logger(
    name=__name__,
    log_dir=LOG_DIR,
    log_filename=f"master_{datetime.now():%Y-%m-%d}.log",
    log_level=logging.INFO,
)

def run(table_name: str = "all", mode: str = "replace") -> list[dict]:
    started = time.monotonic()
    extractor = MasterExtractor()
    loader    = MasterLoader()

    if table_name != "all" and table_name not in MASTER_FILES:
        logger.error("❌ ไม่รู้จัก table '%s' — ที่รองรับ: %s", table_name, list(MASTER_FILES))
        sys.exit(1)

    targets = {table_name: MASTER_FILES[table_name]} if table_name != "all" else MASTER_FILES
    logger.info("=" * 20 + " Finance Master (%s, %s) " + "=" * 20, table_name, mode)

    results = []
    for tbl, file_name in targets.items():
        logger.info("── %s ──", tbl)

        # 1. Extract
        df = extractor.extract(table_name=tbl, file_path=file_name)
        logger.info("   extracted : %s rows", f"{len(df):,}")

        # 2. Transform
        df = MasterTransformer(df).run()
        logger.info("   columns   : %s", df.columns.tolist())

        # 3. Validate (G11) — key ว่าง/ซ้ำ หรือ column หาย → หยุดก่อนแตะ DB
        check = MasterValidator(df, table_name=tbl).run()
        for w in check["warnings"]:
            logger.warning("   ⚠️  %s", w)
        if not check["passed"]:
            for e in check["errors"]:
                logger.error("   ❌ %s", e)
            logger.info("JOB SUMMARY job=finance.master status=validation_failed table=%s duration=%.1fs",
                        tbl, time.monotonic() - started)
            sys.exit(1)
        logger.info("   ✅ Validation passed")

        # 4. Load
        result = loader.load(df, table_name=tbl, mode=mode)
        logger.info("   ✅ inserted %s rows → %s", f"{result['rows_inserted']:,}", tbl)
        results.append(result)

    logger.info("JOB SUMMARY job=finance.master status=ok mode=%s tables=%d rows_out=%d duration=%.1fs",
                mode, len(results), sum(r["rows_inserted"] for r in results), time.monotonic() - started)
    return results


if __name__ == "__main__":
    table_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    mode       = sys.argv[2] if len(sys.argv) > 2 else "replace"
    run(table_name=table_name, mode=mode)
