from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Dict, FrozenSet, List, Optional, Set
from uuid import UUID

import pytest
from pydantic import field_serializer

from filedgr_pkg_utils.canonicalization import CanonicalJsonMixin, CanonicalJsonMixinV2


class DT(CanonicalJsonMixinV2):
    ts: datetime


def test_rfc8785_reference_example():
    """The worked example from RFC 8785, section 3.2.2 / appendix."""

    class Example(CanonicalJsonMixinV2):
        numbers: List[float]
        string: str
        literals: List[Optional[bool]]

    # RFC 8785 input string: \u20ac $ \u000f \u000a A ' \u0042 \u0022 \u005c \\ \" /
    rfc_string = ''.join(chr(c) for c in (
        0x20AC, 0x24, 0x0F, 0x0A, 0x41, 0x27, 0x42, 0x22, 0x5C, 0x5C, 0x22, 0x2F,
    ))
    payload = Example(
        numbers=[333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
        string=rfc_string,
        literals=[None, True, False],
    )
    # Expected string value per the RFC: \u20ac stays literal, \u000f -> \\u000f,
    # newline -> \\n, quote -> \\", backslash -> \\\\
    expected_string = (
        chr(0x20AC) + '$' + chr(92) + 'u000f' + chr(92) + 'n' + "A'B"
        + chr(92) + '"' + chr(92) + chr(92) + chr(92) + chr(92) + chr(92) + '"' + '/'
    )
    expected = (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"' + expected_string + '"}'
    )
    assert payload.canonical_json() == expected


def test_keys_sorted_by_utf16_and_no_whitespace():
    class Keys(CanonicalJsonMixinV2):
        data: Dict[str, int]

    # U+1F600 (UTF-16 D83D DE00) sorts before U+FB01 in UTF-16, after it by code point
    emoji, ligature = chr(0x1F600), chr(0xFB01)
    payload = Keys(data={ligature: 2, emoji: 1, "b": 0, "a": 0})
    assert payload.canonical_json() == '{"data":{"a":0,"b":0,"' + emoji + '":1,"' + ligature + '":2}}'


def test_numbers_follow_javascript_formatting():
    class Nums(CanonicalJsonMixinV2):
        values: List[float]
        count: int

    assert Nums(values=[1.0, 1e21, 0.1, -0.0], count=3).canonical_json() == (
        '{"count":3,"values":[1,1e+21,0.1,0]}'
    )


def test_datetime_default_is_utc_milliseconds_z():
    assert DT(ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)).canonical_json() == (
        '{"ts":"2024-01-01T12:00:00.000Z"}'
    )
    assert DT(ts=datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)).canonical_json() == (
        '{"ts":"2024-01-01T12:00:00.123Z"}'
    )


def test_datetime_other_offsets_are_converted_to_utc():
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert DT(ts=ts).canonical_json() == '{"ts":"2024-01-01T10:00:00.000Z"}'


def test_same_instant_same_bytes():
    utc = DT(ts=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))
    plus2 = DT(ts=datetime(2024, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2))))
    parsed = DT(ts="2024-01-01T10:00:00Z")
    assert utc.canonical_json_bytes() == plus2.canonical_json_bytes() == parsed.canonical_json_bytes()


def test_datetime_microsecond_precision_subclass():
    class PreciseDT(CanonicalJsonMixinV2):
        canonical_datetime_precision: ClassVar[str] = "microseconds"
        ts: datetime

    ts = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
    assert PreciseDT(ts=ts).canonical_json() == '{"ts":"2024-01-01T12:00:00.123456Z"}'
    # ClassVar is not a field
    assert "canonical_datetime_precision" not in PreciseDT(ts=ts).model_dump()


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="Naive datetime"):
        DT(ts=datetime(2024, 1, 1, 12, 0, 0)).canonical_json()


def test_nested_models_and_lists_with_datetimes():
    class Inner(CanonicalJsonMixinV2):
        when: datetime

    class Outer(CanonicalJsonMixinV2):
        items: List[Inner]
        plain: Inner

    when = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert Outer(items=[Inner(when=when)], plain=Inner(when=when)).canonical_json() == (
        '{"items":[{"when":"2024-01-01T00:00:00.000Z"}],"plain":{"when":"2024-01-01T00:00:00.000Z"}}'
    )


def test_non_native_types_use_pydantic_json_representation():
    class Color(Enum):
        RED = "red"

    class Types(CanonicalJsonMixinV2):
        dec: Decimal
        u: UUID
        c: Color
        raw: bytes
        d: date
        td: timedelta
        int_keys: Dict[int, str]

    payload = Types(
        dec=Decimal("1.50"), u=UUID(int=1), c=Color.RED, raw=b"abc",
        d=date(2024, 1, 2), td=timedelta(seconds=90), int_keys={2: "b", 1: "a"},
    )
    assert payload.canonical_json() == (
        '{"c":"red","d":"2024-01-02","dec":"1.50","int_keys":{"1":"a","2":"b"},'
        '"raw":"abc","td":"PT1M30S","u":"00000000-0000-0000-0000-000000000001"}'
    )


def test_sets_are_sorted_deterministically():
    class Tags(CanonicalJsonMixinV2):
        names: Set[str]
        nums: FrozenSet[int]

    payload = Tags(names={"zeta", "alpha", "mu"}, nums=frozenset({10, 2, 33}))
    assert payload.canonical_json() == '{"names":["alpha","mu","zeta"],"nums":[2,10,33]}'


def test_set_of_strings_uses_utf16_order():
    class Tags(CanonicalJsonMixinV2):
        names: Set[str]

    emoji, ligature = chr(0x1F600), chr(0xFB01)
    assert Tags(names={ligature, emoji}).canonical_json() == '{"names":["' + emoji + '","' + ligature + '"]}'


def test_set_of_mixed_values_is_deterministic():
    class Mixed(CanonicalJsonMixinV2):
        values: Set[object]

    payloads = [Mixed(values={"b", 1, None, "a", 2.5}) for _ in range(3)]
    outputs = {p.canonical_json() for p in payloads}
    assert len(outputs) == 1


def test_always_serializers_apply_json_only_do_not():
    class Ser(CanonicalJsonMixinV2):
        a: int
        b: int

        @field_serializer("a", when_used="always")
        def _a(self, v):
            return v * 10

        @field_serializer("b", when_used="json")
        def _b(self, v):
            return f"json-{v}"

    assert Ser(a=1, b=2).canonical_json() == '{"a":10,"b":2}'


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_non_finite_floats_are_rejected(value):
    class F(CanonicalJsonMixinV2):
        x: float

    with pytest.raises(ValueError, match="RFC 8785"):
        F(x=value).canonical_json()


def test_unsafe_integers_are_rejected():
    class Amount(CanonicalJsonMixinV2):
        wei: int

    assert Amount(wei=2**53 - 1).canonical_json() == '{"wei":9007199254740991}'
    with pytest.raises(ValueError, match="RFC 8785"):
        Amount(wei=2**53 + 1).canonical_json()


def test_bytes_and_str_agree():
    payload = DT(ts=datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert payload.canonical_json_bytes() == payload.canonical_json().encode("utf-8")


def test_v1_and_v2_are_independent_classes():
    assert not issubclass(CanonicalJsonMixinV2, CanonicalJsonMixin)
    assert not issubclass(CanonicalJsonMixin, CanonicalJsonMixinV2)
