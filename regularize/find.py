from functools import wraps
from typing import Union
import re
import typing


if typing.TYPE_CHECKING:
    from regularize.expression import Pattern


class Cache:
    NOT_FOUND = object()
    DEFAULT_MAXIMUM_SIZE = 1_000

    def __init__(self, maxsize=DEFAULT_MAXIMUM_SIZE):
        self._cache = dict()
        self._maxsize = maxsize
        self._reset_stats()

    def _increment_metric(self, name):
        self._stats[name] += 1

    def _reset_stats(self):
        self._stats = {
            'maxsize_reached': 0,
            'hits': 0,
            'misses': 0
        }

    @property
    def stats(self):
        return self._stats.copy()

    @property
    def cache(self):
        return self._cache.copy()

    @property
    def current_size(self):
        return len(self._cache)

    def clear(self):
        self._reset_stats()
        self._cache.clear()

    def get(self, key):
        if key in self._cache:
            entry = self._cache[key]
        else:
            entry = self.NOT_FOUND
            self._increment_metric('misses')

        if entry is not self.NOT_FOUND:
            self._increment_metric('hits')
            # Emulate LRU by utilizing LIFO order in dictionaries.
            # Note that this has performance impact, but does not
            # require maintaining extra statistics or structures.
            del self._cache[key]
            self.add(key, entry)

        return entry, entry is not self.NOT_FOUND

    def add(self, key, entry):
        self._cache.setdefault(key, entry)
        if len(self._cache) > self._maxsize:
            self._increment_metric('maxsize_reached')
            # Remove the first key which should be the least recently
            # accessed. See .get for details.
            remove_key = next(iter(self._cache.keys()))
            del self._cache[remove_key]


def enable_dict_cache(maxsize):
    cache = Cache(maxsize=maxsize)

    def cached(func):
        @wraps(func)
        def cached_wrapper(cls, pattern, string):
            key = (pattern, string)
            entry, found = cache.get(key)
            if found:
                return entry
            entry = func(cls, pattern, string)
            cache.add(key, entry)
            return entry
        cached_wrapper._cache = cache
        return cached_wrapper
    return cached


class Finder:
    def __init__(self, pattern: Union['Pattern', re.Pattern]):
        self._pattern = pattern
        self._compiled_pattern = None
        self._is_builtin_pattern = isinstance(pattern, re.Pattern)

    @property
    def pattern(self):
        return self._pattern

    @property
    def compiled_pattern(self):
        if self._is_builtin_pattern:
            return self.pattern

        if self._compiled_pattern is None:
            self._compiled_pattern = self.pattern.compile()

        return self._compiled_pattern

    def match(self, string):
        return self.__class__._match(self.compiled_pattern, string)

    def find(self, string, iterator=True):
        if iterator:
            return self.compiled_pattern.finditer(string)
        else:
            return self.compiled_pattern.findall(string)

    @classmethod
    @enable_dict_cache(maxsize=1_000)
    def _match(cls, regex, string):
        return regex.match(string)

    @classmethod
    def cache_clear(cls):
        return cls._match._cache.clear()


finder = Finder
