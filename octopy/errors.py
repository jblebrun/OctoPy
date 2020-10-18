import traceback
class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.msg = msg
        self.token = token

    def __str__(self):
        lines = []
        err = self
        while err is not None:
            if isinstance(err, ParseError):
                lines.append("{}: {}".format(err.token, err.msg))
            else:
                lines.append("assembler crash: {}".format(err))
                lines += traceback.format_tb(err.__traceback__)
            err = err.__cause__

        return "\n".join(lines)
