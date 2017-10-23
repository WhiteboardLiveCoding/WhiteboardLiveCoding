import logging
import sys

import cv2

from WLC.image_processing.character import Character
from WLC.image_processing.extended_image import ExtendedImage
from WLC.code_fixing.context import word_context_analysis

LOGGER = logging.getLogger()


class Word(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)

        if self.preferences and self.preferences.show_word:
            cv2.imshow("Word", image)
            cv2.waitKey(0)

    def get_code(self, contextual_data=None, prev_context=False):
        characters = self._segment_image()
        return self._merge_code(characters, contextual_data, prev_context)

    def _segment_image(self):
        # find contours
        im2, ctrs, hier = cv2.findContours(self.get_image(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        characters = list()
        previous_x = sys.maxsize

        for i, ctr in enumerate(sorted_ctrs):
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            if height * width > 5 * 5 and abs(x_axis - previous_x) > 10:
                roi = self.get_image()[0:self.get_height(), x_axis:x_axis + width]

                min_y, max_y = self._truncate_black_borders(roi)
                roi = roi[min_y:max_y]

                characters.append(Character(roi, x_axis, y_axis, width, height, self.preferences))
                previous_x = x_axis

        LOGGER.debug("%d characters found in this word.", len(characters))
        return characters

    def _truncate_black_borders(self, img):
        results = list(map(lambda row: sum(row), img))

        min_y = next(x[0] for x in enumerate(results) if x[1] > 0)
        max_y = next(x[0] for x in enumerate(reversed(results)) if x[1] > 0)

        return min_y, len(results)-max_y

    def _merge_code(self, characters, contextual_data=None, prev_context=False):
        """
        Merges all of the words into a line of code

        :param characters: List of characters to parse
        :param contextual_data: Contextual data - eg class names, assignments, or function names
        :param prev_context: whether there is a previous context
        :return:
        """

        return word_context_analysis(characters, contextual_data, prev_context)
