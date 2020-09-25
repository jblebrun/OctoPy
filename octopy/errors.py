class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.msg = msg
        self.token = token

    def __str__(self):
        return "{}: {}".format(self.token, self.msg)
