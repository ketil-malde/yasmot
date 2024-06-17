from stracks.definitions import BBox, Frame

from os import listdir
from os.path import isdir, exists
import sys

# For YOLO-style directories, one file per frame, class first
# Relative coordinates (0-1). Sequence: center_x center_y width height, y (y is from top of frame)
def tobbx_yolo(fn, l):
    ln = l.strip().split(' ')
    assert len(ln) == 6, f'Yolo-style annotations but wrong number of parameters: {ln}'
    return BBox(frameid=fn, x=float(ln[1]), y=float(ln[2]), w=float(ln[3]), h=float(ln[4]), cls=ln[0], pr=float(ln[5]))

def parse_yolodir(dirname):
    fs = []
    # for all files in dir,
    files = listdir(dirname)
    files.sort()
    for f in files:
        with open(dirname + '/' + f, 'r') as fp:
            bs = [tobbx_yolo(f, l) for l in fp.readlines()]
        fs.append(Frame(frameid=f, bboxes=bs))
    return fs

# For RetinaNet outputs: filename, x1 y1 x2 y2 class prob

def tobbx_retina(ln, shape):
    assert len(ln) == 7, f'RetinaNet-style annotations but wrong number of parameters: {len(ln)} instead of 7'
    xm, ym = shape
    x1, y1, x2, y2 = float(ln[1]) / xm, float(ln[2]) / ym, float(ln[3]) / xm, float(ln[4]) / ym
    assert all([s >= 0 and s <= 1 for s in [x1, y1, x2, y2]]), f'Illegal values in RN bbox:\n  {ln}\n  {shape}'
    assert x2 > x1 and y2 > y1, f'RetinaNet annotations but second point smaller: {x1, y1} vs {x2, y2}:\n  {ln}'
    return BBox(frameid=ln[0], x=(x1 + x2) / 2, y=(y1 + y2) / 2, w=x2 - x1, h=y2 - y1, cls=ln[5], pr=float(ln[6]))

def merge_bbs(bs):
    res = []
    fs = []
    for b in bs:
        if fs == [] or b.frameid == fs[0].frameid:
            fs.append(b)
        else:
            assert b.frameid > fs[0].frameid, 'FrameIDs should be lexicographically ordered'
            res.append(Frame(frameid=fs[0].frameid, bboxes=fs))
            fs = [b]
    res.append(Frame(frameid=fs[0].frameid, bboxes=fs))
    return res

def parse_retina(fname, shape):  # File -> [Frame]
    def is_header(l):
        return l.strip() == 'datetime,x0,y0,x1,y1,label,score' or l[0] == '#'
    with open(fname, 'r') as f:
        ls = [tobbx_retina(l.strip().split(','), shape) for l in f.readlines() if not is_header(l)]
    fs = merge_bbs(ls)
    return fs

# Detect and extract

def read_frames(fn, shape=(1228,1027)):
    """Read all frames from a file (RetinaNet format) or directory (YOLO)"""
    if not exists(fn):
        print(f'No such file or directory: {fn}', file=sys.stderr)
        sys.exit(-1)

    if isdir(fn):  # yolo
        return parse_yolodir(fn)
    else:  # retinanet
        return parse_retina(fn, shape)

def show_frames(fs):
    for f in fs:
        print('Frame:', f.frameid)
        for b in f.bboxes:
            print(bbshow(b))

def write_yolo(of, fs):
    for frame in fs:
        with open(of + '/' + frame.frameid + '.txt', 'w') as f:
            for b in frame.bboxes:
                f.write(f'{b.cls} {b.x:.3f} {b.y:.3f} {b.w:.3f} {b.h:.3f} {b.pr:.3f}\n')

def write_rn(of, fs, shape=(1228,1027)):
    with open(of, 'w') as f:
        f.write('# header line\n')
        for frame in fs:
            for b in frame.bboxes:
                x1 = (b.x - b.w / 2) * shape[0]
                y1 = (b.y - b.h / 2) * shape[1]
                x2 = (b.x + b.w / 2) * shape[0]
                y2 = (b.y + b.h / 2) * shape[1]
                f.write(f'{frame.frameid},{x1:.3f},{y1:.3f},{x2:.3f},{y2:.3f},{b.cls},{b.pr:.3f}\n')

import os
def write_frames(outfile, fs):
    if exists(outfile):  # does this handle trailing slash?
        print(f'{outfile} already exists - aborting.', file=sys.stderr)
    elif outfile[-1] == '/':
        os.mkdir(outfile)
        write_yolo(outfile, fs)
    elif outfile[-4:] == '.csv':
        write_rn(outfile, fs)
    else:
        print('Specify an outfile ending in .csv or /', file=sys.stderr)
    
# Testing
import sys
from stracks.definitions import bbshow

if __name__ == "__main__":
    fs = read_frames(sys.argv[1])
    show_frames(fs)
