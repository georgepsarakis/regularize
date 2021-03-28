from collections.abc import MutableMapping
from collections import deque
from functools import partialmethod
import math
import re
from functools import wraps

from regularize.exceptions import SampleNotMatchedError, \
    InvalidRangeError
from regularize.flag import FlagSet


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


class Or(Metacharacter):
    def __str__(self):
        return '|'

    def combine(self, *expressions):
        return str(self).join(expressions)


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
        return self.flags == other.flags and \
               self.token_stack == other.token_stack

    @property
    def flags(self):
        if self._flags is None:
            self._flags = FlagSet()
        return self._flags

    def _on_after_clone(self, new):
        new._flags = self.flags.copy()
        new._extensions = self.extensions.clone()

    def group(self, name=None, optional=False, wrapped=None):
        if wrapped is None:
            wrapped_pattern = self
        else:
            wrapped_pattern = wrapped

        new_group = Group(wrapped_pattern)(name=name, optional=optional)

        if wrapped is None:
            return new_group
        else:
            return self + new_group

    def match_any(self, *subexpressions, **kwargs):
        expression_list = [
            subexpression.build()
            for subexpression in map(self._ensure_pattern, subexpressions)
        ]
        new = self.__class__().raw(Or().combine(expression_list)).group(**kwargs)
        return self.clone_with_updates(new.build())

    @staticmethod
    def _ensure_pattern(obj):
        if isinstance(obj, str):
            return Literal()(obj)
        elif isinstance(obj, Pattern):
            return obj
        else:
            raise TypeError(f'Cannot handle type {obj.__class__.__name__} automatically')

    def __or__(self, other):
        return (self.clone_with_updates(append=Or()) + other).group()

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
        elif minimum == 0 and maximum == 1:
            addition = '?'
        elif minimum == 1 and math.isinf(maximum):
            addition = '+'
        elif minimum == maximum:
            addition = f'{{{minimum}}}'
        elif minimum > 1 and math.isinf(maximum):
            addition = f'{{{minimum},}}'
        elif not math.isinf(maximum):
            addition = f'{{{minimum},{maximum}}}'
        return self.close_bracket().clone_with_updates(append=addition)

    at_least_one = partialmethod(quantify, minimum=1, maximum=math.inf)

    def exactly(self, times):
        return self.quantify(minimum=times, maximum=times)

    def wildcard(self, one_or_more=False):
        if one_or_more:
            add = '.+'
        else:
            add = '.'
        return self.clone_with_updates(add)

    match_all = partialmethod(wildcard, one_or_more=True)

    def literal(self, string):
        return Literal(self)(string)

    def any_of(self, *members, close=True):
        clone = self.clone_with_updates(append=OpeningBracket())
        if members:
            expression = ''.join(
                map(
                    str,
                    map(BracketExpressionPartial.ensure, members)
                )
            )
            clone = clone.clone_with_updates(expression)
        if close:
            clone = clone.close_bracket()
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

    def case_insensitive(self, enabled=True) -> 'Pattern':
        clone = self.clone()
        clone.flags.case_insensitive(enabled=enabled)
        return clone

    def multiline(self, enabled=True):
        clone = self.clone()
        clone.flags.multiline(enabled=enabled)
        return clone

    def dot_matches_newline(self, enabled=True):
        clone = self.clone()
        clone.flags.dot_matches_newline(enabled=enabled)
        return clone

    def ascii_only(self, enabled=True):
        clone = self.clone()
        clone.flags.ascii_only(enabled=enabled)
        return clone

    def __str__(self):
        initial = super(Pattern, self).__str__()
        return f'{initial}{self.flags}'

    @property
    def ext(self) -> 'ExtensionRegistry':
        if self._extensions is None:
            self._extensions = ExtensionRegistry(self)
        return self._extensions

    extensions = ext

    @classmethod
    def join(cls, delimiter, subpatterns):
        composite_pattern = cls()
        for subpattern in subpatterns[:-2]:
            composite_pattern = composite_pattern + subpattern + delimiter
        composite_pattern = composite_pattern + subpatterns[-1]
        return composite_pattern


class Group(Pattern):
    def __call__(self, name=None, optional=False) -> 'Pattern':
        add_right = [')']
        if optional:
            add_right.append('?')
        add_left = ['(']
        if name is not None:
            add_left.append(f'?P<{name}>')
        return self.close_bracket().clone_with_updates(
            prepend=add_left,
            append=add_right
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


class ExtensionRegistry(MutableMapping):
    def __init__(self, pattern: Pattern):
        self._registry = {}
        self._pattern = pattern
        self._callbacks_initialized = False
        self._callbacks = {}

    def __setitem__(self, key, value):
        self._registry[key] = value

    def __delitem__(self, key):
        del self._registry[key]

    def __len__(self):
        return len(self._registry)

    def __getitem__(self, item):
        return self._registry[item]

    def __iter__(self):
        return iter(self._registry)

    def __repr__(self):
        return repr(self._registry)

    @property
    def registry(self):
        return self._registry

    def clone(self):
        new = self.__class__(self._pattern)
        new._callbacks_initialized = False
        return new

    def _initialize_callbacks(self):
        if self._callbacks_initialized:
            return

        for name, klass in self.registry.items():
            self._callbacks[name] = klass(self._pattern)
        self._callbacks_initialized = True

    def _ensure_clone(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            if not isinstance(result, Pattern):
                raise ValueError(type(result))
            if result is self._pattern:
                raise ValueError('pattern instance clone required')
            return result
        return wrapper

    def __getattr__(self, item):
        if item in self.registry:
            self._initialize_callbacks()
            return self._ensure_clone(self._callbacks[item])
        else:
            raise AttributeError(item)


Pattern.ANY_NUMBER = BracketExpressionPartial(Number()(skip_brackets=True).build())
Pattern.ANY_ASCII_CHARACTER = BracketExpressionPartial(
    AsciiLetterCharacter()(skip_brackets=True).build()
)
Pattern.NO_WHITESPACE = BracketExpressionPartial(Whitespace()(match=False).build())
Pattern.ANY_WHITESPACE = BracketExpressionPartial(Whitespace()(match=True).build())
