"""Lysistrata: two women dancing hand in hand, from a round dance of women on an Attic red-figure
calyx-krater from Falerii, in Karl Reichhold's drawing, Furtwängler and Reichhold, Griechische
Vasenmalerei I (Munich, 1904), Taf. 17/18 ("Attischer Krater aus Falerii"), as scanned by Heidelberg
University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/furtwaengler1904bd1%3A017_18.jpg/full/full/0/default.jpg
(6184 x 2426; page https://digi.ub.uni-heidelberg.de/diglit/furtwaengler1904bd1/0018)

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the
crop, the enlargement, the grey, the blurs, the Maximum and Minimum filters and the thresholds.
numpy only combines the masks PhotoCraft made (labels, unions, hysteresis, skeletons, distances),
measures, and cuts along hand-placed lines (geometry, not image filtering). The SVG is written by
linework.trace_svg.

Plate -> drawing. The plate prints the vase's black ground nearly black (grey 10-40, the figures
170-200), so the ground gives the outline. The two women are two of the ring of dancers, joined
hand to hand; they are cut from their neighbours where they touch (ZONES):
  - the left woman's hand, held by the previous dancer: the neighbour's arm and hand go, and her
    hand is closed with a line where the neighbour's hand hid it (John, 2026-10-08: "for left
    woman's hand, we fill in the line");
  - the right woman's hand, holding the next dancer's: the neighbour is cut at her wrist (first pass);
  - the next dancer's raised foot over the right woman's toes: cut along the neighbour's toes;
  - the left woman's raised foot in front of the previous dancer's heel: cut along her heel.
The ornament band below goes: the figures stand on its reserved top strip, cut along its top edge
(FLOOR, a cubic fitted to it within 1.4 px).

Lines: the plate's pen lines by local contrast (Maximum then Minimum of the blurred plate, less
it), redrawn along their centres LINE_W plate px wide; black wider than a line (hair, the hems)
solid; the outline LINE_W wide. Traced as drawn (linework weight "drawn"), as Andromache.

    python3 docs/redesign/drawings/tools/lysistrata.py furtwaengler1904bd1_017_18.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "lysistrata.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
S = lw.STRAIGHT

X0, Y0, X1, Y1 = 2796, 458, 3626, 1410    # crop in plate px: the pair, with the floor strip under them
UP = 3                                    # work at 3x the plate's px
DARK = 90                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 3000                        # plate px: dark areas this large, reaching the crop's edge, are ground
# the floor: the top edge of the band's reserved strip, y = cubic in (x - 3200) (plate px, grey 100)
FLOOR = (-1.095e-07, 0.0001647899, 0.0592393498, 1362.6331982531)
# a point in each woman (plate px)
SEEDS = [(3000, 1000), (3330, 1000)]
# pockets of ground the figures close in (a point in each, plate px): between the two women, under
# their clasped hands, closed below where her heel meets the other's foot
POCKETS = [(3200, 1100)]
# The right woman's hair: its reserved outline (a light line between the black hair and the ground)
# prints faint over the crown, and the hair ran into the ground there. WALLS (plate px) part them,
# WALL_W plate px wide, along that line
WALLS = [[(3437, 493), (3450, 493), (3460, 494), (3468, 496), (3476, 499), (3485, 502)]]
WALL_W = 1.5
# Cuts from the neighbours: closed zones (plate px) cut away; a zone's edge follows the plate's dark
# lines between points, except across a STRAIGHT step
ZONES = {
    # the previous dancer's arm and hand, which hold the left woman's left hand: her hand is closed by
    # a straight line from where the neighbour's arm meets her wrist to her fingers' top
    'prev_hand': [(2842, 873), S, (2834, 907), S, (2796, 905), S, (2796, 840), S, (2838, 840), S],
    # the next dancer's arm, cut at her wrist, from the gap between the two arms to the clasp's right edge
    'next_arm': [(3591, 934), S, (3618, 957), S, (3626, 957), S, (3626, 700), S, (3600, 700), S, (3585, 915), S],
    # the next dancer's foot over the right woman's toes: along the neighbour's toes
    'next_foot': [(3507, 1328), (3501, 1350), (3500, 1362), (3505, 1378), (3512, 1388), (3516, 1396), S,
                  (3626, 1410), S, (3626, 1290), S, (3520, 1290), S],
    # the previous dancer's heel behind the left woman's raised foot: along her heel
    'prev_heel': [(2838, 1326), (2842, 1336), (2848, 1350), (2853, 1362), (2858, 1369), S, (2858, 1410), S,
                  (2796, 1410), S, (2796, 1290), S, (2828, 1290), S],
}
LINE_W = 1.3                              # plate px: every line (the pen lines are 1.5-3 px wide on the plate)
CONTRAST = (14, 26)                       # local contrast (grey levels): hysteresis low, high
# The crinkled chitons: fine wavy pleats 4-6 plate px apart, printed faint and broken; local contrast
# drew them as a tangle of short branching strokes. The plate is first smoothed along its own lines:
# PhotoCraft's Motion Blur, ORIENT_D plate px long, at every ORIENT_STEP degrees, each pixel taking the
# blur at its lines' direction (the structure tensor's, over 2 plate px; measured in numpy), blended
# with the unsmoothed plate where the direction is uncertain (coherence COH[0]-COH[1]). Its local
# contrast at CONTRAST_O gives the pleats as even runs. Faces, hands and feet (PLAIN, boxes, plate px)
# keep the plain plate at CONTRAST: smoothing along a line bends its tight curves
ORIENT_D, ORIENT_STEP, COH = 5, 15, (0.2, 0.5)
CONTRAST_O = (8, 16)
PLAIN = [(2925, 475, 3095, 610), (3395, 485, 3565, 625),                       # the heads
         (2800, 845, 2890, 945), (3150, 860, 3300, 1000), (3530, 900, 3626, 1000),   # the hands
         (2800, 1260, 2940, 1410), (3060, 1260, 3220, 1410), (3380, 1300, 3540, 1410)]   # the feet
SPUR = 3                                  # plate px: shorter centre-line spurs off a junction go
MIN_LEN = 3                               # plate px: shorter centre-line pieces are grain


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
    return [S if p == S else ((p[0] - X0) * UP, (p[1] - Y0) * UP) for p in pts]


def plate_box(shape, box):
    m = np.zeros(shape, bool)
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
    m[max(by0, 0):by1, max(bx0, 0):bx1] = True
    return m


def polyline(pts):
    """Hand-placed points (plate px) joined by straight lines, a point per UP px, (x, y) at UP."""
    P = np.array(up(pts), float)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (path[:, ::-1] - 0.5).astype(int)
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def oriented(t, gl):
    """The blurred plate smoothed along its own lines (ORIENT_*): PhotoCraft's Motion Blur at each
    angle; numpy picks, per pixel, the blur at the lines' direction."""
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(t / "gl.png", t / f"mb{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    mb = np.stack([grey(t / f"mb{a}.png") for a in angs])
    gy, gx = np.gradient(gl)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 2 * UP) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the lines' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    w = np.clip((coh - COH[0]) / (COH[1] - COH[0]), 0, 1)
    comp = w * np.take_along_axis(mb, i[None], 0)[0] + (1 - w) * gl
    Image.fromarray(np.clip(comp, 0, 255).round().astype(np.uint8)).save(t / "comp.png")
    r = (5 * UP) // 2
    pc(t / "comp.png", t / "compc.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
       ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
    return grey(t / "compc.png") - grey(t / "comp.png")


def centre_lines(mask, t, min_len, spur):
    """All of `mask` redrawn along its centre line, t px wide: the skeleton, less spurs (branches
    shorter than spur px between a junction and a free end) and pieces shorter than min_len px
    (as andromache.py)."""
    n8 = np.ones((3, 3), int)
    sk = morphology.skeletonize(mask)
    for _ in range(2):
        nb = ndi.convolve(sk.astype(int), n8, mode='constant') - 1
        near_j = ndi.binary_dilation(sk & (nb >= 3), structure=n8)
        lab, n = ndi.label(sk & ~near_j, structure=n8)
        size = np.bincount(lab.ravel(), minlength=n + 1)
        at_j, at_end = np.zeros(n + 1, bool), np.zeros(n + 1, bool)
        at_j[lab[ndi.binary_dilation(near_j, structure=n8) & ~near_j & sk]] = True
        at_end[lab[sk & (nb == 1) & ~near_j]] = True
        cut = at_j & at_end & (size < spur)
        cut[0] = False
        sk = morphology.skeletonize(sk & ~cut[lab])
    lab, _ = ndi.label(sk, structure=n8)
    sk &= (np.bincount(lab.ravel()) > min_len)[lab]
    return ndi.distance_transform_edt(~sk) <= t / 2


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "dark.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.6 * UP}))
        r = (5 * UP) // 2
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        dark0 = grey(t / "dark.png") < 128
        contrast_o = oriented(t, gl)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    outside = py > np.polyval(FLOOR, px - 3200)
    cost = 1 + 40 * np.clip((gl - 40) / 140, 0, 1)   # cheap along the plate's dark lines
    for pts in ZONES.values():
        outside |= lw.polygon_mask(g.shape, lw.livewire(cost, up(pts), closed=True))

    # ground: dark, thin lines opened away; the large areas reaching the crop's edge or the cuts
    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP)) & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]

    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    paint = dark0 & fig
    paint = ndi.binary_opening(paint, structure=morphology.disk(int(LINE_W * UP)))   # wider than a line
    lab, _ = ndi.label(paint)
    paint &= (np.bincount(lab.ravel()) > 15 * UP * UP)[lab]

    tw = LINE_W * UP
    plain = np.zeros(g.shape, bool)
    for box in PLAIN:
        plain |= plate_box(g.shape, box)
    firm = np.where(plain, apply_hysteresis_threshold(closed - gl, *CONTRAST),
                    apply_hysteresis_threshold(contrast_o, *CONTRAST_O)) & fig
    lines = centre_lines(firm & ~paint, tw, MIN_LEN * UP, SPUR * UP)
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(round(tw)))
    ink = (lines | paint | edge) & fig
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, outside=outside)

    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight="drawn",
        title='Two women dancing hand in hand',
        desc='Line drawing after the 1904 plate of a round dance of women on a red-figure krater '
             '(Furtwängler and Reichhold, Griechische Vasenmalerei I, Taf. 17/18); cut out and retraced.')
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
