import re
import tempfile

import os
from subprocess import Popen, PIPE

from ..code_fixing.haskell_code_fixer import HaskellCodeFixer
from ..code_executor.abstract_executor import AbstractCodeExecutor


class HaskellExecutor(AbstractCodeExecutor):
    def __init__(self, ip="", port=""):
        super().__init__("haskell", HaskellCodeFixer, ip, port)

    def execute_local(self, code):
        file_code = tempfile.NamedTemporaryFile(delete=False, suffix='.hs')
        file_code.write(code.encode('utf8'))
        file_code.close()

        proc = Popen('runghc {}'.format(file_code.name), stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()

        os.unlink(file_code.name)

        return out.decode("utf-8"), self._get_code_errors(err.decode("utf-8"))

    def execute_sandbox(self, code):
        raise NotImplemented()

    def _get_code_errors(self, err):
        matches = re.findall('hs:(\d+):(\d+): (\w+):\W+([^\r\n]+)', err, flags=re.M)
        errors = []

        for error in matches:
            errors.append({'line': int(error[0]), 'column': int(error[1]), 'type': error[2], 'message': error[3]})

        return errors
