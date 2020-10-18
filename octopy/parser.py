from dataclasses import dataclass
from typing import NamedTuple

from octopy.calc import calc
from octopy.errors import ParseError


class Macro(NamedTuple):
    """
    Holds the name, argument list, and unprocessed tokens for a macro.
    """
    name: str
    args: list
    tokens: list
    def __repr__(self):
        return "{}({}): <{}>".format(self.name, self.args, self.tokens)

@dataclass
class MacroEntry():
    macro: Macro
    calls: int

class Parser():
    def __init__(self, tokenizer, emitter, macros=None):
        self.emitter = emitter
        self.macros = macros or {}
        self.tokenizer = tokenizer
        self.tokenizer.advance()

    def parse(self):
        while self.tokenizer.current() is not None:
            self.__expect_statement()
            self.tokenizer.advance()

    def error(self, msg):
        raise ParseError(msg, self.tokenizer.current())

    def emit_macro(self):
        """
        Swap out the program tokens for this macro, and then parse normally.
        """
        macro = self.macros[self.tokenizer.current().text]
        macroargs = {k:self.tokenizer.advance() for k in macro.macro.args}
        macro_tokenizer = self.tokenizer.maptokenizer(macro.macro.tokens, macroargs)
        macro_tokenizer.add_const("CALLS", macro.calls)
        macro.calls += 1
        macro_parser = Parser(macro_tokenizer, self.emitter, self.macros)
        macro_parser.parse()

    def __expect_statement(self):
        start_type = "Parsing Statement"
        try:
            start_token = self.tokenizer.current()
            cur = self.tokenizer.current().text
            if cur in self.macros:
                start_type = "Emitting Macro"
                self.emit_macro()
            elif self.tokenizer.accept_register() is not None:
                self.__expect_register_operation()
            elif cur == ":":
                self.__handle_label()
            elif cur == ";":
                self.__handle_return()
            elif cur in self.emitter.labels:
                self.emitter.CALL(self.tokenizer.expect_ident())
            else:
                num = self.tokenizer.accept_byte()
                if num is not None:
                    self.emitter.emit_byte(num)
                else:
                    methname = "_Parser__handle_{}".format(cur.replace(":", "").replace("-", "_"))
                    meth = getattr(self, methname, self.named_call)
                    meth()
        except Exception as e:
            raise ParseError("{}".format(start_type), start_token) from e

    def named_call(self):
        self.emitter.CALL(self.tokenizer.expect_ident())

    ###############
    #### Directives

    def __handle_label(self, offset=0):
        name = self.tokenizer.next_ident()
        self.emitter.track_label(name, offset)
        self.tokenizer.add_const(name.text, self.emitter.pc() + offset)

    def __handle_alias(self):
        dst = self.tokenizer.next_ident().text
        if self.tokenizer.advance().text == "{":
            src = self.__calc_expr()
            if src < 0 or src > 15:
                self.error("register expression result '{}' is out of range [0x0,0xF]".format(src))
        else:
            src = self.tokenizer.expect_register()
        self.tokenizer.add_register(dst, int(src))

    def __handle_byte(self):
        if self.tokenizer.advance().text == "{":
            value = self.__calc_expr()
            if value < -127 or value > 255:
                self.error("byte expression result {} out of range".format(value))
        else:
            value = self.tokenizer.expect_byte()
        self.emitter.emit_byte(int(value))

    def __handle_calc(self):
        name = self.tokenizer.next_ident().text
        if self.tokenizer.advance().text != "{":
            self.error("expected { to start calc expression")
        value = self.__calc_expr()
        self.tokenizer.add_const(name, value)

    def __calc_expr(self):
        tokens = self.__token_cluster()
        calc_tokenizer = self.tokenizer.maptokenizer(reversed(tokens), {})
        calc_tokenizer.add_const("HERE", self.emitter.pc())
        return calc(calc_tokenizer)


    def __handle_const(self):
        name = self.tokenizer.next_ident().text
        value = self.tokenizer.advance(self.tokenizer.expect_number)
        self.tokenizer.add_const(name, value)

    def __handle_macro(self):
        name = self.tokenizer.next_ident().text
        args = []
        arg = self.tokenizer.advance().text
        while arg != "{":
            args.append(arg)
            arg = self.tokenizer.advance().text
        tokens = self.__token_cluster()
        self.macros[name] = MacroEntry(Macro(name, args, tokens), 0)

    def __handle_org(self):
        addr = self.tokenizer.next_long_address()
        self.emitter.org(addr)

    def __handle_unpack(self):
        msn = self.tokenizer.next_nybble()
        name = self.tokenizer.advance()
        self.tokenizer.expect_ident()
        self.emitter.emit_unpack(msn, name)

    def __handle_next(self):
        self.__handle_label(offset=1)


    def __token_cluster(self):
        tokens = []
        token = self.tokenizer.advance()
        depth = 1
        while depth > 0:
            if token.text == "{":
                depth += 1
            if token.text == "}":
                depth -= 1
            if depth > 0:
                tokens.append(token)
                token = self.tokenizer.advance()
        return tokens


    ##############
    ### Operations

    def __handle_i(self):
        op = self.tokenizer.advance().text
        self.tokenizer.advance()
        if op == "+=":
            reg = self.tokenizer.expect_register()
            self.emitter.ADDI(reg)
            return

        if op != ":=":
            self.error("Only := or += for i")

        curtext = self.tokenizer.current().text
        if curtext in ("hex", "bighex"):
            f = self.emitter.LDHEX if curtext == "hex" else self.emitter.LDBIGHEX
            f(self.tokenizer.next_register())
            return

        if curtext == "long":
            self.emitter.LDIL(self.tokenizer.next_long_location())
            return

        self.emitter.LDI(self.tokenizer.expect_location())

    def __expect_register_operation(self):
        dst = self.tokenizer.expect_register()
        op = self.tokenizer.advance().text
        src = self.tokenizer.advance().text
        srcnum = self.tokenizer.accept_byte()
        reg = self.tokenizer.accept_register()

        if reg is not None:
            self.__register_register_op(op, dst)
        elif srcnum is not None:
            self.__register_const_op(op, dst, srcnum)
        elif src == "delay":
            self.emitter.LDD(dst)
        elif src == "key":
            self.emitter.LDK(dst)
        elif src == "random":
            mask = self.tokenizer.next_byte()
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

    def __register_register_op(self, op, dst):
        try:
            subcode = self.aluOps[op]
        except KeyError:
            self.error("unknown register op")
        self.emitter.ALU(dst, self.tokenizer.expect_register(), subcode)


    ##############
    ### Statements
    def __handle_exit(self):
        self.emitter.EXIT()

    def __handle_clear(self):
        self.emitter.CLS()

    def __handle_scroll_down(self):
        n = self.tokenizer.next_nybble()
        self.emitter.SCD(n)

    def __handle_scroll_left(self):
        self.emitter.SCL()

    def __handle_scroll_right(self):
        self.emitter.SCR()

    def __fx_op(self, emitter_function):
        x = self.tokenizer.next_register()
        emitter_function(x)

    def __save_load(self, emitter_function, emitter_functionxy):
        x = self.tokenizer.next_register()
        next_token = self.tokenizer.advance()
        if (next_token is not None) and next_token.text == "-":
            y = self.tokenizer.next_register()
            emitter_functionxy(x, y)
        else:
            self.tokenizer.unadvance()
            emitter_function(x)

    def __handle_load(self):
        self.__save_load(self.emitter.LOAD, self.emitter.LOADXY)

    def __handle_save(self):
        self.__save_load(self.emitter.SAVE, self.emitter.SAVEXY)

    def __handle_saveflags(self):
        self.__fx_op(self.emitter.SAVEFLAGS)

    def __handle_loadflags(self):
        self.__fx_op(self.emitter.LOADFLAGS)

    def __handle_bcd(self):
        self.__fx_op(self.emitter.BCD)

    def __handle_jump(self):
        self.emitter.JMP(self.tokenizer.next_location())

    def __handle_jump0(self):
        self.emitter.JMP0(self.tokenizer.next_location())

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
        self.tokenizer.advance()
        if self.tokenizer.current().text != ":=":
            self.error("Can only use :=")
        return self.tokenizer.next_register()

    def __handle_sprite(self):
        x = self.tokenizer.next_register()
        y = self.tokenizer.next_register()
        lines = self.tokenizer.next_nybble()
        return self.emitter.SPRITE(x, y, lines)

    ################
    ### Conditionals

    dualOp = {
        "==": "!=", "!=": "==",
        ">": "<=", "<": ">=",
        ">=": "<", "<=": ">",
        "key": "-key", "-key": "key",
    }

    def __handle_while(self):
        self.__parse_conditional("while")

    def __handle_if(self):
        self.__parse_conditional()

    def __parse_conditional(self, body=None):
        a = self.tokenizer.next_register()
        op = self.tokenizer.advance().text
        b_num = None
        b_reg = None
        if op not in ("key", "-key"):
            self.tokenizer.advance()
            b_num = self.tokenizer.accept_byte()
            if b_num is None:
                b_reg = self.tokenizer.expect_register()

        body = body or self.tokenizer.advance().text

        if body not in ("begin", "then", "while"):
            self.error("Expected begin or then")

        if body in ("begin", "while"):
            op = self.dualOp[op]

        self.__if_handle_comparison(op, a, b_num, b_reg)

        self.__if_emit_skip(op, a, b_num, b_reg)

        if body == "begin":
            self.emitter.emit_begin()
        elif body == "while":
            self.emitter.emit_while()

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
