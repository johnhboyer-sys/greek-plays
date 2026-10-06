"""Hippolytus: an Amazon, with bow and axe, fighting a hoplite, from the lower
panel (fig. 4) of Gerhard, Auserlesene griechische Vasenbilder III (1847),
Taf. CLXV, titled there "Theseus und Antiope" (Hippolytus' mother is the
Amazon Theseus took), as scanned by Heidelberg University Library (Public
Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_165.jpg/full/full/0/default.jpg
(2078 x 2869; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0212)
The vase, as Gerhard gives it (text pp. 47-48): a red-figure amphora with
twisted handles (its shape is fig. 3), formerly in the Pizzati collection,
Florence; the second hoplite, at the right, is his Peirithoos.

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
STRING_W = 2.2                            # plate px, its width on the ground (and the strap's)
# the strap looped at her ankle, a thin clay line on the ground, through its centre (every 5 px,
# from where it leaves her foot round to its knot); its light ridge breaks up in two places
STRAP = [(799.8, 2418.7), (794.9, 2418.9), (789.9, 2418.6), (784.9, 2418.2), (779.9, 2417.9),
         (774.9, 2417.8), (769.9, 2417.2), (765.1, 2416.0), (760.6, 2414.2), (756.6, 2410.9),
         (755.1, 2406.4), (757.1, 2401.9), (759.9, 2397.9), (764.3, 2396.1), (769.1, 2395.4),
         (774.1, 2394.5), (779.1, 2394.6), (783.9, 2395.2), (788.9, 2396.5), (793.4, 2398.2),
         (797.9, 2400.2), (802.4, 2402.6), (806.6, 2405.4), (811.8, 2409.0)]
# the faces, boxes in plate px: their lines are fine and close together (the stubble on his cheek
# is a row of short strokes, her eye an open outline), and the local-contrast finder merges them,
# so here the lines are the plate's dark paint itself, at its own width
FACES = [(560, 1486, 672, 1585), (945, 1505, 1015, 1650)]
FACE_DARK = 105
# faint lines the finder breaks up and a tint patch beside them would join wrongly, traced along
# the plate's own line between hand-placed ends (plate px): the thin line down his neck
TRACED = [[(536, 1524), (556.5, 1562)]]
TRACED_W = 1.5                            # plate px
# the panel's left border (centre of its line; it slants) and lower border, plate px
LEFT = [(184, 1243), (183, 1460), (180, 1660), (176, 1860), (174, 1960), (172, 2060), (169, 2160),
        (168, 2260), (165, 2360), (163, 2460), (162, 2500)]
BOTTOM = [(160, 2480), (260, 2483), (380, 2486), (480, 2488), (560, 2489), (680, 2492), (800, 2493),
          (950, 2493), (1050, 2494), (1190, 2497)]
# the next hoplite's spear shaft, from where it comes out from behind her to the crop's edge
OTHER_SPEAR = [(1040, 1882), (1195, 1882), (1195, 1902), (1046, 1902), (1039, 1893)]


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def polyline(shape, pts, width):
    """A line `width` plate px wide through pts (plate px), at UP."""
    m = np.zeros(shape, bool)
    P = up(pts)
    for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
        for t in np.linspace(0, 1, int(np.hypot(xb - xa, yb - ya)) + 1):
            m[int(round(ya + t * (yb - ya))), int(round(xa + t * (xb - xa)))] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def traced(g, pts, width):
    """The plate's own dark line between hand-placed points (plate px), followed by a least-cost
    path along its darkest ridge, `width` plate px wide, at UP."""
    P = up(pts)
    pad = 10 * UP
    x0, y0 = int(P[:, 0].min()) - pad, int(P[:, 1].min()) - pad
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.7 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    path = lw.livewire(cost, [(x - x0, y - y0) for x, y in P])
    m = np.zeros(g.shape, bool)
    m[(path[:, 1] - 0.5).astype(int) + y0, (path[:, 0] - 0.5).astype(int) + x0] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def faint_stretches(firm, loose):
    """The faint stretches of the plate's thin lines, from the looser threshold, where they are
    lines. Away from the firm lines, a stretch long enough to stand alone must be line-shaped
    (3 times as long as wide; a patch of the print's tint is rounder). A short one, or a piece of
    the looser lines' centre line between firm lines (which finds gaps under 2 px, lying wholly
    in the firm lines' fringe), must bridge two firm lines and run along at least one of them: a
    gap in a line, or a line meeting another. One that crosses between two lines side by side
    is a bridge of grain or tint."""
    def axis(p):  # unit vector (y, x) along the longer axis of points p, and how much longer it is
        if len(p) < 3:
            return np.zeros(2), 0.0
        w, v = np.linalg.eigh(np.cov(p.T.astype(float)))
        return v[:, 1], float(np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)))

    firm_lab = ndi.label(firm)[0]
    box = np.ones((2 * UP + 3, 2 * UP + 3), bool)

    def bridges(lab, small):
        keep = np.zeros(lab.max() + 1, bool)
        for k, sl in enumerate(ndi.find_objects(lab), 1):
            pad = 8 * UP
            ys = slice(max(sl[0].start - pad, 0), sl[0].stop + pad)
            xs = slice(max(sl[1].start - pad, 0), sl[1].stop + pad)
            mine = lab[ys, xs] == k
            if mine.sum() > small:
                continue
            fl = firm_lab[ys, xs]
            reach = ndi.binary_dilation(mine, structure=box)
            touched = [f for f in np.unique(fl[reach]) if f]
            near = ndi.distance_transform_edt(~mine) <= 6 * UP
            meets = [np.argwhere(reach & (fl == f)).mean(0) for f in touched]    # where it meets each
            runs = [axis(np.argwhere(near & (fl == f)))[0] for f in touched]      # each one's way there
            for i in range(len(touched)):
                for j in range(i + 1, len(touched)):
                    d = meets[j] - meets[i]
                    if np.hypot(*d) >= 1:
                        d /= np.hypot(*d)
                        keep[k] |= max(abs(d @ runs[i]), abs(d @ runs[j])) > np.cos(np.radians(30))
        return keep[lab]

    flab, n = ndi.label(loose & ~ndi.binary_dilation(firm, iterations=UP))
    alone = np.zeros(n + 1, bool)
    for k, sl in enumerate(ndi.find_objects(flab), 1):
        mine = flab[sl] == k
        alone[k] = mine.sum() > 12 * UP * UP and axis(np.argwhere(mine))[1] >= 3
    centre = ndi.label(morphology.skeletonize(loose) & ~firm, structure=np.ones((3, 3)))[0]
    return alone[flab] | bridges(flab, 12 * UP * UP) | bridges(centre, np.inf)


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
    # smooth the edge, but keep the thin clay on the ground (the bow's tips, the axe blade's
    # point): light ridges narrower than 5 plate px. The strap is drawn from its trace instead.
    string, strap = polyline(g.shape, STRING, STRING_W), polyline(g.shape, STRAP, STRING_W)
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    ridge &= ~ndi.binary_dilation(strap, iterations=3 * UP)
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # lines: the plate's dark lines inside the figures, the outline, the bowstring, and the solid
    # paint. The thin brown lines (his knee and shin, folds of his chiton) fade in places: a
    # looser threshold finds the faint stretches (faint_stretches says which are lines).
    # Every line is then at least 2 plate px wide, or the thin ones break up when the line
    # weight is evened out (it moves every line by the same amount)
    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    for pts in TRACED:
        lines |= traced(g, pts, TRACED_W) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    face = np.zeros_like(fig)
    for box in FACES:
        fx0, fy0, fx1, fy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        face[fy0:fy1, fx0:fx1] = True
    lines = np.where(face, (ndi.gaussian_filter(g, 0.5 * UP) < FACE_DARK) & fig, lines)
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(2.5 * UP))
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    size = np.bincount(lab.ravel())
    ink &= np.where(face, (size > 3 * UP * UP)[lab], (size > 12 * UP * UP)[lab])   # a stroke of stubble stays
    ink |= string | strap

    # the pockets stay open in the dark theme; the string and the strap, thin clay lines on
    # the ground, keep a clay rim there
    held = ndi.binary_fill_holes(fig | string) & ground
    rims = ndi.binary_dilation(string | strap, iterations=2 * UP)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, rim_lines=rims,
        title='An Amazon with bow and axe fighting a Greek hoplite',
        desc='Line drawing after the 1847 plate of a red-figure amphora formerly in the Pizzati collection, '
             'Florence (Gerhard, Auserlesene griechische Vasenbilder III, Taf. CLXV, 4, "Theseus und '
             'Antiope"); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
