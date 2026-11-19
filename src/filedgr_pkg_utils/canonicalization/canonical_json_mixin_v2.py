from datetime import datetime, timezone
from typing import Any, ClassVar

import rfc8785
from pydantic import BaseModel
from pydantic_core import to_jsonable_python


def _utf16_key(value: str) -> bytes:
    return value.encode("utf-16-be")


def _sorted_set_items(items: list) -> list:
    if all(isinstance(i, (int, float)) and not isinstance(i, bool) for i in items):
        return sorted(items)
    if all(isinstance(i, str) for i in items):
        return sorted(items, key=_utf16_key)
    return sorted(items, key=rfc8785.dumps)


class CanonicalJsonMixinV2(BaseModel):
    """
    Canonical JSON per RFC 8785 (JSON Canonicalization Scheme, JCS), for hashing
    and signing. Any JCS implementation (JavaScript, Go, Rust, Java, ...) given
    the same JSON value produces the same bytes.

    RFC 8785 rules (applied by the ``rfc8785`` library):

    - object keys sorted by their UTF-16 code units; no whitespace
    - numbers written the way JavaScript writes them (``1.0`` -> ``1``,
      ``1e21`` -> ``1e+21``); NaN and infinity are rejected
    - integers must be within +/- 2**53 - 1 (larger values, e.g. wei amounts,
      must be modelled as strings) -- otherwise ``ValueError``
    - strings use the minimal escaping defined by the RFC

    Conventions on top of RFC 8785 (JCS itself has no datetime type):

    - datetimes are converted to UTC and written as ISO 8601 with a ``Z`` suffix
      and a fixed number of fractional digits, set by
      ``canonical_datetime_precision`` ("milliseconds" by default, like
      JavaScript's ``Date.toISOString()``; subclasses may set "microseconds").
      Extra precision is truncated.
    - naive datetimes (no timezone) are rejected with ``ValueError``: their
      instant is ambiguous, which is unacceptable for signed data.
    - sets are written as sorted arrays: numbers by value, strings by UTF-16
      code units (the same order JCS uses for keys), anything else (mixed or
      nested values) by the bytes of each element's canonical encoding.
    - other values (Decimal, UUID, Enum, bytes, date, time, timedelta, ...) use
      pydantic's JSON representation (e.g. ``Decimal("1.50")`` -> ``"1.50"``).

    The model is dumped in pydantic's python mode, so field serializers declared
    with ``when_used="json"`` or ``"json-unless-none"`` are NOT applied; use
    ``when_used="always"`` for serializers that should affect the canonical form.
    """

    canonical_datetime_precision: ClassVar[str] = "milliseconds"

    @classmethod
    def _canonical_datetime(cls, value: datetime) -> str:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(
                f"Naive datetime {value.isoformat()} cannot be canonicalized: "
                "attach a timezone (e.g. tzinfo=timezone.utc)."
            )
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec=cls.canonical_datetime_precision)
            .replace("+00:00", "Z")
        )

    @classmethod
    def _to_canonical_tree(cls, value: Any) -> Any:
        """Converts a python-mode dump into plain JSON values (dict/list/str/int/float/bool/None)."""
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, datetime):
            return cls._canonical_datetime(value)
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    # Same key conversion as pydantic's JSON mode (e.g. 1 -> "1")
                    key = next(iter(to_jsonable_python({key: None})))
                out[key] = cls._to_canonical_tree(item)
            return out
        if isinstance(value, (list, tuple)):
            return [cls._to_canonical_tree(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return _sorted_set_items([cls._to_canonical_tree(item) for item in value])
        return cls._to_canonical_tree(to_jsonable_python(value))

    def canonical_json_bytes(self) -> bytes:
        """
        RFC 8785 canonical JSON as UTF-8 bytes (best for hashing & signing).

        :raises ValueError: for naive datetimes, NaN/infinity, or integers
                            outside the JSON-safe range.
        """
        tree = self._to_canonical_tree(self.model_dump(mode="python"))
        try:
            return rfc8785.dumps(tree)
        except rfc8785.CanonicalizationError as exc:
            raise ValueError(f"Payload cannot be canonicalized per RFC 8785: {exc}") from exc

    def canonical_json(self) -> str:
        """
        RFC 8785 canonical JSON as a string.
        """
        return self.canonical_json_bytes().decode("utf-8")
