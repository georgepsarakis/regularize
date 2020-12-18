import unittest
import re

from regex_composer.expression import Pattern, pattern


class TestPattern(unittest.TestCase):
    def setUp(self):
        self.pattern = pattern().lowercase_ascii_letters(closed=True)

    @staticmethod
    def _to_list(pattern_instance):
        return list(map(str, pattern_instance.token_stack))

    def _transform(self, function):
        self.pattern = function(self.pattern)

    def test_named_group(self):
        group_name = 'some_group'
        self.assertListEqual(
            self._to_list(self.pattern.group(group_name)),
            ['(', f'?P<{group_name}>', '[', 'a-z', ']', ')']
        )

    def test_unnamed_group(self):
        self._transform(lambda p: p.group())

        # Return a new Pattern instance
        self.assertIsInstance(self.pattern, Pattern)
        self.assertListEqual(
            self._to_list(self.pattern),
            ['(', '[', 'a-z', ']', ')']
        )


class TestComposition(unittest.TestCase):
    def setUp(self):
        self.pattern = Pattern()

    def test_quantified_numeric_range(self):
        self.pattern = self.pattern.literal('application.'). \
            any_number_between().quantify(minimum=1). \
            literal('.log'). \
            case_insensitive()

        expected = re.compile(r'application\.[0-9]+\.log', re.IGNORECASE)
        self.assertEqual(expected, self.pattern.compile())

    def test_domain_pattern(self):
        # Sample domain name pattern
        expected = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9\-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}')

        ascii_alpha_numeric = pattern(). \
            lowercase_ascii_letters(). \
            uppercase_ascii_letters(). \
            any_number_between()

        domain_pattern = \
            ascii_alpha_numeric.end_range() + \
            ascii_alpha_numeric.literal('-').quantify(1, 61)

        # At least one alphanumeric character before the dot and after the dash
        domain_pattern += ascii_alpha_numeric.end_range()
        # Add TLD
        domain_pattern = domain_pattern.literal('.').\
            lowercase_ascii_letters(closed=False).\
            uppercase_ascii_letters().\
            quantify(minimum=2)

        self.assertEqual(expected, domain_pattern.compile())
