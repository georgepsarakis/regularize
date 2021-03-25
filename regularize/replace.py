from functools import lru_cache
import typing

if typing.TYPE_CHECKING:
    from regularize.expression import Pattern


class Substitution:
    def __init__(self, pattern: 'Pattern'):
        self._stack = []
        self._pattern = pattern
        self._compiled_pattern = None

    @property
    def pattern(self):
        if self._compiled_pattern is None:
            self._compiled_pattern = self._pattern.compile()
        return self._compiled_pattern

    @property
    def stack(self):
        return self._stack

    def _build(self):
        return ''.join(self.stack)

    def add(self, string):
        self.stack.append(string)
        return self

    def backreference(self, name_or_number):
        self.stack.append(f'\\g<{name_or_number}>')
        return self

    @lru_cache(maxsize=1_000)
    def replace(self, string, count=0):
        return self.pattern.sub(self._build(), string, count=count)
    __call__ = replace


substitution = Substitution
