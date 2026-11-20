# Convert inputs to a stream (list) of frames
from yasmot.parser import read_frames
from yasmot.definitions import Frame, BBox
from yasmot.tracking import bbmatch, summarize_probs
from yasmot.metrics import bbdist_stereo, bbdist_track

def merge_frames(fs):
    (f1, f2) = fs
    if f1.frameid != f2.frameid:
        raise ValueError(f"Error: frameids don't match: {f1.frameid} vs {f2.frameid}")
    bbpairs = bbmatch(f1.bboxes, f2.bboxes, metric=bbdist_stereo, scale=1)
    return Frame(frameid=f1.frameid, bboxes=bbpairs)


# what if one frame is missing?
def zip_frames(lists):
    """Merge lists of frames, assumed to be named in lexically increasing order"""
    cur = ''
    results = []
    idxs = [0] * len(lists)
    while any(idxs[k] < len(lists[k]) for k in range(len(lists))):
        heads = [lists[k][idxs[k]] if idxs[k] < len(lists[k]) else None for k in range(len(lists))]
        myframe = min(h.frameid for h in heads if h is not None)
        if not (cur < myframe):
            raise ValueError('Error: frames not in lecially increasing order')
        cur = myframe
        res = []

        for k, h in enumerate(heads):
            if h is not None and h.frameid == myframe:
                res.append(h)
                idxs[k] += 1
            else:
                res.append(Frame(frameid=myframe, bboxes=[]))
        results.append(res)
    return results

def consensus_frame(tup, scale=1.0, unknown_class=None):
    """Build consensus for a tuple of frames"""

    def consensus(bbpair, i):
        """Merge two bboxes"""
        bb1, bb2 = bbpair

        a = i / (i + 1)  # weight_current (bb1)
        b = 1 / (i + 1)  # weight_next (bb2)

        if bb1 is None:
            fid = bb2.frameid
            x, y, w, h, cl = bb2.x, bb2.y, bb2.w, bb2.h, bb2.cls if type(bb2.cls) is list else [(bb2.cls, bb2.pr)]
            p = bb2.pr * b
        elif bb2 is None:
            fid = bb1.frameid
            x, y, w, h, cl = bb1.x, bb1.y, bb1.w, bb1.h, bb1.cls if type(bb1.cls) is list else [(bb1.cls, bb1.pr)]
            p = bb1.pr * a
        else:
            fid = bb1.frameid
            x = a * bb1.x + b * bb2.x
            y = a * bb1.y + b * bb2.y
            w = a * bb1.w + b * bb2.w
            h = a * bb1.h + b * bb2.h
            p = bb1.pr * a + bb2.pr * b
            cl = bb1.cls
            cl.append((bb2.cls, bb2.pr))
        return BBox(fid, x, y, w, h, cl, p)

    def select_class(cplist):
        res = {}
        for (c, p) in cplist:
            if c not in res:
                res[c] = [p]
            else:
                res[c].append(p)
        cls, _1, _2 = summarize_probs(res, unknown=unknown_class)
        return unknown_class if cls is None else cls

    myframe = tup[0].frameid
    mybboxes = [bb._replace(cls=[(bb.cls, bb.pr)]) for bb in tup[0].bboxes]

    i = 0
    for t in tup[1:]:
        if t.frameid != myframe:
            raise ValueError(f'FrameID mismatch ("{t.frameid}" vs "{myframe}")')
        else:
            i = i + 1  # todo: whops, only if not None
            mybboxes = [consensus(pair, i) for pair in bbmatch(mybboxes, t.bboxes, metric=bbdist_track, scale=scale)]
    return Frame(frameid=myframe, bboxes=[bb._replace(cls=select_class(bb.cls)) for bb in mybboxes])


def get_frames(files, shape=(1228, 1027), stereo=False, consensus=False, scale=1.0, unknown_class=None):
    if consensus and stereo:
        raise ValueError('Unsupported combination of arguments: consensus and stereo cannot both be enabled.')

    ##################################################
    # Read in the detections as a stream of stereo frames
    elif stereo:
        if len(files) == 2:
            [fr_left, fr_right] = [read_frames(f, shape=shape) for f in files]
            res1 = []
            for t in zip_frames([fr_left, fr_right]):
                res1.append(merge_frames(t))
        else:
            raise ValueError(f'Wrong number of files {len(files)} instead of 2.')
    ##################################################
    # Read a list of annotations to construct consensus frames
    elif consensus:
        if not files:
            raise ValueError('No files specified.')
        fs = [read_frames(f, shape=shape) for f in files]
        res1 = []
        for t in zip_frames(fs):
            res1.append(consensus_frame(t, scale=scale, unknown_class=unknown_class))
    ##################################################
    # Just a regular annotation file/directory
    else:
        if len(files) == 1:
            res1 = read_frames(files[0], shape=shape)
        elif len(files) > 1:
            raise ValueError('Too many files, maybe you meant -s or -c?')
        else:
            raise ValueError('No files specified?  Use --help for help.')

    return res1
