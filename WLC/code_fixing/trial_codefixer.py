import sys
from math import ceil

import regex

RULES = list()
SYNTAX = dict()


class TrialCodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = []

        SYNTAX['variable'] = '[a-z]\w*'
        SYNTAX['statement'] = '.*'
        SYNTAX['boolean'] = '.*'

        RULES.append(('import .*', 7, self.fix_import))
        RULES.append(('def ({variable})\(({statement})\):', 7, self.fix_def))
        RULES.append(('class ({variable}):', 7, self.fix_class))
        RULES.append(('if ({boolean}):', 4, self.fix_if))
        RULES.append(('elif ({boolean}):', 6, self.fix_elif))
        RULES.append(('else:', 5, self.fix_else))
        RULES.append(('return ({statement})', 7, self.fix_return))
        RULES.append(('while ({boolean}):', 7, self.fix_while))
        RULES.append(('for ({variable}) in ({statement}):', 9, self.fix_for))
        RULES.append(('for ({variable}) in range\(({statement})\):', 16, self.fix_for_range))
        RULES.append(('({variable})\(({statement})\)', 2, self.fix_function_call))
        RULES.append(('({variable}) = ({statement})', 3, self.fix_assignment))
        RULES.append(('(.*)', 0, lambda groups: '{}'.format(*groups)))

    def fix(self):
        lines = self.code.splitlines()
        fixed_lines = list()

        for line in lines:
            match, func = self.find_closest_match(line.lstrip())
            groups = match.groups()[1:]
            fixed_lines.append(func(groups))

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def find_closest_match(self, line):
        distance = sys.maxsize
        closest = None
        regexes = self.compile_regexes(RULES)

        for r, fixed, func in regexes:
            match = r.match(line)


            if match:
                if sum(match.fuzzy_counts) - fixed < distance:
                    distance = sum(match.fuzzy_counts) - fixed
                    closest = (match, func)

        return closest

    def compile_regexes(self, rules):
        regexes = list()

        for rule, fixed, func in rules:
            reg = '(?e)((?:%s){e<=%s})' % (rule, max(ceil(2 * fixed / 10), 0))

            for key in SYNTAX:
                reg = reg.replace('{%s}' % key, SYNTAX[key])

            r = regex.compile(reg)
            regexes.append((r, ceil(2 * fixed / 10), func))

        return regexes

    def fix_import(self, groups):
        return 'import {}'.format(*groups)

    def fix_def(self, groups):
        return 'def {}({}):'.format(*groups)

    def fix_class(self, groups):
        return 'class {}:'.format(*groups)

    def fix_if(self, groups):
        return 'if {}:'.format(*groups)

    def fix_elif(self, groups):
        return 'elif {}:'.format(*groups)

    def fix_else(self, groups):
        return 'else:'

    def fix_return(self, groups):
        return 'return {}'.format(*groups)

    def fix_while(self, groups):
        return 'while {}:'.format(*groups)

    def fix_for(self, groups):
        return 'for {} in {}:'.format(*groups)

    def fix_for_range(self, groups):
        return 'for {} in range({}):'.format(*groups)

    def fix_function_call(self, groups):
        return '{}({})'.format(*groups)

    def fix_assignment(self, groups):
        return '{} = {}'.format(*groups)
