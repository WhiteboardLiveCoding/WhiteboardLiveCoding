import logging
import sys
from itertools import tee
from math import log, floor, ceil

import editdistance
import regex

LOGGER = logging.getLogger()


class CodeFixer:
    PERMUTATION_LENGTH = 3
    ALLOWED_DIFFERENCE = 0.25

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
                perm_count *= len(poss_chars[i][:self.PERMUTATION_LENGTH])

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
            current_perm_length = self.PERMUTATION_LENGTH
        else:
            current_perm_length = floor(10 ** (log(perm_cap, 10) / perm_count))

        if len(poss_chars[0]) == 1:
            permutations = self.generate_permutation_strings(poss_chars[1:], perm_cap, perm_count, perm_length)
        else:
            new_cap = perm_cap / len(poss_chars[0][:current_perm_length])
            new_count = perm_count / len(poss_chars[0][:self.PERMUTATION_LENGTH])
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
            difference = max(ceil(fixed * self.ALLOWED_DIFFERENCE), 0)
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
