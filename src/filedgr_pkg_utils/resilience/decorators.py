import time
import asyncio
import inspect
import threading
from collections import deque
from functools import wraps
from typing import Callable, Deque, Tuple, Type
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


def retry(
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retries a function with exponential backoff on specific exceptions."""

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                attempts = 0
                current_backoff = backoff_seconds
                while attempts < max_attempts:
                    attempts += 1
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        if attempts == max_attempts:
                            raise e
                        await asyncio.sleep(current_backoff)
                        current_backoff *= backoff_multiplier

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                attempts = 0
                current_backoff = backoff_seconds
                while attempts < max_attempts:
                    attempts += 1
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempts == max_attempts:
                            raise e
                        time.sleep(current_backoff)
                        current_backoff *= backoff_multiplier

            return sync_wrapper

    return decorator


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a call is rejected because the circuit breaker is open."""


class RateLimitExceededError(PermissionError):
    """Raised when a call is rejected by ``rate_limit``."""


def circuit_breaker(failure_threshold: int = 5, recovery_timeout_seconds: float = 30.0):
    """
    Trips after N consecutive failures, rejecting calls with ``CircuitBreakerOpenError``
    until ``recovery_timeout_seconds`` have passed.

    After the timeout the breaker is HALF_OPEN and lets exactly one trial call
    through (other callers are still rejected). If it succeeds the breaker closes;
    if it fails the breaker opens again for another full timeout.

    State is shared by all callers of the decorated function and is thread-safe.
    """

    def decorator(func: Callable) -> Callable:
        lock = threading.Lock()
        state = {"failures": 0, "opened_at": 0.0, "state": "CLOSED", "probe_in_flight": False}

        def before_call() -> None:
            with lock:
                if state["state"] == "OPEN":
                    if time.monotonic() - state["opened_at"] < recovery_timeout_seconds:
                        raise CircuitBreakerOpenError("Circuit Breaker is OPEN.")
                    state["state"] = "HALF_OPEN"
                if state["state"] == "HALF_OPEN":
                    if state["probe_in_flight"]:
                        raise CircuitBreakerOpenError("Circuit Breaker is OPEN (trial call in progress).")
                    state["probe_in_flight"] = True

        def on_success() -> None:
            with lock:
                state["failures"] = 0
                state["state"] = "CLOSED"
                state["probe_in_flight"] = False

        def on_failure() -> None:
            with lock:
                state["failures"] += 1
                if state["state"] == "HALF_OPEN" or state["failures"] >= failure_threshold:
                    state["state"] = "OPEN"
                    state["opened_at"] = time.monotonic()
                state["probe_in_flight"] = False

        def on_abort() -> None:
            # Cancelled / interrupted (BaseException): not a failure of the
            # dependency, but a trial slot must not stay taken forever.
            with lock:
                state["probe_in_flight"] = False

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                before_call()
                try:
                    result = await func(*args, **kwargs)
                except Exception:
                    on_failure()
                    raise
                except BaseException:
                    on_abort()
                    raise
                on_success()
                return result

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                before_call()
                try:
                    result = func(*args, **kwargs)
                except Exception:
                    on_failure()
                    raise
                except BaseException:
                    on_abort()
                    raise
                on_success()
                return result

            return sync_wrapper

    return decorator


def fallback(fallback_function: Callable):
    """Executes a fallback function if the main function raises an exception."""

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if inspect.iscoroutinefunction(fallback_function):
                        return await fallback_function(*args, **kwargs)
                    return fallback_function(*args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if inspect.iscoroutinefunction(fallback_function):
                        raise RuntimeError("Cannot use an async fallback with a sync function.")
                    return fallback_function(*args, **kwargs)

            return sync_wrapper

    return decorator


def timeout(seconds: float):
    """
    Raises ``TimeoutError`` if the call takes longer than `seconds`.

    Async functions are cancelled. Sync functions run in a worker thread that
    cannot be stopped: the caller gets the error on time, but the function
    keeps running in the background until it returns.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Not using the executor as a context manager: its __exit__ waits for
                # the worker thread, which would block until func finishes anyway.
                # Python threads cannot be killed, so on timeout the call keeps
                # running in the background; the caller just stops waiting for it.
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except FuturesTimeoutError:
                    raise TimeoutError(f"Function timed out after {seconds}s") from None
                finally:
                    executor.shutdown(wait=False)

            return sync_wrapper

    return decorator


def rate_limit(calls: int = 5, period_seconds: float = 1.0):
    """
    Allows at most ``calls`` calls per sliding window of ``period_seconds``;
    further calls raise ``RateLimitExceededError`` (a ``PermissionError``).
    The limit is shared by all callers of the decorated function and is thread-safe.
    """

    def decorator(func: Callable) -> Callable:
        timestamps: Deque[float] = deque()
        lock = threading.Lock()

        def check_rate_limit():
            with lock:
                now = time.monotonic()
                # Remove timestamps older than the period
                while timestamps and now - timestamps[0] >= period_seconds:
                    timestamps.popleft()
                if len(timestamps) >= calls:
                    raise RateLimitExceededError("Rate limit exceeded")
                timestamps.append(now)

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                check_rate_limit()
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                check_rate_limit()
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator
