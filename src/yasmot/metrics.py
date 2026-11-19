from math import exp, tan, pi

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

def get_geometry(flength, cam_offset, fovx=None, fovy=None):
    xfactor = 2 * tan(fovx / 180 * pi / 2) if fovx else 0
    yfactor = 2 * tan(fovy / 180 * pi / 2) if fovy else 0

    def geom(a, b):
        if a is not None and b is not None:
            xl, wl, hl, xr, wr, hr = a.x, a.w, a.h, b.x, b.w, b.h
            xl, wl = edgecorrect(xl, wl, wr)
            xr, wr = edgecorrect(xr, wr, wl)
            z = flength * cam_offset / (xl - xr) if xl > xr else 0

            h, w = (hl + hr) / 2, (wl + wr) / 2
            width = w * xfactor * z if fovx else None
            height = h * yfactor * z if fovy else None
            return z, width, height
        else:
            return None

    return geom
