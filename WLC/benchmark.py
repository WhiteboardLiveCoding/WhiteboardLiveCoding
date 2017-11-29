import argparse
import logging
import re
import os

from os.path import isfile, join

from WLC.code_executor.code_executor import CodeExecutor
from WLC.image_processing.camera import Camera
from WLC.utils.formatting import FORMAT
from WLC.utils.path import get_full_path

import editdistance

logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--language", default="all", help="Choose which language to run tests for. Defaults to \
                        all languages")

    args, unknown = parser.parse_known_args()

    return args.language


def _get_expected_code(file_name):
    file_name = file_name.replace('images', 'annotations')
    file_name = re.sub(r"\..*", ".txt", file_name)
    file_name = get_full_path(file_name)

    with open(file_name, 'r') as file:
        return file.read().lower()


def benchmark_file(file_name, language="python3"):
    expected_code = _get_expected_code(file_name)
    picture = Camera().read_file(file_name, None)
    code, fixed_code = CodeExecutor(language).process_picture(picture)

    if 'sign' in file_name:
        fixed_code = code

    difference = editdistance.eval("".join(code.split()), "".join(expected_code.split()))
    difference_fixed = editdistance.eval("".join(fixed_code.lower().split()), "".join(expected_code.split()))

    length = len("".join(expected_code.split()))
    accuracy = round(100 - (difference * 100 / length))
    accuracy_fixed = round(100 - (difference_fixed * 100 / length))

    LOGGER.info('Accuracy w/o fixing: %s%%, Accuracy w/ fixing: %s%%, Fix improvement: %s%%,  File: %s',
                accuracy, accuracy_fixed, accuracy_fixed - accuracy, file_name.split('/')[-1])
    return accuracy, accuracy_fixed, length


def run_benchmarks(language="all"):
    LOGGER.info('=== Whiteboard Live Coding Benchmarking ===')
    LOGGER.info('Uses Levenshtein distance to calculate the difference and then uses that to calculate accuracy.')

    total_accuracy = 0
    total_accuracy_fixed = 0
    total_length = 0

    if language.lower() == "python3" or language.lower() == "all":
        LOGGER.info('')
        LOGGER.info('Testing Python3 code:')
        python_directory = get_full_path('assets/examples/images/python3/')

        for file in (f for f in os.listdir(python_directory) if isfile(join(python_directory, f)) and not f.startswith(".")):
            file_path = join(python_directory, file)
            accuracy, accuracy_fixed, length = benchmark_file(file_path, "python3")

            total_accuracy += accuracy * length
            total_accuracy_fixed += accuracy_fixed * length
            total_length += length

    if language.lower() == "haskell" or language.lower() == "all":
        LOGGER.info('')
        LOGGER.info('Testing Haskell code:')
        haskell_directory = get_full_path('assets/examples/images/haskell/')
        for file in (f for f in os.listdir(haskell_directory) if
                     isfile(join(haskell_directory, f)) and not f.startswith(".")):
            file_path = join(haskell_directory, file)
            accuracy, accuracy_fixed, length = benchmark_file(file_path, "haskell")

            total_accuracy += accuracy * length
            total_accuracy_fixed += accuracy_fixed * length
            total_length += length

    overall_accuracy = round(total_accuracy / total_length, 2) if total_length else 0
    overall_accuracy_fixed = round(total_accuracy_fixed / total_length, 2) if total_length else 0

    LOGGER.info('')
    LOGGER.info('Overall Accuracy w/o fix: %s%%', overall_accuracy)
    LOGGER.info('Overall Accuracy w/ fix: %s%%', overall_accuracy_fixed)
    LOGGER.info('Fix improvement: %s%%', round(overall_accuracy_fixed - overall_accuracy, 2))
    LOGGER.info('Code length: %s', total_length)

    return overall_accuracy_fixed


if __name__ == '__main__':
    language = arguments()
    LOGGER.setLevel(logging.INFO)
    run_benchmarks(language)
