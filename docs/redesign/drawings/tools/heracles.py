"""Heracles (Euripides): Herakles drawing his bow, in a lion-skin cap and cloak, his quiver and shield
behind him, from the left panel of Gerhard, Trinkschalen und Gefässe des Königlichen Museums zu
Berlin II (Berlin, 1850), Taf. XXI, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1850bd2%3AV_Tafel_21.jpg/full/full/0/default.jpg
(2950 x 2311; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1850bd2/0055)
The right panel (Poseidon, the vase's other side) is not drawn; nor are the panel's frame and the
meander band he stands on.

Made with PhotoCraft (John, 2026-10-07), as tools/trojan_women_menelaus.py: every image step runs in
`photocraft-cli` (0.2.0): the crop, the enlargement, the grey, the blurs, the Maximum and Minimum
filters and the thresholds. numpy only combines the masks PhotoCraft made (labels, unions, the
difference of two images, hysteresis) and measures (the bowstring's centres). The SVG is written by
linework.trace_svg.

Plate -> drawing, as for Trojan Women: the plate prints the black ground black, so the figure's
outline comes free.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of
    ground the figure closes in (POCKETS). Smaller dark areas inside the figure are paint.
  - The figure is every clay area the ground leaves larger than FIG_MIN and darker than paper: the
    panel holds no other.
    Below the meander band's top edge is outside (BOTTOM): his soles stand on a thin strip of black
    above it.
  - The bowstring crosses the ground as a clay line a px or two wide: drawn along its measured centres
    (STRINGS) and given a clay rim on the dark theme (rim_lines), as Hippolytus' was.
  - Lines: the plate's dark lines inside the figure (local contrast), the faint brown lines (the lion's
    fur, the anatomy) along curves fitted to them, the outline, and the plate's solid paint.
  - Dark theme: the figure's area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/heracles.py gerhard1850bd2_taf21.jpg [qa.png]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from trojan_women_menelaus import join_breaks  # noqa: E402
import trojan_women_menelaus as tw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "heracles.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 34, 150, 1304, 1858     # crop in plate px: the panel inside its left, top and right edges
# the meander band's top edge: its first clay row, y = a + b x (plate px; fitted along the band, the
# feet left out, within 0.9 px); outside below it
BOTTOM = (1844.56, 0.01258)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the panel's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
PAPER = 185
# pockets of ground the figure closes in (a point in each, plate px)
POCKETS = []
WALLS = []
WALL_W = 1.5
LINE_DARK = 100
LINE_MIN = 1.5
HANDS = []
HAND_EDGE = 1.2
# the eye, the front foot's toes and the line on its ankle (boxes, plate px). The eye's outline, iris ring and pupil are lines
# 2 px wide with 2 px of clay between them, which the local-contrast finder ran together (a heavy
# ring); the toe lines it broke into pieces, and the joins across them came out as thick bars. Here
# the lines are the plate's paint at its own width, darker than FACE_DARK after a light blur (as
# hippolytus.py's faces), and the pupil, a dot 2-3 px across, is kept
FACES = [(510, 512, 568, 548), (690, 1795, 805, 1852), (668, 1712, 702, 1752)]
FACE_DARK = 85
# the bowstring where it crosses the ground (plate px): from the bow's upper tip to the drawing hand,
# and from where it leaves the cloak to the lower tip. Its centre is measured every row (the light
# ridge's centroid within STRING_SEARCH px of the straight line between the ends) and fitted by a
# quadratic, so the print's grain does not wiggle it; STRING_W plate px wide
# (it runs into the bow's edge above y 219, a px from it: the search stops there, and stays within 2 px
# so the bow's clay does not pull it). Where it touches the bow (rows 214-225) its px read as the bow's
# clay and put a knot in the bow's outline: within JUNCTION (box, plate px) the bow's left edge is a
# curve (x a quadratic in y) fitted to the edge measured in the rows above and below (EDGE_ROWS; the
# first column, going right from x 926, lighter than grey 90 with two more above 120 after it (the
# string beside it is narrower), interpolated), and the figure lies right
# of it
STRINGS = [((929, 219), (828, 582)), ((881, 790), (911, 878))]
STRING_SEARCH, STRING_W = 2, 2.0
JUNCTION, EDGE_ROWS = (915, 205, 940, 236), [*range(200, 214), *range(226, 241)]
# thin clay parts (boxes, plate px): the arrow's shaft and head in front of the hand, clay 1-3 px wide
# between two lines, and the bow's lower tip: too thin for the body path's smoothing; passed to
# trace_svg as `keep`, so the dark theme shows them clay
THIN = [(1150, 490, 1304, 550), (895, 870, 940, 908)]
SOLES = 6.0                               # plate px: the strip of black under the soles is ground
# The faint lines and the joins across the print's breaks are found as on Trojan Women, with its
# settings (FAINT_*, JOIN_*, ALIGN_* in trojan_women_menelaus.py; the same UP), and one more test: a
# short faint piece must have lines round it (the strength of their direction field at the piece,
# FAINT_SUPPORT, x 1e-4): the open cloak's grain made isolated dashes (field 0.00-0.10, and 2.3-6.1
# near its edge lines), the lion's fur strokes and the torso's anatomy 0.66-33
assert tw.UP == UP
FAINT_SUPPORT = 1.0e-4
# no faint lines on the face (box, plate px): the plate prints none there, and the grain made two
NO_FAINT = (488, 470, 605, 578)
# Outline: 2.5 plate px in from the clay's edge, but no more than 0.6 of the figure's half-width there,
# so thin parts (the arrow's shaft, the bow's tips, the toes) keep clay inside it (as alcestis.py), and
# at least EDGE_MIN (as libation_bearers.py)
EDGE_MIN = 1.0
# The brown lines (the lion's fur, the anatomy, folds) print pale brown, not black: their darkest grey
# within 1.5 plate px stays above BROWN (120-160; the black lines' below 80). With BROWN_TONE they are
# drawn as a wash in the line colour at BROWN_OPACITY (class "tone"), not as black lines
# Only inside BROWN_BOX (plate px: the lion skin, the torso, the cloak at his arm, not the hand), where the plate
# prints them; elsewhere (the legs, toes, shield, quiver) a black line's thinning end passes the same
# test, and drawn as a wash it broke the line into black and grey pieces (the toes)
BROWN, BROWN_TONE, BROWN_OPACITY = 105, True, 0.45
BROWN_BOX = (150, 370, 740, 1010)
# The belt is printed purple (added colour on the vase): grey 70-135 with blue less green above
# BELT_BG (clay -48, the black lines below -30 too but darker). Inside BELT_BOX (plate px) it is
# drawn as its outline, LINE_MIN wide, with a wash at BELT_OPACITY inside it
BELT_BOX = (215, 860, 500, 940)
BELT_BG, BELT_OPACITY = -32, 0.35


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def polyline(pts):
    """Hand-placed points (plate px) joined by straight lines, a point per UP px, (x, y) at UP."""
    P = up(pts)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (path[:, ::-1] - 0.5).astype(int)
    ok = (yx[:, 0] >= 0) & (yx[:, 0] < shape[0]) & (yx[:, 1] >= 0) & (yx[:, 1] < shape[1])
    m[yx[ok, 0], yx[ok, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def bow_edge(plate):
    """The bow's left edge at the string's top (EDGE_ROWS): x = quadratic in y (plate px)."""
    pts = []
    for y in EDGE_ROWS:
        row = plate[y, 926:945]
        i = int(np.argmax((row[:-2] > 90) & (row[1:-1] > 120) & (row[2:] > 120)))   # the bow, not the string
        pts.append((926 + i - 1 + (90 - row[i - 1]) / (row[i] - row[i - 1]), y))
    P = np.array(pts)
    return np.polyfit(P[:, 1], P[:, 0], 2)


def string_centres(plate, a, b):
    """The bowstring's centre between ends a and b (plate px): per row, the centroid of the light
    ridge within STRING_SEARCH px of the line a-b, fitted by x = quadratic in y. Returns (x, y) per
    plate row."""
    (xa, ya), (xb, yb) = a, b
    ys = np.arange(min(ya, yb), max(ya, yb) + 1)
    pts = []
    for y in ys:
        xc = xa + (xb - xa) * (y - ya) / (yb - ya)
        x0 = int(round(xc)) - STRING_SEARCH
        row = plate[int(y), x0:x0 + 2 * STRING_SEARCH + 1]
        w = np.clip(row - np.median(plate[int(y), x0 - 8:x0 + 2 * STRING_SEARCH + 9]), 0, None)
        if w.sum() > 0:
            pts.append((x0 + (w * np.arange(len(w))).sum() / w.sum(), y))
    P = np.array(pts, float)
    f = np.polyfit(P[:, 1], P[:, 0], 2)
    return np.c_[np.polyval(f, ys), ys]


def faint_lines(contrast, fig, lines):
    """tw.faint_lines with the FAINT_SUPPORT test: the faint folds each drawn along a quadratic fitted
    to it, LINE_MIN wide (UP px)."""
    m = apply_hysteresis_threshold(contrast, *tw.FAINT) & fig & ~ndi.binary_dilation(lines, iterations=UP)
    lab, _ = ndi.label(m, structure=np.ones((3, 3)))
    to_edge = ndi.distance_transform_edt(fig)
    gy, gx = np.gradient(ndi.gaussian_filter(lines.astype(np.float32), UP))   # the lines' direction round
    jyy, jxx, jxy = (ndi.gaussian_filter(a, tw.FAINT_NEAR * UP) for a in (gy * gy, gx * gx, gx * gy))
    out = np.zeros_like(m)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float) + (sl[0].start, sl[1].start)
        if len(p) < 3:
            continue
        c = p.mean(0)
        w, v = np.linalg.eigh(np.cov((p - c).T))
        long_ = 4 * np.sqrt(max(w[1], 0))
        if long_ < tw.FAINT_LEN * UP or np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)) < 3:
            continue
        if np.median(to_edge[tuple(p.astype(int).T)]) < tw.FAINT_EDGE * UP:
            continue
        if long_ < 3 * tw.FAINT_LEN * UP:
            i, j = int(c[0]), int(c[1])
            ev, evec = np.linalg.eigh(np.array([[jyy[i, j], jxy[i, j]], [jxy[i, j], jxx[i, j]]]))
            if ev[1] < FAINT_SUPPORT:
                continue
            if abs(evec[:, 0] @ v[:, 1]) < np.cos(np.radians(tw.FAINT_ANGLE)):
                continue
        t, u = (p - c) @ v[:, 1], (p - c) @ v[:, 0]
        f = np.polyfit(t, u, 2 if long_ >= 3 * tw.FAINT_LEN * UP else 1)
        tt = np.linspace(t.min(), t.max(), int(t.max() - t.min()) + 2)
        q = c + tt[:, None] * v[:, 1] + np.polyval(f, tt)[:, None] * v[:, 0]
        q = q.round().astype(int)
        ok = (q[:, 0] >= 0) & (q[:, 0] < m.shape[0]) & (q[:, 1] >= 0) & (q[:, 1] < m.shape[1])
        out[q[ok, 0], q[ok, 1]] = True
    return ndi.distance_transform_edt(~out) <= LINE_MIN * UP / 2


def add_tone(svg, steps, box):
    """Washes added to a drawing written by lw.trace_svg with weight="drawn" (box: the crop box it
    returned), as paths of class "tone" in the line colour between the body and the lines, one per
    (mask, opacity) (as acharnians.py, each wash on its own). Traced at the lines' size, as drawn."""
    x0, y0, x1, y1 = box
    paths = []
    for mask, a in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(mask[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "plate.png", ("image.mode.grayscale", None))
        plate = grey(t / "plate.png")
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = (9 * UP) // 2
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        rf = (5 * UP) // 2
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "gf.png", t / "closedf.png", ("filter.other.maximum", {"radius": rf, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": rf, "preserve": "squareness"}))
        pc(src, t / "bg.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.adjustments.channelMixer", {"monochrome": True, "gray": [0, -100, 100, 50]}))
        pc(t / "gf.png", t / "lmin.png", ("filter.other.minimum", {"radius": round(1.5 * UP), "preserve": "roundness"}))
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        bg = grey(t / "bg.png") - 127.5                    # blue less green
        lmin = grey(t / "lmin.png")
        faint_c = grey(t / "closedf.png") - grey(t / "gf.png")
        dark0 = grey(t / "dark.png") < 128
        core = grey(t / "core.png") < 128
        fine = grey(t / "fine.png") < 128
        pc(t / "up.png", t / "facedark.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": FACE_DARK}))
        face_dark = grey(t / "facedark.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside: the meander band, below its top edge
    a, b = BOTTOM
    outside = (yy + 0.5) / UP - 0.5 + Y0 > a + b * ((xx + 0.5) / UP - 0.5 + X0) - 0.5

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP))
    hand = np.zeros(g.shape, bool)
    for box in HANDS:
        hx0, hy0, hx1, hy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        hand[hy0:hy1, hx0:hx1] = True
    dark = np.where(hand, ndi.binary_opening(fine, structure=morphology.disk(1)), dark)
    dark |= dark0 & (ndi.distance_transform_edt(~outside) <= SOLES * UP)   # under the soles the strip is thin
    dark &= ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2) | (yy >= H - 1)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    # (not the paper past the panel's right edge, which leans into the crop at the bottom: grey 205
    # against the clay's 150; areas whose median is lighter than PAPER: the strip is narrow, and its
    # edge's grey pulls its mean down to 180)
    med = ndi.median(g, lab, np.arange(len(sz)))
    fig &= ~(np.asarray(med) > PAPER)[lab]
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # the bowstring over the ground
    # (a plate px's centre lies UP / 2 into its UP px)
    string = np.zeros(g.shape, bool)
    for a_, b_ in STRINGS:
        string |= along(g.shape, up(string_centres(plate, a_, b_)) + UP / 2, STRING_W)
    jb = np.zeros(g.shape, bool)
    jx0, jy0, jx1, jy1 = [(v - o) * UP for v, o in zip(JUNCTION, (X0, Y0, X0, Y0))]
    jb[jy0:jy1, jx0:jx1] = True
    py, px_ = (yy + 0.5) / UP - 0.5 + Y0, (xx + 0.5) / UP - 0.5 + X0     # each px's centre in plate px
    fig = np.where(jb, fig & (px_ >= np.polyval(bow_edge(plate), py) - 0.5), fig)
    string &= ~fig

    # the belt: purple inside BELT_BOX, its holes filled and its edge smoothed
    bb = np.zeros(g.shape, bool)
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(BELT_BOX, (X0, Y0, X0, Y0))]
    bb[by0:by1, bx0:bx1] = True
    belt = bb & fig & (bg > BELT_BG) & (gl > 70) & (gl < 135)
    belt = ndi.binary_opening(ndi.binary_closing(belt, structure=morphology.disk(UP)), structure=morphology.disk(UP))
    lab, _ = ndi.label(belt)
    belt &= (np.bincount(lab.ravel()) > 500 * UP * UP)[lab]
    belt = ndi.binary_fill_holes(belt)
    belt_edge = belt & ~ndi.binary_erosion(belt, iterations=round(LINE_MIN * UP))
    belt_in = ndi.binary_erosion(belt, iterations=round(LINE_MIN * UP))

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig & ~belt_in
    nf = np.zeros(g.shape, bool)
    nx0, ny0, nx1, ny1 = [(v - o) * UP for v, o in zip(NO_FAINT, (X0, Y0, X0, Y0))]
    nf[ny0:ny1, nx0:nx1] = True
    lines |= faint_lines(faint_c, fig, lines) & fig & ~belt_in & ~nf
    lines |= join_breaks(lines, np.maximum(closed - gl, faint_c), ndi.distance_transform_edt(fig)) & fig
    face = np.zeros(g.shape, bool)
    for box in FACES:
        fx0, fy0, fx1, fy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        face[fy0:fy1, fx0:fx1] = True
    lines = np.where(face, face_dark & fig, lines)
    # every line at least LINE_MIN wide, so no thin neck breaks when the weight is evened out
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_MIN * UP / 2) & fig
    lines |= belt_edge
    solid = paint & fig & ~belt
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    dt = ndi.distance_transform_edt(fig)
    _, (iy, ix) = ndi.distance_transform_edt(~morphology.skeletonize(fig), return_indices=True)
    edge = fig & (dt <= np.maximum(np.minimum(2.5 * UP, 0.6 * dt[iy, ix]), EDGE_MIN * UP))
    edge = np.where(hand, fig & (dt <= HAND_EDGE * UP), edge)
    del dt, iy, ix
    ink = lines | solid | edge | string
    lab, _ = ndi.label(ink)
    ink &= np.where(face, (np.bincount(lab.ravel()) > 3 * UP * UP)[lab], (np.bincount(lab.ravel()) > 12 * UP * UP)[lab])
    # the brown lines: line px whose darkest grey within 1.5 plate px stays above BROWN (not the outline,
    # the solid paint or the belt's edge)
    brown = ink & ~edge & ~solid & ~belt_edge & ~string & ~face & (lmin > BROWN)
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(BROWN_BOX, (X0, Y0, X0, Y0))]
    brown[:by0] = brown[by1:] = False
    brown[:, :bx0] = brown[:, bx1:] = False
    lab, _ = ndi.label(brown)
    brown &= (np.bincount(lab.ravel()) > 3 * UP * UP)[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint,
                            string=string, brown=brown, belt=belt)
    tones = [(belt_in, BELT_OPACITY)]
    if BROWN_TONE:
        ink &= ~brown
        tones.append((brown, BROWN_OPACITY))

    # all outside the figure stays open in the dark theme, so no clay rim strays onto it, except along
    # the bowstring
    held = ~fig
    rims = ndi.binary_dilation(string, iterations=2 * UP)
    keep = np.zeros(g.shape, bool)
    for box in THIN:
        ax0, ay0, ax1, ay1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        keep[ay0:ay1, ax0:ax1] = fig[ay0:ay1, ax0:ax1]
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, rim_lines=rims, keep=keep, weight="drawn",
        title='Herakles drawing his bow',
        desc='Line drawing after the 1850 plate of a red-figure vase in Berlin (Gerhard, Trinkschalen '
             'und Gefässe des Königlichen Museums zu Berlin II, Taf. XXI); cut out and retraced.')
    add_tone(OUT, tones, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
