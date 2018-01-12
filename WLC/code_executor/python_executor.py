import tempfile
import os
from pylint import lint

from ..code_executor.pylint_reporter import CustomJSONReporter
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
        return stdout_prog, self._get_code_errors(code)

    def execute_sandbox(self, code):
        LOGGER.info("Executing in sandbox . . .\n")
        container = self.client.containers.run('python', 'python -c \'{}\''.format(code), detach=True)
        container.wait()

        stdout_prog = container.logs(stdout=True).decode("utf-8")

        if not stdout_prog or "File" in stdout_prog:
            stdout_prog = self.NO_OUTPUT

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, self._get_code_errors(code)

    def _get_code_errors(self, code):
        file_code = tempfile.NamedTemporaryFile(delete=False, suffix='.py')
        file_code.write(code.encode('utf8'))
        file_code.close()

        json_reporter = CustomJSONReporter()
        linter = lint.PyLinter(reporter=json_reporter)
        linter.load_default_plugins()
        linter.error_mode()

        linter.check(file_code.name.replace('\\', '/'))

        os.unlink(file_code.name)

        return json_reporter.get_errors_json()
