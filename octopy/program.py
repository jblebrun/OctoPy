class Program():
    def __init__(self):
        self.program = bytearray()
        self.labels = {}
        self.unresolved = []
        self.loops = []
        self.endjumps = []


    def pc(self): return len(self.program)

    def emit(self, op): self.program.extend(op)
    def emitByte(self, byte): self.program.append(byte)

    def xynOp(self, op, x, y, n): self.emit((op << 4 | x, y << 4 | n))
    def xnOp(self, op, x,  n): self.emit((op << 4 | x, n))
    def nOp(self, op, n): 
        if type(n) is int:
            self.emit((op << 4 | n >> 8, n & 0xFF))
        else:
            self.toResolve(n)
            self.emit((op << 4 | 5, 0x55))

    def SYS(self, n): self.nOp(0, n)
    def RET(self): self.SYS(0xEE)
    def LORES(self): self.SYS(0xFE)
    def HIRES(self): self.SYS(0xFF)
    
    def JMP(self,  n): self.nOp(0x1, n)
    def CALL(self, n): self.nOp(0x2, n)
    def SEN(self, x, n): self.xnOp(0x3, x, n)
    def SNEN(self, x, n): self.xnOp(0x4, x, n)
    def SER(self, x, y): self.xynOp(0x5, x, y, 0)
    def LDN(self, x,n): self.xnOp(0x6, x, n)
    def ADDN(self, x,n): self.xnOp(0x7, x, n)
    def ALU(self, x, y, n): self.xynOp(0x8, x, y, n)
    def SNER(self, x, y): self.xynOp(0x9, x, y, 0)
    def LDI(self, n): self.nOp(0xA, n)
    def JMP0(self, n): self.nOp(0xB, n)
    def RAND(self, x, n): self.xnOp(0xC, x, n)
    def SPRITE(self, x, y, n): self.xynOp(0xD, x, y, n)

    def SKNP(self, x): self.xynOp(0xE, x, 0x9E)
    def SKP(self, x): self.xynOp(0xE, x, 0xA1)

    def FX(self, x, n): self.xnOp(0xF, x, n)
    def LDD(self, x): self.FX(x, 0x07)
    def LDK(self, x): self.FX(x, 0x0A)
    def STD(self, x): self.FX(x, 0x15)
    def STB(self, x): self.FX(x, 0x18)
    def ADDI(self, x): self.FX(x, 0x1E)
    def LDHEX(self, x): self.FX(x, 0x29)
    def LDBIGHEX(self, x): self.FX(x, 0x30)
    def LOAD(self, x): self.FX(x, 0x55)
    def SAVE(self, x): self.FX(x, 0x65)
     
    def toResolve(self, name): self.unresolved.append((name, self.pc()))

    def addMainJump(self):
        self.unresolved.append(("main", 0))
        self.JMP(0x555)

    def trackLabel(self, name):
        if self.pc() == 0 and name != "main": self.addMainJump()
        self.labels[name] = self.pc()

    def pushEndJump(self):
        self.endjumps.append(self.pc())
        self.JMP(0x333)

    def popEndJump(self, offset=0):
        if len(self.endjumps) == 0: self.error("unexpected 'end'")
        endjump = self.endjumps.pop()
        target = self.pc()+0x200 + offset
        self.program[endjump] = (1 << 4) + (target >> 8)
        self.program[endjump+1] = target & 0xFF

    def startLoop(self): self.loops.append(self.pc())

    def endLoop(self): 
        ret = self.loops.pop()
        self.JMP(ret+0x200)

    def resolve(self):
        for (name, location) in self.unresolved:
            if name not in self.labels:
                raise ParseError("Unresolved name {}".format(name))
            op = self.program[location] >> 4
            target = 0x200 + (op << 12 | self.labels[name])
            self.program[location] = target >> 8
            self.program[location+1] = target & 0xFF
