import cv2


class ExtendedImage:
    def __init__(self, image, x, y, w, h):
        self._image = image
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    def save(self, name):
        cv2.imwrite(name, self._image)

    def get_image(self):
        return self._image

    def set_image(self,  image):
        self._image = image

    def get_x(self):
        return self._x

    def get_code(self):
        raise NotImplementedError("get_code not implemented")