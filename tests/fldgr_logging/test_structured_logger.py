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