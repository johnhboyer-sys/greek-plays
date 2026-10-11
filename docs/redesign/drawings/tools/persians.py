"""Persians (Aeschylus): the Persian king flees in his chariot (WORK IN PROGRESS; docstring filled at approval).
From H. Heydemann, Hallisches Winckelmannsprogramm 8 (1883), folding plate, top frieze (Naples H 3220), Heidelberg
hwpr1883 C.jpg (3682 x 2779; Public Domain Mark 1.0).

    python3 docs/redesign/drawings/tools/persians.py C.jpg [qa.png] [dump.npz]
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

OUT = Path(__file__).resolve().parent.parent / "persians.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the whole top frieze with its stars, plants and dotted ground line (John, 2026-10-10)
X0, Y0, X1, Y1 = 180, 185, 3460, 1275
UP = 3                                    # work at 3x the plate's px: the king's face is small
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 16, 34                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 120                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.5                   # a line's core: the darkest px within CORE_R plate px (no farther:
#                                           in the curls a darker neighbour hid the fainter strokes)
SMOOTH = 0.6                              # plate px: the line mask's Gaussian, cut at half
SPECK = 2                                 # plate px^2: smaller pieces of ink are specks of the print (the
#                                           mouth's dot and the beard's are 3)
SEAL = 6
POCKETS = []
SHAFTS = []
CLOSED = []
CLOSE = 2
NEAR = 10                                 # plate px
WEIGHT = 0.00025                          # 0.8 plate px: John chose it (2026-10-10, A/B of 0.8 and 1.4 on the
#                                           king's head; he asked for "crisp and precise"); the plate's pen line is about
#                                           1-1.2 px under the scan's blur (its half-maximum width is 1.5)
WALLS = []
WALL_W = 2.0
# Hatching: the plate shades some parts (the king's cap, sleeves and belt, the chariot's rails and panel, the
# shield's rim) with hatching finer than the scan resolves (strokes 2-3 plate px apart); John (2026-10-10):
# "Even hatch lines", ruled evenly at the plate's angle and spacing. Each hatched area is given by a polygon
# drawn round it (plate px), outside its outlines and along the edge of the hair or the like where no line
# bounds it: the area is the polygon's px where the plate, blurred by DARK_S, is darker than DARK_DK below the
# paper (the paper outside the outlines and between the curls is lighter), closed and opened by a disk
# DARK_R wide, holes under HOLE filled. Inside it the plate's dark lines (STRONG, by local contrast with
# hysteresis) and marks of DOT or more are kept as printed, and the hatch is ruled at the angle (degrees, rising to the
# right) and spacing (plate px) read off the plate at 8x (its spectrum has no clear peak at this scan's
# resolution), each line COVER of the spacing wide.
STRONG = (65, 100)
DARK_S, DARK_DK, DARK_R = 1.0, 20, 1.5    # plate px, grey levels, plate px
HOLE, DOT = 80, 8                         # plate px^2
COVER = 0.3
HATCH = [
    # the king's cap: its top and knob, cut along the hair
    (50, 3.0, [(1238, 300), (1270, 300), (1305, 322), (1345, 340), (1362, 358), (1366, 368), (1334, 368),
               (1310, 365), (1285, 362), (1262, 362), (1250, 368), (1222, 368), (1228, 358), (1236, 350),
               (1234, 320)]),
    # its flap down the left side of his face, and down the right
    (10, 2.5, [(1222, 368), (1250, 368), (1248, 395), (1250, 420), (1246, 442), (1226, 442), (1222, 400)]),
    (0, 2.3, [(1334, 368), (1366, 368), (1368, 400), (1362, 445), (1345, 448), (1338, 420), (1336, 395),
              (1332, 375)]),
    # his raised sleeve, wrist to shoulder
    (-5, 2.8, [(1098, 425), (1112, 402), (1150, 425), (1185, 444), (1225, 442), (1228, 470), (1222, 505),
               (1170, 505), (1140, 490), (1110, 465), (1095, 440)]),
    # his belt, ruled along it
    (-15, 2.4, [(1194, 575), (1200, 566), (1220, 556), (1250, 559), (1282, 569), (1305, 586), (1308, 600),
                (1300, 607), (1288, 602), (1250, 592), (1220, 590), (1196, 594)]),
]


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src):
    """The plate's ink and the figures' area at UP (work px), and the plate in grey."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "src.png", t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it, so each
        # line keeps its printed width (local contrast alone took in its soft edge, and the hair's strokes
        # ran together)
        half = (closed - gl) >= HALF * (closed - core)
        ink = apply_hysteresis_threshold(np.where(half, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": SMOOTH * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    dk = np.clip(closed - gl, 0, None)
    reg, strong = hatched(dk)
    lines = ruled(reg)
    reg = reg > 0
    ink = (ink & ~reg) | (strong & reg)
    return g, gl, ink, reg, lines & reg


def hatched(dk):
    """The hatched areas (work px, numbered as HATCH), and the plate's dark lines and marks inside them."""
    from skimage.draw import polygon as poly
    strong = apply_hysteresis_threshold(dk, *STRONG)
    r = DARK_R * UP
    disk = np.hypot(*np.mgrid[-int(r):int(r) + 1, -int(r):int(r) + 1]) <= r
    dark = ndi.gaussian_filter(dk, DARK_S * UP) > DARK_DK
    dark = ndi.binary_opening(ndi.binary_closing(dark, structure=disk), structure=disk)
    reg = np.zeros(dk.shape, np.int16)
    for i, (_, _, pts) in enumerate(HATCH, 1):
        xs, ys = zip(*pts)
        rr, cc = poly((np.array(ys) - Y0 + 0.5) * UP, (np.array(xs) - X0 + 0.5) * UP, dk.shape)
        m = np.zeros(dk.shape, bool)
        m[rr, cc] = True
        m &= dark
        holes = ndi.binary_fill_holes(m) & ~m
        hl, _ = ndi.label(holes)
        m |= (np.bincount(hl.ravel()) < HOLE * UP * UP)[hl] & holes
        reg[m & (reg == 0)] = i
    sl, _ = ndi.label(strong)
    strong &= (np.bincount(sl.ravel()) >= DOT * UP * UP)[sl]
    return reg, strong


def ruled(reg):
    """Even hatch lines in each hatched area, at its HATCH angle and spacing."""
    out = np.zeros(reg.shape, bool)
    for k, sl in enumerate(ndi.find_objects(reg), 1):
        if sl is None:
            continue
        a, sp = np.radians(HATCH[k - 1][0]), HATCH[k - 1][1]
        yy, xx = np.mgrid[sl]
        u = ((xx + 0.5) / UP * np.sin(a) + (yy + 0.5) / UP * np.cos(a)) / sp % 1
        out[sl] |= (u < COVER) & (reg[sl] == k)
    return out


def shaft(gl, a, b):
    """A shaft's band (bool, work px): the paper between its two edge lines, along the centre line fitted
    to the midpoints between them (read across the shaft every 4 plate px, the darkest px on each side of
    the rough centre within 14 plate px), out to the edge lines' centres. Returns the band, its half-width
    and the fit's rms (plate px)."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a))
    n = np.array([-u[1], u[0]])
    mids, gaps = [], []
    for s in np.arange(0, np.hypot(*(b - a)), 4):
        p = a + s * u
        o = np.arange(-14, 14.01, 0.5)
        q = (p[None] + o[:, None] * n[None] - (X0, Y0)) * UP
        v = ndi.map_coordinates(gl, [q[:, 1], q[:, 0]], order=1)
        lo, hi = o < 0, o > 0
        i, j = np.argmin(np.where(lo, v, 1e9)), np.argmin(np.where(hi, v, 1e9))
        if v[i] < 150 and v[j] < 150 and 4 < o[j] - o[i] < 26:
            mids.append(p + (o[i] + o[j]) / 2 * n)
            gaps.append(o[j] - o[i])
    mids = np.array(mids)
    t = (mids - a) @ u
    f = np.polyfit(t, (mids - a) @ n, 1)
    res = (mids - a) @ n - np.polyval(f, t)
    hw = np.median(gaps) / 2
    band = np.zeros(gl.shape, bool)
    (cx0, cy0), (cx1, cy1) = [(np.floor((np.minimum(a, b) - 20 - (X0, Y0)) * UP)).astype(int).clip(0),
                              (np.ceil((np.maximum(a, b) + 20 - (X0, Y0)) * UP)).astype(int)]
    yy, xx = np.mgrid[cy0:cy1, cx0:cx1]
    px, py = (xx + 0.5) / UP + X0 - a[0], (yy + 0.5) / UP + Y0 - a[1]
    along_, across = px * u[0] + py * u[1], px * n[0] + py * n[1]
    band[cy0:cy1, cx0:cx1] = ((along_ >= 0) & (along_ <= np.hypot(*(b - a))) &
                              (np.abs(across - np.polyval(f, along_)) <= hw))
    return band, hw, float(np.sqrt(np.mean(res ** 2)))


def walls(shape):
    """WALLS as a mask (work px), WALL_W plate px wide."""
    m = np.zeros(shape, bool)
    for pts in WALLS:
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            k = int(np.hypot(xb - xa, yb - ya) * UP * 2) + 2
            xs, ys = np.linspace(xa, xb, k), np.linspace(ya, yb, k)
            m[np.round((ys - Y0) * UP).astype(int), np.round((xs - X0) * UP).astype(int)] = True
    return ndi.distance_transform_edt(~m) <= WALL_W * UP / 2 if m.any() else m


def figure(ink, gl):
    """The figures' area: the paper the ink closes off from the ground round the group by passages narrower
    than SEAL (the watershed areas but for those reaching the crop's edge and the POCKETS), the shafts, the
    small closed parts, and the ink touching them."""
    from skimage.segmentation import watershed
    paper = ~(ink | walls(ink.shape))
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(SEAL * UP)))
    ws = watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    out = out[out > 0]
    ground = np.isin(ws, out)
    for x, y in POCKETS:
        k = ws[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k and k not in out, f'pocket point {(x, y)} is not on paper the group closes'
        ground |= ws == k
    clay = paper & ~ground
    for a, b in SHAFTS:
        band, hw, rms = shaft(gl, a, b)
        print('shaft', a, b, 'half-width', round(hw, 2), 'rms', round(rms, 2))
        clay |= band & paper
    for bx0, by0, bx1, by1 in CLOSED:
        sl = np.s_[(by0 - Y0) * UP:(by1 - Y0) * UP, (bx0 - X0) * UP:(bx1 - X0) * UP]
        c = ndi.binary_closing(ink[sl], structure=morphology.disk(CLOSE * UP))
        clay[sl] |= ndi.binary_fill_holes(c) & ~c & paper[sl]
    # (the ink they close in too: the shield's star, wider than the reach)
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~(ground & paper)


def main(src, qa=None, dump=None):
    g, gl, ink, reg, hatch = masks(src)
    fig = figure(ink | reg, gl) | reg        # the hatched areas whole (the paper between the ruled lines is
    #                                          too narrow for the seal), and walls to the ground
    # specks on the paper round the group: ink farther than NEAR from every figure (a toe's tip stands just
    # outside the foot's outline: the left youth's rear foot)
    lab, n = ndi.label(ink)
    on = np.zeros(n + 1, bool)
    on[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    on[0] = False
    ink &= on[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), gl=gl.astype(np.uint8), ink=ink | hatch, fig=fig, reg=reg)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=hatch, trace_h=lw.WORK_H,
        title='The Persian king fleeing',
        desc='Line drawing after the 1883 plate of an Apulian amphora in Naples (Heydemann, Hallisches Winckelmannsprogramm 8); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
