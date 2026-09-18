"""G18: import ของ finance/main ต้องไม่ทำให้ handler ของ "src" logger ชี้ไป log file ของ module อื่น"""
import importlib
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


def _file_handlers(name):
    return [Path(h.baseFilename).name for h in logging.getLogger(name).handlers if isinstance(h, logging.FileHandler)]


def test_erp_main_import_keeps_src_handlers_on_erp_log():
    for m in ("src.finance.main", "src.finance.master.main"):
        sys.modules.pop(m, None)
    importlib.import_module("src.finance.main")
    files = _file_handlers("src")
    assert files and all(f.startswith("erp_") for f in files), files      # ไม่ใช่ master_*.log
    print("✅ import finance.main → src logger เขียน erp_*.log ไม่ถูก master แย่ง")


def test_master_files_module_has_no_logger_side_effect():
    before = _file_handlers("src")
    sys.modules.pop("src.finance.master.files", None)
    importlib.import_module("src.finance.master.files")
    assert _file_handlers("src") == before
