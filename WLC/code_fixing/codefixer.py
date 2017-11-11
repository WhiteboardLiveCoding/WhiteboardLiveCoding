import logging
import sys
from math import ceil

import editdistance
import regex
from stdlib_list import stdlib_list

from WLC.code_fixing.static import get_functions

PERMUTATION_LENGTH = 2
ALLOWED_DIFFERENCE = 0.2

LOGGER = logging.getLogger()


class CodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines
        self.context = {'variables': [], 'functions': get_functions(), 'classes': [], 'imports': [], 'methods': []}
        self.in_class = False
        self.class_indent = 0
        self.syntax = []
        self.rules = []
        self.statements = []

        self.syntax.append(('VARIABLE', '[a-z_]\w*'))
        self.syntax.append(('FUNCTION', '[a-z_]\w*'))

        self.syntax.append(('STATEMENT', '.*'))
        self.syntax.append(('BOOLEAN', '.*'))
        self.syntax.append(('PARAMETERS', '.*'))

        self.statements.append(('(FUNCTION)\((STATEMENT)\)', 2, None, self.fix_func_or_class_call))
        self.statements.append(('(VARIABLE)\.(FUNCTION)\((STATEMENT)\)', 3, None, self.fix_method_call))
        self.statements.append(('(VARIABLE)', 0, None, self.fix_variable))

        # self.rules: list of quad-tuples (string to match, number of fixed, analysis_func, fix_func)
        # analysis -> goes over result and gets any context var
        # fix_func -> fixes the str with context var
        self.rules.append(('import (.*)', 7, None, self.fix_import))
        self.rules.append(('import (.*?) as (.*)', 11, None, self.fix_import_as))
        self.rules.append(('from (.*?) import (.*?)(, .*?)*', 13, None, self.fix_from_import))
        self.rules.append(('def (VARIABLE)\((PARAMETERS)\):', 7, self.analyze_def, self.fix_def))
        self.rules.append(('class (VARIABLE):', 7, self.analyze_class, self.fix_class))
        self.rules.append(('if (BOOLEAN):', 4, None, self.fix_if))
        self.rules.append(('elif (BOOLEAN):', 6, None, self.fix_elif))
        self.rules.append(('return (STATEMENT)', 7, None, self.fix_return))
        self.rules.append(('while (BOOLEAN):', 7, None, self.fix_while))
        self.rules.append(('for (VARIABLE) in (STATEMENT):', 9, self.analyze_for, self.fix_for))
        self.rules.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, self.analyze_for_range, self.fix_for_range))
        self.rules.append(('(FUNCTION)\((STATEMENT)\)', 2, None, self.fix_function_call))
        self.rules.append(('(VARIABLE)\.(FUNCTION)\((STATEMENT)\)', 3, None, self.fix_method_call))
        self.rules.append(('(VARIABLE) = (STATEMENT)', 3, self.analyze_assignment, self.fix_assignment))
        self.rules.append(('assert (STATEMENT)', 7, None, self.fix_assert))
        self.rules.append(('del (STATEMENT)', 4, None, self.fix_del))
        self.rules.append(('raise (STATEMENT)', 6, None, self.fix_raise))
        self.rules.append(('pass', 4, None, lambda x, y: 'pass'))
        self.rules.append(('else:', 5, None, lambda x, y: 'else:'))
        self.rules.append(('break', 5, None, lambda x, y: 'break'))
        self.rules.append(('continue', 8, None, lambda x, y: 'continue'))
        self.rules.append(('(.*)', 0, None, None))  # If nothing else works this will

        LOGGER.debug('Compiling main rules.')
        self.rules_regexes = self.compile_regex(self.rules)

        LOGGER.debug('Compiling statement rules.')
        self.statements_regexes = self.compile_regex(self.statements)

    def fix(self):
        """
        Main function to be called which finds the closest regex match for each line, extracts context variables and
        function names and then attempts to fix typos.

        :return: Fixed version of the code
        """
        LOGGER.debug('Starting code fixing.')

        fixed_lines = []
        closest_matches = []

        LOGGER.debug('Looking for closest matches.')
        for i in range(len(self.poss_lines)):  # range loop OK because of indexing type
            closest_match = self.find_closest_match(self.poss_lines[i], self.rules_regexes)
            (match, analyze_func, _) = closest_match

            if analyze_func:
                analyze_func(match.groups(), i)

            # At each line, check if currently in a class declaration.
            if self.indents[i] < self.class_indent and self.in_class:
                self.in_class = False

            closest_matches.append(closest_match)

        LOGGER.debug('Fixing lines.')
        for idx, closest_match in enumerate(closest_matches):
            (match, _, fix_func) = closest_match
            if fix_func:
                fixed = fix_func(match, self.poss_lines[idx])
                fixed_lines.append(self.naive_fix(fixed))
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
        closest = None, None, None
        permutations = self.permutations(poss_line)

        LOGGER.debug("Checking {} regex fixes for a good match.".format(len(regexes)))
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

        LOGGER.debug('Trying %s permutations', len(permutations))

        return results

    def compile_regex(self, to_compile):
        """
        Compiles the list of regexes replacing keywords in the rules by the syntax expressions. Syntax expressions can
        also refer to other expressions that were listed before them because they get expanded.

        :param to_compile: List of rules that should get compiled into syntax expressions
        :return: Compiled list of regexes
        """
        regexes = []

        for i in range(len(self.syntax)):
            for j in range(i):
                self.syntax[i] = (self.syntax[i][0], self.syntax[i][1].replace(self.syntax[j][0], self.syntax[j][1]))

        for rule, fixed, analyze, fix in to_compile:
            difference = max(ceil(fixed * ALLOWED_DIFFERENCE), 0)
            reg = '^(?e)((?:%s){e<=%s})$' % (rule, difference)

            for i in range(len(self.syntax)):
                reg = reg.replace('({})'.format(self.syntax[i][0]), '({})'.format(self.syntax[i][1]))

            r = regex.compile(reg)
            regexes.append((r, difference, analyze, fix))

        regexes = sorted(regexes, key=lambda x: -x[1])

        return regexes  # return compiled regexes

    def levenshtein_closest(self, poss_chars, possibilities, allowed_difference=ALLOWED_DIFFERENCE):
        """
        Finds one of the possible strings which is closest to a permutation of a line or part of a line. This is fairly
        expensive when there are a lot of possibilities and permutations.

        :param poss_chars: Possible characters to make up all of the permutations of the line/substring
        :param possibilities: Possible strings which should be matched to the closest permutation
        :param allowed_difference: Maximum percentage difference between closest match and one possibility
        :return: The closest possibility to the provided line/substring and the levenshtein distance
        """

        permutations = self.permutations(poss_chars)
        best = allowed_difference
        recommended = permutations[0]

        for permutation in permutations:
            for possibility in possibilities:
                distance = editdistance.eval(permutation, possibility) / (len(possibility) or 1)

                if distance == 0:
                    return possibility, 0
                elif distance < best:
                    recommended = possibility
                    best = distance
        return recommended, best

    def naive_fix(self, line):
        replace = [('--', '__'), ('\'\'', '"'), (',,', '"')]

        for (find, rep) in replace:
            line = line.replace(find, rep)

        return line

    def find_args(self, args):
        # If no args or args empty string, return empty list
        if not args or not args.strip():
            return []

        # Init prev to first non-whitespace character
        prev = 0
        while prev < len(args) and args[prev] == " ":
            prev += 1

        # No open brackets, so 0
        openBR = 0
        # curr list of results is empty
        arguments = []

        for idx, char in enumerate(args):
            if char == "," and openBR == 0:
                arguments.append((args[prev: idx], prev, idx))
                prev = idx + 1
                while args[prev] == " ":
                    prev += 1
            elif char == "(":
                openBR += 1
            elif char == ")":
                openBR -= 1
        else:
            arguments.append((args[prev:], prev, len(args)))

        return arguments

    # ANALYSE
    def analyze_class(self, groups, line_n):
        LOGGER.debug("Analysing class. Adding {} to context.".format(groups[1]))
        self.context['classes'].append(groups[1])
        self.in_class = True
        self.class_indent = self.indents[line_n]

    def analyze_for_range(self, groups, line_n):
        LOGGER.debug("Analysing range. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_for(self, groups, line_n):
        LOGGER.debug("Analysing for. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_assignment(self, groups, line_n):
        LOGGER.debug("Analysing assignment. Adding {} to context.".format(groups[1]))
        self.context['variables'].append(groups[1])

    def analyze_def(self, groups, line_n):
        LOGGER.debug("Analysing function def. Adding {} to context.".format(groups[1]))
        # differentiate between functions and class methods
        if self.indents[line_n] <= self.class_indent and self.in_class:
            self.context['methods'].append(groups[1])
        else:
            self.context['functions'].append(groups[1])
        variables = groups[2].split(',')
        LOGGER.debug("Analysing function def variables. Adding {} to context.".format(variables))
        self.context['variables'].extend(variables)

    def fix_import(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]

        closest, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import. Adding {} to context after analysis.".format(closest))
        self.context["imports"].append(closest)
        return 'import {}'.format(closest)

    def fix_import_as(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import as. Adding {} to context after analysis.".format(groups[2]))
        self.context["imports"].append(groups[2])
        return 'import {} as {}'.format(closest_module, groups[2])

    def fix_from_import(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing from X import Y. Adding {} to context after analysis.".format(closest_module))
        for imported in groups[1:]:
            self.context["imports"].append(imported)
        return 'from {} import {}'.format(closest_module, ", ".join(groups[1:]))

    def fix_class(self, match, poss_chars):
        groups = match.groups()
        poss_class = poss_chars[match.start(2): match.end(2)]
        closest, _ = self.levenshtein_closest(poss_class, self.context["classes"])
        LOGGER.debug("Fixing class. Changing from {} to {}.".format(groups[1], closest))
        return 'class {}:'.format(closest)

    def fix_if(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing if. Using {}.".format(*groups[1:]))
        return 'if {}:'.format(*groups[1:])

    def fix_elif(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing elif. Using {}.".format(*groups[1:]))
        return 'elif {}:'.format(*groups[1:])

    def fix_return(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing return. Using {}.".format(*groups[1:]))
        return 'return {}'.format(*groups[1:])

    def fix_while(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing while. Using {}.".format(*groups[1:]))
        return 'while {}:'.format(*groups[1:])

    def fix_for(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing for. Using {} and {}.".format(*groups[1:]))
        return 'for {} in {}:'.format(*groups[1:])

    def fix_for_range(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing for range. Using {} and {}.".format(*groups[1:]))
        return 'for {} in range({}):'.format(*groups[1:])

    def fix_function_call(self, match, poss_chars):
        groups = match.groups()
        poss_func = poss_chars[match.start(2): match.end(2)]
        closest, _ = self.levenshtein_closest(poss_func, self.context["functions"])
        LOGGER.debug(groups)
        LOGGER.debug("Fixing func call. Using {} and {}.".format(*(closest, *groups[2:])))

        # use 3 not 2 because of list 0-index
        new_args = self.fix_arguments(groups[2], poss_chars[match.start(3): match.end(3)])

        LOGGER.debug("Fixing func call arguments from {} to {}".format(groups[2], new_args))
        return '{}({})'.format(closest, new_args)

    # Note: not perfect, but can't distinguish between functions or classes, so hard to do much else
    def fix_func_or_class_call(self, match, poss_chars):
        groups = match.groups()
        poss_func = poss_chars[match.start(2): match.end(2)]
        closest, _ = self.levenshtein_closest(poss_func, self.context["functions"] + self.context["classes"])
        LOGGER.debug(groups)
        LOGGER.debug("Fixing func/class call. Using {} and {}.".format(*(closest, *groups[2:])))

        # use 3 not 2 because of list 0-index
        new_args = self.fix_arguments(groups[2], poss_chars[match.start(3): match.end(3)])

        LOGGER.debug("Fixing func/class call arguments from {} to {}".format(groups[2], new_args))
        return '{}({})'.format(closest, new_args)

    def fix_method_call(self, match, poss_chars):
        groups = match.groups()
        poss_var = poss_chars[match.start(2): match.end(2)]
        closest_var, _ = self.levenshtein_closest(poss_var, self.context["variables"])
        LOGGER.debug("Fixing method call var. From {} to {}".format(groups[1], closest_var))

        poss_method = poss_chars[match.start(3): match.end(3)]
        closest_method, _ = self.levenshtein_closest(poss_method, self.context["methods"])
        LOGGER.debug("Fixing method call method. From {} to {}".format(groups[2], closest_method))

        closests_args = [
            self.levenshtein_closest(poss_arg, self.context["variables"])[0] for poss_arg
            in (poss_chars[match.start(group_n): match.end(group_n)] for group_n in range(4, len(groups)+1))
        ]
        LOGGER.debug("Fixing method call args. From {} to {}.".format(groups[3], closests_args))

        return '{}.{}({})'.format(closest_var, closest_method, *closests_args)

    def fix_assignment(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("About to fix RHS of assignment")
        rhs = self.fix_statement(groups[2], poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing assignment. Using {} = {}.".format(groups[1], rhs))
        return '{} = {}'.format(groups[1], rhs)

    def fix_assert(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing assert. Using {}.".format(*groups[1:]))
        return 'assert {}'.format(*groups[1:])

    def fix_del(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing del. Using {}.".format(*groups[1:]))
        return 'del {}'.format(*groups[1:])

    def fix_raise(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing raise. Using {}.".format(*groups[1:]))
        return 'raise {}'.format(*groups[1:])

    def fix_def(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing def. Using {} and {}.".format(*groups[1:]))
        return 'def {}({}):'.format(*groups[1:])

    def fix_arguments(self, args, poss_chars):
        arg_matches = self.find_args(args)

        LOGGER.debug("Fixing {} arguments: {}".format(len(arg_matches), arg_matches))
        result = []
        for match in arg_matches:
            arg = match[0]
            start = match[1]
            end = match[2]
            new_arg = self.fix_statement(arg, poss_chars[start: end])  # when variable.
            LOGGER.debug("Fixing argument {} to {}".format(arg, new_arg))
            result.append(new_arg)

        return ", ".join(result)

    def fix_statement(self, matched_text, poss_chars):
        match, analyze_func, fix_func = self.find_closest_match(poss_chars, self.statements_regexes)

        if fix_func:
            fixed = fix_func(match, poss_chars)
        else:
            LOGGER.debug("No match for {}. Not fixing.".format(matched_text))
            fixed = matched_text

        return fixed

    # TODO: ensure we don't fix non-vars
    def fix_variable(self, matched_text, poss_chars):
        closest, _ = self.levenshtein_closest(poss_chars, self.context["variables"])
        LOGGER.debug("Fixing variable {} to {}.".format(matched_text, closest))
        return closest
