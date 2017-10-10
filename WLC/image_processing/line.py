import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.word import Word


class Line(ExtendedImage):
    def __init__(self, image, x, y, w, h):
        super().__init__(image, x, y, w, h)

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
            words.append(Word(roi, x, y, w, h))

        return words

    def _merge_code(self, words):
        """
        Merges all of the words into a line of code
        """
        # TODO: Actually do something with the code
        for word in words:
            word.get_code()

        return ""