import sys
import io


class CodeExecutor:
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

        s = code_out.getvalue()

        print("Output:\n{}\n".format(s))

        code_out.close()
        code_err.close()
