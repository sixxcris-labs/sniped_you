# app/obs/structured_log.py
import logging
from datetime import datetime


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info(f"Structured logging initialized at {datetime().isoformat()}")
