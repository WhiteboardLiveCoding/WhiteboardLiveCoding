import logging

import docker
import os
from hackerrank.HackerRankAPI import HackerRankAPI
from image_segmentation.preprocessor import Preprocessor

from ..utils.azure import WLCAzure
from ..ocr.picture_ocr import PictureOCR

LOGGER = logging.getLogger()

DEFAULT_DOCKER_PORT = "2375"


class AbstractCodeExecutor:
    NO_OUTPUT = "Program did not generate any output!"

    def __init__(self, language, fixer, ip="", port=""):
        self.language = language
        self.fixer = fixer
        self.force_local = True

        self.client = docker.DockerClient(base_url="tcp://{}:{}".format("13.92.175.199", "2375"))
        self.force_local = False

    def process_picture(self, picture_in):
        image = Preprocessor().process(picture_in)
        code, indents, poss_lines = PictureOCR(image).get_code()
        code = code.lower()
        fixed_code = self.fixer(code, indents, poss_lines).fix()

        return code, fixed_code

    def execute_code_img(self, picture_in):
        code, fixed_code = self.process_picture(picture_in)

        LOGGER.info("Unfixed code recognized from image: \n%s\n", code)
        result, errors = self.execute_code(fixed_code)

        LOGGER.info("Errors: \n%s\n", errors)
        return code, fixed_code, result, errors

    def execute_code(self, code):
        LOGGER.info("Executing code: \n%s\n", code)

        if self.force_local:
            result, errors = self.execute_local(code)
        else:
            result, errors = self.execute_sandbox(code)

        return result, errors

    def execute_tests(self, code, test_key):
        azure = WLCAzure()
        template_code, test_cases, expected_responses, hints = azure.get_tests_from_azure(test_key)
        return self._execute_hacker_rank(template_code.format(code), test_cases, expected_responses, hints)

    def _execute_hacker_rank(self, code, test_cases, expected_responses, hints):
        if 'HACKER_RANK_KEY' not in os.environ:
            raise ValueError('HACKER_RANK_KEY not provided')

        compiler = HackerRankAPI(api_key=os.environ['HACKER_RANK_KEY'])

        result = compiler.run({
            'source': code,
            'lang': self.language,
            'testcases': test_cases
        })

        results = []

        for i in range(len(test_cases)):
            results.append({'passed': result.output[i] == expected_responses[i], 'hint': hints[i]})

        return results

    def execute_local(self, code):
        raise NotImplemented()

    def execute_sandbox(self, code):
        raise NotImplemented()
