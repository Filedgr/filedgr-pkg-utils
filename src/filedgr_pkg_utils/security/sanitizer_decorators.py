import inspect
from functools import wraps
from typing import Callable, Union, List, Set

from filedgr_pkg_utils.security.sanitizer import sanitize_data


def sanitize_return(
    sensitive_keys: Union[Set[str], List[str], None] = None,
    mask: str = "*****"
):
    """
    Decorator that sanitizes the return value of a function.
    WARNING: Use this only at system boundaries (like API endpoints)
    to prevent destroying data needed by downstream internal functions.
    """
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                return sanitize_data(result, sensitive_keys, mask)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                return sanitize_data(result, sensitive_keys, mask)
            return sync_wrapper
    return decorator
