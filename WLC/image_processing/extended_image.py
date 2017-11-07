import logging
import math

import cv2
import numpy as np

LOGGER = logging.getLogger()


class ExtendedImage:
    MAX_ROTATE = 20

    def __init__(self, image, x_axis, y_axis, width, height, preferences):
        self._image = image
        self._x_axis = x_axis
        self._y_axis = y_axis
        self._width = width
        self._height = height

        self.preferences = preferences  # for passing to others

    def save(self, name):
        cv2.imwrite(name, self._image)

    def get_image(self):
        return self._image

    def set_image(self, image):
        self._image = image

    def get_x(self):
        return self._x_axis

    def get_y(self):
        return self._y_axis

    def get_height(self):
        return self._height

    def get_width(self):
        return self._width

    def get_center_points(self, gray_image):
        sorted_ctrs = self._find_contours(gray_image)

        points = []
        used_contours = []

        for ctr in sorted_ctrs:
            point = self._get_center_of_contour(ctr)

            if point:
                points.append(point)
                used_contours.append(ctr)

        return points, used_contours

    def get_bounding_coordinates(self):
        x = self.get_x()
        y = self.get_y()
        width = self.get_width()
        height = self.get_height()

        return [(x, y), (x + width, y), (x + width, y), (x + width, y + height)]

    def _get_center_of_contour(self, ctr):
        moment = cv2.moments(ctr)

        if moment["m00"]:
            cX = int(moment["m10"] // moment["m00"])
            cY = int(moment["m01"] // moment["m00"])

            return cX, cY

        return None

    def _find_contours(self, img):
        im2, ctrs, hier = cv2.findContours(img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

    def average_node_distance(self, nodes):
        if len(nodes) < 2:
            return 0, 0

        distances = [math.sqrt(self.closest_node(n, nodes)) for n in nodes]
        return np.mean(distances), np.std(distances)

    def closest_node(self, node, nodes):
        nodes = np.asarray(nodes)
        deltas = nodes - node
        dist_2 = np.einsum('ij,ij->i', deltas, deltas)
        return np.partition(dist_2, 1)[1]

    def get_segments(self):
        """Get the code from the current image. This may require recursively checking child elements."""
        raise NotImplementedError("get_code not implemented")

    def _fix_rotation(self):
        angle = self._calculate_skewed_angle(self._image)

        if abs(angle) < self.MAX_ROTATE:
            self._image = self._rotate_image(self._image, angle)
            self._height, self._width = self._image.shape

    def _calculate_skewed_angle(self, img):
        coords = np.column_stack(np.where(img > 0))
        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            return -(90 + angle)
        else:
            return -angle

    def _rotate_image(self, img, angle):
        # Pad image so that you don't have 'drag' lines when rotating
        img = cv2.copyMakeBorder(img, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        # Calculate center, the pivot point of rotation
        (height, width) = img.shape[:2]
        center = (width // 2, height // 2)

        # Rotate
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(img, rot_matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _truncate_black_borders(self, img):
        results = list(map(lambda row: sum(row), img))

        min_y = next(x[0] for x in enumerate(results) if x[1] > 0)
        max_y = next(x[0] for x in enumerate(reversed(results)) if x[1] > 0)

        return min_y, len(results) - max_y


class Preferences:
    def __init__(self, show_pic=False, show_line=False, show_word=False, show_char=False, annotate=False):
        self.show_pic = show_pic
        self.show_line = show_line
        self.show_word = show_word
        self.show_char = show_char
        self.annotate = annotate
