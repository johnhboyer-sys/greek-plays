"""Bacchae: four maenads dancing, the first playing the double pipe, the second (Thaleia) with a thyrsos and a
torch held flame down, the third (Choreia) beating a drum, the fourth wrapped in her mantle with a staff,
from Karl Reichhold's drawing of the reverse of the Naples Lenaia stamnos in Furtwängler and Reichhold,
Griechische Vasenmalerei I (Munich, 1904), Taf. 37 ("Attischer Krater mit Dionysosfeier, Neapel",
"Rückseite"; text pp. 193-195), as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/furtwaengler1904bd1/3/037.jpg
(2385 x 3288; page https://digi.ub.uni-heidelberg.de/diglit/furtwaengler1904bd1/0036)
The text calls the vase a krater; it is an Attic red-figure stamnos attributed to the Dinos Painter, from
Nocera de' Pagani, Naples, Museo Archeologico Nazionale 81674 (Heydemann 2419, as the text cites it;
Beazley Archive 215254, ARV2 1151.2). The text names the maenads on this side Choreia and Thaleia, and says
those who make no music carry thyrsoi or burning torches.
John's pick (Plate Picks 25-8Fb, 2026-10-09); the crop (2026-10-10): all four maenads; the border bands, the
side ornaments, and the painted names left out; the fourth maenad's staff stops where it meets the palmette.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop, the
enlargement, the grey, the blurs, Minimum and Maximum, and the thresholds. numpy only combines the masks
PhotoCraft made (labels, unions, distances, fills, centre lines) and measures; the cuts are geometry (the
band's edge measured, the staff's line). The SVG is written by linework.trace_svg.

Plate -> drawing, Furtwängler-Reichhold, red figures on the black ground:
  - Ground: the plate's dark, thin lines opened away; the large areas reaching the crop's edge, and the
    pockets the figures close in (POCKETS). Smaller dark areas inside the figures are paint (the hair).
  - The figures: the clay left inside the cuts, joined to SEEDS. Out: below the meander band's top edge
    (FLOOR), on which the feet stand; right of RIGHT, but for the staff (STAFF, a strip along its line, cut
    square at its end).
  - Lines: the plate's black lines (local contrast), redrawn along their centres at WEIGHT (the F-R weight,
    0.11%: John on Andromache); the outline on the ground just outside the clay, as wide. The paint (the
    belt's cords) at its own width; the hair solid, with the wreath's ivy leaves and berries open (HEADS);
    the eyes finer, the pupils dots (EYES); the white of the torch's flame open, its edge a line (FLAME).
  - The grey brushstrokes of thinned paint (the text: shadows in the folds, and along the upper lids): a
    `tone` wash in the line colour, its opacity following the plate (John, 2026-10-10: "Wash").
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/bacchae.py 037.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "bacchae.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 295, 1580, 2100, 2705    # crop in plate px: the four, the pipes' ends to the staff's end
UP = 3                                     # work at 3x the plate's px
# The meander band's top edge, on which the feet stand: a circle fitted to it where the ground lies over it
# (0.4 px rms on its best stretches), corrected by the edge as measured (the median over 17 plate px at
# each x where the ground lies over it: where the plate's dark first turns to the band's clay, at grey 85);
# between the measured points (under the feet) the correction is interpolated. Below it, out
FLOOR_C = (1136.94, 4812.15, 2236.32)      # centre x, y, radius
FLOOR = [(590, 2642.5), (620, 2637.0), (650, 2630.5), (680, 2626.0), (710, 2621.0), (740, 2615.5),
         (770, 2610.5), (950, 2583.5), (980, 2581.0), (1010, 2579.0), (1040, 2577.5), (1070, 2576.5),
         (1100, 2576.0), (1130, 2576.0), (1160, 2576.0), (1190, 2577.5), (1340, 2588.0), (1370, 2591.5),
         (1400, 2595.5), (1430, 2599.5), (1460, 2603.5), (1580, 2622.5), (1640, 2634.5), (1670, 2640.5),
         (1700, 2647.5), (1730, 2655.5), (1760, 2664.5), (1790, 2673.0), (1820, 2682.0), (1850, 2693.5)]
# right of this, out (the palmette, the band of tongues and its disk), but for the staff: the ground
# between the fourth maenad's back (1940 at most) and the ornament (1955 and over)
RIGHT = 1948
# the fourth maenad's staff beyond RIGHT, to where it meets the palmette (John, 2026-10-10: "Stop at the
# palmette"): a strip along its centre line (fitted to its edges at grey 90, x 1945-2075), as wide as
# the staff and STAFF_PAD px more each side, cut square to the line at its end. A tendril of the ornament
# leaves its lower edge at x 1985: the strip's edge cuts it off
STAFF = ((1940, 1907.4), (2088, 1792.0))   # centre line: start, end (plate px)
STAFF_W = (11.0, 8.5)                      # its width square to the line, at the start and the end
STAFF_PAD = 1.5
SEEDS = [(560, 2300), (1000, 2300), (1350, 2300), (1700, 2300)]
DARK = 85                                  # ground and paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 4000                         # plate px: dark areas this large reaching the crop's edge are ground
# ground the figures close in (a point in each, plate px; the dark area at or nearest it): Choreia, under her
# chin and between her arms and the drum; under the piper's chin, between the pipes and her breast; Thaleia,
# between her arm and her side, and her hand and her dress; between the piper's dress, Thaleia's thyrsos, her
# arm, and her body; between Choreia's skirt and the staff; between Thaleia's foot and the piper's hem
POCKETS = [(1442, 1771), (1510, 1852), (431, 1928), (1037, 1984), (1051, 2111), (783, 2190), (1572, 2290),
           (860, 2533)]
FIG_MIN = 200
PAINT_NEAR, PAINT_CORE = 4, 45
# the hair (boxes round the four heads, plate px): at the paint's threshold it came out mottled, its brown
# curls and the black between the wreath's leaves left open. In each box, the plate darker than HAIR_T
# (lightly smoothed; the hair 20-90, the leaves, berries, and the clay line round the hair 140 and over)
# joined to the paint's dark cores is hair, its holes under HAIR_HOLE plate px filled
HEADS = [(380, 1690, 565, 1850), (870, 1640, 1045, 1800), (1245, 1615, 1400, 1790), (1770, 1695, 1960, 1850)]
HAIR_T, HAIR_HOLE = 120, 4
# the eyes (boxes, plate px: the piper, Thaleia, Choreia, the fourth): each about 12 plate px across, at
# the line weight their lids ran into the pupil (eyes never heavy: John, 2026-10-07). Inside each box the
# lines are drawn finer, EYE_W plate px, and the pupil, darker than PUPIL_T, is a dot at its own size
EYES = [(443, 1781, 470, 1801), (920, 1673, 947, 1699), (1347, 1671, 1372, 1697), (1830, 1738, 1850, 1758)]
EYE_W, PUPIL_T, PUPIL_MAX = 1.0, 55, 12
LINE_R = 2.5                               # plate px: the closing for the lines' local contrast (wider dark,
                                           # the thinned paint's strokes, gives none)
LINE_LO, LINE_HI = 22, 34                  # local contrast (closing less the plate): hysteresis
WEIGHT = 0.0011                            # the line weight, of the longer side (F-R: John on Andromache)
# the wash: the grey strokes, darker by WASH_D than the clay round them (the plate blurred WASH_BLUR plate
# px, against its closing over WASH_R plate px, wider than the broadest band, 19 px: the scan's light falls
# off to the left), wider than WASH_W plate px
WASH_BLUR, WASH_R, WASH_D, WASH_W = 1.0, 16, 22, 3
WASH_MIN = 30                              # plate px: smaller pieces are specks of the print
# its opacity: WASH_A[0] where the stroke is WASH_D darker than the clay round it, WASH_A[1] where it is
# WASH_D1 darker, in steps of WASH_STEP, smoothed over WASH_SIGMA plate px (as the blood on Andromache)
WASH_A, WASH_D1, WASH_STEP, WASH_SIGMA = (0.15, 0.35), 60, 0.05, 2
# the torch's flame, in added white over Thaleia's dress (the box, plate px): lighter than WHITE_T (the
# dress round it 175-200, the white 206-218), its edge drawn as a line
FLAME = (835, 2405, 1045, 2480)
WHITE_T = 203
FLAME_CLEAR = 4.0

def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def floor_y(x):
    """The band's top edge at plate x."""
    cx, cy, r = FLOOR_C
    circ = lambda v: cy - np.sqrt(r * r - (v - cx) ** 2)
    fx = np.array([p[0] for p in FLOOR], float)
    fy = np.array([p[1] for p in FLOOR], float)
    return circ(x) + np.interp(x, fx, fy - circ(fx))


def staff_strip(shape, pad=STAFF_PAD):
    """The staff beyond RIGHT, as a mask at UP, pad plate px more round it."""
    (xa, ya), (xb, yb) = STAFF
    d = np.array([xb - xa, yb - ya], float)
    L = np.hypot(*d)
    d /= L
    n = np.array([-d[1], d[0]])
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    px, py = (xx + 0.5) / UP + X0 - xa, (yy + 0.5) / UP + Y0 - ya
    s, o = px * d[0] + py * d[1], px * n[0] + py * n[1]
    w = STAFF_W[0] + (STAFF_W[1] - STAFF_W[0]) * np.clip(s / L, 0, 1)
    return (s >= -2 * pad) & (s <= L + pad - STAFF_PAD) & (np.abs(o) <= w / 2 + pad)


def add_wash(svg, wash, depth, box):
    """Add the wash to the drawing written by lw.trace_svg (box: its crop box): paths of class "tone" in the
    line colour, between the body and the lines, traced at the lines' own size; the opacity follows how much
    darker the plate is there than the clay round it (WASH_*), in steps, each step's area drawn over the one
    below at the opacity that brings the total there to the step's (so no seam shows), as add_tone in
    andromache.py."""
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


def main(src, qa=None, dump=None):
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

    # out: below the band's top edge; right of RIGHT, but for the staff
    below = py > floor_y(px)
    outside = below | ((px > RIGHT) & ~staff_strip(g.shape))

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP)) & ~outside
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:   # the dark area at or nearest the point (within 15 plate px)
        r = 15 * UP
        cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
        win = lab[cy - r:cy + r + 1, cx - r:cx + r + 1]
        dist = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1])
        iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
        assert win[iy, ix], f'no dark area near {(x, y)}'
        is_ground[win[iy, ix]] = True
    ground = is_ground[lab]

    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[round((y - Y0) * UP), round((x - X0) * UP)] for x, y in SEEDS}
    assert 0 not in keep, keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    # the paint (the hair), at its edge as the plate prints it (less blurred), with the thin black between
    # the wreath's leaves and the curls within PAINT_NEAR plate px of it
    # (only dark areas whose core is darker than PAINT_CORE: the darkest parts of the thinned paint's
    # strokes, 50-80 at their cores, are wash; the hair's cores read 10-25, the cords' 29-36)
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
    firm = apply_hysteresis_threshold(closed - gl, LINE_LO, LINE_HI)
    # (local contrast only: the plain dark threshold took the thinned paint's broad strokes for lines)
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
    # the flame's white: no lines inside it; its edge a line
    fx0, fy0, fx1, fy1 = FLAME
    inbox = (px >= fx0) & (px < fx1) & (py >= fy0) & (py < fy1)
    white = ndi.binary_opening((gw > WHITE_T) & inbox & fig, structure=morphology.disk(UP // 2 + 1))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > 8 * UP * UP)[lab]
    rim_w = (ndi.distance_transform_edt(white) <= tw / 2) & white | \
        (ndi.distance_transform_edt(~white) <= tw / 2) & ~white & ndi.binary_dilation(white, iterations=round(tw))
    # (the plate's dark rims round the white strokes and the torch's lines that run into them, the finder's
    # lines within FLAME_CLEAR plate px of the white, go: the white's edge is the line)
    lines = (lines & ~ndi.binary_dilation(white, iterations=round(FLAME_CLEAR * UP))) | rim_w
    dt = ndi.distance_transform_edt(~fig)
    # (beyond RIGHT, only round the staff: the strip widened by the outline)
    edge = ~fig & (dt <= tw) & ~((px > RIGHT) & ~staff_strip(g.shape, STAFF_PAD + tw / UP) & ~below)
    ink = (lines & fig) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]

    # (the lines as drawn are taken out before the opening, which then leaves only broad strokes: with the
    # lines in, a grey halo ran along every line, and with all the finder's dark out, the broad bands broke
    # into specks; then closed across the lines inside a stroke, and drawn under them)
    w0 = fig & (wclosed - gw > WASH_D) & ~paint
    wash = ndi.binary_opening(w0 & ~ndi.binary_dilation(lines, iterations=UP // 2),
                              structure=morphology.disk(round(WASH_W * UP / 2)))
    wash = ndi.binary_closing(wash, structure=morphology.disk(2 * UP)) & w0 & \
        ~ndi.binary_dilation(white, iterations=round(FLAME_CLEAR * UP))
    wash = morphology.remove_small_objects(wash, max_size=WASH_MIN * UP * UP)
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint,
                            firm=firm & fig, edge=edge, wash=wash, gw=gw.astype(np.uint8))

    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight="drawn",
        title='Four maenads dancing, with pipes, thyrsos, and drum',
        desc='Line drawing after Karl Reichhold\'s 1904 drawing of the Lenaia stamnos by the Dinos Painter, '
             'Naples, Museo Archeologico Nazionale 81674 (Furtwängler and Reichhold, Griechische Vasenmalerei '
             'I, Taf. 37); cut out and retraced.')
    if wash.any():
        add_wash(OUT, wash, wclosed - gw, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
