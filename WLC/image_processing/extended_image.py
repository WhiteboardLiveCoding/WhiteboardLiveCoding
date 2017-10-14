import cv2


class ExtendedImage:
    def __init__(self, image, x_axis, y_axis, width, height, extended_image=None,
                 show_pic=False, show_line=False, show_word=False, show_char=False):
        self._image = image
        self._x_axis = x_axis
        self._y_axis = y_axis
        self._width = width
        self._height = height

        if extended_image:
            if show_pic or show_line or show_word or show_char:
                print("Ignoring show_x variable as extended image was provided")

            self.show_pic = extended_image.show_pic
            self.show_line = extended_image.show_line
            self.show_word = extended_image.show_word
            self.show_char = extended_image.show_char
        else:
            self.show_pic = show_pic
            self.show_line = show_line
            self.show_word = show_word
            self.show_char = show_char

    def save(self, name):
        cv2.imwrite(name, self._image)

    def get_image(self):
        return self._image

    def set_image(self,  image):
        self._image = image

    def get_x(self):
        return self._x_axis

    def get_y(self):
        return self._y

    def get_code(self):
        raise NotImplementedError("get_code not implemented")
