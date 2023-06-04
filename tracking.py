from collections import namedtuple

from definitions import Track
from parser import tobbx_yolo
from math import exp

# manually inlined below for speed
def deltas(bb1, bb2):
    """Helper function to extract the differences in coodinates between two bboxes"""
    return(bb1.x - bb2.x, bb1.y - bb2.y, bb1.w - bb2.w, bb1.h - bb2.h, bb1.cls == bb2.cls)

def edgecorrect(x,w,w2):
    """If w brings x to edge, adjust w to w2"""
    if x + w/2 > 0.97:
        x = x + (w2-w)/2
        w = w2
    if x - w/2 < 0.03:
        x = x - (w2-w)/2
        w = w2
    return(x,w)

def bbdist_track(bb1, bb2, scale): # BBox x BBox -> Float
    """Calculate distance between bboxes
       using scale to soften/sharpen the output."""

    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    x1, w1 = edgecorrect(x1,w1,w2)
    y1, h1 = edgecorrect(y1,h1,h2)
    x2, w2 = edgecorrect(x2,w2,w1)    
    y2, h2 = edgecorrect(y2,h2,h1)
    
    dx, dy, dw, dh, dcls = x1 - x2, y1 - y2, w1 - w2, h1 - h2, bb1.cls == bb2.cls # deltas()
    wsq, hsq = w1*w2*scale, h1*h2*scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2/wsq)
    yascore = exp(-dh**2/hsq)
    ypscore = exp(-dy**2/hsq)
    xpscore = exp(-dx**2/wsq)

    # pscore = 0.19 + 2*min(0.9,bb1.pr)*min(0.9,bb2.pr)
    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return(xpscore * ypscore * xascore * yascore * pscore)

def bbdist_pair(bbsA, bbsB, scale):
    """Distance between pairs of bboxes, return averages of distances"""

    d1 = 0 if bbsA[0] is None or bbsB[0] is None else bbdist_track(bbsA[0], bbsB[0], scale) 
    d2 = 0 if bbsA[1] is None or bbsB[1] is None else bbdist_track(bbsA[1], bbsB[1], scale)
    return 0.5*(d1+d2)

def bbdist_stereo(bb1, bb2, scale=1):
    """Calculate distance between bboxes in left and right stereo frames"""

    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    x1, w1 = edgecorrect(x1,w1,w2)
    y1, h1 = edgecorrect(y1,h1,h2)
    x2, w2 = edgecorrect(x2,w2,w1)    
    y2, h2 = edgecorrect(y2,h2,h1)
    
    dx, dy, dw, dh, dcls = x1 - x2, y1 - y2, w1 - w2, h1 - h2, bb1.cls == bb2.cls # deltas()
    wsq, hsq = w1*w2*scale, h1*h2*scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2/wsq)
    yascore = exp(-dh**2/hsq)

    # difference in y direction should be very small, multiply by 3
    ypscore = exp(-dy**2/hsq*3)
    # x1 should be right of x2, difference can be substantial and independent of bbox size
    xpscore = exp(-2*(x1 - x2 - 0.05)**2)

    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return(xpscore * ypscore * xascore * yascore * pscore)

from scipy.optimize import linear_sum_assignment
import numpy as np

# Used only for stereo tracks, I think?
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

from definitions import BBox, Frame, g_trackno

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

def assign(bbs, tracks, scale, metric, append_threshold = 0.1):
    """Assign bbs'es to tracks (which are modifies), return remaining bbs'es"""
    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        for b in range(len(bbs)):
            s = metric(tracks[t].bblist[-1], bbs[b], scale)
            tmx[t,b] = s
    tind, bind = linear_sum_assignment(tmx, maximize=True)

    ##################################################
    # Step one: match bbs'es to tracks
    bbs_rest = []
    for i in range(len(tind)):
        tix, bix = tind[i], bind[i]
        if tmx[tix, bix] > append_threshold: # good match, add to the track
            tracks[tix].bblist.append(bbs[bix])
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

def tmatch(bbs, tracks, old_tracks, max_age, time_pattern, scale, metric):
    '''Use Hungarian alg to match tracks and bboxes'''
    iou_merge_threshold = 0.8
    old_track_limit     = 5

    ##################################################
    # Step one: match bbs'es to existing tracks
    bbs_rest, _matched, first_unmatched = assign(bbs, tracks, scale, metric)
    # print(f'  *** Tmatch total number of boxes, rest: {len(bbs_rest)}, matched {len([b for t in _matched for b in t.bblist])}, unmatched {len([b for t in first_unmatched for b in t.bblist])}')

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
            while ot_lim < len(old_tracks) and extime(bbs_rest[0].frameid) - extime(old_tracks[ot_lim].bblist[-1].frameid) < max_age:
                ot_lim += 1
        ot = []
        for i in range(ot_lim): ot.append(old_tracks.pop(0))

        bbs_rest, matched, second_unmatched = assign(bbs_rest, ot, scale, metric)
        for m in matched:
            tracks.append(m)

        for o in second_unmatched: old_tracks.insert(0,o)

    for o in first_unmatched: old_tracks.insert(0,o)

    ##################################################
    # Step three: remove spurious detections and generate new tracks
    global g_trackno
    for bb in bbs_rest:
        # if bb matches an existing track, or another bb, then merge, else:
        tracks.insert(0, Track(trackid=g_trackno, bblist=[bb]))
        g_trackno += 1

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

from definitions import frameid, setid

def first(c): return frameid(c[0])

def inject(fids, f0, f1):
    '''Generate num bboxes between f0 and f1'''
    res = []
    num = len(fids)
    dx = (f1.x - f0.x)/num
    dy = (f1.y - f0.y)/num
    dw = (f1.w - f0.w)/num
    dh = (f1.h - f0.h)/num
    for i in range(num):
        if i==0:
            res.append(f0)
        else:
            res.append(BBox(frameid=fids[i], x=f0.x+i*dx, y=f0.y+i*dy, w=f0.w+i*dw, h=f0.h+i*dw, cls=f0.cls, pr=0))
    return res

# All input tracks have the same next frameid, but may have gaps after it
# So find the max next frameid, and fill in the gaps.
def interpolate(cur_tracks):
    """Find all frameids less than max visible frameid,
       then push virtual detections on top of all tracks"""

    # process only tracks longer than one
    nz_cur_tracks = [c for c in cur_tracks if len(c) > 1] # filter(lambda c: len(c)>1, cur_tracks)

    # add all single item tracks
    res = []
    for c in filter(lambda c: len(c)==1, cur_tracks):
        res.append(c)

    # early bailout if no tracks        
    if nz_cur_tracks == []:
        return res
        
    maxfid = max([frameid(c[1]) for c in nz_cur_tracks])
    allfids = set()
    for c in nz_cur_tracks:
        i = 0
        myfid = frameid(c[i])
        while myfid <= maxfid and i<len(c):
            allfids.add(myfid)
            myfid = frameid(c[i])
            i += 1
        allfids.add(myfid)
    fid_list = sorted(allfids)

    # Now populate them
    for c in nz_cur_tracks:
        ix = fid_list.index(frameid(c[1]))
        if ix != 1:
            res.append(inject(fid_list[:ix], c[0], c[1]) + c[1:])
        else:
            res.append(c)

    return res

def process_tracks(tracks, interpol=False):
    """Turn a set of tracks back into a set of frames, and a set of
       annotations, where each bbox is ID'ed with track number"""
    # assumption: tracks sorted by first frameid
    frames = []
    cur = []     # [[BBox]] - list of tracks currently being processed
    tstats = {}
    for t in tracks:
        # output all frames from cur until caught up
        if cur != []:
            myfid = min([first(c) for c in cur])
            if interpol:
                cur=interpolate(cur)
            # generate all frames up to the start of track t
            while myfid < first(t.bblist):
                # select out all bboxes matching myfid and add the frame
                this = [c for c in cur if first(c) == myfid]
                rest = [c for c in cur if first(c) != myfid]
                frames.append(Frame(frameid=myfid, bboxes=[c[0] for c in this]))

                # remove the bboxes in this frame from cur
                cur = [c for c in [c[1:] for c in this] + rest if c != []] # keep all non-empty tracks
                if cur == []: break
                myfid = min([first(c) for c in cur])

        # replace class with trackid and add new track t to cur
        cur.insert(0,[setid(b,str(t.trackid)) for b in t.bblist])

        # add statistics for track t
        tstats[t.trackid] = {}
        if type(t.bblist[0]) is tuple:
            tbl = [b[0]for b in t.bblist if b[0] is not None] + [b[1] for b in t.bblist if b[1] is not None]
        else:
            tbl = t.bblist 
        for b in tbl: tstats[t.trackid][b.cls] = []
        for b in tbl: tstats[t.trackid][b.cls].append(b.pr)

    # out of tracks, process rest of cur (copy from above)
    while cur != []:
        myfid = min([first(c) for c in cur])
        if interpol:
            cur = interpolate(cur)
        this = [c for c in cur if first(c) == myfid]
        rest = [c for c in cur if first(c) != myfid]
        frames.append(Frame(frameid=myfid, bboxes=[c[0] for c in this]))
        cur = [c for c in [c[1:] for c in this] + rest if c != []]

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
            if len(t.bblist)>1:
                print(bbdist_track(t.bblist[0], t.bblist[1]))
