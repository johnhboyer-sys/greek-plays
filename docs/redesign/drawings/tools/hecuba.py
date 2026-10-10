"""Hecuba: Neoptolemos leading veiled Polyxena to the tomb of Achilles, from Gerhard, Trinkschalen und
Gefässe des Königlichen Museums zu Berlin II (Berlin, 1850), Taf. XVI, as scanned by Heidelberg University
Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/gerhard1850bd2/4/V_Tafel_16.jpg
(2123 x 3063; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1850bd2/0051)
John's pick (Plate Picks 15-6Ea, 2026-10-08); the crop (2026-10-10): Polyxena, Neoptolemos with his spear,
the white tomb with the snake and the dog, and Achilles' winged shade above it; the hoplite at the left, his
shield and spears, and the chariot of the frieze above, left out along the pair's own lines.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop, the
enlargement, the grey, the warm channel (Channel Mixer), the blurs, Minimum and Maximum, and the thresholds.
numpy only combines the masks PhotoCraft made (labels, unions, distances, fills) and measures; the cuts are
geometry (least-cost paths through hand-placed points, linework.livewire). The SVG is written in the house
format directly, as for Seven and Lysistrata: linework's trace_svg takes off the clay rim outside the lines
that the dark theme needs here.

Plate -> drawing, black-figure, drawn as silhouettes (John's choice, 2026-10-10, from a test on the two heads,
as on Seven, Ajax and Lysistrata), the added purple as a grey wash:
  - Ground: the orange clay (warm: red less blue over WARM_T, and lighter than CLAY_L), its large areas and
    the pockets the figures close in (POCKETS).
  - The figures: all else inside the cuts, joined to SEEDS. Out: above the frieze's ground line (TOP), but for
    the spear's head and the helmet (TOP_KEEP); right of the frame's inner line (RIGHT); below the ground line
    (FLOOR); left of Polyxena's back (BACK, a least-cost path along her outline through hand-placed points),
    with the hoplite and his shield and spears; the ends of the hoplite's spears behind Neoptolemos' leg
    (SPEARS).
  - The black is drawn black. Open in it: the incisions and the clay dots (light marks, at least LINE_W
    wide), the added white (skin, the tomb, the crest, the dots), with the dark lines printed on it. Where the
    white meets the ground or a cut, an outline LINE_W wide just outside it.
  - The added purple (mantle stripes, dots, shield rims): a `tone` path, the line colour at PURPLE_OP.
  - Dark theme: the figures' area is clay, a RIM wider than the black, so the black reads on the dark page;
    the marks and the white show clay.

    python3 docs/redesign/drawings/tools/hecuba.py V_Tafel_16.jpg [qa.png]
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

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from lysistrata import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "hecuba.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 940, 1190, 1995, 2380     # crop in plate px
UP = 3                                     # work at 3x the plate's px
# the frieze's ground line above the picture: its lower edge, y = 1301.5 (measured 1300-1302 along it);
# above it, out, but for TOP_KEEP
TOP = 1301.5
# above TOP, kept: the spear's head, up to where it meets the rim of the chariot wheel above (its edges measured
# row by row below the wheel, the tip where they would meet over the rim), and the helmet's crest-holder, cut
# from the horses and the frieze's border that touch it along its own outline (CREST, a least-cost path)
# The wheel's rim crosses the point, so the plate gives no edge there: above SPEAR_FILL the polygon is drawn solid
SPEAR_FILL = 1274
SPEAR_TIP = [(1284, 1304), (1269, 1272), (1281, 1250), (1291, 1264), (1305, 1280), (1318, 1304)]
CREST = [(1385, 1302), (1392, 1278), (1412, 1255), (1445, 1236), (1490, 1226), (1530, 1238), (1552, 1262), (1562, 1302)]
# the frame's inner line at the right: its left edge, x = quadratic in (y - 1800) (plate px; fitted to 97 rows
# from 1310 to 2340, within 0.8 px): right of it, out
RIGHT = (-1.05287e-04, -3.84077e-02, 1977.405)
# the ground line's top edge (plate px), measured where clay or white stands above it, between the feet:
# below it, out (FLOOR_CLEAR above it)
FLOOR = [(940, 2365.0), (1110, 2364.7), (1160, 2364.4), (1215, 2362.9), (1470, 2360.8), (1515, 2361.7),
         (1730, 2365.6), (1850, 2365.3), (1920, 2364.2), (1995, 2364.0)]
FLOOR_CLEAR = 1.0
# Polyxena's white feet stand into the ground line, which prints 8-10 px thick under them: cut there, the strip of it
# kept above FLOOR read as thick black soles. Between SOLES (x, plate px), the black within SOLE_H plate px above
# FLOOR with white above it in the same column (or 2 px to either side) goes too, and the feet get the outline LINE_W wide along their
# own lower edge (not further right: Neoptolemos' black foot lies on the white tomb)
SOLES, SOLE_H = (950, 1345), 12
# Polyxena's back, against the hoplite and his shield: his shield's rim shows up to the line that bounds the
# clay gap with his two spears in it, so the shield lies behind her and her back is that line (BACK, a
# least-cost path along it, from her shoulder down to her heel; straight along the end of the rim, where the
# path cut into the purple); left of it, out. Above her shoulder the
# cut runs up the clay between her veil and the hoplite's purple crest, then along the crest's outer edge
# where it meets her shoulder (UP_BACK). At her heel she stands
# against the hoplite's foot with no line between: the cut runs along the white's own edge (HEEL, its
# half-maximum, measured every 5-10 rows), and the outline drawn there is hers.
UP_BACK = [(1136, 1190), (1136, 1450), (1128, 1476), (1121, 1490), (1114, 1503)]
BACK = [(1112, 1512), (1104, 1600), (1117, 1655), (1140, 1700), (1130, 1780), (1131, 1845), (1121.5, 1884),
        lw.STRAIGHT, (1110.5, 1916), (1100, 1990), (1085, 2040), (1033, 2103), (1010, 2180), (988, 2242)]
HEEL = [(972, 2262), (965, 2286), (963.5, 2295), (960.5, 2305), (957.5, 2312), (954.5, 2320), (953.5, 2330),
        (954.5, 2340), (956.5, 2350), (957.5, 2358), (957.5, 2370), (X0 - 2, 2370)]
# the ends of the hoplite's two spears, below and right of Neoptolemos' rear calf, which they pass behind: cut
# along the clay line between them and the calf (SPEARS, a least-cost path), right of it out
SPEARS = [(1356, 2183), (1340, 2207), (1318, 2240)]
# and two short pieces of the same spears across the clay strip between Polyxena's skirt and foot and his calf:
# out between the skirt's edge (or the foot's outline, 1.5 px clear of it) and the calf's edge, both measured
# row by row above and below each piece
SPEAR_BITS = [[(1281, 2146), (1299, 2146), (1296, 2167), (1294, 2173), (1291, 2182), (1289, 2190), (1276, 2190),
               (1277, 2176), (1280, 2160)],
              [(1267, 2229), (1279.5, 2229), (1271.8, 2270), (1254, 2270)]]
WARM_T, CLAY_L = 85, 115                   # clay: red less blue over WARM_T, grey over CLAY_L
BLACK_T = 75                               # light marks in the black: lighter than this (or by the top-hat)
# the added white: lighter than WHITE_T, red less blue under WHITE_WARM, then out to WHITE_EDGE beside it. The
# thin dark lines printed on it (lids, curls, toes) print grey, 80-130: at the half-maximum (112) the white ate
# them into dashes
WHITE_T, WHITE_WARM, WHITE_EDGE = 165, 60, 140
WHITE_MIN = 6                              # plate px^2: the white of Polyxena's eye is 10-15
# the purple: red less blue over PURPLE_WARM and grey PURPLE_L, not clay, wider than PURPLE_OPEN plate px
PURPLE_WARM, PURPLE_L, PURPLE_OPEN = 40, (70, 125), 1.5
PURPLE_OP = 0.45
# plate px: clay areas this large are ground. Every clay area over 30 plate px^2 that the figures close in is
# ground seen between them (fifteen, from 50 to 1,516 plate px^2, checked one by one on the plate): the plate's
# reserved clay is all thinner (incisions)
AUTO_GROUND = 30
WIDE_CLAY = 2.5
POCKETS = []
SEEDS = [(1200, 1700), (1450, 1600), (1800, 2000), (1760, 1400)]
LINE_W = 1.5                               # plate px: the outline and the thinnest mark
RIM = 1.5                                  # plate px: the clay round the black on the dark theme
GRAIN = 4                                  # plate px^2: light specks in the black smaller than this are grain
# light marks: the white top-hat (the plate less its Minimum then Maximum over 1 plate px) over MARK_T, taken on the
# plate smoothed along its own strokes (PhotoCraft's Motion Blur, ORIENT_D plate px long, at every ORIENT_STEP
# degrees, each pixel taking the blur at its strokes' direction, the structure tensor's, as in lysistrata.py): the
# shade's beard is hatched in strokes 1 px wide and 2 px apart, which the plain top-hat broke into specks
MARK_T = 25
ORIENT_D, ORIENT_STEP = 4, 15
NEAR_WHITE = 2.5                           # plate px: no light marks this near the white (its soft edge)
# plate px: nor this near the figures' edge, where the print's soft edge passed for a light mark all round them
# and ate a band off every outline (the shade's profile came out lumpy)
EDGE_CLEAR = 1.5
# The shade's face (40 plate px; John, 2026-10-10, on pass 1: "fix the shade"): its incisions are 1 px, and found
# from the plate they came out as blots (the beard's hatching) and dashes. Inside SHADE_ZONE (plate px) the light
# marks are these strokes instead, placed by hand on the plate's pixel grid at 12-14x (plate px, polylines; the
# iris an ellipse: centre, radii), drawn SHADE_W plate px wide, the hatching HATCH_W
SHADE_ZONE = [(1745, 1334), (1782, 1334), (1782, 1352), (1798, 1356), (1799, 1364), (1808, 1364), (1808, 1378),
              (1792, 1384.5), (1772, 1385.5), (1760, 1384), (1745, 1389)]
SHADE_STROKES = [
    # the eye: upper lid to the corner, lower lid back
    [(1757, 1341.5), (1758, 1338.3), (1761.3, 1337.3), (1764.3, 1337.3), (1766.7, 1338), (1771, 1341), (1775.7, 1344.3),
     (1778.3, 1345.3), (1775.7, 1345.8), (1770.7, 1348.7), (1766, 1349.6), (1762, 1349.6), (1759, 1348), (1757, 1345.5),
     (1757, 1341.5)],
    # the cheek-piece's edge, down to the jaw, and the beard's lower line
    [(1761.3, 1350.7), (1758.7, 1351), (1759, 1354.7), (1758.3, 1356.7), (1756.7, 1360.3), (1754.7, 1361.7), (1754, 1364),
     (1750.3, 1369), (1751.7, 1370), (1757, 1370), (1761.7, 1369.7), (1768.3, 1367.7), (1770.3, 1367.8), (1773.3, 1369.2),
     (1777, 1369.8), (1781, 1370)],
    # under the jaw, the beard's long point: a second line, and its lower edge
    [(1745.5, 1376.5), (1747, 1374.7), (1749, 1373.4), (1753, 1373), (1756, 1372.6), (1758.5, 1371.3), (1760, 1370.4)],
    [(1746, 1387), (1748.5, 1385.5), (1752.5, 1383), (1754.5, 1381.2), (1757, 1380), (1758.5, 1378.8), (1761, 1377.2),
     (1763.5, 1376), (1765, 1375), (1766.5, 1374), (1767.5, 1373), (1769, 1372), (1770.5, 1371), (1772.5, 1370),
     (1774, 1369.3)],
    # the beard's right end, and the two lines of the shoulder below it
    [(1779.7, 1370), (1782.3, 1372), (1782.7, 1375.7), (1783, 1376.7), (1787, 1376.3), (1793.3, 1373.7), (1797.3, 1369)],
    [(1805.7, 1367.3), (1806, 1368.3), (1805, 1371.7), (1801.7, 1374.7), (1798, 1376.7), (1790, 1380), (1783.3, 1382),
     (1779, 1382.7), (1773.7, 1383)],
    # the beard's upper line
    [(1773, 1365.7), (1774.7, 1364.7), (1778.3, 1364), (1782, 1362.3), (1785.3, 1361.7), (1787, 1361.3), (1794.3, 1359.7)],
]
SHADE_IRIS = ((1764.5, 1344.7), (5.0, 4.0))
SHADE_HATCH = [[(1780.5, 1363.5), (1779.5, 1369.5)], [(1784, 1364), (1783, 1369.5)], [(1786.8, 1364), (1788.5, 1368.5)],
               [(1789.3, 1363.3), (1790.8, 1367), (1790, 1369.5)]]
SHADE_W, HATCH_W = 1.2, 1.0
# The rest of the shade (SHADE_BOX, plate px: arm, hand, body, wings): its incisions are as fine and broke into dashes
# at MARK_T; there the light marks are taken over SHADE_T and redrawn along their centres SHADE_W wide, spurs
# shorter than 2 plate px pruned (as lysistrata.centre_lines); marks wider than 2.6 plate px (the crest's dots, the
# clay between arm and body) stay as found
SHADE_BOX, SHADE_T = (1735, 1290, 1885, 1430), 14
SMOOTH = 0.4                               # plate px: every edge smoothed (Gaussian Blur, Threshold at half)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def pc_mask(m, *steps):
    """A mask run through PhotoCraft (steps as for pc), back as a mask (grey 128 and over)."""
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "m.png", Path(td) / "o.png"
        Image.fromarray(m.astype(np.uint8) * 255).save(a)
        pc(a, b, *steps)
        return grey(b) >= 128


def smooth(m, r):
    """m with its edges smoothed: PhotoCraft's Gaussian Blur r plate px, then Threshold at half."""
    return pc_mask(m, ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": r * UP}),
                   ("image.adjustments.threshold", {"level": 128}))


def stroke(shape, pts, w):
    """A polyline (plate px) drawn w plate px wide, as a mask at UP."""
    P = np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)
    path = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])])
    m = np.zeros(shape, bool)
    yx = np.clip(path[:, ::-1].astype(int), 0, np.array(shape) - 1)
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= w * UP / 2


def thick(m, w):
    """m, every part at least w plate px wide (thin marks widened along their centres)."""
    return m | (ndi.distance_transform_edt(~morphology.skeletonize(m)) <= w * UP / 2)


def at(x, y):
    """Plate px -> work px (row, col)."""
    return round((y - Y0) * UP), round((x - X0) * UP)


def poly(shape, pts):
    """A polygon given in plate px, as a mask at UP."""
    return lw.polygon_mask(shape, np.array([((x - X0) * UP + 0.5, (y - Y0) * UP + 0.5) for x, y in pts]))


def oriented(t, src_png, name):
    """src_png smoothed along its own strokes (ORIENT_*): PhotoCraft's Motion Blur at each angle; numpy picks,
    per pixel, the blur at the strokes' direction (as lysistrata.py)."""
    g = grey(src_png)
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(src_png, t / f"{name}{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    mb = np.stack([grey(t / f"{name}{a}.png") for a in angs])
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    out = np.take_along_axis(mb, i[None], 0)[0]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(t / f"{name}.png")
    return t / f"{name}.png"


def write_svg(lines, body, tone, out, title, desc):
    """The house format (as linework.trace_svg writes it): 1000 units tall, the body path under a `tone` path
    (the purple) under the lines, traced at the work px (as seven.py)."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    td, _ = lw.potrace_d(tone[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="tone" fill="currentColor" fill-opacity="{PURPLE_OP}" stroke="none" d="{td}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        pc(t / "up.png", t / "warm.png", ("image.adjustments.channelMixer", {"gray": [100, 0, -100, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        Lo = oriented(t, t / "L.png", "Lo")
        pc(Lo, t / "Lo_open.png", ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}))
        L, W = grey(t / "L.png"), grey(t / "warm.png")
        light_hat = grey(Lo) - grey(t / "Lo_open.png")
    H, Wd = L.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0

    # the cuts (least-cost paths follow the light lines: the incisions and the clay)
    cost = 1.0 / (0.03 + (L / 255.0) ** 3)
    wire = lambda pts: lw.livewire(cost, [q if q == lw.STRAIGHT else ((q[0] - X0) * UP, (q[1] - Y0) * UP) for q in pts])
    plate = lambda xy: [(x / UP - 0.5 + X0 + 0.5 / UP, y / UP - 0.5 + Y0 + 0.5 / UP) for x, y in xy]
    above = py < TOP
    crest = plate(wire(CREST))
    keep_top = poly(L.shape, SPEAR_TIP) | poly(L.shape, crest + [(CREST[-1][0], TOP + 2), (CREST[0][0], TOP + 2)])
    right = px > np.polyval(RIGHT, py - 1800)
    floor = py > np.interp(px, *zip(*FLOOR)) - FLOOR_CLEAR
    left = poly(L.shape, [(X0 - 2, Y0 - 2)] + UP_BACK + plate(wire(BACK)) + HEEL + [(X0 - 2, Y1 + 2)])
    spears = poly(L.shape, plate(wire(SPEARS)) + [(SPEARS[-1][0], 2310), (1480, 2310), (1480, SPEARS[0][1])])
    for bit in SPEAR_BITS:
        spears |= poly(L.shape, bit)
    outside = (above & ~keep_top) | right | floor | left | spears

    # ground: the clay, opened so thin marks do not join it; its large areas and the pockets
    clay = (W > WARM_T) & (L > CLAY_L)
    ground0 = ndi.binary_opening(clay & ~outside, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[at(x, y)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]
    # ...grown into the clay beside it that is wider than an incision (WIDE_CLAY plate px): the opening left the
    # narrow ends of the pockets (wedges between a hand and a body) as reserved clay, clay on the dark theme
    core = ndi.distance_transform_edt(clay) > WIDE_CLAY / 2 * UP
    ground = ndi.binary_propagation(ground, mask=clay & ~outside & (ndi.distance_transform_edt(~core) <= WIDE_CLAY / 2 * UP))
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: clay areas the figures close in, not ground)
        if not is_ground[k] and size[k] > 30 * UP * UP:
            print('clay pocket', size[k] // (UP * UP), X0 + (sl[1].start + sl[1].stop) // (2 * UP),
                  Y0 + (sl[0].start + sl[0].stop) // (2 * UP))

    # the figures: all else, joined to the seeds
    lab, _ = ndi.label(ndi.binary_opening(~ground & ~outside, structure=morphology.disk(UP)))
    keep = {lab[at(x, y)] for x, y in SEEDS}
    assert 0 not in keep, 'a seed is off the figures'
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: what is left out)
        if k not in keep and sz[k] > 200 * UP * UP:
            print('left out', sz[k] // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP,
                  X0 + sl[1].stop // UP, Y0 + sl[0].stop // UP)
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground & ~outside
    tip = poly(L.shape, SPEAR_TIP) & (py < SPEAR_FILL)
    fig |= tip

    # the added white; the purple
    white = ndi.binary_opening((L > WHITE_T) & (W < WHITE_WARM) & fig, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > WHITE_MIN * UP * UP)[lab]
    white |= fig & (L > WHITE_EDGE) & (W < WHITE_WARM) & (ndi.distance_transform_edt(~white) <= NEAR_WHITE * UP)
    mid = (W > PURPLE_WARM) & (L >= PURPLE_L[0]) & (L <= PURPLE_L[1]) & ~clay & fig
    purple = ndi.binary_opening(mid, structure=morphology.disk(round(PURPLE_OPEN * UP)))
    lab, _ = ndi.label(purple)
    purple &= (np.bincount(lab.ravel()) > 20 * UP * UP)[lab]
    purple |= ndi.binary_dilation(purple) & mid
    # the light marks in the black (incisions, the clay and white dots), at least LINE_W wide; not along the
    # white's edge or the figures' edge, where the print's soft edge would pass for one
    clear = (ndi.distance_transform_edt(~white) > NEAR_WHITE * UP) & (ndi.distance_transform_edt(fig) > EDGE_CLEAR * UP)
    marks = fig & ~white & ~purple & clear & ((L > BLACK_T) | (light_hat > MARK_T))
    lab, _ = ndi.label(marks)
    marks &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    marks = thick(marks, LINE_W) & fig & ~white & clear & ~tip
    zone = poly(L.shape, SHADE_ZONE)
    (cx, cy), (rx, ry) = SHADE_IRIS
    t = np.linspace(0, 2 * np.pi, 73)
    hand = stroke(L.shape, list(zip(cx + rx * np.cos(t), cy + ry * np.sin(t))), SHADE_W)
    for pts in SHADE_STROKES:
        hand |= stroke(L.shape, pts, SHADE_W)
    for pts in SHADE_HATCH:
        hand |= stroke(L.shape, pts, HATCH_W)
    sb = (px >= SHADE_BOX[0]) & (px < SHADE_BOX[2]) & (py >= SHADE_BOX[1]) & (py < SHADE_BOX[3]) & ~zone
    fine = fig & ~white & ~purple & clear & sb & ((L > BLACK_T) | (light_hat > SHADE_T))
    lab, _ = ndi.label(fine)
    fine &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    blob = ndi.binary_opening(fine, structure=morphology.disk(round(1.3 * UP)))
    fine = (centre_lines(fine & ~blob, SHADE_W * UP, 2 * UP) | blob) & fig & ~white & clear
    marks = np.where(sb, fine, marks)
    marks = np.where(zone, hand & fig, marks)
    # the black: all the rest of the figures (the dark lines on the white with it); an outline LINE_W wide where
    # the white meets the ground or a cut
    fy = np.interp(px, *zip(*FLOOR))
    feet = (py > fy - SOLE_H) & (px > SOLES[0]) & (px < SOLES[1])
    over = ndi.binary_dilation(white, structure=np.ones((1, 4 * UP + 1), bool))   # (and 2 px to each side)
    for _ in range(SOLE_H * UP):                  # white above, in the same column, within SOLE_H
        over[1:] |= over[:-1]
    sole = feet & over & ~white & fig
    fig &= ~sole
    marks &= ~sole
    outline = ~fig & ~(above & ~keep_top) & (ndi.distance_transform_edt(~white) <= LINE_W * UP)
    lines = smooth((fig & ~marks & ~purple & ~white) | outline, SMOOTH)
    tone = smooth(purple, SMOOTH) & ~lines
    body = ndi.distance_transform_edt(~(fig | outline)) <= RIM * UP
    if dump:
        np.savez_compressed(dump, L=L.astype(np.uint8), fig=fig, white=white, lines=lines, ground=ground,
                            marks=marks, purple=purple, outside=outside)

    info = write_svg(
        lines, body, tone, OUT,
        title='Neoptolemos leading Polyxena to the tomb of Achilles',
        desc='Line drawing after the 1850 plate of a black-figure vase in Berlin (Gerhard, Trinkschalen und '
             'Gefässe II, Taf. XVI): Neoptolemos leads veiled Polyxena to the tomb of Achilles, with a snake '
             'and a dog at the tomb and the winged shade of Achilles above; cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
