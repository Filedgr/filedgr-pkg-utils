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


# --- concurrent misses share one call ---

import threading


def _run_threads(target, n):
    barrier = threading.Barrier(n)
    results, errors = [], []

    def worker():
        barrier.wait()
        try:
            results.append(target())
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, errors


def test_sync_concurrent_misses_run_function_once():
    calls = 0

    @ttl_cache()
    def slow(x):
        nonlocal calls
        calls += 1
        time.sleep(0.1)
        return object()  # unique per call, so we can tell results apart

    results, errors = _run_threads(lambda: slow(1), 10)
    assert errors == []
    assert calls == 1
    assert len(results) == 10 and all(r is results[0] for r in results)


def test_sync_concurrent_misses_share_the_exception_and_do_not_cache_it():
    calls = 0

    @ttl_cache()
    def failing(x):
        nonlocal calls
        calls += 1
        time.sleep(0.1)
        raise ValueError("boom")

    results, errors = _run_threads(lambda: failing(1), 8)
    assert results == []
    assert len(errors) == 8 and all(isinstance(e, ValueError) for e in errors)
    assert calls == 1

    with pytest.raises(ValueError):
        failing(1)  # not cached: runs again
    assert calls == 2


def test_sync_different_keys_still_run_in_parallel():
    @ttl_cache()
    def slow(x):
        time.sleep(0.2)
        return x

    start = time.perf_counter()
    counter = iter(range(5))
    lock = threading.Lock()

    def call_next():
        with lock:
            x = next(counter)
        return slow(x)

    results, errors = _run_threads(call_next, 5)
    assert errors == [] and sorted(results) == [0, 1, 2, 3, 4]
    assert time.perf_counter() - start < 0.6


class _Interrupt(BaseException):
    pass


def test_sync_interrupted_leader_lets_a_waiter_take_over():
    calls = 0
    leader_started = threading.Event()

    @ttl_cache()
    def f(x):
        nonlocal calls
        calls += 1
        if calls == 1:
            leader_started.set()
            time.sleep(0.1)
            raise _Interrupt()
        return "value"

    out = {}

    def leader():
        try:
            f(1)
        except _Interrupt:
            out["leader"] = "interrupted"

    def waiter():
        out["waiter"] = f(1)

    t1 = threading.Thread(target=leader)
    t1.start()
    assert leader_started.wait(timeout=1)
    t2 = threading.Thread(target=waiter)
    t2.start()
    t1.join()
    t2.join()

    assert out == {"leader": "interrupted", "waiter": "value"}
    assert calls == 2


@pytest.mark.asyncio
async def test_async_concurrent_misses_run_function_once():
    calls = 0

    @ttl_cache()
    async def slow(x):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return object()

    results = await asyncio.gather(*(slow(1) for _ in range(10)))
    assert calls == 1
    assert all(r is results[0] for r in results)


@pytest.mark.asyncio
async def test_async_concurrent_misses_share_the_exception():
    calls = 0

    @ttl_cache()
    async def failing(x):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        raise ValueError("boom")

    results = await asyncio.gather(*(failing(1) for _ in range(5)), return_exceptions=True)
    assert calls == 1
    assert all(isinstance(r, ValueError) for r in results)

    with pytest.raises(ValueError):
        await failing(1)
    assert calls == 2


@pytest.mark.asyncio
async def test_async_cancelled_leader_lets_a_waiter_take_over():
    calls = 0

    @ttl_cache()
    async def f(x):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.1)
        return "value"

    leader = asyncio.create_task(f(1))
    await asyncio.sleep(0.01)
    waiter = asyncio.create_task(f(1))
    await asyncio.sleep(0.01)
    leader.cancel()

    assert await waiter == "value"
    with pytest.raises(asyncio.CancelledError):
        await leader
    assert calls == 2


@pytest.mark.asyncio
async def test_async_cancelled_waiter_does_not_cancel_the_shared_call():
    calls = 0

    @ttl_cache()
    async def f(x):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "value"

    leader = asyncio.create_task(f(1))
    await asyncio.sleep(0.01)
    waiter = asyncio.create_task(f(1))
    await asyncio.sleep(0.01)
    waiter.cancel()

    assert await leader == "value"
    assert calls == 1
    assert await f(1) == "value"  # cached


@pytest.mark.asyncio
async def test_async_error_without_waiters_is_not_reported_as_unretrieved():
    import gc

    unretrieved = []
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, ctx: unretrieved.append(ctx))
    try:
        @ttl_cache()
        async def failing(x):
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await failing(1)
        gc.collect()
        await asyncio.sleep(0)
    finally:
        loop.set_exception_handler(previous_handler)

    assert unretrieved == []
