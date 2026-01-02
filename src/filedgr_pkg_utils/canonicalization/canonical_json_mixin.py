import orjson
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Any


class CanonicalJsonMixin(BaseModel):
    """
    Deterministic, whitespace-free, sorted-key JSON serialization.
    Suitable for hashing, signing, and blockchain payloads.
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
