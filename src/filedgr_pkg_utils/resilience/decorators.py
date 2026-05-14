import time
import asyncio
import inspect
from functools import wraps
from typing import Callable, Tuple, Type, Any, Optional
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


def circuit_breaker(failure_threshold: int = 5, recovery_timeout_seconds: float = 30.0):
    """Trips after N failures, preventing execution until recovery timeout passes."""

    def decorator(func: Callable) -> Callable:
        # Closure state
        state = {"failures": 0, "last_failure_time": 0.0, "state": "CLOSED"}

        def check_circuit():
            if state["state"] == "OPEN":
                if time.time() - state["last_failure_time"] > recovery_timeout_seconds:
                    state["state"] = "HALF_OPEN"
                else:
                    raise RuntimeError("Circuit Breaker is OPEN.")

        def handle_success():
            state["failures"] = 0
            state["state"] = "CLOSED"

        def handle_failure():
            state["failures"] += 1
            state["last_failure_time"] = time.time()
            if state["failures"] >= failure_threshold:
                state["state"] = "OPEN"

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                check_circuit()
                try:
                    result = await func(*args, **kwargs)
                    handle_success()
                    return result
                except Exception as e:
                    handle_failure()
                    raise e

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                check_circuit()
                try:
                    result = func(*args, **kwargs)
                    handle_success()
                    return result
                except Exception as e:
                    handle_failure()
                    raise e

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
    """Cancels the execution if it takes longer than `seconds`."""

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        return future.result(timeout=seconds)
                    except FuturesTimeoutError:
                        raise TimeoutError(f"Function timed out after {seconds}s")

            return sync_wrapper

    return decorator


def rate_limit(calls: int = 5, period_seconds: float = 1.0):
    """Limits the amount of times a function can be called in a given period."""

    def decorator(func: Callable) -> Callable:
        timestamps = []

        def check_rate_limit():
            now = time.time()
            # Remove timestamps older than the period
            timestamps[:] = [t for t in timestamps if now - t < period_seconds]
            if len(timestamps) >= calls:
                raise PermissionError("Rate limit exceeded")
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
