import cv2

from WLC.image_processing.picture import Picture


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

    def capture(self):
        # camera_id = self._get_device()

        # cap = cv2.VideoCapture(camera_id)
        # ret, frame = cap.read()

        img = cv2.imread('../input.jpg')
        height, width, _ = img.shape
        return Picture(img, 0, 0, width, height)
