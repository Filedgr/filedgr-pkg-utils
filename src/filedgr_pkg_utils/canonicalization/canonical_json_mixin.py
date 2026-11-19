import orjson
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Any


class CanonicalJsonMixin(BaseModel):
    """
    Deterministic, whitespace-free, sorted-key JSON serialization.

    FROZEN FORMAT: existing signatures and hashes depend on these exact bytes,
    so this class must not change its output. Use ``CanonicalJsonMixinV2`` for
    new payloads.

    Note: values are dumped with pydantic's JSON mode before orjson sees them,
    so datetimes keep pydantic's own ISO format (the ``_default`` hook below is
    never reached for model fields):

    - UTC datetimes end in ``Z`` with microseconds only when non-zero
      (``2024-01-01T12:00:00Z``, ``2024-01-01T12:00:00.789000Z``)
    - other offsets are kept as given (``2024-01-01T12:00:00+02:00``)
    - naive datetimes have no offset (``2024-01-01T12:00:00``)
    - floats keep a trailing ``.0`` (``1.0``), so output is not RFC 8785 compliant
    """

    @staticmethod
    def _default(obj: Any):
        if isinstance(obj, datetime):
            # Enforce UTC + milliseconds + Z
            return (
                obj.astimezone(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
        raise TypeError

    def canonical_json_bytes(self) -> bytes:
        """
        Canonical JSON as bytes (best for hashing & signing).
        """
        return orjson.dumps(
            self.model_dump(mode="json"),
            option=orjson.OPT_SORT_KEYS,
            default=self._default,
        )

    def canonical_json(self) -> str:
        """
        Canonical JSON as UTF-8 string.
        """
        return self.canonical_json_bytes().decode("utf-8")
