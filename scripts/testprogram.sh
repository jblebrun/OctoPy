#!/bin/sh

# Test that the main program runs as expected
python3 -m octopy test/testdata/fibble.8o
cmp fibble.ch8 test/testdata/fibble.expect.ch8
