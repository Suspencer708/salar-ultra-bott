"""
Logger for SALAAR X SPENCER ULTRA BOT
Centralized logging with file rotation and color coding
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT, LOG_MAX_SIZE, LOG_BACKUP_COUNT

# Color codes for console output
COLORS = {
    'grey': '\x1b[38;21m',
    'green': '\x1b[38;5;82m',
    'yellow': '\x1b[38;5;226m',
    'red': '\x1b[38;5;196m',
    'bold_red': '\x1b[31;1m',
    'blue': '\x1b[38;5;39m',
    'cyan': '\x1b[38;5;51m',
    'purple': '\x1b[38;5;129m',
    'reset': '\x1b[0m'
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    def __init__(self, fmt):
        super().__init__(fmt)
        self.FORMATS = {
            logging.DEBUG: COLORS['grey'] + fmt + COLORS['reset'],
            logging.INFO: COLORS['green'] + fmt + COLORS['reset'],
            logging.WARNING: COLORS['yellow'] + fmt + COLORS['reset'],
            logging.ERROR: COLORS['red'] + fmt + COLORS['reset'],
            logging.CRITICAL: COLORS['bold_red'] + fmt + COLORS['reset']
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger(name: str = __name__) -> logging.Logger:
    """Setup and configure logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Remove existing handlers
    logger.handlers.clear()

    # File handler with rotation
    if LOG_FILE:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """Get logger instance"""
    return setup_logger(name)