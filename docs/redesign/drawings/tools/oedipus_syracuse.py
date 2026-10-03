"""Oedipus Tyrannus: Oedipus, standing with his hand to his beard, from the
Sicilian red-figure calyx-krater attributed to the Capodarso Painter,
c. 330-320 BCE, Syracuse, Museo Archeologico Regionale "Paolo Orsi" 66557,
excavated at Syracuse in 1968-69. The scene is usually read as one from the play:
the old Corinthian messenger, Oedipus, Jocasta, and their two daughters.
Photo: Dan Diffendale, 2024, CC BY-NC-SA 2.0. The drawing traces only the
ancient painting, which is public domain, so it does not carry the photo's
licence (John, 2026-10-02); the photo is credited:
https://www.flickr.com/photos/dandiffendale/53976554822/
original file: https://live.staticflickr.com/65535/53976554822_177bacc236_o.jpg

Red-figure photo -> drawing. Black glaze surrounds most of the figure, so
the cut is loose there: inside OUTLINE, wide areas of glaze that reach the
background are left out and the clay figure, with its painted lines, stays.
Hand-drawn shapes do the rest: the stage floor and the girl (FLOOR, below
the hem), the modern plaster fill by his elbow (PLASTER), his hair (HAIR,
drawn solid), and his two black shoes on the floor (SHOES). His beard is
drawn solid too, with its long clay strands as light lines (BEARD), and his
face lines as even lines along their centres (FACE). His hand at his beard
is redrawn stroke by stroke after John's trace of it (HAND, HAND_LINES).
Three cracks cross the figure; their lines are erased (CRACKS) and painted
lines broken by them are joined across the gap. A fourth, a wide break
mended with grey plaster beside his hand, is erased whole (BREAK): the edge
of his sleeve is drawn through it and his robe's folds carried across it.
Below his sleeve the staff
is redrawn as a straight rod on its painted centre line (STAFF): flaking
has left its edges ragged.

    python3 docs/redesign/drawings/tools/oedipus_syracuse.py path/to/photo.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "oedipus-tyrannus.svg"
BOX = (1382, 922, 2962, 3917)  # photo crop around him; all points below are crop (x, y)
CLAY_L, WIDE = 75, 10           # clay is brighter than CLAY_L; glaze wider than 2*WIDE px is ground
SHOE_L = 105                    # the shoes are greyer than the floor
HAIR_REACH = 10                 # curls: glaze this close to the clay between them

# Loose cut through the glaze around him (the curls and the shoes included;
# the staff below his sleeve is drawn as a rod, STAFF); tight only where
# clay touches clay: the flaked glaze left of his robe (x 312, y 1200-1950)
# and the column (x 1188, y 850-1100).
OUTLINE = [(240, 30), (720, 30), (930, 160), (940, 400), (1060, 560), (1150, 760), (1188, 880),
           (1188, 1060), (1120, 1160), (1035, 1250), (1028, 1400), (1045, 1600), (1040, 2100), (1040, 2580),
           (1140, 2600), (1150, 2760), (1110, 2880), (940, 2940), (380, 2945), (370, 2860),
           (338, 2790), (336, 2600), (336, 2400), (334, 2250), (325, 2100), (315, 1950), (310, 1900),
           (312, 1800), (314, 1700), (314, 1600), (312, 1500), (312, 1400), (312, 1300), (314, 1200),
           (318, 1110),
           (60, 1000), (60, 860), (100, 700), (180, 540), (250, 440), (255, 300), (230, 150)]
# The stage floor and everything right of his shoe: below the hem.
FLOOR = [(0, 2780), (380, 2780), (430, 2815), (560, 2818), (700, 2815), (800, 2815), (935, 2808),
         (965, 2760), (985, 2690), (998, 2630), (1040, 2595), (1580, 2595), (1580, 2995), (0, 2995)]
PLASTER = [(0, 995), (110, 1012), (250, 1052), (262, 1100), (230, 1250), (170, 1400),
           (110, 1500), (0, 1520)]
# The head, in three zones. His hair is a mass of tiny curls that traces as
# speckle, so it is drawn solid, as hair often is on red-figure vases, with
# its curly outline (HAIR). His beard (BEARD) is a fan of strokes too dense to
# hold apart at the house line weight, so it is drawn solid too, with its
# longest clay strands kept as light lines. The face (FACE) has its own
# finer lines.
# The face's top edge runs just inside the forehead, below the hairline.
HAIRLINE = [(302, 258), (320, 240), (340, 228), (360, 222), (380, 224), (400, 236), (420, 250),
            (445, 264), (468, 290)]
HAIR = [(290, 262), (294, 205), (312, 150), (350, 110), (405, 82), (470, 68), (550, 62), (635, 80),
        (700, 108), (765, 150), (830, 205), (875, 262), (900, 335), (905, 420), (870, 462), (800, 482),
        (745, 492), (712, 540), (700, 600), (660, 630), (610, 615), (600, 560), (585, 480), (560, 420),
        (520, 380), (470, 360)] + HAIRLINE[::-1]
FACE = HAIRLINE + [(466, 345), (440, 372), (410, 392), (392, 428), (372, 424), (345, 370), (318, 300)]
# His hand at his beard is redrawn stroke by stroke (HAND_LINES), after John's
# trace of it (2026-10-02). Each stroke follows a painted line, read from
# Diffendale's second photo of the krater, which shows the hand more sharply
# (https://www.flickr.com/photos/dandiffendale/53977685498/); where the paint
# is worn, or hidden under the two restored patches, it follows John's trace.
# The thumb stands between the yellow flap of his sleeve and the V of its web;
# the index finger runs along the top, under his beard; three fingers curl
# below it. Inside HAND only these strokes are drawn, and the solid beard
# stops at it.
HAND = [(341, 480), (372, 481), (384, 482), (393, 479), (401, 476), (413, 474), (426, 472), (440, 471),
        (452, 473), (461, 477), (468, 486), (477, 490), (488, 486), (500, 486), (512, 487), (521, 488),
        (528, 492), (530, 499), (526, 507), (512, 509), (498, 510), (486, 511), (484, 520), (481, 532),
        (480, 543), (485, 549), (489, 558), (492, 570), (494, 584), (496, 597), (497, 609), (496, 619),
        (491, 626), (482, 627), (474, 627), (471, 634), (464, 643), (463, 655), (462, 667), (458, 678),
        (448, 690), (438, 704), (428, 719), (419, 734), (410, 748), (404, 757), (396, 762), (393, 750),
        (391, 725), (388, 700), (383, 675), (378, 650), (372, 625), (367, 600), (363, 578), (359, 560),
        (355, 540), (350, 520), (345, 500)]
HAND_LINES = [
    [(365, 553), (367, 540), (369, 524), (370, 508), (371, 497), (374, 490), (379, 490), (384, 497),
     (389, 510), (394, 524), (399, 537)],  # the thumb, round its tip to the web
    [(426, 502), (416, 516), (409, 526), (403, 535), (399, 537)],  # the web's other side
    [(399, 538), (395, 544), (389, 551), (385, 560), (381, 572), (377, 588), (368, 603), (357, 614)],  # the hand's back
    [(381, 482), (395, 484), (410, 486), (425, 488), (438, 490), (446, 491)],  # the line above the index finger
    [(382, 494), (392, 494), (405, 496), (417, 498), (430, 499), (442, 500), (455, 499), (466, 497),
     (476, 493), (487, 489), (500, 489), (512, 490), (521, 491), (526, 495), (526, 501), (520, 506),
     (509, 507), (497, 507), (487, 508), (476, 510), (465, 514), (455, 518), (447, 524), (438, 531),
     (431, 537), (427, 541)],  # the index finger, out to its tip and back
    [(481, 508), (480, 520), (478, 532), (476, 544)],  # the hand's edge against the beard
    [(427, 541), (440, 540), (455, 539), (467, 540), (475, 544), (481, 551), (485, 560), (488, 572),
     (490, 585), (492, 598), (493, 610), (490, 618), (484, 622), (477, 621), (474, 613)],  # second finger
    [(484, 600), (485, 606), (486, 612)],  # its nail
    [(427, 565), (440, 564), (455, 564), (463, 566), (468, 571), (471, 579), (473, 590), (473, 603),
     (472, 616), (469, 627), (463, 635), (457, 639)],  # third finger
    [(422, 598), (435, 598), (448, 600)], [(424, 601), (433, 606), (442, 612)],  # a crease
    [(412, 621), (424, 617), (437, 618), (444, 624), (447, 634), (449, 645), (452, 656), (451, 666),
     (446, 676), (439, 687), (431, 699), (422, 714), (413, 729), (405, 743), (399, 752), (391, 750),
     (380, 743), (367, 734)],  # fourth finger, to his wrist
    [(433, 637), (437, 647), (440, 657), (441, 667)],
]
HAND_W = 7  # px, about the median width of his painted lines
# A break runs down beside his hand, from the top of his sleeve to the long
# crack below his chest, mended with grey plaster (John, 2026-10-02: "it looks
# like damage to the vase"). Inside BREAK nothing is traced. The edge of his
# sleeve is drawn where its yellow ends, on the break's left (SLEEVE_EDGE;
# above the break, the edge of the yellow flap beside his thumb), and the
# lines of his hand and robe that run into the break are carried on across
# it to that edge.
SLEEVE_EDGE = [(372, 492), (369, 520), (366, 545), (359, 570), (354, 600), (357, 650), (362, 700),
               (368, 750), (373, 800), (375, 850), (375, 900), (371, 950), (365, 1000), (358, 1050),
               (355, 1085)]
BREAK = [(341, 482), (343, 500), (344, 530), (340, 560), (350, 600), (356, 650), (358, 700), (362, 750),
         (368, 800), (362, 850), (368, 900), (362, 950), (350, 1000), (348, 1050), (352, 1095),
         (424, 1095), (426, 1050), (428, 1000), (428, 950), (426, 900), (424, 850), (422, 800), (416, 750),
         (406, 700), (394, 650), (392, 600), (390, 560), (366, 530), (360, 500), (358, 482)]
BEARD = [(372, 424), (392, 428), (410, 392), (440, 372), (470, 360), (520, 380), (560, 420), (585, 480),
         (600, 560), (560, 600), (480, 600), (420, 560), (395, 500)]
POCKET = [(303, 1300), (290, 1400), (285, 1500)]  # points in the glaze between staff and robe
# Below his sleeve the staff runs over glaze so flaked that its edges are
# lost in flecks; it is drawn as the straight rod it is, on its painted
# centre line (measured at y 1200-1600), STAFF_W px wide.
STAFF, STAFF_W = ((338, 1000), (192, 1696)), 22
SHOES = [[(385, 2818), (755, 2818), (765, 2870), (700, 2918), (400, 2925), (378, 2870)],
         [(950, 2650), (1132, 2650), (1136, 2720), (1112, 2842), (990, 2852), (945, 2795)]]
# rough paths of the cracks; each is snapped to the line within CORRIDOR px
CRACKS = [[(0, 1005), (250, 1062), (450, 1100), (690, 1140), (970, 1112), (1290, 1000), (1580, 810)],
          [(125, 1465), (250, 1610), (340, 1720), (465, 1895), (665, 2165), (840, 2390), (955, 2500),
           (1065, 2600), (1200, 2740)],
          [(65, 16), (180, 230), (290, 468)]]


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(pts, float))


CORRIDOR = 14


def crack_bands(L, shape, width=5):
    """Each crack snapped to the line nearest its rough points, widened."""
    from skimage.draw import line
    band = np.zeros(shape, bool)
    # a crack is darker than the clay it crosses but lighter than the glaze
    contrast = np.abs(L - ndi.uniform_filter(L, 25))
    for pts in CRACKS:
        pts = [(min(x, shape[1] - 1), min(y, shape[0] - 1)) for x, y in pts]
        rough = np.zeros(shape, bool)
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            rr, cc = line(ya, xa, yb, xb)
            rough[rr, cc] = True
        near = ndi.distance_transform_edt(~rough) <= CORRIDOR
        cost = np.where(near, 1.0 + 40.0 / (1.0 + contrast), 1e4)
        xy = lw.livewire(cost, pts)
        yx = (xy[:, ::-1] - 0.5).astype(int)
        band[yx[:, 0], yx[:, 1]] = True
    return ndi.binary_dilation(band, structure=morphology.disk(width))


def staff_masks(shape):
    """The rod, and the strip beside it whose flecks are cleared: 25 px on
    the left, over open glaze; 4 px on the right, short of his robe."""
    (xa, ya), (xb, yb) = STAFF
    Y, X = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.array([xb - xa, yb - ya], float)
    t = np.clip(((X - xa) * d[0] + (Y - ya) * d[1]) / (d @ d), 0, 1)
    off = ((X - xa) * d[1] - (Y - ya) * d[0]) / np.hypot(*d)  # signed distance; < 0 is left of the rod
    along = np.hypot(X - (xa + t * d[0]), Y - (ya + t * d[1]))
    r = STAFF_W / 2
    rod = (along <= r) & (Y >= ya + 10)
    beside = (Y >= ya + 10) & (Y <= yb + 30) & (off >= -(r + 25)) & (off <= r + 4) & (t > 0) & ~rod
    return rod, beside


PEN = 5  # px, the width of redrawn face lines


def centre_lines(m, spur=6, min_len=14):
    """Centre lines of a stroke mask, with side spurs under `spur` px pruned
    (the line ends are kept) and pieces under `min_len` px dropped."""
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    sk = morphology.skeletonize(m)
    s = sk.copy()
    for _ in range(spur):  # peel the ends...
        s &= ~((ndi.convolve(s.astype(int), k, mode="constant") == 1) & s)
    front = (ndi.convolve(s.astype(int), k, mode="constant") == 1) & s
    for _ in range(spur):  # ...and grow the surviving ends back
        front = ndi.binary_dilation(front, structure=np.ones((3, 3))) & sk & ~s
        s |= front
    return morphology.remove_small_objects(s, max_size=min_len, connectivity=2), k


def pen(m, w):
    """Strokes redrawn as even lines w px wide along their centre lines."""
    s, _ = centre_lines(m)
    return ndi.distance_transform_edt(~s) <= w / 2


def solid_beard(dark, zone):
    """The beard's strokes closed up into one mass, with the long clay strands
    between them carved back in as light lines."""
    from skimage.measure import regionprops
    bd = zone & dark
    mass = ndi.binary_closing(bd, structure=morphology.disk(6)) & zone
    holes = ndi.binary_fill_holes(mass) & ~mass
    mass |= holes & ~morphology.remove_small_objects(holes, max_size=400)
    mass = morphology.remove_small_objects(ndi.gaussian_filter(mass.astype(float), 2.0) > 0.5, max_size=200)
    gaps, _ = ndi.label(mass & ~ndi.binary_dilation(bd), structure=np.ones((3, 3)))
    strands = np.zeros_like(mass)
    for r in regionprops(gaps):
        if r.axis_major_length >= 14 and r.eccentricity > 0.85:
            strands[gaps == r.label] = True
    return mass & ~(ndi.distance_transform_edt(~morphology.skeletonize(strands)) <= 2.0)


def drawn(shape, strokes, w):
    """Strokes drawn by hand: each a smooth curve through its points, w px
    wide, with round ends."""
    from scipy.interpolate import splprep, splev
    m = np.zeros(shape, bool)
    for pts in strokes:
        p = np.array(pts, float).T
        tck, _ = splprep(p, k=min(3, p.shape[1] - 1), s=len(pts))
        x, y = splev(np.linspace(0, 1, 40 * len(pts)), tck)
        m[np.round(y).astype(int), np.round(x).astype(int)] = True
    return ndi.distance_transform_edt(~m) <= w / 2


def carry_across(lines, zone, stop, w, reach=90):
    """Folds that run into zone from the right are carried on across it in a
    straight line, the way their last 30 px run, until they meet stop. Only
    long, nearly level lines count as folds; the zone's own ragged edges,
    which run along it, are left out."""
    sk = morphology.skeletonize(lines & ~zone)
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    around = ndi.binary_dilation(zone, iterations=6)
    ends = sk & (ndi.convolve(sk.astype(int), k, mode="constant") == 1) & around
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    path = np.zeros_like(lines)
    for y, x in zip(*np.nonzero(ends)):
        ys, xs = np.nonzero(lab == lab[y, x])
        if (lab == lab[y, x]).sum() < 40:  # a fleck, not a fold
            continue
        near = np.hypot(ys - y, xs - x) <= 30
        ys, xs = ys[near], xs[near]
        if xs.max() - x < 20 or xs.min() < x:  # it must run off to the right of its end
            continue
        b, c = np.polyfit(xs, ys, 1)
        if abs(b) > 0.7:  # too steep for a fold
            continue
        for xx in range(x - 1, x - reach, -1):
            yy = int(round(b * xx + c))
            if not (0 <= yy < lines.shape[0]) or stop[yy, xx] or not around[yy, xx]:
                break
            path[yy, xx] = True
    return ndi.distance_transform_edt(~path) <= w / 2


def main(src: str) -> None:
    a = np.asarray(Image.open(src).convert("RGB").crop(BOX), dtype=np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    shape = L.shape
    inside = poly(shape, OUTLINE) & ~poly(shape, FLOOR) & ~poly(shape, PLASTER)
    hand_zone = poly(shape, HAND)
    face_zone, beard_zone = poly(shape, FACE), poly(shape, BEARD) & ~hand_zone
    hair_zone = poly(shape, HAIR) & ~face_zone & ~beard_zone
    head = hair_zone | face_zone | beard_zone | hand_zone
    shoe_zone = np.zeros(shape, bool)
    for s in SHOES:
        shoe_zone |= poly(shape, s)
    cracks = crack_bands(L, shape)

    clay = ndi.binary_opening(L > CLAY_L, structure=morphology.disk(2))  # drops hairline cracks and specks
    dark = L <= CLAY_L
    # the figure: its large areas of clay (flecks of clay in the glaze are small)...
    body = morphology.remove_small_objects(clay & inside & ~cracks, max_size=4000)
    # ...his curls: glaze within reach of the clay showing between them...
    gaps = clay & hair_zone
    hair = hair_zone & dark & (ndi.distance_transform_edt(~gaps) <= HAIR_REACH)
    hair = ndi.binary_closing(hair, structure=morphology.disk(5)) & hair_zone
    hair = ndi.gaussian_filter(ndi.binary_fill_holes(hair).astype(float), 2.0) > 0.5
    hair = morphology.remove_small_objects(hair, max_size=400)
    # ...and his shoes, solid
    shoes = shoe_zone & (L < SHOE_L) & ~cracks
    shoes = ndi.binary_closing(ndi.binary_opening(shoes, structure=morphology.disk(3)), structure=morphology.disk(10))
    shoes = ndi.binary_fill_holes(morphology.remove_small_objects(shoes, max_size=2000))
    shoes = ndi.binary_opening(shoes, structure=morphology.disk(8))  # worn edges rounded off
    # painted lines inside the clay close up; glaze at the outline, and the
    # glaze between his staff and his robe (POCKET), stay out
    sil = ndi.binary_closing(body | hair | shoes, structure=morphology.disk(4))
    # whole again across the cracks, but not where a crack runs along his
    # outline: there the crack is the glaze's, not his
    glaze = ndi.binary_dilation(ndi.binary_opening(dark, structure=morphology.disk(WIDE)), structure=morphology.disk(12))
    sil |= ndi.binary_closing(sil, structure=morphology.disk(9)) & cracks & ~glaze
    holes, _ = ndi.label(ndi.binary_fill_holes(sil) & ~sil)
    open_ = [holes[y, x] for x, y in POCKET if holes[y, x]]
    sil |= (holes > 0) & ~np.isin(holes, open_)
    rod, beside = staff_masks(shape)
    brk = poly(shape, BREAK)
    sil = (sil & ~beside) | rod | brk
    sil = morphology.remove_small_objects(sil, max_size=4000)
    sil = ndi.gaussian_filter(sil.astype(float), 1.5) > 0.5

    # painted lines and dots by local contrast; wide strokes by a wider window
    lines = lw.ink_lines(L, size=21, low=13, high=32, sigma=1.2) | lw.ink_lines(L, size=45, low=40, high=70, sigma=1.5)
    lines &= ndi.binary_erosion(sil, structure=morphology.disk(4))
    lines &= ~(beside | rod | head)
    beard = solid_beard(dark, beard_zone)
    face = lw.ink_lines(L, size=15, low=16, high=38, sigma=1.0) & ndi.binary_erosion(face_zone, iterations=3)
    face &= ~ndi.binary_dilation(ndi.binary_opening(dark, structure=morphology.disk(8)), iterations=3)  # the ground
    dots = ndi.binary_opening(face, structure=morphology.disk(3))  # the pupil, kept solid
    face = pen(face & ~ndi.binary_dilation(dots, iterations=2), PEN) | dots
    lines |= hair | beard | face | shoes
    broken = lines & ~cracks  # the cracks erased...
    lines = broken | (ndi.binary_closing(broken, structure=morphology.disk(6)) & cracks)  # ...lines rejoined
    lines = morphology.remove_small_objects(lines, max_size=120)  # specks of wear
    sleeve = drawn(shape, [SLEEVE_EDGE], HAND_W)
    lines = (lines & ~brk) | carry_across(lines & ~hand_zone, brk, sleeve, HAND_W) | sleeve \
        | drawn(shape, HAND_LINES, HAND_W)
    edge = sil & ~ndi.binary_erosion(sil, structure=morphology.disk(4))

    if "--masks" in sys.argv:  # diagnostic: the masks over the photo
        g = np.clip(L, 0, 255) * 0.55
        rgb = np.stack([g, g, g], -1)
        rgb[sil] = rgb[sil] * 0.55 + np.array([255, 60, 60]) * 0.45
        rgb[cracks] = [0, 255, 255]
        for m, c in ((poly(shape, OUTLINE), (255, 255, 0)), (poly(shape, FLOOR), (60, 120, 255)),
                     (poly(shape, PLASTER), (60, 255, 60)), (hair_zone, (255, 0, 255)), (shoe_zone, (255, 160, 0))):
            rim = m & ~ndi.binary_erosion(m, iterations=3)
            rgb[rim] = c
        Image.fromarray(rgb.astype(np.uint8)).save(sys.argv[2])
        return

    info = lw.trace_svg(
        edge | lines, OUT, body=sil,
        title="Oedipus, bearded, in a long embroidered robe, his hand at his beard, holding a staff",
        desc="Line drawing after the Sicilian red-figure calyx-krater attributed to the Capodarso Painter, "
             "c. 330-320 BCE, Syracuse, Museo Archeologico Regionale Paolo Orsi 66557, read as a scene from "
             "Sophocles' Oedipus Tyrannus; traced from Dan Diffendale's photograph: cut out, cracks removed, "
             "redrawn as line.")
    print(OUT, info)
    if len(sys.argv) > 2:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(sys.argv[2]))
        lw.qa_dark(OUT, info["box"], Path(sys.argv[2]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(sys.argv[1])
