from collections import namedtuple

from definitions import Track
from parser import tobbx_yolo

######################################################################
# Match bboxes from two stereo still frames

sdistparams = namedtuple('SDparm', 'undefined')
# Vertical should be very similar, horizontal can/should vary, size should be similar
# Can we determine empirically?

def sdist(bleft, bright): # BBox x BBbox -> Float
    '''Calculate distance between a bbox in the left and right frames'''
    pass

def smatch(frameleft, frameright):
    '''Use Hungarian algorithm to match bboxes between left and right frames'''
    pass

######################################################################
# Match paired bboxes with a set of existing tracks

tdistparams = namedtuple('TDparm', 'undefined')
# size and position should be similar, and maybe relative?
# Determine empirically?
# 50% likelihood of 10% distance/size change: fit Gaussian
# cutoff prob < 0.1?

from math import exp

def bbdist1(bb1, bb2, ignorey=False, scale=1): # BBox x BBox -> Float
    """Calculate distance between bboxes, optionally ignoring y position 
       (for stereo pairs), and providing a scale to soften/sharpen the output."""
    dx, dy = bb1.x - bb2.x, bb1.y - bb2.y
    dw, dh = bb1.w - bb2.w, bb1.h - bb2.h
    dcls = bb1.cls == bb2.cls
    w2, h2 = bb1.w*bb2.w, bb1.h*bb2.h

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2/w2*scale)
    yascore = exp(-dh**2/h2*scale)
    xpscore = exp(-dx**2/w2*scale)
    if ignorey:
        ypscore = 1
    else:
        ypscore = exp(-dy**2/h2*scale)

    # use .pr? (confidence)
    # print('-> xa: ', xascore, 'ya: ', yascore, 'xp: ', xpscore, 'yp: ', ypscore,)
    return(xpscore * ypscore * xascore * yascore)

def bbdist_stereo(bb1, bb2):
    return bbdist1(bb1, bb2, ignorey = True)

def tdist(track, bbox): # Track x BBpairs
    return bbdist1(track.bbpairs[-1], bbox)

from scipy.optimize import linear_sum_assignment
import numpy as np

def bbmatch(f1, f2, threshold=0.1, metric=bbdist1): # [BBox] x [BBox] -> [(BBox,BBox)]
    """Match bboxes from two frames."""
    mx = np.empty((len(f1), len(f2)))
    for a in range(len(f1)):
        for b in range(len(f2)):
            mx[a,b] = -metric(f1[a], f2[b])
    aind, bind = linear_sum_assignment(mx)
    # print(aind, bind)
    res = []
    # todo: filter on threshold
    for i in range(len(aind)):
        if -mx[aind[i],bind[i]] > threshold:
            res.append( (f1[aind[i]],f2[bind[i]]) )
        else:
            res.append( (f1[aind[i]], None) )
            res.append( (None, f2[bind[i]]) )
    for i in range(len(f1)):
        if i not in aind: res.append( (f1[i], None) )
    for i in range(len(f2)):
        if i not in bind: res.append( (None, f2[i]) )

    # todo: add assertion that all inputs are outputs once?
    return res
    
# NB! Modifies tracks parameter (append)
# Might use bbmatch above for its guts?
def tmatch(bbs, tracks, old_tracks):
    '''Use Hungarian alg to match tracks and bboxes'''
    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        # print('***** track=',t, '\n ->', tracks[t].bbpairs[-1])
        for b in range(len(bbs)):
            s = tdist(tracks[t], bbs[b])
            # print('  match track=', t, 'bbox=', b, 'score=', s)
            # print(bpairs[b])
            tmx[t,b] = -s # tdist(tracks[t], bpairs[b])
    tind, bind = linear_sum_assignment(tmx)
    # append b[bind] to t[tind] for index pairs
    for i in range(len(tind)):
        tracks[tind[i]].bbpairs.append(bbs[bind[i]])

    # process the unmatched tracks
    for i in range(len(tracks))[::-1]:
        if i not in tind:
            # maybe...something?
            # else move to old tracks
            old_tracks.insert(0, tracks.pop(i))

    # process the unmatched bboxes
    for i in range(len(bbs)):
        if i not in bind:
            # todo: eliminate if too much IoU (double predictions)
            # todo: else search old tracks to rejuvenate
            # else create new track
            tracks.append(Track([bbs[i]]))
        pass

    return

# Output:
# tracks.txt: trackid class [BBPair]
# incorrectly labeled frames (by confidence?)

def test():
    # read two annotation files
    f1, f2 = 'data/labels/frame_000155.txt','data/labels/frame_000156.txt'
    with open(f1,'r') as f:
        ls = f.readlines()
        boxes1 = [tobbx_yolo(f1,l) for l in ls]
    with open(f2,'r') as f:
        ls = f.readlines()
        boxes2 = [tobbx_yolo(f2,l) for l in ls]

    # test box pairing
    print(bbmatch(boxes1, boxes2))
        
    # test track building
    if False:
        tracks = Track(boxes1)
        tmatch(tracks, boxes2)
    
        # print tdist
        for t in tracks:
            print(t)
            if len(t.bbpairs)>1:
                print(bbdist1(t.bbpairs[0], t.bbpairs[1]))
