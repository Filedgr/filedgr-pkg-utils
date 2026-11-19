from datetime import datetime, timezone, timedelta
import pytest

from filedgr_pkg_utils.canonicalization.canonical_json_mixin import CanonicalJsonMixin


# --- Test Models ---

class StandardPayload(CanonicalJsonMixin):
    z_field: str
    a_field: int
    m_field: str


class DatetimePayload(CanonicalJsonMixin):
    timestamp: datetime


# --- Tests ---

def test_canonical_json_sorting_and_whitespace():
    """
    Tests that keys are strictly alphabetically sorted and there is no
    superfluous whitespace in the resulting JSON string/bytes.
    """
    payload = StandardPayload(
        z_field="last",
        m_field="middle",
        a_field=1,
    )

    # 1. Test bytes generation
    json_bytes = payload.canonical_json_bytes()
    assert isinstance(json_bytes, bytes)

    # Expected output: Sorted keys (a_field, m_field, z_field), no spaces
    expected_str = '{"a_field":1,"m_field":"middle","z_field":"last"}'
    assert json_bytes == expected_str.encode('utf-8')

    # 2. Test string generation
    json_str = payload.canonical_json()
    assert isinstance(json_str, str)
    assert json_str == expected_str


def test_canonical_json_datetime_serialization():
    """
    Tests that datetimes are correctly dumped into the JSON representation.
    Note: Pydantic V2's `model_dump(mode="json")` natively converts datetimes
    to strings, but we test the end-to-end integration here.
    """
    # Create a datetime in UTC
    dt = datetime(2023, 10, 25, 12, 34, 56, 789000, tzinfo=timezone.utc)
    payload = DatetimePayload(timestamp=dt)

    json_str = payload.canonical_json()

    # It should correctly represent the ISO format
    assert '"timestamp":"2023-10-25T12:34:56.789000Z"' in json_str


def test_default_datetime_formatter():
    """
    Tests the static `_default` fallback method directly to ensure it
    enforces UTC + milliseconds + Z formatting correctly.
    """
    # Datetime with a non-UTC timezone (e.g., UTC+2)
    tz_plus_2 = timezone(timedelta(hours=2))
    dt = datetime(2023, 1, 1, 14, 30, 0, tzinfo=tz_plus_2)

    # Convert using the static default method
    formatted = CanonicalJsonMixin._default(dt)

    # 14:30 at UTC+2 is 12:30 UTC. Expected to convert to UTC and format with Z.
    assert formatted == "2023-01-01T12:30:00.000Z"


def test_default_type_error_on_unknown():
    """
    Tests that the fallback `_default` method correctly rejects non-datetime
    objects with a TypeError.
    """

    class UnserializableObject:
        pass

    with pytest.raises(TypeError):
        CanonicalJsonMixin._default(UnserializableObject())

# --- Frozen output: existing signatures depend on these exact bytes. ---
# If one of these fails, the change breaks verification of already-signed
# payloads. Put the new behaviour in CanonicalJsonMixinV2 instead.

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID

from pydantic import Field, computed_field, field_serializer


class _Color(Enum):
    RED = "red"


class _Plain(CanonicalJsonMixin):
    z: str
    a: int
    f: float
    b: bool
    n: Optional[str] = None


class _Nested(CanonicalJsonMixin):
    items: List[Dict[str, int]]
    inner: Optional[_Plain] = None


class _Types(CanonicalJsonMixin):
    dec: Decimal
    u: UUID
    c: _Color
    raw: bytes
    d: object
    s: Set[int]


class _Aliased(CanonicalJsonMixin):
    user_id: str = Field(alias="userId")


class _JsonOnlySerializer(CanonicalJsonMixin):
    v: int

    @field_serializer("v", when_used="json")
    def _ser(self, v):
        return f"json-{v}"


class _Computed(CanonicalJsonMixin):
    x: int

    @computed_field
    @property
    def doubled(self) -> int:
        return self.x * 2


class _OptDT(CanonicalJsonMixin):
    ts: Optional[datetime] = None


@pytest.mark.parametrize("payload, expected", [
    (_Plain(z="é ü", a=1, f=1.5, b=True), '{"a":1,"b":true,"f":1.5,"n":null,"z":"é ü"}'),
    (_Plain(z="", a=0, f=1.0, b=False), '{"a":0,"b":false,"f":1.0,"n":null,"z":""}'),
    (
        _Nested(items=[{"b": 2, "a": 1}], inner=_Plain(z="x", a=2, f=0.1, b=True)),
        '{"inner":{"a":2,"b":true,"f":0.1,"n":null,"z":"x"},"items":[{"a":1,"b":2}]}',
    ),
    (
        _Types(dec=Decimal("1.50"), u=UUID(int=1), c=_Color.RED, raw=b"abc", d="2024-01-02", s={3}),
        '{"c":"red","d":"2024-01-02","dec":"1.50","raw":"abc","s":[3],"u":"00000000-0000-0000-0000-000000000001"}',
    ),
    (_Aliased(userId="u1"), '{"user_id":"u1"}'),
    (_JsonOnlySerializer(v=2), '{"v":"json-2"}'),
    (_Computed(x=2), '{"doubled":4,"x":2}'),
    (_OptDT(), '{"ts":null}'),
    (DatetimePayload(timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)), '{"timestamp":"2024-01-01T12:00:00Z"}'),
    (
        DatetimePayload(timestamp=datetime(2024, 1, 1, 12, 0, 0, 789000, tzinfo=timezone.utc)),
        '{"timestamp":"2024-01-01T12:00:00.789000Z"}',
    ),
    (
        DatetimePayload(timestamp=datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)),
        '{"timestamp":"2024-01-01T12:00:00.123456Z"}',
    ),
    (
        DatetimePayload(timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))),
        '{"timestamp":"2024-01-01T12:00:00+02:00"}',
    ),
    (DatetimePayload(timestamp=datetime(2024, 1, 1, 12, 0, 0)), '{"timestamp":"2024-01-01T12:00:00"}'),
    (DatetimePayload(timestamp="2024-01-01T12:00:00.000Z"), '{"timestamp":"2024-01-01T12:00:00Z"}'),
])
def test_v1_output_is_frozen(payload, expected):
    assert payload.canonical_json() == expected
    assert payload.canonical_json_bytes() == expected.encode("utf-8")
