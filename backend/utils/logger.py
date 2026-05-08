import sys
import logging
from typing import Optional

from config import settings


def setup_logger(
    name: str = "voiceagent",
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    log_level = level or settings.LOG_LEVEL
    log_format = format_string or settings.LOG_FORMAT

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"voiceagent.{name}")


logger = setup_logger()
