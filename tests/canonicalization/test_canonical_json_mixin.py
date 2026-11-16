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
    Tests that datetimes go through the canonical formatter end-to-end
    (UTC, millisecond precision, Z suffix).
    """
    # Create a datetime in UTC
    dt = datetime(2023, 10, 25, 12, 34, 56, 789000, tzinfo=timezone.utc)
    payload = DatetimePayload(timestamp=dt)

    json_str = payload.canonical_json()

    assert json_str == '{"timestamp":"2023-10-25T12:34:56.789Z"}'


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

def test_canonical_json_non_utc_datetime_is_normalized():
    dt = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone(timedelta(hours=2)))
    assert DatetimePayload(timestamp=dt).canonical_json() == '{"timestamp":"2024-01-01T10:00:00.123Z"}'


def test_canonical_json_naive_datetime_treated_as_utc():
    dt = datetime(2024, 1, 1, 12, 0, 0)
    assert DatetimePayload(timestamp=dt).canonical_json() == '{"timestamp":"2024-01-01T12:00:00.000Z"}'


def test_canonical_json_nested_and_non_native_types():
    from decimal import Decimal
    from typing import List

    class Inner(CanonicalJsonMixin):
        when: datetime
        amount: Decimal

    class Outer(CanonicalJsonMixin):
        items: List[Inner]
        b: str

    payload = Outer(
        b="x",
        items=[Inner(when=datetime(2024, 1, 1, tzinfo=timezone.utc), amount=Decimal("1.50"))],
    )
    assert payload.canonical_json() == (
        '{"b":"x","items":[{"amount":"1.50","when":"2024-01-01T00:00:00.000Z"}]}'
    )
