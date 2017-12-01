import logging

import collections

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

        self.context = {'variables': [], 'functions': []}

        self.func_context = collections.defaultdict(lambda: collections.defaultdict(list))
        self.curr_func = None

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

        self.rules.append(("(VARIABLE) = (VAL)", 3, None, self.fix_assignment))
        self.rules.append(("let (VARIABLE) = (VAL)", 7, None, self.fix_global_assignment))
        self.rules.append(("(FUNCTION) (ARGS) = (PARAMETERS)", 4, self.analyse_func, self.fix_func_decl))
        self.rules.append(("(FUNCTION) (ARGS)", 1, self.analyse_func, self.fix_func_decl_newline))
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

    def analyse_global_assignment(self, match, line_n):
        groups = match.groups()
        var_name = groups[1]
        self.context['functions'].append(var_name)
        LOGGER.debug("{} var added to global scope".format(var_name))


    def analyse_func(self, match, line_n):
        groups = match.groups()
        func_name = groups[1]  # add to global scope
        self.curr_func = func_name
        self.context['functions'].append(func_name)
        LOGGER.debug("{} function added to global scope".format(func_name))

        func_args = groups[2].split()  # add to function scope
        self.func_context[self.curr_func2]['variables'].extend(func_args)
        LOGGER.debug("{} added to local function scope".format(func_args))

    def fix_and(self, match, poss_chars):
        groups = match.groups()
        var1 = groups[1]
        var2 = groups[2]
        LOGGER.debug("Fixing &&")
        return "{} && {}".format(var1, var2)

    def fix_or(self, match, poss_chars):
        groups = match.groups()
        var1 = groups[1]
        var2 = groups[2]
        LOGGER.debug("Fixing ||")
        return "{} || {}".format(var1, var2)

    def fix_not(self, match, poss_chars):
        groups = match.groups()
        var1 = groups[1]
        LOGGER.debug("Fixing not")
        return "not {}".format(var1)

    def fix_assignment(self, match, poss_chars):
        groups = match.groups()
        var1 = groups[1]
        var2 = groups[2]
        LOGGER.debug("Fixing assignment")
        return "{} = {}".format(var1, var2)

    def fix_global_assignment(self, match, poss_chars):
        groups = match.groups()
        var1 = groups[1]
        var2 = groups[2]
        LOGGER.debug("Fixing let assignment")
        return "let {} = {}".format(var1, var2)

    def fix_func_decl(self, match, poss_chars):
        groups = match.groups()
        funcname = groups[1]
        self.curr_func = funcname

        func_args = groups[2].split()
        func_exec = groups[3]

        LOGGER.debug("Function declared for {}".format(funcname))
        LOGGER.debug("With args {}".format(func_args))
        LOGGER.debug("With exec {}".format(func_exec))
        return "{} {} = {}".format(funcname, " ".join(func_args), func_exec)

    def fix_func_decl_newline(self, match, poss_chars):
        groups = match.groups()
        funcname = groups[1]
        self.curr_func = funcname

        func_args = groups[2].split()

        LOGGER.debug("Newline function declared for {}".format(funcname))
        LOGGER.debug("With args {}".format(func_args))
        return "{} {}".format(funcname, " ".join(func_args))

    def fix_default(self, match, poss_chars):
        groups = match.groups()
        all = groups[0]
        LOGGER.debug("Could not fix '{}'".format(all))
        return all
