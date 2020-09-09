import sys
import traceback
from octopy.parser import Parser, ParseError
from octopy.tokenizer import tokenize
from octopy.program import Program 

def printError(e):
    c = e
    while c != None:
        if c.__class__ is not ParseError:
            print("Parser Crash: {}", c)
            traceback.print_exc()
            return
        c = c.__cause__
    
    while e != None:
        print(e)
        e = e.__cause__


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: octoypy <infile.8o>")
        exit()

    f = open(sys.argv[1])

    p = Program()
    try:
        Parser(tokenize(f), p)

    except Exception as e:
        printError(e)

    outname = sys.argv[1] + ".ch8"
    fout = open(outname, 'w')
    fout.buffer.write(p.program)
