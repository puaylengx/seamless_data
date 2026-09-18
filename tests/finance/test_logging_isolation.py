"""G18/G9: การ import module ที่มี get_styled_logger ต้องไม่ย้าย handler ของ "src" logger (entrypoint เท่านั้นที่เป็นเจ้าของ)"""
import importlib
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


def _file_handlers(name):
    return [Path(h.baseFilename).name for h in logging.getLogger(name).handlers if isinstance(h, logging.FileHandler)]


def test_importing_pipeline_modules_leaves_src_handlers_untouched():
    before = _file_handlers("src")
    for m in ("src.finance.main", "src.finance.master.main"):
        sys.modules.pop(m, None)
        importlib.import_module(m)
    assert _file_handlers("src") == before                                   # import ≠ entrypoint → ไม่แย่ง src
    assert all(f.startswith("erp_") for f in _file_handlers("src.finance.main"))
    assert all(f.startswith("master_") for f in _file_handlers("src.finance.master.main"))
    print("✅ import finance.main / master.main → src handlers ไม่เปลี่ยน, แต่ละ module มี log ของตัวเอง")


def test_master_files_module_has_no_logger_side_effect():
    before = _file_handlers("src")
    sys.modules.pop("src.finance.master.files", None)
    importlib.import_module("src.finance.master.files")
    assert _file_handlers("src") == before
