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

    with pytest.raises(TimeoutError):
        slow_func()


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
