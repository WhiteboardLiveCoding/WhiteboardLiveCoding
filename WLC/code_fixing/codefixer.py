import collections
import importlib
import logging
import sys
from itertools import tee
from math import log, floor, ceil

import editdistance
import regex
from stdlib_list import stdlib_list

from ..code_fixing.static import get_functions

PERMUTATION_LENGTH = 5
ALLOWED_DIFFERENCE = 0.25

LOGGER = logging.getLogger()


class CodeFixer:
    def __init__(self, code, indents, poss_lines):
        self.code = code
        self.indents = indents
        self.poss_lines = poss_lines

        self.syntax = []
        self.rules = []
        self.statements = []

        self.curr_line_n = 0
        self.context = {'variables': [], 'functions': get_functions(), 'classes': [], 'imports': [], 'methods': []}

        self.class_indent = 0
        self.class_context = collections.defaultdict(lambda: collections.defaultdict(list))
        self.curr_class = None

        self.def_indent = 0
        self.def_context = collections.defaultdict(lambda: collections.defaultdict(list))
        self.curr_def = None

        self.syntax.append(('VARIABLE', '[a-z_]+'))
        self.syntax.append(('FUNCTION', '[a-z_]+'))

        self.syntax.append(('STATEMENT', '.+?'))  # Note - should be '.+?' or '.+' ?
        self.syntax.append(('PARAMETERS', '.*'))

        self.statements.append(('(FUNCTION)\((PARAMETERS)\)', 2, None, self.fix_func_or_class_call))
        self.statements.append(('(VARIABLE)\.(FUNCTION)\((PARAMETERS)\)', 3, None, self.fix_method_call))
        self.statements.append(('(self)\.(FUNCTION)\((PARAMETERS)\)', 7, None, self.fix_self_method_call))
        self.statements.append(('(VARIABLE)', 0, None, self.fix_variable))
        self.statements.append(('(STATEMENT) and (STATEMENT)', 5, None, self.fix_and))
        self.statements.append(('(STATEMENT) or (STATEMENT)', 4, None, self.fix_or))
        self.statements.append(('not (STATEMENT)', 4, None, self.fix_not))
        self.statements.append(('(STATEMENT) for (VARIABLE) in (STATEMENT)', 9, None, self.fix_generator))
        self.statements.append(('\[(STATEMENT) for (VARIABLE) in (STATEMENT)\]', 11, None, self.fix_list_comp))
        self.statements.append(
            ('(STATEMENT) for (VARIABLE) in range\((STATEMENT)\)', 16, None, self.fix_range_generator))
        self.statements.append(
            ('\[(STATEMENT) for (VARIABLE) in range\((STATEMENT)\)\]', 18, None, self.fix_range_list_comp))
        self.statements.append(('true', 4, None, lambda x, y: "True"))
        self.statements.append(('false', 5, None, lambda x, y: "False"))
        self.statements.append(('none', 4, None, lambda x, y: "None"))

        # check how the size can be changed to account for spaces.
        # self.statements.append(('\((STATEMENT)\)', 2, None, self.fix_bracketed))
        # self.statements.append(('(STATEMENT) == (STATEMENT)', 4, None, self.fix_eq))
        # self.statements.append(('(STATEMENT) + (STATEMENT)', 3, None, self.fix_add))
        # self.statements.append(('(STATEMENT) - (STATEMENT)', 3, None, self.fix_sub))
        # self.statements.append(('(STATEMENT) * (STATEMENT)', 3, None, self.fix_mul))
        # self.statements.append(('(STATEMENT) / (STATEMENT)', 3, None, self.fix_div))

        # self.rules: list of quad-tuples (string to match, number of fixed, analysis_func, fix_func)
        # analysis -> goes over result and gets any context var
        # fix_func -> fixes the str with context var
        self.rules.append(('import (.*)', 7, None, self.fix_import))
        self.rules.append(('import (.*?) as (.*)', 11, None, self.fix_import_as))
        self.rules.append(('from (.*?) import (.*)', 13, None, self.fix_from_import))
        self.rules.append(('def (VARIABLE)\((PARAMETERS)\):', 7, self.analyze_def, self.fix_def))
        self.rules.append(('class (VARIABLE):', 7, self.analyze_class, self.fix_class))
        self.rules.append(('if (STATEMENT):', 4, None, self.fix_if))
        self.rules.append(('elif (STATEMENT):', 6, None, self.fix_elif))
        self.rules.append(('return (STATEMENT)', 7, None, self.fix_return))
        self.rules.append(('while (STATEMENT):', 7, None, self.fix_while))
        self.rules.append(('for (VARIABLE) in (STATEMENT):', 9, self.analyze_for, self.fix_for))
        self.rules.append(('for (VARIABLE) in range\((STATEMENT)\):', 16, self.analyze_for_range, self.fix_for_range))
        self.rules.append(('(FUNCTION)\((PARAMETERS)\)', 2, None, self.fix_function_call))
        self.rules.append(('(VARIABLE)\.(FUNCTION)\((PARAMETERS)\)', 3, None, self.fix_method_call))
        self.rules.append(('self\.(FUNCTION)\((PARAMETERS)\)', 7, None, self.fix_self_method_call))
        self.rules.append(('(VARIABLE) = (STATEMENT)', 3, self.analyze_assignment, self.fix_assignment))
        self.rules.append(('assert (STATEMENT)', 7, None, self.fix_assert))
        self.rules.append(('del (STATEMENT)', 4, None, self.fix_del))
        self.rules.append(('raise (STATEMENT)', 6, None, self.fix_raise))
        self.rules.append(('pass', 4, None, lambda x, y: 'pass'))
        self.rules.append(('else:', 5, None, lambda x, y: 'else:'))
        self.rules.append(('break', 5, None, lambda x, y: 'break'))
        self.rules.append(('continue', 8, None, lambda x, y: 'continue'))
        self.rules.append(('(.*)', 0, None, self.fix_default))  # If nothing else works this will

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

            # At each line, check if currently in a class declaration.
            if self.indents[i] < self.class_indent and self.curr_class:
                self.curr_class = None

            if self.indents[i] < self.def_indent and self.curr_def:
                self.curr_def = None

            if analyze_func:
                analyze_func(match.groups(), i)

            closest_matches.append(closest_match)

        self.curr_def = None
        self.curr_class = None

        LOGGER.debug('Fixing lines.')
        for idx, closest_match in enumerate(closest_matches):
            (match, _, fix_func) = closest_match

            # At each line, check if currently in a class declaration.
            if self.indents[idx] < self.class_indent and self.curr_class:
                self.curr_class = None

            if self.indents[idx] < self.def_indent and self.curr_def:
                self.curr_def = None

            self.curr_line_n = idx

            fixed = fix_func(match, self.poss_lines[idx])
            fixed_lines.append(self.naive_fix(fixed))

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
        permutations_main = self.permutations(poss_line)
        LOGGER.debug('Permutating.')

        LOGGER.debug("Checking {} regex fixes for a good match.".format(len(regexes)))
        for r, fixed, analyze, fix in regexes:
            # duplicate generator to reuse it at each iteration.
            permutations, permutations_main = tee(permutations_main)
            for possible in permutations:
                match = r.match(possible)

                if match:
                    # use fuzzy counts here
                    if sum(match.fuzzy_counts) - fixed < distance:
                        distance = sum(match.fuzzy_counts) - fixed
                        closest = (match, analyze, fix)

                        if sum(match.fuzzy_counts) == 0:
                            return closest

        return closest

    def permutation_count(self, poss_chars):
        """
        Calculates the number of permutations the algorithm would try to create without capping to see if it is
        possible to try all of them or if caps should be applied.

        :param poss_chars: Characters that will be permuted
        :return: The number of all permutations that would be created and number of characters that would be included
                 in the permutations. If there is only one character in a slot then it wont be included in the length
                 because it cannot be permuted.
        """
        perm_count = 1
        perm_length = 0

        for i in range(len(poss_chars)):
            if len(poss_chars[i]) > 1:
                perm_length += 1
                perm_count *= len(poss_chars[i][:PERMUTATION_LENGTH])

        return perm_count, perm_length

    def generate_permutation_strings(self, poss_chars, perm_cap, perm_count, perm_length):
        """
        Finds the most probable permutations of the line. If the count of possible permutations is higher than the cap
        then it will only create a subset of the most probable permutations.

        :param poss_chars: Possible characters that make up the line
        :param perm_cap: The maximum number of permutations that can be created by this function
        :param perm_count: The number of permutations that would be created if left uncapped
        :param perm_length: The number of characters that will be included in calculating the permutations
        :return: Possible ways to write the line returned as a list of strings
        """
        if not poss_chars:
            return ['']

        if perm_count <= perm_cap:
            current_perm_length = PERMUTATION_LENGTH
        else:
            current_perm_length = floor(10 ** (log(perm_cap, 10) / perm_count))

        if len(poss_chars[0]) == 1:
            permutations = self.generate_permutation_strings(poss_chars[1:], perm_cap, perm_count, perm_length)
        else:
            new_cap = perm_cap / len(poss_chars[0][:current_perm_length])
            new_count = perm_count / len(poss_chars[0][:PERMUTATION_LENGTH])
            permutations = self.generate_permutation_strings(poss_chars[1:], new_cap, new_count, perm_length - 1)

        return (char + permutation for permutation in permutations for char in poss_chars[0][:current_perm_length])

    def permutations(self, poss_chars):
        """
        Finds the most probable permutations of the line while capping the maximum number of permutations.

        :param poss_chars: Possible characters that make up the line
        :return: Possible ways to write the line returned as a list of strings
        """

        perm_count, perm_length = self.permutation_count(poss_chars)
        perm_cap = 2 ** 16

        return self.generate_permutation_strings(poss_chars, perm_cap, perm_count, perm_length)

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
        LOGGER.debug('Permutating.')
        best = allowed_difference
        recommended = None

        for permutation in permutations:
            if not recommended:
                recommended = permutation

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
                new_match = CustomMatch(args[prev: idx], prev, idx)
                arguments.append(new_match)
                prev = idx + 1
                while args[prev] == " ":
                    prev += 1
            elif char == "(":
                openBR += 1
            elif char == ")":
                openBR -= 1
        else:
            new_match = CustomMatch(args[prev:], prev, len(args))
            arguments.append(new_match)

        return arguments

    # ANALYSE
    def analyze_class(self, groups, line_n):
        LOGGER.debug("Analysing class. Adding {} to context.".format(groups[1]))
        self.context['classes'].append(groups[1])
        self.class_indent = self.indents[line_n]
        self.curr_class = groups[1]

    def analyze_for_range(self, groups, line_n):
        LOGGER.debug("Analysing range. Adding {} to context.".format(groups[1]))
        if self.curr_def:
            self.def_context[self.curr_def]['variables'].append(groups[1])
        elif self.curr_class:
            self.class_context[self.curr_class]['variables'].append(groups[1])
        else:
            self.context['variables'].append(groups[1])

    def analyze_for(self, groups, line_n):
        LOGGER.debug("Analysing for. Adding {} to context.".format(groups[1]))
        if self.curr_def:
            self.def_context[self.curr_def]['variables'].append(groups[1])
        elif self.curr_class:
            self.class_context[self.curr_class]['variables'].append(groups[1])
        else:
            self.context['variables'].append(groups[1])

    def analyze_assignment(self, groups, line_n):
        LOGGER.debug("Analysing assignment. Adding {} to context.".format(groups[1]))
        if self.curr_def:
            self.def_context[self.curr_def]['variables'].append(groups[1])
        elif self.curr_class:
            self.class_context[self.curr_class]['variables'].append(groups[1])
        else:
            self.context['variables'].append(groups[1])

    def analyze_def(self, groups, line_n):
        LOGGER.debug("Analysing function def. Adding {} to context, and setting class context.".format(groups[1]))
        # differentiate between functions and class methods
        self.def_indent = self.indents[line_n]
        self.curr_def = groups[1]

        if self.curr_def:
            self.def_context[self.curr_def]['functions'].append(groups[1])  # inline func -> only available in scope.
        elif self.curr_class:
            self.context['methods'].append(groups[1])
            self.class_context[self.curr_class]['methods'].append(groups[1])
        else:
            self.context['functions'].append(groups[1])

        variables = groups[2].split(',')
        LOGGER.debug("Analysing function def variables. Adding {} to def context.".format(variables))

        self.def_context[self.curr_def]['variables'].extend(variables)

    def fix_default(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("No match found for {}. Defaulting to not fixing.".format(groups[0]))
        return groups[0]

    def fix_import(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]
        closest, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import. Changing from {} to {}, and adding to context after analysis.".format(groups[1],
                                                                                                           closest))

        self.context["imports"].append(closest)
        return 'import {}'.format(closest)

    def fix_import_as(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        LOGGER.debug("Fixing import as. Changing from {} to {}, and adding {} "
                     "to context after analysis.".format(groups[1], closest_module, groups[2]))

        self.context["imports"].extend(groups[2])
        return 'import {} as {}'.format(closest_module, groups[2])

    def fix_from_import(self, match, poss_chars):
        groups = match.groups()
        poss_import = poss_chars[match.start(2): match.end(2)]
        closest_module, _ = self.levenshtein_closest(poss_import, stdlib_list("3.6"))
        imported = [i.strip() for i in groups[2].split(",")]
        LOGGER.debug("Fixing from X import Y. Changing from {} to {}, and adding {}"
                     " to context after analysis.".format(groups[1], closest_module, imported))

        self.context["imports"].extend(imported)
        return 'from {} import {}'.format(closest_module, ", ".join(imported))

    def fix_class(self, match, poss_chars):
        groups = match.groups()
        poss_class = poss_chars[match.start(2): match.end(2)]
        closest, _ = self.levenshtein_closest(poss_class, self.context["classes"])
        LOGGER.debug("Fixing class. Changing from {} to {}.".format(groups[1], closest))
        return 'class {}:'.format(closest)

    def fix_if(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing if. From {} to {}.".format(groups[1], stmt))
        return 'if {}:'.format(stmt)

    def fix_elif(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing elif. From {} to {}.".format(groups[1], stmt))
        return 'elif {}:'.format(stmt)

    def fix_return(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing return. From {} to {}.".format(groups[1], stmt))
        return 'return {}'.format(stmt)

    def fix_while(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing while. From {} to {}.".format(groups[1], stmt))
        return 'while {}:'.format(stmt)

    def fix_for(self, match, poss_chars):
        groups = match.groups()

        var = self.fix_variable(CustomMatch(groups[1], match.start(2), match.end(2)),
                                poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing for loop var from {} to {}".format(groups[1], var))

        stmt = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
                                  poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing for loop stmt from {} to {}".format(groups[2], stmt))

        return 'for {} in {}:'.format(var, stmt)

    def fix_for_range(self, match, poss_chars):
        groups = match.groups()
        var = self.fix_variable(CustomMatch(groups[1], match.start(2), match.end(2)),
                                poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing for range loop var from {} to {}".format(groups[1], var))

        stmt = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
                                  poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing for range loop stmt from {} to {}".format(groups[2], stmt))

        return 'for {} in range({}):'.format(var, stmt)

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
        poss_callable = poss_chars[match.start(2): match.end(2)]
        poss_method = poss_chars[match.start(3): match.end(3)]

        if self.curr_def:
            ctxt = self.def_context[self.curr_def]['variables'] + self.context['variables']
        elif self.curr_class:
            ctxt = self.class_context[self.curr_class]['variables'] + self.context['variables']
        else:
            ctxt = self.context['variables']

        closest_var, distance_var = self.levenshtein_closest(poss_callable, ctxt)
        closest_import, distance_import = self.levenshtein_closest(poss_callable, self.context["imports"])

        # Check if its more likely to be a call on a custom variable, or an import.
        if distance_var <= distance_import:
            # is a var -> harder to check method -> TODO?
            closest_callable = closest_var
            LOGGER.debug("Fixing method call var. From {} to {}".format(groups[1], closest_callable))

            closest_method, _ = self.levenshtein_closest(poss_method, self.context["methods"])
            LOGGER.debug("Fixing method call method. From {} to {}".format(groups[2], closest_method))
        else:
            # is an import -> method can be checked if __all__ is present
            # TODO: workaround __all__ not being present
            closest_callable = closest_import
            LOGGER.debug("Method call was found to be on an import!")
            LOGGER.debug("Fixing method call var. From {} to {}".format(groups[1], closest_import))

            imported = importlib.import_module(closest_import)
            if hasattr(imported, "__all__"):
                closest_method, _ = self.levenshtein_closest(poss_method, imported.__all__)
            else:
                closest_method = groups[2]
            del imported

            LOGGER.debug("Fixing method call method. From {} to {}".format(groups[2], closest_method))

        closest_args = self.fix_arguments(groups[3], poss_chars[match.start(4): match.end(4)])

        LOGGER.debug("Fixing method call args. From {} to {}.".format(groups[3], closest_args))

        return '{}.{}({})'.format(closest_callable, closest_method, closest_args)

    def fix_self_method_call(self, match, poss_chars):
        # NOTE: 'self' is group 1, so as to be able to pass it to standard method fixing
        groups = match.groups()
        # Not in class -> shouldn't be self, revert to fixing
        if not self.curr_class:
            return self.fix_method_call(match, poss_chars)

        poss_method = poss_chars[match.start(3): match.end(3)]
        closest_method, _ = self.levenshtein_closest(poss_method, self.class_context[self.curr_class]["methods"])
        LOGGER.debug("Fixing method call method. From {} to {}".format(groups[2], closest_method))

        closest_args = self.fix_arguments(groups[3], poss_chars[match.start(4): match.end(4)])
        LOGGER.debug("Fixing method call args. From {} to {}.".format(groups[3], closest_args))

        return 'self.{}({})'.format(closest_method, closest_args)

    def fix_assignment(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("About to fix RHS of assignment")
        rhs = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
                                 poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing assignment. Using {} = {}.".format(groups[1], rhs))
        return '{} = {}'.format(groups[1], rhs)

    def fix_assert(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing assert. From {} to {}.".format(groups[1], stmt))
        return 'assert {}'.format(stmt)

    def fix_del(self, match, poss_chars):
        groups = match.groups()
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing del. From {} to {}.".format(groups[1], stmt))
        return 'del {}'.format(stmt)

    def fix_raise(self, match, poss_chars):
        groups = match.groups()
        LOGGER.debug("Fixing raise. From {} to {}.".format(*groups[1:]))
        return 'raise {}'.format(*groups[1:])

    def fix_def(self, match, poss_chars):
        groups = match.groups()
        # TODO: set curr scope with the parsed args and rm later.
        LOGGER.debug("Fixing def. Using {} and {}.".format(*groups[1:]))
        return 'def {}({}):'.format(*groups[1:])

    def fix_arguments(self, args, poss_chars):
        arg_matches = self.find_args(args)

        LOGGER.debug("Fixing {} arguments: {}".format(len(arg_matches), arg_matches))
        result = []
        for match in arg_matches:
            new_arg = self.fix_statement(match, poss_chars[match.start(1): match.end(1)])  # when variable.
            LOGGER.debug("Fixing argument {} to {}".format(match.groups()[0], new_arg))
            result.append(new_arg)

        return ", ".join(result)

    def fix_statement(self, match, poss_chars):
        matched, analyze_func, fix_func = self.find_closest_match(poss_chars, self.statements_regexes)

        if fix_func:
            fixed = fix_func(matched, poss_chars)
        else:
            LOGGER.debug("No match for {}. Not fixing.".format(match.groups()[0]))
            fixed = match.groups()[0]

        return fixed

    # TODO: ensure we don't fix non-vars
    def fix_variable(self, match, poss_chars):
        if self.curr_def:
            ctxt = self.def_context[self.curr_def]['variables'] + self.context['variables']
        elif self.curr_class:
            ctxt = self.class_context[self.curr_class]['variables'] + self.context['variables']
        else:
            ctxt = self.context['variables']
        closest, _ = self.levenshtein_closest(poss_chars, ctxt)
        LOGGER.debug("Fixing variable {} to {}.".format(match.groups()[0], closest))
        return closest

    def fix_range_generator(self, match, poss_chars):
        groups = match.groups()

        var = self.fix_variable(CustomMatch(groups[2], match.start(3), match.end(3)),
                                poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing range generator var from {} to {}".format(groups[2], var))

        # NOTE: fix_for returns an extra : so would be invalid.
        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing range generator result from {} to {}".format(groups[0], stmt))

        stmt2 = self.fix_statement(CustomMatch(groups[3], match.start(4), match.end(4)),
                                   poss_chars[match.start(4): match.end(4)])
        LOGGER.debug("Fixing range generator iterator from {} to {}".format(groups[3], stmt2))

        return "{} for {} in range({})".format(stmt, var, stmt2)

    def fix_generator(self, match, poss_chars):
        groups = match.groups()

        stmt = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                  poss_chars[match.start(2): match.end(2)])
        LOGGER.debug("Fixing generator result from {} to {}".format(groups[0], stmt))

        # NOTE: fix_for returns an extra : so would be invalid.
        var = self.fix_variable(CustomMatch(groups[2], match.start(3), match.end(3)),
                                poss_chars[match.start(3): match.end(3)])
        LOGGER.debug("Fixing generator var from {} to {}".format(groups[2], var))

        stmt2 = self.fix_statement(CustomMatch(groups[3], match.start(4), match.end(4)),
                                   poss_chars[match.start(4): match.end(4)])
        LOGGER.debug("Fixing generator iterator from {} to {}".format(groups[3], stmt2))

        return "{} for {} in {}".format(stmt, var, stmt2)

    def fix_range_list_comp(self, match, poss_chars):
        LOGGER.debug("Fixing range list comprehension: {}".format(match.groups()[0]))
        return "[{}]".format(self.fix_range_generator(match, poss_chars[1:len(poss_chars) - 1]))

    def fix_list_comp(self, match, poss_chars):
        LOGGER.debug("Fixing list comprehension: {}".format(match.groups()[0]))
        return "[{}]".format(self.fix_generator(match, poss_chars[1:len(poss_chars) - 1]))

    # def fix_eq(self, match, poss_chars):
    #     groups = match.groups()
    #     stmt1 = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
    #                                poss_chars[match.start(2): match.end(2)])
    #     stmt2 = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
    #                                poss_chars[match.start(3): match.end(3)])
    #
    #     LOGGER.debug("Fixing equality from {} == {} to {} == {}".format(groups[1], groups[2], stmt1, stmt2))
    #     return "{} == {}".format(stmt1, stmt2)
    #
    # def fix_bracketed(self, match, poss_chars):
    #     LOGGER.debug("Fixing bracketed {}".format(match.groups()[0]))
    #     return ""

    def fix_and(self, match, poss_chars):
        groups = match.groups()
        stmt1 = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                   poss_chars[match.start(2): match.end(2)])
        stmt2 = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
                                   poss_chars[match.start(3): match.end(3)])

        LOGGER.debug("Fixing '{} and {}' to '{} and {}'".format(groups[1], groups[2], stmt1, stmt2))
        return "{} and {}".format(stmt1, stmt2)

    def fix_or(self, match, poss_chars):
        groups = match.groups()
        stmt1 = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                   poss_chars[match.start(2): match.end(2)])
        stmt2 = self.fix_statement(CustomMatch(groups[2], match.start(3), match.end(3)),
                                   poss_chars[match.start(3): match.end(3)])

        LOGGER.debug("Fixing '{} or {}' to '{} or {}'".format(groups[1], groups[2], stmt1, stmt2))
        return "{} or {}".format(stmt1, stmt2)

    def fix_not(self, match, poss_chars):
        groups = match.groups()
        stmt1 = self.fix_statement(CustomMatch(groups[1], match.start(2), match.end(2)),
                                   poss_chars[match.start(2): match.end(2)])

        LOGGER.debug("Fixing 'not {}' to 'not {}'".format(groups[1], stmt1))
        return "not {}".format(stmt1)


class CustomMatch(object):
    def __init__(self, arg, start, end):
        self._args = [arg]
        self._start = [start]
        self._end = [end]

    def groups(self):
        return self._args

    def start(self, n):
        return self._start[n - 1]

    def end(self, n):
        return self._end[n - 1]

    def add(self, arg, start, end):
        self._args.append(arg)
        self._start.append(start)
        self._end.append(end)

    def __repr__(self):
        return str(self._args)
