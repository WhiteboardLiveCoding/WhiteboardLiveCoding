import argparse
import logging

from WLC.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera
from WLC.image_processing.preprocessor import Preprocessor

FORMAT = '%(levelname)-10s %(message)s'

logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()


def arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--pics", action="store_true", default=False, help="Show pics")
    parser.add_argument("-l", "--lines", action="store_true", default=False, help="Show lines")
    parser.add_argument("-w", "--words", action="store_true", default=False, help="Show words")
    parser.add_argument("-c", "--characters", action="store_true", default=False, help="Show characters")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Run in debug mode")

    args, unknown = parser.parse_known_args()
    show_pic = args.pics
    show_line = args.lines
    show_word = args.words
    show_character = args.characters
    debug_mode = args.debug

    if debug_mode:
        LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug("""Command line arguments parsed:
    - show_pic: %s
    - show_line: %s
    - show_word: %s
    - show_character: %s
    - debug_mode: %s
    """, show_pic, show_line, show_word, show_character, debug_mode)

    return show_pic, show_line, show_word, show_character


def main(show_pic=False, show_line=False, show_word=False, show_character=False):
    LOGGER.info("Acquiring Image")
    picture = Camera().capture(show_pic, show_line, show_word, show_character)

    LOGGER.info("Preprocessing Image")
    image = Preprocessor().process(picture)

    LOGGER.info("Obtaining code")
    code = image.get_code().lower()

    CodeExecutor().execute_code(code)

    LOGGER.info("Complete!")


if __name__ == '__main__':
    LOGGER.setLevel(logging.INFO)
    show_pic, show_line, show_word, show_character = arguments()
    LOGGER.info("Welcome to Live Whiteboard Coding!")
    main(show_pic, show_line, show_word, show_character)
