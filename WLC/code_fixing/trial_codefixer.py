import sys
import editdistance
import logging

from math import ceil
from stdlib_list import stdlib_list

import regex

from WLC.code_fixing.static import get_functions

RULES = list()
SYNTAX = list()

PERMUTATION_LENGTH = 2
ALLOWED_DIFFERENCE = 0.2

LOGGER = logging.getLogger()


class TrialCodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = []

        SYNTAX.append(('VARIABLE', '[a-z]+[0-9]*'))
        SYNTAX.append(('STATEMENT', '.*'))
        SYNTAX.append(('BOOLEAN', '.*'))
        SYNTAX.append(('PARAMETERS', '.*'))

        RULES.append(('import (.*)', 7, None, self.fix_import))
        RULES.append(('def (VARIABLE)\((PARAMETERS)\):', 7, self.analyze_def, self.fix_def))
        RULES.append(('class (VARIABLE):', 7, self.analyze_class, self.fix_class))
        RULES.append(('if (BOOLEAN):', 4, None, self.fix_if))
        RULES.append(('elif (BOOLEAN):', 6, None, self.fix_elif))
        RULES.append(('return (STATEMENT)', 7, None, self.fix_return))
        RULES.append(('while (BOOLEAN):', 7, None, self.fix_while))
        RULES.append(('for (VARIABLE) in (STATEMENT):', 9, self.analyze_for, self.fix_for))
        RULES.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, self.analyze_for_range, self.fix_for_range))
        RULES.append(('(VARIABLE)\((STATEMENT)\)', 2, self.analyze_function_call, self.fix_function_call))
        RULES.append(('(VARIABLE) = (STATEMENT)', 3, self.analyze_assignment, self.fix_assignment))
        RULES.append(('assert (STATEMENT)', 7, None, self.fix_assert))
        RULES.append(('del (STATEMENT)', 4, None, lambda _: self.fix_del))
        RULES.append(('raise (STATEMENT)', 6, None, self.fix_raise))
        RULES.append(('pass', 4, None, lambda x, y, z: 'pass'))
        RULES.append(('else:', 5, None, lambda x, y, z: 'else:'))
        RULES.append(('break', 5, None, lambda x, y,z: 'break'))
        RULES.append(('continue', 8, None, lambda x, y, z: 'continue'))
        RULES.append(('(.*)', 0, None, lambda groups, x, y: '{}'.format(*groups[1:]))) # If nothing else works this will

    def fix(self):
        """
        Main function to be called which finds the closest regex match for each line, extracts context variables and
        function names and then attempts to fix typos.

        :return: Fixed version of the code
        """
        LOGGER.debug('Starting code fixing.')

        poss_lines = self.poss_lines
        lines = self.code.splitlines()
        fixed_lines = list()
        closest_matches = list()

        LOGGER.debug('Compiling main rules.')
        regexes = self.compile_regexes(RULES)

        LOGGER.debug('Looking for closest matches.')
        for i in range(len(poss_lines)):
            closest_matches.append(self.find_closest_match(poss_lines[i], regexes))

        context = {'variables': [], 'functions': []}

        LOGGER.debug('Analyzing lines.')
        for i in range(len(closest_matches)):
            (match, analyze, _) = closest_matches[i]

            if analyze:
                analyze(match.groups(), poss_lines[i], context)

        LOGGER.debug('Fixing lines.')
        for i in range(len(closest_matches)):
            (match, _, fix) = closest_matches[i]
            fixed_lines.append(fix(match.groups(), poss_lines[i], context))

        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line) for indent, line in
                         zip(self.indents, fixed_lines))

    def find_closest_match(self, poss_line, regexes):
        """
        Finds the closest regex to the line provided looking at possible permutations of characters.

        :param poss_line: Possible characters that make up the line. Type: [[Char]]
        :param regexes: Compiled list of regexes
        :return: The closest match and the functions used to analyze and fix the line
        """
        distance = sys.maxsize
        closest = None
        permutations = self.permutations(poss_line)

        for r, fixed, analyze, fix in regexes:
            for possible in permutations:
                match = r.match(possible)

                if match:
                    if sum(match.fuzzy_counts) - fixed < distance:
                        distance = sum(match.fuzzy_counts) - fixed
                        closest = (match, analyze, fix)

                        if distance < 0:
                            return closest

        return closest

    def permutations(self, poss_chars):
        """
        Finds the most probable permutations of the line. Complexity is reduced by the fact that there are only 1 or 2
        possibilities of a character.

        :param poss_chars: Possible characters that make up the line
        :return: Possible ways to write the line returned as a list of strings
        """
        if not poss_chars:
            return ['']

        results = list()
        permutations = self.permutations(poss_chars[1:])

        for char in poss_chars[0][:PERMUTATION_LENGTH]:
            for permutation in permutations:
                results.append(char + permutation)

        LOGGER.debug('Trying %s permutations', len(permutations))

        return results

    def compile_regexes(self, rules):
        """
        Compiles the list of regexes replacing keywords in the rules by the syntax expressions. Syntax expressions can
        also refer to other expressions that were listed before them because they get expanded.

        :param rules: List of rules that should get compiled into syntax expressions
        :return: Compiled list of regexes
        """
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

        regexes = sorted(regexes, key=lambda x: -x[1])

        return regexes

    def levenshtein_closest(self, poss_chars, possibilities):
        """
        Finds one of the possible strings which is closest to a permutation of a line or part of a line. This is fairly
        expensive when there are a lot of possibilities and permutations.

        :param poss_chars: Possible characters to make up all of the permutations of the line/substring
        :param possibilities: Possible strings which should be matched to the closest permutation
        :return: The closest possibility to the provided line/substring and the levenshtein distance
        """

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
        """
        Finds a substring(target) in a line and extracts the possible characters for that substring from the possible
        characters for the whole line. This should be used when calling levenshtein_closest or find_closest_match
        on a substring of a line.

        :param line: A line of text
        :param poss_chars: Possible characters that make up the line
        :param target: Target substring which should be extracted
        :return: Possible characters that make up the substring
        """
        pos = line.find(target)
        return poss_chars[pos:pos + len(target)]

    def fix_import(self, groups, poss_chars, context):
        poss_import = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        return 'import {}'.format(*groups[1:])

    def analyze_class(self, groups, poss_chars, context):
        context['functions'].append(groups[1])

    def fix_class(self, groups, poss_chars, context):
        return 'class {}:'.format(*groups[1:])

    def fix_if(self, groups, poss_chars, context):
        return 'if {}:'.format(*groups[1:])

    def fix_elif(self, groups, poss_chars, context):
        return 'elif {}:'.format(*groups[1:])

    def fix_return(self, groups, poss_chars, context):
        return 'return {}'.format(*groups[1:])

    def fix_while(self, groups, poss_chars, context):
        return 'while {}:'.format(*groups[1:])

    def analyze_for(self, groups, poss_chars, context):
        context['variables'].append(groups[1])

    def fix_for(self, groups, poss_chars, context):
        return 'for {} in {}:'.format(*groups[1:])

    def analyze_for_range(self, groups, poss_chars, context):
        context['variables'].append(groups[1])

    def fix_for_range(self, groups, poss_chars, context):
        return 'for {} in range({}):'.format(*groups[1:])

    def analyze_function_call(self, groups, poss_chars, context):
        context['functions'].extend(groups[1].split('.'))

    def fix_function_call(self, groups, poss_chars, context):
        return '{}({})'.format(*groups[1:])

    def analyze_assignment(self, groups, poss_chars, context):
        context['variables'].append(groups[1])

    def fix_assignment(self, groups, poss_chars, context):
        return '{} = {}'.format(*groups[1:])

    def fix_assert(self, groups, poss_chars, context):
        return 'assert {}'.format(*groups[1:])

    def fix_del(self, groups, poss_chars, context):
        return 'del {}'.format(*groups[1:])

    def fix_raise(self, groups, poss_chars, context):
        return 'raise {}'.format(*groups[1:])

    def analyze_def(self, groups, poss_chars, context):
        context['functions'].append(groups[1])
        variables = groups[2].split(',')
        context['variables'].extend(variables)

    def fix_def(self, groups, poss_chars, context):
        return 'def {}({}):'.format(*groups[1:])
