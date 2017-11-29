import logging

PERMUTATION_LENGTH = 5
ALLOWED_DIFFERENCE = 0.25

LOGGER = logging.getLogger()


class HaskellCodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines

    def fix(self):
        return self.code
