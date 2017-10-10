from WLC.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera


def main():
    picture = Camera().capture()
    code = picture.get_code()
    CodeExecutor().execute_code(code)


if __name__ == '__main__':
    print("Welcome to Live Whiteboard Coding!")
    main()
