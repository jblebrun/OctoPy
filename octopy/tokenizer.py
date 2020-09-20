from typing import NamedTuple

class Token(NamedTuple):
    text: str
    line: int
    field: int

    def __repr__(self):
        return "`{}` (at line {} field {})".format(self.text, self.line, self.field)

# Strip out whitespace and comments while tokenizing
def tokenize(source):
    for line_num, line in enumerate(source):

        fields = line.split()

        for field_num, field in enumerate(fields):
            # Comments will consume the rest of the line, so we can ignore
            if field.startswith("#"):
                break

            yield Token(field, line_num+1, field_num+1)

def maptokens(tokens, mapping):
    """
    A helper that takes a sequence of tokens and returns a generator that
    produces the sequence of tokens, but for any token that appears as a key in the
    provided mapping, the map value will be provided, instead.
    """
    def convert_token(token):
        if token.text in mapping:
            return Token(mapping[token.text], token.line, token.field)
        return token

    return (convert_token(t) for t in tokens)
