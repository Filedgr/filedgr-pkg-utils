"""Canonical JSON mixins. Both need the 'canonical' extra."""
import importlib
from typing import Any


# Classes needing an optional extra are imported on first access, so the rest
# of this package works without that extra installed.
_LAZY = {
    "CanonicalJsonMixin": ".canonical_json_mixin",
    "CanonicalJsonMixinV2": ".canonical_json_mixin_v2",
}

__all__ = ["CanonicalJsonMixin", "CanonicalJsonMixinV2"]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        value = getattr(importlib.import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
