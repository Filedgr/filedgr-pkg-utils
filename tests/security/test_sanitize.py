import copy
from filedgr_pkg_utils.security.sanitizer import sanitize_data


def test_sanitize_flat_dict():
    """Test basic flat dictionary sanitization."""
    payload = {
        "username": "alice",
        "password": "super_secret_password",
        "age": 30
    }

    result = sanitize_data(payload)

    assert result["username"] == "alice"
    assert result["age"] == 30
    assert result["password"] == "*****"


def test_sanitize_nested_dict():
    """Test that it recursively enters nested dictionaries."""
    payload = {
        "user": "bob",
        "auth": {
            "method": "oauth",
            "token": "sensitive_jwt_token"
        }
    }

    result = sanitize_data(payload)

    assert result["user"] == "bob"
    assert result["auth"]["method"] == "oauth"
    assert result["auth"]["token"] == "*****"


def test_sanitize_list_of_dicts():
    """Test that it recursively traverses lists and tuples."""
    payload = [
        {"id": 1, "secret": "hide_me"},
        {"id": 2, "api_key": "hide_me_too"}
    ]

    result = sanitize_data(payload)

    assert result[0]["secret"] == "*****"
    assert result[1]["api_key"] == "*****"
    assert result[0]["id"] == 1


def test_sanitize_case_insensitive():
    """Test that capitalized and mixed-case keys are caught."""
    payload = {
        "API_KEY": "key_1",
        "Password": "pass",
        "Authorization": "Bearer 123"
    }

    result = sanitize_data(payload)

    assert result["API_KEY"] == "*****"
    assert result["Password"] == "*****"
    assert result["Authorization"] == "*****"


def test_sanitize_custom_keys_and_mask():
    """Test that a developer can provide custom keys and mask strings."""
    payload = {
        "user_id": "123",
        "favorite_color": "blue"
    }

    result = sanitize_data(
        payload,
        sensitive_keys=["favorite_color"],
        mask="[REDACTED]"
    )

    assert result["user_id"] == "123"
    assert result["favorite_color"] == "[REDACTED]"


def test_sanitize_does_not_mutate_original():
    """CRITICAL: Ensure the original payload is not modified in memory."""
    payload = {
        "user": "charlie",
        "password": "my_password",
        "metadata": [{"token": "123"}]
    }

    # Take a snapshot of the original object
    snapshot = copy.deepcopy(payload)

    # Run the sanitizer
    sanitize_data(payload)

    # Assert the original payload is entirely untouched
    assert payload == snapshot
    assert payload["password"] == "my_password"
    assert payload["metadata"][0]["token"] == "123"


def test_sanitize_primitives():
    """Test that passing non-iterable primitives directly doesn't crash."""
    assert sanitize_data("just a string") == "just a string"
    assert sanitize_data(12345) == 12345
    assert sanitize_data(None) is None