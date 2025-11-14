"""Centralized logging configuration."""
import logging
import sys

from config import config


def setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger with consistent formatting."""
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    # Formatter
    formatter = logging.Formatter(config.LOG_FORMAT)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger
