import traceback

from octopy.parser import Parser, ParseError
from octopy.tokenizer import Tokenizer
from octopy.program import Program

def print_error(err):
    cause = err
    while cause is not None:
        if cause.__class__ is not ParseError:
            print("Parser Crash: {}", cause)
            traceback.print_exc()
            return
        cause = cause.__cause__

    while err is not None:
        print(err)
        err = err.__cause__

def assemble(f):
    program = Program()
    tokenizer = Tokenizer(f)
    try:
        parser = Parser(tokenizer, program)
        parser.parse()
        program.resolve()

    except ParseError as error:
        print_error(error)

    program.consts = tokenizer.consts
    return program
