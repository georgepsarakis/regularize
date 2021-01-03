from collections import deque
from functools import partialmethod
import math
import re

from regex_composer.exceptions import SampleNotMatchedError, \
    InvalidRangeError
from regex_composer.flag import FlagSet


class Metacharacter:
    def __copy__(self):
        return self.__class__()

    def __repr__(self):
        return f'\'{self.__class__.__name__} -> {str(self)}\''


class OpeningBracket(Metacharacter):
    def __str__(self):
        return '['


class ClosingBracket(Metacharacter):
    def __str__(self):
        return ']'


class Expression:
    def __init__(self, parent: 'Expression' = None):
        self._token_stack = deque()
        self._bracket_stack = []
        if parent:
            self._copy_state(parent)

    def _copy_state(self, other, clear=True):
        if clear:
            self.bracket_stack.clear()
            self.token_stack.clear()
        self.bracket_stack.extend(other.bracket_stack)
        self.token_stack.extend(other.token_stack)

    @property
    def token_stack(self) -> deque:
        return self._token_stack

    @property
    def bracket_stack(self) -> list:
        return self._bracket_stack

    def has_open_bracket(self):
        if not self.bracket_stack:
            return False
        return isinstance(self.bracket_stack[-1], OpeningBracket)

    def close_bracket(self):
        if not self.has_open_bracket():
            return self

        if self.bracket_stack:
            last_item_in_stack = self.bracket_stack[-1]
        else:
            last_item_in_stack = None

        if not isinstance(last_item_in_stack, OpeningBracket):
            raise RuntimeError('Cannot close bracket without opening')

        return self.clone_with_updates(append=ClosingBracket())

    def _prepare_for_build(self):
        return self.close_bracket()

    def build(self):
        return ''.join(map(str, self._prepare_for_build().token_stack))

    def __repr__(self):
        return f"{self.__class__.__name__}<{hex(id(self))}>[{self.token_stack}]"

    def __str__(self):
        return f'Expression: /{self.build()}/'

    def __add__(self, other):
        new = self.__class__(parent=self)
        new._copy_state(other, clear=False)
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
        clone.token_stack.extendleft(reversed(prepend or []))
        clone.token_stack.extend(append or [])

        if append:
            for item in append:
                if isinstance(item, ClosingBracket):
                    if clone.has_open_bracket():
                        clone.bracket_stack.pop()
                elif isinstance(item, OpeningBracket):
                    clone.bracket_stack.append(item)

        return clone


class Pattern(Expression):
    def __init__(self, *args, **kwargs):
        self._extensions = None
        self._flags = None
        super(Pattern, self).__init__(*args, **kwargs)

    def _copy_state(self, other, clear=True):
        super(Pattern, self)._copy_state(other, clear=clear)
        self._extensions = other.extensions.clone()

    def __eq__(self, other):
        return self.flags.equals(other.flags) and \
               self.token_stack == other.token_stack

    @property
    def flags(self):
        if self._flags is None:
            self._flags = FlagSet(pattern=self)
        return self._flags

    def _on_after_clone(self, new):
        new._flags = FlagSet.copy(pattern=new)

    def group(self, name=None, optional=False):
        # TODO: all open ranges should be closed before applying group
        if name is None:
            return Group(self)(optional=optional)
        else:
            return NamedGroup(self)(name, optional=optional)

    def whitespace(self, match=True) -> 'Pattern':
        return Whitespace(self)(match)

    def lowercase_ascii_letters(self, **kwargs):
        return AsciiLetterCharacter(self)(lowercase=True, **kwargs)
    # Alias due to high frequency use (along with case-insensitive flag)
    ascii_letters = lowercase_ascii_letters

    def uppercase_ascii_letters(self, **kwargs) -> 'Pattern':
        return AsciiLetterCharacter(self)(lowercase=False, **kwargs)

    def any_number_between(self, **kwargs):
        return Number(self)(**kwargs)
    any_number = any_number_between

    def quantify(self, minimum=0, maximum=math.inf):
        addition = None
        if minimum == 0 and math.isinf(maximum):
            addition = '*'
        elif minimum == 1 and math.isinf(maximum):
            addition = '+'
        elif minimum == maximum:
            addition = f'{{{minimum}}}'
        elif minimum > 1 and math.isinf(maximum):
            addition = f'{{{minimum},}}'
        elif not math.isinf(maximum):
            addition = f'{{{minimum},{maximum}}}'
        return self.close_bracket().clone_with_updates(append=addition)

    def wildcard(self, one_or_more=False):
        if one_or_more:
            add = '.+'
        else:
            add = '.'
        return self.clone_with_updates(add)
    match_all = partialmethod(wildcard, one_or_more=True)

    def literal(self, string):
        return Literal(self)(string)

    def any_of(self, *members):
        clone = self.clone_with_updates(append=OpeningBracket())
        if members:
            expression = ''.join(
                map(
                    str,
                    map(BracketExpressionPartial.ensure, members)
                )
            )
            clone = clone.clone_with_updates(expression)
        return clone

    def none_of(self, *members):
        clone = self.clone_with_updates(append=OpeningBracket())
        if members:
            expression = ''.join(
                map(
                    str,
                    map(BracketExpressionPartial.ensure, members)
                )
            )
            clone = clone.clone_with_updates(
                f"^{expression}"
            )
        return clone

    def raw(self, string):
        return self.clone_with_updates(string)

    def start_anchor(self):
        return self.clone_with_updates(append='^')

    def end_anchor(self):
        return self.clone_with_updates(append='$')

    def compile(self):
        try:
            return re.compile(self.build(), self.flags.compile())
        except re.error as e:
            print(f'Unable to build regular expression: {self}')
            raise e

    def test(self, sample):
        regex = self.compile()
        match = regex.match(sample)
        if not match:
            raise SampleNotMatchedError(f'{regex} tested with "{sample}"')
        return match

    def case_insensitive(self, enabled=True):
        return self.clone().flags.case_insensitive(enabled=enabled)

    def multiline(self, enabled=True):
        return self.clone().flags.multiline(enabled=enabled)

    def dot_matches_newline(self, enabled=True):
        return self.clone().flags.dot_matches_newline(enabled=enabled)

    def ascii_only(self, enabled=True):
        return self.clone().flags.ascii_only(enabled=enabled)

    def __str__(self):
        initial = super(Pattern, self).__str__()
        return f'{initial}{self.flags}'


class Group(Pattern):
    def __call__(self, optional) -> 'Pattern':
        append_additions = [')']
        if optional:
            append_additions.append('?')
        return self.close_bracket().clone_with_updates(
            prepend='(',
            append=append_additions
        )


class NamedGroup(Group):
    def __call__(self, name, optional) -> 'Pattern':
        append_additions = [')']
        if optional:
            append_additions.append('?')
        return self.close_bracket().clone_with_updates(
            prepend=('(', f'?P<{name}>'),
            append=append_additions
        )


class Literal(Pattern):
    def __call__(self, string):
        return self.clone_with_updates(re.escape(string))


class Whitespace(Pattern):
    def __call__(self, match):
        return self.clone_with_updates('\\s' if match else '\\S')


class Range(Pattern):
    def __call__(self, start, end, closed=False, negated=False, skip_brackets=False):
        if negated:
            start = f'^{start}'

        additions = []
        if not self.has_open_bracket() and not skip_brackets:
            additions.append(OpeningBracket())
        additions.append(f'{start}-{end}')
        if closed and not skip_brackets:
            additions.append(ClosingBracket())
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


class BracketExpressionPartial:
    def __init__(self, expression: str):
        self._expression = expression

    def __str__(self):
        return self._expression

    def __repr__(self):
        return f'{self.__class__.__name__}: {repr(self._expression)}'

    @property
    def expression(self):
        return self._expression

    @classmethod
    def ensure(cls, obj):
        if not isinstance(obj, cls):
            return cls(Literal()(obj).build())
        else:
            return obj


class ExtensionRegistry:
    def __init__(self):
        self._registrations = {}

    @property
    def registrations(self):
        return self._registrations

    def add(self, name, klass):
        self._registrations[name] = klass

    def __iter__(self):
        for registration in self._registrations.items():
            yield registration

    def __contains__(self, item):
        return item in self._registrations

    def __repr__(self):
        return repr(self._registrations)

    def clear(self):
        self._registrations.clear()


Pattern.registry = ExtensionRegistry()


class Extensions:
    _registry = Pattern.registry

    def __init__(self, pattern):
        self._pattern = pattern
        self._callbacks_initialized = False
        self._callbacks = {}

    @property
    def registry(self):
        return self.__class__._registry

    def clone(self):
        new = self.__class__(self._pattern)
        new._callbacks_initialized = False
        return new

    def _initialize_callbacks(self):
        if self._callbacks_initialized:
            return

        for name, klass in self.registry:
            self._callbacks[name] = klass(self._pattern)
        self._callbacks_initialized = True

    def __getattr__(self, item):
        if item in self.registry:
            self._initialize_callbacks()
            return self._callbacks[item]
        else:
            raise AttributeError(item)


Pattern.ANY_NUMBER = BracketExpressionPartial(Number()(skip_brackets=True).build())
Pattern.ANY_CHARACTER = BracketExpressionPartial(
    AsciiLetterCharacter()(skip_brackets=True).build()
)
Pattern.NO_WHITESPACE = BracketExpressionPartial(Whitespace()(match=False).build())
Pattern.ANY_WHITESPACE = BracketExpressionPartial(Whitespace()(match=True).build())

pattern = Pattern
