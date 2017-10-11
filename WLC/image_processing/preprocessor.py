import cv2
import imutils
import numpy as np
from skimage.filters import threshold_adaptive


class Preprocessor:
    def __init__(self):
        pass

    def process(self, extended_image):
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

        screenCnt = None
        edgesFound = False
        for c in contours:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            # Transform only if we can see 4 edges
            if len(approx) == 4:
                screenCnt = approx
                edgesFound = True
                break

        if edgesFound:
            # get top-down view of image
            warped = self.four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)

            # put fancy filters on the image
            warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            warped = threshold_adaptive(warped, 251, offset=10)
            warped = warped.astype("uint8") * 255

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

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def four_point_transform(self, image, pts):
        rect = self.order_points(pts)
        (tl, tr, br, bl) = rect

        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        # compute the perspective transform matrix and then apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        # return the warped image
        return warped
