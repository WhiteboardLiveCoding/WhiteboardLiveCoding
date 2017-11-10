import logging

import sys

import numpy as np

from ..ocr.ocr import OCR

LOGGER = logging.getLogger()


class PictureOCR:
    def __init__(self, picture):
        self.picture = picture
        self.ocr = OCR()
        self.indentation_threshold = None

    def get_code(self):
        lines = self.picture.get_segments()
        self.indentation_threshold = self.picture.get_indentation_threshold()
        return self._merge_code_lines(lines)

    def _merge_code_lines(self, lines):
        """
        Should return a string with the code from all of the lines, this function will also have to figure out how far
        each line is indented.
        """
        indents = self._determine_indentation(lines)

        coded_lines = []
        lines_variations = {}
        for idx, (indent, line) in enumerate(zip(indents, lines)):
            words = line.get_segments()
            code_line, poss_words = self._merge_code_words(words)

            lines_variations[idx] = poss_words
            coded_lines.append("{indent}{code}".format(indent="  " * indent, code=code_line))

        return "\n".join(coded_lines), indents, lines_variations

    def _determine_indentation(self, lines):
        """
        Returns a list of indentation distances for each line
        """
        if not lines:
            return []

        indents = []
        indent_locations = []

        indents.append(0)
        indent_locations.append([lines[0].get_x()])

        for line_n, line in enumerate(lines[1:]):
            if self._is_before_first_indent(line, indent_locations):
                indent_locations[0].append(line.get_x())
                indentation = 0

            elif self._is_after_last_indent(line, indent_locations):
                indent_locations.append([line.get_x()])
                indentation = len(indent_locations) - 1

            else:
                indentation = self._get_closest_indentation(line, indent_locations)

                if indentation is not None:
                    indent_locations[indentation].append(line.get_x())

                else:
                    raise ValueError("Could not determine indentation")

            LOGGER.debug("Indentation of %d detected on line %d.", indentation, line_n)
            indents.append(indentation)
        return indents

    def _is_before_first_indent(self, line, indent_locations):
        """
        Returns whether this line is indented less than the currently least indented line.
        """
        return line.get_x() < np.mean(indent_locations[0]) - self.indentation_threshold

    def _is_after_last_indent(self, line, indent_locations):
        """
        Returns whether this line is indented further than the currently most indented line.
        """
        return line.get_x() > np.mean(indent_locations[-1]) + self.indentation_threshold

    def _get_closest_indentation(self, line, indent_locations):
        """
        Returns how far the line should be indented based on looking at other lines and finding the closest match.
        """
        distance = sys.maxsize
        indentation = None

        for idx, indent in enumerate(indent_locations):
            if abs(np.mean(indent) - line.get_x()) < distance:
                distance = abs(np.mean(indent) - line.get_x())
                indentation = idx

        return indentation

    def _merge_code_words(self, words):
        """
        Merges all of the words into a line of code
        """

        coded_words = []
        word_variances = {}
        for idx, word in enumerate(words):
            characters = word.get_segments()
            code_word, poss_chars = self._merge_code_characters(characters)

            word_variances[idx] = poss_chars
            coded_words.append(code_word)

        return " ".join(coded_words), self.join_words(word_variances)

    def join_words(self, poss_lines):
        joined = list()

        for word in range(len(poss_lines)):
            for j in range(len(poss_lines[word])):
                joined.append(poss_lines[word][j])

            if word < len(poss_lines) - 1:
                joined.append([' '])

        return joined

    def _merge_code_characters(self, characters):
        """
        Merges all of the words into a line of code

        :param characters: List of characters to parse
        :return:
        """

        coded_chars = []
        char_variances = {}
        for idx, char in enumerate(characters):
            image = char.get_segments()
            code_char, other_poss_chars = self.ocr.predict(image)

            char_variances[idx] = other_poss_chars
            coded_chars.append(code_char)

        return "".join(coded_chars), char_variances
