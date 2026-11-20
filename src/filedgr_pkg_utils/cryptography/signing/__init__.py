"""Signing. Secp256k1Algorithm needs the 'crypto' extra, Secp256k1EvmAlgorithm the 'evm' extra."""
import importlib
from typing import Any

from .hmac_signature_algorithm import HmacAlgorithm
from .signature_algorithm import SignatureAlgorithm
from .signature_utils import SignatureUtils
from .conversion_utils import sig_hex_to_vrs

# Classes needing an optional extra are imported on first access, so the rest
# of this package works without that extra installed.
_LAZY = {
    "Secp256k1Algorithm": ".secp256k1_signature_algorithm",
    "Secp256k1EvmAlgorithm": ".secp256k1_evm_signature_algorithm",
}

__all__ = ["HmacAlgorithm", "SignatureAlgorithm", "SignatureUtils", "sig_hex_to_vrs", "Secp256k1Algorithm", "Secp256k1EvmAlgorithm"]


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        value = getattr(importlib.import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
