from octopy.parser import Parser, ParseError
from octopy.tokenizer import Tokenizer
from octopy.program import Program

def assemble(f):
    program = Program()
    tokenizer = Tokenizer(f)
    try:
        parser = Parser(tokenizer, program)
        parser.parse()
        program.resolve()

    except ParseError as error:
        program.error = error

    program.consts = tokenizer.consts
    return program
