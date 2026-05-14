import json
import os
import logging
import pytest

from filedgr_pkg_utils.fldgr_logging.structured_logger import LoggerFactory


def test_logger_json_format(capsys):
    """Test that the logger correctly formats basic logs to JSON."""
    logger = LoggerFactory.get_logger("test_logger", enabled=True)
    logger.info("hello world")

    # Capture stdout
    captured = capsys.readouterr()
    log_output = captured.err  # StreamHandler defaults to sys.stderr

    assert log_output != ""

    # Parse the captured JSON string
    log_dict = json.loads(log_output)
    assert log_dict["level"] == "INFO"
    assert log_dict["message"] == "hello world"
    assert log_dict["logger"] == "test_logger"
    assert "timestamp" in log_dict


def test_logger_extra_kwargs(capsys):
    """Test that the logger injects the `extra` dictionary into the JSON root."""
    logger = LoggerFactory.get_logger("test_kwargs", enabled=True)
    logger.warning("file uploaded", extra={"file_id": "123", "user_id": 999})

    captured = capsys.readouterr()
    log_dict = json.loads(captured.err)

    assert log_dict["level"] == "WARNING"
    assert log_dict["message"] == "file uploaded"
    assert log_dict["file_id"] == "123"
    assert log_dict["user_id"] == 999


def test_logger_disabled_programmatically(capsys):
    """Test that setting enabled=False mutes all output."""
    logger = LoggerFactory.get_logger("silent_logger", enabled=False)
    logger.error("this should not print")

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""

    # Ensure it attached the NullHandler
    assert isinstance(logger.handlers[0], logging.NullHandler)


def test_logger_disabled_via_env_var(capsys, monkeypatch):
    """Test that the FILEDGR_LOGGING_ENABLED environment variable silences output."""
    # Mock the environment variable
    monkeypatch.setenv("FILEDGR_LOGGING_ENABLED", "false")

    # Do not pass the `enabled` kwarg, forcing it to read the env var
    logger = LoggerFactory.get_logger("env_logger")
    logger.critical("this should not print either")

    captured = capsys.readouterr()
    assert captured.err == ""
    assert isinstance(logger.handlers[0], logging.NullHandler)


def test_logger_exception_formatting(capsys):
    """Test that exceptions are caught and formatted inside the JSON structure."""
    logger = LoggerFactory.get_logger("error_logger", enabled=True)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("A math error occurred")

    captured = capsys.readouterr()
    log_dict = json.loads(captured.err)

    assert log_dict["level"] == "ERROR"
    assert log_dict["message"] == "A math error occurred"
    assert "ZeroDivisionError" in log_dict["exception"]