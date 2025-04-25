# Convert inputs to a stream (list) of frames
from yasmot.parser import read_frames
from yasmot.definitions import error, Frame, BBox
from yasmot.tracking import bbmatch, bbdist_stereo, bbdist_track, summarize_probs


def merge_frames(fs):
    (f1, f2) = fs
    assert f1.frameid == f2.frameid, f"Error: frameids don't match: {f1.frameid} vs {f2.frameid}"
    bbpairs = bbmatch(f1.bboxes, f2.bboxes, metric=bbdist_stereo, scale=1)
    return Frame(frameid=f1.frameid, bboxes=bbpairs)


# what if one frame is missing?
def zip_frames(lists):
    """Merge lists of frames, assumed to be named in lexically increasing order"""
    cur = ''
    results = []
    while not all([t == [] for t in lists]):
        heads = [l[0] if l != [] else None for l in lists]
        tails = [l[1:] if l != [] else [] for l in lists]
        myframe = min([h.frameid for h in heads if h is not None])
        assert cur < myframe, 'Error: frames not in lecially increasing order'
        cur = myframe
        res = []

        for i in range(len(heads)):
            if heads[i] is None:
                res.append(Frame(frameid=myframe, bboxes=[]))
            elif heads[i].frameid == myframe:
                res.append(heads[i])
            else:
                res.append(Frame(frameid=myframe, bboxes=[]))
                tails[i].insert(0, heads[i])
        results.append(res)
        lists = tails
    return results

def consensus_frame(tup, args):
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
        cls, _1, _2 = summarize_probs(res, unknown=args.unknown_class)
        return args.unknown_class if cls is None else cls

    myframe = tup[0].frameid
    mybboxes = [bb._replace(cls=[(bb.cls, bb.pr)]) for bb in tup[0].bboxes]

    i = 0
    for t in tup[1:]:
        if t.frameid != myframe:
            error(f'FrameID mismatch ("{t.frameid}" vs "{myframe}")')
        else:
            i = i + 1  # todo: whops, only if not None
            mybboxes = [consensus(pair, i) for pair in bbmatch(mybboxes, t.bboxes, metric=bbdist_track, scale=args.scale)]
    return Frame(frameid=myframe, bboxes=[bb._replace(cls=select_class(bb.cls)) for bb in mybboxes])


def get_frames(args):
    if args.consensus and args.stereo:
        error('Unsupported combination of arguments:\n' + str(args))

    ##################################################
    # Read in the detections as a stream of stereo frames
    elif args.stereo:
        if len(args.FILES) == 2:
            [fr_left, fr_right] = [read_frames(f, shape=args.shape) for f in args.FILES]
            res1 = []
            for t in zip_frames([fr_left, fr_right]):
                res1.append(merge_frames(t))
        else:
            error(f'Wrong number of files {len(args.FILES)} instead of 2.')
    ##################################################
    # Read a list of annotations to construct consensus frames
    elif args.consensus:
        fs = [read_frames(f, shape=args.shape) for f in args.FILES]
        res1 = []
        for t in zip_frames(fs):
            res1.append(consensus_frame(t, args))
    ##################################################
    # Just a regular annotation file/directory
    else:
        if len(args.FILES) == 1:
            res1 = read_frames(args.FILES[0], shape=args.shape)
        elif len(args.FILES) > 1:
            error('Too many files, maybe you meant -s or -c?')
        else:
            error('No files specified?  Use --help for help.')

    return res1
