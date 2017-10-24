import logging
from os.path import dirname, join

import cv2

from WLC.image_processing.extended_image import Preferences
from WLC.image_processing.picture import Picture
from WLC.utils.path import get_full_path

LOGGER = logging.getLogger()


class Camera:
    _camera_id = None

    def __init__(self):
        pass

    def _get_device(self):
        """
        Gets the camera with the highest ID
        """
        if self._camera_id:
            return self._camera_id

        camera_id = 0

        while True:
            cap = cv2.VideoCapture(camera_id)
            ret, frame = cap.read()

            if frame is None:
                break

            camera_id += 1

        if camera_id < 0:
            raise Exception('No camera found')

        self._camera_id = camera_id
        return camera_id

    def read_file(self, file_name, to_show):
        input_path = get_full_path(file_name)
        img = cv2.imread(input_path)
        height, width, _ = img.shape
        return Picture(img, 0, 0, width, height, to_show)

    def capture(self, show_pic=False, show_line=False, show_word=False, show_character=False, image_path="",
                annotate=False):
        LOGGER.debug("Capturing image")
        # camera_id = self._get_device()

        # cap = cv2.VideoCapture(camera_id)
        # ret, frame = cap.read()

        to_show = Preferences(show_pic, show_line, show_word, show_character, annotate)

        if not image_path:
            image_path = 'assets/examples/images/shade_1.png'

        return self.read_file(image_path, to_show)
