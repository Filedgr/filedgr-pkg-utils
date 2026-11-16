import asyncio
import inspect
import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Hashable, Optional, Tuple

_KWARGS_MARKER = object()

# Outcome markers for a shared (in-flight) call
_RETRY = object()  # the leading call was aborted (cancelled / interrupted): waiters try again


def _make_key(args: tuple, kwargs: dict) -> Optional[Hashable]:
    """Builds a hashable cache key, or returns None if an argument is unhashable."""
    key: Tuple = args
    if kwargs:
        key = args + (_KWARGS_MARKER,) + tuple(sorted(kwargs.items()))
    try:
        hash(key)
    except TypeError:
        return None
    return key


class _SyncCall:
    """A sync call in progress that other threads can wait on."""
    __slots__ = ("event", "result", "error")

    def __init__(self):
        self.event = threading.Event()
        self.result: Any = _RETRY
        self.error: Optional[BaseException] = None


def ttl_cache(maxsize: int = 128, ttl_seconds: float = 3600):
    """
    Thread-safe in-memory LRU cache with Time-To-Live (TTL).
    Supports both sync and async functions.

    - When full, the least recently *used* entry is evicted (expired entries go first).
    - Expired entries are removed when looked up and whenever a new result is stored.
    - Calls with unhashable arguments (dicts, lists, ...) are not cached; the
      function simply runs.
    - Concurrent misses for the same arguments are collapsed into ONE call: the
      first caller runs the function, the others (threads, or tasks on the same
      event loop) wait and receive the same result. If that call raises, all of
      them receive the same exception and nothing is cached. If it is cancelled
      or interrupted, a waiting caller takes over and runs the function itself.

    The decorated function gets ``cache_clear()`` and ``cache_len()`` helpers.
    """

    def decorator(func: Callable) -> Callable:
        cache: "OrderedDict[Hashable, Tuple[float, Any]]" = OrderedDict()
        lock = threading.Lock()

        def _get(key) -> Tuple[bool, Any]:
            """Cache lookup. Caller must hold the lock."""
            entry = cache.get(key)
            if entry is None:
                return False, None
            expiration_time, result = entry
            if time.monotonic() >= expiration_time:
                del cache[key]
                return False, None
            cache.move_to_end(key)
            return True, result

        def _put(key, result) -> None:
            """Store a result. Caller must hold the lock."""
            if maxsize <= 0:
                return
            now = time.monotonic()
            # Drop expired entries so stale results don't linger in memory.
            # Saves only happen on a miss (the function just ran), so this
            # O(maxsize) sweep is cheap by comparison.
            for k in [k for k, (exp, _) in cache.items() if exp <= now]:
                del cache[k]
            cache[key] = (now + ttl_seconds, result)
            cache.move_to_end(key)
            # Still full: evict the least recently used entries
            while len(cache) > maxsize:
                cache.popitem(last=False)

        def cache_clear() -> None:
            with lock:
                cache.clear()

        def cache_len() -> int:
            with lock:
                return len(cache)

        if inspect.iscoroutinefunction(func):
            # key -> (event loop, future) of the call currently computing that key
            in_flight: Dict[Hashable, Tuple[asyncio.AbstractEventLoop, "asyncio.Future[Any]"]] = {}

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = _make_key(args, kwargs)
                if key is None:
                    return await func(*args, **kwargs)
                loop = asyncio.get_running_loop()

                while True:
                    with lock:
                        hit, result = _get(key)
                        if hit:
                            return result
                        current = in_flight.get(key)
                        if current is None:
                            future = loop.create_future()
                            # Mark any exception as retrieved, so an error with no
                            # waiters doesn't log "exception was never retrieved".
                            future.add_done_callback(lambda f: f.cancelled() or f.exception())
                            in_flight[key] = (loop, future)
                            break  # we lead the call
                        waiting_loop, future = current

                    if waiting_loop is not loop:
                        # In flight on another event loop: can't await its future here.
                        return await func(*args, **kwargs)

                    # shield: a cancelled waiter must not cancel the shared call
                    result = await asyncio.shield(future)
                    if result is _RETRY:
                        continue
                    return result

                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    with lock:
                        in_flight.pop(key, None)
                    future.set_exception(exc)
                    raise
                except BaseException:
                    with lock:
                        in_flight.pop(key, None)
                    future.set_result(_RETRY)
                    raise

                with lock:
                    _put(key, result)
                    in_flight.pop(key, None)
                future.set_result(result)
                return result

            wrapper = async_wrapper
        else:
            sync_in_flight: Dict[Hashable, _SyncCall] = {}

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = _make_key(args, kwargs)
                if key is None:
                    return func(*args, **kwargs)

                while True:
                    with lock:
                        hit, result = _get(key)
                        if hit:
                            return result
                        call = sync_in_flight.get(key)
                        if call is None:
                            call = _SyncCall()
                            sync_in_flight[key] = call
                            break  # we lead the call

                    call.event.wait()
                    if call.error is not None:
                        raise call.error
                    if call.result is _RETRY:
                        continue
                    return call.result

                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    call.error = exc
                    raise
                except BaseException:
                    raise  # call.result stays _RETRY: a waiter takes over
                else:
                    with lock:
                        _put(key, result)
                    call.result = result
                    return result
                finally:
                    with lock:
                        sync_in_flight.pop(key, None)
                    call.event.set()

            wrapper = sync_wrapper

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        wrapper.cache_len = cache_len  # type: ignore[attr-defined]
        return wrapper

    return decorator
