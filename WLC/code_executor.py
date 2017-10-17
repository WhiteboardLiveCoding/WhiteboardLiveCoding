import io
import logging
import sys

LOGGER = logging.getLogger()


class CodeExecutor:
    def __init__(self):
        pass

    def execute_code(self, code):
        LOGGER.info("Executing code: \n%s\n", code)

        with io.StringIO() as code_out:
            sys.stdout = code_out

            try:
                exec(code)
            except:
                LOGGER.exception("An error was raised!")
            else:
                LOGGER.info("No errors occurred.")

            sys.stdout = sys.__stdout__

            s = code_out.getvalue()

            LOGGER.info("Output:\n%s\n", s)
