import filecmp
import logging
import os
from math import floor, ceil

import cv2
from os.path import isfile, join, dirname

import re

from WLC.image_processing.extended_image import ExtendedImage
from WLC.ocr.ocr import OCR

# the MNIST standard image size.
STD_IMAGE_SIZE = 28
LOGGER = logging.getLogger()

LOWEST_ALLOWED_CHAR = 33
HIGHEST_ALLOWED_CHAR = 126


class Character(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences):
        super().__init__(image, x_axis, y_axis, width, height, preferences)
        self.ocr = OCR()
        self._fix_rotation()

    def get_code(self):
        img = self.transform_to_standard()

        return self.ocr.predict(img)

    def _annotate(self, res):
        """
        This will show the image on the screen and ask the user to enter the character which is shown, this image will
        be then saved to a directory with the name of the character. Later these saved images will be used for training
        the neural network. The image should be first transformed to standard.
        """
        cv2.imshow("Character", res)
        dec = cv2.waitKey(0)

        if LOWEST_ALLOWED_CHAR <= dec <= HIGHEST_ALLOWED_CHAR:
            proj_path = dirname(dirname(dirname(__file__)))  # 3 dirs up. Change this if proj structure is modified.
            directory = join(proj_path, 'assets/characters/{}'.format(dec))

            if not os.path.exists(directory):
                os.makedirs(directory)

            files = [f for f in os.listdir(directory) if isfile(join(directory, f))]

            temp = '{}/temp.png'.format(directory)
            cv2.imwrite(temp, res)

            exists = False
            for file in files:
                if filecmp.cmp(temp, '{}/{}'.format(directory, file)):
                    exists = True

            if exists:
                os.remove(temp)
            else:
                if files:
                    max_file = max(list(map(lambda x: self.extract_file_number(x, '.png'), files)))
                else:
                    max_file = 0

                name = '{}/{}.png'.format(directory, str(max_file + 1))
                os.rename(temp, name)

    def transform_to_standard(self):
        """
        The image should be transformed into standard width and height (eg. 28px - the MNIST standard size). This is
        done so that we can use neural networks to figure out the letter
        """
        LOGGER.debug("Resizing character to fit to standard.")
        res = self._resize()

        # cv2.imshow('resized', img)
        # cv2.waitKey(0)

        if self.preferences and self.preferences.annotate:
            self._annotate(res)

        return res

    def _resize(self):
        """
        Re-sizes the image into 28x28px without stretching and pads the image with black border.
        """
        img = self.get_image()

        maximum_dimension = max(self.get_width(), self.get_height())

        top = floor((maximum_dimension - self.get_height()) / 2)
        bottom = ceil((maximum_dimension - self.get_height()) / 2)
        left = floor((maximum_dimension - self.get_width()) / 2)
        right = ceil((maximum_dimension - self.get_width()) / 2)

        res = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
        res = cv2.resize(res, (STD_IMAGE_SIZE, STD_IMAGE_SIZE))

        if self.preferences and self.preferences.show_char:
            # cv2.imshow("Original Character", img)
            cv2.imshow("Resized Character", res)
            cv2.waitKey(0)

        return res

    def extract_file_number(self, file_name, suffix):
        s = re.findall("\d+{}$".format(suffix), file_name)
        if s:
            return int(s[0].replace(suffix, ''))
        else:
            return 0
