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
is redrawn stroke by stroke after John's trace of it (HAND, HAND_LINES),
each finger a closed outline, and the black ground showing between two
fingertips is filled (FINGER_GAP). Painted lines broken by wear are joined
across their gaps where two line ends face each other (join_gaps).
Three cracks cross the figure; their lines are erased (CRACKS) and painted
lines broken by them are joined across the gap. A fourth, mended with grey
plaster beside his hand, is erased whole along John's outline of it (BREAK),
with nothing drawn along it: his hand's edges are drawn across it after
John's trace, and his robe's folds are carried across it to his sleeve.
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
HAND = [(369, 481), (384, 482), (393, 479), (401, 476), (413, 474), (426, 472), (440, 471), (452, 473),
        (461, 477), (468, 486), (477, 490), (488, 486), (500, 486), (512, 487), (521, 488), (528, 492),
        (530, 499), (526, 507), (512, 509), (498, 510), (486, 511), (484, 520), (481, 532), (480, 543),
        (485, 549), (489, 558), (492, 570), (494, 584), (496, 597), (497, 609), (496, 619), (491, 626),
        (482, 627), (474, 627), (471, 634), (464, 643), (463, 655), (462, 667), (458, 678), (448, 690),
        (438, 704), (428, 719), (419, 734), (410, 748), (404, 757), (396, 762), (386, 756), (373, 745),
        (367, 720), (359, 680), (354, 640), (353, 600), (355, 570), (360, 545), (366, 520), (369, 492)]
HAND_LINES = [
    [(371, 501), (371, 496), (374, 490), (379, 490), (384, 497), (389, 510), (394, 524), (399, 537)],
    # the thumb: round its tip, from the hand's outer edge to the web
    [(372, 492), (369, 520), (364, 545), (360, 570), (357, 595), (354, 618), (350, 641), (342, 660),
     (333, 678), (325, 695), (317, 712)],  # the outer edge of thumb and hand, across the crack, to the wrist
    [(426, 502), (416, 516), (409, 526), (403, 535), (399, 537)],  # the web's other side
    [(399, 538), (392, 549), (386, 561), (380, 575), (372, 591), (363, 606), (355, 618)],  # the hand's back
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
     (472, 616), (469, 627), (463, 635), (457, 639), (452, 636), (449, 628), (448, 618), (450, 608),
     (451, 600)],  # third finger, round its tip and up its inner edge to the crease
    [(422, 598), (435, 598), (448, 600)], [(424, 601), (433, 606), (442, 612)],  # a crease
    [(412, 621), (424, 617), (437, 618), (444, 624), (448, 633), (451, 643), (454, 655), (457, 666),
     (459, 675), (457, 681), (452, 680), (447, 673), (443, 664), (438, 652), (434, 642), (432, 636)],
    # the little finger: its outer edge, round its tip, and back up its inner edge
    [(443, 664), (439, 672), (435, 683), (431, 699), (422, 714), (413, 729), (405, 743), (399, 752),
     (391, 750), (379, 742), (368, 735), (360, 731)],  # the hand's lower edge, across the crack to his wrist
]
HAND_W = 7  # px, about the median width of his painted lines
# Between the tips of his third and little fingers the black ground shows, as
# the painter left it.
FINGER_GAP = [(459, 641), (472, 641), (464, 650)]
# A crack runs down beside his hand, from the black ground above it, through
# the top of his sleeve, to the long crack below his chest, mended with grey
# plaster. BREAK is John's outline of it (2026-10-02, "The red outline is the
# crack"; "The outlines of the crack need to be gone"; "Draw the lines so as
# to fill in the parts missing due to the crack"). Inside it nothing is
# traced, and nothing is drawn along it: the lines it broke are carried
# across it instead. His hand's lines are drawn across it by hand
# (HAND_LINES, after John's trace), and the folds of his robe that run into it
# from the right are carried on to its far side, where his sleeve begins.
# At its foot, where it meets the long crack below his chest, the same grey
# plaster spreads left of John's outline in a small triangle (same colour and
# grain); it is erased with the crack.
BREAK_FOOT = [(382, 1012), (352, 1046), (337, 1048), (322, 1058), (320, 1066), (322, 1074), (331, 1074),
              (338, 1082), (349, 1078), (354, 1088), (378, 1094), (392, 1090), (390, 1050)]
BREAK_TOP = 480  # px: the top of his sleeve where the crack meets it
BREAK = [(402, 1090), (393, 1088), (390, 1085), (390, 1065), (380, 1020), (380, 991), (374, 981), (374, 944),
         (378, 932), (380, 909), (382, 849), (378, 819), (378, 763), (374, 749), (366, 741), (372, 735),
         (372, 732), (368, 723), (356, 655), (354, 576), (352, 573), (354, 570), (354, 547), (350, 496),
         (348, 469), (340, 444), (349, 428), (356, 431), (354, 451), (356, 476), (362, 497), (368, 531),
         (380, 571), (384, 595), (392, 617), (394, 650), (402, 676), (408, 713), (406, 727), (412, 754),
         (416, 786), (424, 793), (428, 824), (428, 884), (430, 887), (430, 914), (434, 935), (430, 943),
         (426, 969), (426, 995), (422, 1033), (422, 1053), (418, 1063), (406, 1077), (406, 1084)]
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


def carry_across(lines, zone, w, reach=90):
    """Folds that run into zone from the right are carried on across it in a
    straight line, the way their last 30 px run, to its far side. Only long,
    nearly level lines count as folds."""
    sk = morphology.skeletonize(lines & ~zone)
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    near_zone = ndi.binary_dilation(zone, iterations=6)
    ends = sk & (ndi.convolve(sk.astype(int), k, mode="constant") == 1) & near_zone
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    path = np.zeros_like(lines)
    for y, x in zip(*np.nonzero(ends)):
        ys, xs = np.nonzero(lab == lab[y, x])
        if len(ys) < 40:  # a fleck, not a fold
            continue
        near = np.hypot(ys - y, xs - x) <= 30
        ys, xs = ys[near], xs[near]
        if xs.max() - x < 20 or xs.min() < x:  # it must run off to the right of its end
            continue
        b, c = np.polyfit(xs, ys, 1)
        if abs(b) > 0.7:  # too steep for a fold
            continue
        entered = False
        for xx in range(x - 1, x - reach, -1):
            yy = int(round(b * xx + c))
            if not (0 <= yy < lines.shape[0]):
                break
            if zone[yy, xx]:
                entered = True
            elif entered:  # out the far side
                break
            path[yy, xx] = True
    return ndi.distance_transform_edt(~path) <= w / 2


def join_gaps(lines, keep_out, max_gap=40, max_turn=32.0, max_bend=50.0, min_len=12):
    """Lines broken by wear joined across their gaps: two line ends are joined
    by a smooth curve when they are at most max_gap px apart, each points at
    the other within max_turn degrees, the two lines run the same way within
    max_bend degrees, both run at least min_len px, and the curve crosses no
    other line and stays out of keep_out (the cracks). Returns the curves."""
    from scipy.spatial import cKDTree
    sk, k = centre_lines(lines, spur=5, min_len=min_len)
    dist = ndi.distance_transform_edt(lines)
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    ends = np.argwhere(sk & (ndi.convolve(sk.astype(int), k, mode="constant") == 1))
    if len(ends) < 2:
        return np.zeros_like(lines)
    heads, widths = [], []
    for y, x in ends:  # each end's outward direction, from the last 12 px of its line
        path, seen, cur = [(y, x)], {(y, x)}, (y, x)
        for _ in range(12):
            nxt = [(cur[0] + dy, cur[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= cur[0] + dy < sk.shape[0] and 0 <= cur[1] + dx < sk.shape[1]
                   and sk[cur[0] + dy, cur[1] + dx] and (cur[0] + dy, cur[1] + dx) not in seen]
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
            path.append(cur)
        P = np.array(path, float)
        d = P[0] - P[len(P) // 2:].mean(0) if len(P) >= 6 else np.zeros(2)
        n = np.hypot(*d)
        heads.append(d / n if n else d)
        widths.append(2 * max(dist[int(py), int(px)] for py, px in path[2:8]) if len(path) > 2 else 4)
    heads = np.array(heads)
    cos_max, cos_bend = np.cos(np.radians(max_turn)), np.cos(np.radians(max_bend))
    pairs = []
    for i, j in cKDTree(ends).query_pairs(max_gap):
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
        v = (ends[j] - ends[i]).astype(float)
        g = np.hypot(*v)
        if g < 2:
            continue
        v /= g
        a, b = heads[i] @ v, heads[j] @ -v
        if a >= cos_max and b >= cos_max and heads[i] @ -heads[j] >= cos_bend:
            pairs.append((g * (3 - a - b), i, j, g))
    out = np.zeros_like(lines)
    used = set()
    for _, i, j, g in sorted(pairs):
        if i in used or j in used:
            continue
        p0, p3 = ends[i].astype(float), ends[j].astype(float)
        p1, p2 = p0 + heads[i] * g / 3, p3 + heads[j] * g / 3
        tt = np.linspace(0, 1, int(g * 2) + 2)[:, None]
        curve = (1 - tt) ** 3 * p0 + 3 * (1 - tt) ** 2 * tt * p1 + 3 * (1 - tt) * tt ** 2 * p2 + tt ** 3 * p3
        cy = np.clip(np.round(curve[:, 0]).astype(int), 0, lines.shape[0] - 1)
        cx = np.clip(np.round(curve[:, 1]).astype(int), 0, lines.shape[1] - 1)
        # the curve may touch ink only near its two ends, inside the lines it joins
        off = (np.hypot(*(curve - p0).T) > widths[i] / 2 + 2) & (np.hypot(*(curve - p3).T) > widths[j] / 2 + 2)
        if lines[cy[off], cx[off]].any() or keep_out[cy, cx].any():
            continue
        used |= {i, j}
        r = max(1.5, min(5.0, (widths[i] + widths[j]) / 4))
        m = np.zeros_like(lines)
        m[cy, cx] = True
        out |= ndi.distance_transform_edt(~m) <= r
    return out


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
    brk = poly(shape, BREAK) | poly(shape, BREAK_FOOT)
    above = np.arange(shape[0])[:, None] < BREAK_TOP  # the crack in the black ground, above his sleeve
    sil = (((sil | brk) & ~(brk & above)) & ~beside) | rod  # the gap beside the staff stays open
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
    brk_rim = ndi.binary_dilation(brk, iterations=3)  # the plaster's grey bleeds past the outline
    carried = carry_across(lines & ~hand_zone, brk_rim, HAND_W)
    lines = morphology.remove_small_objects(lines & ~brk_rim, max_size=120)  # bits the erasing cut off
    joins = join_gaps(lines & ~head, cracks | brk_rim)  # lines broken by wear, joined across their gaps
    if "--joins" in sys.argv:
        np.save(sys.argv[-1], joins)
    lines |= joins
    lines |= carried | drawn(shape, HAND_LINES, HAND_W) | poly(shape, FINGER_GAP)
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
