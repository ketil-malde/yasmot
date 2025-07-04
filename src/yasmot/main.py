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
    parser.add_argument('--unknown-class', '-u', default=None, type=str, help="""Class to avoid in consensus output""")
    parser.add_argument('--shape', default=(1228, 1027), type=intpair, help="""Image dimensions, width and height.""")
    parser.add_argument('--focal-length', '-F', default=None, type=float, help="""Camera focal length as a fraction of image width""")
    parser.add_argument('--camera-offset', '-D', default=0, type=float, help="""Distance between left and right camera.""")
    parser.add_argument('--fovx', default=None, type=float, help="""Camera horizontal field of view (degrees)""")
    parser.add_argument('--fovy', default=None, type=float, help="""Camera vertical field of view (degrees)""")

    # Tracking
    parser.add_argument('--track', default='True', action=argparse.BooleanOptionalAction,
                        help="""Generate tracks from video frames or seuqential stills.""")
    parser.add_argument('--scale', default=1.0, type=float, help="""Size of the search space to link detections.""")

    # Allowing gaps in tracks
    parser.add_argument('--interpolate', default=False, action=argparse.BooleanOptionalAction, help="""Generate virtual detections by interpolating""")
    parser.add_argument('--max-age', '-m', default=2, type=float,
                        help="""Maximum age to search for old tracks to resurrect.
                                (in seconds for time stamps, or frames for frame numbers.)""")
    parser.add_argument('--timestamp', action=argparse.BooleanOptionalAction,
                        help="""Interpret framenumber as a timestamp.""")
    parser.add_argument('--framelabel-pattern', '-P', default=None, type=str,
                        help="""Pattern to extract the frame number or time from the frame ID.""")

    # Inputs and outputs
    parser.add_argument('--output', '-o', default=None, type=str, help="""Output file or directory""")
    parser.add_argument('FILES', metavar='FILES', type=str, nargs='*',
                        help='Files or directories to process')
    return parser

import sys

def show_geom(triple):
    out = ""
    if not triple:
        out = "n/a"
    else:
        z, w, h = triple
        if not z:
            out = "n/a"
        else:
            out = f'z={z:.3f}'
            if w: out += f' w={w:.2f}'
            if h: out += f' h={h:.2f}'
    return out

def main():
    global args
    parser = make_args_parser()
    args = parser.parse_args()
    if not args.timestamp:
        args.max_age = int(args.max_age)

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
    from yasmot.frames import get_frames
    from yasmot.tracking import track, bbdist_track, bbdist_stereo, bbdist_pair, summarize_probs, process_tracks, edgecorrect, get_geometry
    from yasmot.definitions import frameid, bbshow, getcls
    from yasmot.parser import show_frames

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

        if args.stereo:
            # Note that 'label' here replaces class annotation with track number (from process_tracks())
            output('#frame_id         \txl\tyl\twl\thl\ttrack_l\tprob_l\txr\tyr\twr\thr\ttrack_r\tprob_r\tlabel')
        else:
            output('#frame_id         \tx\ty\tw\th\ttrack\tprob\tlabel')
        for f in fs:
            for b in f.bboxes:
                # todo: output class too
                output(bbshow(b) + f'\t{track_ann[int(getcls(b))]}')

    elif args.stereo:  # not tracking, stereo frames
        # just output input_frames (::[Frame])
        header = '#frame_id         \txl\tyl\twl\thl\tlabel_l  \tprob_l\txr\tyr\twr\thr\tlabel_r  \tprob_r\tsimilarity'
        if args.focal_length and args.camera_offset: header = header + '\tz-val'
        if args.fovx or args.fovy: header = header + '\tsize'
        output(header)
        get_geom = get_geometry(args.focal_length, args.camera_offset, args.fovx, args.fovy)
        for x in input_frames:
            for a, b in x.bboxes:
                sim = f'{bbdist_stereo(a, b, args.scale):.3f}' if a is not None and b is not None else " n/a"
                geom = get_geom(a, b) if args.focal_length and args.camera_offset else None
                output(bbshow((a, b)) + f'\t{sim}\t{show_geom(geom)}')
    else:
        show_frames(input_frames)

    closeup()

if __name__ == '__main__':
    main()
