import os
import sys

from octopy.assemble import assemble

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: octoypy <infile.8o>")
        sys.exit()

    f = open(sys.argv[1])

    path, filename = os.path.split(sys.argv[1])
    basename, ext = os.path.splitext(filename)


    program = assemble(f)

    if program.error is not None:
        print("Assembly failed:")
        print(program.error)
        sys.exit(-1)

    if len(sys.argv) > 2:
        outname = sys.argv[2]
    else:
        outname = basename + ".ch8"
    fout = open(outname, 'w')
    fout.buffer.write(program.program)

    if len(sys.argv) > 3:
        outname = sys.argv[3]
    else:
        outname = basename + ".sym"

    fout = open(outname, 'w')
    for name, pc in program.labels.items():
        fout.write("{} = 0x{:04X}\n".format(name, pc))
    for name, pc in program.consts.items():
        if name not in program.labels:
            fout.write("{} = {}\n".format(name, pc))

    breakpoints = program.debugger.breakpoints

    for name, (token, pc) in breakpoints.items():
        fout.write("{} = 0x{:04X}   # breakpoint: {}\n".format(name, pc, token))

    format_breakpoint = "0x{:04X}".format
    formatted_breakpoints = (format_breakpoint(pc) for (token, pc) in breakpoints.values())
    fout.write("breakpoints=[{}]\n".format(", ".join(formatted_breakpoints)))

    format_monitor = "(0x{:04X}, {})".format
    monitors = program.debugger.monitors
    formatted_monitors = (format_monitor(addr, monlen) for (addr, monlen) in monitors)

    fout.write("monitors=[{}]\n".format(", ".join(formatted_monitors)))
