import sys
from io import StringIO


class redirected_std:
    def __init__(self):
        self.orig_stdout = None
        self.orig_stderr = None
        self.new_stdout = None
        self.new_stderr = None

    def __enter__(self):
        self.orig_stdout = sys.stdout
        sys.stdout = self.new_stdout = StringIO()
        self.orig_stderr = sys.stderr
        sys.stderr = self.new_stderr = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr

    @property
    def str_stdout(self):
        return self.new_stdout.getvalue()

    @property
    def str_stderr(self):
        return self.new_stderr.getvalue()