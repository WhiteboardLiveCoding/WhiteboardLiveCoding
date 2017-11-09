PY_STR_ERR_SYNTAX = "SyntaxError:"


class ExecutorError:
    def __init__(self, type="none", line=-1, col=-1):
        self.type = type
        self.line = line
        self.col = col

    def __str__(self):
        if self.type is "none":
            return "No error detected"
        else:
            return "Error type: " + str(self.type) + " at line: " + str(self.line) + " at column " + str(self.col)

    def get_type(self):
        return self.type

    def get_line(self):
        return self.line

    def get_column(self):
        return self.col
