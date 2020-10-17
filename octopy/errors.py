class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.msg = msg
        self.token = token

    def __str__(self):
        cause = self
        while cause is not None:
            if cause.__class__ is not ParseError:
                return "Parser Crash: {}".format(cause)
            cause = cause.__cause__

        lines = []
        err = self
        while err is not None:
            lines.append("{}: {}".format(err.token, err.msg))
            err = err.__cause__

        return "\n".join(lines)
