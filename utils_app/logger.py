import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_LEVEL


class Logger:

    _instance = None

    @classmethod
    def get_logger(cls):

        if cls._instance:
            return cls._instance

        logger = logging.getLogger("FinancialParser")
        logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

        logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        cls._instance = logger

        return logger


logger = Logger.get_logger()


def info(message):
    logger.info(message)


def warning(message):
    logger.warning(message)


def error(message):
    logger.error(message)


def debug(message):
    logger.debug(message)


def exception(message):
    logger.exception(message)