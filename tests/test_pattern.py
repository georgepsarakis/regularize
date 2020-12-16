import unittest
import re

from regex_composer.expression import Pattern, pattern


class TestPattern(unittest.TestCase):
    def setUp(self):
        self.pattern = pattern().lowercase_ascii_letters(closed=True)

    @staticmethod
    def _to_list(pattern_instance):
        return list(map(str, pattern_instance.stack))

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
            any_number().quantify(minimum=1). \
            literal('.log'). \
            case_insensitive()

        expected_regex = re.compile(r'application\.[0-9]+\.log',
                                    re.IGNORECASE)
        self.assertEqual(expected_regex, self.pattern.compile())

    def test_domain_pattern(self):
        # [a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}
        ascii_alpha_numeric = \
            pattern().any_number(). \
            lowercase_ascii_letters(). \
            uppercase_ascii_letters()

        print(ascii_alpha_numeric.end_range() + ascii_alpha_numeric.literal('-').quantify(1, 61))
