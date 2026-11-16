import json
import logging
import os
from datetime import datetime, timezone
from typing import Union

from filedgr_pkg_utils.fldgr_logging.sanitizer_logger_adapter import SanitizerLoggerAdapter


# Attributes every LogRecord carries; anything else on a record came from `extra=`.
# Computed from a real record so new Python versions (e.g. 3.12's taskName) are covered.
_RESERVED_RECORD_ATTRS = frozenset(
    logging.LogRecord("", logging.INFO, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """
    Formats standard Python log records into a deterministic JSON structure.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject any extra contextual data passed to the logger
        # e.g., logger.info("User logged in", extra={"user_id": "123"})
        # Core fields above always win over an extra with the same name.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS and key not in log_obj:
                log_obj[key] = value

        # Handle Exception traces safely
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_obj["stack_info"] = self.formatStack(record.stack_info)

        # default=str: a non-JSON value in `extra` (datetime, UUID, custom object)
        # must never make the log line disappear.
        return json.dumps(log_obj, default=str)


class LoggerFactory:
    @staticmethod
    def get_logger(
            name: str,
            sanitize_pii: Union[bool, None] = None
    ) -> Union[logging.Logger, logging.LoggerAdapter]:
        """
        Creates and configures a logger for the application.

        :param name: The name of the logger (usually __name__).
        :param sanitize_pii: If True, wraps the logger in a PII Sanitizer.
                             If None, defaults to the 'FILEDGR_SANITIZE_LOGS' env variable (default: True).
        """
        # 1. Determine if we should sanitize based on param or environment variable
        if sanitize_pii is None:
            # Default to True for safety, unless explicitly disabled in the environment
            env_sanitize = os.getenv("FILEDGR_SANITIZE_LOGS", "true").lower()
            should_sanitize = env_sanitize in ("true", "1", "yes")
        else:
            should_sanitize = sanitize_pii

        # 2. Get the base logger
        base_logger = logging.getLogger(name)

        # Configure handlers, formatters, and log levels if not already set up
        if not base_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            base_logger.addHandler(handler)
            base_logger.setLevel(logging.INFO)

        # 3. Return the Secure Adapter or the raw Base Logger
        if should_sanitize:
            # Secure mode: Intercepts and masks sensitive data
            return SanitizerLoggerAdapter(base_logger, extra={})
        else:
            # Raw mode: Highly dangerous for production, great for local debugging
            return base_logger
