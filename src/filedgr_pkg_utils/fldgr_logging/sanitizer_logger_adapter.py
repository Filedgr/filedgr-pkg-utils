import logging
from typing import Any, MutableMapping, Tuple
from filedgr_pkg_utils.security.sanitizer import sanitize_data


class SanitizerLoggerAdapter(logging.LoggerAdapter):
    """
    A LoggerAdapter that automatically intercepts the 'extra' dictionary
    and sanitizes any PII or sensitive keys before the log is formatted and emitted.
    """

    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> Tuple[Any, MutableMapping[str, Any]]:
        # Check if the developer passed an 'extra' dictionary
        if 'extra' in kwargs and isinstance(kwargs['extra'], dict):
            # Run the entire 'extra' dictionary through our PII sanitizer
            kwargs['extra'] = sanitize_data(kwargs['extra'])

        # You could also sanitize the main message here if it happens to be a dictionary!
        if isinstance(msg, dict):
            msg = sanitize_data(msg)

        return msg, kwargs
