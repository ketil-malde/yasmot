from collections import namedtuple

global g_trackno
g_trackno = 0

BBox = namedtuple('BBox', 'frameid x y w h cls pr')  # :: Doubles

def bbshow(b):
    return f'{b.frameid}\t{b.x:.5f}\t{b.y:.5f}\t{b.w:.5f}\t{b.h:.5f}\t{b.cls}\t{b.pr:.5f}'

Frame = namedtuple('Frame', 'frameid bboxes') # :: [BBox]

BBpair = namedtuple('BBPair', 'bbleft bbright')

Track = namedtuple('Track', 'trackid bblist')

import sys
def error(msg):
    sys.stderr.write(msg+'\n')
    exit(255)
