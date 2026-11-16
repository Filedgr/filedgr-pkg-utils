import inspect
import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Hashable, Optional, Tuple

_KWARGS_MARKER = object()


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


def ttl_cache(maxsize: int = 128, ttl_seconds: float = 3600):
    """
    Thread-safe in-memory LRU cache with Time-To-Live (TTL).
    Supports both sync and async functions.

    - When full, the least recently *used* entry is evicted (expired entries go first).
    - Expired entries are removed when looked up and whenever a new result is stored.
    - Calls with unhashable arguments (dicts, lists, ...) are not cached; the
      function simply runs.
    - The cache's own state is protected by a lock. Concurrent calls with the
      same uncached arguments may each run the function once; the last result wins.

    The decorated function gets ``cache_clear()`` and ``cache_len()`` helpers.
    """

    def decorator(func: Callable) -> Callable:
        cache: "OrderedDict[Hashable, Tuple[float, Any]]" = OrderedDict()
        lock = threading.Lock()

        def check_cache(key) -> Tuple[bool, Any]:
            with lock:
                entry = cache.get(key)
                if entry is None:
                    return False, None
                expiration_time, result = entry
                if time.monotonic() >= expiration_time:
                    del cache[key]
                    return False, None
                cache.move_to_end(key)
                return True, result

        def save_cache(key, result) -> None:
            if maxsize <= 0:
                return
            with lock:
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
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = _make_key(args, kwargs)
                if key is None:
                    return await func(*args, **kwargs)
                hit, result = check_cache(key)
                if hit:
                    return result
                result = await func(*args, **kwargs)
                save_cache(key, result)
                return result

            wrapper = async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = _make_key(args, kwargs)
                if key is None:
                    return func(*args, **kwargs)
                hit, result = check_cache(key)
                if hit:
                    return result
                result = func(*args, **kwargs)
                save_cache(key, result)
                return result

            wrapper = sync_wrapper

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        wrapper.cache_len = cache_len  # type: ignore[attr-defined]
        return wrapper

    return decorator
