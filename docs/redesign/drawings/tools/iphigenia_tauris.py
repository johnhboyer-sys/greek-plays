"""Iphigenia in Tauris: the whole frieze of R. Jaene's lithograph of the Duke of Buckingham's vase, Archäologische
Zeitung 7 (1849), Denkmäler und Forschungen Taf. XII ("Iphigenia in Tauris. Vasenbild des Herzogs von Buckingham"),
with O. Jahn's article: Iphigenia hands her letter to Pylades (Iphigenia in Tauris 727 ff.) before the temple, Orestes
leaning on a pillar, Eros flying, Artemis above, an attendant with a tray. Internet Archive scan (Getty Research
Institute copy), leaf n156 (2239 x 3118): https://archive.org/download/archaologischez07deut/page/n156.jpg
John chose this scan on 2026-10-13 over Cornell's copy on HathiTrust (the same 300 ppi, compressed harder) and over
the vase's first publication, Monumenti inediti IV (1844-48) pl. LI on Arachne (another engraver's drawing).

Made with PhotoCraft (John, 2026-10-07; the redo asked 2026-10-09), as tools/eumenides.py: every image step runs in
`photocraft-cli` (0.2.0); numpy only combines the masks PhotoCraft made and measures. The scan leans about 0.15
degrees (3-6 px over the frieze's 1700): left as it is, so the cut's points are the 2026-10-02 tool's. The SVG is
written by linework.trace_svg.

Plate -> drawing. A lithograph in fine grey pen lines on paper, no black ground: the lines are found by local contrast
at half maximum (darker than halfway between the paper and the line's darkest px near it) and redrawn along their
centres at the plate's pen width; the figures' area is the paper the lines close off. John, 2026-10-13: the whole
frieze (the vase sketch and the caption below it left out), and Iphigenia cut from it for the Euripides home page.

Writes iphigenia-in-tauris.svg (the frieze) and euripides-iphigenia.svg (Iphigenia alone; John's crop of 2026-10-02,
kept: her with the whole tablet, the temple key, its chain and knob, and her right forearm down its outer edge;
Pylades, the temple door and steps, Artemis' foot, the attendant and her tray left out; the cut follows her veil's
curve).

    python3 docs/redesign/drawings/tools/iphigenia_tauris.py path/to/n156.jpg [qa.png]
"""
import json
import os
import shutil
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
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "iphigenia-in-tauris.svg"
HOME_OUT = Path(__file__).resolve().parent.parent / "euripides-iphigenia.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 60, 420, 1930, 1790     # crop, scan px: the frieze, from the acroteria to the two ground rules
UP = 3                                    # work at 3x the scan's px (her face is about 90 px tall)
BLUR = 0.3                                # scan px: the Gaussian before the line finder
CLOSE_R = 4                               # scan px: Maximum then Minimum, wider than a line (1-3 px)
LOW, HIGH = 8, 20                         # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 100                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 2, 0.5                     # a line's core: the darkest px within CORE_R scan px; half maximum
SMOOTH = 0.3                              # scan px: the line mask's Gaussian, cut at half
# the lines are redrawn along their centres at one width, the plate's pen (the printed lines are grey and 1.5-3 px
# wide; found by threshold they came out blotchy, the eyes as blots): spurs under SPUR scan px pruned, pieces of
# centre line under MIN_LEN scan px dropped as grain
PEN = 1.2                                 # scan px
SPUR, MIN_LEN = 2, 3
SOLID_OPEN = 1.5                          # scan px: solid black (the wave band's strokes, 4 px) is what an opening
                                          # this wide leaves of the plate darker than SOLID; it stays as printed
SPECK = 3                                 # scan px^2: smaller pieces of ink are specks of the print
SEAL = 4                                  # scan px: passages narrower than this do not join ground to figure
NEAR = 2                                  # scan px: her ink lies within this of her body
# breaks in the printed lines (ground leaked through them into clay: John, pass 1): line ends facing each other within
# JOIN_ANGLE degrees, up to JOIN_MAX scan px apart, joined straight where the plate's local contrast holds at JOIN_C
# grey levels all the way across; a free end runs on straight to the line it points at on the same terms (as
# tools/euphorbos.py). JOIN_RUN scan px of centre line give an end's direction
JOIN_MAX, JOIN_ANGLE, JOIN_C, JOIN_RUN = 8, 35, 4, 4
# points on the field (scan px): the paper areas they fall in are the vase's ground; areas reaching the crop's edge
# are ground too, every other area the lines close is clay (the temple, the altar, the pillar and its steps among
# them). The ground line, the pillar and the temple close the lower field into pockets: between the pillar and
# Orestes, between his legs and the spear; before the temple's floor, by Pylades' feet; before the door; between the
# chain and the attendant; beside the temple under Artemis's arm, between her and her spear; under the tray. John
# ringed the places pass 1's area map had wrongly as ground: under the bowl by Orestes' thigh, between Artemis's
# legs, the attendant's upper arm, the temple step under Iphigenia and the altar by the tassel are clay; the rest he
# ringed (Orestes' hand on the spear, his foot, Pylades' far shin, the attendant's hair, the lower meander) were
# leaks the line joins closed. (Read once as "flip these", it blacked out a hand, a foot and a shin.)
GROUND = [(386, 1568), (569, 1549), (713, 1548), (846, 1697), (1063, 1508), (1560, 1545), (1529, 866), (1749, 887), (1601, 1308)]
# open ends of narrow clay bands, walled for the areas only (not drawn): the strip under the entablature's left end;
# both ends of the pillar base's lower moulding (John, pass 1: these read as ground); both ends of the strip under
# Iphigenia's lower meander (the skirt's outline breaks there, 1516-1552)
WALLS = [((637.5, 636), (638, 645)), ((404, 1599), (413, 1596)), ((221, 1603), (229, 1600)),
         ((1204, 1516), (1199, 1552)), ((1343, 1524), (1349, 1536))]
# the two spears print as three lines 7 px apart; the paper between the outer pair on one side read as ground
# (John, pass 1): clay inside these polygons (scan px, on the lines' centres): Artemis's spear down to the
# attendant's head; Pylades' spear below his hand
CLAY = [[(1780, 858), (1788, 858), (1736, 1103), (1727, 1103)],
        [(1008.7, 1478), (1016, 1478), (1015, 1550), (1008.3, 1600), (1001.7, 1650), (995.3, 1700), (993, 1712),
         (987, 1712), (989.7, 1700), (995.7, 1650), (1001.7, 1600), (1007.7, 1550)]]# John's marks on pass 1b (2026-10-13), in PhotoCraft on the plate at MARKS_K x its scan px over the crop: blue
# strokes are lines the trace missed (most close a gap where ground ran into clay); green squiggles mark ground (each
# squiggle names the paper area it lies most in)
MARKS_FILES = [Path(__file__).with_name("iphigenia_tauris_marks_1.png")]
MARKS_K = 2
# a clay area meeting the ground with no line between them is a gap in the outline (John: "the ground leaks are due
# to lines not being fully traced"): where the clay's edge lies farther than GAP scan px from any line, the outline is
# drawn along the clay's edge at the pen's width
GAP = 1.0

# Iphigenia's checkered skirt (scan px): every other square hatched in strokes 2-3 px apart, too fine to trace. John
# (2026-10-13) chose a grey wash for the hatched squares. Inside CHECKER only the grid is drawn, found at a stricter
# contrast (CHECKER_LOW, CHECKER_HIGH: the hatching prints fainter than the grid); the hatching is where the plate's
# mean grey away from the lines (Gaussian over HATCH_SIGMA scan px) is darker than HATCH; a square most of which is
# hatched (HATCH_FILL) is washed whole; where a grid line is missing (an area over SQUARE) the wash follows the
# hatching. The wash: a tone path in the line colour at HATCH_OP
CHECKER = [(1196, 1519), (1270, 1522), (1350, 1530), (1360, 1600), (1372, 1668), (1190, 1675), (1188, 1600)]
CHECKER_LOW, CHECKER_HIGH = 32, 50
HATCH, HATCH_SIGMA, HATCH_FILL, HATCH_OP = 238, 3, 0.5, 0.3
SQUARE = 260                              # scan px^2: a larger area is squares a missing grid line ran together
# her areas that run on outside the cut through a break, so the test above leaves them out: points in them (scan px):
# the strip under the lower meander, the strip in her hem, two at her right foot
HOME_CLAY = [(1300, 1524), (1230, 1665), (1408, 1694), (1442, 1696)]

# Points on Iphigenia's outline in scan px, clockwise from the veil's top left corner (the 2026-10-02 tool's, approved
# by John; the stretch round her right foot moved onto its outer line; at her elbow the cut runs straight along the
# tray's lower edge, taking in the bracelet's bands; under her raised arm it runs on the arm's lower line, not into
# the strip between her bracelet and her side); the guided path snaps them onto her own
# lines. On her right the cut runs down the outer edge of her forearm, below the attendant's tray, to the hand on the
# key, down the hanging end of her stole to its tip and straight across to her skirt (the gable of the altar behind
# her stays out), and takes in the key's chain and knob.
OUTLINE = [
    (1208, 976), (1219, 966), (1234, 956), (1290, 948), (1346, 952), (1370, 972), (1376, 1000), (1385, 1025), (1395, 1050),
    (1406, 1076), (1402, 1108), (1414, 1132), (1426, 1164), (1422, 1204), (1434, 1244), (1440, 1263), lw.STRAIGHT, (1462, 1272), lw.STRAIGHT,
    (1462, 1292), (1477, 1296),
    (1490, 1314), (1501, 1334), (1510, 1352), (1517, 1370), (1516, 1392), (1530, 1402), (1545, 1400), (1558, 1410),
    (1557, 1430), (1540, 1435), (1527, 1428), (1527, 1440), lw.STRAIGHT, (1528, 1628), (1518, 1640), (1516, 1690),
    (1505, 1698), (1488, 1690), (1486, 1650), (1490, 1632), (1494, 1628), lw.STRAIGHT, (1497, 1440), lw.STRAIGHT,
    (1505, 1416), (1426, 1380), (1430, 1460), (1412, 1474), (1398, 1488), (1394, 1500), lw.STRAIGHT, (1352, 1510),
    (1362, 1530), (1372, 1546), (1381, 1563), (1389, 1583), (1396, 1602), (1402, 1621), (1408, 1650), (1424, 1668),
    (1440, 1684), (1442, 1700), (1425, 1708), (1400, 1704), (1384, 1690), (1370, 1672), (1314, 1672), (1294, 1672),
    (1297, 1686), (1285, 1697), (1240, 1701),
    (1200, 1700), (1189, 1693), (1186, 1668), (1170, 1652), (1197, 1578), (1190, 1508), (1166, 1440), (1183, 1462),
    (1154, 1348), (1178, 1316), (1210, 1236), (1180, 1288), (1150, 1268), (1138, 1260), (1118, 1262), (1095, 1258), (1070, 1251),
    (1072, 1235), (1080, 1218), (1088, 1198), (1094, 1181), (1115, 1187), (1137, 1194), (1135, 1210), (1150, 1222),
    (1170, 1228), (1210, 1212), (1234, 1164), (1226, 1140), (1222, 1115), (1216, 1090), (1224, 1060), (1221, 1040),
    (1217, 1022), (1212, 1005), (1209, 988),
]


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src, box=None, blur=BLUR, half=HALF, smooth=SMOOTH, core_r=CORE_R, speck=SPECK, low=LOW, high=HIGH):
    """The plate's ink at UP (work px) in box (scan px; the crop by default), the plate in grey, and blurred."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = x1 - x0, y1 - y0
        pc(src, t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        if blur:
            pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": blur * UP}))
        else:
            shutil.copy(t / "up.png", t / "gl.png")
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": core_r * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it
        hm = (closed - gl) >= half * (closed - core)
        ink = apply_hysteresis_threshold(np.where(hm, closed - gl, 0), low, high) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": smooth * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > speck * UP * UP)[lab]
    return g, gl, ink, closed - gl


def areas(ink, seal=SEAL):
    """The paper the ink closes off, sealed at seal (scan px): watershed labels (0 on ink)."""
    from skimage.segmentation import watershed
    paper = ~ink
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(seal * UP)))
    return watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)


def at(ws, x, y):
    """The area at a point (scan px), the commonest label within 2 scan px if it lands on ink."""
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP]
    v, n = np.unique(win[win > 0], return_counts=True)
    assert len(v), f"no paper near {(x, y)}"
    return v[np.argmax(n)]


def join_breaks(lines, contrast, tw):
    """The breaks in `lines` (work px) that JOIN_* describe, joined straight at width tw (tools/euphorbos.py's)."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    H, W = sk.shape

    def run_back(p):   # the end's last JOIN_RUN scan px of centre line, from the end inward
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

    out = np.zeros_like(lines)
    if len(ends) < 2:
        return out
    runs = [run_back(p) for p in ends]
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
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
        n = int(np.hypot(*(b - a))) * 2 + 2
        for y, x in np.linspace(a, b, n):
            out[int(round(y)), int(round(x))] = True
        used |= {i, j}
    for i, p in enumerate(ends):
        if i in used or len(runs[i]) < JOIN_RUN * UP / 2:
            continue
        d = runs[i][0] - runs[i][-1]
        d /= max(np.hypot(*d), 1e-6)
        hit = None
        for k in range(round(tw) + 1, JOIN_MAX * UP):
            y, x = np.round(p + k * d).astype(int)
            if not (0 <= y < H and 0 <= x < W):
                break
            if lines[y, x]:
                hit = k
                break
        if hit is None:
            continue
        q = p[None] + np.linspace(1, hit, hit * 2)[:, None] * d[None]
        if ndi.map_coordinates(contrast, q.T, order=1).min() < JOIN_C:
            continue
        for y, x in np.round(q).astype(int):
            out[y, x] = True
    return ndi.distance_transform_edt(~out) <= tw / 2 if out.any() else out


def lines(src):
    """The frieze's lines (work px): the line finder's ink redrawn along its centres at PEN, the solid black as
    printed, the breaks joined; the plate in grey, and blurred."""
    g, gl, found, contrast = masks(src)
    solid = ndi.binary_opening(gl < SOLID, structure=morphology.disk(SOLID_OPEN * UP))
    ink = centre_lines(found, PEN * UP, MIN_LEN * UP, SPUR * UP) | solid
    joins = join_breaks(ink, contrast, PEN * UP)
    print("joins", ndi.label(joins)[1])
    return g, gl, ink | joins


def sl(box):
    """A box (scan px) as a slice of the work arrays."""
    x0, y0, x1, y1 = box
    return np.s_[(y0 - Y0) * UP:(y1 - Y0) * UP, (x0 - X0) * UP:(x1 - X0) * UP]


def checker(src, shape):
    """The checkered skirt (work px, full frame): its grid lines, the hatched squares' wash, and the polygon."""
    xy = np.array(CHECKER, float)
    box = (*(xy.min(0) - 6).astype(int).tolist(), *(xy.max(0) + 6).astype(int).tolist())
    g, gl, found, contrast = masks(src, box, low=CHECKER_LOW, high=CHECKER_HIGH)
    grid = centre_lines(found, PEN * UP, MIN_LEN * UP, SPUR * UP)
    grid |= join_breaks(grid, contrast, PEN * UP)
    poly = lw.polygon_mask(grid.shape, (xy - box[:2]) * UP)
    paper = ~ndi.binary_dilation(grid, iterations=UP)
    s = HATCH_SIGMA * UP
    mean = ndi.gaussian_filter(g * paper, s) / np.maximum(ndi.gaussian_filter(paper.astype(np.float32), s), 1e-3)
    hatch = (mean < HATCH) & poly & ~grid
    ws = areas(grid, seal=2)
    wash = np.zeros_like(grid)
    for lab in np.unique(ws[poly & (ws > 0)]):
        m = ws == lab
        if (m & ~poly).sum() > 0.3 * m.sum():
            continue
        if m.sum() > SQUARE * UP * UP:
            wash |= ndi.binary_opening(ndi.binary_closing(m & hatch, iterations=UP), iterations=UP)
        elif hatch[m].mean() >= HATCH_FILL:
            wash |= m
    wash &= poly
    out = [np.zeros(shape, bool) for _ in range(3)]
    for o, m in zip(out, (grid & poly, wash, poly)):
        o[sl(box)] = m
    return out


def add_tone(svg, steps, box):
    """Washes added to a drawing written by lw.trace_svg with weight="drawn" (box: the crop box it returned), as paths
    of class "tone" in the line colour between the body and the lines, one per (mask, opacity) (tools/heracles.py's)."""
    x0, y0, x1, y1 = box
    paths = []
    for mask, a in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(mask[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def marks(shape):
    """John's marks on the work grid: (blue, green) bool masks; blue thinned to its centre line at the pen."""
    blue, green = np.zeros(shape, bool), np.zeros(shape, bool)
    for f in MARKS_FILES:
        a = np.asarray(Image.open(f).convert("RGBA")).astype(np.float32)
        r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3] / 255
        assert abs(a.shape[1] * UP / MARKS_K - shape[1]) <= UP and abs(a.shape[0] * UP / MARKS_K - shape[0]) <= UP
        up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((shape[1], shape[0]),
                                                                                        Image.BILINEAR)) >= 128
        blue |= up(al * ((b > r + 40) & (b > g + 20)))
        green |= up(al * ((g > r + 40) & (g > b + 20)))
    sk = morphology.skeletonize(blue)
    return ndi.distance_transform_edt(~sk) <= PEN * UP / 2, green


def figure(ink, ws, marked=()):
    """The figures' area: every paper area but the ground (GROUND, `marked`, and the areas reaching the crop's edge),
    and the ink touching it."""
    edge = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    ground = np.isin(ws, np.r_[edge[edge > 0], [at(ws, x, y) for x, y in GROUND], list(marked)].astype(int))
    # paper the seal leaves without a seed (slivers the lines close: a wreath's leaves, a drape's folds) is clay,
    # unless it reaches the crop's edge (tools/eumenides.py)
    lab, _ = ndi.label((ws == 0) & ~ink)
    out = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    clay = ((ws > 0) | ((lab > 0) & ~np.isin(lab, out))) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~ground, ground


def iphigenia(ink, fig, ws, wash):
    """Iphigenia alone, cut along OUTLINE by a least-cost path on the frieze's lines, written to HOME_OUT at the same
    pen."""
    w = lambda p: p if p == lw.STRAIGHT else ((p[0] - X0) * UP, (p[1] - Y0) * UP)
    soft = ndi.gaussian_filter(ink.astype(np.float32), 1.5 * UP / 4)
    cost = 1 + 30 * (1 - np.clip(soft * 2, 0, 1))
    path, on_straight = lw.livewire(cost, [w(p) for p in OUTLINE], closed=True, flags=True)
    keep, inner, _ = lw.cut_masks(ink.shape, path, on_straight, rim=2 * UP)
    # her body is her clay inside the cut and the lines bordering it (the frieze's body counts every line touching
    # clay: Pylades' fingers on the tablet, whose clay lies outside her cut, would come in with it). Her clay: the
    # areas lying mostly inside the cut; the altar's and the temple wall's, which the cut crosses beside her stole and
    # arm, lie mostly outside it
    n = ws.max() + 1
    hers = np.bincount(ws[inner], minlength=n) >= 0.5 * np.bincount(ws.ravel(), minlength=n)
    hers[0] = True                        # slivers the seal leaves unseeded: inside the cut, hers
    hers[[at(ws, x, y) for x, y in HOME_CLAY]] = True
    b = fig & inner & hers[ws]
    b = ndi.binary_fill_holes(b | (ink & keep & ndi.binary_dilation(b, iterations=2 * UP)))
    i = ink & keep & (ndi.distance_transform_edt(~b) <= NEAR * UP)
    lab, _ = ndi.label(i)
    i &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    info = lw.trace_svg(
        i, HOME_OUT, body=b, open_holes=~b, keep=b, weight="drawn",
        title="Iphigenia, priestess of Artemis, holding out a letter tablet and the temple key",
        desc="Line drawing after R. Jaene's 1849 lithograph of the Buckingham vase "
             "(Archäologische Zeitung 7, Taf. XII); cut out and retraced.")
    add_tone(HOME_OUT, [(wash & b, HATCH_OP)], info["box"])
    print(HOME_OUT, info)
    return info


def main(src, qa=None, dump=None):
    # (trace_svg's `keep` is the whole clay: its smoothing opening took the strips between lines 2-3 px apart, which
    # showed dark on the dark theme)
    g, gl, ink = lines(src)
    grid, wash, poly = checker(src, ink.shape)
    ink = (ink & ~poly) | grid
    walls = np.zeros_like(ink)
    for a, b in WALLS:
        for t in np.linspace(0, 1, 60):
            x, y = (np.array(a) + t * (np.array(b) - a) - (X0, Y0)) * UP
            walls[round(y), round(x)] = True
    walls = ndi.distance_transform_edt(~walls) <= PEN * UP / 2
    blue, green = marks(ink.shape)
    ink |= blue
    ws = areas(ink | walls)
    # each green squiggle: the paper area it lies most in is ground
    lab, n = ndi.label(ndi.binary_dilation(green, iterations=2 * UP))
    marked = []
    for k in range(1, n + 1):
        v, c = np.unique(ws[(lab == k) & green & (ws > 0)], return_counts=True)
        if len(v):
            marked.append(v[np.argmax(c)])
    fig, ground = figure(ink | walls, ws, marked)
    for pts in CLAY:
        m = lw.polygon_mask(ink.shape, (np.array(pts, float) - (X0, Y0)) * UP)
        fig |= m
        ground &= ~m
    lab, n = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    # outline the clay where it meets the ground with no line: the clay's edge band, a pen wide, where the edge lies
    # farther than GAP from the lines, run on a pen's width each way to meet them
    rim = fig & ndi.binary_dilation(ground, iterations=1)
    gap = rim & (ndi.distance_transform_edt(~ink) > GAP * UP)
    band = fig & (ndi.distance_transform_edt(~ndi.binary_dilation(ground, iterations=1)) <= PEN * UP)
    edge_line = band & (ndi.distance_transform_edt(~gap) <= PEN * UP * 1.5)
    print("outline gaps (work px)", int(gap.sum()))
    ink |= edge_line
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=ground, keep=fig & ~ground, weight="drawn",
        title="Iphigenia in Tauris",
        desc="Line drawing after R. Jaene's 1849 lithograph of the Buckingham vase (Archäologische Zeitung 7, "
             "Taf. XII): Iphigenia handing her letter to Pylades before the temple, Orestes, Eros, Artemis and an "
             "attendant; retraced.")
    add_tone(OUT, [(wash, HATCH_OP)], info["box"])
    print(OUT, info)
    home = iphigenia(ink, fig, ws, wash)
    if qa:  # optional: the drawings over their source, and as the dark theme shows them
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))
        q = Path(qa).with_name(Path(qa).stem + "_home.png")
        lw.qa_overlay(g, HOME_OUT, home["box"], q)
        lw.qa_dark(HOME_OUT, home["box"], q.with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
