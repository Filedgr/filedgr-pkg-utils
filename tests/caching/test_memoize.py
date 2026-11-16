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


def test_ttl_cache_evicts_least_recently_used():
    calls = []

    @ttl_cache(maxsize=2, ttl_seconds=60)
    def f(x):
        calls.append(x)
        return x

    f(1)
    f(2)
    f(1)  # 1 is now the most recently used
    f(3)  # must evict 2, not 1
    calls.clear()
    f(1)
    f(2)
    assert calls == [2]


def test_ttl_cache_expired_entries_are_removed():
    @ttl_cache(maxsize=10, ttl_seconds=0.05)
    def f(x):
        return x

    f(1)
    f(2)
    assert f.cache_len() == 2
    time.sleep(0.06)
    f(3)  # storing a new result sweeps out the expired 1 and 2
    assert f.cache_len() == 1


def test_ttl_cache_full_cache_drops_expired_before_live():
    calls = []

    @ttl_cache(maxsize=2, ttl_seconds=0.05)
    def f(x):
        calls.append(x)
        return x

    f(1)
    time.sleep(0.06)
    f(2)
    f(3)  # cache full: expired 1 goes, live 2 stays
    calls.clear()
    f(2)
    assert calls == []
    assert f.cache_len() == 2


def test_ttl_cache_unhashable_args_are_not_cached():
    calls = 0

    @ttl_cache()
    def f(data):
        nonlocal calls
        calls += 1
        return len(data)

    assert f({"a": 1}) == 1
    assert f({"a": 1}) == 1
    assert f([1, 2]) == 2
    assert calls == 3
    assert f.cache_len() == 0


def test_ttl_cache_args_and_kwargs_are_distinct_keys():
    @ttl_cache()
    def f(*args, **kwargs):
        return (args, kwargs)

    assert f(("a", 1)) == ((("a", 1),), {})
    assert f(a=1) == ((), {"a": 1})
    assert f.cache_len() == 2


def test_ttl_cache_maxsize_zero_disables_caching():
    calls = 0

    @ttl_cache(maxsize=0)
    def f(x):
        nonlocal calls
        calls += 1
        return x

    f(1)
    f(1)
    assert calls == 2


def test_ttl_cache_clear():
    @ttl_cache()
    def f(x):
        return x

    f(1)
    f.cache_clear()
    assert f.cache_len() == 0


def test_ttl_cache_is_thread_safe():
    import random
    import sys
    import threading

    @ttl_cache(maxsize=4, ttl_seconds=60)
    def f(x):
        return x * 2

    errors = []

    def worker():
        try:
            for _ in range(2000):
                x = random.randint(0, 1000)
                assert f(x) == x * 2
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    # Force very frequent thread switches so races show up reliably
    # (the previous implementation failed with "dictionary changed size during iteration").
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(old_interval)

    assert errors == []
    assert f.cache_len() <= 4


@pytest.mark.asyncio
async def test_async_ttl_cache_unhashable_args():
    @ttl_cache()
    async def f(data):
        return sorted(data)

    assert await f([3, 1]) == [1, 3]
    assert f.cache_len() == 0
