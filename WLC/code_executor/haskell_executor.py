from WLC.code_fixing.haskell_code_fixer import HaskellCodeFixer
from ..code_executor.abstract_executor import AbstractCodeExecutor


class HaskellExecutor(AbstractCodeExecutor):
    def __init__(self, ip="", port=""):
        super().__init__("haskell", HaskellCodeFixer, ip, port)

    def execute_local(self, code):
        raise NotImplemented()

    def execute_sandbox(self, code):
        raise NotImplemented()

    def get_code_errors(self, code):
        raise NotImplemented()
