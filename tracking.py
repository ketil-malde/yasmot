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
    # print(bb1, bb2)
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
    """Distance between a track (last bbox) a set of bboxes)"""
    return bbdist1(track.bbpairs[-1], bbox)

from scipy.optimize import linear_sum_assignment
import numpy as np

def bbmatch(f1, f2, threshold=0.1, metric=bbdist1): # [BBox] x [BBox] -> [(BBox,BBox)]
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

def consensus(bbs):
    """Create a consensus bbox from a list of bboxes"""
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

# NB! Modifies tracks parameter (append)
# Might use bbmatch above for its guts?
def tmatch(bbs, tracks, old_tracks, max_age=None, time_pattern=None):
    '''Use Hungarian alg to match tracks and bboxes'''
    iou_merge_threshold = 0.8
    append_threshold    = 0.1
    old_track_limit     = 5

    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        # print('***** track=',t, '\n ->', tracks[t].bbpairs[-1])
        for b in range(len(bbs)):
            s = tdist(tracks[t], bbs[b])
            # print('  match track=', t, 'bbox=', b, 'score=', s)
            # print(bpairs[b])
            tmx[t,b] = s
    tind, bind = linear_sum_assignment(tmx, maximize=True)

    # append b[bind] to t[tind] for index pairs
    new_tracks = []
    for i in range(len(tind)):
        tix, bix = tind[i], bind[i]
        if tmx[tix, bix] > append_threshold:
            # good match, add to the track
            tracks[tix].bbpairs.append(bbs[bix])
        elif max(tmx[:,bix]) < iou_merge_threshold:
            # doesn't match any existing track
            new_tracks.append(bbs[bix])
        else:
            # duplicate of a track
            # print('*** duplicate, p=', max(tmx[:,bind[i]])) # todo which track is max index here?
            best = None
            prob = 0
            for j in range(len(tind)):
                if tmx[tind[j], bix] > prob:
                    prob = tmx[tind[j], bix]
                    best = j
            # print('ignoring:\n  ',bbs[bix],"\nbecause of\n",tracks[best].bbpairs[-1],'\np=',prob)

    # process the unmatched tracks, push to old_tracks
    for j in range(len(tracks))[::-1]:
        if j not in tind:
            old_tracks.insert(0, tracks.pop(j))

    # process unmatched bboxes
    for k in range(len(bbs)):
        if k not in bind:
            # todo: eliminate if too much IoU (double predictions)
            if len(tmx[:,k]) > 0 and max(tmx[:,k]) > iou_merge_threshold:
                # todo: make consensus annotation here?
                pass
            else:
                new_tracks.append(bbs[k])

    # merge duplicate bboxes
    for i, t in enumerate(new_tracks):
        dupidx = [j for j in range(i,len(new_tracks)) if bbdist1(t,new_tracks[j]) > iou_merge_threshold ]
        tmp_tracks = []
        for j in dupidx[::-1]:
            tmp_tracks.append(new_tracks.pop(j))
        new_tracks.insert(0,consensus(tmp_tracks))
                
    for t in new_tracks:
        # todo: limit in real time (number of frames)
        if max_age is not None:
            def extime(frid):
                t = parse(time_pattern,frid)
                if t is None:
                    print(f'Error: invalid time pattern "{time_pattern}", doesn\'t match frame label "{frid}".')
                    exit(255)
                else:
                    return int((t)[0])
            ot_lim = len([o for o in old_tracks[:old_track_limit] if extime(t.frameid) - extime(o.bbpairs[-1].frameid) < max_age])
        else:
            ot_lim = old_track_limit

        appended = False
        for j, u in enumerate(old_tracks[:ot_lim]):
            if tdist(old_tracks[j], t) > append_threshold:
                new = old_tracks.pop(j)
                new.bbpairs.append(t)
                tracks.append(new)
                appended = True
                break
        if appended == False: tracks.append(Track([t]))
    return

from math import log

def summarize_probs(assoc):
    """From an assoc array of class -> [probs], calculate consensus prob"""
    # should probably take into account autoregressive properties and whatnot, but...
    res = {}
    num = len(assoc)
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
                if p<0.0001: p=0.0001
                if p>0.9999: p=0.9999
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
                print(bbdist1(t.bbpairs[0], t.bbpairs[1]))
