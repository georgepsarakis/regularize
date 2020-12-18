from functools import lru_cache
from typing import Union
import re

from regex_composer.expression import Pattern


class Finder:
    def __init__(self, pattern: Union[Pattern, re.Pattern]):
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

    # TODO: configurable cache size
    @classmethod
    @lru_cache(maxsize=1_000)
    def _match(cls, regex, string):
        return regex.match(string)

    @classmethod
    def cache_clear(cls):
        return cls._match.cache_clear()


finder = Finder
