from functools import lru_cache
from math import exp
from datetime import datetime
from scipy.optimize import linear_sum_assignment
import numpy as np

from yasmot.metrics import bbdist_track
from yasmot.definitions import Track

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

def _predict_single(bb_last, bb_prev, t_last, t_prev, cur_time):
    """Constant-velocity linear extrapolation for a single BBox."""
    dt_obs = t_last - t_prev
    dt_pred = cur_time - t_last
    if dt_obs <= 0 or dt_pred <= 0:
        return bb_last
    vx = (bb_last.x - bb_prev.x) / dt_obs
    vy = (bb_last.y - bb_prev.y) / dt_obs
    px = min(1.0, max(0.0, bb_last.x + vx * dt_pred))
    py = min(1.0, max(0.0, bb_last.y + vy * dt_pred))
    return BBox(
        frameid=bb_last.frameid,
        x=px,
        y=py,
        w=bb_last.w,
        h=bb_last.h,
        cls=bb_last.cls,
        pr=bb_last.pr,
    )


def predict_track(trk, cur_time=None, time_fn=None):
    """Predict a track's expected BBox (or stereo pair) at cur_time using constant velocity."""
    last = trk.bblist[-1]
    if cur_time is None or time_fn is None or len(trk.bblist) < 2:
        return last

    if type(last) is tuple:
        lefts = []
        rights = []
        for b in reversed(trk.bblist):
            if b[0] is not None and len(lefts) < 2:
                lefts.append(b[0])
            if b[1] is not None and len(rights) < 2:
                rights.append(b[1])
            if len(lefts) == 2 and len(rights) == 2:
                break
        pred_l = (
            _predict_single(lefts[0], lefts[1], time_fn(lefts[0].frameid), time_fn(lefts[1].frameid), cur_time)
            if len(lefts) == 2
            else (lefts[0] if lefts else None)
        )
        pred_r = (
            _predict_single(rights[0], rights[1], time_fn(rights[0].frameid), time_fn(rights[1].frameid), cur_time)
            if len(rights) == 2
            else (rights[0] if rights else None)
        )
        return (pred_l, pred_r)

    bb_prev = trk.bblist[-2]
    return _predict_single(last, bb_prev, time_fn(last.frameid), time_fn(bb_prev.frameid), cur_time)


def assign(bbs, tracks, scale, metric, append_threshold=0.1, cur_time=None, time_fn=None):
    """Assign bbs'es to tracks (which are modified), return remaining bbs'es"""
    tmx = np.empty((len(tracks), len(bbs)))
    for t in range(len(tracks)):
        pred = predict_track(tracks[t], cur_time=cur_time, time_fn=time_fn)
        for b in range(len(bbs)):
            tmx[t, b] = metric(pred, bbs[b], scale)
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


def tmatch(bbs, tracks, time_pred, scale, metric, cur_time=None, time_fn=None, archive_stale=False):

    # Partition all tracks by time_pred in a single pass
    cur_tracks = []
    stale_tracks = []
    for t in tracks:
        if time_pred(t):
            cur_tracks.append(t)
        else:
            stale_tracks.append(t)

    # Match new bboxes to active tracks
    bbs_rest, matched, unmatched = assign(bbs, cur_tracks, scale, metric, cur_time=cur_time, time_fn=time_fn)

    # Recombine: active tracks first (and optionally keep stale tracks in place)
    tracks[:] = matched + unmatched if archive_stale else matched + unmatched + stale_tracks

    # Create new tracks for unmatched bboxes (i.e. bbs_rest).
    global g_trackno
    for bb in bbs_rest:
        # if bb matches an existing track, or another bb, then merge, else:
        tracks.insert(0, Track(trackid=g_trackno, bblist=[bb]))
        g_trackno += 1

    return stale_tracks


def make_time_fn(pattern, is_time=False):
    """Return a cached function mapping a frame ID string to a numeric frame number or timestamp."""
    @lru_cache(maxsize=None)
    def exframeno(frid):
        if is_time:
            try:
                t = datetime.strptime(frid, pattern)
            except ValueError as e:
                raise ValueError(f'Timestamp pattern "{pattern}", doesn\'t match frame label "{frid}".') from e
            else:
                return t.timestamp()
        else:
            t = parse(pattern, frid)
            if t is None:
                raise ValueError(f'Invalid frame number pattern "{pattern}", doesn\'t match frame label "{frid}".')
            else:
                return int((t)[0])
    return exframeno


def get_time_predicate(cur_frame, max_age, pattern, is_time=False):
    """Check whether a track is still current by checking its last detection against the current frame"""
    exframeno = make_time_fn(pattern, is_time=is_time)
    cur_val = exframeno(cur_frame)

    def time_predicate(trk):
        last = trk.bblist[-1]
        return exframeno(frameid(last)) >= cur_val - max_age

    return time_predicate


def track(frames, metric=bbdist_track, scale=1.0, max_age=2, framelabel_pattern=None, timestamp=False, velocity=True):
    active_tracks = []
    finished_tracks = []
    if framelabel_pattern:
        time_fn = make_time_fn(framelabel_pattern, is_time=timestamp)
    else:
        frame_indices = {f.frameid: idx for idx, f in enumerate(frames)}
        def time_fn(frid): return frame_indices[frid]

    for i, f in enumerate(frames):
        # print(f'FrameID {f.frameid} boxes {len(f.bboxes)}')
        # def boxes(ts): return [b for t in ts for b in t.bbpairs]
        if f.bboxes:
            if framelabel_pattern:
                cur_val = time_fn(frameid(f.bboxes[0]))
                cutoff = cur_val - max_age
                def time_pred(trk): return time_fn(frameid(trk.bblist[-1])) >= cutoff
            else:
                cur_val = i
                valid_fids = {fr.frameid for fr in frames[max(0, i - max_age):i]}
                def time_pred(trk): return frameid(trk.bblist[-1]) in valid_fids
            stale = tmatch(
                f.bboxes,
                active_tracks,
                time_pred,
                scale,
                metric,
                cur_time=cur_val if velocity else None,
                time_fn=time_fn if velocity else None,
                archive_stale=True,
            )  # match bboxes to tracks (tmatch)
            if stale:
                finished_tracks.extend(reversed(stale))
        # print(f' --- Tracked boxes: {len(boxes(tracks))}, {len(boxes(old_tracks))}')
    return active_tracks + list(reversed(finished_tracks))


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
                    raise ValueError(f'Invalid probability: p={p}')
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
    for r in res:
        totp += exp(res[r] - maxlogit)
    totp += exp(other - maxlogit)
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
            raise ValueError("Interpolation: negative number of frames to insert?")

    return res


def summarize_geom(getgeom, track):
    """Given a geometry conversion function and a (stereo) track, produce stats on object geometry.
       This includes range, size, and velocities."""

    pass

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
