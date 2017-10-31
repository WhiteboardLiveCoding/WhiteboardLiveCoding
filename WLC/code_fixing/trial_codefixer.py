import logging
import sys
import editdistance
import builtins

from math import ceil
from stdlib_list import stdlib_list

import regex

from WLC.code_fixing.static import get_functions

RULES = []
SYNTAX = []

PERMUTATION_LENGTH = 2
ALLOWED_DIFFERENCE = 0.2

LOGGER = logging.getLogger()


class TrialCodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = {'variables': [], 'functions': [], 'classes': [], 'imports': [], 'methods': {}}

        SYNTAX.append(('VARIABLE', '[a-z_]\w*'))
        SYNTAX.append(('FUNCTION', '[a-z_]\w*'))

        SYNTAX.append(('DECLARED_VARIABLE', '|'.join(self.context['variables'])))
        SYNTAX.append(('DECLARED_FUNCTION', '|'.join(self.context['functions'])))

        SYNTAX.append(('STATEMENT', '.*'))
        SYNTAX.append(('BOOLEAN', '.*'))
        SYNTAX.append(('PARAMETERS', '.*'))

        # RULES: list of quad-tuples (string to match, number of fixed, analysis_func, fix_func)
        # analysis -> goes over result and gets any context var
        # fix_func -> fixes the str with context var
        RULES.append(('import (.*)', 7, None, self.fix_import))
        RULES.append(('import (.*?) as (.*)', 11, None, self.fix_import_as))
        RULES.append(('from (.*?) import (.*?)(, .*?)*', 13, None, self.fix_from_import))
        RULES.append(('def (VARIABLE)\((PARAMETERS)\):', 7, self.analyze_def, self.fix_def))
        RULES.append(('class (VARIABLE):', 7, self.analyze_class, self.fix_class))
        RULES.append(('if (BOOLEAN):', 4, None, self.fix_if))
        RULES.append(('elif (BOOLEAN):', 6, None, self.fix_elif))
        RULES.append(('return (STATEMENT)', 7, None, self.fix_return))
        RULES.append(('while (BOOLEAN):', 7, None, self.fix_while))
        RULES.append(('for (VARIABLE) in (STATEMENT):', 9, self.analyze_for, self.fix_for))
        RULES.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, self.analyze_for_range, self.fix_for_range))
        RULES.append(('(DECLARED_FUNCTION)\((STATEMENT)\)', 2, None, self.fix_function_call))
        RULES.append(('(DECLARED_VARIABLE)\.(DECLARED_FUNCTION)\((STATEMENT)\)', 3, None, self.fix_method_call))
        RULES.append(('(VARIABLE) = (STATEMENT)', 3, self.analyze_assignment, self.fix_assignment))
        RULES.append(('assert (STATEMENT)', 7, None, self.fix_assert))
        RULES.append(('del (STATEMENT)', 4, None, lambda _: self.fix_del))
        RULES.append(('raise (STATEMENT)', 6, None, self.fix_raise))
        RULES.append(('pass', 4, None, lambda x, y: 'pass'))
        RULES.append(('else:', 5, None, lambda x, y: 'else:'))
        RULES.append(('break', 5, None, lambda x, y: 'break'))
        RULES.append(('continue', 8, None, lambda x, y: 'continue'))
        RULES.append(('(.*)', 0, None, None))  # If nothing else works this will

    def fix(self):
        """
        Main function to be called which finds the closest regex match for each line, extracts context variables and
        function names and then attempts to fix typos.

        :return: Fixed version of the code
        """
        fixed_lines = []
        closest_matches = []

        regexes = self.compile_regexes(RULES)

        for i in range(len(self.poss_lines)):  # range loop OK because of indexing type
            closest_matches.append(self.find_closest_match(self.poss_lines[i], regexes))

        for idx, closest_match in enumerate(closest_matches):
            (match, analyze_func, _) = closest_match

            if analyze_func:
                analyze_func(match.groups(), self.poss_lines[idx])

        for idx, closest_match in enumerate(closest_matches):
            (match, _, fix_func) = closest_match
            if fix_func:
                fixed_lines.append(fix_func(match.groups(), self.poss_lines[idx]))
            else:
                groups = match.groups()
                LOGGER.debug("No match found for {}. Defaulting to not fixing.".format(*groups[1:]))
                fixed_lines.append('{}'.format(*groups[1:]))

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
                    # use fuzzy counts here
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

        results = []
        permutations = self.permutations(poss_chars[1:])

        for char in poss_chars[0][:PERMUTATION_LENGTH]:
            for permutation in permutations:
                results.append(char + permutation)

        return results

    def compile_regexes(self, rules):
        """
        Compiles the list of regexes replacing keywords in the rules by the syntax expressions. Syntax expressions can
        also refer to other expressions that were listed before them because they get expanded.

        :param rules: List of rules that should get compiled into syntax expressions
        :return: Compiled list of regexes
        """
        regexes = []

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
                elif distance < best:
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

    # ANALYSE
    def analyze_class(self, groups, poss_chars):
        LOGGER.debug("Analysing class. Adding {} to context.".format(groups[1]))
        self.context['classes'].append(groups[1])

    def analyze_for_range(self, groups, poss_chars):
        LOGGER.debug("Analysing range. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_for(self, groups, poss_chars):
        LOGGER.debug("Analysing for. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_assignment(self, groups, poss_chars):
        LOGGER.debug("Analysing assignment. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_def(self, groups, poss_chars):
        LOGGER.debug("Analysing function def. Adding {} to context.".format(groups[1]))
        self.context['functions'].append(groups[1])
        variables = groups[2].split(',')
        LOGGER.debug("Analysing function def variables. Adding {} to context.".format(variables))
        self.context['variables'].extend(variables)

    # FIX
    def fix_import(self, groups, poss_chars):
        poss_import = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import. Adding {} to context after analysis.".format(closest))
        self.context["imports"].append(closest)
        return 'import {}'.format(closest)

    def fix_import_as(self, groups, poss_chars):
        poss_import = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import as. Adding {} to context after analysis.".format(groups[2]))
        self.context["imports"].append(groups[2])
        return 'import {} as {}'.format(closest_module, groups[2])

    def fix_from_import(self, groups, poss_chars):
        poss_import = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing from X import Y. Adding {} to context after analysis.".format(closest_module))
        for imported in groups[1:]:
            self.context["imports"].append(imported)
        return 'from {} import {}'.format(closest_module, ", ".join(groups[1:]))

    def fix_class(self, groups, poss_chars):
        poss_class = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest, _ = self.levenshtein_closest(poss_class, self.context["classes"])
        LOGGER.debug("Fixing class. Changing from {} to {}.".format(groups[1], closest))

        return 'class {}:'.format(closest)

    def fix_if(self, groups, poss_chars):
        LOGGER.debug("Fixing if. Using {}.".format(*groups[1:]))
        return 'if {}:'.format(*groups[1:])

    def fix_elif(self, groups, poss_chars):
        LOGGER.debug("Fixing elif. Using {}.".format(*groups[1:]))
        return 'elif {}:'.format(*groups[1:])

    def fix_return(self, groups, poss_chars):
        LOGGER.debug("Fixing return. Using {}.".format(*groups[1:]))
        return 'return {}'.format(*groups[1:])

    def fix_while(self, groups, poss_chars):
        LOGGER.debug("Fixing while. Using {}.".format(*groups[1:]))
        return 'while {}:'.format(*groups[1:])

    def fix_for(self, groups, poss_chars):
        LOGGER.debug("Fixing for. Using {} and {}.".format(*groups[1:]))
        return 'for {} in {}:'.format(*groups[1:])

    def fix_for_range(self, groups, poss_chars):
        LOGGER.debug("Fixing for range. Using {} and {}.".format(*groups[1:]))
        return 'for {} in range({}):'.format(*groups[1:])

    def fix_function_call(self, groups, poss_chars):
        # TODO: check poss_chars. if possible method call by checking if starts with known var followed by . followed by method name

        poss_func = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest, _ = self.levenshtein_closest(poss_func, self.context["functions"])
        LOGGER.debug("Fixing func call. Using {} and {}.".format(*(closest, *groups[2:])))
        return '{}({})'.format(closest, *groups[2:])

    def fix_method_call(self, groups, poss_chars):
        poss_var = self.extract_poss_chars(groups[0], poss_chars, groups[1])
        closest_var, _ = self.levenshtein_closest(poss_var, self.context["variables"])

        poss_method = self.extract_poss_chars(groups[0], poss_chars, groups[2])
        closest_method, _ = self.levenshtein_closest(poss_method, self.context["methods"])

        closests_args = [
            self.levenshtein_closest(poss_arg, self.context["variables"])[0] for poss_arg
            in (self.extract_poss_chars(groups[0], poss_chars, group) for group in groups[3:])
        ]
        LOGGER.debug("Fixing method call. Using {}.".format(*(closest_var, closest_method, closests_args, *groups[2:])))

        return '{}.{}({})'.format(closest_var, closest_method, *closests_args)

    def fix_assignment(self, groups, poss_chars):
        LOGGER.debug("Fixing assignment. Using {} = {}.".format(*groups[1:]))
        return '{} = {}'.format(*groups[1:])

    def fix_assert(self, groups, poss_chars):
        LOGGER.debug("Fixing assert. Using {}.".format(*groups[1:]))
        return 'assert {}'.format(*groups[1:])

    def fix_del(self, groups, poss_chars):
        LOGGER.debug("Fixing del. Using {}.".format(*groups[1:]))
        return 'del {}'.format(*groups[1:])

    def fix_raise(self, groups, poss_chars):
        LOGGER.debug("Fixing raise. Using {}.".format(*groups[1:]))
        return 'raise {}'.format(*groups[1:])

    def fix_def(self, groups, poss_chars):
        LOGGER.debug("Fixing def. Using {} and {}.".format(*groups[1:]))
        return 'def {}({}):'.format(*groups[1:])
