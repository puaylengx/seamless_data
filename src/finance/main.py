"""
Finance ETL — ERP 2025
extract → transform → validate → load
"""
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from helpers.logger import get_styled_logger
from src.finance import ErpExtractor, ErpTransformer, ErpValidator, ErpLoader
from src.finance.master.files import MASTER_FILES
from src.finance.reference import load_master_reference

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs" / "finance"

logger = get_styled_logger(
    name=__name__,
    log_dir=LOG_DIR,
    log_filename=f"erp_{datetime.now():%Y-%m-%d}.log",
    log_level=logging.INFO,
)


def job_summary(job: str, status: str, started: float, **fields) -> None:
    """บรรทัดสรุปงานท้ายทุก run (G9/G18) — grep ได้ด้วย "JOB SUMMARY" สำหรับ monitoring ระดับ infra"""
    extra = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("JOB SUMMARY job=%s status=%s duration=%.1fs %s", job, status, time.monotonic() - started, extra)


def run(mode: str = "append") -> dict:
    started = time.monotonic()
    logger.info("=" * 20 + " Finance ERP (%s) " + "=" * 20, mode)

    # 1. Extract
    logger.info("── Extract ──")
    df = ErpExtractor().extract()
    rows_in = len(df)
    logger.info("   %s rows extracted", f"{rows_in:,}")

    # 2. Transform
    logger.info("── Transform ──")
    df = ErpTransformer(df).run()
    logger.info("   columns: %s", df.columns.tolist())

    # 3. Validate — referential/timeliness เทียบกับไฟล์ master ในเครื่อง (G13, advisory)
    logger.info("── Validate ──")
    reference, as_of = load_master_reference(MASTER_FILES)
    result = ErpValidator(df, reference=reference, reference_as_of=as_of).run()
    for w in result.get("warnings", []):
        logger.warning("   ⚠️  %s", w)
    if not result["passed"]:
        for e in result["errors"]:
            logger.error("   ❌ %s", e)
        job_summary("finance.erp", "validation_failed", started, rows_in=rows_in, errors=len(result["errors"]))
        sys.exit(1)
    logger.info("   ✅ Validation passed (%d warnings)", len(result.get("warnings", [])))

    # 4. Load
    logger.info("── Load (%s) ──", mode)
    loader = ErpLoader()
    try:
        load_result = loader.load(df, mode=mode)
    except Exception as e:
        job_summary("finance.erp", "load_failed", started, rows_in=rows_in, error=type(e).__name__)
        raise
    logger.info("   ✅ Inserted %s rows → erp_2025", f"{load_result['rows_inserted']:,}")
    if loader.created_by:
        logger.info("   created_by: %s", loader.created_by)

    job_summary("finance.erp", "ok", started, mode=mode, rows_in=rows_in, rows_out=load_result["rows_inserted"],
                warnings=len(result.get("warnings", [])))
    return {**result, **load_result}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "append"
    run(mode=mode)
