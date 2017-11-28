import logging
import re
import traceback

import docker
import os
from hackerrank.HackerRankAPI import HackerRankAPI

from ..utils.azure import WLCAzure
from ..ocr.picture_ocr import PictureOCR
from ..code_executor.executor_error import ExecutorError
from ..code_executor.redirected_std import redirected_std
from ..code_fixing.codefixer import CodeFixer

from image_segmentation.preprocessor import Preprocessor

LOGGER = logging.getLogger()

DEFAULT_DOCKER_PORT = "2375"


class CodeExecutor:
    NO_OUTPUT = "Program did not generate any output!"

    def __init__(self, ip="", port=""):
        if ip and port:
            self.client = docker.DockerClient(base_url="tcp://{}:{}".format(ip, port))
            self.force_local = False
        else:
            self.force_local = True

    def process_picture(self, picture_in):
        image = Preprocessor().process(picture_in)
        code, indents, poss_lines = PictureOCR(image).get_code()
        code = code.lower()
        fixed_code = CodeFixer(code, indents, poss_lines).fix()

        return code, fixed_code

    def execute_code_img(self, picture_in):
        code, fixed_code = self.process_picture(picture_in)

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

    def execute_tests(self, code, test_key):
        azure = WLCAzure()
        template_code, test_cases, expected_responses = azure.get_tests_from_azure(test_key)
        return self._execute_hacker_rank(template_code.format(code), test_cases, expected_responses)

    def _execute_hacker_rank(self, code, test_cases, expected_responses):
        if 'HACKER_RANK_KEY' not in os.environ:
            raise ValueError('HACKER_RANK_KEY not provided')

        compiler = HackerRankAPI(api_key=os.environ['HACKER_RANK_KEY'])

        result = compiler.run({
            'source': code,
            'lang': 'python3',
            'testcases': test_cases
        })

        results = []

        for i in range(len(test_cases)):
            results.append({'passed': result.output[i] == expected_responses[i], 'output': result.output[i]})

        return result

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
            e = self.parse_error(error_string)
            return self.NO_OUTPUT, e

        if not stdout_prog:
            stdout_prog = self.NO_OUTPUT

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, ExecutorError()

    def execute_sandbox(self, code):
        LOGGER.info("Executing in sandbox . . .\n")
        container = self.client.containers.run('python', 'python -c \"{}\"'.format(code), detach=True)
        container.wait()

        stdout_prog = container.logs(stdout=True).decode("utf-8")
        stderr_prog = container.logs(stderr=True).decode("utf-8")

        error_match, _ = self.find_error(stderr_prog)
        if error_match:
            error_parsed = self.parse_error(stderr_prog)
            return self.NO_OUTPUT, error_parsed

        if not stdout_prog:
            stdout_prog = self.NO_OUTPUT

        LOGGER.info("Output:\n%s\n", stdout_prog)
        return stdout_prog, ExecutorError()

    def find_error(self, err):
        start_point = err.find("<string>")
        if start_point == -1:
            start_point = 0

        match = re.search("[A-Za-z]+Error:", err[start_point:])

        return match, start_point

    def parse_error(self, err):
        match, start_point = self.find_error(err)

        error_type = "<unknown>"
        error_line = -1
        error_column = -1

        if match:
            error_type = match.group(0)
            match = re.search("line ([0-9]+)", err[start_point:])
            if match:
                error_line = match.group(1)
            else:
                LOGGER.info("Could not parse error, error string: \n%s\n", err)

            # only some errors contain column
            match = re.search("(\s*)\^", err[start_point:])
            if match:
                error_column = len(match.group(1))

        else:
            LOGGER.info("Could not parse error, error string: \n%s\n", err)

        error = ExecutorError(error_type, int(error_line), int(error_column))
        LOGGER.info("Execution failed with: %s\n", str(error))

        return error
