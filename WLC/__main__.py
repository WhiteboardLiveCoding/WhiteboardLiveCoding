from WLC.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera
from WLC.image_processing.preprocessor import Preprocessor


def main():
    picture = Camera().capture()
    image = Preprocessor().process(picture)
    code = image.get_code()
    CodeExecutor().execute_code(code)


if __name__ == '__main__':
    print("Welcome to Live Whiteboard Coding!")
    main()
