from typing import Any, List, Set, Union

# A robust default set of keys that should almost always be redacted in logs
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


def sanitize_data(
    data: Any,
    sensitive_keys: Union[Set[str], List[str], None] = None,
    mask: str = "*****"
) -> Any:
    """
    Recursively scans dictionaries and lists, replacing the values of sensitive keys
    with a mask string. Safely builds a new object without mutating the original.

    :param data: The input dictionary, list, or primitive to sanitize.
    :param sensitive_keys: A custom list/set of keys to redact. Defaults to DEFAULT_SENSITIVE_KEYS.
    :param mask: The string used to replace sensitive values.
    :return: A sanitized copy of the data.
    """
    if sensitive_keys is None:
        target_keys = DEFAULT_SENSITIVE_KEYS
    else:
        target_keys = {k.lower() for k in sensitive_keys}

    # Handle Dictionaries
    if isinstance(data, dict):
        sanitized_dict = {}
        for key, value in data.items():
            # Check if the key is a string and if its lowercase version matches our sensitive list
            if isinstance(key, str) and key.lower() in target_keys:
                sanitized_dict[key] = mask
            else:
                # Recursively sanitize nested structures
                sanitized_dict[key] = sanitize_data(value, target_keys, mask)
        return sanitized_dict

    # Handle Lists
    elif isinstance(data, list):
        return [sanitize_data(item, target_keys, mask) for item in data]

    # Handle Tuples
    elif isinstance(data, tuple):
        return tuple(sanitize_data(item, target_keys, mask) for item in data)

    # Return primitive types (strings, ints, floats, booleans, None) untouched
    return data
