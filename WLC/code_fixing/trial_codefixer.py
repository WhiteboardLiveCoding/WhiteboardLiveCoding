import sys
import editdistance
import builtins

from math import ceil
from stdlib_list import stdlib_list

import regex

from WLC.code_fixing.static import get_functions

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
        SYNTAX.append(('PARAMETERS', '.*'))

        RULES.append(('import (.*)', 7, None, self.fix_import))
        RULES.append(('def (VARIABLE)\((PARAMETERS)\):', 7, self.analyze_defs, self.fix_def))
        RULES.append(('class (VARIABLE):', 7, None, self.fix_class))
        RULES.append(('if (BOOLEAN):', 4, None, self.fix_if))
        RULES.append(('elif (BOOLEAN):', 6, None, self.fix_elif))
        RULES.append(('return (STATEMENT)', 7, None, self.fix_return))
        RULES.append(('while (BOOLEAN):', 7, None, self.fix_while))
        RULES.append(('for (VARIABLE) in (STATEMENT):', 9, None, self.fix_for))
        RULES.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, None, self.fix_for_range))
        RULES.append(('(VARIABLE)\((STATEMENT)\)', 2, None, self.fix_function_call))
        RULES.append(('(VARIABLE) = (STATEMENT)', 3, None, self.fix_assignment))
        RULES.append(('assert (STATEMENT)', 7, None, self.fix_assert))
        RULES.append(('del (STATEMENT)', 4, None, lambda _: self.fix_del))
        RULES.append(('raise (STATEMENT)', 6, None, self.fix_raise))
        RULES.append(('pass', 4, None, lambda _, **kwargs: 'pass'))
        RULES.append(('else:', 5, None, lambda _, **kwargs: 'else:'))
        RULES.append(('break', 5, None, lambda _, **kwargs: 'break'))
        RULES.append(('continue', 8, None, lambda _, **kwargs: 'continue'))
        RULES.append(('(.*)', 0, None, lambda groups, **kwargs: '{}'.format(*groups))) # If nothing else works this will

    def fix(self):
        poss_lines = self.poss_lines
        lines = self.code.splitlines()
        fixed_lines = list()
        closest_matches = list()
        poss_lines_simplified = list()

        for line, i in zip(lines, poss_lines):
            joined = self.join_words(poss_lines[i])
            simplified = self.reduce_line(joined)
            poss_lines_simplified.append(simplified)

            closest_matches.append(self.find_closest_match(simplified))

        context = {'functions': [], 'variables': []}

        for (match, analyze, _) in closest_matches:
            if analyze:
                context = analyze(match.groups()[1:], **context)

        for i in range(len(closest_matches)):
            (match, _, fix) = closest_matches[i]

            kwargs = {'poss_chars': poss_lines_simplified[i],
                      'line': lines[i]}
            kwargs.update(context)

            fixed_lines.append(fix(match.groups()[1:], **kwargs))

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
            deduped = self.remove_duplicate_predictions(filtered)
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
        permutations = self.permutations(poss_line)

        for r, fixed, analyze, fix in regexes:
            for possible in permutations:
                match = r.match(possible)

                if match:
                    if sum(match.fuzzy_counts) - fixed < distance:
                        distance = sum(match.fuzzy_counts) - fixed
                        closest = (match, analyze, fix)

        return closest

    def permutations(self, poss_chars):
        if not poss_chars:
            return ['']

        results = list()
        permutations = self.permutations(poss_chars[1:])

        for char in poss_chars[0][:PERMUTATION_LENGTH]:
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

    def closest_match(self, poss_chars, possibilities):
        permutations = self.permutations(poss_chars)
        best = sys.maxsize
        recommended = None

        for permutation in permutations:
            for possibility in possibilities:
                distance = editdistance.eval(permutation, possibility)

                if distance == 0:
                    return possibility, 0
                elif best > distance:
                    recommended = possibility
                    best = distance
        return recommended, best

    def extract_poss_chars(self, line, poss_chars, target):
        pos = line.find(target)
        return poss_chars[pos:pos + len(target)]

    def fix_import(self, groups, **kwargs):
        line = kwargs.get('line')
        poss_chars = kwargs.get('poss_chars')[line.find(groups[0]):]
        closest, _ = self.closest_match(poss_chars, stdlib_list("3.6"))
        return 'import {}'.format(closest)

    def fix_def(self, groups, **kwargs):
        return 'def {}({}):'.format(*groups)

    def fix_class(self, groups, **kwargs):
        return 'class {}:'.format(*groups)

    def fix_if(self, groups, **kwargs):
        return 'if {}:'.format(*groups)

    def fix_elif(self, groups, **kwargs):
        return 'elif {}:'.format(*groups)

    def fix_else(self, groups, **kwargs):
        return 'else:'

    def fix_return(self, groups, **kwargs):
        return 'return {}'.format(*groups)

    def fix_while(self, groups, **kwargs):
        return 'while {}:'.format(*groups)

    def fix_for(self, groups, **kwargs):
        return 'for {} in {}:'.format(*groups)

    def fix_for_range(self, groups, **kwargs):
        return 'for {} in range({}):'.format(*groups)

    def fix_function_call(self, groups, **kwargs):
        return '{}({})'.format(*groups)

    def fix_assignment(self, groups, **kwargs):
        return '{} = {}'.format(*groups)

    def fix_assert(self, group, **kwargs):
        return 'assert {}'.format(*group)

    def fix_del(self, group, **kwargs):
        return 'del {}'.format(*group)

    def fix_raise(self, group, **kwargs):
        return 'raise {}'.format(*group)

    def analyze_defs(self, group, **context):
        context['functions'].append(group[0])
        return context
