import re
from typing import Any, FrozenSet, List, Set, Union

# A robust default set of keys that should almost always be redacted in logs.
# Kept for backwards compatibility; the default matching rules below are a superset.
DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "jwt",
    "bearer",
    "credit_card",
    "ssn",
    "private_key",
    "client_secret"
}

# With the default rules, a key is redacted if its normalized form (lowercase,
# separators removed) CONTAINS one of these words, so variants such as
# "access_token", "refreshToken", "x-api-key" or "db_password" are caught.
DEFAULT_SENSITIVE_SUBSTRINGS: FrozenSet[str] = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "authorization",
    "creditcard",
    "privatekey",
})

# Short words are only matched as the whole key, to avoid false positives
# (e.g. "ssn" inside "classname").
DEFAULT_SENSITIVE_EXACT: FrozenSet[str] = frozenset({"jwt", "bearer", "ssn"})

_SEPARATORS = re.compile(r"[\s_\-.]")


def _normalize(key: str) -> str:
    return _SEPARATORS.sub("", key.lower())


def is_sensitive_key(key: Any) -> bool:
    """Returns True if ``key`` matches the default sensitive-key rules."""
    if not isinstance(key, str):
        return False
    normalized = _normalize(key)
    if normalized in DEFAULT_SENSITIVE_EXACT:
        return True
    return any(word in normalized for word in DEFAULT_SENSITIVE_SUBSTRINGS)


def sanitize_data(
    data: Any,
    sensitive_keys: Union[Set[str], List[str], None] = None,
    mask: str = "*****"
) -> Any:
    """
    Recursively scans dictionaries, lists and tuples, replacing the values of
    sensitive keys with a mask string. Builds a new object without mutating the original.

    :param data: The input dictionary, list, or primitive to sanitize.
    :param sensitive_keys: A custom list/set of keys to redact (exact, case-insensitive match).
                           If omitted, the default rules are used: any key containing one of
                           DEFAULT_SENSITIVE_SUBSTRINGS, or equal to one of DEFAULT_SENSITIVE_EXACT,
                           ignoring case and the separators ``_``, ``-``, ``.`` and spaces.
    :param mask: The string used to replace sensitive values.
    :return: A sanitized copy of the data.
    """
    if sensitive_keys is None:
        matches = is_sensitive_key
    else:
        target_keys = {k.lower() for k in sensitive_keys}

        def matches(key: Any) -> bool:
            return isinstance(key, str) and key.lower() in target_keys

    def _walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: (mask if matches(k) else _walk(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [_walk(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_walk(item) for item in value)
        # Primitive types (strings, ints, floats, booleans, None) are returned untouched
        return value

    return _walk(data)
