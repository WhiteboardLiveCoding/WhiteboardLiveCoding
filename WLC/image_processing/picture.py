import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.line import Line


class Picture(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, extended_image=None,
                 show_pic=False, show_line=False, show_word=False, show_char=False):
        super().__init__(image, x_axis, y_axis, width, height, extended_image,
                         show_pic, show_line, show_word, show_char)
        if self.show_pic:
            cv2.imshow("Full picture", image)
            cv2.waitKey(0)

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
            lines.append(Line(roi, x, y, w, h, self))

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
