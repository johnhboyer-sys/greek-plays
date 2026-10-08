"""Ajax: Ajax carrying the body of Achilles, between Phoenix and Briseis (left) and two warriors
(right), from the lower picture (fig. 4) of Gerhard, Auserlesene griechische Vasenbilder III (1847),
Taf. CCXI-CCXII, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_211_ROEM_212.jpg/full/full/0/default.jpg
(4178 x 2965, a double plate across a fold; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0253)

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0). Geometry
(levelling the two pages across the fold) is not image filtering: it is numpy/scipy here, as in
alcestis.py and libation_bearers.py.

The fold. The plate is printed across two pages, folded at x = FOLD; the fold is a ridge, not a
gutter (the lines bend at it, none are lost). The frame's edges are printed straight, but in the scan
the right page stands about 30 px higher next to the fold and is about 2% shorter (tilted away from
the camera), and both edges bend near the fold. Measured on the band's palmettes, the two pages have
the same horizontal scale (period 78.3 and 78.0 px), so the levelling is vertical only: column by
column, the band's upper edge goes to row T0 and the panel's lower edge to row T0 + HP.

    python3 docs/redesign/drawings/tools/ajax.py gerhard1847bd3_211_212.jpg [qa.png]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "ajax.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
UP = 2                          # work at 2x the levelled frame's px

# The NYPL scan (the source): the frame's edges, measured: the band's upper edge (grey below N_EDGE_T,
# scanning down rows N_TOP_ROWS) and the panel's lower edge (scanning up rows N_BOTTOM_ROWS), on columns
# N_EDGE_X (nypl_edges). Levelled column by column, the band's upper edge to row N_T0 and the lower edge to N_T0 + N_HP,
# each column leaning by the mean slope of the two edges there (the sheet is turned about 0.4 degrees),
# as alcestis.py does. The levelled frame: scan columns N_X0-N_X1.
N_EDGE_X, N_EDGE_T = (1600, 4420), 120
N_TOP_ROWS, N_BOTTOM_ROWS = (1540, 1600), (3180, 3320)
N_X0, N_X1, N_T0, N_HP, N_H = 1500, 4500, 60.0, 1667.0, 1800
# Heidelberg's scan (patches the tear): the plate across two pages, folded at H_FOLD; levelled column by
# column (vertical only: the two pages have the same horizontal scale, palmette period 78.3 and 78.0 px)
H_FOLD = 2040                   # the fold in the scan (x), where both edges kink
SX0, SX1, SY0 = 1040, 3140, 1000   # Heidelberg's levelled frame: scan columns SX0-SX1
EDGE_X = (1080, 3120)           # columns the edges are measured on
EDGE_T = 70                     # grey: an edge is where the plate falls below this
TOP_ROWS = (1020, 1090)         # the band's upper border line lies in these rows (scanned downward)
BOTTOM_ROWS = (2250, 2400)      # the panel's lower edge (the ground stripe's foot) in these (scanned upward)
T0, HP = 70.0, 1268.0           # the levelled band edge (row) and the frame's height (the left page's, far from the fold)
H_OUT = 1420                    # rows in Heidelberg's levelled frame
# The NYPL sheet tore along its left-hand fold, from the top of the band through Briseis' fillet, ear and
# braid to her neck, and below that the fold leaves a faint grey hairline (it would read as an incision
# in her robe). The strip (levelled NYPL px: row, centre x, half width, joined straight) is filled from
# Heidelberg's scan, whose fold lies elsewhere: Heidelberg's levelled frame mapped onto NYPL's by
# HEID_TO_NYPL (a homography from SIFT matches round the strip, median error 0.9 px), its tones
# matched to NYPL's channel by channel (a table from the pixels of a ring TEAR_RING px round the strip).
TEAR = [(0, 803, 11), (165, 803, 11), (175, 801, 19), (345, 801, 19), (355, 802, 10), (600, 801, 10),
        (620, 799, 4), (1000, 797, 4), (1380, 795, 4), (1800, 792, 4)]
TEAR_RING = 40
TEAR_WIN = 160
HEID_TO_NYPL = ((1.27426448, 6.54126212e-04, 44.2696083), (-2.73266661e-03, 1.29116360, -23.1440338),
                (-1.63900371e-05, -3.58221171e-06, 1.0))
# the panel, as drawn (levelled px): just below the band's lower line (its foot wavers 264-271), the
# ground stripe's top edge, the side lines' inner edges (x a quartic in y, fitted within 2.4 px)
BAND_Y, STRIPE_Y = 273.0, 1710.0
LEFT = (6.299651e-12, -4.3421863e-08, 0.00023169255, -0.46540408, 362.69867)
RIGHT = (-9.344963e-11, 4.6584007e-07, -0.00098566804, 0.96516175, 2463.7811)
BOX = (40, 180, 2940, 1715)     # the work box in the levelled frame (x0, y0, x1, y1)
# the dark mass over Ajax's shoulders (Achilles' shield on his back, and a bar rising past it) rises into
# the band; there it is the black inside the shield's printed top edge (MASS_CIRCLE: centre x, y and
# radius, fitted to it within 1.4 px, dropping the columns where palmette tips touch it) and inside the
# bar's edges (MASS_BAR, placed on them at 4x), up to MASS_TOP
MASS_CIRCLE = (1494.08, 462.59, 247.4)
MASS_BAR = [(1379.5, 189.5), (1391.0, 189.5), (1426.0, 232.0), (1440.0, 290.0), (1403.0, 290.0)]
MASS_TOP = 189.0
DARK, WHITE = 122, 205          # grey (lightly blurred): black below DARK, the added white above WHITE
WHITE_MIN = 35                  # levelled px^2: smaller white is a speck
AUTO_GROUND = 5200              # levelled px^2: clay areas this large are ground
POCKETS = []                    # pockets of ground the figures close in (a point in each, levelled px)
FIG_MIN = 700                   # levelled px^2: smaller pieces on the ground are inscriptions and specks
INC_T, INC_W = 32, 1.4          # incisions: lighter than the Minimum-then-Maximum by INC_T; drawn INC_W px wide
DL_T, DL_ABS, LINE_W = 22, 175, 1.5   # thin dark lines: darker than the Maximum-then-Minimum by DL_T and than DL_ABS
WHITE_LINE = 185                # grey: on the white, a line is darker than this
CLAY_W = 3.0                    # levelled px: reserved clay is at least this wide
WHITE_DOT = 135                 # grey: a dot on the white darker than this is kept (pupil 108; specks 173 and up)
WHITE_EDGE = 3.0                # levelled px: the plate's line beside the white within this gives way to the white's edge line
WHITE_GROW, WHITE_REACH, WHITE_SMOOTH, WHITE_ALONG = 178, 6.0, 1.0, 9.0   # white_outline (grey, levelled px)
WHITE_R = 4                     # levelled px: on the white, lines are thinner than this (the grey iris is wider)
HAND_BOX = (558, 1012, 628, 1112)
HAND_AREA = [(566, 1012), (566.5, 1040), (567.5, 1055), (570, 1062), (570.5, 1094), (573, 1099), (576.5, 1097.5),
             (578.5, 1100), (582.5, 1104), (587, 1103), (590.5, 1105), (595, 1107), (598.5, 1104), (603, 1099),
             (614, 1092), (628, 1060), (628, 1012)]
HAND_LINES = [[(577, 1046), (578, 1064), (578, 1081), '-', (577, 1090), '-', (576, 1098)],
              [(587, 1044), (587, 1060), (589, 1080), (591, 1092), (592, 1104)],
              [(598, 1043), (598, 1070), (598, 1100)],
              [(609, 1025), (613.5, 1031), (618, 1036)],
              [(610, 1035), (610.5, 1048), (611, 1060)]]
FOLD_LINES, FOLD_HALF = [(2382, 630, 960)], 4
WORN = [(2376, 630, 2436, 990)]
MARKS_FILE = Path(__file__).parent / "ajax_marks.png"
MARKS_ORIGIN = (117, 185)       # levelled px of the marks layer's top-left pixel
WHITE_HOLE = 300                # levelled px^2: parts the white closes in smaller than this are on it (an eye)
THIN = 4.0                      # levelled px: black parts thinner than this are drawn as lines
HATCH_WIN, HATCH_SD, HATCH_MEAN, HATCH_MIN = 7, (12, 40), (120, 185), 150
# hatch_strokes (see there)
HATCH_DIP, HATCH_RIDGE, HATCH_ALONG, HATCH_ANGLE, HATCH_W, HATCH_SAME, HATCH_EDGE = 2.5, 1.0, 15, 12, 1.6, 2.2, 1.5
HATCH_N, HATCH_COH = 8, 0.8
# joining broken lines: ends pointing at each other within JOIN_ANGLE degrees (over their last JOIN_RUN
# levelled px), at most JOIN_MAX apart, where the plate's contrast along the gap holds at JOIN_C; a free
# end runs on to the black when it points at it within REACH levelled px
JOIN_RUN, JOIN_ANGLE, JOIN_MAX, JOIN_C, REACH = 4, 15, 10, 14, 3
RIM = 2.0                       # levelled px: the clay round the figures on the dark theme
ANGLES = tuple(range(0, 180, 15))   # Motion Blur directions (degrees)
ALONG = 4                       # levelled px: the Motion Blur's length
LINE_R = 7                      # levelled px: the Minimum/Maximum radius that finds the thin lines


def edges(g):
    """The band's upper edge and the panel's lower edge at every column SX0-SX1 (scan px, sub-pixel),
    each side of the fold smoothed on its own (the fold bends them in a sharp V)."""
    gs = ndi.gaussian_filter(g, 0.8)

    def cross(p, start, step):    # first index where p falls below EDGE_T, sub-pixel
        i = np.where(p < EDGE_T)[0]
        if not len(i) or i[0] == 0:
            return np.nan
        i = i[0]
        return start + step * ((i - 1) + (p[i - 1] - EDGE_T) / (p[i - 1] - p[i]))

    xs = np.arange(*EDGE_X)
    top = np.array([cross(gs[TOP_ROWS[0]:TOP_ROWS[1], x], TOP_ROWS[0], 1) for x in xs])
    bot = np.array([cross(gs[BOTTOM_ROWS[1]:BOTTOM_ROWS[0]:-1, x], BOTTOM_ROWS[1], -1) for x in xs])
    cols = np.arange(SX0, SX1, dtype=float)
    out = []
    for e in (top, bot):
        full = np.empty_like(cols)
        for side in (xs <= H_FOLD, xs >= H_FOLD):
            x, v = xs[side], e[side]
            ok = ~np.isnan(v)
            # a column where a figure or a speck crosses the line reads off it: drop readings more than
            # 3 px from the running median, then smooth
            med = ndi.median_filter(np.interp(x, x[ok], v[ok]), 21)
            ok &= np.abs(v - med) <= 3
            sm = ndi.gaussian_filter1d(np.interp(x, x[ok], v[ok]), 4, mode='nearest')
            sel = (cols <= H_FOLD) if side[0] else (cols >= H_FOLD)
            full[sel] = np.interp(cols[sel], x, sm)
        out.append(full)
    return out


def level_heid(img):
    """Heidelberg's scan levelled: columns SX0-SX1, H_OUT rows; the band's upper edge at row T0, the
    panel's lower edge at row T0 + HP."""
    g = np.asarray(Image.fromarray(img).convert('L'), np.float32)
    top, bot = edges(g)
    v = np.arange(H_OUT, dtype=float)
    X = np.broadcast_to(np.arange(SX0, SX1, dtype=float), (H_OUT, SX1 - SX0))
    Y = top[None] + (v[:, None] - T0) * (bot - top)[None] / HP
    out = np.stack([ndi.map_coordinates(img[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)


def nypl_edges(g):
    """The NYPL frame's two edges (see N_*) at every scan column N_X0-N_X1: the readings, those more
    than 3 px off their running median dropped (figures, specks), smoothed over 40 px (the paper bends
    a little at its old folds, so no one curve fits), and run on straight past the readings' ends
    (a line fitted to their last 200 px)."""
    gs = ndi.gaussian_filter(g, 0.8)

    def cross(p, start, step):
        i = np.where(p < N_EDGE_T)[0]
        if not len(i) or i[0] == 0:
            return np.nan
        i = i[0]
        return start + step * ((i - 1) + (p[i - 1] - N_EDGE_T) / (p[i - 1] - p[i]))

    xs = np.arange(*N_EDGE_X, 5)
    top = np.array([cross(gs[N_TOP_ROWS[0]:N_TOP_ROWS[1], x], N_TOP_ROWS[0], 1) for x in xs])
    bot = np.array([cross(gs[N_BOTTOM_ROWS[1]:N_BOTTOM_ROWS[0]:-1, x], N_BOTTOM_ROWS[1], -1) for x in xs])
    cols = np.arange(N_X0, N_X1, dtype=float)
    out = []
    for e in (top, bot):
        ok = ~np.isnan(e)
        med = ndi.median_filter(np.interp(xs, xs[ok], e[ok]), 21)
        ok &= np.abs(e - med) <= 3
        x, v = xs[ok], e[ok]
        sm = ndi.gaussian_filter1d(np.interp(np.arange(x[0], x[-1] + 1, 5), x, v), 8, mode='nearest')
        xg = np.arange(x[0], x[-1] + 1, 5)
        lo, hi = np.polyfit(xg[:40], sm[:40], 1), np.polyfit(xg[-40:], sm[-40:], 1)
        out.append(np.where(cols < xg[0], np.polyval(lo, cols),
                            np.where(cols > xg[-1], np.polyval(hi, cols), np.interp(cols, xg, sm))))
    return out


def level(img):
    """The NYPL scan levelled (see N_*): columns N_X0-N_X1, N_H rows."""
    g = np.asarray(Image.fromarray(img).convert('L'), np.float32)
    top, bot = nypl_edges(g)
    cols = np.arange(N_X0, N_X1, dtype=float)
    # the columns' lean: the edges' mean slope, smoothed over 400 px (a vertical leans with the sheet,
    # not with each little bend of its edge)
    lean_c = ndi.gaussian_filter1d((np.gradient(top) + np.gradient(bot)) / 2, 80, mode='nearest')
    U, V = np.meshgrid(cols, np.arange(N_H, dtype=float))
    X = U.copy()
    for _ in range(4):   # the edges are read at the source column, which the lean moves
        t, b = np.interp(X, cols, top), np.interp(X, cols, bot)
        Y = t + (V - N_T0) * (b - t) / N_HP
        X = U - np.interp(X, cols, lean_c) * (Y - (t + b) / 2)
    out = np.stack([ndi.map_coordinates(img[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)


def mend_tear(nyp, heid):
    """The NYPL levelled frame with the TEAR strip filled from Heidelberg's levelled frame (see TEAR)."""
    H, W = nyp.shape[:2]
    ys = np.arange(H, dtype=float)
    ty, tx, th = (np.array(v, float) for v in zip(*TEAR))
    # the homography, then the leftover offset along the strip: measured by phase correlation in windows
    # TEAR_WIN px square every 50 px down it (the plates differ a little from place to place), smoothed
    hw = cv2.warpPerspective(heid, np.array(HEID_TO_NYPL), (W, H), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    gn = ndi.gaussian_filter(np.asarray(Image.fromarray(nyp).convert('L'), np.float32), 1.0)
    gh = ndi.gaussian_filter(np.asarray(Image.fromarray(hw).convert('L'), np.float32), 1.0)
    cy = np.arange(TEAR_WIN // 2, H - TEAR_WIN // 2, 50)
    sh = []
    for y in cy:
        x = int(np.interp(y, ty, tx))
        sl = (slice(y - TEAR_WIN // 2, y + TEAR_WIN // 2), slice(x - TEAR_WIN // 2, x + TEAR_WIN // 2))
        a, b = gn[sl].copy(), gh[sl].copy()
        # (the strip itself left out of the measure: the tear and the crease are not in Heidelberg)
        cols = np.abs(np.arange(TEAR_WIN) - TEAR_WIN // 2) <= np.interp(y, ty, th) + 2
        a[:, cols], b[:, cols] = a[:, ~cols].mean(), b[:, ~cols].mean()
        win = cv2.createHanningWindow((TEAR_WIN, TEAR_WIN), cv2.CV_32F)
        (sx, sy), _ = cv2.phaseCorrelate(b, a, win)
        sh.append((sx, sy))
    sh = ndi.median_filter(np.array(sh), size=(5, 1), mode='nearest')
    sh = ndi.gaussian_filter1d(sh, 1.5, axis=0, mode='nearest')
    dxs, dys = np.interp(ys, cy, sh[:, 0]), np.interp(ys, cy, sh[:, 1])
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    hw = cv2.remap(hw, X - dxs[:, None].astype(np.float32), Y - dys[:, None].astype(np.float32),
                   cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    dx = np.abs(np.arange(W)[None, :] - np.interp(ys, ty, tx)[:, None])
    half = np.interp(ys, ty, th)[:, None]
    strip, ring = dx <= half, (dx > half + 2) & (dx <= half + TEAR_RING)
    out = nyp.astype(np.float32)
    # the tones: for each of Heidelberg's levels, the median NYPL level at the same place in the ring
    # (both lightly blurred, so a px of misregistration counts less), made non-decreasing
    for c in range(3):
        hb = np.round(ndi.gaussian_filter(hw[..., c], 1.5)[ring]).astype(int)
        nb = ndi.gaussian_filter(out[..., c], 1.5)[ring]
        lv = np.unique(hb)
        med = np.array([np.median(nb[hb == v]) for v in lv])
        cnt = np.array([(hb == v).sum() for v in lv])
        lv, med = lv[cnt >= 20], med[cnt >= 20]
        lut = np.maximum.accumulate(np.interp(np.arange(256), lv, med))
        hw[..., c] = np.interp(hw[..., c], np.arange(256), lut)
    wgt = np.clip((half + 2 - dx) / 2, 0, 1)[..., None]   # 1 in the strip, falling to 0 over 2 px
    out = out * (1 - wgt) + hw * wgt
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def plates(lev, box):
    """PhotoCraft's images of the levelled frame's `box` (x0, y0, x1, y1), at UP: the plate in grey (up),
    lightly blurred (gs); gs smoothed along the lines (along): Motion Blur over ALONG levelled px at
    ANGLES directions, of which each pixel keeps the one farthest from their mean (a line, dark or
    light, keeps its tone when blurred along itself and fades across), so close strokes of a hatching
    stay apart while each evens out (LESSONS: smooth along each stroke first); and its local contrast
    over LINE_R levelled px: its Minimum then Maximum (opened; along less it is the light lines) and
    its Maximum then Minimum (closed; it less along is the dark lines). The mean and the choice per
    pixel are numpy."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    r = LINE_R * UP // 2
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(lev).save(t / "lev.png")
        pc(t / "lev.png", t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        for i, a in enumerate(ANGLES):
            pc(t / "gs.png", t / f"mb{i}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ALONG * UP}))
        mean = sum(grey(t / f"mb{i}.png") for i in range(len(ANGLES))) / len(ANGLES)
        along, best = mean.copy(), np.zeros_like(mean)
        for i in range(len(ANGLES)):
            m = grey(t / f"mb{i}.png")
            far = np.abs(m - mean) > best
            along[far], best[far] = m[far], np.abs(m - mean)[far]
        Image.fromarray(np.clip(np.round(along), 0, 255).astype(np.uint8)).save(t / "along.png")
        rs = WHITE_R * UP // 2
        pc(t / "gs.png", t / "closed_s.png", ("filter.other.maximum", {"radius": rs, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": rs, "preserve": "squareness"}))
        pc(t / "gs.png", t / "opened_gs.png", ("filter.other.minimum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.maximum", {"radius": r, "preserve": "squareness"}))
        pc(t / "along.png", t / "opened.png", ("filter.other.minimum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.maximum", {"radius": r, "preserve": "squareness"}))
        pc(t / "along.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        return {k: grey(t / f"{k}.png") for k in ("up", "gs", "along", "opened", "opened_gs", "closed", "closed_s")}


def skeleton_paths(mask):
    """The centre lines of `mask` as ordered (y, x) paths, split where lines meet; a closed loop comes
    as one path whose ends are the same point."""
    sk = morphology.skeletonize(mask)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    node = sk & (nb != 2)                       # ends and junctions
    H, W = sk.shape
    seen = np.zeros_like(sk)
    steps = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def nbrs(y, x):
        return [(y + dy, x + dx) for dy, dx in steps if 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]]

    paths = []
    for y, x in np.argwhere(node):
        for q in nbrs(y, x):
            if node[q] and (q < (y, x)):
                paths.append(np.array([(y, x), q]))   # two nodes side by side: once
                continue
            if node[q] or seen[q]:
                continue
            path, prev, cur = [(y, x)], (y, x), q
            while True:
                path.append(cur)
                if node[cur]:
                    break
                seen[cur] = True
                nxt = [n for n in nbrs(*cur) if n != prev and not seen[n] and n not in path[-3:]]
                if not nxt:
                    break
                nn = [n for n in nxt if node[n]]
                prev, cur = cur, (nn or nxt)[0]
            paths.append(np.array(path))
    for y, x in np.argwhere(sk & ~node & ~seen):  # loops with no node
        if seen[y, x]:
            continue
        path, prev, cur = [], None, (y, x)
        while cur is not None and not seen[cur]:
            seen[cur] = True
            path.append(cur)
            nxt = [n for n in nbrs(*cur) if n != prev and not seen[n]]
            prev, cur = cur, (nxt[0] if nxt else None)
        path.append(path[0])
        paths.append(np.array(path))
    return paths


def smooth_path(p, sigma):
    """A path (y, x) smoothed along its length (Gaussian, `sigma` px), its ends kept where they are (a
    loop smoothed round)."""
    p = p.astype(float)
    if len(p) < 4:
        return p
    if (p[0] == p[-1]).all():
        q = ndi.gaussian_filter1d(p[:-1], sigma, axis=0, mode='wrap')
        return np.vstack([q, q[:1]])
    q = ndi.gaussian_filter1d(p, sigma, axis=0, mode='nearest')
    # pin the ends, easing the smoothing in over `sigma` px so a line still meets what it met
    t = np.minimum(np.arange(len(p)), np.arange(len(p))[::-1])[:, None]
    a = np.clip(t / max(2 * sigma, 1), 0, 1)
    return p * (1 - a) + q * a


def draw_paths(shape, paths, widths):
    """The paths (y, x at UP) drawn round-ended, each `widths[i]` work px wide: a pixel is ink when its
    centre lies within half the width of the path (measured to points 0.2 px apart along it)."""
    m = np.zeros(shape, bool)
    for w in sorted(set(widths)):
        pts = []
        for p, pw in zip(paths, widths):
            if pw != w:
                continue
            if len(p) == 1:
                pts.append(p.astype(float))
                continue
            seg = np.diff(p, axis=0)
            n = np.maximum(np.ceil(np.hypot(*seg.T) / 0.2).astype(int), 1)
            for a, d, k in zip(p[:-1], seg, n):
                pts.append(a + np.arange(k)[:, None] / k * d)
            pts.append(p[-1:].astype(float))
        if not pts:
            continue
        P = np.vstack(pts)
        r = w / 2
        near = np.zeros(shape, bool)
        ij = np.clip(P.round().astype(int), 0, np.array(shape) - 1)
        near[ij[:, 0], ij[:, 1]] = True
        near = ndi.binary_dilation(near, iterations=int(np.ceil(r)) + 1)
        cand = np.argwhere(near)
        d, _ = cKDTree(P).query(cand.astype(float), distance_upper_bound=r + 0.5)
        hit = cand[d <= r]
        m[hit[:, 0], hit[:, 1]] = True
    return m


def free_ends(paths, sk):
    """The free ends of the paths (ends of a skeleton line, not junctions): (path index, which end,
    point, outward unit direction over its last JOIN_RUN levelled px)."""
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    out = []
    for i, p in enumerate(paths):
        if len(p) < 3 or (p[0] == p[-1]).all():
            continue
        k = min(len(p) - 1, JOIN_RUN * UP)
        for end, q, r in ((0, p[0], p[k]), (1, p[-1], p[-1 - k])):
            if nb[tuple(q)] == 1:
                d = (q - r).astype(float)
                out.append((i, end, q.astype(float), d / max(np.hypot(*d), 1e-9)))
    return out


def join_and_reach(paths, sk, contrast, stop):
    """Segments that join a broken line and run a stopped one on: two free ends that point at each
    other (within JOIN_ANGLE degrees, both ways) across at most JOIN_MAX levelled px of plate whose
    `contrast` holds at JOIN_C or more (median) are joined straight; a free end that points at `stop`
    (the black) within REACH levelled px is run on to it. Returns the segments as paths (y, x)."""
    ends = free_ends(paths, sk)
    segs, used = [], set()
    if ends:
        P = np.array([e[2] for e in ends])
        cos = np.cos(np.radians(JOIN_ANGLE))
        pairs = sorted(cKDTree(P).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(P[ij[0]] - P[ij[1]])))
        for a, b in pairs:
            if a in used or b in used or ends[a][0] == ends[b][0]:
                continue
            v = P[b] - P[a]
            u = v / np.hypot(*v)
            if ends[a][3] @ u < cos or ends[b][3] @ -u < cos:
                continue
            t = np.linspace(0, 1, max(int(np.hypot(*v)), 2) + 1)
            q = P[a][None] + t[:, None] * v[None]
            if np.median(ndi.map_coordinates(contrast, q.T, order=1)) < JOIN_C:
                continue
            segs.append(q)
            used |= {a, b}
    H, W = stop.shape
    for k, (i, end, q, d) in enumerate(ends):
        if k in used:
            continue
        for step in range(2, REACH * UP + 1):
            y, x = np.round(q + step * d).astype(int)
            if not (0 <= y < H and 0 <= x < W):
                break
            if stop[y, x]:
                segs.append(np.linspace(q, q + step * d, step + 1))
                break
    return segs


def even_lines(mask, width, sigma=1.5, min_len=0, max_width=None, contrast=None, stop=None):
    """The lines in `mask` redrawn along their centre lines, smoothed along each line (`sigma` levelled
    px), at an even width (levelled px): `width`, or with max_width, each line's own median width
    (from its centre to its edge in the mask, in steps of a quarter px), no less than `width` and no
    more than `max_width`. A thresholded line's ragged edge and a pixel skeleton's zigzag both go.
    Paths shorter than `min_len` levelled px that end free at both ends are dropped (grain). With
    `contrast` and `stop`, broken lines are joined and stopped ones run on (join_and_reach)."""
    sk = morphology.skeletonize(mask)
    raw = skeleton_paths(mask)
    if contrast is not None:
        extra = join_and_reach(raw, sk, contrast, stop)
    keep = [p for p in raw if not min_len or len(p) >= min_len * UP or (p[0] == p[-1]).all()]
    if max_width:
        dt = ndi.distance_transform_edt(mask)
        widths = [round(4 * np.clip(np.median(2 * dt[tuple(p.T)] - 1) / UP, width, max_width)) / 4 * UP
                  for p in keep]
    else:
        widths = [width * UP] * len(keep)
    paths = [smooth_path(p, sigma * UP) for p in keep]
    if contrast is not None:
        paths += extra
        widths += [width * UP] * len(extra)
    return draw_paths(mask.shape, paths, widths)


def hatch_strokes(al, gs, hatch, fig):
    """The strokes of the hatched bands (shields' rims, fillets), each drawn straight across its band.
    The plate rules a band's hatching parallel all round it, 4-5 levelled px apart, but not as one exact
    ruling (fitted as one, the lines drifted off the strokes), so each band is read on its own:
      - its angle: the axial mean of its pieces of stroke (darker than their surroundings by HATCH_DIP);
      - the plate blurred along that angle over HATCH_ALONG levelled px (PhotoCraft Motion Blur), which
        joins each stroke's dots into a ridge and blurs the rest; the ridges are what lies HATCH_RIDGE
        under their surroundings (HATCH_WIN levelled px), inside the band;
      - each ridge's centre line, if it runs within HATCH_ANGLE degrees of the angle, fitted straight and
        run out both ways to the band's edge or the first black, as the plate's strokes run edge to edge;
      - strokes found twice (within HATCH_SAME levelled px side to side, overlapping) count once.
    Drawn HATCH_W levelled px wide. Returns the strokes and the bands drawn this way. (UP px; the blur in
    PhotoCraft, the rest numpy.)"""
    H, W = al.shape
    m = ndi.uniform_filter(al, HATCH_WIN * UP)
    st = ndi.binary_opening((al < m - HATCH_DIP) & hatch, structure=np.ones((2, 2)))
    # the bands: the hatched clay (closed over its gaps in main), inside the figure, less the black
    bands = hatch & fig & ~(gs < DARK - 20)
    zl, nz = ndi.label(bands)
    lab, _ = ndi.label(st, structure=np.ones((3, 3)))
    pieces = {}
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float) + (sl[0].start, sl[1].start)
        if len(p) < 4 * UP:
            continue
        c = p.mean(0)
        w, v = np.linalg.eigh(np.cov((p - c).T))
        if np.sqrt(w[1] / max(w[0], 1e-3)) < 2.5:
            continue
        b = zl[tuple(np.round(c).astype(int))]
        if b:
            pieces.setdefault(b, []).append(np.arctan2(v[1, 1], v[0, 1]))
    black = gs < DARK - 20
    segs = []
    used = np.zeros_like(hatch)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(np.clip(np.round(gs), 0, 255).astype(np.uint8)).save(t / "gs.png")
        for b, angs in sorted(pieces.items()):
            # a band is hatching only if its pieces agree on one angle (HATCH_COH, the length of their mean
            # axial direction) and are many (HATCH_N): hair, a white part's soft edge and folds do not
            z = np.mean(np.exp(2j * np.array(angs)))
            if len(angs) < HATCH_N or abs(z) < HATCH_COH:
                continue
            used |= zl == b
            a = np.angle(z) / 2      # stroke direction: (y, x) = (cos a, sin a)
            u = np.array([np.cos(a), np.sin(a)])
            ps_angle = float(np.degrees(np.arctan2(-u[0], u[1])))         # PhotoCraft: counterclockwise from +x
            pc(t / "gs.png", t / "mb.png", ("filter.blur.motionBlur", {"angle": round(ps_angle, 2),
                                                                         "distance": HATCH_ALONG * UP}))
            mb = grey(t / "mb.png")
            zone = zl == b
            to_edge = ndi.distance_transform_edt(zone)
            ridge = (mb < ndi.uniform_filter(mb, HATCH_WIN * UP) - HATCH_RIDGE) & zone
            for path in skeleton_paths(ridge):
                if len(path) < 3 * UP:
                    continue
                q = path.astype(float)
                c = q.mean(0)
                # (a ridge along the band's edge is its outline, drawn as such: not a stroke)
                if np.median(to_edge[tuple(path.T)]) < HATCH_EDGE * UP:
                    continue
                w, v = np.linalg.eigh(np.cov((q - c).T))
                d = v[:, 1]
                if abs(d @ u) < np.cos(np.radians(HATCH_ANGLE)):
                    continue
                ends = []
                for sgn in (-1, 1):
                    e = c.copy()
                    for _ in range(int(60 * UP / 0.5)):
                        ne = e + sgn * d * 0.5
                        yi, xi = np.round(ne).astype(int)
                        if not (0 <= yi < H and 0 <= xi < W) or not zone[yi, xi] or black[yi, xi]:
                            break
                        e = ne
                    ends.append(e)
                segs.append(np.array(ends))
    order = sorted(range(len(segs)), key=lambda k: -np.hypot(*(segs[k][1] - segs[k][0])))
    keep = []
    for k in order:
        a0, b0 = segs[k]
        mid = (a0 + b0) / 2
        same = False
        for j in keep:
            c0, d0 = segs[j]
            L = np.hypot(*(d0 - c0))
            uu = (d0 - c0) / max(L, 1e-9)
            if abs((mid - c0) @ np.array([-uu[1], uu[0]])) < HATCH_SAME * UP and -2 * UP <= (mid - c0) @ uu <= L + 2 * UP:
                same = True
                break
        if not same:
            keep.append(k)
    return draw_paths(hatch.shape, [segs[k] for k in keep], [HATCH_W * UP] * len(keep)), used


def white_outline(on_white, gs, fig):
    """The white's outline as smooth curves on the plate's printed line. The white prints smaller than
    its outline (on the shin 4-6 levelled px inside the printed line, on the nose and hand 2-3), so its
    edge alone would leave clay between the two. The white's edge (its mask smoothed, WHITE_SMOOTH
    levelled px, traced at half) is followed; from each point the plate is read outward along the normal
    up to WHITE_REACH levelled px for the printed line (the first dip darker than WHITE_GROW); the
    offsets, smoothed along the curve (median, then Gaussian WHITE_ALONG levelled px), move the curve onto
    the line, so a missed dip does not jag it. Returns the curves (y, x at UP) and the area they close.
    (numpy and skimage: curve fitting, not image filtering)"""
    from skimage import measure
    sm = ndi.gaussian_filter(on_white.astype(np.float32), WHITE_SMOOTH * UP)
    H, W = gs.shape
    paths, area = [], np.zeros_like(on_white)
    for c in measure.find_contours(sm, 0.5):
        if len(c) < 8 * UP:
            continue
        closed_c = np.allclose(c[0], c[-1])
        mode = 'wrap' if closed_c else 'nearest'
        tg = np.gradient(ndi.gaussian_filter1d(c, 2, axis=0, mode=mode), axis=0)
        nrm = np.stack([-tg[:, 1], tg[:, 0]], 1)
        nrm /= np.maximum(np.hypot(*nrm.T), 1e-9)[:, None]
        # outward: towards lower values of the smoothed mask
        probe = c + nrm
        if np.mean(ndi.map_coordinates(sm, probe.T, order=1)) > 0.5:
            nrm = -nrm
        steps = np.arange(0, WHITE_REACH * UP + 0.01, 0.5)
        prof = np.stack([ndi.map_coordinates(gs, (c + d * nrm).T, order=1, mode='nearest') for d in steps], 1)
        off = np.zeros(len(c))
        for k, pr in enumerate(prof):
            for j in range(1, len(pr) - 1):
                if pr[j] < WHITE_GROW and pr[j] <= pr[j - 1] and pr[j] <= pr[j + 1]:
                    off[k] = steps[j]
                    break
                if pr[j] < DARK:      # the black: the white meets it here
                    break
        off = ndi.gaussian_filter1d(ndi.median_filter(off, size=int(WHITE_ALONG * UP) | 1, mode=mode),
                                    WHITE_ALONG * UP / 2, mode=mode)
        q = c + off[:, None] * nrm
        paths.append(q)
        if closed_c:
            area |= lw.polygon_mask(on_white.shape, q[:, ::-1])
    return paths, area


def write_svg(lines, body, out, title, desc):
    """The house format (as linework.trace_svg writes it, and seven.py): 1000 units tall, the body path
    under the lines, traced at the work px."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def traced(g, pts, width):
    """The plate's own dark line between hand-placed points (levelled px), followed by a least-cost path
    along its darkest ridge, `width` levelled px wide, at UP (as trojan_women_menelaus.py)."""
    # ('-' between two points joins them straight, where the print is too faint to follow)
    P = np.array([((x - BOX[0]) * UP, (y - BOX[1]) * UP) for x, y in (q for q in pts if q != '-')], float)
    pad = 6 * UP
    x0, y0 = int(P[:, 0].min()) - pad, int(P[:, 1].min()) - pad
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.7 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    it = iter(P)
    path = lw.livewire(cost, [lw.STRAIGHT if q == '-' else tuple(np.subtract(next(it), (x0, y0))) for q in pts])
    yx = np.c_[path[:, 1] - 0.5 + y0, path[:, 0] - 0.5 + x0]
    return draw_paths(g.shape, [smooth_path(yx, 1.5 * UP)], [width * UP])


def main(src, heid, qa=None, dump=None):
    lev = mend_tear(level(np.asarray(Image.open(src).convert('RGB'))),
                    level_heid(np.asarray(Image.open(heid).convert('RGB'))))
    P = plates(lev, BOX)
    g, gs, opened, closed, al = P['up'], P['gs'], P['opened'], P['closed'], P['along']
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + BOX[0], (yy + 0.5) / UP + BOX[1]    # levelled px
    disk = lambda r: morphology.disk(round(r * UP))  # noqa: E731

    # outside the panel: the band above its lower line, the ground stripe (the feet stand on its top
    # edge), the side lines and the paper beyond them
    outside = (py < BAND_Y) | (py >= STRIPE_Y) | (px < np.polyval(LEFT, py)) | (px > np.polyval(RIGHT, py))
    black0 = gs < DARK
    # line and palmettes drop away, and grown back as far as the opening took it
    # but where the dark mass rises into the band (MASS_*), its black there
    cx, cy, cr = MASS_CIRCLE
    inside = (np.hypot(px - cx, py - cy) <= cr) | lw.polygon_mask(px.shape, (np.array(MASS_BAR) - BOX[:2]) * UP)
    outside &= ~(black0 & inside & (py < BAND_Y) & (py >= MASS_TOP))

    white = ndi.binary_opening((gs > WHITE) & ~outside, structure=disk(1.3))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > WHITE_MIN * UP * UP)[lab]

    # hatched clay (the shields' rims, the fillets): its strokes print paler than DARK, so it would pass for
    # ground; it is clay whose local spread (over HATCH_WIN levelled px; numpy) is HATCH_SD[0]-HATCH_SD[1]
    # round a mean tone of HATCH_MEAN (plain ground spreads about 5, an edge between black and clay more
    # than 40), opened so the thin band along an edge goes, at least HATCH_MIN levelled px^2
    solid0 = ndi.binary_opening(black0, structure=disk(2.6))
    w = HATCH_WIN * UP
    m = ndi.uniform_filter(gs, w)
    sd = np.sqrt(np.maximum(ndi.uniform_filter(gs * gs, w) - m * m, 0))
    hatch = (sd > HATCH_SD[0]) & (sd < HATCH_SD[1]) & (m > HATCH_MEAN[0]) & (m < HATCH_MEAN[1]) & ~outside
    hatch = ndi.binary_closing(ndi.binary_opening(hatch, structure=disk(1.3)), structure=disk(1.3))
    lab, _ = ndi.label(hatch)
    hatch &= (np.bincount(lab.ravel()) > HATCH_MIN * UP * UP)[lab]
    # (and its gaps closed: where the strokes run nearly along the band the spread test misses patches)
    hatch = morphology.remove_small_holes(ndi.binary_closing(hatch, structure=disk(4)),
                                          max_size=400 * UP * UP) & ~outside & ~solid0

    # ground: the clay, opened so thin lines do not join it; its large areas and the listed pockets
    clay = ndi.binary_opening(~black0 & ~white & ~outside & ~hatch, structure=disk(2.6))
    lab, _ = ndi.label(clay)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[round((y - BOX[1]) * UP), round((x - BOX[0]) * UP)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]

    # the figures: all else in the panel; specks on the ground (the inscriptions, stray marks) go
    fig = ndi.binary_fill_holes(~ground & ~outside) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=disk(0.7))
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) > FIG_MIN * UP * UP)[lab]
    white &= fig
    # incisions (light lines in the black) and the thin dark lines (on the white, the clay bands, the
    # ground inside the figures), each redrawn along its smoothed centre line at an even width
    solid = ndi.binary_opening(black0, structure=disk(2.6))
    # (the incisions on the plate as printed, lightly blurred: the along-the-line blur smears an eye's
    # small rings into one)
    inc_raw = ((gs - P['opened_gs']) > INC_T) & ndi.binary_closing(black0, structure=disk(2.6)) & ~white & fig
    on_white = morphology.remove_small_holes(white, max_size=WHITE_HOLE * UP * UP) & fig
    # Briseis' lower hand (HAND_*): its white printed out of register, so clay strips run beside each
    # finger line and the line finder made a muddle of them. In HAND_BOX the hand is HAND_AREA (placed
    # on the plate at 10x: its edges against the clay; against the robe it stops at the black) and its
    # lines are the plate's own, traced along their ridges between HAND_LINES' points (seven.py's feet)
    hb = np.zeros_like(fig)
    hx0, hy0, hx1, hy1 = [round((v - o) * UP) for v, o in zip(HAND_BOX, BOX[:2] * 2)]
    hb[hy0:hy1, hx0:hx1] = True
    hand = lw.polygon_mask(fig.shape, (np.array(HAND_AREA, float) - BOX[:2]) * UP) & ~solid & ~outside
    hand_lines = np.zeros_like(fig)
    for pts in HAND_LINES:
        hand_lines |= traced(g, pts, LINE_W)
    hand_lines &= ndi.binary_dilation(hand, iterations=UP) & hb
    on_white = np.where(hb, hand, on_white)
    white = np.where(hb, hand, white)
    fig |= hand
    dark_raw = ((closed - al) > DL_T) & (al < DL_ABS) & ~solid & fig & ~on_white
    # and on the white (eyes, mouths, fingers), anything darker than WHITE_LINE: the white with the small
    # parts it closes in (an eye, under WHITE_HOLE levelled px^2), less a px at its edge
    dark_raw |= (gs < WHITE_LINE) & ((P['closed_s'] - gs) > DL_T) & ndi.binary_erosion(on_white, structure=disk(0.7))
    # the hatched bands: their strokes drawn straight (hatch_strokes); the other finders keep out of them
    strokes, hatched = hatch_strokes(al, gs, hatch, fig)
    near_h = ndi.binary_dilation(hatched, iterations=UP)
    dark_raw &= ~near_h
    # the NYPL sheet's old fold prints a light streak down the black (FOLD_LINES: x, y0, y1, levelled px,
    # found as the one long vertical streak that is no line of the picture), and beside it the print of the
    # plain black shield is worn to a mottle (WORN, boxes): not incisions
    for fx, fy0, fy1 in FOLD_LINES:
        inc_raw &= ~((np.abs(px - fx) <= FOLD_HALF) & (py >= fy0) & (py <= fy1))
    for wx0, wy0, wx1, wy1 in WORN:
        inc_raw &= ~((px >= wx0) & (px <= wx1) & (py >= wy0) & (py <= wy1))
    inc = even_lines(inc_raw, INC_W, sigma=2.0, min_len=2.6)
    darkl = even_lines(dark_raw, LINE_W, sigma=2.0, min_len=2.6, max_width=THIN, contrast=closed - al,
                       stop=ndi.binary_opening(black0, structure=disk(THIN / 2)))
    # the black, lightly opened (specks of the print go; the thin black between close incisions, as in
    # an eye's rings, stays), less the incisions; on the white only the lines found there
    # The black is the figure less its white, its incisions, and its reserved clay (the clay at least
    # CLAY_W levelled px wide: an incision is narrower), not the plate's dark as thresholded: the black
    # between an eye's close rings prints paler than DARK and would drop out
    reserved = ndi.binary_opening(fig & ~black0 & ~white, structure=disk(CLAY_W / 2))
    black = fig & ~on_white & ~inc & ~reserved
    # the white's outline where it meets the ground: a line just outside it (the plate prints a faint
    # line there), as in seven.py
    # (the white with what it closes in: specks of the print in the white are no edge), on the plate's
    # printed line round it (white_outline); the figure runs out to that line
    wpaths, warea = white_outline(on_white, gs, fig)
    fig_in = fig.copy()
    fig |= warea & ~outside
    wline = draw_paths(fig.shape, wpaths, [LINE_W * UP] * len(wpaths)) & ~outside
    # one line there: the plate's own faint line beside the white (printed 1-2 px off the white's edge,
    # and broken) gives way to it
    darkl &= ~(~on_white & (ndi.distance_transform_edt(~on_white) <= (WHITE_REACH + 1) * UP))
    # dark dots on the white (a pupil) as printed, darker than WHITE_DOT: the line redraw drops marks
    # this small
    dots = ndi.binary_opening((gs < WHITE_DOT) & ndi.binary_erosion(on_white, structure=disk(0.7)), structure=disk(0.5))
    darkl &= ~hb
    dots &= ~hb
    lines = ((black | darkl | strokes | dots | hand_lines) & fig) | wline
    # John's corrections (2026-10-08), drawn over the whole pass in PhotoCraft (show4/ajax_corrections.pcraft,
    # layer "John Trace"; MARKS_FILE holds them as he drew them: 1 green = take the ink out, 2 blue = ink).
    # His layer is at UP px with its origin at MARKS_ORIGIN (levelled px), so it maps 1:1 onto the work px.
    # Green also takes out the figure's area where the ink he removed lay outside it (an outline he moved);
    # blue brings the figure's area out under his lines, so they keep their clay on the dark theme.
    mk = np.asarray(Image.open(MARKS_FILE))
    ox, oy = [round((v - o) * UP) for v, o in zip(MARKS_ORIGIN, BOX[:2])]
    green, blue = np.zeros_like(fig), np.zeros_like(fig)
    sy, sx = slice(max(oy, 0), min(oy + mk.shape[0], H)), slice(max(ox, 0), min(ox + mk.shape[1], W))
    msub = mk[sy.start - oy:sy.stop - oy, sx.start - ox:sx.stop - ox]
    green[sy, sx], blue[sy, sx] = msub == 1, msub == 2
    fig &= ~(green & lines & ~fig_in)
    lines = (lines & ~green) | blue
    fig |= blue & ~outside
    body = ndi.distance_transform_edt(~fig) <= RIM * UP
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), hatch=hatch, on_white=on_white, hatched=hatched, darkl=darkl, fig=fig, ground=ground, white=white, lines=lines,
                            inc_raw=inc_raw, dark_raw=dark_raw, black0=black0)

    info = write_svg(
        lines, body, OUT,
        title='Ajax carrying the body of Achilles',
        desc='Line drawing after the 1847 plate of an archaic black-figure amphora (Gerhard, Auserlesene '
             'griechische Vasenbilder III, Taf. CCXI-CCXII, 4); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:5])
