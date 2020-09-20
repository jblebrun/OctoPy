import re
import sys
from octopy.tokenizer import maptokens


#TODO
# Calc
# stringmode
# next
# org
# unpack
# clear
# number ranges
# alias calc expr

# bcd
# scollrs
# exit
# flags

class ParseError(Exception):
    def __init__(self, msg, token):
        self.msg = msg
        self.token = token
    def __repr__(self): return __str__()
    def __str__(self): return "{}: {}".format(self.token, self.msg)

class LinkError(Exception):
    def __init__(self, name):
        self.name = name
    def __str__(self): return "Unresolved name {}".format(self.name)


class Macro():
    """
    Holds the name, argument list, and unprocessed tokens for a macro.
    """
    def __init__(self, name, args, tokens):
        self.name = name
        self.args = args
        self.tokens = tokens
    def __repr__(self):
        return "{}({}): <{}>".format(self.name, self.args, self.tokens)

    
validIdent = re.compile("[a-zA-Z_][0-9a-zA-Z-_]*")

class Parser():

    def __init__(self, tokens, emitter):
        self.registers = self.registers = {"v"+hex(i)[2:]: i for i in range(0,16)}
        self.tokens = tokens
        self.emitter = emitter
        self.currentToken = ""
        self.macros = {}
        self.advance()
        self.parse()
        self.emitter.resolve()

    def parse(self):
        while True: 
            self.expectProgramLine()
            try: 
                self.advance()
            except StopIteration:
                return

    def error(self, msg):
        raise ParseError(msg, self.currentToken)

    def advance(self):
        self.currentToken = next(self.tokens)
        return self.currentToken

    def emitMacro(self):
        """
        Swap out the program tokens for this macro, and then parse normally.
        """
        macroEmitToken = self.currentToken
        macro = self.macros[self.currentToken.text]
        macroargs = {k:self.advance().text for k in macro.args}
        pgmtokens = self.tokens
        self.tokens = maptokens(macro.tokens, macroargs)
        self.advance()
        try:
            self.parse()
        except ParseError as e:
            raise ParseError("During macro emission", macroEmitToken) from e 
        self.tokens = pgmtokens


    def handleLabel(self):
        self.advance()
        name = self.expectIdent()
        self.emitter.trackLabel(name)

    def handleAlias(self):
        self.advance()
        dst = self.expectIdent()
        self.advance()
        src = self.expectRegister()
        self.registers[dst] = src

    def handleI(self):
        op = self.advance().text
        self.advance()
        if op == "+=":
            reg = self.expectRegister()
            self.emitter.ADDI(reg)
            return

        if op != ":=": self.error("Only := or += for i")

        if self.currentToken.text in ("hex", "bighex"):
            f = self.emitter.LDHEX if self.currentToken.text == "hex" else self.emitter.LDBIGHEX
            self.advance()
            src = self.expectRegister()
            f(src)
            return
        
        num = self.acceptAddress()
        if num != None:
            self.emitter.LDI(num)
            return

        name = self.expectIdent()
        self.emitter.LDI(name)

    def handleSave(self):
        self.advance()
        x = self.expectRegister()
        self.emitter.LOAD(x)

    def handleLoad(self):
        self.advance()
        x = self.expectRegister()
        self.emitter.SAVE(x)

    def jumpTarget(self, op):
        self.advance()
        num = self.acceptAddress()
        if num != None:
            return num
        return self.currentToken.text

    def handleJump(self): self.JMP(self.jumpTarget())
    def handleJump0(self): self.JMP0(self.jumpTarget())

    def handleMacro(self):
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


    def expectIdent(self):
        if not validIdent.match(self.currentToken.text): self.error("Expected an identifier")
        return self.currentToken.text

    def expectRegisterOperation(self):
        dstName = self.currentToken.text
        dst = self.registers[self.currentToken.text]
        op = self.advance().text
        src = self.advance().text
        srcnum = self.acceptNumber()

        if src in self.registers:
            if op == ":=":  return self.emitter.ALU(dst, self.registers[src], 0)
            if op == "|=":  return self.emitter.ALU(dst, self.registers[src], 1)
            if op == "&=":  return self.emitter.ALU(dst, self.registers[src], 2)
            if op == "^=":  return self.emitter.ALU(dst, self.registers[src], 3)
            if op == "+=":  return self.emitter.ALU(dst, self.registers[src], 4)
            if op == "-=":  return self.emitter.ALU(dst, self.registers[src], 5)
            if op == ">>=": return self.emitter.ALU(dst, self.registers[src], 6)
            if op == "=-":  return self.emitter.ALU(dst, self.registers[src], 7)
            if op == "<<=": return self.emitter.ALU(dst, self.registers[src], 0xE)
            else: self.error("unknown register op")
        elif srcnum is not None:
            if op == ":=": return self.emitter.LDN(dst, srcnum) 
            elif op == "+=": return self.emitter.ADDN(dst, srcnum)
            elif op == "-=": return self.emitter.ADDN(dst, -srcnum&0xFF)
            else: self.error("Register op with constant: Only := or +=")
        elif src == "delay": return self.emitter.LDD(dst)
        elif src == "key": return self.emitter.LDK(dst)
        elif src == "random":
            self.advance()
            mask = self.expectNumber()
            return self.emitter.RAND(dst, mask)
        else: raise self.error("Unknown operand")

    def handleLoop(self): self.emitter.startLoop()
    def handleAgain(self): self.emitter.endLoop()
    
    def handleHires(self): return self.emitter.HIRES()
    
    def handleLores(self): return self.emitter.LORES()

    def acceptRegister(self):
        return self.registers.get(self.currentToken.text, None)

    def expectRegister(self):
        reg = self.acceptRegister()
        if reg == None: self.error("expected a register")
        return reg

    def acceptNumber(self):
        try: 
            num = int(self.currentToken.text, 0)
            if num < -127 or num > 255: self.error("invalid byte number")
            if num < 0: num = num & 0xFF
        except ValueError:  return None
        return num

    def acceptAddress(self):
        try: 
            num = int(self.currentToken.text, 0)
            if num < -0x7FF or num > 0xFFF: self.error("invalid address number")
            if num < 0: num = num & 0xFFF
        except ValueError:  return None
        return num

    def expectNumber(self):
        num = self.acceptNumber()
        if num == None: self.error("expected a number")
        return num


    def handleDelay(self): self.STD(self.delayOrBuzzerTarget())
    def handleBuzzer(self): self.STB(self.delayOrBuzzerTarget())
    def delayOrBuzzerTarget(self):
        self.advance()
        if self.currentToken.text != ":=": self.error("Can only use :=")
        self.advance()
        return self.expectRegister()

    def handleSprite(self): 
        self.advance()
        x = self.expectRegister()
        self.advance()
        y = self.expectRegister()
        self.advance()
        n = self.expectNumber()
        return self.emitter.SPRITE(x, y, n)


    oppOp = {
        "==": "!=",
        "!=": "==",
        ">": "<=",
        "<": ">=",
        ">=": "<",
        "<=": ">",
        "key": "-key",
        "-key": "key",
    }

    def trackEnd(self):
        pass

    def handleIf(self):
        self.advance()
        a = self.expectRegister()
        op = self.advance().text
        bn = None
        br = None
        if op not in ("key", "-key"):
            self.advance().text
            bn = self.acceptNumber()
            if bn == None:
                br = self.expectRegister()

        isNum = bn != None
        body = self.advance().text

        if body not in ("begin", "then"): self.error("Expected begin or then")

        if body == "begin": op = self.oppOp[op]

        # loads for comparison subtraction
        if op in ("<", ">", "<=", ">="): 
            if isNum: self.emitter.LDN(0xF, bn)
            else: self.emitter.ALU(0xF, br, 0)

        # subtraction for comparison
        if op in (">", "<="): self.emitter.ALU(0xF, a, 5)
        if op in ("<", ">="): self.emitter.ALU(0xF, a, 7) 

        # Handle key
        if op == "-key": self.emitter.SKNP(a)
        elif op == "key": self.emitter.SKP(a)
        # handle reg
        elif op == "==":
            if isNum: self.emitter.SNEN(a, bn)
            else: self.emitter.SNER(a, br)
        elif op == "!=":
            if isNum: self.emitter.SEN(a, bn)
            else: self.emitter.SER(a, br)
        elif op in ("<", ">"): self.emitter.SNEN(0xf, 0)
        elif op in ("<=", ">="): self.emitter.SEN(0xf, 0)

        if body == "begin": self.emitter.pushEndJump()


    def handleElse(self):
        self.emitter.popEndJump(2)
        self.emitter.pushEndJump()

    def handleEnd(self): self.emitter.popEndJump()

    def handleReturn(self): self.emitter.RET()

    def handleBareCall(self):
        num = self.acceptAddress()
        if num != None:
            self.emitter.emitByte(num)
            return

        try:
            name = self.expectIdent()
        except ParseError:
            raise self.error("expected a number or identifier to start a statement. (Is there an error just before this?)")
        self.emitter.CALL(name)

    def expectProgramLine(self):
        startToken = self.currentToken
        try:
            cur = self.currentToken.text
            if cur in self.macros: self.emitMacro()
            elif cur in self.registers: self.expectRegisterOperation()
            elif cur == ":": self.handleLabel()
            elif cur == ";": self.handleReturn()
            else:
                methname = cur.replace(":", "").capitalize()
                meth = getattr(self, "handle{}".format(methname), self.handleBareCall)
                meth()
        except Exception as e:
            raise ParseError("Statement start", startToken) from e






