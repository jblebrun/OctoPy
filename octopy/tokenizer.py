import re
import traceback
import sys


class Token():
    def __init__(self, text, line, field):
        self.text = text
        self.line = line
        self.field = field
    
    def __repr__(self):
        return "`{0.text}` (at line {0.line} field {0.field})".format(self)

# Strip out whitespace and comments while tokenizing
def tokenize(source):
    for ln, line in enumerate(source):
        
        fields = line.split()
        tokenizingString = False

        for fn, field in enumerate(fields):
            # Comments will consume the rest of the line, so we can ignore
            if field.startswith("#"):
                break

            if field.startswith("\""):
                tokenizingString = True
                
            currentToken = Token(field, ln+1, fn+1)
            yield currentToken


def maptokens(tokens, mapping):
    def convertToken(token):
        if token.text in mapping:
            return Token(mapping[token.text], token.line, token.field)
        return token

    return (convertToken(t) for t in tokens)
    
