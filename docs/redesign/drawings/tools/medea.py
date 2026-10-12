"""Medea: the lower band of the Munich Medea krater, from Karl Reichhold's drawing in Furtwängler and Reichhold,
Griechische Vasenmalerei II (Munich, 1906), Taf. 90 ("Die Medea-Vase in München"; text pp. 161-166): a servant leads
one son away by the hair; Medea, in a Phrygian cap, seizes the other, who has fled to an altar, and draws her sword;
in the middle, the serpent chariot that waits for her, driven by Oistros (the text: a demon of frenzy, from a later
play, not Euripides), torches in his hands; Jason, sword drawn and spear in hand, rushes in too late, his spearman
behind him. A casket and a dish float in the field; flowers on the ground.
The vase: Apulian red-figure volute krater attributed to the Underworld Painter, from Canosa, Munich,
Staatliche Antikensammlungen 3296.
The plate as photographed for Williams College Archives and Special Collections (JSTOR community collection, image
10.2307/community.16370860; 3474 x 2589). John's pick (2026-10-12), after the Cleveland krater's fine lines proved
too faint to trace; the crop (John, 2026-10-12): the whole lower band; the ghost of Aietes at its right edge left
out (the spearman's spear stops at his robe); the painted names, on the temple's base above, left out with it.
Maximum detail (John, 2026-10-12).

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop, the
enlargement, the grey, the blurs, Minimum and Maximum, and the thresholds. numpy only combines the masks PhotoCraft
made (labels, unions, distances, fills, centre lines) and measures; the cuts are geometry (measured edges and lines).
The SVG is written by linework.trace_svg.

Plate -> drawing, Furtwängler-Reichhold, red figures on the black ground (as tools/bacchae.py):
  - Ground: the plate's dark, thin lines opened away; the large dark areas reaching the crop's edge or the cuts, and
    the dark areas wider than POCKET_W the figures close in (between the serpents' coils, under the chariot).
  - Hair whose black runs into the ground's (HAIRS): outlined by hand along the curls' tips; inside, figure.
  - The figures: the clay left, each piece kept if most of it lies below the upper band's ground (TOPLINE), down to
    the dots of the ground lines. Out: the upper band (UPPER: its figures, the temple's base), the palmettes left of LEFT and
    right of RIGHT (the ghost of Aietes and the cloud he stands on), the frame below FLOOR.
  - On the base, kept: the casket's lid inside its outline (CASKET); the torches' flames, their strokes with the
    clay closed round them as their body (FLAMES), unoutlined.
  - Lines: the plate's black lines (local contrast), redrawn along their centres at LINE_W; the outline on the ground
    just outside the clay, as wide. The paint (the black bands of Medea's dress, the hair's dark) at its own width.
  - The grey of the plate (the robes and sleeves in thinned paint): a `tone` wash in the line colour, its opacity
    following how much darker than the clay the plate is there; the white dots and patterns on it left open.
  - The faces (FACES): their features traced finer, from the plate barely blurred.
  - Medea's sword-arm sleeve (SLEEVE): ink, its white dots open.
  - The added white (WHITE_*): lighter than the clay round it; `white` paths (as Wealth), outlined finely where it
    meets clay by a `day` path the dark theme hides.
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/medea.py jstor_medea.jpg [qa.png [dump.npz]]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import draw, morphology
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "medea.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 670, 1385, 2655, 2330      # crop in plate px: the left palmette's border to the ghost's robe
UP = 4                                      # work at 4x the plate's px
# the upper band's ground, the dotted line its figures stand on (plate px, x: y): a piece of clay mostly above it
# belongs to the upper band (the upper figures at the right; the dots of its ground line, behind the boy's arm)
TOPLINE = [(670, 1712), (1085, 1712), (1090, 1585), (1300, 1585), (1302, 1610), (1500, 1610), (1505, 1480),
           (2255, 1480), (2260, 1475),
           (2455, 1475), (2460, 1505), (2655, 1505)]
# above this, out (plate px, x: y): the upper band, cut where its figures touch the lower one's: under the left
# figure's foot and the first booted leg, over the servant's head, under the second boot, over the servant's club,
# under the hem that Medea's cap touches (along the cap's rim), then the temple's base along its lower edge
# (measured where the plate turns from its clay to the ground, grey 90: the base, the painted names, the temple),
# its second step under Jason's name
UPPER = [(670, 1712), (735, 1712), (736, 1689), (822, 1689), (824, 1592), (928, 1592), (930, 1690), (1012, 1690),
         (1014, 1572), (1185, 1572), (1200, 1550), (1215, 1538), (1240, 1547), (1260, 1557), (1298, 1566),
         (1300, 1479), (1400, 1469), (1500, 1467), (1600, 1462), (1700, 1459), (1800, 1460), (1900, 1463),
         (1960, 1465), (2060, 1476), (2140, 1480), (2200, 1481), (2255, 1483)]
UPPER_X = 2255
# on the base, kept: the casket's lid (its outline on the plate, plate px), and the torches' flames, their strokes
# on the base's clay (boxes, plate px) with the clay closed round them (FLAME_R plate px) as their body, unoutlined
CASKET = [(1974, 1441), (2066, 1436), (2072, 1442), (2049, 1484), (1953, 1492), (1953, 1486)]
FLAMES = [(1462, 1390, 1605, 1472), (1912, 1388, 2060, 1446)]
FLAME_R, FLAME_T = 6, 15
# the flames' necks, where each flame narrows onto its torch at the base's edge (plate px, measured at 6x)
NECKS = [[(1478, 1438), (1520, 1438), (1516, 1471), (1482, 1471)], [(1916, 1438), (1964, 1438), (1959, 1466),
                                                                        (1921, 1466)]]
LEFT = 672                                  # the left palmette's border band, left of this
# the ghost of Aietes, his robe's left edge and the cloud under him, then the right palmette (plate px, y: x):
# right of this, out
RIGHT = [(1385, 2656), (1700, 2651), (1835, 2653), (1860, 2640), (2100, 2632), (2150, 2592), (2330, 2592)]
# the frame's lower edge (measured, grey 120), less FLOOR_PAD
FLOOR = [(670, 2330), (900, 2322), (1000, 2316), (1240, 2303), (1520, 2298), (1800, 2295), (2000, 2302),
         (2200, 2308), (2400, 2317), (2560, 2331), (2660, 2340)]
FLOOR_PAD = 3
DARK = 85                                   # ground and paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 3000                          # plate px: dark areas this large reaching the crop's edge are ground
POCKET_W = 34                               # plate px: dark areas inside the figures wider than this are ground
# the ground the figures close in, narrower than that (a point in each, plate px; the dark area at or nearest it):
# under Medea's raised arm; between the boy's arm and side; in the left serpent's upper loop, by Oistros' hair, by
# his arms (two), and the wedge below; in the right serpent's upper loop (two) and below his hand; between Jason's
# back and his mantle; in the curl of the left serpent's tail
POCKETS = [(1340, 1717), (1469, 1690), (1616, 1690), (1667, 1684), (1695, 1686), (1700, 1713), (1650, 1760),
           (1912, 1670), (1945, 1700), (1916, 1729), (2262, 1740), (1615, 2251)]
# hair whose black runs into the ground's with no clay between (outlines, plate px, along the curls' tips and the
# beads): inside, figure, and its dark is hair: Medea's, under the beads of her cap; the spearman's, under his hat
HAIRS = [[(1212, 1566), (1236, 1567), (1255, 1571), (1253, 1584), (1245, 1600), (1240, 1640), (1215, 1650),
          (1205, 1600)],
         [(2503, 1582), (2548, 1582), (2553, 1600), (2551, 1632), (2540, 1646), (2520, 1646), (2505, 1625)]]
# the chariot's wheels (ellipses: centre, half-width, half-height, plate px): the dark between the spokes is ground
WHEELS = [(1597, 2131, 56, 112), (1910, 2110, 48, 108)]
DOT_MIN = 4                                 # plate px: smaller pieces of clay are specks of the print
PAINT_NEAR, PAINT_CORE = 3, 45
LINE_R = 2.5                                # plate px: the closing for the lines' local contrast
LINE_LO, LINE_HI = 26, 40                   # local contrast (closing less the plate): hysteresis
# the line weight: the plate's own (its fold lines 1.5-2 plate px): the F-R rule, 0.11% of the longer side (John on
# Andromache), gives 2.2 plate px on this wide band, heavier than the plate for figures this size
LINE_W = 1.7
# the heads (boxes, plate px: the son, the servant, Medea, the boy, Oistros, Jason, the spearman): the hair, its
# curls, and the beard drawn at the printed shapes, darker than HAIR_T (barely smoothed), with the clay inside
# the curls open (pinholes under HAIR_HOLE plate px filled)
HEADS = [(685, 1840, 790, 1980), (835, 1605, 905, 1692), (1205, 1580, 1248, 1645), (1378, 1600, 1425, 1700),
         (1688, 1476, 1798, 1600), (2093, 1525, 2190, 1652), (2495, 1578, 2526, 1645)]
HAIR_T, HAIR_HOLE = 55, 2
# the eyes (boxes, plate px: the servant, Medea, the boy, Oistros' two, Jason, the spearman): finer lines, EYE_W
# plate px, and the pupil, darker than PUPIL_T, a dot at its own size (eyes never heavy: John, 2026-10-07)
EYES = [(880, 1651, 898, 1669), (1226, 1617, 1246, 1636), (1410, 1628, 1446, 1648), (1726, 1515, 1741, 1536),
        (1749, 1513, 1767, 1533), (2099, 1586, 2115, 1601), (2490, 1601, 2508, 1617)]
EYE_W, PUPIL_T, PUPIL_MAX = 1.0, 60, 10
# the faces (boxes, plate px: the servant, Medea, the boy, Oistros, Jason, the spearman): their features traced
# finer (John, 2026-10-12: "faces need to be more precise"): the plate barely blurred, closed over FACE_R plate px,
# local contrast FACE_LO/FACE_HI, drawn at FACE_W plate px, the short strokes of the lips and nostrils kept
FACES = [(866, 1640, 915, 1700), (1213, 1598, 1262, 1662), (1398, 1612, 1452, 1668), (1700, 1490, 1792, 1565),
         (2092, 1555, 2135, 1628), (2466, 1588, 2512, 1652)]
FACE_R, FACE_LO, FACE_HI, FACE_W = 1.5, 24, 40, 1.2
# the added white (John, 2026-10-12: "white paint strokes should be made visible"): on the figures, lighter than
# the clay round it by WHITE_D (the plate lightly blurred, against the clay's level there: the mean over WHITE_S
# plate px of the figures' clay, 150-212, WHITE_CLEAR plate px or more from the plate's dark, less what reads
# WHITE_D2 over it; the scan's light falls off across the
# band, 175 at the left, 200 at the right); none in the faces. Drawn as `white` paths in WHITE_FILL under the lines (as Wealth); where
# it meets clay, a fine outline, WHITE_LINE plate px, as a `day` path the dark theme hides
WHITE_D, WHITE_D2, WHITE_S, WHITE_MIN, WHITE_CLEAR = 20, 10, 20, 3, 2.5
WHITE_FILL, WHITE_LINE = "#f7f3ea", 0.8
# slivers of it narrower than WHITE_W plate px along the lines' edges dropped; a clay area between the lines that is
# white for more than WHITE_AREA of it is white whole (the casket, the dish, the wheels' rims, the hilts); the altar,
# lighter than the clay all over (205 to the figures' 175 there) and so not found against it, white whole (ALTAR)
WHITE_W, WHITE_AREA = 1.8, 0.45
ALTAR = [(1272, 2056), (1490, 2061), (1484, 2082), (1466, 2092), (1466, 2244), (1496, 2250), (1496, 2298),
         (1242, 2298), (1248, 2250), (1268, 2240), (1268, 2090)]
# Medea's cap: its grey (the plate barely blurred, from CAP_LINE to CAP_GREY) a flat tone (CAP_DEPTH), the white
# scrolls open at the plate's width (no opening there)
CAP_DEPTH, CAP_GREY = 75, 140
# Medea's sword-arm sleeve (box, plate px): ink, with its white dots open (John, 2026-10-12: "the sleeve should be
# ink with white dots"): its grey area, closed over SLEEVE_CLOSE plate px and filled, less the dots (the plate
# barely blurred, lighter than SLEEVE_DOT: the dots 214-245, the grey 90-130)
SLEEVE, SLEEVE_CLOSE, SLEEVE_DOT = (1045, 1705, 1130, 1840), 2, 170
# Medea's cap and the border of her veil (plate px): a band of dark grey (60-90) with white scrolls and dots, as dark
# as the plate's thin lines blurred; inside it only the black (lightly blurred, darker than CAP_LINE) is line, the
# grey is tone
CAP = [(1172, 1545), (1218, 1540), (1222, 1560), (1213, 1600), (1212, 1660), (1212, 1722), (1196, 1722),
       (1196, 1660), (1182, 1650), (1172, 1625), (1169, 1580)]
CAP_LINE = 50
# the tone: where the plate blurred over TONE_SMOOTH plate px is darker than the clay (CLAY) by TONE_D or more (the
# mottling of the skin gives none), or the plate barely blurred darker than TONE_DARK (the grey of Medea's cap
# between its white scrolls, which the blur lightens), away from the lines (TONE_CLEAR plate px) and the figures' edges (TONE_EDGE), at
# least TONE_W plate px across; the white patterns on it (the cap's scrolls, the sleeves' dots: the plate barely
# blurred, lighter than TONE_WHITE) cut out of it, crisp. Its opacity TONE_A[0] there, TONE_A[1] at
# TONE_D1 darker, in steps of TONE_STEP, smoothed over TONE_SIGMA plate px
CLAY, TONE_BLUR, TONE_D, TONE_D1 = 178, 0.7, 38, 100
TONE_CLEAR, TONE_EDGE, TONE_W, TONE_SMOOTH, TONE_WHITE, TONE_DARK = 1.0, 2.0, 1.5, 2.5, 150, 108
TONE_A, TONE_STEP, TONE_SIGMA = (0.12, 0.5), 0.04, 1.0
TONE_MIN = 6                                # plate px


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def poly_y(pts, x):
    """The polyline pts [(x, y)] at plate x."""
    return np.interp(x, [p[0] for p in pts], [p[1] for p in pts])


def poly_x(pts, y):
    """The polyline pts [(y, x)] at plate y."""
    return np.interp(y, [p[0] for p in pts], [p[1] for p in pts])


def add_tone(svg, tone, depth, box):
    """The tone, as paths of class "tone" in the line colour between the body and the lines (as add_wash in
    bacchae.py): each step's area drawn over the one below at the opacity that brings the total there to the
    step's, so no seam shows."""
    x0, y0, x1, y1 = box
    b, dp, s = tone[y0:y1, x0:x1], depth[y0:y1, x0:x1], TONE_SIGMA * UP
    dpt = ndi.gaussian_filter(np.where(b, dp, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (a0, a1) = TONE_A
    alpha = a0 + (a1 - a0) * np.clip((dpt - TONE_D) / (TONE_D1 - TONE_D), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, TONE_STEP):
        m = b & (alpha >= a - TONE_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=8, alphamax=1.0)
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
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.6 * UP}))
        r = round(LINE_R * UP)
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "tone.png", ("filter.blur.gaussianBlur", {"radius": TONE_BLUR * UP}))
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 0.3 * UP}))
        pc(t / "gf.png", t / "fine.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "tone.png", t / "tsm.png", ("filter.blur.gaussianBlur", {"radius": TONE_SMOOTH * UP}))
        r = round(FACE_R * UP)
        pc(t / "gf.png", t / "fclosed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        g, gl, closed, tn = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "tone.png")
        gs, gf, tsm = grey(t / "gs.png"), grey(t / "gf.png"), grey(t / "tsm.png")
        fclosed, gw = grey(t / "fclosed.png"), grey(t / "gw.png")
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + X0 - 0.5, (yy + 0.5) / UP + Y0 - 0.5

    above = (px <= UPPER_X) & (py < poly_y(UPPER, px) + 1)
    outside = (px < LEFT) | (px > poly_x(RIGHT, py)) | (py > poly_y(FLOOR, px) - FLOOR_PAD) | above

    hairs = np.zeros_like(dark0)
    for pts in HAIRS:
        rr, cc = draw.polygon([(y - Y0) * UP for _, y in pts], [(x - X0) * UP for x, _ in pts], hairs.shape)
        hairs[rr, cc] = True
    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP)) & ~outside
    lab, n = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    wide = np.r_[False, np.array(ndi.maximum(ndi.distance_transform_edt(dark), lab, range(1, n + 1)))
                 > POCKET_W * UP / 2]
    for x, y in POCKETS:   # the dark area at or nearest the point (within 15 plate px)
        r = 15 * UP
        cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
        win = lab[cy - r:cy + r + 1, cx - r:cx + r + 1]
        dist = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1])
        iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
        assert win[iy, ix], f'no dark area near {(x, y)}'
        wide[win[iy, ix]] = True
    ground = (is_ground | wide)[lab] & ~hairs
    for cx, cy, ax, ay in WHEELS:
        ground |= dark & (((px - cx) / ax) ** 2 + ((py - cy) / ay) ** 2 <= 1)

    clay = ~ground & ~outside & ~dark0
    lab, n = ndi.label(clay)
    size = np.bincount(lab.ravel(), minlength=n + 1)
    low = np.bincount(lab.ravel(), weights=(py > poly_y(TOPLINE, px)).ravel(), minlength=n + 1)
    keep = (low > size / 2) & (size >= DOT_MIN * UP * UP)
    keep[0] = False
    fig = keep[lab]
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP // 2))
    # on the base: the casket's lid, and the flames' bodies round their strokes (FLAME_T: local contrast)
    lid = np.zeros_like(fig)
    rr, cc = draw.polygon([(y - Y0) * UP for _, y in CASKET], [(x - X0) * UP for x, _ in CASKET], fig.shape)
    lid[rr, cc] = True
    lid &= above
    flames = np.zeros_like(fig)
    for fx0, fy0, fx1, fy1 in FLAMES:
        box = (px >= fx0) & (px < fx1) & (py >= fy0) & (py < fy1) & above
        strokes = (closed - gl > FLAME_T) & box
        env = ndi.binary_closing(strokes, structure=morphology.disk(FLAME_R * UP))
        flames |= ndi.binary_fill_holes(env) & box
    for pts in NECKS:
        rr, cc = draw.polygon([(y - Y0) * UP for _, y in pts], [(x - X0) * UP for x, _ in pts], fig.shape)
        flames[rr, cc] = True
    fig |= lid | flames | (hairs & ~outside)

    # the paint: dark areas within the figures whose core is darker than PAINT_CORE, at the edge the plate prints
    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    paint = fine & ndi.binary_dilation(solid, iterations=PAINT_NEAR * UP) & fig

    def boxes(bs):
        m = np.zeros_like(fig)
        for bx0, by0, bx1, by1 in bs:
            m |= (px >= bx0) & (px < bx1) & (py >= by0) & (py < by1)
        return m
    eyes, heads = boxes(EYES), boxes(HEADS)
    hair = (gf < HAIR_T) & fig & (heads | hairs) & ~eyes
    hair = morphology.remove_small_objects(hair, max_size=UP * UP)
    hair |= ndi.binary_fill_holes(hair) & ~morphology.remove_small_objects(
        ndi.binary_fill_holes(hair) & ~hair, max_size=HAIR_HOLE * UP * UP)
    paint = (paint & ~heads) | hair

    tw = LINE_W * UP                            # the line width, work px
    firm = apply_hysteresis_threshold(closed - gl, LINE_LO, LINE_HI)
    cap = np.zeros_like(fig)
    rr, cc = draw.polygon([(y - Y0) * UP for _, y in CAP], [(x - X0) * UP for x, _ in CAP], fig.shape)
    cap[rr, cc] = True
    firm &= ~cap | (gl < CAP_LINE)
    black = firm & fig & ~ndi.binary_dilation(paint, iterations=UP)
    lines = centre_lines(black, tw, 3 * UP, 2 * tw) | paint
    pupil = (gs < PUPIL_T) & eyes & fig
    lab, _ = ndi.label(pupil)
    pupil &= (np.bincount(lab.ravel()) < PUPIL_MAX * UP * UP)[lab]
    faces = boxes(FACES) & ~ndi.binary_dilation(paint, iterations=UP)
    ffirm = apply_hysteresis_threshold(fclosed - gf, FACE_LO, FACE_HI) & fig
    face_lines = centre_lines(ffirm & faces & ~eyes, FACE_W * UP, UP, UP)
    eye_lines = centre_lines(ffirm & eyes & ~ndi.binary_dilation(pupil, iterations=UP // 2), EYE_W * UP, UP, UP)
    lines = np.where(eyes, eye_lines | pupil, np.where(faces, face_lines, lines))
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & (dt <= tw) & ~outside
    ink = (lines & fig) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 2 * UP * UP)[lab]

    # the added white, against the clay's level round it
    s_ = WHITE_S * UP
    clayish = fig & (gw > 150) & (gw < 212) & (ndi.distance_transform_edt(~dark0) > WHITE_CLEAR * UP)
    level = ndi.gaussian_filter(np.where(clayish, gw, 0), s_) / np.maximum(ndi.gaussian_filter(clayish * 1.0, s_), 1e-3)
    clayish &= gw < level + WHITE_D2
    level = ndi.gaussian_filter(np.where(clayish, gw, 0), s_) / np.maximum(ndi.gaussian_filter(clayish * 1.0, s_), 1e-3)
    white = morphology.remove_small_objects((gw > level + WHITE_D) & fig & ~boxes(FACES), max_size=WHITE_MIN * UP * UP)
    white = ndi.binary_opening(white, structure=morphology.disk(round(WHITE_W * UP / 2))) | (white & cap)
    lab, n = ndi.label(fig & ~ndi.binary_dilation(ink, iterations=UP // 2))
    frac = ndi.mean(white, lab, range(1, n + 1)) if n else []
    whole = np.r_[False, np.asarray(frac) > WHITE_AREA][lab]
    altar = np.zeros_like(fig)
    rr, cc = draw.polygon([(y - Y0) * UP for _, y in ALTAR], [(x - X0) * UP for x, _ in ALTAR], fig.shape)
    altar[rr, cc] = True
    white = (white | whole | (altar & fig & ~ndi.binary_dilation(ink, iterations=UP // 2))) & ~boxes(FACES)
    # (its outline where it meets clay, not where it meets the lines or the ground: there the white shows already)
    rim = (ndi.distance_transform_edt(~white) <= WHITE_LINE * UP) & ~white & fig & ~ink
    day = rim & ~ndi.binary_dilation(ink, iterations=UP)
    lab, _ = ndi.label(day)
    day &= (np.bincount(lab.ravel()) > UP * UP)[lab]
    ink |= day

    depth = np.where(cap, CAP_DEPTH, CLAY - tn)
    inner = ndi.distance_transform_edt(fig) > TONE_EDGE * UP
    tone = inner & ((CLAY - tsm > TONE_D) | (gf < TONE_DARK)) & \
        ~ndi.binary_dilation(black | paint, iterations=round(TONE_CLEAR * UP))
    tone = ndi.binary_opening(tone, structure=morphology.disk(max(1, round(TONE_W * UP / 2)))) & (gf < TONE_WHITE) & \
        ~white
    tone = (tone & ~cap) | ndi.binary_opening(cap & fig & (gf >= CAP_LINE) & (gf < CAP_GREY) & ~white,
                                              structure=morphology.disk(UP // 2))
    tone = morphology.remove_small_objects(tone, max_size=TONE_MIN * UP * UP)
    sleeve = ndi.binary_fill_holes(ndi.binary_closing(tone & boxes([SLEEVE]),
                                                      structure=morphology.disk(SLEEVE_CLOSE * UP))) & fig
    dots = sleeve & (gf > SLEEVE_DOT)
    ink = (ink & ~sleeve) | (sleeve & ~dots) | (ink & sleeve & ~dots)
    white = (white & ~sleeve) | dots
    tone &= ~sleeve
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint,
                            firm=firm & fig, edge=edge, tone=tone, depth=depth.astype(np.float16), white=white, day=day)

    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight="drawn", day=day,
        title='Medea seizing her son, the serpent chariot, and Jason',
        desc='Line drawing after Karl Reichhold\'s 1906 drawing of the Medea krater by the Underworld Painter, '
             'Munich, Staatliche Antikensammlungen 3296 (Furtwängler and Reichhold, Griechische Vasenmalerei II, '
             'Taf. 90); the lower band, cut out and retraced.')
    if tone.any():
        add_tone(OUT, tone, depth, info['box'])
    add_white(OUT, white, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it (the day path hidden)
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        dark = Path(qa).with_suffix('.dark.svg')
        dark.write_text(re.sub(r'<path class="day"[^>]*/>', "", OUT.read_text()))
        lw.qa_dark(dark, info['box'], Path(qa).with_suffix('.dark.png'))
        dark.unlink()


def add_white(svg, white, box):
    """The added white as a path of class "white" in WHITE_FILL, between the body (and the tone) and the lines, as
    Wealth: traced at the lines' size."""
    x0, y0, x1, y1 = box
    d, _ = lw.potrace_d(white[y0:y1, x0:x1], turdsize=4, alphamax=1.0)
    svg.write_text(svg.read_text().replace(
        '<path class="lines"', f'<path class="white" fill="{WHITE_FILL}" stroke="none" d="{d}"/><path class="lines"', 1))


if __name__ == '__main__':
    main(*sys.argv[1:4])
