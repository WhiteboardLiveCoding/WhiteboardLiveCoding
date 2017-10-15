import logging

import cv2
import imutils
import numpy as np
from skimage.filters import threshold_adaptive

LOGGER = logging.getLogger()


class Preprocessor:
    def __init__(self):
        pass

    def process(self, extended_image):
        LOGGER.debug("Processing image")
        image = extended_image.get_image()

        ratio = image.shape[0] / 500.0
        orig = image.copy()
        image = imutils.resize(image, height=500)

        # Detect edges
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)

        # Create contour around board/paper
        (_, contours, _) = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        screen_cnt = None
        edges_found = False
        for cntour in contours:
            # approximate the contour
            peri = cv2.arcLength(cntour, True)
            approx = cv2.approxPolyDP(cntour, 0.02 * peri, True)

            # Transform only if we can see 4 edges
            if len(approx) == 4:
                screen_cnt = approx
                edges_found = True
                LOGGER.debug("Edges found!")
                break

        if edges_found:
            LOGGER.debug("Reshaping image to get top-down view")
            # get top-down view of image
            warped = self.four_point_transform(orig, screen_cnt.reshape(4, 2) * ratio)

            # put fancy filters on the image
            warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            warped = threshold_adaptive(warped, 251, offset=10)
            warped = warped.astype("uint8") * 255

            if extended_image.show_pics:
                cv2.imshow("Original", imutils.resize(orig, height=650))
                cv2.imshow("Scanned", imutils.resize(warped, height=650))
                cv2.waitKey(0)
        else:
            # Else we do our usual stuff
            image = extended_image.get_image()
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # These 2 lines are highly experimental, they make font "bolder"
            # gray_image = threshold_adaptive(gray_image, 251, offset=10)
            # gray_image = gray_image.astype("uint8") * 255

            ret, gray_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY_INV)

            extended_image.set_image(gray_image)
        return extended_image

    # HELPERS BELOW FOR ANGLED SCREEN TRANSFORMATION, EXTRACT SOMEWHERE

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")

        sum_ = pts.sum(axis=1)
        rect[0] = pts[np.argmin(sum_)]
        rect[2] = pts[np.argmax(sum_)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def four_point_transform(self, image, pts):
        rect = self.order_points(pts)
        (top_left, top_right, bottom_right, bottom_left) = rect

        width_a = np.sqrt(((bottom_right[0] - bottom_left[0]) ** 2) + ((bottom_right[1] - bottom_left[1]) ** 2))
        width_b = np.sqrt(((top_right[0] - top_left[0]) ** 2) + ((top_right[1] - top_left[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((top_right[0] - bottom_right[0]) ** 2) + ((top_right[1] - bottom_right[1]) ** 2))
        height_b = np.sqrt(((top_left[0] - bottom_left[0]) ** 2) + ((top_left[1] - bottom_left[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")

        # compute the perspective transform matrix and then apply it
        transform_matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))

        # return the warped image
        return warped
