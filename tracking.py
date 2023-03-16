from collections import namedtuple

from definitions import Track
from parser import tobbx_yolo
from math import exp

def deltas(bb1, bb2):
    """Helper function to extract the differences in coodinates between two bboxes"""
    return(bb1.x - bb2.x, bb1.y - bb2.y, bb1.w - bb2.w, bb1.h - bb2.h, bb1.cls == bb2.cls)

def bbdist_track(bb1, bb2, scale=1): # BBox x BBox -> Float
    """Calculate distance between bboxes
       using scale to soften/sharpen the output."""
    # print(bb1, bb2)
    dx, dy, dw, dh, dcls = deltas(bb1,bb2)
    w2, h2 = bb1.w*bb2.w, bb1.h*bb2.h

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2/w2*scale)
    yascore = exp(-dh**2/h2*scale)
    ypscore = exp(-dy**2/h2*scale)
    xpscore = exp(-dx**2/w2*scale)

    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return(xpscore * ypscore * xascore * yascore * pscore)

def bbdist_stereo(bb1, bb2, scale=1):
    """Calculate distance between bboxes in left and right stereo frames"""
    dx, dy, dw, dh, dcls = deltas(bb1,bb2)
    w2, h2 = bb1.w*bb2.w, bb1.h*bb2.h

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2/w2*scale)
    yascore = exp(-dh**2/h2*scale)
    ypscore = exp(-dy**2/h2*scale)
    xpscore = 1 # or should it be y?

    return(xpscore * ypscore * xascore * yascore)

def tdist(track, bbox): # Track x BBpairs
    """Distance between a track (i.e. its last bbox) a bbox"""
    return bbdist_track(track.bbpairs[-1], bbox)

from scipy.optimize import linear_sum_assignment
import numpy as np

def bbmatch(f1, f2, threshold=0.1, metric=bbdist_track): # [BBox] x [BBox] -> [(BBox,BBox)]
    """Match bboxes from two frames."""
    mx = np.empty((len(f1), len(f2)))
    for a in range(len(f1)):
        for b in range(len(f2)):
            mx[a,b] = metric(f1[a], f2[b])
    aind, bind = linear_sum_assignment(mx, maximize=True)
    # print(aind, bind)
    res = []
    # todo: filter on threshold
    for i in range(len(aind)):
        if mx[aind[i],bind[i]] > threshold:
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

from definitions import BBox, Frame

def xconsensus(bbs):
    """Create a consensus bbox from a list of bboxes - not used?"""
    assert len(bbs)>0, 'Error: consensus of zero bboxes?'

    def avg(ls): return sum(ls)/len(ls)
    fid = bbs[0].frameid
    x = avg([b.x for b in bbs])
    y = avg([b.y for b in bbs])
    w = avg([b.w for b in bbs])
    h = avg([b.h for b in bbs])

    # todo: how to calculate class and prob?
    probs = {}
    for b in bbs: probs[b.cls] = []
    for b in bbs: probs[b.cls].append(b.pr)

    if len(probs) == 1:
        cl = list(probs.keys())[0]
        p  = max(probs[cl])
    else:
        cl, p, res = summarize_probs(probs)

    return BBox(fid,x,y,w,h,cl,p)

from parse import parse

def assign(bbs, tracks, append_threshold = 0.1):
    """Assign bbs'es to tracks (which are modifies), return remaining bbs'es"""
    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        for b in range(len(bbs)):
            s = tdist(tracks[t], bbs[b])
            tmx[t,b] = s
    tind, bind = linear_sum_assignment(tmx, maximize=True)

    ##################################################
    # Step one: match bbs'es to tracks
    bbs_rest = []
    for i in range(len(tind)):
        tix, bix = tind[i], bind[i]
        if tmx[tix, bix] > append_threshold: # good match, add to the track
            tracks[tix].bbpairs.append(bbs[bix])
        else:
            bbs_rest.append(bbs[bix])

    # add all bbs not in bind
    for k in range(len(bbs)):
        if k not in bind:
            bbs_rest.append(bbs[k])

    # pop unmatched tracks and return them
    unmatched = []
    for l in range(len(tracks)):
        if l not in tind: unmatched.append(l)
    unmatched_tracks = []
    for l in sorted(unmatched)[::-1]:
        unmatched_tracks.append(tracks.pop(l))

    return bbs_rest, tracks, unmatched_tracks

def tmatch(bbs, tracks, old_tracks, max_age=None, time_pattern=None):
    '''Use Hungarian alg to match tracks and bboxes'''
    iou_merge_threshold = 0.8
    old_track_limit     = 5

    bbs_rest, _matched, first_unmatched = assign(bbs, tracks)
    # print(f'  *** Tmatch total number of boxes, rest: {len(bbs_rest)}, matched {len([b for t in _matched for b in t.bbpairs])}, unmatched {len([b for t in first_unmatched for b in t.bbpairs])}')

    ##################################################
    # Step two: match bbs_rest to old_tracks
    # Helper function: Extract time value from frame ID
    def extime(frid):
        t = parse(time_pattern,frid)
        if t is None:
            print(f'Error: invalid time pattern "{time_pattern}", doesn\'t match frame label "{frid}".')
            exit(255)
        else:
            return int((t)[0])

    # Determine how far back to look
    if bbs_rest != []:
        if max_age is None:
            ot_lim = min(old_track_limit, len(old_tracks))
        else:
            ot_lim = 0
            while ot_lim < len(old_tracks) and extime(bbs_rest[0].frameid) - extime(old_tracks[ot_lim].bbpairs[-1].frameid) < max_age:
                ot_lim += 1
        ot = []
        for i in range(ot_lim): ot.append(old_tracks.pop(0))

        bbs_rest, matched, second_unmatched = assign(bbs_rest, ot)
        for m in matched:
            tracks.append(m)

        for o in second_unmatched: old_tracks.insert(0,o)

    for o in first_unmatched: old_tracks.insert(0,o)

    ##################################################
    # Step three: remove spurious detections and generate new tracks
    for bb in bbs_rest:
        # if bb matches an existing track, or another bb, then merge, else:
        tracks.insert(0, Track([bb]))

from math import log

def summarize_probs(assoc):
    """From an assoc array of class -> [probs], calculate consensus prob"""
    # should probably take into account autoregressive properties and whatnot, but...
    res = {}
    num = len(assoc)+1
    other = 0  # maintain an "other" category
    for cl in assoc:
        res[cl] = 0
    # for each prob p:
    #   multiply the corresponding res with p
    #   multipy all other classes plus the 'other' class with (1-p)/n
    for cl in assoc:
        # print('- ', cl,assoc[cl])
        for r in res:
            for p in assoc[cl]:
                if p<=0 or p>1:
                    print(f'Whops: p={p}')
                # Set floor and ceiling for p
                if p<0.001: p=0.001
                if p>0.999: p=0.999
                if cl==r:
                    res[r] += log(p)
                else:
                    res[r] += log((1.0-p)/num)
                other      += log((1.0-p)/num)
    # return max class and prob
    cur = None
    maxlogit = -999999999
    for r in res:
        if res[r] > maxlogit: # remember the best
            cur = r
            maxlogit = res[r]
    totp = 0
    for r in res:
        totp += exp(res[r]-maxlogit)
    totp += exp(other-maxlogit)
    return cur, 1/totp, res

def process_tracks(tracks, interpolate=False):
    """Turn a set of tracks back into a set of frames, and a set of
       annotations, where each bbox is ID'ed with track number"""
    # assumption: tracks sorted by first frameid
    frames = []
    cur = []     # [[BBox]]
    tnum = 0
    tstats = {}
    for t in tracks:
        curframe = t.bbpairs[0].frameid

        # output all frames from cur until caught up
        def first(c): return c[0].frameid
        if cur != []:
            myfid = min([first(c) for c in cur])
            while myfid < curframe:
                # select out all myfids and build frame
                mybbs = [c[0] for c in cur if first(c) == myfid]
                frames.append(Frame(frameid=myfid, bboxes=mybbs))
                # purge myfids from cur
                c0 = [c[1:] for c in cur if first(c) == myfid]
                rest = [c for c in cur if first(c) != myfid]
                cur = [c for c in c0 + rest if c != []]
                if cur == []: break
                myfid = min([first(c) for c in cur])

        def setid(bbox, label): return BBox(frameid=bbox.frameid, x=bbox.x, y=bbox.y, w=bbox.w, h=bbox.h, cls=label, pr=bbox.pr)
        cur.insert(0,[setid(b,str(tnum)) for b in t.bbpairs])
        tstats[tnum] = {}
        for b in t.bbpairs: tstats[tnum][b.cls] = []
        for b in t.bbpairs: tstats[tnum][b.cls].append(b.pr)
        # how to summarize this?
        tnum += 1

    # process rest of cur (copy from above)
    while cur != []:
        myfid = min([first(c) for c in cur])
        mybbs = [c[0] for c in cur if first(c) == myfid]
        frames.append(Frame(frameid=myfid, bboxes=mybbs))
        # purge myfids from cur
        c0 = [c[1:] for c in cur if first(c) == myfid]
        rest = [c for c in cur if first(c) != myfid]
        cur = [c for c in c0 + rest if c != []]

    return frames, tstats

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
                print(bbdist_track(t.bbpairs[0], t.bbpairs[1]))
