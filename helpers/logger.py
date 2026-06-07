import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorlog


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
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

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
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path / log_filename, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
