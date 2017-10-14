import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.line import Line


class Picture(ExtendedImage):
    def __init__(self, image, x, y, w, h):
        super().__init__(image, x, y, w, h)

    def get_code(self):
        lines = self._segment_image(self.get_image())
        return self._merge_code(lines)

    def _segment_image(self, gray_image):
        # dilation
        kernel = np.ones((5, 20), np.uint8)
        img = cv2.dilate(gray_image, kernel, iterations=1)

        kernel = np.ones((8, 8), np.uint8)
        img = cv2.erode(img, kernel, iterations=1)

        kernel = np.ones((1, 100), np.uint8)
        img = cv2.dilate(img, kernel, iterations=1)

        # find contours
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        lines = list()

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x, y, w, h = cv2.boundingRect(ctr)

            # Getting ROI
            roi = gray_image[y:y + h, x:x + w]
            lines.append(Line(roi, x, y, w, h))

        return lines

    def _merge_code(self, lines):
        """
        Should return a string with the code from all of the lines, this function will also have to figure out how far
        each line is indented.
        """
        # TODO: Actually do something with the code

        return "\n".join(line.get_code() for line in lines)  # Note: joining on newlines

# show images with:
# cv2.imshow('file', img)
# cv2.waitKey(0)
