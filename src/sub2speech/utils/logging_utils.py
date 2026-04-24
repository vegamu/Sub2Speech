from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "sub2speech"
_IS_INITIALIZED = False


def init_logging(app_root: Path) -> Path:
    global _IS_INITIALIZED
    logs_dir = app_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if _IS_INITIALIZED:
        return logs_dir

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = TimedRotatingFileHandler(
        filename=str(logs_dir / "sub2speech.log"),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if not getattr(sys, "frozen", False):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    _IS_INITIALIZED = True
    return logs_dir

def log_info(message: str) -> None:
    _log("INFO", message)


def log_error(message: str) -> None:
    _log("ERROR", message)


def _log(level: str, message: str) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    if _IS_INITIALIZED:
        if level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)
        return
    print(f"[{level}] {message}", flush=True)
