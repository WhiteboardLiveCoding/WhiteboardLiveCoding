import cv2


class ExtendedImage:
    def __init__(self, image, x_axis, y_axis, width, height, to_show):
        self._image = image
        self._x_axis = x_axis
        self._y_axis = y_axis
        self._width = width
        self._height = height

        if to_show:
            self.show_pic = to_show.show_pic
            self.show_line = to_show.show_line
            self.show_word = to_show.show_word
            self.show_char = to_show.show_char
        else:
            self.show_pic = False
            self.show_line = False
            self.show_word = False
            self.show_char = False

        self.to_show = to_show  # for passing to others

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

    def get_code(self):
        raise NotImplementedError("get_code not implemented")

class ToShow:
    def __init__(self, show_pic=False, show_line=False, show_word=False, show_char=False):
        self.show_pic = show_pic
        self.show_line = show_line
        self.show_word = show_word
        self.show_char = show_char
