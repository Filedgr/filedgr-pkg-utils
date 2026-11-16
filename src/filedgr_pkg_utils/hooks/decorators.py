import inspect
import logging
import time
import asyncio
import threading
from functools import wraps
from typing import Callable, Any, Optional, Set, Tuple, Type


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


# Strong references to in-flight background tasks. The event loop only keeps weak
# references, so without this a running task can be garbage-collected mid-execution.
_background_tasks: Set["asyncio.Task[Any]"] = set()

_logger = logging.getLogger(__name__)


def fire_and_forget(
        func: Optional[Callable] = None,
        *,
        on_error: Optional[Callable[..., Any]] = None
):
    """
    Runs the function in the background and returns None immediately.

    Usable as ``@fire_and_forget`` or ``@fire_and_forget(on_error=handler)``.

    - Async functions are scheduled as a task on the running event loop. The task
      is kept referenced until it finishes, so it cannot be garbage-collected early.
    - Sync functions run in a daemon thread. Daemon threads are killed when the
      process exits, so don't use this for work that must complete.

    Exceptions raised by the background work are never silently lost: they are
    logged with their traceback on the ``filedgr_pkg_utils.hooks.decorators``
    logger and, if given, passed to ``on_error(exception, *args, **kwargs)``.
    ``on_error`` must be a plain (sync) callable.
    """

    def _report(exc: BaseException, args: tuple, kwargs: dict, func_name: str) -> None:
        _logger.error(
            "Background task %s failed", func_name,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        if on_error is not None:
            try:
                on_error(exc, *args, **kwargs)
            except Exception:
                _logger.exception("on_error handler for background task %s failed", func_name)

    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(on_error):
            raise TypeError("fire_and_forget on_error must be a sync callable.")

        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                task = asyncio.create_task(fn(*args, **kwargs))
                _background_tasks.add(task)

                def _done(t: "asyncio.Task[Any]") -> None:
                    _background_tasks.discard(t)
                    if not t.cancelled() and t.exception() is not None:
                        _report(t.exception(), args, kwargs, fn.__qualname__)

                task.add_done_callback(_done)
                return None

            return async_wrapper
        else:
            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                def _run():
                    try:
                        fn(*args, **kwargs)
                    except Exception as exc:
                        _report(exc, args, kwargs, fn.__qualname__)

                t = threading.Thread(target=_run, daemon=True, name=f"fire_and_forget:{fn.__qualname__}")
                t.start()
                return None

            return sync_wrapper

    if func is not None:
        # Used as bare @fire_and_forget
        return decorator(func)
    return decorator


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
