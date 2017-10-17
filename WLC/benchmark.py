import logging
import re

from WLC.image_processing.camera import Camera
from WLC.image_processing.preprocessor import Preprocessor

import editdistance

from WLC.utils.formatting import FORMAT

logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger()


def _get_expected_code(file_name):
    file_name = file_name.replace('images', 'annotations')
    file_name = re.sub(r"\..*", ".txt", file_name)
    file_name = Camera().get_full_path(file_name)

    with open(file_name, 'r') as file:
        return file.read().lower()


def benchmark_file(file_name):
    expected_code = _get_expected_code(file_name)
    picture = Camera().read_file(file_name, None)
    image = Preprocessor().process(picture)
    code = image.get_code().lower()
    difference = editdistance.eval("".join(code.split()), "".join(expected_code.split()))
    accuracy = round(100 - (difference * 100 / len(expected_code)))
    LOGGER.info('Accuracy: {}%, File: {}'.format(accuracy, file_name))


def run_benchmarks():
    LOGGER.info('=== Whiteboard Live Coding Benchmarking ===')
    LOGGER.info('Uses Levenshtein distance to calculate the difference and then uses that to calculate accuracy.')
    LOGGER.info('')

    for i in range(1, 6):
        benchmark_file('assets/examples/images/example_{}.png'.format(i))


if __name__ == '__main__':
    LOGGER.setLevel(logging.INFO)
    run_benchmarks()
