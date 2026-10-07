"""Women of Trachis: Herakles and Deianeira with their infant son Hyllos, between Athena and
Deianeira's father Oineus, all five named on the vase, from Gerhard, Auserlesene griechische
Vasenbilder II (1843), Taf. CXVI, "Herakles und Hyllos", as scanned by Heidelberg University
Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_116.jpg/full/full/0/default.jpg
(2105 x 2780; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0241)
The vase, as Gerhard gives it (text pp. 114-120): a red-figure pelike "of Nolan style", described
by Brondsted among the Campanari vases (no. 1), then Durand collection no. 318, bought at the
Durand sale by W. Hope; the other side, drawn small on the plate, is Hermes killing Argos.

Plate -> drawing, as for Hippolytus (Gerhard AV III, Taf. CLXV): the plate prints the black
ground black, so the figures' outline comes free.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets
    of ground the figures close in (POCKETS).
  - The panel is a ring sector: the palmette band above, the meander band below. Both edges are
    arcs of circles, fitted to the plate (TOP_ARC, the ground's upper edge, within 0.7 px;
    BOTTOM_ARC, the top edge of the meander band's top line, which the feet stand on). Where a
    figure crosses a band (Athena's crest and spear, her sleeve), the part kept is outlined
    along the plate's own lines (CREST, SPEAR, SLEEVE).
  - The scene is the clay area the ground leaves, from SEEDS.
  - Lines: the plate's own (LINE_DARK): its dark paint, solid black included (hair, beards, the
    black borders of the mantles), and its thin brown lines by a ridge filter; the outline; the
    crest's holder built as the plate draws it (HOLDER).
  - Traced as drawn (linework weight "drawn"), at the plate's own line weight: re-weighting
    blurs the 1 px gaps between close lines shut (LESSONS.md, Andromache).

    python3 docs/redesign/drawings/tools/trachiniae.py gerhard1843bd2_116.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "trachiniae.svg"

X0, Y0, X1, Y1 = 119, 155, 1852, 1609     # crop in plate px (the panel)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large are ground
TOP_ARC = (904.9, -1176.2, 1559.9)        # centre x, y and radius, plate px: above it is the palmette band
# below BOTTOM_ARC, the meander band: its centre is the one fitted to the band (to the light strip
# under its top line, within 2 px); its radius, the line's top edge under the feet (the median of
# 479 columns). Cut through the line's centre instead, the soles came out twice as thick as the
# other outlines, and the dark theme showed a broken clay strip under them.
BOTTOM_ARC = (909.8, -1150.5, 2708.0)
# the left band's inner edge: its inner border line is straight (centre x = 445.5 - 0.318 (y - 380),
# measured from y 380 to 1000), with a thin clay line beside it; the ground starts 7 px further in,
# and the cut runs 1.5 px inside the ground (at the ground's edge it took in a sliver of the thin
# clay line where the ground narrows to meet Athena's sleeve). Left of the cut is the band. The
# right band touches no figure.
LEFT = [(454 + 0.318 * 225, 155), (454 - 0.318 * 1229, 1609)]
# where a figure crosses a band, the part kept, outlined along the plate's lines (plate px); each
# polygon closes inside the panel, where it changes nothing.
# Athena's crest rises through the palmette band to the vase's rim line: the line of its tail
# (which hangs behind her helmet; straight, measured from y 304 to 340, then curving up to meet
# the rim line at x 633), the rim line's lower edge
# (its centre + 2 px: cut through the centre, the crest's top came out a line and a half wide), its
# front line (measured every 5 px, 0.5 px outside the line's centre) down to its tip, the top edge
# of the band's lower border line (the border line itself is band), and the top of her helmet,
# which rises above the band.
CREST = [(541, 400), (546, 390), (551, 380), (557, 367), (560, 361), (565.5, 346), (567.7, 340),
         (569.1, 336), (572, 328), (575.6, 318), (579.3, 308), (585.6, 296), (589.8, 283),
         (594.5, 270), (599.5, 258), (605.5, 245), (611, 236), (616, 229), (621, 227.6), (625, 226),
         (629, 224.4), (633, 222.8), (640, 224), (660, 227.5), (680, 231), (700, 234), (720, 236.5),
         (733, 239), (734.5, 240), (739.5, 244), (745.5, 252), (746.5, 256), (748.5, 260),
         (750.5, 265), (751.5, 270), (751.5, 280), (750.5, 285), (750.5, 290), (748.5, 295),
         (747.5, 300), (745.5, 305), (744.5, 310), (742.5, 315), (740.5, 320), (738.5, 325),
         (736.5, 330), (735.5, 335), (734.5, 340), (732.5, 345), (731.5, 350), (730.5, 355),
         (729, 358), (728, 360), (720, 360), (710, 360), (700, 358.5), (690, 357), (680, 354.5),
         (670, 354), (662, 357), (664, 362), (666, 367), (670, 371.5), (674, 376), (678, 381),
         (680, 400)]
# her spear's head: the clay the palmette's leaves leave round it (the leaves stop at its edge), with
# a thin line along its right edge near the tip; then its shaft, through the band's lower lines
SPEAR = [(466, 198.5), (468, 206), (469.5, 212), (471, 218), (471.5, 224), (471.5, 230), (472.5, 236),
         (473.5, 242), (474.5, 250), (476, 256), (477.5, 262), (480, 268), (482.5, 274), (484, 280),
         (485.5, 286), (496, 292), (499, 300), (504.4, 320), (509.8, 340), (511.2, 345), (517.2, 345),
         (515.8, 340), (510.4, 320), (505, 300), (502, 292), (502.5, 276), (501.5, 270), (499.5, 264),
         (497, 258), (494.5, 252), (492, 246), (490, 240), (488.5, 236), (486.5, 233), (484.5, 230),
         (481.5, 226), (479.5, 224), (476.5, 218), (473.5, 212), (470.5, 206), (467.5, 199)]
# her sleeve hangs over the left band from y 531 down: its upper edge (the line the band's ivy stops
# at, through its measured centre every 3 px, from where it leaves the ground at the top), the curve
# of its outer hem, then the ends of its fringe. (Begun 50 px lower, at a fold, it left the border cut
# slicing across the sleeve, and a sliver of the band's thin clay line in the figure.)
SLEEVE = [(405.7, 532.2), (402.7, 535), (399.6, 537.7), (396.6, 540.6), (393.6, 543.5), (390.5, 546.3),
          (387.4, 549.1), (384.5, 552.1), (381.3, 554.8), (378.3, 557.6), (375.5, 560.7), (372.5, 563.6),
          (369.6, 566.5), (366.7, 569.6), (363.8, 572.6), (361, 575.6), (358.2, 578.7), (355.3, 581.8),
          (352.4, 584.8), (349.5, 587.7), (346.5, 590.6), (343.3, 593.2), (338, 600), (332, 607),
          (327, 615), (324, 624), (322, 634), (321, 643), (323, 650), (329, 652), (332, 660), (333, 672),
          (335, 675), (341, 683), (350, 688), (361, 690), (368, 692), (430, 692), (430, 515),
          (412, 526.7)]
SEEDS = [(330, 1250), (800, 1000), (1200, 1100), (1600, 1200)]   # Athena, Herakles, Deianeira, Oineus
# pockets of ground the figures close in, smaller than AUTO_GROUND (a point in each, plate px):
# between Athena's raised arm and her body; between her spear, the tail of her crest and the band;
# between the tail and her helmet; between Herakles' heel and Athena's spear; between Oineus' feet;
# between Herakles' bow and his mantle; between the thumb and fingers of Oineus' raised hand
POCKETS = [(681, 587), (538, 364), (560, 400), (772, 1495), (1674, 1404), (1022, 888), (1325, 419)]
# paint that runs into the ground, cut from it along the thin clay line between them (plate px):
# the lock of Athena's hair that falls from under her jaw over the aegis
PAINT_CUTS = [[(607, 489), (609.5, 497), (611, 504), (612, 512)]]
# Lines (John, 2026-10-07, of the first pass, drawn by Hippolytus' local-contrast finder: "Details
# are being lost here. Too blotchy"; the finder blurs before it looks, and ran close lines together:
# the pleats at Deianeira's neck, the eyes, the crest's holder). Here the lines are the plate's own:
# its dark paint (darker than LINE_DARK, lightly smoothed: 1 px of clay between two lines stays
# open), and its thin brown lines, by a ridge filter (RIDGE: a line is darker than the clay on both
# sides of it, so the slope at a dark line's edge is not one, and the gap between two lines stays
# open), no lighter than RIDGE_GREY. No line is thinner than LINE_W, nor the outline wider.
LINE_DARK = 115
RIDGE = (8, 16)                           # sato response, hysteresis low and high
RIDGE_GREY = 175
LINE_W = 1.5                              # plate px
SPECK = 4                                 # plate px^2: smaller marks are grain
# Inside the crest's base the plate lets the band show through: the lower leaves of a palmette, the
# arcs round them, a spiral with dots, and the band's lower border, which runs between the crest
# and the helmet. They go (John, 2026-10-07: "Remove the vase band that is still around the base of
# the crest"): every line inside CREST_BASE (plate px), two areas placed between the lines that
# stay: the crest's outline, its holder with the curl under it, the stalk from the curl down to the
# helmet, and the helmet's top line. The stalk and the helmet's line are redrawn at LINE_W through
# their measured centres (STALK, HELMET), as the band's leaves and border touch both.
STALK = [(651.5, 306), (651.5, 309), (650.5, 312), (649, 315), (648, 318), (647, 321), (646, 324),
         (645, 327), (644, 330), (643, 333), (642.5, 336), (642, 339), (641.5, 342), (641, 345),
         (640.5, 348), (640, 350.5)]
HELMET = [(590, 354.5), (596, 353.5), (600, 353), (604, 352), (608, 351.2), (616, 350.6), (628, 350.2),
          (636, 350.6), (644, 351.6), (652, 352.6), (657, 354), (662, 356.5)]
CREST_BASE = [
    # left of the stalk: the leaves and the arcs round them, and the border, from the crest's tail
    # down to the helmet line
    [(564, 336), (576, 327), (580, 318), (587, 311), (597, 306), (610, 304), (619, 304), (620, 319.5),
     (638, 319.5), (639.5, 330), (639, 340), (638.5, 348), (636, 349.7), (628, 349.3), (616, 349.7),
     (608, 350.3), (600, 352.1), (594, 353.1), (590, 353.6), (586, 349.3), (576, 349.3), (570, 352),
     (559, 350)],
    # the stalk's own strip, below the curl (the stalk is redrawn)
    [(638, 319.5), (641, 312), (655, 312), (651, 314.5), (650.5, 317), (649.5, 320), (648, 325),
     (646, 335), (644, 345), (643, 349.5), (638.5, 348), (639, 340), (639.5, 330)],
    # right of the stalk, below the curl and the line from it to the holder's foot: the leaves,
    # the arcs, the spiral and its dots, and the border, down to the helmet line and the crest's base
    [(651, 314.5), (655, 312), (657, 313.5), (663, 313.5), (663, 317), (694.5, 317.5), (695.5, 310),
     (738, 309), (737, 320), (735, 330), (733, 340), (731, 350), (729.5, 364), (668, 364), (662, 362), (662, 355.6),
     (657, 353.1), (652, 351.7), (647, 351.0), (643, 349.5), (644, 345), (646, 335), (648, 325),
     (649.5, 320), (650.5, 317)]]
# Along the crest's top the rim line's lower edge, ragged in the print, dips below the cut in
# places, and at its top-left corner the tip of a band leaf touches its edge: there, within 4 px of
# the edge, only the crest's outline is drawn.
CREST_TOP = [(612, 228), (621, 225), (630, 221.5), (640, 223), (660, 226.5), (680, 230), (700, 233),
             (720, 235.5), (733, 238), (733, 242), (720, 240), (700, 237.5), (680, 234.5), (660, 231),
             (640, 227.5), (632, 226), (624, 229.5), (618, 232.5), (613, 234)]
# The crest's holder is a band of dots between two thin lines, the dots 1-2 px apart: too close
# for any one grey to part them (a light grey ran them into a black band, a dark one broke the band
# into blobs), so it is built as the plate draws it: the band's outline at LINE_W, and the dots'
# dark cores inside it (John, 2026-10-07: "Yes"). HOLDER: the band's box, a point on it, and the
# curl inside the arch (centre and radius, plate px), which is not band.
HOLDER = dict(box=(620, 268, 694, 316), on=(657, 278), curl=(659, 303, 9))


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


def main(src, qa=None):
    plate = Image.open(src).convert('L').crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx / UP + X0, yy / UP + Y0   # plate px

    # outside the panel: the palmette band above, the meander band below
    outside = np.hypot(px - TOP_ARC[0], py - TOP_ARC[1]) < TOP_ARC[2]
    outside |= np.hypot(px - BOTTOM_ARC[0], py - BOTTOM_ARC[1]) > BOTTOM_ARC[2]
    left = up(LEFT)
    outside |= xx < np.interp(yy, left[:, 1], left[:, 0])
    for poly in (CREST, SPEAR, SLEEVE):
        outside &= ~lw.polygon_mask(g.shape, up(poly))

    # ground: dark, thin lines opened away; the large areas and the listed pockets
    dark = ndi.binary_opening(gs < DARK, structure=morphology.disk(2 * UP)) & ~outside
    for pts in PAINT_CUTS:
        dark &= ~polyline(g.shape, pts, 1.5)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]

    # the scene: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground   # paint stays theirs; pockets of ground do not
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # lines: the plate's dark paint and its thin brown lines (see LINE_DARK), the holder, the outline
    from skimage.filters import apply_hysteresis_threshold, sato
    g_fine = ndi.gaussian_filter(g, 0.5 * UP)
    lines = g_fine < LINE_DARK
    lines |= apply_hysteresis_threshold(sato(g_fine, sigmas=[1.0, 1.5, 2.0], black_ridges=True), *RIDGE) & \
        (g_fine < RIDGE_GREY)
    lines &= fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_W * UP / 2) & fig
    hx0, hy0, hx1, hy1 = [(v - o) * UP for v, o in zip(HOLDER['box'], (X0, Y0, X0, Y0))]
    hbox = np.zeros_like(fig)
    hbox[hy0:hy1, hx0:hx1] = True
    ccx, ccy, cr = HOLDER['curl']
    curl = np.hypot(px - ccx, py - ccy) <= cr
    hlab, _ = ndi.label(ndi.binary_closing(g_fine < 140, structure=morphology.disk(2 * UP)) & hbox & ~curl)
    arch = ndi.binary_fill_holes(hlab == hlab[(HOLDER['on'][1] - Y0) * UP, (HOLDER['on'][0] - X0) * UP])
    rim = arch & (ndi.distance_transform_edt(arch) <= LINE_W * UP)
    dots = (g_fine < 90) & (ndi.distance_transform_edt(arch) > 2.5 * UP)
    dlab, _ = ndi.label(dots)
    dots &= (np.bincount(dlab.ravel()) > 2 * UP * UP)[dlab]
    lines = np.where(arch, rim | dots, lines)
    for poly in CREST_BASE + [CREST_TOP]:   # the band in the crest goes; the helmet keeps its top line
        lines &= ~lw.polygon_mask(g.shape, up(poly))
    lines |= (polyline(g.shape, HELMET, LINE_W) | polyline(g.shape, STALK, LINE_W)) & fig
    edge = fig & (ndi.distance_transform_edt(fig) <= LINE_W * UP)
    ink = lines | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]

    # all that is not figure stays open in the dark theme: the pockets, the ground and the bands. (The
    # tracer gives a line with no clay beside it a clay rim; where the plate's outline is wider than
    # a line and a half, its outer part counted as such a line, and the rims showed as clay slivers
    # outside the outline, on the ground.)
    held = ~fig
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight='drawn',
        title='Herakles and Deianeira with their son Hyllos, between Athena and Oineus',
        desc='Line drawing after the 1843 plate of a red-figure pelike formerly in the Durand '
             'collection (Gerhard, Auserlesene griechische Vasenbilder II, Taf. CXVI, "Herakles und '
             'Hyllos"); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
