"""Helpers for features that depend on optional extras."""
import importlib
from types import ModuleType

PACKAGE = "filedgr-pkg-utils"


def missing_extra_error(extra: str, feature: str, cause: BaseException = None) -> ImportError:
    """Builds the ImportError raised when an optional dependency is not installed."""
    detail = f" ({cause})" if cause is not None else ""
    error = ImportError(
        f"{feature} requires the '{extra}' extra{detail}. "
        f"Install it with: pip install \"{PACKAGE}[{extra}]\""
    )
    error.__cause__ = cause
    return error


def require(module: str, extra: str, feature: str) -> ModuleType:
    """Imports ``module`` or raises an ImportError explaining which extra to install."""
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise missing_extra_error(extra, feature, exc) from exc
