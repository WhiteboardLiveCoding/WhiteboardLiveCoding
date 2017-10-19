from WLC.benchmark import run_benchmarks

MINIMUM_ACCURACY = 45


def test_benchmarks():
    accuracy = run_benchmarks()
    assert accuracy > MINIMUM_ACCURACY
