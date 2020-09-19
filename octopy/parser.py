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
    def __init__(self, tokens):
        self.registers = self.registers = {"v"+hex(i)[2:]: i for i in range(0,16)}
        self.tokens = tokens
        self.advance()
        self.program = bytearray()
        self.labels = {}
        self.macros = {}
        self.unresolved = []
        self.loops = []
        self.endjumps = []

    def parse(self):
        while True: 
            self.expectProgramLine()
            try: 
                self.advance()
            except StopIteration:
                return

    def resolve(self):
        for (name, location) in self.unresolved:
            if name not in self.labels:
                raise LinkError(name)
            op = self.program[location] >> 4
            target = 0x200 + (op << 12 | self.labels[name])
            self.program[location] = target >> 8
            self.program[location+1] = target & 0xFF

    def error(self, msg):
        raise ParseError(msg, self.currentToken)

    def pc(self): return len(self.program)

    def advance(self):
        self.currentToken = next(self.tokens)
        return self.currentToken

    def addMainJump(self):
        self.unresolved.append(("main", 0))
        self.program.extend((0x15, 0x55))

    def emit4(self, op, x, y, n): self.program.extend((op << 4 | x, y << 4 | n))
    def emit3(self, op, x,  n): self.program.extend((op << 4 | x, n))
    def emit2(self, op, n): self.program.extend((op << 4 | n >> 8, n & 0xFF))
    def emit(self, op): self.program.extend((op >> 8, op & 0xFF))

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

    def toResolve(self, name): self.unresolved.append((name, self.pc()))

    def handleLabel(self):
        self.advance()
        name = self.expectIdent()
        if self.pc() == 0 and name != "main": self.addMainJump()
        self.labels[name] = self.pc()

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
            self.emit3(0xF, reg, 0x1E)
            return

        if op != ":=": self.error("Only := or += for i")

        if self.currentToken.text in ("hex", "bighex"):
            num = 0x29 if self.currentToken.text == "hex" else 0x30
            op = self.currentToken.text
            self.advance()
            src = self.expectRegister()
            self.emit3(0xF, src, num)
            return
        
        num = self.acceptAddress()
        if num != None:
            self.emit2(0xA, num)
            return

        name = self.expectIdent()
        self.toResolve(name)
        self.emit2(0xA, 0x666)

    def handleSave(self):
        self.advance()
        x = self.expectRegister()
        self.emit3(0xF, x, 0x55)

    def handleLoad(self):
        self.advance()
        x = self.expectRegister()
        self.emit3(0xF, x, 0x65)

    def jumpOrJump0(self, op):
        self.advance()
        num = self.acceptAddress()
        if num != None:
            self.emit2(0x1, num)
        else:
            name = self.expectIdent()
            self.toResolve(name)
            self.emit(0x1666)

    def handleJump(self): self.jumpOrJump0(0x1)
    def handleJump0(self): self.jumpOrJump0(0xB)

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
            if op == ":=":  return self.emit4(0x8, dst, self.registers[src], 0)
            if op == "|=":  return self.emit4(0x8, dst, self.registers[src], 1)
            if op == "&=":  return self.emit4(0x8, dst, self.registers[src], 2)
            if op == "^=":  return self.emit4(0x8, dst, self.registers[src], 3)
            if op == "+=":  return self.emit4(0x8, dst, self.registers[src], 4)
            if op == "-=":  return self.emit4(0x8, dst, self.registers[src], 5)
            if op == ">>=": return self.emit4(0x8, dst, self.registers[src], 6)
            if op == "=-":  return self.emit4(0x8, dst, self.registers[src], 7)
            if op == "<<=": return self.emit4(0x8, dst, self.registers[src], 0xE)
            else: self.error("unknown register op")
        elif srcnum is not None:
            if op == ":=": return self.emit3(0x6, dst, srcnum) 
            elif op == "+=": return self.emit3(0x7, dst, srcnum)
            elif op == "-=": return self.emit3(0x7, dst, -srcnum&0xFF)
            else: self.error("Register op with constant: Only := or +=")
        elif src == "delay": return self.emit3(0xF, dst, 0x7)
        elif src == "key": return self.emit3(0xF, dst, 0x0A)
        elif src == "random":
            self.advance()
            mask = self.expectNumber()
        else: raise self.error("Unknown operand")

    def handleLoop(self): self.loops.append(self.pc())

    def handleAgain(self):
        ret = self.loops.pop()
        self.emit2(1, ret+0x200)
    
    def handleHires(self): return self.emit(0x00FF)
    
    def handleLores(self): return self.emit(0x00FE)

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


    def handleDelay(self): self.emitDelayOrBuzzer()
    def handleBuzzer(self): self.emitDelayOrBuzzer()
    def emitDelayOrBuzzer(self):
        subop = 0x15 if self.currentToken.text == "delay" else 0x18
        self.advance()
        if self.currentToken.text != ":=": self.error("Can only use :=")
        self.advance()
        dest = self.expectRegister()
        self.emit3(0xF, dest, subop)

    def handleSprite(self): 
        self.advance()
        x = self.expectRegister()
        self.advance()
        y = self.expectRegister()
        self.advance()
        n = self.expectNumber()
        return self.emit4(0xD, x, y, n)


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

    # r == n -> SNE R, N
    # r != n -> SE R,
    # r > n -> LD VF, N; SUB R; SNE VF, 0
    # r < n -> LD VF, N; NSUB R; SNE VF, 0
    # r >= n -> LD VF N; NSUB R; SE VF, 0
    # r <= n -> LD VF N; SUB R; SE VF, 0
    # key -> SKP
    # -key -> SKNP
    # But if begin, instead of then:
    # reverse SNE/SNE and emit JMP.
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
            if isNum: self.emit3(0x6, 0xF, bn)
            else: self.emit4(0x8, 0xF, br, 0)

        # subtraction for comparison
        if op in (">", "<="): self.emit4(0x8, 0xF, a, 5)
        if op in ("<", ">="): self.emit4(0x8, 0xF, a, 7) 

        # Handle key
        if op == "-key": self.emit4(0xE, a, 0x9, 0xE) 
        elif op == "key": self.emit4(0xE, a, 0xA, 0x1) 
        # handle reg
        elif op == "==":
            if isNum: self.emit3(4, a, bn)
            else: self.emit4(9, a, br, 0)
        elif op == "!=":
            if isNum: self.emit3(3, a, bn)
            else: self.emit4(5, a, br,0)
        elif op in ("<", ">"): self.emit3(4, 0xf, 0)
        elif op in ("<=", ">="): self.emit3(3, 0xf, 0)

        if body == "begin": self.pushEndJump()


    def pushEndJump(self):
        self.endjumps.append(self.pc())
        self. emit(0x1333)

    def popEndJump(self, offset=0):
        if len(self.endjumps) == 0: self.error("unexpected 'end'")
        endjump = self.endjumps.pop()
        target = self.pc()+0x200 + offset
        self.program[endjump] = (1 << 4) + (target >> 8)
        self.program[endjump+1] = target & 0xFF

    def handleElse(self):
        self.popEndJump(2)
        self.pushEndJump()

    def handleEnd(self): self.popEndJump()

    def handleReturn(self): self.emit(0xEE)

    def handleBareCall(self):
        num = self.acceptAddress()
        if num != None:
            self.program.append(num)
            return

        try:
            name = self.expectIdent()
        except ParseError:
            raise self.error("expected a number or identifier to start a statement. (Is there an error just before this?)")
        self.toResolve(name)
        self.program.append(0x2F)
        self.program.append(0xFF)

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






