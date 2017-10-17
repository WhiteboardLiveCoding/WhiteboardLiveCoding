import keyword
import logging
import sys

import cv2
from fuzzysearch import find_near_matches

from WLC.image_processing.character import Character
from WLC.image_processing.extended_image import ExtendedImage

LOGGER = logging.getLogger()

KW_LIST = keyword.kwlist + ["print", "list", "dict", "set", "file", "open", "assert", "main"]


class Word(ExtendedImage):
    def __init__(self, image, x_axis, y_axis, width, height, preferences=None):
        super().__init__(image, x_axis, y_axis, width, height, preferences)

        if self.preferences and self.preferences.show_word:
            cv2.imshow("Word", image)
            cv2.waitKey(0)

    def get_code(self):
        characters = self._segment_image()
        return self._merge_code(characters)

    def _segment_image(self):
        # find contours
        im2, ctrs, hier = cv2.findContours(self.get_image(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # sort contours
        sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])

        characters = list()
        previous_x = sys.maxsize

        for i, ctr in enumerate(sorted_ctrs):
            x_axis, y_axis, width, height = cv2.boundingRect(ctr)

            if height * width > 5 * 5 and abs(x_axis - previous_x) > 10:
                roi = self.get_image()[0:self.get_height(), x_axis:x_axis + width]

                min_y, max_y = self._truncate_black_borders(roi)
                roi = roi[min_y:max_y]

                characters.append(Character(roi, x_axis, y_axis, width, height, self.preferences))
                previous_x = x_axis

        LOGGER.debug("%d characters found in this word.", len(characters))
        return characters

    def _truncate_black_borders(self, img):
        results = list(map(lambda row: sum(row), img))

        min_y = next(x[0] for x in enumerate(results) if x[1] > 0)
        max_y = next(x[0] for x in enumerate(reversed(results)) if x[1] > 0)

        return min_y, len(results)-max_y

    def _merge_code(self, characters):
        """
        Merges all of the words into a line of code
        """
        # TODO: Actually do something with the code
        word = "".join(character.get_code().lower() for character in characters)

        start = 0
        end = 0
        curr_best_match = None
        curr_best_word = None

        for kw in KW_LIST:
            pos = find_near_matches(kw, word, max_l_dist=min(2, len(kw) - 1), max_insertions=0, max_deletions=0)

            for p in pos or []:
                if p.start == 0:
                    # start = pos[0].start  # always 0
                    if end < p.end:
                        end = p.end
                        curr_best_match = p
                        curr_best_word = kw
                        # print(curr_best_word)

        if curr_best_match and curr_best_word:
            new_word = word[:start] + curr_best_word + word[end:]
            # print("Replace {} with {}".format(word, new_word))
            word = new_word
        return word