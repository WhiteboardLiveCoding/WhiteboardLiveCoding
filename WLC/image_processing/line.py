import logging

import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.word import Word

LOGGER = logging.getLogger()


class Line(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)
        self._fix_rotation()

        if self.preferences and self.preferences.show_line:
            cv2.imshow("Line", self.get_image())
            cv2.waitKey(0)

    def get_code(self, contextual_data=None):
        words = self._segment_image()
        return self._merge_code(words, contextual_data)

    def _segment_image(self):
        # dilation
        kernel = np.ones((20, 20), np.uint8)
        img = cv2.dilate(self.get_image(), kernel, iterations=1)

        # find contours
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        words = list()

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            # Getting ROI
            roi = self.get_image()[y_axis:y_axis + height, x_axis:x_axis + width]
            words.append(Word(roi, x_axis, y_axis, width, height, self.preferences))

        LOGGER.debug("%d words detected in this line.", len(words))
        return words

    def _merge_code(self, words, contextual_data=None):
        """
        Merges all of the words into a line of code
        """
        if not contextual_data:
            contextual_data = []

        # line = ""
        word_list = []
        for word in words:
            prev_word = word_list[-1] if word_list else None

            prev_context = prev_word if prev_word in ["def", "class", "=", "import"] else False
            code = word.get_code(contextual_data, prev_context)

            if prev_word == "class" or prev_word == "def":
                contextual_data.append(code.split(":")[0].split("(")[0])  # split on "(" to lose the args on a function

            if prev_word == "=":
                contextual_data.append(word_list[-2] if len(word_list) > 2 else None)

            word_list.append(code)

        line = " ".join(word_list)

        # If any of these, I expect it to end with a colon
        # NOTE: this is currently hardcoding; not interesting.
        # if any(line.startswith(b) for b in ["class", "def", "if", "for"]) and line.endswith("i"):
        #     line = line[:-1] + ":"

        return line, contextual_data
