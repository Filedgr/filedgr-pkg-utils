import time
import asyncio
import pytest
from filedgr_pkg_utils.caching.memoize import ttl_cache

def test_sync_ttl_cache():
    call_count = 0

    @ttl_cache(maxsize=10, ttl_seconds=1)
    def calculate(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert calculate(5) == 10
    assert calculate(5) == 10
    assert call_count == 1  # Hit cache

    time.sleep(1.1) # Wait for TTL to expire
    assert calculate(5) == 10
    assert call_count == 2  # Re-ran function

@pytest.mark.asyncio
async def test_async_ttl_cache():
    call_count = 0

    @ttl_cache(maxsize=10, ttl_seconds=1)
    async def acalculate(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert await acalculate(5) == 10
    assert await acalculate(5) == 10
    assert call_count == 1
