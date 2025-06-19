# from collections import namedtuple
from math import exp
from yasmot.definitions import Track

# manually inlined below for speed
def deltas(bb1, bb2):
    """Helper function to extract the differences in coodinates between two bboxes"""
    return (bb1.x - bb2.x, bb1.y - bb2.y, bb1.w - bb2.w, bb1.h - bb2.h, bb1.cls == bb2.cls)

def edgecorrect(x, w, w2):
    """If w brings x to edge, adjust w to w2"""
    if x + w / 2 > 0.97:
        x = x + (w2 - w) / 2
        w = w2
    if x - w / 2 < 0.03:
        x = x - (w2 - w) / 2
        w = w2
    return (x, w)

def bbdist_track(bb1, bb2, scale):  # BBox x BBox -> Float
    """Calculate distance between bboxes
       using scale to soften/sharpen the output."""

    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    x1, w1 = edgecorrect(x1, w1, w2)
    y1, h1 = edgecorrect(y1, h1, h2)
    x2, w2 = edgecorrect(x2, w2, w1)
    y2, h2 = edgecorrect(y2, h2, h1)

    dx, dy, dw, dh, _dcls = x1 - x2, y1 - y2, w1 - w2, h1 - h2, bb1.cls == bb2.cls  # deltas()
    wsq, hsq = w1 * w2 * scale, h1 * h2 * scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2 / wsq)
    yascore = exp(-dh**2 / hsq)
    ypscore = exp(-dy**2 / hsq)
    xpscore = exp(-dx**2 / wsq)

    # pscore = 0.19 + 2*min(0.9,bb1.pr)*min(0.9,bb2.pr)
    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return (xpscore * ypscore * xascore * yascore * pscore)

def bbdist_pair(bbsA, bbsB, scale):
    """Distance between pairs of bboxes, return averages of distances"""

    d1 = 0 if bbsA[0] is None or bbsB[0] is None else bbdist_track(bbsA[0], bbsB[0], scale)
    d2 = 0 if bbsA[1] is None or bbsB[1] is None else bbdist_track(bbsA[1], bbsB[1], scale)
    return 0.5 * (d1 + d2)

def bbdist_stereo(bb1, bb2, scale):
    """Calculate distance between bboxes in left and right stereo frames"""

    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    x1, w1 = edgecorrect(x1, w1, w2)
    y1, h1 = edgecorrect(y1, h1, h2)
    x2, w2 = edgecorrect(x2, w2, w1)
    y2, h2 = edgecorrect(y2, h2, h1)

    _dx, dy, dw, dh, _dcls = x1 - x2, y1 - y2, w1 - w2, h1 - h2, bb1.cls == bb2.cls  # deltas()
    wsq, hsq = w1 * w2 * scale, h1 * h2 * scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2 / wsq)
    yascore = exp(-dh**2 / hsq)

    # difference in y direction should be very small, multiply by 3
    ypscore = exp(-dy**2 / hsq * 3)
    # x1 should be right of x2, difference can be substantial and independent of bbox size
    xpscore = exp(-2 * (x1 - x2 - 0.05)**2)

    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return (xpscore * ypscore * xascore * yascore * pscore)

from scipy.optimize import linear_sum_assignment
import numpy as np

# Used for stereo tracks and consensus annotations
def bbmatch(f1, f2, metric, scale, threshold=0.1):  # [BBox] x [BBox] -> [(BBox,BBox)]
    """Match bboxes from two frames."""
    mx = np.empty((len(f1), len(f2)))
    for a in range(len(f1)):
        for b in range(len(f2)):
            mx[a, b] = metric(f1[a], f2[b], scale=scale)
    aind, bind = linear_sum_assignment(mx, maximize=True)
    # print(aind, bind)
    res = []
    # Filter on threshold:
    for i in range(len(aind)):
        if mx[aind[i], bind[i]] > threshold:
            res.append((f1[aind[i]], f2[bind[i]]))
        else:
            res.append((f1[aind[i]], None))
            res.append((None, f2[bind[i]]))
    for i in range(len(f1)):
        if i not in aind: res.append((f1[i], None))
    for i in range(len(f2)):
        if i not in bind: res.append((None, f2[i]))

    # todo: add assertion that all inputs are outputs once?
    return res

from parse import parse
from yasmot.definitions import BBox, Frame, g_trackno

def assign(bbs, tracks, scale, metric, append_threshold=0.1):
    """Assign bbs'es to tracks (which are modifies), return remaining bbs'es"""
    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        for b in range(len(bbs)):
            s = metric(tracks[t].bblist[-1], bbs[b], scale)
            tmx[t, b] = s
    tind, bind = linear_sum_assignment(tmx, maximize=True)

    ##################################################
    # Step one: match bbs'es to tracks
    bbs_rest = []
    for i in range(len(tind)):
        tix, bix = tind[i], bind[i]
        if tmx[tix, bix] > append_threshold:  # good match, add to the track
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


def get_time_predicate(cur_frame, max_age, pattern):
    """Check whether a track is still current by checking its last detection against the current frame"""

    def exframeno(frid):
        t = parse(pattern, frid)
        if t is None:
            print(f'Error: invalid frame number pattern "{pattern}", doesn\'t match frame label "{frid}".')
            exit(255)
        else:
            return int((t)[0])

    def time_predicate(trk):
        last = trk.bblist[-1]
        return exframeno(frameid(last)) >= exframeno(cur_frame) - max_age

    return time_predicate


def tmatch(bbs, tracks, time_pred, scale, metric):

    # Move tracks that are new enough to cur_tracks
    cur_tracks = []
    while len(tracks) > 0 and time_pred(tracks[0]):
        cur_tracks.append(tracks.pop(0))

    # Match new bboxes to tracks
    bbs_rest, matched, unmatched = assign(bbs, cur_tracks, scale, metric)

    # New tracks are: matched ++ unmatched ++ old tracks
    for t in unmatched:
        tracks.insert(0, t)
    for t in matched:
        tracks.insert(0, t)

    # Create new tracks for unmatched bboxes (i.e. bbs_rest).
    global g_trackno
    for bb in bbs_rest:
        # if bb matches an existing track, or another bb, then merge, else:
        tracks.insert(0, Track(trackid=g_trackno, bblist=[bb]))
        g_trackno += 1


def track(frames, metric, args):
    tracks = []
    for i, f in enumerate(frames):
        # print(f'FrameID {f.frameid} boxes {len(f.bboxes)}')
        # def boxes(ts): return [b for t in ts for b in t.bbpairs]
        if f.bboxes:
            if args.framenumber_pattern:
                time_pred = get_time_predicate(cur_frame=frameid(f.bboxes[0]), max_age=args.max_age, pattern=args.framenumber_pattern)
            else:
                def time_pred(trk): return frameid(trk.bblist[-1]) in [f.frameid for f in frames[max(0, i - args.max_age):i]]
            tmatch(f.bboxes, tracks, time_pred, args.scale, metric)  # match bboxes to tracks (tmatch)
        # print(f' --- Tracked boxes: {len(boxes(tracks))}, {len(boxes(old_tracks))}')
    return tracks


from math import log

def summarize_probs(assoc, num_classes=None, unknown=None):  # TODO: ignore=None
    """From an assoc array of class -> [probs], calculate consensus prob"""
    # should probably take into account autoregressive properties and whatnot, but...
    res = {}
    if num_classes is None:
        num = len(assoc) + 1
    else:
        num = num_classes
    other = 0.0  # maintain an "other" category
    for cl in assoc:
        res[cl] = 0.0
    # for each prob p:
    #   multiply the corresponding res with p
    #   multipy all other classes plus the 'other' class with (1-p)/n
    for cl in assoc:
        # print('- ', cl, assoc[cl])
        for r in res:
            for p in assoc[cl]:
                if p <= 0 or p > 1:
                    print(f'Whops: p={p}')
                # Set floor and ceiling for p
                if p < 0.001: p = 0.001
                if p > 0.999: p = 0.999
                if cl == r:
                    res[r] += log(p)
                else:
                    res[r] += log((1.0 - p) / num)
                other      += log((1.0 - p) / num)
    # return max class and prob
    cur = None
    curmax = -999999999
    maxlogit = other
    for r in res:
        if res[r] > maxlogit: maxlogit = res[r]
        if res[r] > curmax and r != unknown:
            cur = r
            curmax = res[r]
    totp = 0
    try:
        for r in res:
            totp += exp(res[r] - maxlogit)
        totp += exp(other - maxlogit)
    except OverflowError:
        print(res, other)
    return cur, 1 / totp, res

from yasmot.definitions import frameid, setid

def first(c): return frameid(c[0])

def inject(fids, f0, f1):
    '''Generate num bboxes between f0 and f1'''
    res = []
    num = len(fids)
    dx = (f1.x - f0.x) / num
    dy = (f1.y - f0.y) / num
    dw = (f1.w - f0.w) / num
    dh = (f1.h - f0.h) / num
    for i in range(num):
        if i == 0:
            res.append(f0)
        else:
            res.append(BBox(frameid=fids[i], x=f0.x + i * dx, y=f0.y + i * dy, w=f0.w + i * dw, h=f0.h + i * dh, cls=f0.cls, pr=0))
    return res

# All input tracks have the same next frameid, but may have gaps after it
# So find the max next frameid, and fill in the gaps.
def interpolate(cur_tracks):
    """Find all frameids less than max visible frameid,
       then push virtual detections on top of all tracks"""

    # process only tracks longer than one
    nz_cur_tracks = [c for c in cur_tracks if len(c) > 1]  # filter(lambda c: len(c)>1, cur_tracks)

    # add all single item tracks
    res = []
    for c in filter(lambda c: len(c) == 1, cur_tracks):
        res.append(c)

    # early bailout if no tracks
    if nz_cur_tracks == []:
        return res

    # build fidlist: a list of all seen frames until maxfid
    # TODO: for serial numbers, interpolate unseen frames as well?
    # POSSIBLE WORKAROUND: generate empty annotation files and include them?
    maxfid = max([frameid(c[1]) for c in nz_cur_tracks])
    allfids = set()
    for c in nz_cur_tracks:
        i = 0
        myfid = frameid(c[i])
        while myfid <= maxfid and i < len(c):
            allfids.add(myfid)
            myfid = frameid(c[i])
            i += 1
        allfids.add(myfid)
    fid_list = sorted(allfids)

    # Now populate them
    for c in nz_cur_tracks:
        ix0 = fid_list.index(frameid(c[0]))
        ix1 = fid_list.index(frameid(c[1]))
        if ix1 - ix0 > 1:
            res.append(inject(fid_list[ix0:ix1], c[0], c[1]) + c[1:])
        elif ix1 - ix0 == 1:
            res.append(c)
        else:
            assert False, "Interpolation: negative number of frames to insert?"

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
                cur = interpolate(cur)
            # generate all frames up to the start of track t
            while myfid < first(t.bblist):
                # select out all bboxes matching myfid and add the frame
                this = [c for c in cur if first(c) == myfid]
                rest = [c for c in cur if first(c) != myfid]
                frames.append(Frame(frameid=myfid, bboxes=[c[0] for c in this]))

                # remove the bboxes in this frame from cur
                cur = [c for c in [c[1:] for c in this] + rest if c != []]  # keep all non-empty tracks
                if cur == []: break
                myfid = min([first(c) for c in cur])

        # replace class with trackid and add new track t to cur
        cur.insert(0, [setid(b, str(t.trackid)) for b in t.bblist])

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

from yasmot.parser import tobbx_yolo

def test():
    # read two annotation files
    f1, f2 = 'data/labels/frame_000155.txt', 'data/labels/frame_000156.txt'
    with open(f1, 'r') as f:
        ls = f.readlines()
        boxes1 = [tobbx_yolo(f1, _) for _ in ls]
    with open(f2, 'r') as f:
        ls = f.readlines()
        boxes2 = [tobbx_yolo(f2, _) for _ in ls]

    # test box pairing
    print(bbmatch(boxes1, boxes2))

    # test track building
    if False:
        tracks = Track(boxes1)
        tmatch(tracks, boxes2)

        # print tdist
        for t in tracks:
            print(t)
            if len(t.bblist) > 1:
                print(bbdist_track(t.bblist[0], t.bblist[1]))
