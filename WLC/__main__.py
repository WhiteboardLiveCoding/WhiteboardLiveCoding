import argparse
import logging
import tkinter as tk

from WLC.code_executor.abstract_executor import DEFAULT_DOCKER_PORT
from WLC.code_executor.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera
from WLC.utils.formatting import FORMAT
from WLC.utils.gui import Gui

logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()


def arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-g", "--gui", action="store_true", default=False, help="Show gui")
    parser.add_argument("-p", "--pics", action="store_true", default=False, help="Show pics")
    parser.add_argument("-l", "--lines", action="store_true", default=False, help="Show lines")
    parser.add_argument("-w", "--words", action="store_true", default=False, help="Show words")
    parser.add_argument("-c", "--characters", action="store_true", default=False, help="Show characters")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Run in debug mode")
    parser.add_argument("-ip", "--dockerip", help="Docker daemon IP")
    parser.add_argument("-a", "--annotate", action="store_true", default=False, help="Ask user to annotate images")

    args, unknown = parser.parse_known_args()
    show_gui = args.gui
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
    - show_gui: %s
    - show_pic: %s
    - show_line: %s
    - show_word: %s
    - show_character: %s
    - debug_mode: %s
    - docker_ip: %s
    - annotate: %s
    """, show_gui, show_pic, show_line, show_word, show_character, debug_mode, docker_ip, annotate)

    return show_gui, show_pic, show_line, show_word, show_character, docker_ip, annotate


def main():

    show_gui, show_pic, show_line, show_word, show_character, docker_ip, annotate = arguments()

    picture_path = None

    if show_gui:
        LOGGER.info("Setting up GUI of the application")
        root = tk.Tk()
        root.geometry("1200x1000")
        app = Gui(root)
        picture_path = app.get_picture()

    LOGGER.info("Acquiring Image")
    picture = Camera().capture(show_pic, show_line, show_word, show_character, picture_path, annotate)

    if show_gui:
        app.save_picture(picture)
        app.save_docker_ip(docker_ip)
        app.display_picture(picture_path)

        LOGGER.info("Image loaded, waiting for execute click")
        app.init_button()
        app.mainloop()

    else:
        CodeExecutor("python3", docker_ip, DEFAULT_DOCKER_PORT).execute_code_img(picture)


if __name__ == '__main__':
    LOGGER.setLevel(logging.INFO)
    LOGGER.info("Welcome to Live Whiteboard Coding!")

    main()

