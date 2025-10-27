import logging
import sys

def init_logger(name: str = "augment", level: int = logging.INFO) -> logging.Logger:
    """
    Initialize a consistent, structured logger.
    - ISO timestamps
    - Single stdout stream handler
    - Lazy reinit prevention
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s"
        handler.setFormatter(logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


log = init_logger()
