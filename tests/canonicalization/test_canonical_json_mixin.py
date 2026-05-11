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