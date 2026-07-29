"""
UTILS/LOGGING_CONFIG.PY
Centralized logging setup for the AI DM engine.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def configure_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    numeric_level = getattr(logging, str(level or "INFO").upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(
            RotatingFileHandler(
                log_file,
                maxBytes=2_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )

    # Keep noisy libraries quieter by default.
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
