PY_STR_ERR_SYNTAX = "SyntaxError:"


class ExecutorError:
    ERROR_TYPE_SYNTAX = 0

    def __init__(self, type, line):
        self.type = type
        self.line = line

    def __str__(self):
        type_str = "<unknown>"
        if self.type == self.ERROR_TYPE_SYNTAX:
            type_str = "syntax error"

        return "type: " + type_str + " at line: " + str(self.line)

    def get_type(self):
        return self.type

    def get_line(self):
        return self.line
