from octopy.parser import ParseError
from octopy.tokenizer import Token

# pylint: disable=too-many-public-methods
class Program():
    def __init__(self):
        self.program = bytearray()
        self.labels = {}
        self.unresolved = []
        self.loops = []
        self.endjumps = []

    def __pc(self):
        return len(self.program)

    def __emit(self, op):
        self.program.extend(op)

    def __xyn_op(self, op, x, y, n):
        self.__emit((op << 4 | x, y << 4 | n))

    def __xn_op(self, op, x, n):
        self.__emit((op << 4 | x, n))

    def __n_op(self, op, n):
        if isinstance(n, int):
            self.__emit((op << 4 | n >> 8, n & 0xFF))
        elif isinstance(n, Token):
            self.unresolved.append((n, self.__pc()))
            self.__emit((op << 4 | 5, 0x55))
        else:
            raise Exception("Only number or token for n_op")

    def __add_main_jump(self):
        self.unresolved.append((Token("main", 0, 0), 0))
        self.JMP(0x555)

    def __pop_end_jump(self, offset=0):
        if len(self.endjumps) == 0:
            return False

        endjump = self.endjumps.pop()
        target = self.__pc()+0x200 + offset
        self.program[endjump] = (1 << 4) + (target >> 8)
        self.program[endjump+1] = target & 0xFF
        return True


    def emit_byte(self, byte):
        self.program.append(byte)

    def SYS(self, n):
        self.__n_op(0, n)
    def SCD(self, n):
        self.SYS(0xC << 4 | n)
    def RET(self):
        self.SYS(0xEE)
    def SCR(self):
        self.SYS(0xFB)
    def SCL(self):
        self.SYS(0xFC)
    def EXIT(self):
        self.SYS(0xFD)
    def LORES(self):
        self.SYS(0xFE)
    def HIRES(self):
        self.SYS(0xFF)

    def JMP(self, n):
        self.__n_op(0x1, n)
    def CALL(self, n):
        self.__n_op(0x2, n)
    def SEN(self, x, n):
        self.__xn_op(0x3, x, n)
    def SNEN(self, x, n):
        self.__xn_op(0x4, x, n)
    def SER(self, x, y):
        self.__xyn_op(0x5, x, y, 0)
    def LDN(self, x, n):
        self.__xn_op(0x6, x, n)
    def ADDN(self, x, n):
        self.__xn_op(0x7, x, n)
    def ALU(self, x, y, n):
        self.__xyn_op(0x8, x, y, n)
    def SNER(self, x, y):
        self.__xyn_op(0x9, x, y, 0)
    def LDI(self, n):
        self.__n_op(0xA, n)
    def JMP0(self, n):
        self.__n_op(0xB, n)
    def RAND(self, x, n):
        self.__xn_op(0xC, x, n)
    def SPRITE(self, x, y, n):
        self.__xyn_op(0xD, x, y, n)

    def SKNP(self, x):
        self.__xn_op(0xE, x, 0x9E)
    def SKP(self, x):
        self.__xn_op(0xE, x, 0xA1)

    def FX(self, x, n):
        self.__xn_op(0xF, x, n)
    def LDD(self, x):
        self.FX(x, 0x07)
    def LDK(self, x):
        self.FX(x, 0x0A)
    def STD(self, x):
        self.FX(x, 0x15)
    def STB(self, x):
        self.FX(x, 0x18)
    def ADDI(self, x):
        self.FX(x, 0x1E)
    def LDHEX(self, x):
        self.FX(x, 0x29)
    def LDBIGHEX(self, x):
        self.FX(x, 0x30)
    def BCD(self, x):
        self.FX(x, 0x33)
    def SAVE(self, x):
        self.FX(x, 0x55)
    def LOAD(self, x):
        self.FX(x, 0x65)
    def SAVEFLAGS(self, x):
        self.FX(x, 0x75)
    def LOADFLAGS(self, x):
        self.FX(x, 0x85)

    def track_label(self, name):
        if self.__pc() == 0 and name != "main":
            self.__add_main_jump()
        self.labels[name] = self.__pc()

    def emit_else(self):
        if not self.__pop_end_jump(2):
            return False
        self.endjumps.append(self.__pc())
        self.JMP(0x333)
        return True

    def emit_begin(self):
        self.endjumps.append(self.__pc())
        self.JMP(0x333)

    def emit_end(self):
        return self.__pop_end_jump()

    def start_loop(self):
        self.loops.append(self.__pc())

    def end_loop(self):
        ret = self.loops.pop()
        self.JMP(ret+0x200)

    def resolve(self):
        for (token, location) in self.unresolved:
            if token.text not in self.labels:
                raise ParseError("Unresolved name", token)
            op = self.program[location] >> 4
            target = 0x200 + (op << 12 | self.labels[token.text])
            self.program[location] = target >> 8
            self.program[location+1] = target & 0xFF
