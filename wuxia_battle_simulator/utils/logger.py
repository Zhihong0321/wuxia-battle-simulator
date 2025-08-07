import logging
from pathlib import Path
from typing import Optional


_LOGGER: Optional[logging.Logger] = None


def get_logger(name: str = "wuxia_battle_simulator", level: int = logging.INFO) -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    _LOGGER = logger
    return logger


def enable_file_logging(log_dir: Path, filename: str = "app.log", level: int = logging.DEBUG) -> None:
    """
    Optional file logging (not used by default). Creates log_dir if needed.
    """
    logger = get_logger()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / filename, encoding="utf-8")
        fh.setLevel(level)
        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:
        logger.warning(f"Failed to enable file logging: {e}")