import json
import re
import tempfile
import traceback

import os
from pylint import epylint as lint

from ..code_fixing.python_code_fixer import PythonCodeFixer
from ..code_executor.executor_error import ExecutorError
from ..code_executor.redirected_std import redirected_std
from ..code_executor.abstract_executor import AbstractCodeExecutor, LOGGER


class PythonExecutor(AbstractCodeExecutor):
    def __init__(self, ip="", port=""):
        super().__init__("python3", PythonCodeFixer, ip, port)

    def execute_local(self, code):
        LOGGER.info("Executing locally (UNSAFE! use -ip parameter to run the code safely) . . .\n")

        stdout_prog = ""

        with redirected_std() as out:
            try:
                exec(code)
                stdout_prog = out.str_stdout
            except:
                pass

        if not stdout_prog:
            stdout_prog = self.NO_OUTPUT

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog

    def execute_sandbox(self, code):
        LOGGER.info("Executing in sandbox . . .\n")
        container = self.client.containers.run('python', 'python -c \"{}\"'.format(code), detach=True)
        container.wait()

        stdout_prog = container.logs(stdout=True).decode("utf-8")

        if not stdout_prog:
            stdout_prog = self.NO_OUTPUT

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, ExecutorError()

    def get_code_errors(self, code):
        file_code = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
        file_code.write(code.encode('utf8'))
        file_code.close()

        (pylint_stdout, _) = lint.py_run(
            command_options=file_code.name.replace("\\", "/") + " -E -r n -f json", return_std=True)

        os.unlink(file_code.name)

        if pylint_stdout.getvalue():
            return json.loads(pylint_stdout.getvalue())
