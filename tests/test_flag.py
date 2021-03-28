import re
import unittest

from regularize.flag import FlagSet
from regularize.expression import Pattern


class TestFlagSet(unittest.TestCase):
    def test_case_insensitive(self):
        pass

    def test_equality_without_pattern(self):
        flags = FlagSet()
        other_flags = FlagSet()
        self.assertEqual(flags, other_flags)

    def test_compile(self):
        flags = FlagSet()
        flags.case_insensitive()
        flags.multiline()
        self.assertEqual(flags.compile(), re.I | re.M)

    def test_copy(self):
        flags = FlagSet()
        flags.case_insensitive()
        new_flags = flags.copy()
        self.assertEqual(flags.compile(), new_flags.compile())
