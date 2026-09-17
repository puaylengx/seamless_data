import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorlog


# logger ราก ("src") ที่ทุก submodule ใน src/ ใช้ผ่าน logging.getLogger(__name__)
SRC_LOGGER_NAME = "src"

# ── Custom SUCCESS level ──────────────────────────────────────────────────────
_SUCCESS = 25
logging.addLevelName(_SUCCESS, "SUCCESS")


def _success(self, message, *args, **kws):
    if self.isEnabledFor(_SUCCESS):
        self._log(_SUCCESS, message, args, **kws)


logging.Logger.success = _success


# ── Public API ────────────────────────────────────────────────────────────────

def get_logger(
    name: str,
    log_dir: Optional[Path] = None,
    log_filename: Optional[str] = None,
    log_level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Logger ที่มี RotatingFileHandler + StreamHandler
    ใช้เป็น default เมื่อไม่ต้องการสี
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    if log_dir is None:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    if log_filename is None:
        log_filename = f"{name.replace('.', '_')}.log"

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_dir / log_filename, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def get_styled_logger(
    name: str,
    log_dir: Path,
    log_filename: str,
    log_level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Logger พร้อมสีใน terminal (ใช้ colorlog) + บันทึกไฟล์แบบปกติ
    รองรับ level SUCCESS (25) เพิ่มเติม

    handler ชุดเดียวกันจะถูกผูกไว้ 2 จุด:
      - logger ชื่อ `name` (ปกติคือ "__main__" ของ pipeline ที่รัน)
      - logger ชื่อ SRC_LOGGER_NAME ("src") — เพื่อให้ submodule ที่ใช้
        logging.getLogger(__name__) เช่น "src.research.publication.validator"
        เขียนลงไฟล์/terminal เดียวกัน (ก่อนหน้านี้ log พวกนี้หายเงียบๆ
        เพราะ "src.*" ไม่ใช่ลูกของ "__main__" ใน logging hierarchy)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "light_blue",
            "SUCCESS": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(color_formatter)

    file_handler = logging.FileHandler(log_path / log_filename, encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger(name)
    targets = [logger]
    if name != SRC_LOGGER_NAME:
        targets.append(logging.getLogger(SRC_LOGGER_NAME))

    # ถูกเรียกซ้ำ (เช่นใน test หรือรัน pipeline หลายตัวใน process เดียว)
    # → handler ชุดล่าสุดแทนชุดเดิมทั้งสอง logger ไม่เขียนซ้ำ
    for target in targets:
        target.setLevel(log_level)
        _close_handlers(target)
        target.addHandler(stream_handler)
        target.addHandler(file_handler)
        target.propagate = False

    return logger


def _close_handlers(logger: logging.Logger) -> None:
    """ถอด handler เดิมออกและปิด file ที่เปิดอยู่ กันการเขียนซ้ำเมื่อถูกเรียกหลายรอบ"""
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
