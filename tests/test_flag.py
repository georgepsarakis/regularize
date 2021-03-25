import re
import unittest

from regularize.flag import FlagSet
from regularize.expression import Pattern


class TestFlagSet(unittest.TestCase):
    def test_case_insensitive(self):
        pass

    def test_equality_without_pattern(self):
        flags = FlagSet(pattern=None)
        other_flags = FlagSet(pattern=None)
        self.assertEqual(flags, other_flags)

    def test_equality_with_pattern(self):
        flags = FlagSet(pattern=Pattern())
        other_flags = FlagSet(pattern=Pattern())
        self.assertEqual(flags, other_flags)

    def test_compile(self):
        flags = FlagSet()
        flags.case_insensitive()
        flags.multiline()
        self.assertEqual(flags.compile(), re.I | re.M)

    def test_copy(self):
        p = Pattern()
        p.flags.case_insensitive()
        flags = FlagSet.copy(p)
        self.assertEqual(flags.compile(), p.flags.compile())
