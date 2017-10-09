import cv2
import numpy as np

from character import Character


class Word:
    def __init__(self, gray_image, x, y, w, h):
        self._gray_image = gray_image
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    def get_code(self):
        characters = self._segment_image()
        return self._merge_code(characters)

    def _segment_image(self):
        # dilation
        kernel = np.ones((20, 2), np.uint8)
        img = cv2.dilate(self._gray_image, kernel, iterations=1)

        # find contours
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        words = list()

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x, y, w, h = cv2.boundingRect(ctr)

            # Getting ROI
            roi = self._gray_image[y:y + h, x:x + w]
            words.append(Character(roi, x, y, w, h))

        return words

    def _merge_code(self, characters):
        """
        Merges all of the words into a line of code
        """
        # ToDo: Actually do something with the code
        for character in characters:
            character.get_code()

        return ""
