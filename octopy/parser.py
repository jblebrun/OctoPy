import math
import re

from typing import NamedTuple
from octopy.tokenizer import maptokens

class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.msg = msg
        self.token = token

    def __str__(self):
        return "{}: {}".format(self.token, self.msg)

class Macro(NamedTuple):
    """
    Holds the name, argument list, and unprocessed tokens for a macro.
    """
    name: str
    args: list
    tokens: list
    def __repr__(self):
        return "{}({}): <{}>".format(self.name, self.args, self.tokens)

validIdent = re.compile("[a-zA-Z_][0-9a-zA-Z-_]*")

class Parser():
    def __init__(self, tokens, emitter):
        self.registers = self.registers = {"v"+hex(i)[2:]: i for i in range(0, 16)}
        self.consts = { "PI": math.pi, "E": math.e }
        self.tokens = tokens
        self.emitter = emitter
        self.macros = {}
        self.current_token = None
        self.advance()
        self.parse()
        self.emitter.resolve()

    def parse(self):
        while self.current_token is not None:
            self.__expect_statement()
            self.advance()

    def error(self, msg):
        raise ParseError(msg, self.current_token)

    def advance(self, matcher=None):
        self.current_token = next(self.tokens, None)
        if matcher is not None:
            return matcher()
        return self.current_token

    def emit_macro(self):
        """
        Swap out the program tokens for this macro, and then parse normally.
        """
        macro = self.macros[self.current_token.text]
        macroargs = {k:self.advance().text for k in macro.args}
        pgmtokens = self.tokens
        self.tokens = maptokens(macro.tokens, macroargs)
        self.advance()
        self.parse()
        self.tokens = pgmtokens

    def expect(self, matcher, msg):
        res = matcher()
        if res is None:
            self.error("Expected {}".format(msg))
        return res

    def expect_ident(self):
        if not validIdent.match(self.current_token.text):
            self.error("Expected an identifier")
        return self.current_token

    def accept_register(self):
        return self.registers.get(self.current_token.text, None)

    def expect_register(self):
        return self.expect(self.accept_register, "register")

    def parse_number(self):
        if self.current_token.text in self.consts:
            return self.consts[self.current_token.text]

        try:
            num = int(self.current_token.text, 0)
        except ValueError:
            return None
        return num

    def accept_ranged_number(self, low, high):
        num = self.parse_number()
        if num is None:
            return None
        if num < low or num > high:
            self.error("number out of range")
        return num & high

    def accept_nybble(self):
        return self.accept_ranged_number(-0x7, 0xF)

    def accept_byte(self):
        return self.accept_ranged_number(-0x7F, 0xFF)

    def accept_address(self):
        return self.accept_ranged_number(-0x7FF, 0xFFF)

    def expect_nybble(self):
        return self.expect(self.accept_nybble, "nybble")

    def expect_byte(self):
        return self.expect(self.accept_byte, "byte")

    def expect_address(self):
        return self.expect(self.accept_address, "address")

    def expect_number(self):
        return self.expect(self.parse_number, "number")

    def __expect_statement(self):
        start_type = "Parsing Statement"
        try:
            start_token = self.current_token
            cur = self.current_token.text
            if cur in self.macros:
                start_type = "Emitting Macro"
                self.emit_macro()
            elif cur in self.registers:
                self.__expect_register_operation()
            elif cur == ":":
                self.__handle_label()
            elif cur == ";":
                self.__handle_return()
            else:
                num = self.accept_byte()
                if num is not None:
                    self.emitter.emit_byte(num)
                else:
                    methname = "_Parser__handle_{}".format(cur.replace(":", "").replace("-", "_"))
                    meth = getattr(self, methname, self.named_call)
                    meth()
        except Exception as e:
            raise ParseError("{}".format(start_type), start_token) from e

    def named_call(self):
        self.emitter.CALL(self.expect_ident())

    ###############
    #### Directives

    def __handle_label(self):
        name = self.advance(self.expect_ident)
        self.emitter.track_label(name.text)

    def __handle_alias(self):
        dst = self.advance(self.expect_ident).text
        src = self.advance(self.expect_register)
        self.registers[dst] = src

    def __handle_const(self):
        dst = self.advance(self.expect_ident).text
        src = self.advance(self.expect_number)
        self.consts[dst] = src

    def __handle_macro(self):
        name = self.advance().text
        args = []
        arg = self.advance().text
        while arg != "{":
            args.append(arg)
            arg = self.advance().text
        tokens = []
        token = self.advance()
        while token.text != "}":
            tokens.append(token)
            token = self.advance()
        self.macros[name] = Macro(name, args, tokens)

    ##############
    ### Operations

    def __handle_i(self):
        op = self.advance().text
        self.advance()
        if op == "+=":
            reg = self.expect_register()
            self.emitter.ADDI(reg)
            return

        if op != ":=":
            self.error("Only := or += for i")

        if self.current_token.text in ("hex", "bighex"):
            f = self.emitter.LDHEX if self.current_token.text == "hex" else self.emitter.LDBIGHEX
            f(self.advance(self.expect_register))
            return

        num = self.accept_address()
        if num is not None:
            self.emitter.LDI(num)
            return

        self.emitter.LDI(self.expect_ident())

    def __expect_register_operation(self):
        dst = self.registers[self.current_token.text]
        op = self.advance().text
        src = self.advance().text
        srcnum = self.accept_byte()

        if src in self.registers:
            self.__register_register_op(op, dst, src)
        elif srcnum is not None:
            self.__register_const_op(op, dst, srcnum)
        elif src == "delay":
            self.emitter.LDD(dst)
        elif src == "key":
            self.emitter.LDK(dst)
        elif src == "random":
            mask = self.advance(self.expect_byte)
            self.emitter.RAND(dst, mask)
        else: raise self.error("Unknown operand")

    def __register_const_op(self, op, dst, srcnum):
        if op == ":=":
            self.emitter.LDN(dst, srcnum)
        elif op == "+=":
            self.emitter.ADDN(dst, srcnum)
        elif op == "-=":
            self.emitter.ADDN(dst, -srcnum&0xFF)
        else: self.error("Register op with constant: Only := or +=")

    aluOps = {
        ":=": 0, "|=": 1, "&=":  2, "^=": 3,
        "+=": 4, "-=": 5, ">>=": 6, "=-": 7,
        "<<=": 0xE
    }

    def __register_register_op(self, op, dst, src):
        try:
            subcode = self.aluOps[op]
        except KeyError:
            self.error("unknown register op")
        self.emitter.ALU(dst, self.registers[src], subcode)


    ##############
    ### Statements
    def __handle_exit(self):
        self.emitter.EXIT()

    def __handle_scroll_down(self):
        n = self.advance(self.expect_nybble)
        self.emitter.SCD(n)

    def __handle_scroll_left(self):
        self.emitter.SCL()

    def __handle_scroll_right(self):
        self.emitter.SCR()

    def __fx_op(self, emitter_function):
        x = self.advance(self.expect_register)
        emitter_function(x)

    def __handle_save(self):
        self.__fx_op(self.emitter.SAVE)

    def __handle_load(self):
        self.__fx_op(self.emitter.LOAD)

    def __handle_saveflags(self):
        self.__fx_op(self.emitter.SAVEFLAGS)

    def __handle_loadflags(self):
        self.__fx_op(self.emitter.LOADFLAGS)

    def __handle_bcd(self):
        self.__fx_op(self.emitter.BCD)

    def __handle_jump(self):
        self.emitter.JMP(self.jump_target())

    def __handle_jump0(self):
        self.emitter.JMP0(self.jump_target())

    def jump_target(self):
        """ Used by handle_jump and handle_jump0 """
        num = self.advance(self.accept_address)
        return num if num is not None else self.expect_ident()

    def __handle_loop(self):
        self.emitter.start_loop()

    def __handle_again(self):
        self.emitter.end_loop()

    def __handle_hires(self):
        return self.emitter.HIRES()

    def __handle_lores(self):
        return self.emitter.LORES()

    def __handle_delay(self):
        self.emitter.STD(self.__delay_or_buzzer_target())

    def __handle_buzzer(self):
        self.emitter.STB(self.__delay_or_buzzer_target())

    def __delay_or_buzzer_target(self):
        self.advance()
        if self.current_token.text != ":=":
            self.error("Can only use :=")
        return self.advance(self.expect_register)

    def __handle_sprite(self):
        x = self.advance(self.expect_register)
        y = self.advance(self.expect_register)
        lines = self.advance(self.expect_nybble)
        return self.emitter.SPRITE(x, y, lines)

    ################
    ### Conditionals

    dualOp = {
        "==": "!=", "!=": "==",
        ">": "<=", "<": ">=",
        ">=": "<", "<=": ">",
        "key": "-key", "-key": "key",
    }

    def __handle_if(self):
        a = self.advance(self.expect_register)
        op = self.advance().text
        b_num = None
        b_reg = None
        if op not in ("key", "-key"):
            self.advance()
            b_num = self.accept_byte()
            if b_num is None:
                b_reg = self.expect_register()

        body = self.advance().text

        if body not in ("begin", "then"):
            self.error("Expected begin or then")

        if body == "begin":
            op = self.dualOp[op]

        self.__if_handle_comparison(op, a, b_num, b_reg)

        self.__if_emit_skip(op, a, b_num, b_reg)

        if body == "begin":
            self.emitter.emit_begin()

    def __if_handle_comparison(self, op, a, b_num, b_reg):
        # Load the right side of the conditional into VF for comparison subtraction.
        if op in ("<", ">", "<=", ">="):
            if b_num is not None:
                self.emitter.LDN(0xF, b_num)
            else:
                self.emitter.ALU(0xF, b_reg, 0)

        # Do subtraction for comparison
        if op in (">", "<="):
            self.emitter.ALU(0xF, a, 5)
        if op in ("<", ">="):
            self.emitter.ALU(0xF, a, 7)


    def __if_emit_skip(self, op, a, b_num, b_reg):
        # Handle key
        if op == "-key":
            self.emitter.SKNP(a)
        elif op == "key":
            self.emitter.SKP(a)
        # Handle SNE/SE variants
        elif op == "==":
            if b_num is not None:
                self.emitter.SNEN(a, b_num)
            else:
                self.emitter.SNER(a, b_reg)
        elif op == "!=":
            if b_num is not None:
                self.emitter.SEN(a, b_num)
            else:
                self.emitter.SER(a, b_reg)
        elif op in ("<", ">"):
            self.emitter.SNEN(0xf, 0)
        elif op in ("<=", ">="):
            self.emitter.SEN(0xf, 0)

    def __handle_else(self):
        if not self.emitter.emit_else():
            self.error("unexpected else")

    def __handle_end(self):
        if not self.emitter.emit_end():
            self.error("unexpected end")

    def __handle_return(self):
        self.emitter.RET()
