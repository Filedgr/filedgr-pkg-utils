import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    """
    Formats standard Python log records into a deterministic JSON structure.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject any extra contextual data passed to the logger
        # e.g., logger.info("User logged in", extra={"user_id": "123"})
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                           "funcName", "levelname", "levelno", "lineno", "module",
                           "msecs", "message", "msg", "name", "pathname", "process",
                           "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                log_obj[key] = value

        # Handle Exception traces safely
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class LoggerFactory:
    """
    Factory to retrieve a pre-configured, structured JSON logger.
    """

    @staticmethod
    def get_logger(name: str, enabled: Optional[bool] = None, level: int = logging.INFO) -> logging.Logger:
        """
        Retrieves a configured JSON logger.

        :param name: The name of the logger (usually __name__).
        :param enabled: Explicitly enable/disable fldgr_logging. If None, checks the
                        FILEDGR_LOGGING_ENABLED environment variable.
        :param level: The fldgr_logging level (e.g., fldgr_logging.INFO, fldgr_logging.DEBUG).
        """
        logger = logging.getLogger(name)

        # Clear existing handlers to prevent duplicate log lines if called multiple times
        if logger.hasHandlers():
            logger.handlers.clear()

        # Determine if fldgr_logging should be enabled (Code takes precedence over Env Vars)
        if enabled is None:
            env_enabled = os.getenv("FILEDGR_LOGGING_ENABLED", "true").lower()
            is_enabled = env_enabled in ("true", "1", "yes")
        else:
            is_enabled = enabled

        # If disabled, attach a NullHandler (logs go into the void with zero overhead)
        if not is_enabled:
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            return logger

        # If enabled, attach the JSON Formatter outputting to stdout
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())

        logger.addHandler(handler)
        logger.setLevel(level)
        # Prevent logs from propagating to the root logger and printing twice
        logger.propagate = False

        return logger
