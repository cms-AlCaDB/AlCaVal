"""
Module that contains caching classes
"""

import time


class TimeoutCache():
    """
    Simplest time based cache
    """
    def __init__(self, timeout=300):
        self.default_timeout = timeout
        self.values = {}

    def set(self, key, value, custom_timeout=None):
        """
        Add value to cache
        """
        self.values[key] = {'time': time.time(),
                            'timeout': custom_timeout or self.default_timeout,
                            'value': value}

    def get(self, key, default=None):
        """
        Get value from cache
        Returns None if value does not exist or expired
        """
        value = self.values.get(key, None)
        if value is None:
            return default

        if time.time() > value['time'] + value['timeout']:
            self.values.pop(key)
            return default

        return value['value']