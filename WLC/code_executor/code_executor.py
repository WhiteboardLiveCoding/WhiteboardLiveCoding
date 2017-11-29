from ..code_executor.haskell_executor import HaskellExecutor
from ..code_executor.python_executor import PythonExecutor


class CodeExecutor:
    def __init__(self, language="python3", ip="", port=""):
        if language.lower() == "haskell":
            self.executor = HaskellExecutor(ip, port)
        elif language.lower() == "python3":
            self.executor = PythonExecutor(ip, port)
        else:
            raise Exception("Unsupported CodeExecutor language.")

    def process_picture(self, picture_in):
        return self.executor.process_picture(picture_in)

    def execute_code_img(self, picture_in):
        return self.executor.execute_code_img(picture_in)

    def execute_code(self, code):
        return self.executor.execute_code(code)

    def execute_tests(self, code, test_key):
        return self.executor.execute_tests(code, test_key)

    def execute_local(self, code):
        return self.executor.execute_local(code)

    def execute_sandbox(self, code):
        return self.executor.execute_sandbox(code)
