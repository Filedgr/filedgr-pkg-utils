import pytest
import asyncio
from filedgr_pkg_utils.security.sanitizer_decorators import sanitize_return


def test_sync_sanitize_return():
    @sanitize_return()
    def fetch_data():
        return {"id": 1, "password": "super_secret"}

    result = fetch_data()

    assert result["id"] == 1
    assert result["password"] == "*****"


@pytest.mark.asyncio
async def test_async_sanitize_return():
    @sanitize_return(sensitive_keys=["custom_secret"], mask="[HIDDEN]")
    async def async_fetch():
        await asyncio.sleep(0.01)
        return [{"public": "info", "custom_secret": "hide_this"}]

    result = await async_fetch()

    assert result[0]["public"] == "info"
    assert result[0]["custom_secret"] == "[HIDDEN]"
