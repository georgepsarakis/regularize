from functools import reduce
from operator import or_
import re


class FlagSet:
    def __init__(self):
        self._options = set()

    def copy(self):
        new = self.__class__()
        new.options.update(self.options)
        return new

    @property
    def options(self):
        return self._options

    def _add_option(self, flag):
        self.options.add(flag)

    def _remove_option(self, flag):
        self.options.remove(flag)

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
        return self.options == other.options

    def __str__(self):
        if self._options:
            return repr(self.options)
        else:
            return ''

    def __repr__(self):
        return f'{self.__class__.__name__}: {repr(self.options)}'
