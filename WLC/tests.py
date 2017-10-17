from unittest import TestCase

from WLC.benchmark import run_benchmarks

MINIMUM_ACCURACY = 45


class BenchmarkTest(TestCase):
    def testBenchmarks(self):
        accuracy = run_benchmarks()
        self.assertGreater(accuracy, MINIMUM_ACCURACY)
