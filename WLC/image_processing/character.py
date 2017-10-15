import logging
from math import floor, ceil

import cv2

from WLC.image_processing.extended_image import ExtendedImage
from WLC.ocr.ocr import OCR

# the MNIST standard image size.
STD_IMAGE_SIZE = 28
LOGGER = logging.getLogger()


class Character(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, to_show):
        super().__init__(image, x_axis, y_axis, width, height, to_show)
        self.ocr = OCR()

        if self.show_char:
            cv2.imshow("Character", image)
            cv2.waitKey(0)

    def get_code(self):
        img = self.transform_to_standard()

        return self.ocr.predict(img)

    def classify(self):
        """
        This will show the image on the screen and ask the user to enter the character which is shown, this image will
        be then saved to a directory with the name of the character. Later these saved images will be used for training
        the neural network. The image should be first transformed to standard.
        """
        img = self.transform_to_standard()

        LOGGER.warning("Classifying hasnt been implemented yet!")

        # TODO: actually classify

        pass

    def transform_to_standard(self):
        """
        The image should be transformed into standard width and height (eg. 28px - the MNIST standard size). This is
        done so that we can use neural networks to figure out the letter
        """
        LOGGER.debug("Resizing character to fit to standard.")
        img = self._resize()

        # cv2.imshow('resized', img)
        # cv2.waitKey(0)

        return img

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

        if self.show_char:
            # cv2.imshow("Original Character", img)
            cv2.imshow("Resized Character", res)
            cv2.waitKey(0)

        return res
