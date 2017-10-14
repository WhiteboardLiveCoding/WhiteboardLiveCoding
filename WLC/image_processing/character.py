import cv2

from WLC.image_processing.extended_image import ExtendedImage


class Character(ExtendedImage):
    def __init__(self, image, x, y, w, h):
        super().__init__(image, x, y, w, h)

    def get_code(self):
        # TODO: plugin to tensorflow
        img = self.transform_to_standard()

        # cv2.imshow("char", img)
        # cv2.waitKey(0)

        return ""

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
        img = self.get_image()
        # TODO: transform

        return img
