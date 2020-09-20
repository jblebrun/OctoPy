#!/bin/sh

# Test that the main program runs as expected
python3 -m octopy test/testdata/loop.8o
cmp test/testdata/loop.8o.ch8 test/testdata/loop.expect.ch8
