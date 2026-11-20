from math import exp, tan, pi

# manually inlined below for speed
def deltas(bb1, bb2):
    """Helper function to extract the differences in coodinates between two bboxes"""
    return (bb1.x - bb2.x, bb1.y - bb2.y, bb1.w - bb2.w, bb1.h - bb2.h, bb1.cls == bb2.cls)

def find_occlusions(bboxes):
    """For each bbox in a frame, detect which edges (x_low, x_high, y_low, y_high)
    lie strictly inside another overlapping bbox in the same frame."""
    n = len(bboxes)
    occs = [(False, False, False, False)] * n
    bounds = []
    for b in bboxes:
        if b is None:
            bounds.append(None)
        else:
            bounds.append((b.x - b.w / 2, b.x + b.w / 2, b.y - b.h / 2, b.y + b.h / 2))

    for i in range(n):
        bi = bounds[i]
        if bi is None:
            continue
        ix1, ix2, iy1, iy2 = bi
        xl, xh, yl, yh = False, False, False, False
        for j in range(n):
            if i == j or bounds[j] is None:
                continue
            jx1, jx2, jy1, jy2 = bounds[j]
            # Check 2D overlap
            if ix1 < jx2 and jx1 < ix2 and iy1 < jy2 and jy1 < iy2:
                if jx1 < ix1 < jx2:
                    xl = True
                if jx1 < ix2 < jx2:
                    xh = True
                if jy1 < iy1 < jy2:
                    yl = True
                if jy1 < iy2 < jy2:
                    yh = True
        occs[i] = (xl, xh, yl, yh)
    return occs

def axis_delta(x1, w1, x2, w2, margin=0.03, clip_low=False, clip_high=False):
    """Compute position and size delta along one axis, using unclipped/outer edges
    when either box is truncated at the frame border or occluded by another box."""
    low_clipped = clip_low or (x1 - w1 / 2 < margin) or (x2 - w2 / 2 < margin)
    high_clipped = clip_high or (x1 + w1 / 2 > 1.0 - margin) or (x2 + w2 / 2 > 1.0 - margin)

    if high_clipped and not low_clipped:
        return (x1 - w1 / 2) - (x2 - w2 / 2), 0.0
    if low_clipped and not high_clipped:
        return (x1 + w1 / 2) - (x2 + w2 / 2), 0.0
    if low_clipped and high_clipped:
        return x1 - x2, 0.0
    return x1 - x2, w1 - w2

def stereo_disparity(bb_l, bb_r, margin=0.03, occ_l=None, occ_r=None):
    """Compute horizontal stereo disparity (x_left - x_right) using unclipped/outer
    edges when truncated at the frame border or occluded."""
    clip_lx = (occ_l[0] if occ_l else False) or (occ_r[0] if occ_r else False)
    clip_hx = (occ_l[1] if occ_l else False) or (occ_r[1] if occ_r else False)
    disp, _ = axis_delta(bb_l.x, bb_l.w, bb_r.x, bb_r.w, margin=margin, clip_low=clip_lx, clip_high=clip_hx)
    return disp

def edgecorrect(x, w, w2):
    """If w brings x to edge, adjust w to w2 (retained for backwards compatibility)."""
    if x + w / 2 > 0.97:
        x = x + (w2 - w) / 2
        w = w2
    if x - w / 2 < 0.03:
        x = x - (w2 - w) / 2
        w = w2
    return (x, w)

def bbdist_track(bb1, bb2, scale, occ1=None, occ2=None):  # BBox x BBox -> Float
    """Calculate similarity between bboxes across frames,
       using scale to soften/sharpen the output and outer edges when clipped/occluded."""
    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    clip_lx = (occ1[0] if occ1 else False) or (occ2[0] if occ2 else False)
    clip_hx = (occ1[1] if occ1 else False) or (occ2[1] if occ2 else False)
    clip_ly = (occ1[2] if occ1 else False) or (occ2[2] if occ2 else False)
    clip_hy = (occ1[3] if occ1 else False) or (occ2[3] if occ2 else False)

    dx, dw = axis_delta(x1, w1, x2, w2, clip_low=clip_lx, clip_high=clip_hx)
    dy, dh = axis_delta(y1, h1, y2, h2, clip_low=clip_ly, clip_high=clip_hy)

    wsq, hsq = w1 * w2 * scale, h1 * h2 * scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2 / wsq)
    yascore = exp(-dh**2 / hsq)
    ypscore = exp(-dy**2 / hsq)
    xpscore = exp(-dx**2 / wsq)

    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return (xpscore * ypscore * xascore * yascore * pscore)

def bbdist_pair(bbsA, bbsB, scale, occA=None, occB=None, sigma_d=0.05):
    """Similarity between stereo pairs of bboxes across frames.
    Uses a small discount for single-camera pairs and a bounded depth/disparity tie-breaker."""
    aL, aR = bbsA
    bL, bR = bbsB
    occA_l, occA_r = occA if occA is not None else (None, None)
    occB_l, occB_r = occB if occB is not None else (None, None)

    d1 = None if aL is None or bL is None else bbdist_track(aL, bL, scale, occ1=occA_l, occ2=occB_l)
    d2 = None if aR is None or bR is None else bbdist_track(aR, bR, scale, occ1=occA_r, occ2=occB_r)

    if d1 is None and d2 is None:
        return 0.0
    if d1 is None:
        return 0.85 * d2
    if d2 is None:
        return 0.85 * d1

    base = 0.5 * (d1 + d2)
    dispA = stereo_disparity(aL, aR, occ_l=occA_l, occ_r=occA_r)
    dispB = stereo_disparity(bL, bR, occ_l=occB_l, occ_r=occB_r)
    depth_factor = 0.6 + 0.4 * exp(-((dispA - dispB) ** 2) / (sigma_d ** 2))
    return base * depth_factor

def bbdist_stereo(bb1, bb2, scale, occ1=None, occ2=None, disp_mean=0.10, disp_sigma=0.15):
    """Calculate similarity between bboxes in left and right stereo frames."""
    x1, y1, w1, h1 = bb1.x, bb1.y, bb1.w, bb1.h
    x2, y2, w2, h2 = bb2.x, bb2.y, bb2.w, bb2.h

    clip_lx = (occ1[0] if occ1 else False) or (occ2[0] if occ2 else False)
    clip_hx = (occ1[1] if occ1 else False) or (occ2[1] if occ2 else False)
    clip_ly = (occ1[2] if occ1 else False) or (occ2[2] if occ2 else False)
    clip_hy = (occ1[3] if occ1 else False) or (occ2[3] if occ2 else False)

    disp, dw = axis_delta(x1, w1, x2, w2, clip_low=clip_lx, clip_high=clip_hx)
    dy, dh = axis_delta(y1, h1, y2, h2, clip_low=clip_ly, clip_high=clip_hy)

    wsq, hsq = w1 * w2 * scale, h1 * h2 * scale

    # these are 1 when dx, dy, dw, dh are zero, and zero as they go towards infty
    xascore = exp(-dw**2 / wsq)
    yascore = exp(-dh**2 / hsq)

    # difference in y direction should be very small, multiply by 3
    ypscore = exp(-dy**2 / hsq * 3)
    # x1 should be right of x2; wide Gaussian centered at disp_mean allows jitter near 0
    # while naturally suppressing negative or implausibly large disparities
    xpscore = exp(-((disp - disp_mean)**2) / (disp_sigma**2))

    pscore = 0.4 + min(0.6, bb1.pr, bb2.pr)

    return (xpscore * ypscore * xascore * yascore * pscore)

def get_geometry(flength, cam_offset, fovx=None, fovy=None):
    xfactor = 2 * tan(fovx / 180 * pi / 2) if fovx else 0
    yfactor = 2 * tan(fovy / 180 * pi / 2) if fovy else 0

    def geom(a, b):
        if a is not None and b is not None:
            disp = stereo_disparity(a, b)
            z = flength * cam_offset / disp if disp > 0 else 0

            h, w = (a.h + b.h) / 2, (a.w + b.w) / 2
            width = w * xfactor * z if fovx else None
            height = h * yfactor * z if fovy else None
            return z, width, height
        else:
            return None

    return geom
