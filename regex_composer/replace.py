import re

from regex_composer.expression import Expression


class Substitution(Expression):
    def backreference(self, name_or_number):
        self.stack.append(f'\\g<{name_or_number}')
        return self

    def build(self):
        return ''.join(self.stack)

    def replace(self, pattern, string, count=0):
        return pattern.compile().sub(self.build(), string, count=count)
