"""Suppliant Women (Aeschylus): Amymone, one of the Danaids, running, and her father Danaus, from
Lenormant and de Witte, Élite des monuments céramographiques III (Paris, 1858), pl. XX, as scanned
by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1858bd3%3A303_Planche_ROEM_020.jpg/full/full/0/default.jpg
(1976 x 2871, printed sideways; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0341)
The vase, as the Élite gives it (text p. 55): a Nola amphora, formerly in the Durand collection
(Catalogue Durand no. 208), in 1858 owned by M. Paravey. Poseidon pursues Amymone on the front;
Danaus, an old man in a mantle holding a staff, is on the back, and the plate sets him beside her.

Plate -> drawing, as for Hippolytus (tools/hippolytus.py): the plate prints the black ground
black, so the figures' outline comes free.
  - The scan is turned upright (90 degrees clockwise); every point below is in that frame.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets
    of ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is the clay area the ground leaves, from SEEDS: Amymone and Danaus, his staff.
    The clay strip they stand on is cut off along its top edge (BOTTOM).
  - Poseidon is out. His cloak, forearm, hand and sceptre come into the crop at the left but
    touch neither figure, and drop out with the ground. The toes of his front foot lie across
    her raised heel and the ball of her foot: they are cut off (POSEIDON_TOES) along a line from
    her heel to the ball of her foot, which becomes her sole, and his lines that lay over her
    foot go (HIS_LINES).
  - Lines: the plate's dark lines inside the figures (local contrast), joined where the print
    breaks them (JOINS); the outline; and the plate's solid paint: the hair inside its reserved
    outline (HAIR), the dashes and dots of her hem's border, the two dark bands on Danaus
    (WALLS part them from the ground they run into).
  - Dark theme: the figures' area is the body; the ground pockets stay open, as on the vase.

    python3 docs/redesign/drawings/tools/suppliants_aesch.py 03n_elite3_pl20.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "suppliants-aesch.svg"

X0, Y0, X1, Y1 = 1085, 256, 2728, 1584    # crop in the upright plate's px
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
# The plate's own line weight (0.15% of the drawing's width), not the house weight (0.22%): the
# house weight is a share of the longer side, and this drawing is wider than tall, so at it the
# lines came out 3.7 plate px wide (median, on the SVG rendered at 3x), against 3.0 on
# Hippolytus, whose figures are as tall in plate px (about 1,200), and 2.3 at the plate's own.
# The dots and dashes of her hem's border ran into the pleats, and her fingers kept little clay
# between their outlines.
WEIGHT = "own"
AUTO_GROUND = 10000                       # plate px: dark areas this large are ground
SEEDS = [(1785, 956), (2465, 956)]        # her dress, his mantle (plate px)
# pockets of ground the figures close in, smaller than AUTO_GROUND (a point in each, plate px):
# between Danaus' ankles, above his front foot
POCKETS = [(2393, 1455)]
# Two dark brown bands on Danaus are paint: the wavy band across his chest (a small head at its
# upper end) and the band round his ankles, with its loop. Each runs into the ground: the chest
# band at his outline, the ankle band along the top of the gap between his ankles and of the
# ground behind his far foot, where only a faint clay line, often broken, parts them. WALLS
# (plate px) part them from the ground, WALL_W px wide: along those clay lines, and along his
# outline across the chest band's end.
WALLS = [[(2350, 1425.5), (2358.8, 1424.4), (2370, 1423.1), (2382.5, 1421.9), (2395, 1420), (2407.5, 1418.1),
          (2417.5, 1416.3), (2426.3, 1414.4), (2434, 1412.5)],
         [(2483, 1400), (2495, 1402), (2505, 1403.5), (2517, 1405.5)],
         [(2295, 737), (2290, 765)]]
WALL_W = 1.5
# the top edge of the clay strip they stand on, 2 px above it (measured every 80 px)
BOTTOM = [(1060, 1524), (1140, 1524), (1220, 1534), (1300, 1540), (1380, 1537), (1460, 1530),
          (1540, 1524), (1620, 1522), (1700, 1525), (1780, 1533), (1860, 1545), (1940, 1561),
          (2020, 1558), (2100, 1545), (2180, 1530), (2260, 1523), (2340, 1519), (2420, 1517),
          (2500, 1520), (2580, 1538), (2660, 1555), (2740, 1570)]
# Poseidon's front foot, from the crop's left edge to the line from her heel to the ball of her
# foot (her sole, hidden by his toes on the plate)
POSEIDON_TOES = [(1080, 1445), (1128, 1465), (1131, 1478), (1137, 1487), (1144, 1495), (1150, 1502),
                 (1155, 1508), (1157, 1516), (1080, 1516)]
# his lines that lay over her foot: the top of his toes, the line between them, his big toe's tip
HIS_LINES = [(1131, 1476), (1150, 1478), (1166, 1484), (1163, 1497), (1158, 1508), (1155, 1508),
             (1150, 1502), (1144, 1495), (1137, 1487)]
# The hair is dark like the ground, inside the painter's reserved outline, a thin clay line round
# the head (as on the Berlin Oedipus and Euphorbos). A least-cost path follows that line's light
# ridge through hand-placed points (plate px), from the forehead over the head to the nape
# (RESERVED); straight lines through the face close it (CLOSE). Within, the dark is hair, drawn
# solid; her fillet, a clay line across her hair, stays. The reserved line itself is drawn as the
# hair's outline, RESERVED_W plate px wide along its ridge (it is 2-4 px wide): at this weight the
# outline left its wider stretches showing, in dashes. The dark theme gives the outline a clay rim
# on the ground side, where the reserved line was.
HAIR = {
    'amymone': dict(
        RESERVED=[(1567, 370), (1571, 356), (1585, 345), (1610, 331), (1647, 329), (1682, 337), (1710, 359),
                  (1731, 372), (1744, 385), (1752, 401), (1747, 419), (1735, 427), (1717, 430), (1702, 431)],
        CLOSE=[(1695, 440), (1650, 442), (1600, 428), (1578, 400)]),
    'danaus': dict(
        RESERVED=[(2317, 357), (2305, 355), (2299, 345), (2299, 336), (2305, 331), (2315, 329), (2322, 320),
                  (2331, 317), (2337, 319), (2350, 314), (2390, 306), (2430, 310), (2457, 326), (2472, 352),
                  (2477, 370), (2480, 390), (2470, 400), (2460, 403)],
        CLOSE=[(2445, 410), (2400, 412), (2360, 385), (2330, 365)]),
}
RESERVED_W = 4.5
# her fillet, a clay line across her hair from the forehead to above the ear: followed along its
# light ridge through these points (plate px) and kept open in the hair, FILLET_W plate px wide
FILLET = [(1592.5, 381), (1596, 389), (1602, 394), (1610, 398.5), (1618, 402.5), (1630, 404), (1636, 406),
          (1640, 411), (1647, 413), (1657, 412.5), (1667, 410), (1673, 407.5)]
FILLET_W = 2.5
# her outstretched hand (box, plate px): its fingers are clay strips 4-6 px wide, the ground
# between them 2-3 px. Here the ground is found at less blur, so the gaps stay ground, and the
# outline is drawn finer (HAND_EDGE plate px), so each finger keeps its clay inside it.
HAND = (1193, 748, 1262, 790)
HAND_EDGE = 1.2
# breaks in the plate's thin lines, where the print fades (her chiton, her skirt, his chest) or a
# flaw crosses a line (a pink smudge and a light speck on his chest): the line ends either side
# (plate px), joined straight, JOIN_W px wide, a little past each end. Ends that face each other
# across a short gap and are true ends (his fingers, two short strokes on her dress) stay apart.
JOINS = [[(1595, 591), (1595, 596)], [(1699, 1363), (1697, 1367)], [(2452, 542), (2449, 546)],
         [(2350, 626), (2347, 630)], [(2531, 559), (2527, 564)], [(2355, 582), (2351, 588)],
         [(2400, 530), (2395, 534)]]
JOIN_W = 2.3


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def light_path(g, pts):
    """A least-cost path along a thin clay line's light ridge, through hand-placed points (plate
    px); (x, y) at UP."""
    P = up(pts)
    pad = 10 * UP
    x0, y0 = int(P[:, 0].min()) - pad, int(P[:, 1].min()) - pad
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.5 * UP)
    cost = 1 + 40 * np.exp(-np.clip(w - ndi.grey_opening(w, size=(5 * UP, 5 * UP)), 0, None) / 12)
    return lw.livewire(cost, [(x - x0, y - y0) for x, y in P]) + (x0, y0)


def polyline(pts):
    """Hand-placed points (plate px) joined by straight lines, a point per UP px, (x, y) at UP."""
    P = up(pts)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (path[:, ::-1] - 0.5).astype(int)
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def faint_stretches(firm, loose):
    """The faint stretches of the plate's thin lines, from the looser threshold, where they are
    lines (as in hippolytus.py). Away from the firm lines, a stretch long enough to stand alone
    must be line-shaped (3 times as long as wide; a patch of the print's tint is rounder). A short
    one, or a piece of the looser lines' centre line between firm lines, must bridge two firm lines
    and run along at least one of them: a gap in a line, or a line meeting another."""
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
    plate = Image.open(src).convert('L').transpose(Image.Transpose.ROTATE_270)   # upright
    plate = plate.crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside: on and below the strip's top edge
    bottom = up(BOTTOM)
    outside = yy >= np.interp(xx, bottom[:, 0], bottom[:, 1])
    other = lw.polygon_mask(g.shape, up(POSEIDON_TOES))

    # ground: dark, thin lines opened away; the large areas and the listed pockets. The hair is not
    # ground: its dark is paint
    hair = np.zeros(g.shape, bool)
    reserved = np.zeros(g.shape, bool)
    for h in HAIR.values():
        path = light_path(g, h['RESERVED'])
        hair |= lw.polygon_mask(g.shape, np.vstack([path, up(h['CLOSE'])]))
        reserved |= along(g.shape, path, RESERVED_W)
    mass = ndi.binary_opening(gs < DARK, structure=morphology.disk(2 * UP)) & ~outside
    hand = np.zeros(g.shape, bool)
    hx0, hy0, hx1, hy1 = [(v - o) * UP for v, o in zip(HAND, (X0, Y0, X0, Y0))]
    hand[hy0:hy1, hx0:hx1] = True
    fine = ndi.binary_opening(ndi.gaussian_filter(g, 0.35 * UP) < DARK, structure=morphology.disk(1))
    mass = np.where(hand, fine, mass)
    for pts in WALLS:
        mass &= ~along(g.shape, polyline(pts), WALL_W)
    dark = mass & ~hair
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = (dark & ~ground) | (mass & hair)

    # the scene: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground & ~outside & ~other)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground   # paint stays theirs; pockets of ground do not
    # smooth the edge, but keep thin clay on the ground (the staff, fingertips): light ridges
    # narrower than 5 plate px
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # lines: the plate's dark lines inside the figures, the outline, and the solid paint; a
    # looser threshold finds the faint stretches of the thin lines (faint_stretches says which
    # are lines). Every line is then at least 2 plate px wide, or the thin ones break up when
    # the line weight is evened out
    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    lines &= ~lw.polygon_mask(g.shape, up(HIS_LINES))
    for a, b in JOINS:
        a, b = np.array(a, float), np.array(b, float)
        u = (b - a) / np.hypot(*(b - a))
        lines |= along(g.shape, polyline([a - 1.5 * u, b + 1.5 * u]), JOIN_W) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(2.5 * UP))
    edge = np.where(hand, fig & ~ndi.binary_erosion(fig, iterations=round(HAND_EDGE * UP)), edge)
    ink = lines | solid | edge | (reserved & fig)
    ink &= ~along(g.shape, light_path(g, FILLET), FILLET_W)
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]

    # the pockets stay open in the dark theme
    held = ndi.binary_fill_holes(fig) & ground
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight=WEIGHT,
        title='Amymone running, and her father Danaus',
        desc='Line drawing after the 1858 plate of a Nola amphora formerly in the Durand collection '
             '(Lenormant and de Witte, Élite des monuments céramographiques III, pl. XX); cut out and '
             'retraced, without Poseidon.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
