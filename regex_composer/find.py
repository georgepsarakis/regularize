from functools import lru_cache

from regex_composer.expression import Pattern


class Finder:
    def __init__(self, pattern: Pattern):
        self._pattern = pattern

    @property
    def pattern(self):
        return self._pattern

    def match(self, string):
        return self.__class__._match(self.pattern.compile(), string)

    def find(self, string, iterator=True):
        regex = self.pattern.compile()
        if iterator:
            return regex.finditer(string)
        else:
            return regex.findall(string)

    # TODO: configurable cache size
    @classmethod
    @lru_cache(maxsize=1000, typed=True)
    def _match(cls, regex, string):
        return regex.match(string)

    @classmethod
    def cache_clear(cls):
        return cls._match.cache_clear()


finder = Finder
