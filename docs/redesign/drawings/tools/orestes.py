"""Orestes: Apollo purifies Orestes at Delphi, holding a piglet over him; Orestes sits on the altar before the
omphalos, his sword in his hand; Artemis at the right with her spears; at the left Clytemnestra's ghost tries
to wake the sleeping Furies, and a third Fury rises below. From Karl Reichhold's drawing of the Eumenides
Painter's Apulian bell-krater in the Louvre (Cp 710) in Furtwängler and Reichhold, Griechische Vasenmalerei
II (Munich, 1909), Taf. 120.3 ("Unteritalischer Krater im Louvre"; text pp. 327-330), as scanned by the
Visual Resources Center, Williams College (JSTOR community.17147024, FRSerieIIpt111_120_120.jpg, 2615 x 3440;
the scan CC BY-NC-SA 4.0, the plate public domain in the US).
John's pick (2026-10-12): this plate rather than the Yale krater (1994.11.1), which has no old drawing.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli`, as in bacchae.py, whose
rules this tool follows (the same book and family: red figures on the black ground).

Plate -> drawing:
  - Out: above the top band's lower edge (TOP), below the meander's top edge (FLOOR), outside the panel's
    sides (LEFT, RIGHT). The side ornaments reach no seed and drop out.
  - Ground: the plate's dark, thin lines opened away; the large areas reaching the crop's edge, and the
    pockets the figures close in (POCKETS).
  - The figures: the clay joined to SEEDS (each moved to the nearest clay within 15 plate px).
  - Lines, paint, hair, eyes, and the wash: as bacchae.py.

    python3 docs/redesign/drawings/tools/orestes.py fr120_full.jpg [qa.png]
    python3 docs/redesign/drawings/tools/orestes.py fr120_full.jpg qa.png --test x0,y0,x1,y1 out.svg
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
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "orestes.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 466, 1886, 2141, 2948    # crop in plate px: the panel between the bands
UP = 3                                     # work at 3x the plate's px
# the top band's lower edge (where the plate's dark begins below its last light line, grey 85 lightly
# smoothed; measured every 100 px, x 500-2100: 1888 to 1899, a straight line within 1 px). Above it, out
TOP = ((500, 1888.0), (2100, 1899.0))
FLOOR = 2946.0                             # the meander's top edge (2945-2947 across the panel). Below, out
LEFT, RIGHT = 467, 2138                    # the panel's sides
SEEDS = [(1270, 2363), (1587, 2113), (1887, 2530), (603, 2197), (803, 2280), (1020, 2247), (770, 2813),
         (1353, 2772), (1087, 1950), (1237, 2113), (1403, 2380)]
DARK = 85                                  # ground and paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 4000                         # plate px: dark areas this large reaching the crop's edge are ground
# ground the figures close in (a point in each, plate px; the dark area at or nearest it): left of the sleeping Fury's
# head, under the ghost's arm; under the seated Fury's chin; between the seated Fury's arm and her side; between
# Orestes' arm and his thigh; between his shin and the altar; between his cloak and Apollo's himation; between
# Apollo's feet; between the risen Fury's arm and her head
POCKETS = [(780, 2193), (922, 2124), (1039, 2304), (1188, 2386), (1088, 2556), (1498, 2536), (1616, 2674),
           (863, 2744)]
PAINT_NEAR, PAINT_CORE = 4, 45
HEADS = []
HAIR_T, HAIR_HOLE = 120, 4
EYES = []
EYE_W, PUPIL_T, PUPIL_MAX = 1.0, 55, 12
LINE_R = 2.5
LINE_LO, LINE_HI = 22, 34
WEIGHT = 0.0011                            # the line weight, of the longer side (F-R: John on Andromache)
WASH_BLUR, WASH_R, WASH_D, WASH_W = 1.0, 16, 22, 3
WASH_MIN = 30
WASH_A, WASH_D1, WASH_STEP, WASH_SIGMA = (0.15, 0.35), 60, 0.05, 2
MARKS_FILES = []


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def top_y(x):
    """The top band's lower edge at plate x."""
    (xa, ya), (xb, yb) = TOP
    return ya + (yb - ya) * (x - xa) / (xb - xa)


def add_wash(svg, wash, depth, box):
    """The wash, as bacchae.add_wash."""
    x0, y0, x1, y1 = box
    b, dp, s = wash[y0:y1, x0:x1], depth[y0:y1, x0:x1], WASH_SIGMA * UP
    dpt = ndi.gaussian_filter(np.where(b, dp, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (a0, a1) = WASH_A
    alpha = a0 + (a1 - a0) * np.clip((dpt - WASH_D) / (WASH_D1 - WASH_D), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, WASH_STEP):
        m = b & (alpha >= a - WASH_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def nearest(lab, x, y, r=15):
    """The label at or nearest plate (x, y), within r plate px (0 if none)."""
    r = r * UP
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = lab[max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
    oy, ox = max(cy - r, 0) - (cy - r), max(cx - r, 0) - (cx - r)
    dist = np.hypot(*np.mgrid[-r + oy:-r + oy + win.shape[0], -r + ox:-r + ox + win.shape[1]])
    iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
    return win[iy, ix]


def main(src, qa=None, test=None, out=None):
    global X0, Y0, X1, Y1
    out = Path(out) if out else OUT
    if test:
        X0, Y0, X1, Y1 = (int(v) for v in test.split(','))
    inbox = lambda x, y: X0 <= x < X1 and Y0 <= y < Y1
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = round(LINE_R * UP)
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": WASH_BLUR * UP}))
        r = WASH_R * UP
        pc(t / "gw.png", t / "wclosed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        g, gl, closed, gw = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "gw.png")
        gs = grey(t / "gs.png")
        wclosed = grey(t / "wclosed.png")
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + X0 - 0.5, (yy + 0.5) / UP + Y0 - 0.5

    outside = (py < top_y(px)) | (py > FLOOR) | (px < LEFT) | (px > RIGHT)

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP)) & ~outside
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        if inbox(x, y):
            i = nearest(lab, x, y)
            assert i, f'no dark area near {(x, y)}'
            is_ground[i] = True
    ground = is_ground[lab]

    lab, _ = ndi.label(~ground & ~outside)
    keep = {nearest(lab, x, y) for x, y in SEEDS if inbox(x, y)}
    assert 0 not in keep, keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    blue = np.zeros_like(fig)
    for mf in MARKS_FILES:
        m = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
        assert m.shape[:2] == fig.shape, (m.shape, fig.shape)
        r, gg, bb, al = (m[..., i] for i in range(4))
        blue |= (al > 40) & (bb > r + 40) & (bb > gg + 20)

    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    paint = fine & ndi.binary_dilation(solid, iterations=PAINT_NEAR * UP) & fig
    heads = np.zeros_like(fig)
    for hx0, hy0, hx1, hy1 in HEADS:
        heads |= (px >= hx0) & (px < hx1) & (py >= hy0) & (py < hy1)
    lab, n = ndi.label((gs < HAIR_T) & fig & heads)
    hair = np.bincount(lab[solid & heads].ravel(), minlength=n + 1) > 0
    hair[0] = False
    hair = hair[lab]
    hair |= ndi.binary_fill_holes(hair) & ~hair & ~morphology.remove_small_objects(
        ndi.binary_fill_holes(hair) & ~hair, max_size=HAIR_HOLE * UP * UP)
    paint = (paint & ~heads) | hair

    ys, xs = np.nonzero(fig)
    tw = WEIGHT * max(np.ptp(ys), np.ptp(xs))   # the line width, work px
    if test:   # a test box: the weight the whole panel gives
        tw = WEIGHT * (X1_FULL - X0_FULL) * UP
    firm = apply_hysteresis_threshold(closed - gl, LINE_LO, LINE_HI)
    black = firm & fig & ~ndi.binary_dilation(paint, iterations=UP)
    lines = centre_lines(black, tw, 3 * UP, 2 * tw) | paint
    eyes = np.zeros_like(fig)
    for ex0, ey0, ex1, ey1 in EYES:
        eyes |= (px >= ex0) & (px < ex1) & (py >= ey0) & (py < ey1)
    pupil = (gs < PUPIL_T) & eyes & fig & ~paint
    lab, _ = ndi.label(pupil)
    pupil &= (np.bincount(lab.ravel()) < PUPIL_MAX * UP * UP)[lab]
    eye_lines = centre_lines(black & eyes & ~ndi.binary_dilation(pupil, iterations=UP // 2), EYE_W * UP, UP, UP)
    lines = np.where(eyes & ~paint, eye_lines | pupil, lines)
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & (dt <= tw) & ~outside
    ink = (lines & fig) | edge
    if blue.any():
        ink |= ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= tw / 2
        ink |= ndi.binary_opening(blue, structure=morphology.disk(max(1, round(tw))))
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]

    w0 = fig & (wclosed - gw > WASH_D) & ~paint
    wash = ndi.binary_opening(w0 & ~ndi.binary_dilation(lines, iterations=UP // 2),
                              structure=morphology.disk(round(WASH_W * UP / 2)))
    wash = ndi.binary_closing(wash, structure=morphology.disk(2 * UP)) & w0
    wash = morphology.remove_small_objects(wash, max_size=WASH_MIN * UP * UP)

    info = lw.trace_svg(
        ink, out, body=fig, open_holes=~fig, weight="drawn",
        title='Apollo purifies Orestes at Delphi',
        desc='Line drawing after Karl Reichhold\'s 1909 drawing of the Eumenides Painter\'s bell-krater, Paris, '
             'Louvre Cp 710 (Furtwängler and Reichhold, Griechische Vasenmalerei II, Taf. 120.3); cut out and '
             'retraced.')
    if wash.any():
        add_wash(out, wash, wclosed - gw, info['box'])
    print(out, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, out, info['box'], Path(qa))
        lw.qa_dark(out, info['box'], Path(qa).with_suffix('.dark.png'))


X0_FULL, X1_FULL = X0, X1

if __name__ == '__main__':
    a = sys.argv[1:]
    test = out = None
    if '--test' in a:
        i = a.index('--test')
        test, out = a[i + 1], a[i + 2]
        del a[i:i + 3]
    main(*a[:2], test=test, out=out)
