from definitions import BBox, Frame

from os import listdir
from os.path import isdir, exists
import sys

# For YOLO-style directories, one file per frame, class first

def tobbx_yolo(fn, l):
    ln = l.strip().split(' ')
    assert len(ln)==6, f'Yolo-style annotations but wrong number of parameters: {ln}'
    return BBox(frameid=fn, x=float(ln[1]), y=float(ln[2]), w=float(ln[3]), h=float(ln[4]), cls=ln[0], pr=float(ln[5]))

def parse_yolodir(dirname):
    fs = []
    # for all files in dir,
    files = listdir(dirname)
    files.sort()
    for f in files:
        with open(dirname+'/'+f, 'r') as fp:
            bs = [ tobbx_yolo(f, l) for l in fp.readlines() ]
        fs.append(Frame(frameid=f, bboxes=bs))
    return fs

# For RetinaNet outputs: filename, x1 y1 x2 y2 class prob

def tobbx_retina(ln):
    assert len(ln)==7, f'RetinaNet-style annotations but wrong number of parameters: {len(ln)} instead of 7'
    x1,y1,x2,y2 = float(ln[1]), float(ln[2]), float(ln[3]), float(ln[4])
    assert x2 > x1 and y2 > y1, f'RetinaNet annotations but second point smaller: {x1,y1} vs {x2,y2}'
    return BBox(frameid=ln[0], x=(x1+x2)/2, y=(y1+y2)/2, w=x2-x1, h=y2-y1, cls=ln[5], pr=float(ln[6]))

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

def parse_retina(fname): # File -> [Frame]
    with open(fname, 'r') as f:
        ls = [ tobbx_retina(l.strip().split(',')) for l in f.readlines()[1:] ]
    fs = merge_bbs(ls)
    return fs

# Detect and extract

def read_frames(fn):
    """Read all frames from a file (RetinaNet format) or directory (YOLO)"""
    if not exists(fn):
        print(f'No such file or directory: {fn}')
        sys.exit(-1)

    if isdir(fn): # yolo
        return parse_yolodir(fn)
    else: # retinanet
        return parse_retina(fn)
