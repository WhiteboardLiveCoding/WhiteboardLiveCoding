import argparse

from WLC.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera
from WLC.image_processing.preprocessor import Preprocessor


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

    return show_pic, show_line, show_word, show_character, debug_mode


def main(show_pic=False, show_line=False, show_word=False, show_character=False):
    print("Acquiring Image")
    picture = Camera().capture(show_pic, show_line, show_word, show_character)

    print("Preprocessing Image")
    image = Preprocessor().process(picture)

    print("Obtaining code")
    code = image.get_code().lower()

    CodeExecutor().execute_code(code)

    print("Complete!")


if __name__ == '__main__':
    print("Welcome to Live Whiteboard Coding!")
    main(*arguments())
