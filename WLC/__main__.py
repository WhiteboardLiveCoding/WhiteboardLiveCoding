import argparse
import logging

from WLC.code_executor import CodeExecutor, DEFAULT_DOCKER_PORT
from WLC.code_fixing.codefixer import CodeFixer
from WLC.image_processing.camera import Camera
from WLC.image_processing.preprocessor import Preprocessor
from WLC.utils.formatting import FORMAT

logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()


def arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--pics", action="store_true", default=False, help="Show pics")
    parser.add_argument("-l", "--lines", action="store_true", default=False, help="Show lines")
    parser.add_argument("-w", "--words", action="store_true", default=False, help="Show words")
    parser.add_argument("-c", "--characters", action="store_true", default=False, help="Show characters")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Run in debug mode")
    parser.add_argument("-ip", "--dockerip", help="Docker daemon IP")
    parser.add_argument("-a", "--annotate", action="store_true", default=False, help="Ask user to annotate images")

    args, unknown = parser.parse_known_args()
    show_pic = args.pics
    show_line = args.lines
    show_word = args.words
    show_character = args.characters
    debug_mode = args.debug
    docker_ip = args.dockerip
    annotate = args.annotate

    if debug_mode:
        LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug("""Command line arguments parsed:
    - show_pic: %s
    - show_line: %s
    - show_word: %s
    - show_character: %s
    - debug_mode: %s
    - docker_ip: %s
    - annotate: %s
    """, show_pic, show_line, show_word, show_character, debug_mode, docker_ip, annotate)

    return show_pic, show_line, show_word, show_character, docker_ip, annotate


def main(show_pic=False, show_line=False, show_word=False, show_character=False, docker_ip="", annotate=False):
    executor = CodeExecutor(docker_ip, DEFAULT_DOCKER_PORT)

    LOGGER.info("Acquiring Image")
    picture = Camera().capture(show_pic, show_line, show_word, show_character, annotate)

    LOGGER.info("Preprocessing Image")
    image = Preprocessor().process(picture)

    LOGGER.info("Obtaining code")
    code, indents, poss_lines = image.get_code()  # TODO: use poss_lines variations to fix code
    code = code.lower()

    LOGGER.info("Unfixed code: \n%s\n", code)

    fixed_code = CodeFixer(code, indents).fix()

    executor.execute_code(fixed_code)

    LOGGER.info("Complete!")


if __name__ == '__main__':
    LOGGER.setLevel(logging.INFO)
    LOGGER.info("Welcome to Live Whiteboard Coding!")

    show_pic, show_line, show_word, show_character, docker_ip, annotate = arguments()
    main(show_pic, show_line, show_word, show_character, docker_ip, annotate)

