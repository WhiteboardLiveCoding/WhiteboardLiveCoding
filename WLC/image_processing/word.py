import cv2
import numpy as np

from WLC.image_processing.character import Character
from WLC.image_processing.extended_image import ExtendedImage


class Word(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, to_show=None):
        super().__init__(image, x_axis, y_axis, width, height, to_show)

        if self.show_word:
            cv2.imshow("Word", image)
            cv2.waitKey(0)

    def get_code(self):
        characters = self._segment_image()
        return self._merge_code(characters)

    def _segment_image(self):
        # dilation
        kernel = np.ones((20, 2), np.uint8)
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
            words.append(Character(roi, x_axis, y_axis, width, height, self))

        return words

    def _merge_code(self, characters):
        """
        Merges all of the words into a line of code
        """
        # TODO: Actually do something with the code
        return "".join(character.get_code() for character in characters)
