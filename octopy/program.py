from typing import NamedTuple

from octopy.errors import ParseError
from octopy.tokenizer import Token

class Unresolved(NamedTuple):
    jumpsandcalls: list
    begins: list
    loops: list
    whiles: list
    unpacks: dict

class Debugger(NamedTuple):
    breakpoints: dict
    monitors: list

# pylint: disable=too-many-public-methods
class Program():
    def __init__(self):
        self.program = bytearray()
        self.__offset = 0
        self.error = None
        self.labels = {}
        self.debugger = Debugger({}, [])
        self.unresolved = Unresolved([], [], [], [], {})

    def pc(self):
        return self.__offset + 0x200

    def org(self, org):
        self.__offset = org - 0x200

    def lookup(self, n):
        return self.program[n - 0x200]

    def breakpoint(self, name):
        self.debugger.breakpoints[name.text] = (name, self.pc())

    def monitor(self, addr, monlen):
        self.debugger.monitors.append((addr, monlen))

    def __emit(self, op):
        if self.__offset < 0:
            raise Exception("Can't emit data below 0x200. org: {}".format(self.__offset))
        additional_size = self.__offset + len(op) - len(self.program)
        self.program.extend([0] * additional_size)
        self.program[self.__offset:self.__offset+len(op)] = op
        self.__offset += len(op)

    def __xyn_op(self, op, x, y, n):
        self.__emit((op << 4 | x, y << 4 | n))

    def __xn_op(self, op, x, n):
        self.__emit((op << 4 | x, n))

    def __n_op(self, op, n):
        if isinstance(n, int):
            self.__emit((op << 4 | n >> 8, n & 0xFF))
        elif isinstance(n, Token):
            self.unresolved.jumpsandcalls.append((n, self.__offset))
            self.__emit((op << 4 | 5, 0x55))
        else:
            raise Exception("Only number or token for n_op")

    def __resolve_addrop(self, jumpspot, value):
        self.program[jumpspot] &= 0xF0
        self.program[jumpspot] |= (value >> 8)
        self.program[jumpspot+1] = value & 0xFF

    def __add_main_jump(self):
        self.unresolved.jumpsandcalls.append((Token("main", 0, 0), 0))
        self.JMP(0x555)

    def __pop_end_jump(self, offset=0):
        if len(self.unresolved.begins) == 0:
            return False

        endjump = self.unresolved.begins.pop()
        self.__resolve_addrop(endjump, self.pc() + offset)
        return True


    def emit_byte(self, byte):
        self.__emit((byte,))

    def SYS(self, n):
        self.__n_op(0, n)
    def CLS(self):
        self.SYS(0xE0)
    def SCD(self, n):
        self.SYS(0xC << 4 | n)
    def SCU(self, n):
        self.SYS(0xD << 4 | n)
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
    def LDIL(self, addr):
        self.__emit((0xF0, 0x00))
        self.__n_op(0, addr)
    def JMP0(self, n):
        self.__n_op(0xB, n)
    def RAND(self, x, n):
        self.__xn_op(0xC, x, n)
    def SPRITE(self, x, y, n):
        self.__xyn_op(0xD, x, y, n)
    def PLANE(self, n):
        self.__xn_op(0xF, n, 0x01)
    def AUDIO(self):
        self.__n_op(0xF, 0x002)

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

    def SAVEXY(self, x, y):
        self.__xyn_op(5, x, y, 2)
    def LOADXY(self, x, y):
        self.__xyn_op(5, x, y, 3)
    def track_label(self, name, offset):
        if self.pc() + offset == 0x200 and name.text != "main":
            self.__add_main_jump()
        if name.text in self.labels:
            raise ParseError("duplicate label defined", name)
        self.labels[name.text] = self.pc() + offset

    def emit_else(self):
        if not self.__pop_end_jump(2):
            return False
        self.unresolved.begins.append(self.__offset)
        self.JMP(0x333)
        return True

    def emit_begin(self):
        self.unresolved.begins.append(self.__offset)
        self.JMP(0x333)

    def emit_while(self):
        self.unresolved.whiles[-1].append(self.__offset)
        self.JMP(0x444)

    def emit_end(self):
        return self.__pop_end_jump()

    def start_loop(self):
        self.unresolved.whiles.append([])
        self.unresolved.loops.append(self.pc())

    def end_loop(self):
        whiles = self.unresolved.whiles.pop()
        for whilespot in whiles:
            self.__resolve_addrop(whilespot, self.pc()+2)

        ret = self.unresolved.loops.pop()
        self.JMP(ret)

    def emit_unpack(self, msn, name):
        self.LDN(0, msn << 4)
        self.LDN(1, 0)
        self.unresolved.unpacks[self.__offset] = name

    def resolve(self):
        for pc, token in self.unresolved.unpacks.items():
            if token.text not in self.labels:
                raise ParseError("Unresolved name", token)
            target = self.labels[token.text]
            self.program[pc-1] = target & 0xFF
            self.program[pc-3] |= (target >> 8) & 0xF

        for (token, location) in self.unresolved.jumpsandcalls:
            if token.text not in self.labels:
                raise ParseError("Unresolved name", token)
            target = self.labels[token.text]
            self.__resolve_addrop(location, target)
