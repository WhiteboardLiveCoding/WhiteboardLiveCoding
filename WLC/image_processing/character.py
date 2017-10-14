from math import floor, ceil

import cv2

from WLC.image_processing.extended_image import ExtendedImage
from WLC.ocr.ocr import OCR

# the MNIST standard image size.
STD_IMAGE_SIZE = 28


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

        # TODO: actually classify

        pass

    def transform_to_standard(self):
        """
        The image should be transformed into standard width and height (eg. 28px - the MNIST standard size). This is
        done so that we can use neural networks to figure out the letter
        """
        img = self._resize()

        cv2.imshow('resized', img)
        cv2.waitKey(0)

        return img

    def _resize(self):
        """
        Re-sizes the image into 28x28px without stretching and pads the image with black border.
        """
        img = self.get_image()

        maximum_dimension = max(self.get_width(), self.get_height())
        scale = STD_IMAGE_SIZE / maximum_dimension

        scaled_width = floor(self.get_width() * scale)
        scaled_height = floor(self.get_height() * scale)

        res = cv2.resize(img, (scaled_width, scaled_height))

        top = floor((STD_IMAGE_SIZE - scaled_height) / 2)
        bottom = ceil((STD_IMAGE_SIZE - scaled_height) / 2)
        left = floor((STD_IMAGE_SIZE - scaled_width) / 2)
        right = ceil((STD_IMAGE_SIZE - scaled_width) / 2)

        res = cv2.copyMakeBorder(res, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])

        if self.show_char:
            # cv2.imshow("Original Character", img)
            cv2.imshow("Resized Character", res)
            cv2.waitKey(0)

        return res
