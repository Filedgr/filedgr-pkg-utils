from datetime import datetime, timezone
from typing import Any

import orjson
from pydantic import BaseModel
from pydantic_core import to_jsonable_python


class CanonicalJsonMixin(BaseModel):
    """
    Deterministic, whitespace-free, sorted-key JSON serialization.
    Suitable for hashing, signing, and blockchain payloads.

    Datetimes are always emitted in UTC with millisecond precision and a ``Z``
    suffix (e.g. ``2023-01-01T12:30:00.000Z``). Naive datetimes are treated as
    UTC so the output never depends on the host's local timezone.
    """

    @staticmethod
    def _default(obj: Any):
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            # Enforce UTC + milliseconds + Z
            return (
                obj.astimezone(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
        raise TypeError

    @classmethod
    def _serialize_fallback(cls, obj: Any):
        """orjson ``default`` hook: canonical datetimes, pydantic for everything else."""
        if isinstance(obj, datetime):
            return cls._default(obj)
        # Decimal, bytes, sets, etc. -> the same representation pydantic's JSON mode uses
        return to_jsonable_python(obj)

    def canonical_json_bytes(self) -> bytes:
        """
        Canonical JSON as bytes (best for hashing & signing).
        """
        # Dump in python mode so datetimes reach our formatter instead of being
        # pre-stringified by pydantic's JSON mode.
        return orjson.dumps(
            self.model_dump(mode="python"),
            option=orjson.OPT_SORT_KEYS | orjson.OPT_PASSTHROUGH_DATETIME,
            default=self._serialize_fallback,
        )

    def canonical_json(self) -> str:
        """
        Canonical JSON as UTF-8 string.
        """
        return self.canonical_json_bytes().decode("utf-8")
