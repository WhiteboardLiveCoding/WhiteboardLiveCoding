PY_STR_ERR_SYNTAX = "SyntaxError:"


class ExecutorError:
    def __init__(self, type="none", line=-1):
        self.type = type
        self.line = line

    def __str__(self):
        if self.type is "none":
            return "No error detected"
        else:
            return "Error type: " + str(self.type) + " at line: " + str(self.line)

    def get_type(self):
        return self.type

    def get_line(self):
        return self.line
