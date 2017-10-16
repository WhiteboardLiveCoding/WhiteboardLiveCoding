import logging
import sys

import cv2
import numpy as np

from WLC.image_processing.extended_image import ExtendedImage
from WLC.image_processing.line import Line

LOGGER = logging.getLogger()


class Picture(ExtendedImage):
    INDENTATION_THRESHOLD = 50
    ARTIFACT_PERCENTAGE_THRESHOLD = 0.08

    def __init__(self, image, x_axis, y_axis, width, height, to_show=None):
        super().__init__(image, x_axis, y_axis, width, height, to_show)
        if self.show_pic:
            cv2.imshow("Full picture", image)
            cv2.waitKey(0)

    def get_code(self):
        lines = self._segment_image(self.get_image())
        LOGGER.debug("Getting code for the %d lines detected.", len(lines))
        return self._merge_code(lines)

    def _segment_image(self, gray_image):
        img = self._prepare_for_contouring(gray_image)
        sorted_ctrs = self._find_contours(img)

        lines = list()

        # Get average height and width of all lines
        average_width = sum(cv2.boundingRect(ctr)[2] for i, ctr in enumerate(sorted_ctrs)) / len(sorted_ctrs)
        average_height = sum(cv2.boundingRect(ctr)[3] for i, ctr in enumerate(sorted_ctrs)) / len(sorted_ctrs)

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x, y, w, h = cv2.boundingRect(ctr)

            # Discard lines which have a very small width or height (based on the threshold)
            if w < (average_width * self.ARTIFACT_PERCENTAGE_THRESHOLD) or \
               h < (average_height * self.ARTIFACT_PERCENTAGE_THRESHOLD):
                continue

            roi = gray_image[y:y + h, x:x + w]
            mask = self._get_mask(img, sorted_ctrs, i)[y:y + h, x:x + w]

            result = cv2.bitwise_and(roi, roi, mask=mask)

            lines.append(Line(result, x, y, w, h, self))

        # Sort lines based on y offset
        lines = sorted(lines, key=lambda line: line.get_y())
        LOGGER.debug("%d lines detected.", len(lines))
        return lines

    def _prepare_for_contouring(self, gray_image):
        kernel = np.ones((5, 20), np.uint8)
        img = cv2.dilate(gray_image, kernel, iterations=1)

        kernel = np.ones((8, 8), np.uint8)
        img = cv2.erode(img, kernel, iterations=1)

        kernel = np.ones((1, 100), np.uint8)
        img = cv2.dilate(img, kernel, iterations=1)

        return img

    def _find_contours(self, img):
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

    def _get_mask(self, img, contours, contour_index):
        mask = np.zeros_like(img)
        cv2.drawContours(mask, contours, contour_index, 255, -1)
        return mask

    def _merge_code(self, lines):
        """
        Should return a string with the code from all of the lines, this function will also have to figure out how far
        each line is indented.
        """
        indent = self._determine_indentation(lines)
        return "\n".join("{indent}{code}".format(indent="  " * indent, code=line.get_code())
                         for indent, line in zip(indent, lines))

    def _determine_indentation(self, lines):
        """
        Returns a list of indentation distances for each line
        """
        if not lines:
            return []

        indents = list()
        indent_locations = list()

        indents.append(0)
        indent_locations.append([lines[0].get_x()])

        for line_n, line in enumerate(lines):
            if self._is_before_first_indent(line, indent_locations):
                indent_locations[0].append(line.get_x())
                indentation = 0

            elif self._is_after_last_indent(line, indent_locations):
                indent_locations.append([line.get_x()])
                indentation = len(indent_locations) - 1

            else:
                indentation = self._get_closest_indentation(line, indent_locations)

                if indentation is not None:
                    indent_locations[indentation].append(line.get_x())

                else:
                    raise ValueError("Could not determine indentation")

            LOGGER.debug("Indentation of %d detected on line %d.", indentation, line_n)
            indents.append(indentation)
        return indents

    def _is_before_first_indent(self, line, indent_locations):
        """
        Returns whether this line is indented less than the currently least indented line.
        """
        return line.get_x() < np.mean(indent_locations[0]) - self.INDENTATION_THRESHOLD

    def _is_after_last_indent(self, line, indent_locations):
        """
        Returns whether this line is indented further than the currently most indented line.
        """
        return line.get_x() > np.mean(indent_locations[-1]) + self.INDENTATION_THRESHOLD

    def _get_closest_indentation(self, line, indent_locations):
        """
        Returns how far the line should be indented based on looking at other lines and finding the closest match.
        """
        distance = sys.maxsize
        indentation = None

        for i in range(len(indent_locations)):
            if abs(np.mean(indent_locations[i]) - line.get_x()) < distance:
                distance = abs(np.mean(indent_locations[i]) - line.get_x())
                indentation = i

        return indentation
