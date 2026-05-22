"""Hex-string normalization helpers for EVM logs / topics / data fields.

web3.py returns topic / data / address values as a mix of native ``bytes``,
``HexBytes``, and 0x-prefixed strings depending on the call path and the
provider. Downstream code that compares these against ABI-derived topic0
values or stores them in DynamoDB consistently needs a normalized form:
lowercase, 0x-prefixed hex.

These helpers do exactly that — nothing more. No web3 dependency; only
duck-typing on ``.hex()`` for objects that quack like ``HexBytes``.
"""
# Standard library imports
from typing import Any, Dict, List, Optional


def normalize_hex(value: Any) -> Optional[str]:
    """Coerce ``value`` to a lowercase 0x-prefixed hex string.

    Accepts:
      * ``None`` → returns ``None``
      * ``str`` (with or without ``0x`` prefix) → returns lowercase 0x-prefixed
      * ``bytes`` / ``bytearray`` → ``"0x" + value.hex().lower()``
      * Anything with a ``.hex()`` method (e.g. web3's ``HexBytes``) → uses it
      * Falls back to ``str(value).lower()`` for the rare degenerate case
    """
    if value is None:
        return None
    if isinstance(value, str):
        s = value.lower()
    elif isinstance(value, (bytes, bytearray)):
        s = "0x" + value.hex().lower()
    else:
        try:
            s = value.hex().lower()
        except AttributeError:
            s = str(value).lower()
    if not s.startswith("0x"):
        s = "0x" + s
    return s


def normalize_topic(topic: Any) -> str:
    """Same as :func:`normalize_hex` but never returns ``None``.

    Topic0 + indexed topics are always present in a valid EVM log; treating
    them as ``None``-able would mask a producer bug. Callers that legitimately
    need an optional form should use :func:`normalize_hex` directly.
    """
    out = normalize_hex(topic)
    if out is None:
        raise ValueError("topic value cannot be None")
    return out


def normalize_log(log_entry: Any) -> Dict[str, Any]:
    """Project an arbitrary web3 log object into a plain JSON-safe dict.

    Returned shape::

        {
            "address": "0x..." | None,
            "topics":  ["0x...", ...],
            "data":    "0x..." | None,
        }

    Useful as the input to ABI decoders that operate on plain dicts.
    """
    if hasattr(log_entry, "get"):
        topics_raw: List[Any] = list(log_entry.get("topics", []) or [])
        return {
            "address": normalize_hex(log_entry.get("address")),
            "topics": [normalize_topic(t) for t in topics_raw],
            "data": normalize_hex(log_entry.get("data")) or "0x",
        }
    # AttributeDict-style fallback: getattr-only access.
    topics_attr: List[Any] = list(getattr(log_entry, "topics", []) or [])
    return {
        "address": normalize_hex(getattr(log_entry, "address", None)),
        "topics": [normalize_topic(t) for t in topics_attr],
        "data": normalize_hex(getattr(log_entry, "data", None)) or "0x",
    }
