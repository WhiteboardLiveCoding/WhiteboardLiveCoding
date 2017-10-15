import logging
from os.path import dirname, join

import cv2

from WLC.image_processing.extended_image import ToShow
from WLC.image_processing.picture import Picture

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

        camera_id -= 1

        if camera_id < 0:
            raise Exception('No camera found')

        self._camera_id = camera_id
        return camera_id

    def capture(self, show_pic=False, show_line=False, show_word=False, show_character=False):
        LOGGER.debug("Capturing image")

        # camera_id = self._get_device()

        # cap = cv2.VideoCapture(camera_id)
        # ret, frame = cap.read()

        proj_path = dirname(dirname(dirname(__file__)))  # 3 dirs up. Change this if proj structure is modified.
        input_path = join(proj_path, "assets/basic/basic_1.jpg")
        img = cv2.imread(input_path)
        height, width, _ = img.shape
        to_show = ToShow(show_pic, show_line, show_word, show_character)
        return Picture(img, 0, 0, width, height, to_show)
