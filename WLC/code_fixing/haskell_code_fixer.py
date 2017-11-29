import logging

from WLC.code_fixing.code_fixer import CodeFixer

LOGGER = logging.getLogger()


class HaskellCodeFixer(CodeFixer):
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines

        self.syntax = []
        self.rules = []
        self.statements = []

        self.syntax.append(('VARIABLE', '[a-z_]+'))
        self.syntax.append(('FUNCTION', '[a-z_]+'))

        self.syntax.append(('STATEMENT', '.+'))
        self.syntax.append(('PARAMETERS', '.*'))
        self.syntax.append(('ARGS', '.*?'))
        self.syntax.append(('VAL', '.+'))

        self.statements.append(('(STATEMENT) && (STATEMENT)', 4, None, self.fix_and))
        self.statements.append(('(STATEMENT) || (STATEMENT)', 4, None, self.fix_or))
        self.statements.append(('not (STATEMENT)', 4, None, self.fix_not))
        self.statements.append(('true', 4, None, lambda x, y: "True"))
        self.statements.append(('false', 5, None, lambda x, y: "False"))

        self.rules.append(("succ (VAL)", 5, None, self.fix_succ))
        self.rules.append(("min (VAL) (VAL)", 5, None, self.fix_min))
        self.rules.append(("max (VAL) (VAL)", 5, None, self.fix_max))
        self.rules.append(("(VARIABLE) = (VAL)", 5, None, self.fix_assignment))
        self.rules.append(("(FUNCTION) (ARGS) = (PARAMETERS)", 5, None, self.fix_func))

    def fix(self):
        return self.code

    def fix_and(self, match, poss_chars):
        pass

    def fix_or(self, match, poss_chars):
        pass

    def fix_not(self, match, poss_chars):
        pass

    def fix_succ(self, match, poss_chars):
        pass

    def fix_min(self, match, poss_chars):
        pass

    def fix_max(self, match, poss_chars):
        pass

    def fix_assignment(self, match, poss_chars):
        pass

    def fix_func(self, match, poss_chars):
        pass
