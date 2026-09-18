"""ทดสอบ get_styled_logger — log จาก submodule ใต้ "src" ต้องลงไฟล์เดียวกับ main (G9)

หมายเหตุ: โฟลเดอร์นี้ตั้งใจไม่มี __init__.py — ถ้ามี pytest จะมอง tests/helpers
เป็น package ชื่อ "helpers" แล้วบังของจริงที่ project root
"""
import logging
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from helpers.logger import SRC_LOGGER_NAME, get_styled_logger


# ── helpers ───────────────────────────────────────────────────────────────────

def _read(log_file: Path) -> str:
    for h in logging.getLogger(SRC_LOGGER_NAME).handlers:
        h.flush()
    return log_file.read_text(encoding="utf-8")


def _read_file(log_file: Path) -> str:
    for lg in logging.Logger.manager.loggerDict.values():
        for h in getattr(lg, "handlers", []):
            h.flush()
    return log_file.read_text(encoding="utf-8")


def _teardown(*names: str) -> None:
    """ปิด handler ที่ test เปิดไว้ ไม่ให้ค้างข้าม test / ค้างชี้ไฟล์ใน tmp dir ที่ถูกลบ"""
    for n in (*names, SRC_LOGGER_NAME):
        lg = logging.getLogger(n)
        for h in list(lg.handlers):
            lg.removeHandler(h)
            h.close()
        lg.propagate = True


# ── tests ─────────────────────────────────────────────────────────────────────

def test_src_submodule_warning_reaches_log_file():
    """กรณีจริง: main.py รันตรง (__main__) ส่วน validator ใช้ logging.getLogger(__name__)"""
    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "run.log"
        main_logger = get_styled_logger("__main__", Path(tmp), "run.log", logging.INFO)
        try:
            main_logger.info("from main")
            logging.getLogger("src.research.publication.validator").warning(
                "Column 'rank' มีค่า null ที่ Excel rows: [5]"
            )
            logging.getLogger("src.finance.loader").info("inserted 10 rows")

            content = _read(log_file)
            assert "from main" in content
            assert "src.research.publication.validator - WARNING" in content
            assert "มีค่า null ที่ Excel rows: [5]" in content
            assert "src.finance.loader - INFO" in content
        finally:
            _teardown("__main__")
    print("✅ log จาก src.* ลงไฟล์เดียวกับ __main__")


def test_no_duplicate_lines_when_called_twice():
    """เรียก get_styled_logger ซ้ำ (เช่น import main หลายครั้ง) ต้องไม่เขียนบรรทัดซ้ำ"""
    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "run.log"
        get_styled_logger("__main__", Path(tmp), "run.log", logging.INFO)
        get_styled_logger("__main__", Path(tmp), "run.log", logging.INFO)
        try:
            logging.getLogger("src.x.y").warning("once")
            assert _read(log_file).count("once") == 1
        finally:
            _teardown("__main__")
    print("✅ ไม่มีบรรทัดซ้ำเมื่อเรียกซ้ำ")


def test_src_logger_does_not_propagate_to_root():
    """กัน log วิ่งซ้ำไป root handler (เช่น pytest caplog / basicConfig ของคนอื่น)"""
    with tempfile.TemporaryDirectory() as tmp:
        get_styled_logger("__main__", Path(tmp), "run.log", logging.INFO)
        try:
            assert logging.getLogger(SRC_LOGGER_NAME).propagate is False
            assert logging.getLogger("__main__").propagate is False
        finally:
            _teardown("__main__")
    print("✅ src logger ไม่ propagate ไป root")


def test_imported_module_logger_does_not_hijack_src_handlers():
    """G9 follow-up: entrypoint (__main__) เป็นเจ้าของ src; module ที่ถูก import ตั้ง logger ตัวเองได้แต่ห้ามแย่ง src"""
    with tempfile.TemporaryDirectory() as tmp:
        erp_log, master_log = Path(tmp) / "erp.log", Path(tmp) / "master.log"
        get_styled_logger("__main__", Path(tmp), "erp.log", logging.INFO)          # entrypoint จริง
        imported = get_styled_logger("src.finance.master.main", Path(tmp), "master.log", logging.INFO)  # ถูก import
        try:
            logging.getLogger("src.finance.validator").warning("from-validator")
            imported.info("from-master-module")
            assert "from-validator" in _read(erp_log)                               # ยังอยู่ไฟล์ของ entrypoint
            assert "from-validator" not in master_log.read_text(encoding="utf-8")
            assert "from-master-module" in master_log.read_text(encoding="utf-8")   # module มี log ของตัวเอง
            assert "from-master-module" not in _read(erp_log)
        finally:
            _teardown("__main__", "src.finance.master.main")
    print("✅ import module อื่นไม่ย้าย src handlers ออกจาก log ของ entrypoint")


def test_name_under_src_does_not_double_write():
    """ถ้า name เป็นลูกของ src อยู่แล้ว (import เป็น module) ห้ามเขียน 2 รอบ"""
    with tempfile.TemporaryDirectory() as tmp:
        log_file = Path(tmp) / "run.log"
        lg = get_styled_logger("src.research.publication.main", Path(tmp), "run.log", logging.INFO)
        try:
            lg.info("hello-from-child")
            content = _read_file(log_file)
            assert content.count("hello-from-child") == 1
        finally:
            _teardown("src.research.publication.main")
    print("✅ name ใต้ src ไม่เขียนซ้ำ")


if __name__ == "__main__":
    test_src_submodule_warning_reaches_log_file()
    test_no_duplicate_lines_when_called_twice()
    test_src_logger_does_not_propagate_to_root()
    test_imported_module_logger_does_not_hijack_src_handlers()
    test_name_under_src_does_not_double_write()
    print("\n🎉 ทุก test ผ่าน")
