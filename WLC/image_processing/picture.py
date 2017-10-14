import sys

import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.line import Line


class Picture(ExtendedImage):
    INDENTATION_THRESHOLD = 50

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
        indent = self._determine_indentation(lines)
        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line.get_code())
                         for indent, line in zip(indent, lines))

    def _determine_indentation(self, lines):
        if not lines:
            return []

        indents = list()
        indent_locations = list()

        indents.append(0)
        indent_locations.append([lines[0].get_x()])

        for line in lines[1:]:
            if self._is_before_first_indent(line, indent_locations):
                indent_locations[0].append(line.get_x())
                indents.append(0)
            elif self._is_after_last_indent(line, indent_locations):
                indent_locations.append([line.get_x()])
                indents.append(len(indent_locations) - 1)
            else:
                indentation = self._get_closest_indentation(line, indent_locations)

                if indentation is not None:
                    indent_locations[indentation].append(line.get_x())
                    indents.append(indentation)
                else:
                    raise ValueError("Could not determine indentation")

        return indents

    def _is_before_first_indent(self, line, indent_locations):
        return line.get_x() < np.mean(indent_locations[0]) - self.INDENTATION_THRESHOLD

    def _is_after_last_indent(self, line, indent_locations):
        return line.get_x() > np.mean(indent_locations[-1]) + self.INDENTATION_THRESHOLD

    def _get_closest_indentation(self, line, indent_locations):
        distance = sys.maxsize
        indentation = None

        for i in range(len(indent_locations)):
            if abs(np.mean(indent_locations[i]) - line.get_x()) < distance:
                distance = abs(np.mean(indent_locations[i]) - line.get_x())
                indentation = i

        return indentation

# show images with:
# cv2.imshow('file', img)
# cv2.waitKey(0)
