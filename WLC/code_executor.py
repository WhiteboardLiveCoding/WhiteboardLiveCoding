import logging
import sys
import io

LOGGER = logging.getLogger()


class CodeExecutor:
    def __init__(self):
        pass

    def execute_code(self, code):
        LOGGER.info("Executing code: \n{}\n".format(code))

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

            LOGGER.info("Output:\n{}\n".format(s))
