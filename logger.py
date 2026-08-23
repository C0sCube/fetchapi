import logging
import os
import sys
import functools
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import colorlog

try:
    import colorlog  # type: ignore
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


# --- Formats ---
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


# --- Formatter ---
def _get_formatter(use_color=False):
    if use_color and COLORLOG_AVAILABLE:
        return colorlog.ColoredFormatter(
            "%(log_color)s" + DEFAULT_FORMAT,
            datefmt=DATE_FORMAT,
            log_colors=LOG_COLORS,
        )
    return logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)


# --- Console Handler ---
def _add_console_handler(logger, level, use_color=True):
    handler = (
        colorlog.StreamHandler(sys.stdout)
        if use_color and COLORLOG_AVAILABLE
        else logging.StreamHandler(sys.stdout)
    )
    handler.setFormatter(_get_formatter(use_color))
    handler.setLevel(level)
    logger.addHandler(handler)


# --- Global Logger ---
_active_logger = None


def get_global_logger():
    return _active_logger or logging.getLogger("default_logger")


# --- Setup Logger ---
def setup_logger(
    name="app_logger",
    log_dir="logs",
    level=logging.INFO,
    to_console=True,
    to_file=True,
    use_color=True,
    make_global=True
):
    """
    - Creates logs/YYYY-MM-DD/app_logger.log
    - Rotates daily at midnight
    - Keeps last 7 logs
    """

    global _active_logger

    # --- Folder per day ---
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(log_dir, today)
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    # 🔴 IMPORTANT: prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(level)
    logger.propagate = False

    # --- File Handler (daily rotation) ---
    if to_file:
        file_path = os.path.join(log_dir, f"{name}.log")

        file_handler = TimedRotatingFileHandler(
            file_path,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )

        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(_get_formatter(False))
        file_handler.setLevel(logging.DEBUG)

        logger.addHandler(file_handler)

    # --- Console ---
    if to_console:
        _add_console_handler(logger, level, use_color)

    # --- Make Global ---
    if make_global:
        _active_logger = logger

    return logger


# --- Exception Decorator ---
def log_exceptions(level="error", return_value=None, raise_error=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_global_logger()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls_name = args[0].__class__.__name__ if args else ""
                context = f"[{cls_name}.{func.__name__}]"

                log_func = getattr(logger, level, logger.error)
                log_func(f"{context} {type(e).__name__}: {e}")
                logger.error(traceback.format_exc())

                if raise_error:
                    raise
                return return_value

        return wrapper
    return decorator