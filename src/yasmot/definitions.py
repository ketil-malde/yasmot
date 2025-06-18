from collections import namedtuple

global g_trackno
g_trackno = 0

BBox = namedtuple('BBox', ['frameid',            # :: String
                           'x', 'y', 'w', 'h',   # :: Doubles
                           'cls', 'pr'           # :: String and Double
                           ])

def bbshow1(b):
    '''Convert a single BBox to a string'''
    return f'{b.x:.5f}\t{b.y:.5f}\t{b.w:.5f}\t{b.h:.5f}\t{b.cls}\t{b.pr:.5f}'

def bbshow2(pair):
    '''Convert a pair of (stereo) BBoxes to a string'''
    a, b = pair
    dashes = '-\t' * 5 + '-'
    astr = bbshow1(a) if a is not None else dashes
    bstr = bbshow1(b) if b is not None else dashes
    return f'{frameid(pair)}\t{astr}\t{bstr}'

def bbshow(b):
    '''Convert a BBox or stereo pair to a string'''
    if type(b) is tuple: return bbshow2(b)
    else: return f'{b.frameid}\t{bbshow1(b)}'

def getcls(b):
    if type(b) is tuple: return b[0].cls if b[0] is not None else b[1].cls
    else: return b.cls

def frameid(b):  # b is a Frame or pair of Frames?
    if type(b) is tuple: return b[0].frameid if b[0] is not None else b[1].frameid
    else: return b.frameid

def setid(bbox, label):
    if bbox is None:
        return None
    elif type(bbox) is tuple:
        a, b = bbox
        return (setid(a, label), setid(b, label))
    else:
        return BBox(frameid=bbox.frameid, x=bbox.x, y=bbox.y, w=bbox.w, h=bbox.h, cls=label, pr=bbox.pr)

Frame = namedtuple('Frame', ['frameid', 'bboxes'])  # :: String and [BBox]

BBpair = namedtuple('BBPair', ['bbleft', 'bbright'])  # :: two BBoxes

Track = namedtuple('Track', ['trackid', 'bblist'])  # :: Int and [BBox] or [BBpair] if stereo

import sys
def error(msg):
    sys.stderr.write(msg + '\n')
    exit(255)
