from collections import deque
from functools import reduce
import math
from operator import or_
import re

from regex_composer.exceptions import SampleNotMatchedError, InvalidRangeError


class Operator:
    def __copy__(self):
        return self.__class__()

    def __repr__(self):
        return f'\'{self.__class__.__name__} -> {str(self)}\''


class OpenBracket(Operator):
    def __str__(self):
        return '['


class ClosedBracket(Operator):
    def __str__(self):
        return ']'


class Expression:
    def __init__(self, parent: 'Expression' = None):
        self._stack = deque()
        self._bracket_stack = []
        if parent:
            self._copy_stacks_from(parent)

    def _copy_stacks_from(self, other, clear=True):
        if clear:
            self.bracket_stack.clear()
            self.stack.clear()
        self.bracket_stack.extend(other.bracket_stack)
        self.stack.extend(other.stack)

    @property
    def stack(self) -> deque:
        return self._stack

    @property
    def bracket_stack(self) -> list:
        return self._bracket_stack

    def has_open_range(self):
        if not self.bracket_stack:
            return False
        return isinstance(self.bracket_stack[-1], OpenBracket)

    def end_range(self):
        if not self.has_open_range():
            return self

        if self.bracket_stack:
            last_item_in_stack = self.bracket_stack[-1]
        else:
            last_item_in_stack = None

        if not isinstance(last_item_in_stack, OpenBracket):
            raise RuntimeError('Cannot close bracket without opening')

        return self.clone_with_updates(append=ClosedBracket())

    def _prepare_for_build(self):
        return self.end_range()

    def build(self):
        return ''.join(map(str, self._prepare_for_build().stack))

    def __repr__(self):
        return f"{self.__class__.__name__}<{hex(id(self))}>[{self.stack}]"

    def __str__(self):
        return f'Expression: /{self.build()}/'

    def __add__(self, other):
        new = self.__class__(parent=self)
        new._copy_stacks_from(other, clear=False)
        return new

    def clone(self) -> 'Expression':
        new = self.__class__(parent=self)
        self._on_after_clone(new)
        return new

    def _on_after_clone(self, new):
        pass

    def clone_with_updates(self, append=None, prepend=None) -> 'Expression':
        if append is not None and not isinstance(append, (list, tuple)):
            append = (append,)

        if prepend is not None and not isinstance(prepend, (list, tuple)):
            prepend = (prepend,)

        clone = self.clone()
        clone.stack.extendleft(reversed(prepend or []))
        clone.stack.extend(append or [])

        if append:
            for item in append:
                if isinstance(item, ClosedBracket):
                    if clone.has_open_range():
                        clone.bracket_stack.pop()
                elif isinstance(item, OpenBracket):
                    clone.bracket_stack.append(item)

        return clone


class Pattern(Expression):
    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)
        self._flags = Flags(pattern=self)

    def __eq__(self, other):
        return self.flags == other.flags and \
               self.stack == other.stack

    @property
    def flags(self):
        return self._flags

    def _on_after_clone(self, new):
        new._flags = Flags.copy(pattern=new)

    def group(self, name=None):
        if name is None:
            return Group(self.end_range())()
        else:
            return NamedGroup(self.end_range())(name)

    def whitespace(self, match) -> 'Pattern':
        return Whitespace(self)(match)

    def lowercase_ascii_letters(self, **kwargs):
        return AsciiLetterCharacter(self)(lowercase=True, **kwargs)
    # Alias due to high frequency use (along with case-insensitive flag)
    ascii_letters = lowercase_ascii_letters

    def uppercase_ascii_letters(self, **kwargs) -> 'Pattern':
        return AsciiLetterCharacter(self)(lowercase=False, **kwargs)

    def any_number(self, quantification=None, **kwargs):
        if quantification is None:
            return Number(self)(**kwargs)
        else:
            return self.any_number().end_range() + quantification

    def number_range(self, minimum, maximum, quantification=None, **kwargs):
        if quantification is None:
            return Number(self)(minimum=minimum, maximum=maximum, **kwargs)
        else:
            return self.number_range(minimum, maximum).end_range() + quantification

    def quantify(self, minimum=0, maximum=math.inf):
        addition = None
        if minimum == 0 and math.isinf(maximum):
            addition = '*'
        elif minimum == 1 and math.isinf(maximum):
            addition = '+'
        elif minimum == maximum:
            addition = f'{{minimum}}'
        elif minimum > 1 and math.isinf(maximum):
            addition = f'{{{minimum},}}'
        elif not math.isinf(maximum):
            addition = f'{{{minimum},{maximum}}}'
        return self.end_range().clone_with_updates(append=addition)

    def wildcard(self):
        return self.clone_with_updates('.')

    def literal(self, string):
        return Literal(self)(string)

    def start_anchor(self):
        return self.clone_with_updates(append='^')

    def end_anchor(self):
        return self.clone_with_updates(append='$')

    def compile(self):
        return re.compile(self.build(), self.flags.compile())

    def test(self, sample):
        regex = self.compile()
        match = regex.match(sample)
        if not match:
            raise SampleNotMatchedError(f'{regex} tested with "{sample}"')
        return match

    def flag(self, **names):
        new = self.clone()
        for name, value in names.items():
            if name == 'case_insensitive':
                new = new.flags.case_insensitive()
            elif name == 'ascii_only':
                new = new.flags.ascii_only()
            elif name == 'dot_matches_newline':
                new = new.flags.dot_matches_newline()
            elif name == 'multiline':
                new = new.flags.multiline()
            else:
                raise NameError(f'Invalid flag name: {name}')
        return new

    def case_insensitive(self):
        return self.clone().flags.case_insensitive()

    def case_sensitive(self):
        return self.clone().flags.case_sensitive()

    def multiline(self, enabled=True):
        return self.clone().flags.multiline()

    def dot_matches_newline(self, enabled=True):
        return self.clone().flags.dot_matches_newline()

    def ascii_only(self, enabled=True):
        return self.clone().flags.ascii_only()

    def __str__(self):
        initial = super(Pattern, self).__str__()
        return f'{initial}{self.flags}'


class Flags:
    def __init__(self, pattern: Pattern = None):
        self._options = set()
        self._pattern = pattern

    @classmethod
    def copy(cls, pattern: Pattern = None):
        new = cls(pattern=pattern)
        if pattern is not None:
            new._options.update(pattern.flags.options)
        return new

    def clone(self):
        new = self.__class__(pattern=self.pattern)
        new._options.update(self.options)
        return new

    @property
    def options(self):
        return self._options

    @property
    def pattern(self):
        return self._pattern

    def __eq__(self, other):
        if self.pattern is None:
            pattern_equal = other.pattern is None
        else:
            pattern_equal = self.pattern == other.pattern

        options_equal = self.options == other.options

        return pattern_equal and options_equal

    def __str__(self):
        if self._options:
            return repr(self.options)
        else:
            return ''

    def __repr__(self):
        return f'Flags: {repr(self.options)}'

    def compile(self):
        if self._options:
            return reduce(or_, self._options, 0)
        return 0

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


class Group(Pattern):
    def __call__(self) -> 'Pattern':
        return self.clone_with_updates(
            prepend='(',
            append=')'
        )


class NamedGroup(Group):
    def __call__(self, name) -> 'Pattern':
        return self.clone_with_updates(
            prepend=('(', f'?P<{name}>'),
            append=')'
        )


class Literal(Pattern):
    def __call__(self, string):
        return self.clone_with_updates(re.escape(string))


class Whitespace(Pattern):
    def __call__(self, match):
        return self.clone_with_updates('\\s' if match else '\\S')


class Range(Pattern):
    def __call__(self, start, end, closed=False, negated=False):
        if negated:
            start = f'^{start}'

        additions = []
        if not self.has_open_range():
            additions.append(OpenBracket())
        additions.append(f'{start}-{end}')
        if closed:
            additions.append(ClosedBracket())
        return self.clone_with_updates(append=additions)


class AsciiLetterCharacter(Range):
    def __call__(self, lowercase=True, **kwargs):
        start = 'a' if lowercase else 'A'
        end = 'z' if lowercase else 'Z'
        return super(AsciiLetterCharacter, self).__call__(start, end, **kwargs)


class Number(Range):
    def __call__(self, minimum=0, maximum=9, **kwargs) -> Pattern:
        if minimum >= maximum or minimum < 0 or maximum > 9:
            raise InvalidRangeError(
                f'Cannot build range between {minimum} and {maximum}'
            )
        return super(Number, self).__call__(minimum, maximum, **kwargs)


pattern = Pattern


if __name__ == "__main__":
    from regex_composer.find import finder
    from regex_composer.expression import pattern

    p = pattern().literal('application.').\
        any_number().quantify(minimum=1).\
        literal('.log').\
        case_insensitive()

    print(p)
    f = finder(p)
    print(f.match('application.1.log'))
    print(f.match('application.a.log'))

    p2 = p.multiline()
    print(p2)
    print(p)
