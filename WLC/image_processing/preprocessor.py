import cv2
import logging


LOGGER = logging.getLogger()


class Preprocessor:
    def __init__(self):
        pass

    def process(self, extended_image):
        LOGGER.debug("Processing image")
        image = extended_image.get_image()

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_image = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 115,
                                           60)

        gray_image = self._remove_noise(gray_image)

        extended_image.set_image(gray_image)
        return extended_image

    def _remove_noise(self, img):
        proc = img.copy()
        height, width = proc.shape

        biggest_dimension = max(height, width)
        scale = 800 / biggest_dimension
        proc = cv2.resize(proc, (round(width * scale), round(height * scale)))

        proc = cv2.fastNlMeansDenoising(proc, None, 30, 7, 21)
        se1 = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
        proc = cv2.dilate(proc, se1)

        proc = cv2.threshold(proc, 127, 255, cv2.THRESH_BINARY)[1]
        proc = cv2.resize(proc, (width, height))

        result = cv2.bitwise_and(img, img, mask=proc)

        return result
