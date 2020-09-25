import sys
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: octoypy <infile.8o>")
        sys.exit()

    f = open(sys.argv[1])

    p = Program()
    try:
        Parser(Tokenizer(f), p)

    except ParseError as error:
        print_error(error)

    outname = sys.argv[1] + ".ch8"
    fout = open(outname, 'w')
    fout.buffer.write(p.program)
