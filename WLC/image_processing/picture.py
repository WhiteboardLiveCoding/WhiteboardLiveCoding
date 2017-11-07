import logging

import cv2
import numpy as np

from ..image_processing.extended_image import ExtendedImage
from ..image_processing.line import Line

LOGGER = logging.getLogger()


class Picture(ExtendedImage):
    INDENTATION_THRESHOLD = 50
    ARTIFACT_PERCENTAGE_THRESHOLD = 0.08
    MINIMUM_LINE_OVERLAP = 0.25

    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)

        self.lines = []
        self.indentation_threshold = self.INDENTATION_THRESHOLD

        if self.preferences and self.preferences.show_pic:
            cv2.imshow("Full picture", image)
            cv2.waitKey(0)

    def get_line_coordinates(self, n):
        if 0 > n or n > len(self.lines):
            return []

        line = self.lines[n - 1]
        return line.get_bounding_coordinates()

    def get_segments(self):
        self.lines = self._segment_image(self.get_image())
        LOGGER.debug("Getting code for the %d lines detected.", len(self.lines))
        return self.lines

    def get_indentation_threshold(self):
        return self.indentation_threshold

    def _segment_image(self, gray_image):
        lines = []
        img = self.get_contoured(gray_image)

        sorted_ctrs = self._find_contours(img)
        sorted_ctrs = self._merge_subcontours(sorted_ctrs)

        # Get average height and width of all lines
        average_width = sum(cv2.boundingRect(ctr)[2] for i, ctr in enumerate(sorted_ctrs)) / len(sorted_ctrs)
        average_height = sum(cv2.boundingRect(ctr)[3] for i, ctr in enumerate(sorted_ctrs)) / len(sorted_ctrs)

        for i, ctr in enumerate(sorted_ctrs):
            # Get bounding box
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            # Discard lines which have a very small width or height (based on the threshold)
            if width < (average_width * self.ARTIFACT_PERCENTAGE_THRESHOLD) or \
               height < (average_height * self.ARTIFACT_PERCENTAGE_THRESHOLD):
                continue

            roi = gray_image[y_axis:y_axis + height, x_axis:x_axis + width]
            mask = self._get_mask(img, sorted_ctrs, i)[y_axis:y_axis + height, x_axis:x_axis + width]

            result = cv2.bitwise_and(roi, roi, mask=mask)

            if len(self._find_contours(result)) >= 2:
                lines.append(Line(result, x_axis, y_axis, width, height, self.preferences))

        # Sort lines based on y offset
        lines = sorted(lines, key=lambda line: line.get_y())
        LOGGER.debug("%d lines detected.", len(lines))
        return lines

    def _get_mask(self, img, contours, contour_index):
        mask = np.zeros_like(img)
        cv2.drawContours(mask, contours, contour_index, 255, -1)
        return mask

    def get_contoured(self, gray_image):
        img = np.copy(gray_image)

        points, used_contours = self.get_center_points(gray_image)
        average_distance, standard_deviation = self.average_node_distance(points)

        self.indentation_threshold = average_distance
        horizontal_distance = int(1.5 * average_distance + 2 * standard_deviation)

        for ctr, point in zip(used_contours, points):
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)
            x_center, y_center = point[0], point[1]

            minimum_height = round(0.9 * min(y_center - y_axis, y_axis + height - y_center))

            cv2.rectangle(
                img,
                (x_center - horizontal_distance, y_center - minimum_height),
                (x_center + horizontal_distance, y_center + minimum_height),
                (255, 255, 255),
                -1
            )

        return img

    def _merge_subcontours(self, sorted_ctrs):
        merged = []
        for i, ctr in enumerate(sorted_ctrs):
            x1, y1, width1, height1 = cv2.boundingRect(ctr)

            remove = None
            add = True

            for merged_ctr in merged:
                x2, y2, width2, height2 = cv2.boundingRect(merged_ctr)

                if (x1 <= x2 and y1 <= y2 and x1 + width1 >= x2 + width2 and y1 + height1 >= y2 + height2) or \
                        (y1 < y2 < y1 + height1 and (y1 + height1 - y2) / height1 > self.MINIMUM_LINE_OVERLAP):
                    merged.append(np.concatenate((ctr, merged_ctr), axis=0))
                    remove = merged_ctr
                    add = False
                    break

            if add:
                merged.append(ctr)
            else:
                merged = [x for x in merged if x.shape != remove.shape or not np.equal(x, remove).all()]

        return merged
