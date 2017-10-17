import logging

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

    def get_code(self, contextual_data=None):
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


class Preferences:
    def __init__(self, show_pic=False, show_line=False, show_word=False, show_char=False, annotate=False):
        self.show_pic = show_pic
        self.show_line = show_line
        self.show_word = show_word
        self.show_char = show_char
        self.annotate = annotate
