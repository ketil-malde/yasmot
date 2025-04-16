#!/usr/bin/env python3

# Main program

# Usage:
#  -c, --consensus
#    Generate consensus annotation per image
#  -s, --stereo
#    Match detections in stereo pairs
#  -t, --track=True/False
#    Extract tracks from video frames/sequential stills

import argparse
from parse import parse


def intpair(s):
    """Parse a pair of integers from the command line"""
    w, h = parse("{:d},{:d}", s)
    if w is None or h is None:
        print(f'Error: can\'t parse {s} as a pair of integers')
        exit(255)
    else:
        return (int(w), int(h))


desc = """Track detected objects, optionally linking stereo images and/or
          merging independent detections into a consensus"""


def make_args_parser():
    parser = argparse.ArgumentParser(prog='yasmot', description=desc, add_help=True)  # false?

    # Modes of operation
    parser.add_argument('--consensus', '-c', action='store_const', default=False, const=True,
                        help="""Output consensus annotation per image.""")
    parser.add_argument('--stereo', '-s', action='store_const', default=False, const=True,
                        help="""Process stereo images.""")

    # Tracking
    parser.add_argument('--track', default='True', action=argparse.BooleanOptionalAction,
                        help="""Generate tracks from video frames or seuqential stills.""")
    parser.add_argument('--max_age', '-m', default=None, type=int,
                        help="""Maximum age to search for old tracks to resurrect.""")
    parser.add_argument('--time_pattern', '-t', default='{}', type=str,
                        help="""Pattern to extract time from frame ID.""")
    parser.add_argument('--scale', default=1.0, type=float, help="""Size of the search space to link detections.""")
    parser.add_argument('--interpolate', default=False, action=argparse.BooleanOptionalAction, help="""Generate virtual detections by interpolating""")
    parser.add_argument('--unknown_class', '-u', default=None, type=str, help="""Class to avoid in consensus output""")
    parser.add_argument('--shape', default=(1228, 1027), type=intpair, help="""Image dimensions, width and height.""")
    parser.add_argument('--output', '-o', default=None, type=str, help="""Output file or directory""")

    parser.add_argument('FILES', metavar='FILES', type=str, nargs='*',
                        help='Files or directories to process')
    return parser

import sys

def main():
    global args
    parser = make_args_parser()
    args = parser.parse_args()

    rnheader = "frame_id\tx\ty\tw\th\tlabel\tprob"

    # Define (trivial) functions for generating output
    if args.output is None:
        def output(line):         sys.stdout.write(line + '\n')
        def pred_output(line):    sys.stdout.write(line + '\n')
        def tracks_output(line):  sys.stdout.write(line + '\n')
        def closeup(): pass
    else:
        of = open(args.output + '.frames', 'w')
        tf = open(args.output + '.pred', 'w')
        tr = open(args.output + '.tracks', 'w')
        def output(line):          of.write(line + '\n')
        def pred_output(line):   tf.write(line + '\n')
        def tracks_output(line):   tr.write(line + '\n')
        def closeup():
            of.close()
            tf.close()
            tr.close()

    ##################################################
    # Perform tracking
    from frames import get_frames
    from tracking import track, bbdist_track, bbdist_stereo, bbdist_pair, summarize_probs, process_tracks
    from definitions import frameid, bbshow, getcls
    from parser import show_frames

    input_frames = get_frames(args)

    if args.track:
        # todo: if pattern/enumeration is given, insert empty frames
        if args.stereo:
            metric = bbdist_pair
            # def firstframe(t): return t.bblist[0][0].frameid if t.bblist[0][0] is not None else t.bblist[0][1].frameid
        else:
            metric = bbdist_track

        def firstframe(t): return frameid(t.bblist[0])

        ts = track(input_frames, metric, args)
        ts.sort(key=firstframe)

        # print(f'*** Created number of tracks: {len(ts)}, total bboxes {len([b for f in ts for b in f.bblist])}')

        # maybe eliminate very short tracks?
        for x in ts:
            tracks_output(f'Track: {x.trackid}')
            for b in x.bblist:
                tracks_output(bbshow(b))
            tracks_output('')

        fs, ss = process_tracks(ts, args.interpolate)
        track_ann = {}
        for s in ss:
            cls, prb, res = summarize_probs(ss[s])
            track_ann[s] = cls
            pred_output(f'track: {s} len: {sum([len(v) for v in ss[s].values()])} prediction: {cls} prob: {prb:.5f} logits: {res}')

        output('# frame_id\tx\ty\tw\th\ttrack\tprob\tlabel')
        for f in fs:
            for b in f.bboxes:
                # todo: output class too
                output(bbshow(b) + f'\t{track_ann[int(getcls(b))]}')

    elif args.stereo:  # not tracking, stereo frames
        # just output input_frames (::[Frame])
        dashes = '-\t' * 6 + '-'
        output('# ' + rnheader + '\t' + rnheader + '\tsimilarity')
        for x in input_frames:
            for a, b in x.bboxes:  # assuming -s here?
                astr = bbshow(a) if a is not None else dashes
                bstr = bbshow(b) if b is not None else dashes
                dist = str(bbdist_stereo(a, b, args.scale)) if a is not None and b is not None else "n/a"
                output(astr + "\t" + bstr + "\t" + dist)
    else:
        show_frames(input_frames)

    closeup()

if __name__ == '__main__':
    main()
