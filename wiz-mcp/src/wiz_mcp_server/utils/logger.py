import json
import logging
import os
import sys

DEFAULT_LOGGER_NAME = "wiz.io.mcp_server"


class CustomFormatter(logging.Formatter):
    """Custom formatter for CSV logs."""

    def format(self, record):
        wiz_env = os.getenv("WIZ_ENV", "default")
        record.wiz_env = wiz_env
        record.timestamp = self.formatTime(record, self.datefmt)
        return f'{record.timestamp},{record.levelname},{record.wiz_env},{record.filename}:{record.lineno},"{record.msg}"'


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON logs."""

    def format(self, record):
        wiz_env = os.getenv("WIZ_ENV", "default")
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "wiz_env": wiz_env,
            "file": record.filename,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)


def get_logger(name: str = None) -> logging.Logger:
    """Create and configure a logger."""
    name = name or DEFAULT_LOGGER_NAME
    logger = logging.getLogger(name)
    logger.propagate = False

    if not logger.hasHandlers():
        log_format = os.getenv("LOG_FORMAT", "CSV").upper()
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        logger.setLevel(log_level)

        handler = logging.StreamHandler(stream=sys.stderr)

        if log_format == "JSON":
            formatter = JSONFormatter()
        else:  # Default to CSV
            formatter = CustomFormatter(fmt="%(asctime)s,%(levelname)s,%(wiz_env)s,%(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
