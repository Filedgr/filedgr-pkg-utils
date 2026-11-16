import os
import logging
from unittest.mock import patch
from filedgr_pkg_utils.fldgr_logging.structured_logger import LoggerFactory
from filedgr_pkg_utils.fldgr_logging.sanitizer_logger_adapter import SanitizerLoggerAdapter


def test_logger_factory_sanitizes_by_default():
    """Ensure that out-of-the-box, the factory protects the system."""
    logger = LoggerFactory.get_logger("default_test")

    assert isinstance(logger, SanitizerLoggerAdapter)


def test_logger_factory_disables_sanitization_via_param():
    """Ensure developers can turn it off via code parameter."""
    logger = LoggerFactory.get_logger("param_test", sanitize_pii=False)

    # Should be a raw logging.Logger, NOT our SecureAdapter
    assert not isinstance(logger, SanitizerLoggerAdapter)
    assert isinstance(logger, logging.Logger)


@patch.dict(os.environ, {"FILEDGR_SANITIZE_LOGS": "false"})
def test_logger_factory_disables_sanitization_via_env_var():
    """Ensure DevOps can turn it off globally via environment variables."""
    logger = LoggerFactory.get_logger("env_test")

    assert not isinstance(logger, SanitizerLoggerAdapter)
    assert isinstance(logger, logging.Logger)


@patch.dict(os.environ, {"FILEDGR_SANITIZE_LOGS": "false"})
def test_logger_factory_param_overrides_env_var():
    """Ensure the code parameter overrides the environment variable."""
    # Even though the env var says False, we explicitly request True
    logger = LoggerFactory.get_logger("override_test", sanitize_pii=True)

    assert isinstance(logger, SanitizerLoggerAdapter)

# --- JsonFormatter / handler output ---

import io
import json
import uuid
from datetime import datetime, timezone

from filedgr_pkg_utils.fldgr_logging.structured_logger import JsonFormatter


def _record(msg="hello", extra=None, exc_info=None):
    record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, msg, (), exc_info)
    record.created = 1700000000.123456
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_json_formatter_timestamp_is_utc_millis_z():
    out = json.loads(JsonFormatter().format(_record()))
    assert out["timestamp"] == "2023-11-14T22:13:20.123Z"
    assert out["level"] == "INFO"
    assert out["logger"] == "test.logger"
    assert out["message"] == "hello"


def test_json_formatter_only_emits_user_extras():
    out = json.loads(JsonFormatter().format(_record(extra={"user_id": "123"})))
    assert out["user_id"] == "123"
    # Internal LogRecord attributes (incl. 3.12+ taskName) must not leak
    for internal in ("taskName", "args", "levelno", "pathname", "msecs"):
        assert internal not in out


def test_json_formatter_handles_non_json_extras():
    when = datetime(2024, 1, 1, tzinfo=timezone.utc)
    uid = uuid.UUID(int=1)
    out = json.loads(JsonFormatter().format(_record(extra={"when": when, "id": uid, "obj": object()})))
    assert out["when"] == str(when)
    assert out["id"] == str(uid)
    assert "object" in out["obj"]


def test_json_formatter_core_fields_win_over_extras():
    out = json.loads(JsonFormatter().format(_record(extra={"level": "FAKE", "logger": "spoof"})))
    assert out["level"] == "INFO"
    assert out["logger"] == "test.logger"


def test_json_formatter_includes_exception():
    import sys
    try:
        raise ValueError("boom")
    except ValueError:
        out = json.loads(JsonFormatter().format(_record(exc_info=sys.exc_info())))
    assert "ValueError: boom" in out["exception"]


def test_logger_factory_emits_sanitized_json():
    logger = LoggerFactory.get_logger("json_output_test", sanitize_pii=True)
    handler = logger.logger.handlers[0]
    assert isinstance(handler.formatter, JsonFormatter)

    stream = io.StringIO()
    handler.setStream(stream)
    logger.info("login", extra={"user": "alice", "access_token": "abc"})

    out = json.loads(stream.getvalue())
    assert out["message"] == "login"
    assert out["user"] == "alice"
    assert out["access_token"] == "*****"
