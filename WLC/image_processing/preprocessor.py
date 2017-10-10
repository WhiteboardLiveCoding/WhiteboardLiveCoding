import cv2


class Preprocessor:
    def __init__(self):
        pass

    def process(self, extended_image):
        image = extended_image.get_image()

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, gray_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY_INV)

        extended_image.set_image(gray_image)
        return extended_image