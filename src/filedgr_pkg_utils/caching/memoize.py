import time
import inspect
from functools import wraps
from typing import Callable, Any, Dict, Tuple


def ttl_cache(maxsize: int = 128, ttl_seconds: int = 3600):
    """
    LRU-style in-memory cache with Time-To-Live (TTL).
    Supports both sync and async functions.
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[Tuple, Tuple[float, Any]] = {}

        def get_cache_key(args, kwargs):
            return (args, tuple(sorted(kwargs.items())))

        def check_cache(key):
            current_time = time.time()
            if key in cache:
                expiration_time, result = cache[key]
                if current_time < expiration_time:
                    return True, result
            return False, None

        def save_cache(key, result):
            if len(cache) >= maxsize:
                oldest_key = next(iter(cache))
                del cache[oldest_key]
            cache[key] = (time.time() + ttl_seconds, result)

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = get_cache_key(args, kwargs)
                hit, result = check_cache(key)
                if hit:
                    return result
                result = await func(*args, **kwargs)
                save_cache(key, result)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = get_cache_key(args, kwargs)
                hit, result = check_cache(key)
                if hit:
                    return result
                result = func(*args, **kwargs)
                save_cache(key, result)
                return result
            return sync_wrapper
    return decorator
