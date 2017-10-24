import logging

import cv2

from WLC.image_processing.character import Character
from WLC.image_processing.extended_image import ExtendedImage

LOGGER = logging.getLogger()

CHARACTER_SEPARATION = 5
CHARACTER_DIMENSION = 5
MAXIMUM_OVERLAP = 0.5


class Word(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)

        if self.preferences and self.preferences.show_word:
            cv2.imshow("Word", image)
            cv2.waitKey(0)

    def get_code(self):
        characters = self._segment_image()
        return self._merge_code(characters)

    def _segment_image(self):
        # find contours
        im2, ctrs, hier = cv2.findContours(self.get_image(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        characters = list()
        previous_x = -1000
        previous_width = 1

        for i, ctr in enumerate(sorted_ctrs):
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            if self._should_be_separated(previous_x, previous_width, x_axis, height, width):
                roi = self.get_image()[0:self.get_height(), x_axis:x_axis + width]

                min_y, max_y = self._truncate_black_borders(roi)
                roi = roi[min_y:max_y]

                characters.append(Character(roi, x_axis, y_axis, width, max_y - min_y, self.preferences))
                previous_x = x_axis
                previous_width = width

        LOGGER.debug("%d characters found in this word.", len(characters))
        return characters

    def _truncate_black_borders(self, img):
        results = list(map(lambda row: sum(row), img))

        min_y = next(x[0] for x in enumerate(results) if x[1] > 0)
        max_y = next(x[0] for x in enumerate(reversed(results)) if x[1] > 0)

        return min_y, len(results)-max_y

    def _merge_code(self, characters):
        """
        Merges all of the words into a line of code

        :param characters: List of characters to parse
        :return:
        """

        coded_chars = []
        char_variances = {}
        for idx, char in enumerate(characters):
            code_char, other_poss_chars = char.get_code()

            char_variances[idx] = other_poss_chars
            coded_chars.append(code_char)

        return "".join(coded_chars), char_variances

    def _should_be_separated(self, previous_x, previous_width, x_axis, height, width):
        separate = height * width > CHARACTER_DIMENSION ** 2 and abs(x_axis - previous_x) > CHARACTER_SEPARATION

        if not separate:
            return False
        if previous_x + previous_width < x_axis:
            return True
        elif (previous_x + previous_width - x_axis) / previous_width < MAXIMUM_OVERLAP:
            return True

        return False
