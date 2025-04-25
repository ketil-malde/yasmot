# usage: convert.py infile outfile

import sys
from parser import read_frames, write_frames

inf  = sys.argv[1]
outf = sys.argv[2]

write_frames(outf, read_frames(inf))
