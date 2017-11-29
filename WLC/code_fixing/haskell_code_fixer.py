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

        self.rules.append(("(VARIABLE) = (VAL)", 5, None, self.fix_assignment))
        self.rules.append(("let (VARIABLE) = (VAL)", 9, None, self.fix_assignment))
        self.rules.append(("(FUNCTION) (ARGS) = (PARAMETERS)", 5, None, self.fix_func_decl))
        self.rules.append(('(.*)', 0, None, self.fix_default))  # If nothing else works this will

        LOGGER.debug('Compiling main haskell rules.')
        self.rules_regexes = self.compile_regex(self.rules)

        LOGGER.debug('Compiling haskell statement rules.')
        self.statements_regexes = self.compile_regex(self.statements)

    def fix(self):
        """
        Main function to be called which finds the closest regex match for each line, extracts context variables and
        function names and then attempts to fix typos.

        :return: Fixed version of the code
        """
        LOGGER.debug('Starting haskell code fixing.')

        fixed_lines = []
        closest_matches = []

        LOGGER.debug('Looking for closest matches.')
        for i in range(len(self.poss_lines)):  # range loop OK because of indexing type
            closest_match = self.find_closest_match(self.poss_lines[i], self.rules_regexes)
            (match, analyze_func, _) = closest_match

            if analyze_func:
                analyze_func(match.groups(), i)

            closest_matches.append(closest_match)

        LOGGER.debug('Fixing lines.')
        for idx, closest_match in enumerate(closest_matches):
            (match, _, fix_func) = closest_match

            fixed = fix_func(match, self.poss_lines[idx])
            fixed_lines.append(fixed)

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def fix_and(self, match, poss_chars):
        pass

    def fix_or(self, match, poss_chars):
        pass

    def fix_not(self, match, poss_chars):
        pass

    def fix_assignment(self, match, poss_chars):
        pass

    def fix_func(self, match, poss_chars):
        pass

    def fix_default(self, match, poss_chars):
        pass