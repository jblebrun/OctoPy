import sys

from octopy.assemble import assemble

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: octoypy <infile.8o>")
        sys.exit()

    f = open(sys.argv[1])

    program = assemble(f)

    if len(sys.argv) > 2:
        outname = sys.argv[2]
    else:
        outname = sys.argv[1].split(".")[0] + ".ch8"
    fout = open(outname, 'w')
    fout.buffer.write(program.program)

    if len(sys.argv) > 3:
        outname = sys.argv[3]
    else:
        outname = sys.argv[1].split(".")[0] + ".sym"

    fout = open(outname, 'w')
    for name, pc in program.labels.items():
        fout.write("{} = 0x0{:3X}\n".format(name, pc+0x200))
    for name, pc in program.consts.items():
        if name not in program.labels:
            fout.write("{} = {}\n".format(name, pc))
