"""Hippolytus: an Amazon, with bow and axe, fighting a hoplite, from the lower
panel of Gerhard, Auserlesene griechische Vasenbilder III (1847), Taf. CLXV,
titled there "Theseus und Antiope" (Hippolytus' mother is the Amazon Theseus
took), as scanned by Heidelberg University Library (public domain):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_165.jpg/full/full/0/default.jpg
(2078 x 2869; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0212)

Plate -> drawing, as for the maenad test from Furtwängler-Reichhold Taf. 44
(2026-10-04): the plate prints the black ground black, so the figures'
outline comes free.
  - Ground: the dark of the plate, its thin lines opened away; the large
    areas, and the pockets of ground the figures close in (POCKETS). Each
    figure is ringed by a dark band a little lighter than the ground
    (25-55 grey against 14); the threshold (DARK) lies above it, so the
    outline sits on the clay's edge, not the band's.
  - The scene is the clay area the ground leaves, from SEEDS: the hoplite,
    the Amazon, his spear, her bow, its string and her axe. The panel's
    borders are cut along their lines (LEFT, BOTTOM): the soles stand on the
    lower border, and his spear's butt ends 2 px inside the left one.
  - At the right edge a sliver of the next hoplite comes in: his spear shaft
    runs behind her to the corner of her skirt and the bow case at her back,
    so cutting the shaft there (OTHER_SPEAR) parts his shield and toes from
    her; her outline there is the plate's own line. The inscription is not
    joined to her and drops out with the ground.
  - Lines: the plate's dark lines inside the figures (local contrast), the
    outline, and the plate's solid black (hair, the inside of the shield,
    the dark points of her patterns).
  - Dark theme: the figures' area is the body; the ground pockets stay open,
    as on the vase.

    python3 docs/redesign/drawings/tools/hippolytus.py gerhard1847bd3_190a.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "hippolytus.svg"

X0, Y0, X1, Y1 = 160, 1243, 1190, 2495   # crop in plate px (the lower panel's left two figures)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large are ground
SEEDS = [(370, 1600), (900, 2050)]        # his chest, her dress (plate px)
# pockets of ground the figures close in, smaller than AUTO_GROUND (a point in each, plate px):
# between his right arm and his side; below his spear, between her bow, her hand and her arm,
# and the sliver between the bowstring and her arm; between the bow's lower limb and her body.
# Smaller dark areas inside the figures are paint: the hair, the inside of his shield, the black
# of her patterns.
POCKETS = [(355, 1690), (840, 1735), (893, 1695), (835, 1795)]
# the bowstring, plate px: a thin clay line on the ground from the upper tip (its centre,
# measured every 30 px; it bows by up to 4 px), then a faint dark line across her dress to the
# lower tip, bending where it meets her arm, with a 30 px gap in the printing (1806-1838) joined
STRING = [(826.5, 1452), (829.6, 1480), (836.5, 1510), (842.8, 1540), (849.9, 1570), (857.6, 1600),
          (865.9, 1630), (873.9, 1660), (880.9, 1690), (886.9, 1710), (888, 1720), (897, 1750),
          (905, 1785), (915, 1806), (925, 1838), (941, 1880), (949, 1900), (957, 1920), (966, 1940),
          (974, 1960)]
STRING_W = 2.2                            # plate px, its width on the ground
LOOP = (745, 2385, 812, 2426)             # box round the strap looped at her ankle (x0, y0, x1, y1)
# the panel's left border (centre of its line; it slants) and lower border, plate px
LEFT = [(184, 1243), (183, 1460), (180, 1660), (176, 1860), (174, 1960), (172, 2060), (169, 2160),
        (168, 2260), (165, 2360), (163, 2460), (162, 2500)]
BOTTOM = [(160, 2480), (260, 2483), (380, 2486), (480, 2488), (560, 2489), (680, 2492), (800, 2493),
          (950, 2493), (1050, 2494), (1190, 2497)]
# the next hoplite's spear shaft, from where it comes out from behind her to the crop's edge
OTHER_SPEAR = [(1040, 1882), (1195, 1882), (1195, 1902), (1046, 1902), (1039, 1893)]


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def main(src, qa=None):
    plate = Image.open(src).convert('L').crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside the panel: left of the left border, on and below the lower border
    left, bottom = up(LEFT), up(BOTTOM)
    outside = xx <= np.interp(yy, left[:, 1], left[:, 0]) + UP
    outside |= yy >= np.interp(xx, bottom[:, 0], bottom[:, 1])
    other = lw.polygon_mask(g.shape, up(OTHER_SPEAR))

    # ground: dark, thin lines opened away; the large areas and the listed pockets
    dark = ndi.binary_opening(gs < DARK, structure=morphology.disk(2 * UP)) & ~outside
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    # the scene: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground & ~outside & ~other)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground   # paint stays hers; pockets of ground do not
    # smooth the edge, but keep the thin clay lines on the ground (the strap looped at her
    # ankle): light ridges narrower than 5 plate px
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)
    string = np.zeros_like(fig)
    pts = up(STRING)
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, int(np.hypot(xb - xa, yb - ya)) + 1):
            string[int(round(ya + t * (yb - ya))), int(round(xa + t * (xb - xa)))] = True
    string = ndi.distance_transform_edt(~string) <= STRING_W * UP / 2

    # lines: the plate's dark lines inside the figures, the outline, the bowstring, and the solid
    # paint. The thin brown lines (his knee and shin, folds of his chiton) fade in places: a
    # looser threshold finds the faint stretches. A stretch is added where it joins two firm
    # lines (a gap in one line, or a faint line between two), or is long enough to be a line of
    # its own; one that touches a single firm line is a spur of grain beside it.
    # Every line is then at least 2 plate px wide, or the thin ones break up when the line
    # weight is evened out (it moves every line by the same amount)
    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = loose & ~ndi.binary_dilation(firm, iterations=UP)
    flab, n = ndi.label(faint)
    reach = ndi.grey_dilation(flab, size=(2 * UP + 3, 2 * UP + 3))   # each stretch, a little grown
    firm_lab = ndi.label(firm)[0]
    pairs = np.unique(np.stack([reach[firm], firm_lab[firm]]), axis=1)
    joins = np.bincount(pairs[0][pairs[0] > 0], minlength=n + 1)    # firm lines each one meets
    keep = (joins >= 2) | (np.bincount(flab.ravel(), minlength=n + 1) > 12 * UP * UP)
    keep[0] = False
    faint = keep[flab]
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(2.5 * UP))
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]
    ink |= string

    # the pockets stay open in the dark theme; the string and the strap, thin clay lines that
    # cross them, keep their clay rim there
    held = ndi.binary_fill_holes(fig | string) & ground
    strap = np.zeros_like(fig)
    lx0, ly0, lx1, ly1 = [(v - o) * UP for v, o in zip(LOOP, (X0, Y0, X0, Y0))]
    strap[ly0:ly1, lx0:lx1] = (fig & ridge)[ly0:ly1, lx0:lx1]
    rims = ndi.binary_dilation(string | strap, iterations=2 * UP)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, rim_lines=rims,
        title='An Amazon with bow and axe fighting a Greek hoplite',
        desc='Line drawing after the lower panel of Gerhard, Auserlesene griechische Vasenbilder III '
             '(1847), Taf. CLXV ("Theseus und Antiope").')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
