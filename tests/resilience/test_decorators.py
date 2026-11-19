import time
import asyncio
import pytest
from filedgr_pkg_utils.resilience.decorators import (
    retry, circuit_breaker, fallback, timeout, rate_limit
)


@pytest.mark.asyncio
async def test_async_retry():
    attempts = 0

    @retry(max_attempts=3, backoff_seconds=0.01)
    async def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Failed")
        return "Success"

    result = await flaky_func()
    assert result == "Success"
    assert attempts == 3


def test_sync_circuit_breaker():
    @circuit_breaker(failure_threshold=2, recovery_timeout_seconds=0.1)
    def failing_api():
        raise ValueError("API Down")

    with pytest.raises(ValueError):
        failing_api()
    with pytest.raises(ValueError):
        failing_api()

    # 3rd time should hit the open circuit
    with pytest.raises(RuntimeError, match="Circuit Breaker is OPEN"):
        failing_api()

    time.sleep(0.15)  # Wait for recovery
    # Should be half-open now and allow a call, which will raise the original ValueError again
    with pytest.raises(ValueError):
        failing_api()


@pytest.mark.asyncio
async def test_async_fallback():
    async def default_value():
        return 42

    @fallback(fallback_function=default_value)
    async def failing_query():
        raise ConnectionError()

    result = await failing_query()
    assert result == 42


@pytest.mark.asyncio
async def test_async_timeout():
    @timeout(seconds=0.1)
    async def slow_func():
        await asyncio.sleep(0.5)
        return "Done"

    with pytest.raises(asyncio.TimeoutError):
        await slow_func()


def test_sync_timeout():
    @timeout(seconds=0.1)
    def slow_func():
        time.sleep(0.5)
        return "Done"

    start = time.perf_counter()
    with pytest.raises(TimeoutError):
        slow_func()
    # Must return at the deadline, not when the worker thread finishes
    assert time.perf_counter() - start < 0.4


def test_rate_limit():
    @rate_limit(calls=2, period_seconds=0.5)
    def api_call():
        return True

    assert api_call() is True
    assert api_call() is True

    # 3rd call in the same window should fail
    with pytest.raises(PermissionError, match="Rate limit exceeded"):
        api_call()

    time.sleep(0.51)
    # Allowed again
    assert api_call() is True


# --- circuit_breaker: half-open, exceptions, thread safety ---

import threading

from filedgr_pkg_utils.resilience import CircuitBreakerOpenError, RateLimitExceededError


def test_circuit_breaker_open_error_is_backwards_compatible():
    assert issubclass(CircuitBreakerOpenError, RuntimeError)
    assert issubclass(RateLimitExceededError, PermissionError)


def test_circuit_breaker_half_open_success_closes():
    fail = True

    @circuit_breaker(failure_threshold=1, recovery_timeout_seconds=0.05)
    def api():
        if fail:
            raise ValueError("down")
        return "ok"

    with pytest.raises(ValueError):
        api()
    with pytest.raises(CircuitBreakerOpenError):
        api()

    time.sleep(0.06)
    fail = False
    assert api() == "ok"  # trial call succeeds -> CLOSED
    assert api() == "ok"


def test_circuit_breaker_half_open_failure_reopens_immediately():
    @circuit_breaker(failure_threshold=3, recovery_timeout_seconds=0.05)
    def api():
        raise ValueError("down")

    for _ in range(3):
        with pytest.raises(ValueError):
            api()
    time.sleep(0.06)
    with pytest.raises(ValueError):
        api()  # trial call fails
    with pytest.raises(CircuitBreakerOpenError):
        api()  # open again right away, for a full timeout


def test_circuit_breaker_half_open_allows_single_trial_call():
    release = threading.Event()
    started = threading.Event()
    should_fail = True

    @circuit_breaker(failure_threshold=1, recovery_timeout_seconds=0.05)
    def api():
        if should_fail:
            raise ValueError("down")
        started.set()
        release.wait(timeout=2)
        return "ok"

    with pytest.raises(ValueError):
        api()
    time.sleep(0.06)
    should_fail = False

    results = []
    trial = threading.Thread(target=lambda: results.append(api()))
    trial.start()
    assert started.wait(timeout=1)

    # While the trial call is running, everyone else is rejected
    with pytest.raises(CircuitBreakerOpenError):
        api()

    release.set()
    trial.join()
    assert results == ["ok"]
    assert api() == "ok"


@pytest.mark.asyncio
async def test_circuit_breaker_cancelled_trial_frees_the_slot():
    @circuit_breaker(failure_threshold=1, recovery_timeout_seconds=0.05)
    async def api(fail=False, hang=False):
        if fail:
            raise ValueError("down")
        if hang:
            await asyncio.sleep(10)
        return "ok"

    with pytest.raises(ValueError):
        await api(fail=True)
    await asyncio.sleep(0.06)

    task = asyncio.create_task(api(hang=True))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert await api() == "ok"  # a new trial call is allowed


def test_circuit_breaker_counts_failures_across_threads():
    @circuit_breaker(failure_threshold=50, recovery_timeout_seconds=60)
    def api():
        raise ValueError("down")

    def worker():
        for _ in range(10):
            try:
                api()
            except (ValueError, CircuitBreakerOpenError):
                pass

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with pytest.raises(CircuitBreakerOpenError):
        api()


def test_rate_limit_is_exact_under_concurrency():
    @rate_limit(calls=10, period_seconds=60)
    def api():
        return True

    allowed = []
    rejected = []
    barrier = threading.Barrier(50)

    def worker():
        barrier.wait()
        try:
            allowed.append(api())
        except RateLimitExceededError:
            rejected.append(1)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(allowed) == 10
    assert len(rejected) == 40
