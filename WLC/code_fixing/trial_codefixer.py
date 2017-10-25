import sys
from math import ceil

import regex

RULES = list()
SYNTAX = list()

MINIMUM_PROBABILITY = 0.01
PERMUTATION_LENGTH = 2
ALLOWED_DIFFERENCE = 0.2


class TrialCodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = []

        SYNTAX.append(('VARIABLE', '[a-z]\w*'))
        SYNTAX.append(('STATEMENT', '.*'))
        SYNTAX.append(('BOOLEAN', '.*'))

        RULES.append(('import (.*)', 7, None, self.fix_import))
        RULES.append(('def (VARIABLE)\((STATEMENT)\):', 7, None, self.fix_def))
        RULES.append(('class (VARIABLE):', 7, None, self.fix_class))
        RULES.append(('if (BOOLEAN):', 4, None, self.fix_if))
        RULES.append(('elif (BOOLEAN):', 6, None, self.fix_elif))
        RULES.append(('else:', 5, None, self.fix_else))
        RULES.append(('return (STATEMENT)', 7, None, self.fix_return))
        RULES.append(('while (BOOLEAN):', 7, None, self.fix_while))
        RULES.append(('for (VARIABLE) in (STATEMENT):', 9, None, self.fix_for))
        RULES.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, None, self.fix_for_range))
        RULES.append(('(VARIABLE)\((STATEMENT)\)', 2, None, self.fix_function_call))
        RULES.append(('(VARIABLE) = (STATEMENT)', 3, None, self.fix_assignment))
        RULES.append(('(.*)', 0, None, lambda groups: '{}'.format(*groups)))

    def fix(self):
        poss_lines = self.poss_lines
        lines = self.code.splitlines()
        fixed_lines = list()
        closest_matches = list()

        for line, i in zip(lines, poss_lines):
            joined = self.join_words(poss_lines[i])
            simplified = self.reduce_line(joined)

            closest_matches.append(self.find_closest_match(simplified))

        for (match, analyze, _) in closest_matches:
            if analyze:
                analyze(match.groups()[1:])

        for (match, _, fix) in closest_matches:
            fixed_lines.append(fix(match.groups()[1:]))

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def join_words(self, poss_lines):
        joined = list()

        for word in range(len(poss_lines)):
            for j in range(len(poss_lines[word])):
                joined.append(poss_lines[word][j])

            if word < len(poss_lines) - 1:
                joined.append([(' ', 1)])

        return joined

    def reduce_line(self, line):
        reduced = list()

        for possibilities in line:
            lowered = map(lambda p: (p[0].lower(), p[1]), possibilities)
            filtered = list(map(lambda c: c[0], filter(lambda c: c[1] > MINIMUM_PROBABILITY, lowered)))
            deduped = self.remove_duplicate_predictions(filtered)[:PERMUTATION_LENGTH]
            reduced.append(deduped)

        return reduced

    def remove_duplicate_predictions(self, seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    def find_closest_match(self, poss_line):
        distance = sys.maxsize
        closest = None
        regexes = self.compile_regexes(RULES)
        permutations = self.permutations(poss_line, 0)

        for r, fixed, analyze, fix in regexes:
            for possible in permutations:
                match = r.match(possible)

                if match:
                    if sum(match.fuzzy_counts) - fixed < distance:
                        distance = sum(match.fuzzy_counts) - fixed
                        closest = (match, analyze, fix)

        return closest

    def permutations(self, poss_line, i):
        if i >= len(poss_line):
            return ['']

        results = list()
        permutations = self.permutations(poss_line, i + 1)

        for char in poss_line[i]:
            for permutation in permutations:
                results.append(char + permutation)

        return results

    def compile_regexes(self, rules):
        regexes = list()

        for i in range(len(SYNTAX)):
            for j in range(i):
                SYNTAX[i] = (SYNTAX[i][0], SYNTAX[i][1].replace(SYNTAX[j][0], SYNTAX[j][1]))

        for rule, fixed, analyze, fix in rules:
            difference = max(ceil(fixed * ALLOWED_DIFFERENCE), 0)
            reg = '(?e)((?:%s){e<=%s})' % (rule, difference)

            for i in range(len(SYNTAX)):
                reg = reg.replace(SYNTAX[i][0], SYNTAX[i][1])

            r = regex.compile(reg)
            regexes.append((r, difference, analyze, fix))

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
