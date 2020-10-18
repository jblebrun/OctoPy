import unittest

from octopy.tokenizer import Tokenizer, Token
from octopy.calc import calc
from octopy.parser import ParseError

def no_rom(n): 
    raise Exception("no rom provided")

class TestCalc(unittest.TestCase):
    def expr_test(self, expr, expect, msg=None, rom_lookup=no_rom, consts=None):
        print("TEST", expr)
        tokens = [Token(t, 0, 0) for t in expr.split(" ")]
        tokenizer = Tokenizer("")
        tokenizer.tokengen = reversed(tokens)
        if consts is not None:
            tokenizer.consts.update(consts)
        if isinstance(expect, type):
            print("CHECK RAISES", msg)
            with self.assertRaisesRegex(expect, msg):
                calc(tokenizer, rom_lookup)
        else:
            result = calc(tokenizer, rom_lookup)
            self.assertEqual(result, expect)

    def test_simple(self):
        self.expr_test("4 + 3", 7)

    def test_long(self):
        self.expr_test("5 - 4 + 3", -2)

    def test_unary(self):
        self.expr_test("5 - - 4 + 3", 12)

    def test_422group(self):
        self.expr_test("( 4 * 2 ) + 2", 10)
    
    def test_422group2(self):
        self.expr_test("4 * ( 2 + 2 )", 16)

    def test_422nogroup(self):
        self.expr_test("4 * 2 + 2", 16)

    def test_badopen(self):
        self.expr_test("( 4 * 2 + 2", ParseError, "unclosed group")

    def test_badclose(self):
        self.expr_test("4 * 2 ) + 2", ParseError, "unexpected \)")

    def test_doublenum(self):
        self.expr_test("4 4 3", ParseError, "unexpected number")
 
    def test_incomplete(self):
        self.expr_test("+ 4", ParseError, "incomplete expression")

    def test_doubleop(self):
        self.expr_test("3 + + 4", ParseError, "expected number")
    
    def test_emptygroup(self):
        self.expr_test("( )", ParseError, "incomplete expression")

    def test_doublegroup(self):
        self.expr_test("( ( 1 ) ) + 3", 4)

    def test_nestedgroup(self):
        self.expr_test("4 * ( 2 + ( 3 * ( 1 + 1 ) ) + 3 ) - 2", 36)

    def test_startunaryneg(self):
        self.expr_test("- 1 * 6", -6)

    def test_romlookup(self):
        consts = {"somewhere": 1, "another": 3}
        def lookup(n):
            print("lookup",n)
            return [11, 2, 33, 44][n]
        self.expr_test("2 * @ somewhere + @ somewhere", 88, consts=consts, rom_lookup=lookup)


if __name__ == '__main__': unittest.main()
