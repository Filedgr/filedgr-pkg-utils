"""Compression algorithms. Zstd and Brotli need the 'compression' extra."""
import importlib
from typing import Any

from .algorithms.compression_algorithm_zip import ZipAlgorithm
from .algorithms.compression_algortihm_gzip import GzipAlgorithm
from .compression_algorithm import CompressionAlgorithm
from .compression_utils import CompressionUtils

# Classes needing an optional extra are imported on first access, so the rest
# of this package works without that extra installed.
_LAZY = {
    "ZstdAlgorithm": ".algorithms.compression_algorithm_zstd",
    "BrotliAlgorithm": ".algorithms.compression_algorithm_brotli",
}

__all__ = ["ZipAlgorithm", "GzipAlgorithm", "CompressionAlgorithm", "CompressionUtils", "ZstdAlgorithm", "BrotliAlgorithm"]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        value = getattr(importlib.import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
