"""Perceptual image hashing. The algorithms need the 'images' extra."""
import importlib
from typing import Any

from .image_hash_algorithm import ImageHashAlgorithm
from .image_hash_utils import ImageHashUtils

# Classes needing an optional extra are imported on first access, so the rest
# of this package works without that extra installed.
_LAZY = {
    "AHashAlgorithm": ".algorithms.image_hashing_algorithm_ahash",
    "DHashAlgorithm": ".algorithms.image_hashing_algorithm_dhash",
    "PHashAlgorithm": ".algorithms.image_hashing_algorithm_phash",
}

__all__ = ["ImageHashAlgorithm", "ImageHashUtils", "AHashAlgorithm", "DHashAlgorithm", "PHashAlgorithm"]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        value = getattr(importlib.import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
