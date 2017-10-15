import logging

import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.word import Word

LOGGER = logging.getLogger()


class Line(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, to_show=None):
        super().__init__(image, x_axis, y_axis, width, height, to_show)
        self._fix_rotation()

        if self.show_line:
            cv2.imshow("Line", self.get_image())
            cv2.waitKey(0)

    def get_code(self):
        words = self._segment_image()
        return self._merge_code(words)

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
            x, y, w, h = cv2.boundingRect(ctr)

            # Getting ROI
            roi = self.get_image()[y:y + h, x:x + w]
            words.append(Word(roi, x, y, w, h, self))

        LOGGER.debug("{} words detected in this line.".format(len(words)))
        return words

    def _merge_code(self, words):
        """
        Merges all of the words into a line of code
        """
        # TODO: Actually do something with the code
        return " ".join(word.get_code() for word in words)  # TODO: join on more than just spaces?
