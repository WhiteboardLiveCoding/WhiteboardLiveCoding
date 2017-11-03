import logging
import re
import traceback

import docker

from WLC.code_executor.executor_error import ExecutorError, PY_STR_ERR_SYNTAX
from WLC.code_executor.redirected_std import redirected_std
from WLC.code_fixing.trial_codefixer import TrialCodeFixer
from WLC.image_processing.preprocessor import Preprocessor

LOGGER = logging.getLogger()

DEFAULT_DOCKER_PORT = "2375"


class CodeExecutor:
    def __init__(self, ip="", port=""):
        if ip and port:
            self.client = docker.DockerClient(base_url="tcp://{}:{}".format(ip, port))
            self.force_local = False
        else:
            self.force_local = True

    def execute_code_img(self, picture_in):
        image = Preprocessor().process(picture_in)
        code, indents, poss_lines = image.get_code()
        code = code.lower()
        fixed_code = TrialCodeFixer(code, indents, poss_lines).fix()

        LOGGER.info("Unfixed code OCRd from image: \n%s\n", code)

        result, error = self.execute_code(fixed_code)

        return code, fixed_code, result, error

    def execute_code(self, code):
        LOGGER.info("Executing code: \n%s\n", code)

        if self.force_local:
            result, error = self.execute_local(code)
        else:
            result, error = self.execute_sandbox(code)

        return result, error

    def execute_local(self, code):
        LOGGER.info("Executing locally (UNSAFE! use -ip parameter to run the code safely) . . .\n")

        error_string = None
        stdout_prog = ""

        with redirected_std() as out:
            try:
                exec(code)
                stdout_prog = out.str_stdout
            except:
                error_string = traceback.format_exc()

        if error_string:
            e = self.check_error(error_string)
            if e:
                return "", e

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, None

    def execute_sandbox(self, code):
        LOGGER.info("Executing in sandbox . . .\n")
        container = self.client.containers.run('python', 'python -c \"{}\"'.format(code), detach=True)
        container.wait()

        stdout_prog = container.logs(stdout=True).decode("utf-8")
        stderr_prog = container.logs(stderr=True).decode("utf-8")

        e = self.check_error(stderr_prog)
        if e:
            return "", e

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, None

    def check_error(self, err):
        start_point = err.find("<string>")
        if start_point == -1:
            start_point = 0

        if err.find(PY_STR_ERR_SYNTAX) != -1:
            match = re.search("line ([0-9]+)", err[start_point:])
            if match:
                line = match.group(1)
            else:
                line = -1
                LOGGER.info("Could not parse error, error string: \n%s\n", err)
            e = ExecutorError(ExecutorError.ERROR_TYPE_SYNTAX, line)
            LOGGER.info("Execution failed with error: %s\n", str(e))

            return e

        return None
