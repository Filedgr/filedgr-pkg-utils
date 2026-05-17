import inspect
import time
import asyncio
import threading
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type


def post_action(
        callback: Callable[..., Any],
        condition: Optional[Callable[..., bool]] = None
):
    """
    Executes a callback action after the decorated function returns.
    Seamlessly supports both synchronous and asynchronous functions.

    :param callback: The function to execute after the main function. (Can be sync or async)
    :param condition: An optional synchronous function that evaluates the result and inputs.
    """

    def decorator(func: Callable) -> Callable:

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Await the actual result of the coroutine
                result = await func(*args, **kwargs)

                if condition is None or condition(result, *args, **kwargs):
                    if inspect.iscoroutinefunction(callback):
                        await callback(result, *args, **kwargs)
                    else:
                        # Plain callable: could be sync, or a sync wrapper (e.g., lambda)
                        # that returns a coroutine. If we get a coroutine back, await it
                        # so async side effects actually run.
                        maybe_coro = callback(result, *args, **kwargs)
                        if inspect.iscoroutine(maybe_coro):
                            await maybe_coro

                return result

            return async_wrapper

        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)

                if condition is None or condition(result, *args, **kwargs):
                    if inspect.iscoroutinefunction(callback):
                        raise RuntimeError("Cannot use an async callback with a synchronous function.")
                    callback(result, *args, **kwargs)

                return result

            return sync_wrapper

    return decorator


def pre_action(callback: Callable[..., Any]):
    """
    Executes a callback action before the decorated function runs.
    The callback receives the exact *args and **kwargs the main function will receive.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if inspect.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if inspect.iscoroutinefunction(callback):
                    raise RuntimeError("Cannot use an async callback with a sync function.")
                callback(*args, **kwargs)
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def on_failure(callback: Callable[..., Any], exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    Executes a callback if the main function raises specific exceptions.
    The callback receives (exception_instance, *args, **kwargs).
    The exception is re-raised after the callback finishes.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if inspect.iscoroutinefunction(callback):
                        await callback(e, *args, **kwargs)
                    else:
                        callback(e, *args, **kwargs)
                    raise e

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if inspect.iscoroutinefunction(callback):
                        raise RuntimeError("Cannot use an async callback with a sync function.")
                    callback(e, *args, **kwargs)
                    raise e

            return sync_wrapper

    return decorator


def measure_time(callback: Callable[..., Any]):
    """
    Measures the execution time of the main function in milliseconds.
    The callback receives (execution_time_ms, result, *args, **kwargs).
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000

                if inspect.iscoroutinefunction(callback):
                    await callback(duration_ms, result, *args, **kwargs)
                else:
                    callback(duration_ms, result, *args, **kwargs)
                return result

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000

                if inspect.iscoroutinefunction(callback):
                    raise RuntimeError("Cannot use an async callback with a sync function.")
                callback(duration_ms, result, *args, **kwargs)
                return result

            return sync_wrapper

    return decorator


def fire_and_forget(func: Callable) -> Callable:
    """
    Runs the function in the background.
    Returns None immediately, unblocking the caller.
    """
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Schedules the coroutine to run on the event loop
            asyncio.create_task(func(*args, **kwargs))
            return None

        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Spawns a background thread for the sync function
            t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
            t.start()
            return None

        return sync_wrapper


def transform_input(transformer: Callable[..., Tuple[Tuple, dict]]):
    """
    Modifies the inputs before they reach the main function.
    The transformer must return (new_args_tuple, new_kwargs_dict).
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if inspect.iscoroutinefunction(transformer):
                    new_args, new_kwargs = await transformer(*args, **kwargs)
                else:
                    new_args, new_kwargs = transformer(*args, **kwargs)
                return await func(*new_args, **new_kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if inspect.iscoroutinefunction(transformer):
                    raise RuntimeError("Cannot use an async transformer with a sync function.")
                new_args, new_kwargs = transformer(*args, **kwargs)
                return func(*new_args, **new_kwargs)

            return sync_wrapper

    return decorator


def transform_output(transformer: Callable[..., Any]):
    """
    Modifies the return value of the main function.
    The transformer receives (original_result, *args, **kwargs) and returns the new result.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                if inspect.iscoroutinefunction(transformer):
                    return await transformer(result, *args, **kwargs)
                return transformer(result, *args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if inspect.iscoroutinefunction(transformer):
                    raise RuntimeError("Cannot use an async transformer with a sync function.")
                return transformer(result, *args, **kwargs)

            return sync_wrapper

    return decorator
