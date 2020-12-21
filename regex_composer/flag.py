from functools import reduce
from operator import or_
import re
import typing

if typing.TYPE_CHECKING:
    from regex_composer.expression import Pattern


class FlagSet:
    def __init__(self, pattern: 'Pattern' = None):
        self._options = set()
        self._pattern = pattern

    @classmethod
    def copy(cls, pattern: 'Pattern' = None):
        new = cls(pattern=pattern)
        if pattern is not None:
            new._options.update(pattern.flags.options)
        return new

    @property
    def options(self):
        return self._options

    @property
    def pattern(self):
        return self._pattern

    def _add_option(self, flag):
        self.options.add(flag)
        return self.pattern or self

    def _remove_option(self, flag):
        self.options.remove(flag)
        return self.pattern or self

    def _update_option(self, flag, enabled):
        if enabled:
            return self._add_option(flag)
        else:
            return self._remove_option(flag)

    def case_insensitive(self, enabled=True):
        return self._update_option(re.IGNORECASE, enabled=enabled)

    def ascii_only(self, enabled=True):
        return self._update_option(re.ASCII, enabled=enabled)

    def multiline(self, enabled=True):
        return self._update_option(re.MULTILINE, enabled=enabled)

    def dot_matches_newline(self, enabled=True):
        return self._update_option(re.DOTALL, enabled=enabled)

    def compile(self):
        if self._options:
            return reduce(or_, self._options, 0)
        return 0

    def __eq__(self, other):
        if self.pattern is None:
            pattern_equal = other.pattern is None
        else:
            pattern_equal = self.pattern == other.pattern
        return pattern_equal and self.equals(other)

    def equals(self, other):
        return self.options == other.options

    def __str__(self):
        if self._options:
            return repr(self.options)
        else:
            return ''

    def __repr__(self):
        return f'{self.__class__.__name__}: {repr(self.options)}'
