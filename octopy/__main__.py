import sys

from octopy.assemble import assemble

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: octoypy <infile.8o>")
        sys.exit()

    f = open(sys.argv[1])

    program = assemble(f)

    outname = sys.argv[1] + ".ch8"
    fout = open(outname, 'w')
    fout.buffer.write(program)
