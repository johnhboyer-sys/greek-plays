"""Libation Bearers: Orestes killing Aegisthus, with Clytemnestra and Electra, the whole frieze of
Gerhard, Etruskische und kampanische Vasenbilder des Königlichen Museums zu Berlin (Berlin, 1843),
Taf. XXIV, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843%3AT_24.jpg/full/full/0/default.jpg
(3510 x 2590; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843/0071)
Clytemnestra comes up at the left with an axe; Orestes, in helmet and cuirass, holds Aegisthus by
the head and stabs him in the chest; Aegisthus sits on a throne, his feet on a footstool; Electra
stands at the right.

The scan is a photo of the open book, and the plate's frame bends a little: its bottom edge sags
9 px in the middle, its top edge rises 3 px, and its sides lean out (0.5 degrees each way). So the
scan is levelled first (level): the frame's four edges are measured, the top and bottom fitted with
cubics and the sides with straight lines, and a Coons patch maps them onto a rectangle; points in
between move smoothly with them, by up to 10 px. The edges then run straight within 1 px. Every
point below is in the levelled scan.

Plate -> drawing, as for Suppliant Women (tools/suppliants_aesch.py): the plate prints the black
ground black, so the figures' outline comes free.
  - The tongue band along the top and the meander along the bottom are cut off along their edges
    (BAND_Y, BOTTOM). The axe head reaches up into the tongue band and is kept whole: inside the
    band, the figure is what lies within the axe head's own outline (AXE).
  - Ground: the dark of the plate, its thin lines opened away; the large areas, found where they are
    at least 2 x CORE plate px wide, and the pockets of ground the figures close in (POCKETS). Where
    the ground narrows (between fingers, in a wedge between two limbs) it is ground still, and so is
    the strip under the feet, between their soles and the meander. Black lines and locks of hair
    that run into the ground through a narrow neck are paint, not ground (LINES, a point on each):
    found as ground, they cut notches into the figures.
  - The scene is the clay area the ground leaves, from SEEDS: the four figures, the throne and the
    footstool, joined (Clytemnestra's hem lies under Orestes' rear foot, his arms lock with
    Aegisthus') but for Electra. The names painted on the ground join no figure and drop out.
  - Lines: the plate's dark lines inside the figures (local contrast), the faint ones in the blue
    channel (FAINT), breaks in the print joined (JOIN_*); the outline; and the plate's solid paint.
    The faces (FACES), Electra's ringlets (RINGLETS), Aegisthus' genitals (CURLS) and Orestes' rear
    big toe (HANDS) are the plate's paint at its own width, so eyes and curls stay fine (John,
    2026-10-07: "not too heavy of a line on fine details like eyes").
  - The blood on Aegisthus' chest is a wash in the line colour, the lines black through it (BLOOD).
  - Line weight: the plate's own (WEIGHT), not the house weight, which on a drawing this wide runs
    close lines together (LESSONS.md, the Élite plates).
  - John's corrections on pass 1 (MARKS): black ink where he marked it blue, none where green.
  - Dark theme: the figures' area is the body; all the ground stays open, as on the vase. The
    outline is capped at 0.6 of a thin part's half-width, so thin parts keep their clay (as in
    tools/alcestis.py), but never thinner than EDGE_MIN; and where hair or a black border meets the
    ground across the thin clay line the plate prints, that line is kept as a clay rim (RIM_*).

    python3 docs/redesign/drawings/tools/libation_bearers.py 06n_gerhard1843_T24.jpg [qa_stem]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "libation-bearers.svg"
# John's corrections on pass 1 (2026-10-07), drawn over it: 'blue lines and fill are where there should
# be black ink. green lines and fill are where you should remove black ink.' Rings in plate px
# (add: his blue; remove: his green), filled even-odd
MARKS = Path(__file__).with_name('libation_bearers_marks.json')

# ---------------------------------------------------------------- levelling (scan px)
EDGE_T = 140                    # the frame's edges: where the grey crosses this, paper to print
TOP_ROWS, BOTTOM_ROWS = (425, 480), (1820, 1858)     # where each edge is looked for (scan rows)
LEFT_COLS, RIGHT_COLS = (440, 560), (2900, 2990)
EDGE_X, EDGE_Y = (505, 2930), (470, 1840)            # the stretch of each edge measured
MARGIN = 80                     # levelled this far outside the frame (px)

# ---------------------------------------------------------------- drawing (levelled px)
X0, Y0, X1, Y1 = 600, 466, 2938, 1716   # crop
UP = 3                                  # work at 3x, so curves stay smooth
DARK = 85                               # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                     # plate px: dark areas this large are ground
CORE = 5                                # plate px: the ground's large areas are found where they are 2 x CORE wide
BAND_Y = 500                            # the tongue band's lower edge (its tongues end above 497)
# the meander's top edge, 2 px above it (measured every 200 px)
BOTTOM = [(600, 1714), (700, 1714), (900, 1712.5), (1100, 1713), (1300, 1712), (1500, 1713),
          (1700, 1713), (1900, 1713), (2100, 1713), (2300, 1714), (2500, 1714), (2700, 1714),
          (2940, 1714)]
# the axe head's outline inside the tongue band, from its left side at the band's edge round its top
# to its right side (followed along the plate's dark line through these points)
AXE = [(854.4, 504.2), (851.7, 498.7), (847.2, 492), (841.7, 484.2), (836.1, 477), (846.1, 473.7),
       (857.2, 472.6), (868.3, 472.6), (879.4, 473.1), (890.6, 474.8), (904.4, 478.4), (897.2, 482.6),
       (892.8, 488.7), (889.4, 495.3), (886.7, 502)]
SEEDS = [(971, 1123), (1035, 768), (1475, 1207), (1584, 1340), (1760, 1196), (1762, 1448), (1765, 1650),
         (2617, 1319), (2301, 676)]
# pockets of ground the figures close in, smaller than AUTO_GROUND (a point in each): between
# Clytemnestra's face and her raised arm; between Electra's raised arm and her head; between Orestes'
# sword arm and Aegisthus; between Clytemnestra's feet, under her hem; between Orestes' rear foot and
# her front foot; between Electra's hem and her rear leg; the strip under Orestes' front heel, between
# his sole, the footstool and the meander
POCKETS = [(1224, 612), (2680, 594), (1929, 989), (873, 1690), (1094, 1690), (2830, 1655), (1590, 1709)]
# black lines and hair that run into the ground through a narrow neck (a point on each): the wavy
# lower border of Electra's himation; the dark between the leaves of Aegisthus' wreath; the
# himation's edge from Electra's shoulder; the black border of Aegisthus' drape over his shoulder;
# Orestes' hair down his back; the drape's hem border below Aegisthus' thigh; Orestes' jaw line at
# the throat; the knot of Aegisthus' hair at his nape; the lower end of Electra's zigzag band; the
# palmettes on the throne's two legs; the end of a pleat on Clytemnestra's sleeve; Aegisthus'
# fringe; the zigzag band on Clytemnestra's skirt
LINES = [(2672, 1147), (2040, 734), (2520, 715), (2222, 797), (1455, 720), (1655, 1478), (1608, 676),
         (2146, 761), (2413, 1510), (2250, 1550), (1799, 1542), (1074, 651), (1985, 776), (1207, 1273)]
# Hair that runs into the ground where the plate prints no reserved line: a cut (WALL_W plate px wide)
# closes it from the ground. Aegisthus' hair below his wreath, from the wreath's end to the top of
# the curls over his forehead; Electra's hair between the second and third leaves of her wreath,
# from the second leaf's tip to the reserved line's end (John, 2026-10-07: "forgot about this part
# of his head")
WALLS = [[(1951, 753), (1957, 760), (1963, 767)], [(2553.5, 513.6), (2558.5, 514), (2563.5, 514.6)]]
WALL_W = 1.5
# the faces, boxes: their lines are the plate's paint darker than FACE_DARK, at its own width
# (Clytemnestra with her curls, Orestes with the locks on his cheek, Aegisthus, the curls over his
# forehead, Electra with the ringlets over her brow): the curls are fine lines a px or two apart,
# and the ringlets small clay rings on the black hair, which the line finder runs together
FACES = [(1112, 535, 1216, 652), (1550, 588, 1642, 690), (1995, 768, 2062, 832), (1955, 765, 2000, 803),
         (2495, 518, 2600, 640)]
FACE_DARK = 110
# and the paler lines in them (the lower lids, the irises, Clytemnestra's whole eye), each at its
# own width: where the plate is darker than halfway between the line's core and the clay round it
# (half_max; LINE_W plate px across, lines LINE_DEPTH grey levels deep). Without them the eyes came
# out as a dash, Clytemnestra's not at all; found by local contrast instead, they came out heavier
# than printed
LINE_W, LINE_CORE, LINE_DEPTH = 5, 3, 40
# Electra's ringlets: clay rings a px wide round a dark dot, on her black hair, and her fillet's
# bands. Here (boxes, kept clear of her brow) the clay lines are found by the same rule turned over
# (lighter than halfway between their core, RING_CORE plate px across, and the black round them),
# and all else darker than RING_DARK is paint; the dots, under potrace's speck size, are traced as dots
RINGLETS = [(2478, 512, 2600, 558), (2548, 558, 2598, 598)]
RING_CORE, RING_DARK = 2, 150
# Aegisthus' genitals, drawn as printed (John, 2026-10-05): a row of small curls of hair, strokes 2
# plate px wide a px apart, above a thin outline. Here the lines are the paint at its own width by
# half_max alone, over a narrower window (CURLS_W, CURLS_CORE plate px): with the faces' threshold the
# curls ran into one dark patch
CURLS = [(1958, 1144, 1992, 1198)]
CURLS_W, CURLS_CORE = 3, 1
# toes too fine for the outline's width: Orestes' rear big toe, whose nail is a sliver of clay between
# the toe's line and the ground, which the outline covered. Here the outline is HAND_EDGE plate px
# wide, and the lines are the paint at its own width, as in the faces
HANDS = [(1240, 1680, 1305, 1716)]
HAND_EDGE = 1.2
# The plate's own line weight, as pass 1 measured it (weight "own": 0.116% of the longer side before
# evening, lines 2.4 plate px across at the median). Measured again now, it would count John's traced
# strokes, which are wider, and every line came out heavier (3.0 px at the median)
WEIGHT = 0.00109
# The outline is at least EDGE_MIN plate px wide: where a notch in the edge (a line meeting it) put out
# a spur of the figure's skeleton, the cap thinned the outline beside it until it broke up in tracing
# (John, 2026-10-07: "one more line i missed", the edge of Aegisthus' drape at his shoulder)
EDGE_MIN = 1.0
# Where hair or a black border meets the ground, the plate prints a thin clay line between them,
# which the outline covers: on the dark theme the outline there gets a clay rim. Only along a thin
# light line (half_max over RIM_W plate px, core RIM_CORE) at least RIM_LEN plate px long, with paint
# on one side and ground on the other within RIM_NEAR px: not round the leaves of Electra's wreath,
# and not where paint runs straight into the ground (the ends of her zigzag bands)
RIM_W, RIM_CORE, RIM_LEN, RIM_NEAR = 3, 1, 8, 2
# The dark brown between Aegisthus' jaw and his shoulder, round the locks of his beard, is the black
# ground, printed lighter there (John, 2026-10-07: "the blob here of clay is not part his body"): the
# bare clay (no ink) there, the parts of it that the plate prints darker than OPEN_T on average, is
# left open on the dark theme, as ground. OPEN: a ring round it; the locks inside keep their clay
OPEN = [(2014, 818), (2054, 818), (2054, 840), (2014, 840)]
OPEN_T = 120
# The faint lines (the anatomy of arms, legs and chests, in thinned glaze) print pale brown: in grey
# they are 15-20 levels darker than the clay, under the line finder's thresholds, but in the blue
# channel 30-55 (the clay is orange). There they are found by local contrast (FAINT, hysteresis low
# and high); a piece away from the lines found in grey is kept if it is a line (its centre line
# FAINT_LEN plate px long, its mean width under FAINT_W) lying apart from them (its median distance
# from them FAINT_OFF plate px or more: a sliver along a black line is that line's own fringe), and
# is joined back to the lines it runs into
FAINT, FAINT_LEN, FAINT_W, FAINT_OFF = (18, 32), 8, 5, 3
# Breaks in the thin lines where the print fades (pleats above all): line ends that face each other
# across a gap of at most JOIN_MAX plate px (the last JOIN_RUN plate px of each end's centre line
# point at the other end, within JOIN_ANGLE degrees) are joined straight, at the lines' width, where
# the plate prints a line all across the gap: its local contrast in the blue channel is JOIN_C or
# more along the gap's middle 70%. Across the breaks it ran 7-40 (7-12 where the print fades most);
# between true ends (a palmette's petals, two toes) 0-6
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C = 10, 6, 30, 7
# Blood runs down Aegisthus' chest from the wound, printed in a lighter red-brown than the lines.
# Inside BLOOD (a ring round it), the blood is the plate darker than BLOOD_T[0], and the paler
# plate joined to it down to BLOOD_T[1] (the streaks' tapering tails), but the black lines (darker
# than BLACK_T: the sword's edges, which end at the blood). The line across his chest runs through
# the blood: it is drawn black through it along its own dark ridge (BLOOD_LINES), BLOOD_LINE_W plate
# px wide, as on the plate. The blood is drawn as LESSONS.md says (Blood): a wash in the line
# colour whose opacity follows the plate's darkness under it, smoothed over BLEND_SIGMA plate px,
# from BLEND_A[0] where the plate is BLEND_T[0] to BLEND_A[1] where it is BLEND_T[1], in steps of
# BLEND_STEP, as tools/andromache.py draws it (John, 2026-10-06)
BLOOD = [(2024, 931), (2030, 926), (2045, 926), (2052, 929), (2062, 934), (2072, 937), (2077, 950),
         (2077, 960), (2074, 990), (2068, 1030), (2062, 1070), (2058, 1108), (2050, 1110), (2040, 1125),
         (2030, 1150), (2024, 1158), (2018, 1152), (2022, 1120), (2030, 1080), (2040, 1040), (2047, 1005),
         (2050, 978), (2052, 962), (2045, 945), (2032, 942), (2024, 938)]
BLOOD_T, BLACK_T = (135, 145), 82
BLOOD_LINES = [[(2044, 976.5), (2060, 976), (2075, 974.5), (2090, 973)]]
BLOOD_LINE_W = 2.0
BLEND_T, BLEND_A, BLEND_STEP, BLEND_SIGMA = (140, 85), (0.25, 0.55), 0.05, 2


def level(img):
    """The scan levelled (see the docstring): the frame's edges straight, the frame a rectangle."""
    g = ndi.gaussian_filter(np.asarray(Image.fromarray(img).convert('L'), np.float32), 0.8)

    def cross(p, start, step=1):    # first index where p falls below EDGE_T, sub-pixel
        i = np.where(p < EDGE_T)[0]
        if not len(i) or i[0] == 0:
            return np.nan
        i = i[0]
        return start + step * ((i - 1) + (p[i - 1] - EDGE_T) / (p[i - 1] - p[i]))

    xs = np.arange(*EDGE_X, 5.0)
    ys = np.arange(*EDGE_Y, 5.0)
    top = np.array([cross(g[TOP_ROWS[0]:TOP_ROWS[1], int(x)], TOP_ROWS[0]) for x in xs])
    bot = np.array([cross(g[BOTTOM_ROWS[1]:BOTTOM_ROWS[0]:-1, int(x)], BOTTOM_ROWS[1], -1) for x in xs])
    left = np.array([cross(g[int(y), LEFT_COLS[0]:LEFT_COLS[1]], LEFT_COLS[0]) for y in ys])
    right = np.array([cross(g[int(y), RIGHT_COLS[1]:RIGHT_COLS[0]:-1], RIGHT_COLS[1], -1) for y in ys])

    def fit(t, e, deg):             # least squares, dropping points 2.5 robust sigmas off
        ok = ~np.isnan(e)
        for _ in range(5):
            p = np.polyfit(t[ok], e[ok], deg)
            r = e - np.polyval(p, t)
            s = 1.4826 * np.nanmedian(np.abs(r[ok]))
            ok = ~np.isnan(e) & (np.abs(r) <= 2.5 * max(s, 0.5))
        return p

    pt, pb, pl, pr = fit(xs, top, 3), fit(xs, bot, 3), fit(ys, left, 1), fit(ys, right, 1)

    def corner(ph, pv):
        y = np.polyval(ph, 1000.0)
        for _ in range(20):
            x = np.polyval(pv, y)
            y = np.polyval(ph, x)
        return np.array([x, y])

    TL, TR, BL, BR = corner(pt, pl), corner(pt, pr), corner(pb, pl), corner(pb, pr)
    XL, XR = (TL[0] + BL[0]) / 2, (TR[0] + BR[0]) / 2
    YT, YB = (TL[1] + TR[1]) / 2, (BL[1] + BR[1]) / 2
    x0, x1, y0, y1 = int(XL) - MARGIN, int(XR) + MARGIN, int(YT) - MARGIN, int(YB) + MARGIN
    Y, X = np.mgrid[y0:y1, x0:x1].astype(float)
    u, v = (X - XL) / (XR - XL), (Y - YT) / (YB - YT)
    xt = TL[0] + u * (TR[0] - TL[0])
    xb = BL[0] + u * (BR[0] - BL[0])
    yl = TL[1] + v * (BL[1] - TL[1])
    yr = TR[1] + v * (BR[1] - TR[1])
    corners = (1 - u) * (1 - v) * np.array(TL)[:, None, None] + u * (1 - v) * np.array(TR)[:, None, None] + \
        (1 - u) * v * np.array(BL)[:, None, None] + u * v * np.array(BR)[:, None, None]
    sx = (1 - v) * xt + v * xb + (1 - u) * np.polyval(pl, yl) + u * np.polyval(pr, yr) - corners[0]
    sy = (1 - v) * np.polyval(pt, xt) + v * np.polyval(pb, xb) + (1 - u) * yl + u * yr - corners[1]
    out = img.copy()
    for c in range(3):
        out[y0:y1, x0:x1, c] = np.clip(ndi.map_coordinates(img[..., c].astype(np.float32), [sy, sx], order=3,
                                                           mode='nearest'), 0, 255).astype(np.uint8)
    return out


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def at(x, y):
    return int(round((y - Y0) * UP)), int(round((x - X0) * UP))


def rings_mask(shape, rings):
    """Rings (plate px) filled even-odd, at UP."""
    m = np.zeros(shape, bool)
    for ring in rings:
        P = up(ring)
        x0, y0 = max(int(P[:, 0].min()) - 1, 0), max(int(P[:, 1].min()) - 1, 0)
        x1, y1 = min(int(P[:, 0].max()) + 2, shape[1]), min(int(P[:, 1].max()) + 2, shape[0])
        if x1 > x0 and y1 > y0:
            m[y0:y1, x0:x1] ^= lw.polygon_mask((y1 - y0, x1 - x0), P - (x0, y0))
    return m


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


def dark_path(g, pts):
    """A least-cost path along a thin dark line's ridge, through hand-placed points (plate px);
    (x, y) at UP."""
    P = up(pts)
    pad = 10 * UP
    x0, y0 = max(int(P[:, 0].min()) - pad, 0), max(int(P[:, 1].min()) - pad, 0)
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.5 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    return lw.livewire(cost, [(x - x0, y - y0) for x, y in P]) + (x0, y0)


def half_max(gf, size, core, depth, light=False):
    """Thin lines at their own width: the px darker (light: lighter) than halfway between the line's
    core (the extreme within `core` plate px) and the ground round it (the grey closing, light:
    opening, over `size` plate px), where the line is at least `depth` grey levels deep."""
    if light:
        gf = 255 - gf
    bg = ndi.grey_closing(gf, size=(size * UP, size * UP))
    d = bg - ndi.grey_erosion(gf, size=(core * UP, core * UP))
    return ((bg - gf) > 0.5 * d) & (d > depth)


def faint_stretches(firm, loose):
    """The faint stretches of the plate's thin lines (as in suppliants_aesch.py): a stretch standing
    alone must be line-shaped; a short one, or a piece of the looser lines' centre line between
    firm lines, must bridge two firm lines and run along at least one."""
    def axis(p):
        if len(p) < 3:
            return np.zeros(2), 0.0
        w, vv = np.linalg.eigh(np.cov(p.T.astype(float)))
        return vv[:, 1], float(np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)))

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
            meets = [np.argwhere(reach & (fl == f)).mean(0) for f in touched]
            runs = [axis(np.argwhere(near & (fl == f)))[0] for f in touched]
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


def join_breaks(lines, contrast):
    """The breaks in `lines` (at UP) that JOIN_* describe, joined; `contrast` is the plate's local
    contrast (UP px)."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    dt = ndi.distance_transform_edt(lines)
    H, W = sk.shape

    def run_back(p):   # the end's last JOIN_RUN plate px of centre line, from the end inward
        path, seen = [tuple(p)], {tuple(p)}
        for _ in range(JOIN_RUN * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]
                   and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        return np.array(path, float)

    runs = [run_back(p) for p in ends]
    out = np.zeros_like(lines)
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX * UP),
                   key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or len(runs[i]) < JOIN_RUN * UP / 2 or len(runs[j]) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        t = np.linspace(0.15, 0.85, max(int(np.hypot(*(b - a))), 3))
        q = a[None] + t[:, None] * (b - a)[None]
        if ndi.map_coordinates(contrast, q.T, order=1).min() < JOIN_C:
            continue
        w = np.median([dt[tuple(r.astype(int))] for r in np.vstack([runs[i], runs[j]])]) * 2 / UP
        seg = np.linspace(a - 1.5 * u, b + 1.5 * u, int(np.hypot(*(b - a))) + 4)[:, ::-1] + 0.5
        out |= along(lines.shape, seg, max(w, 2.0))
        used |= {i, j}
    return out


def add_tone(svg, blood, tone, box):
    """Add the blood to the drawing written by lw.trace_svg (box: the crop box it returned), as
    tools/andromache.py's add_tone does: a wash in the line colour whose opacity follows the plate's
    darkness under it (BLEND_*), in steps, each step's area drawn over the one below at the opacity
    that brings the total there to the step's: paths of class "tone", between the body and the
    lines. Each step is resampled as trace_svg resamples the lines (to WORK_H, then TRACE_H) and
    traced at that size, so the wash stays in register with them."""
    x0, y0, x1, y1 = box
    b, g, s = blood[y0:y1, x0:x1], tone[y0:y1, x0:x1], BLEND_SIGMA * UP
    dark = ndi.gaussian_filter(np.where(b, g, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (t0, t1), (a0, a1) = BLEND_T, BLEND_A
    alpha = a0 + (a1 - a0) * np.clip((t0 - dark) / (t0 - t1), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, BLEND_STEP):
        m = b & (alpha >= a - BLEND_STEP / 2)
        if not m.any():
            break
        m = lw.resample_ink(lw.resample_ink(m, lw.WORK_H), lw.TRACE_H)
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def main(src, qa=None):
    lev = level(np.asarray(Image.open(src).convert('RGB')))
    if qa:
        Image.fromarray(lev).save(f'{qa}_levelled.png')
    plate = Image.fromarray(lev).crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    blue = np.asarray(plate, np.float32)[..., 2]
    g = np.asarray(plate.convert('L'), np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside: the tongue band (but the axe head inside its outline) and the meander
    bottom = up(BOTTOM)
    outside = yy >= np.interp(xx, bottom[:, 0], bottom[:, 1])
    axe = lw.polygon_mask(g.shape, dark_path(g, AXE))
    outside |= (yy < (BAND_Y - Y0) * UP) & ~axe

    # ground: dark, thin lines opened away. The large areas are found where the ground is 2 x CORE
    # wide; the dark that joins them where it narrows is ground too, but the lines in LINES
    dark = ndi.binary_opening(gs < DARK, structure=morphology.disk(2 * UP)) & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    thick =ndi.binary_opening(dark, structure=morphology.disk(CORE * UP))
    lab, _ = ndi.label(thick)
    size = np.bincount(lab.ravel())
    size[0] = 0
    core = size > AUTO_GROUND * UP * UP
    cores = core[lab]
    dlab, _ = ndi.label(dark)
    for x, y in POCKETS:
        k = lab[at(x, y)]
        cores |= (lab == k) if k else (dlab == dlab[at(x, y)])
        assert k or dlab[at(x, y)], f'pocket point {(x, y)} is not on dark'
    near = ndi.binary_dilation(thick, iterations=UP)
    tlab, tn = ndi.label(dark & ~near)
    joins = np.zeros(tn + 1, bool)
    joins[np.unique(tlab[ndi.binary_dilation(cores, iterations=UP + 1)])] = True
    joins[0] = False
    for x, y in LINES:   # the narrow dark part nearest the point, within 3 plate px
        (r, c), d = at(x, y), 3 * UP
        win = tlab[r - d:r + d + 1, c - d:c + d + 1]
        assert win.any(), f'line point {(x, y)} is not near a narrow dark part'
        yx = np.argwhere(win)
        joins[win[tuple(yx[np.argmin(((yx - d) ** 2).sum(1))])]] = False
    ground = (dark & ndi.binary_dilation(cores, iterations=UP)) | joins[tlab]
    # and the dark between the soles and the meander, however small: the strip of ground the feet
    # stand on (under Electra's arch, between toes and the cut it is closed off, and was taken for paint)
    lab, _ = ndi.label(dark & ~ground)
    foot = yy >= np.interp(xx, bottom[:, 0], bottom[:, 1]) - 3 * UP
    ground |= np.isin(lab, np.setdiff1d(np.unique(lab[foot]), [0]))
    paint = dark & ~ground

    # the scene: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[at(x, y)] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground   # paint stays theirs; pockets of ground do not
    lab, _ = ndi.label(fig)                      # nor the names on the ground they close in
    fig = np.isin(lab, list({lab[at(x, y)] for x, y in SEEDS}))
    # smooth the edge, but keep thin clay on the ground: light ridges narrower than 5 plate px
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # lines: the plate's dark lines inside the figures, the outline, and the solid paint; a looser
    # threshold finds the faint stretches of the thin lines. Every line is then at least 2 plate px
    # wide, or the thin ones break up when the line weight is evened out
    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    dilute = lw.ink_lines(blue, size=9 * UP, low=FAINT[0], high=FAINT[1], sigma=0.8 * UP) & fig
    lab, n = ndi.label(dilute & ~ndi.binary_dilation(lines, iterations=2 * UP), structure=np.ones((3, 3)))
    length = np.bincount(lab[morphology.skeletonize(lab > 0)], minlength=n + 1)
    area = np.bincount(lab.ravel(), minlength=n + 1)
    off = ndi.distance_transform_edt(~lines)
    keep = (length >= FAINT_LEN * UP) & (area <= FAINT_W * UP * np.maximum(length, 1))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        keep[k] &= np.median(off[sl][lab[sl] == k]) >= FAINT_OFF * UP
    keep[0] = False
    lines |= dilute & ndi.binary_dilation(keep[lab], iterations=2 * UP + 2)
    del off
    # the blood: inside its ring, the plate darker than BLOOD_T[0] and the paler plate joined to it,
    # but the black lines; the line finder took its streaks for lines, and they go. The line across
    # his chest is drawn through it
    gb = ndi.gaussian_filter(g, 0.75 * UP)
    ring = lw.polygon_mask(g.shape, up(BLOOD)) & fig
    across = [along(g.shape, dark_path(g, pts), BLOOD_LINE_W) for pts in BLOOD_LINES]
    black = ndi.binary_dilation(ring & (gb < BLACK_T), iterations=round(1.5 * UP))
    for a in across:
        black &= ~ndi.binary_dilation(a, iterations=2 * UP)
    pale = ring & (gb < BLOOD_T[1]) & ~black
    blood = ndi.binary_propagation(pale & (gb < BLOOD_T[0]), mask=pale)
    lab, _ = ndi.label(blood)
    blood &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]
    lines &= ~(ndi.binary_dilation(blood, iterations=UP) & ~black)
    for a in across:
        lines |= a & fig
    sb = ndi.gaussian_filter(blue, 0.8 * UP)
    lines |= join_breaks(lines, ndi.grey_closing(sb, size=(9 * UP, 9 * UP)) - sb) & fig
    del sb
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    face = np.zeros_like(fig)
    for fx0, fy0, fx1, fy1 in FACES:
        (a, b), (c, d) = at(fx0, fy0), at(fx1, fy1)
        face[a:c, b:d] = True
    hand = np.zeros_like(fig)
    for hx0, hy0, hx1, hy1 in HANDS:
        (a, b), (c, d) = at(hx0, hy0), at(hx1, hy1)
        hand[a:c, b:d] = True
    face |= hand
    gf = ndi.gaussian_filter(g, 0.5 * UP)
    lines = np.where(face, ((gf < FACE_DARK) | half_max(gf, LINE_W, LINE_CORE, LINE_DEPTH)) & fig, lines)
    for cx0, cy0, cx1, cy1 in CURLS:
        (a, b), (c, d) = at(cx0, cy0), at(cx1, cy1)
        face[a:c, b:d] = True
        lines[a:c, b:d] = half_max(gf, CURLS_W, CURLS_CORE, LINE_DEPTH)[a:c, b:d] & fig[a:c, b:d]
    rings = np.zeros_like(fig)
    for fx0, fy0, fx1, fy1 in RINGLETS:
        (a, b), (c, d) = at(fx0, fy0), at(fx1, fy1)
        face[a:c, b:d] = rings[a:c, b:d] = True
    clay = half_max(gf, LINE_W, RING_CORE, LINE_DEPTH, light=True)
    lines = np.where(rings, (gf < RING_DARK) & ~clay & fig, lines)
    solid = paint & fig & ~rings
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the outline: 2.5 plate px in from the clay's edge, but no more than 0.6 of the figure's
    # half-width there, so thin parts keep clay inside their outline on the dark theme; at least EDGE_MIN
    dt = ndi.distance_transform_edt(fig)
    _, (iy, ix) = ndi.distance_transform_edt(~morphology.skeletonize(fig), return_indices=True)
    edge = fig & (dt <= np.maximum(np.minimum(2.5 * UP, 0.6 * dt[iy, ix]), EDGE_MIN * UP))
    edge = np.where(hand, fig & (dt <= HAND_EDGE * UP), edge)
    del dt, iy, ix
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    size = np.bincount(lab.ravel())
    dots = ink & rings & ((size > UP * UP) & (size < 12 * UP * UP))[lab]   # the ringlets' dots, 1-12 px^2
    ink &= np.where(face, (size > 3 * UP * UP)[lab], (size > 12 * UP * UP)[lab])
    ink |= dots
    # John's corrections: black ink where he marked it blue, none where he marked it green
    marks = json.loads(MARKS.read_text())
    ink = (ink | rings_mask(ink.shape, marks['add'])) & ~rings_mask(ink.shape, marks['remove'])

    # all the ground stays open on the dark theme. Where the plate prints a thin clay line between
    # paint (hair, a black border) and the ground, the outline covers it, and the paint would run into
    # the ground on the dark theme: the outline there gets a clay rim, as hair does in
    # suppliants_aesch.py (RIM_*)
    held = ground & ~fig
    ridge = half_max(gf, RIM_W, RIM_CORE, LINE_DEPTH, light=True) & fig
    lab, n = ndi.label(ridge, structure=np.ones((3, 3)))
    ridge &= (np.bincount(lab[morphology.skeletonize(ridge)], minlength=n + 1) >= RIM_LEN * UP)[lab]
    ds, (sy, sx) = ndi.distance_transform_edt(~(solid | (lines & rings)), return_indices=True)
    dh, (hy, hx) = ndi.distance_transform_edt(~held, return_indices=True)
    yy, xx = np.mgrid[0:fig.shape[0], 0:fig.shape[1]]
    across = (sy - yy) * (hy - yy) + (sx - xx) * (hx - xx) < -0.5 * ds * dh   # paint and ground on opposite sides
    rims = ndi.binary_dilation(ridge & (ds <= RIM_NEAR * UP) & (dh <= RIM_NEAR * UP) & across, iterations=3 * UP)
    del ds, dh, sy, sx, hy, hx, yy, xx, across
    lab, n = ndi.label(fig & ~ink)
    mean = np.bincount(lab.ravel(), weights=gs.ravel(), minlength=n + 1) / np.maximum(np.bincount(lab.ravel(), minlength=n + 1), 1)
    near = np.unique(lab[lw.polygon_mask(fig.shape, up(OPEN)) & (lab > 0)])
    held |= np.isin(lab, near[mean[near] < OPEN_T])
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, rim_lines=rims, dots=dots, weight=WEIGHT,
        title='Orestes killing Aegisthus, with Clytemnestra and Electra',
        desc='Line drawing after the 1843 plate of a red-figure stamnos by the Copenhagen Painter, formerly Berlin '
             'F 2184, now Moscow, Pushkin Museum (Gerhard, Etruskische und kampanische Vasenbilder, Taf. XXIV); cut '
             'out and retraced.')
    add_tone(OUT, blood, gb, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(f'{qa}.png'))
        lw.qa_dark(OUT, info['box'], Path(f'{qa}.dark.png'))
    return info


if __name__ == '__main__':
    main(*sys.argv[1:3])
