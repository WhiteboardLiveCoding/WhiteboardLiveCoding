import cv2

from picture import Picture


class Camera:
    def capture(self):
        return Picture(cv2.imread('input.jpg'))
