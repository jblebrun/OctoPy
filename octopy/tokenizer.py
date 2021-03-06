from typing import NamedTuple

import math
import re
import copy
from octopy.errors import ParseError

class Token(NamedTuple):
    text: str
    line: int
    field: int

    def __repr__(self):
        return "`{}` (at line {} field {})".format(self.text, self.line, self.field)

validIdent = re.compile(r'[^\d\s][\S]*')

class Tokenizer():
    def __init__(self, source):
        keys = ('X', '1', '2', '3', 'Q', 'W', 'E', 'A', 'S', 'D', 'Z', 'C', '4', 'R', 'F', 'V')
        self.consts = {"OCTO_KEY_{}".format(k):i for i, k in enumerate(keys)}
        self.consts["PI"] = math.pi
        self.consts["E"] = math.e
        self.registers = {"v{:x}".format(i): i for i in range(0, 16)}
        self.registers.update({"v{:X}".format(i): i for i in range(0, 16)})
        self.current_token = None
        self.repeat_token = False
        self.calls = []

        # Strip out whitespace and comments while tokenizing
        def tokenize(source):
            for line_num, line in enumerate(source):

                fields = line.split()

                for field_num, field in enumerate(fields):
                    # Comments will consume the rest of the line, so we can ignore
                    if field.startswith("#"):
                        break

                    yield Token(field, line_num+1, field_num+1)

        self.tokengen = tokenize(source)

    def error(self, msg):
        raise ParseError(msg, self.current_token)

    def add_const(self, name, value):
        self.consts[name] = value

    def add_register(self, name, value):
        self.registers[name] = value

    def current(self):
        return self.current_token

    def unadvance(self):
        self.repeat_token = True

    def advance(self, matcher=None):
        if self.repeat_token:
            self.repeat_token = False
        else:
            self.current_token = next(self.tokengen, None)
        if matcher is not None:
            return matcher()
        return self.current_token

    def emit_macro(self, calls, tokens, mapping):
        def convert_token(token):
            if token.text in mapping:
                return Token(mapping[token.text].text, token.line, token.field)
            return token
        macrotokengen = (convert_token(t) for t in tokens)

        self.calls.append(calls)

        curgen = self.tokengen
        def newgen():
            yield from macrotokengen
            self.calls.pop()
            self.tokengen = curgen
            yield next(curgen, None)

        self.tokengen = newgen()

    def copy(self, tokens):
        copied = copy.copy(self)
        copied.tokengen = tokens
        return copied

    def expect(self, matcher, msg):
        res = matcher()
        if res is None:
            self.error("Expected {}".format(msg))
        return res

    def expect_ident(self):
        if not validIdent.match(self.current_token.text):
            self.error("Expected an identifier: {}".format(self.current_token.text))
        return self.current_token

    def next_ident(self):
        return self.advance(self.expect_ident)

    def next_register(self):
        return self.advance(self.expect_register)

    def next_address(self):
        return self.advance(self.expect_address)

    def next_long_address(self):
        return self.advance(self.expect_long_address)

    def accept_register(self):
        return self.registers.get(self.current_token.text, None)

    def expect_register(self):
        return self.expect(self.accept_register, "register")

    def parse_number(self):
        if self.current_token.text == "CALLS":
            return self.calls[-1]

        if self.current_token.text in self.consts:
            return self.consts[self.current_token.text]

        try:
            return int(self.current_token.text, 0)
        except ValueError:
            # Decimal numbers with leading 0 do not parse in Python.
            # So also attempt exlicit decimal parsing ot handle those.
            try:
                return int(self.current_token.text, 10)
            except ValueError:
                return None

    def accept_ranged_number(self, low, high):
        num = self.parse_number()
        if num is None:
            return None
        if num < low or num > high:
            self.error("number {} out of range [{}, {}]".format(num, low, high))
        return int(num) & high

    def accept_nybble(self):
        return self.accept_ranged_number(-0x7, 0xF)

    def accept_byte(self):
        return self.accept_ranged_number(-0x7F, 0xFF)

    def accept_address(self):
        return self.accept_ranged_number(-0x7FF, 0xFFF)

    def accept_long_address(self):
        return self.accept_ranged_number(-0x7FFF, 0xFFFF)

    def expect_nybble(self):
        return self.expect(self.accept_nybble, "nybble")

    def expect_byte(self):
        return self.expect(self.accept_byte, "byte")

    def expect_address(self):
        return self.expect(self.accept_address, "address")

    def expect_long_address(self):
        return self.expect(self.accept_long_address, "long_address")

    def expect_number(self):
        return self.expect(self.parse_number, "number")

    def next_byte(self):
        return self.advance(self.expect_byte)

    def next_nybble(self):
        return self.advance(self.expect_nybble)

    def next_number(self):
        return self.advance(self.expect_number)

    def expect_location(self):
        num = self.accept_address()
        if num is not None:
            return num
        return self.expect_ident()

    def expect_long_location(self):
        num = self.accept_long_address()
        if num is not None:
            return num
        return self.expect_ident()

    def next_location(self):
        return self.advance(self.expect_location)

    def next_long_location(self):
        return self.advance(self.expect_long_location)
