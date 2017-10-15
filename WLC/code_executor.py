import io
import sys


class CodeExecutor:
    def __init__(self):
        pass

    def execute_code(self, code):
        print("Executing code: \n{}\n".format(code))

        code_out = io.StringIO()
        code_err = io.StringIO()

        sys.stdout = code_out
        sys.stderr = code_err

        exec(code)

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        s = code_err.getvalue()

        print("Error:\n{}\n".format(s))

        code_res = code_out.getvalue()

        print("Output:\n{}\n".format(code_res))
