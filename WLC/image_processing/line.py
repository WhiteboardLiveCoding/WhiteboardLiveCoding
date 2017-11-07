import logging

import cv2
import numpy as np

from ..image_processing.extended_image import ExtendedImage
from ..image_processing.word import Word


LOGGER = logging.getLogger()

HEIGHT_DILATION_MODIFIER = 1.5
WIDTH_DILATION_MODIFIER = 0.75


class Line(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)

        self.words = []
        self._fix_rotation()

        if self.preferences and self.preferences.show_line:
            cv2.imshow("Line", self.get_image())
            cv2.waitKey(0)

    def get_code(self):
        self.words = self._segment_image()
        return self._merge_code(self.words)

    def _segment_image(self):
        points, used_contours = self.get_center_points(self.get_image())
        average_distance, standard_deviation = self.average_node_distance(points)

        height = int(average_distance * HEIGHT_DILATION_MODIFIER)
        width = int(average_distance * WIDTH_DILATION_MODIFIER)

        # dilation
        kernel = np.ones((height, width), np.uint8)
        img = cv2.dilate(self.get_image(), kernel, iterations=1)

        # find contours
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        words = list()
        previous_x = -1000

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            if height * width > 5 * 5 and abs(x_axis - previous_x) > 10:

                # Getting ROI
                roi = self.get_image()[0:self.get_height(), x_axis:x_axis + width]

                min_y, max_y = self._truncate_black_borders(roi)
                roi = roi[min_y:max_y]

                words.append(Word(roi, x_axis, y_axis, width, max_y - min_y, average_distance, self.preferences))
                previous_x = x_axis

        LOGGER.debug("%d words detected in this line.", len(words))
        return words

    def _merge_code(self, words):
        """
        Merges all of the words into a line of code
        """

        coded_words = []
        word_variances = {}
        for idx, word in enumerate(words):
            code_word, poss_chars = word.get_code()

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
