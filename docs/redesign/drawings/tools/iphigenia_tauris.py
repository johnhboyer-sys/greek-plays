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
from ajax import draw_paths, skeleton_paths, smooth_path  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "iphigenia-in-tauris.svg"
HOME_OUT = Path(__file__).resolve().parent.parent / "euripides-iphigenia.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 60, 420, 1930, 1790     # crop, scan px: the frieze, from the acroteria to the two ground rules
# John's tone change (2026-10-13, in PhotoCraft on the pass 2 file): Levels with input black 90, then Levels with input
# black 152 and white 248. The faint grey lines print dark and unbroken; the lines are found on the plate so changed
LEVELS = [{"inBlack": 90, "inWhite": 255}, {"inBlack": 152, "inWhite": 248}]
UP = 3                                    # work at 3x the scan's px (her face is about 90 px tall)
BLUR = 0.3                                # scan px: the Gaussian before the line finder
CLOSE_R = 4                               # scan px: Maximum then Minimum, wider than a line (1-3 px)
LOW, HIGH = 24, 60                        # local contrast (grey levels, after LEVELS): a line starts at HIGH, runs on
                                          # down to LOW (8, 20 on the plate as scanned)
SOLID = 100                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 2, 0.5                     # a line's core: the darkest px within CORE_R scan px; half maximum
SMOOTH = 0.3                              # scan px: the line mask's Gaussian, cut at half
# the lines are redrawn along their centres at one width, the plate's pen (the printed lines are grey and 1.5-3 px
# wide; found by threshold they came out blotchy, the eyes as blots): spurs under SPUR scan px pruned, pieces of
# centre line under MIN_LEN scan px dropped as grain
PEN = 1.2                                 # scan px
SPUR, MIN_LEN = 2, 3
# pass 4 (John: "too many lines look like cracks. carefully attend to all clothing lines"): each line is redrawn as a
# path along its centre, smoothed along its length over LINE_SIGMA scan px (a pixel skeleton zigzags and forks), at
# the pen; side branches shorter than BRANCH scan px with a free end are dropped (the forks that read as cracks), and
# pieces free at both ends shorter than GRAIN scan px
LINE_SIGMA, BRANCH, GRAIN = 1.5, 3, 5
# her eyes (John, pass 3: "iphigenia's eyes are wonky"), drawn as curves through points read off the plate at 16x
# (scan px), in a box each where the found lines are dropped: brow, lid crease and upper lid of each eye, the right
# eye's inner corner and both lower lids; the irises as rings with the pupil a dot, a finer pen (eyes never heavy)
EYE_BOXES = [(1271, 1036, 1292, 1060), (1295, 1032, 1328, 1058),
             (1298, 1085, 1318, 1099)]   # her lower lip and chin (John, pass 7), drawn the same way
EYE_LINES = [
    [(1270, 1043.5), (1273, 1041.5), (1277, 1040.6), (1281, 1040.8), (1284.5, 1042.5), (1287, 1045.5)],
    [(1272, 1050), (1275, 1047.6), (1279, 1046.6), (1283, 1047), (1286.5, 1048.8), (1289, 1051.5)],
    [(1275.5, 1053), (1278, 1051.2), (1282, 1050.6), (1286, 1051.6), (1289, 1054)],
    [(1278, 1057), (1282, 1057.6), (1286, 1056.6)],
    [(1297, 1041.5), (1300, 1038), (1305, 1036), (1311, 1035), (1317, 1036), (1322, 1038), (1325, 1040)],
    [(1300, 1047), (1303, 1043.5), (1308, 1042), (1314, 1042), (1319, 1043.5), (1323, 1046)],
    [(1302, 1047.5), (1306, 1045.6), (1311, 1045), (1316, 1045.8), (1320, 1047.5), (1323, 1049)],
    [(1302, 1047.5), (1301.5, 1051), (1302.5, 1054.5)],
    [(1306, 1052.5), (1311, 1053.2), (1316, 1052.5), (1320, 1050.5)],
    # "the lower lip is actually two curves. lower lip dips down and then chin is slight dip up under that" (John):
    # the trace crossed them into an X
    [(1300.5, 1087), (1303, 1088.8), (1306, 1089.6), (1309, 1088.5), (1311.5, 1086)],
    [(1301, 1094.5), (1305, 1092.4), (1309, 1091.3), (1313, 1091.8)],
]
# John also traced the eyes in his pass 4 marks, then kept these instead ("your prior eye was okay"): his strokes
# inside EYE_BOXES are left out
EYE_REDRAWN, IRIS_REDRAWN = set(), set()
EYE_IRIS = [(1282, 1053.6, 2.3), (1311, 1049.2, 2.5)]   # centre x, y, radius (scan px)
EYE_PUPIL = 1.0                           # scan px: the pupil's radius; both pupils or neither (John): they go to the
                                          # tracer as `dots`, or its speck filter drops them
EYE_PEN = 1.0                             # scan px
SOLID_OPEN = 1.5                          # scan px: solid black (the wave band's strokes, 4 px) is what an opening
                                          # this wide leaves of the plate darker than SOLID; it stays as printed
WAVE = (1205, 1380, 1362, 1418)           # scan px: the wave band on Iphigenia's dress, the only solid black; elsewhere
                                          # the plate's dark is where lines cross, and drawn solid it made blots
SPECK = 3                                 # scan px^2: smaller pieces of ink are specks of the print
SEAL = 4                                  # scan px: passages narrower than this do not join ground to figure
NEAR = 2                                  # scan px: her ink lies within this of her body
# breaks in the printed lines (ground leaked through them into clay: John, pass 1): line ends facing each other within
# JOIN_ANGLE degrees, up to JOIN_MAX scan px apart, joined straight where the plate's local contrast holds at JOIN_C
# grey levels all the way across; a free end runs on straight to the line it points at on the same terms (as
# tools/euphorbos.py). JOIN_RUN scan px of centre line give an end's direction
JOIN_MAX, JOIN_ANGLE, JOIN_C, JOIN_RUN = 8, 35, 12, 4    # JOIN_C after LEVELS (4 as scanned)
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
        # the top of Artemis's hair, whose printed outline is too faint to close it (pass 3); the strip between the
        # altar's edge and the hanging chain, down to the tassel (John's ring, pass 1)
        [(1640, 575), (1645, 561), (1675, 556), (1700, 557), (1712, 566), (1700, 600), (1650, 600)],
        [(1489, 1422), (1508, 1422), (1508, 1700), (1489, 1700)],
        [(1008.7, 1478), (1016, 1478), (1015, 1550), (1008.3, 1600), (1001.7, 1650), (995.3, 1700), (993, 1712),
         (987, 1712), (989.7, 1700), (995.7, 1650), (1001.7, 1600), (1007.7, 1550)]]# John's marks on pass 1b (2026-10-13), in PhotoCraft on the plate at MARKS_K x its scan px over the crop: blue
# strokes are lines the trace missed (most close a gap where ground ran into clay); green squiggles mark ground (each
# squiggle names the paper area it lies most in)
MARKS_FILES = [Path(__file__).with_name(f"iphigenia_tauris_marks_{k}.png") for k in (1, 2, 3, 4, 5, 6)]
MARKS_K = 2
# pass 4 marks (John): blue strokes redraw lines (her brows, eye, nose, mouth, jaw and neck, the sleeve's zigzag edge,
# the pleat points, the ribbon's folds). Each stroke goes in along its centre, smoothed as the found lines, at the
# pen; the found lines within REPLACE scan px of it go (the same line drawn twice), those crossing it are cut there
REPLACE = 2.5
# his lines are a guide, not the line ("my lines weren't perfectly precise, but a guide for you"): each is moved onto
# the printed line it follows, within SNAP scan px (snap), the shift smoothed over SNAP_SIGMA scan px
SNAP, SNAP_SIGMA = 1.5, 5        # a wider search (3) and less smoothing (2) made the lines wobble onto neighbours and grain
# pass 5 marks (John): he traced the skirt's middle zone whole (the palmettes, the wave band's edges, the plants, the
# meander) and painted the meander's strip at half opacity: "added more at half opacity where it should be grey".
# Alpha MARK_HALF[0]..MARK_HALF[1] is that grey (a wash at HATCH_OP); above it, a line. An area he traced whole (his
# strokes closed over TRACED_CLOSE scan px, larger than TRACED_MIN scan px^2) is all clay ("that skirt is all clay and
# ink, not ground")
MARK_HALF = (0.25, 0.8)
# yellow (John, pass 5): clay with no black ink: the area is clay and any line under it goes
TRACED_CLOSE, TRACED_MIN = 4, 4000
TRACED_FROM = 3                           # only the pass 5 marks trace an area whole (marks_3)
# pass 6 marks (John, marks_4): he painted some dots and Pylades' irises solid. A small mark on its own (no side over
# DOT_MAX scan px, at least DOT_FILL of its box painted) is a dot, kept as painted; in FILL_BOXES (Pylades' eyes) what
# is wider than his pen (an opening over FILL_R scan px) is kept as painted too. The rest are lines, as before
FILLS_FROM = 4
DOT_MAX, DOT_FILL = 12, 0.6
DOT_IN_GREY = 0.5                         # (a dot ringed by his grey paint is where his strokes overlapped to full opacity)
DOT_LONG = 2                              # a piece longer than twice its width is a short stroke (marks_5: the messenger's upper lip, hair)
FILL_BOXES = [(925, 1040, 975, 1062)]
FILL_R = 2
# pass 7 marks (John, marks_5): his marks layer and the blue he painted on the red layer (the fillets: grey at half
# opacity, edged in line), merged. From these marks on (LOCAL_FROM) a green squiggle is ground only where it lies:
# the paper under it out to LOCAL_R scan px, inside the lines (his squiggles sit in slivers between the hair and the
# jaw, the hip and the hand, which no line seals off from the face and the hand: named whole, those went to ground);
# and his half-opacity paint, laid over the red layer, erases the found lines under it (they broke the grey)
LOCAL_FROM, LOCAL_R = 5, 3
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
CHECKER_LOW, CHECKER_HIGH = 96, 150      # after LEVELS (32, 50 as scanned)
HATCH, HATCH_SIGMA, HATCH_FILL, HATCH_OP = 238, 3, 0.5, 0.3
SQUARE = 260                              # scan px^2: a larger area is squares a missing grid line ran together
# her areas that run on outside the cut through a break, so the test above leaves them out: points in them (scan px):
# the strip under the lower meander, two at her right foot (John's outline leaves the gap between her hem and her
# left foot open: that strip and the floor round the sandal are one area)
HOME_CLAY = [(1300, 1524), (1408, 1694), (1442, 1696)]

# Iphigenia's outline for the home cut: John drew it (2026-10-14) as a closed line in PhotoCraft on the plate at
# MARKS_K x its scan px over the crop; inside it, with the line itself, is the cut (my guided cut left out part of
# the stole on her left)
HOME_OUTLINE = Path(__file__).with_name("iphigenia_tauris_outline.png")
# the top of her left foot under the hem, printed faint and found only in dashes, so the gap between hem and foot
# ran into the foot (John: "there are some broken lines in ink outlining the foot and sandal"): drawn through
# points read off the plate at 12x (scan px), at the pen, from the sandal's toe to the hem's edge
FOOT_LINES = [[(1200, 1672.5), (1208, 1667.5), (1218, 1666.3), (1228, 1665.3), (1236, 1664), (1243, 1661),
               (1247, 1658.5)]]


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
    """The plate's ink at UP (work px) in box (scan px; the crop by default), found on the plate with LEVELS applied;
    the plate in grey and blurred (as scanned, without LEVELS: the solid black and the hatching are read there, since
    LEVELS takes every line to black); and the local contrast the ink was found by."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = x1 - x0, y1 - y0
        pc(src, t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "adj.png", *[("image.adjustments.levels", lv) for lv in LEVELS])
        for a, b in (("up", "gl"), ("adj", "al")):
            if blur:
                pc(t / f"{a}.png", t / f"{b}.png", ("filter.blur.gaussianBlur", {"radius": blur * UP}))
            else:
                shutil.copy(t / f"{a}.png", t / f"{b}.png")
        r = CLOSE_R * UP
        pc(t / "al.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "al.png", t / "core.png", ("filter.other.minimum", {"radius": core_r * UP, "preserve": "roundness"}))
        g, gl, al = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "al.png")
        closed, core = grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it
        hm = (closed - al) >= half * (closed - core)
        ink = apply_hysteresis_threshold(np.where(hm, closed - al, 0), low, high) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": smooth * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > speck * UP * UP)[lab]
    return g, gl, ink, closed - al


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


def even_lines(found):
    """The lines of `found` (work px) redrawn as smoothed paths at the pen (LINE_SIGMA, BRANCH, GRAIN)."""
    paths = skeleton_paths(found)
    sk = morphology.skeletonize(found)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    free = sk & (nb == 1)
    keep = []
    for q in paths:
        n = len(q)
        if (q[0] == q[-1]).all():
            keep.append(q)
            continue
        ends = int(free[tuple(q[0])]) + int(free[tuple(q[-1])])
        if ends == 2 and n < GRAIN * UP:
            continue
        if ends == 1 and n < BRANCH * UP:
            continue
        keep.append(q)
    keep = [smooth_path(q, LINE_SIGMA * UP) for q in keep]
    return draw_paths(found.shape, keep, [PEN * UP] * len(keep))


def eyes(shape):
    """Her eyes (EYE_*), drawn at EYE_PEN on the work grid, and the boxes they replace the found lines in."""
    from scipy.interpolate import splev, splprep
    w = lambda pts: (np.array(pts, float) - (X0, Y0)) * UP
    paths = []
    for i, pts in enumerate(EYE_LINES):
        if i in EYE_REDRAWN:
            continue
        xy = w(pts)
        tck, _ = splprep(xy.T, s=0, k=min(3, len(xy) - 1))
        x, y = splev(np.linspace(0, 1, 40 * len(xy)), tck)
        paths.append(np.c_[y, x])
    for k, (cx, cy, r) in enumerate(EYE_IRIS):
        if k in IRIS_REDRAWN:
            continue
        t = np.linspace(0, 2 * np.pi, 120)
        (x, y), = [w([(cx, cy)])[0]]
        paths.append(np.c_[y + r * UP * np.sin(t), x + r * UP * np.cos(t)])
    m = draw_paths(shape, paths, [EYE_PEN * UP] * len(paths))
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    for k, (cx, cy, _) in enumerate(EYE_IRIS):
        if k in IRIS_REDRAWN:
            continue
        (x, y), = [w([(cx, cy)])[0]]
        m |= (yy - y) ** 2 + (xx - x) ** 2 <= (EYE_PUPIL * UP) ** 2
    box = np.zeros(shape, bool)
    for b in EYE_BOXES:
        box[sl(b)] = True
    return m, box


def lines(src):
    """The frieze's lines (work px): the line finder's ink redrawn along its centres at PEN, the solid black as
    printed, the breaks joined; the plate in grey, and blurred."""
    g, gl, found, contrast = masks(src)
    solid = ndi.binary_opening(gl < SOLID, structure=morphology.disk(SOLID_OPEN * UP))
    w = np.zeros_like(solid)
    w[sl(WAVE)] = True
    solid &= w
    ink = even_lines(found) | solid
    eye, box = eyes(ink.shape)
    ink = (ink & ~box) | eye
    joins = join_breaks(ink, contrast, PEN * UP) & ~box
    print("joins", ndi.label(joins)[1])
    return g, gl, ink | joins, contrast


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


def snap(q, contrast):
    """A path of John's (y, x, work px) moved onto the printed line it follows: each point slides along the path's
    normal, up to SNAP scan px, to where the plate's local contrast is highest; where nothing there reaches JOIN_C
    (no printed line: a gap he closed) it stays. The shifts are smoothed along the path over SNAP_SIGMA scan px."""
    q = smooth_path(q, LINE_SIGMA * UP)
    if len(q) < 3:
        return q
    t = np.gradient(q, axis=0)
    t /= np.maximum(np.hypot(*t.T), 1e-6)[:, None]
    n = np.c_[-t[:, 1], t[:, 0]]
    offs = np.arange(-SNAP, SNAP + 0.01, 0.25) * UP
    pts = q[:, None, :] + offs[None, :, None] * n[:, None, :]
    v = ndi.map_coordinates(contrast, [pts[..., 0].ravel(), pts[..., 1].ravel()], order=1).reshape(pts.shape[:2])
    v -= 0.002 * offs[None, :] ** 2       # ties go to the nearer line
    best = offs[np.argmax(v, 1)]
    best[v.max(1) < JOIN_C] = 0
    best = ndi.gaussian_filter1d(best, SNAP_SIGMA * UP, mode="nearest")
    return q + best[:, None] * n


def marks(shape, contrast):
    """John's marks on the work grid: (lines, green, grey, traced, yellow). Blue at full opacity is a line, redrawn along its
    centre at the pen; blue at half opacity (MARK_HALF) wider than a stroke's soft edge is a grey wash; `traced` is the
    area inside each large group of his strokes (an area he traced whole: all of it clay)."""
    blue, green, grey_, traced, yellow, fills, spots, over = (np.zeros(shape, bool) for _ in range(8))
    for f in MARKS_FILES:
        a = np.asarray(Image.open(f).convert("RGBA")).astype(np.float32)
        r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3] / 255
        assert abs(a.shape[1] * UP / MARKS_K - shape[1]) <= UP and abs(a.shape[0] * UP / MARKS_K - shape[0]) <= UP
        up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((shape[1], shape[0]),
                                                                                        Image.BILINEAR)) >= 128
        isb = (b > r + 40) & (b > g + 20)
        line = up((al >= MARK_HALF[1]) & isb)
        if int(f.stem.rsplit("_", 1)[1]) >= FILLS_FROM:
            full = (al >= MARK_HALF[1]) & isb
            painted = (al > MARK_HALF[0]) & isb
            lab, _ = ndi.label(full, structure=np.ones((3, 3)))
            fill = np.zeros_like(full)
            for k, o in enumerate(ndi.find_objects(lab), 1):
                piece = lab[o] == k
                o2 = tuple(slice(max(t.start - 2, 0), t.stop + 2) for t in o)
                ring = ndi.binary_dilation(lab[o2] == k, iterations=2) & ~(lab[o2] == k)
                if (max(piece.shape) <= DOT_MAX * MARKS_K and piece.mean() >= DOT_FILL
                        and max(piece.shape) <= DOT_LONG * min(piece.shape)
                        and painted[o2][ring].mean() < DOT_IN_GREY):
                    fill[o] |= piece
            wide = ndi.binary_opening(full, structure=morphology.disk(FILL_R * MARKS_K))
            for x0, y0, x1, y1 in FILL_BOXES:
                o = np.s_[(y0 - Y0) * MARKS_K:(y1 - Y0) * MARKS_K, (x0 - X0) * MARKS_K:(x1 - X0) * MARKS_K]
                fill[o] |= wide[o]
            fill = up(fill)
            fills |= fill
            line &= ~fill
        blue |= line
        if f.stem.endswith(f"_{TRACED_FROM}"):
            whole = line
        local = int(f.stem.rsplit("_", 1)[1]) >= LOCAL_FROM
        if local:
            spots |= up(al * ((g > r + 40) & (g > b + 20)))
        else:
            green |= up(al * ((g > r + 40) & (g > b + 20)))
        yellow |= up(al * ((r > b + 60) & (g > b + 60)))
        half = (al > MARK_HALF[0]) & (al < MARK_HALF[1]) & isb
        if local:                         # (the red lines he painted over left holes in it)
            half = ndi.binary_closing(half, structure=morphology.disk(2 * MARKS_K))
        half = up(ndi.binary_opening(half, structure=morphology.disk(MARKS_K)))
        grey_ |= half
        if local:
            over |= half
    # the area his strokes enclose (closed over TRACED_CLOSE, holes filled), where it is larger than TRACED_MIN: the
    # convex hull of his strokes took in the ribbon and the dress above the band, and their lines went
    closed = ndi.binary_fill_holes(ndi.binary_closing(whole, structure=morphology.disk(TRACED_CLOSE * UP)))
    lab, n = ndi.label(closed & ~ndi.binary_opening(whole, structure=morphology.disk(UP)))
    size = np.bincount(lab.ravel())
    big = size > TRACED_MIN * UP * UP
    big[0] = False
    traced = ndi.binary_fill_holes(ndi.binary_dilation(big[lab], iterations=UP) & closed)
    # (bits of skeleton shorter than 2 scan px, where a thick stroke forks, drew blobs)
    paths = [snap(q, contrast) for q in skeleton_paths(blue) if len(q) >= 2 * UP]
    lines_ = draw_paths(shape, paths, [PEN * UP] * len(paths))
    # (the grey stops at his drawn lines; less his raw strokes, it kept pinholes where his paint overlapped to full)
    return lines_, green, grey_ & ~lines_ & ~fills, traced, yellow, fills, spots, over & ~lines_


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


def pupils(shape):
    """The pupils (EYE_IRIS centres, EYE_PUPIL radius) on the work grid."""
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    m = np.zeros(shape, bool)
    for cx, cy, _ in EYE_IRIS:
        x, y = (cx - X0) * UP, (cy - Y0) * UP
        m |= (yy - y) ** 2 + (xx - x) ** 2 <= (EYE_PUPIL * UP) ** 2
    return m


def iphigenia(ink, fig, ws, wash, fills):
    """Iphigenia alone, cut along John's HOME_OUTLINE, written to HOME_OUT at the same pen."""
    line = np.asarray(Image.open(HOME_OUTLINE).convert("RGBA"))[..., 3] > 0
    inner = np.asarray(Image.fromarray(ndi.binary_fill_holes(line).astype(np.uint8) * 255).resize(
        (ink.shape[1], ink.shape[0]), Image.BILINEAR)) >= 128
    keep = inner
    # her body is her clay inside the cut and the lines bordering it (the frieze's body counts every line touching
    # clay: Pylades' fingers on the tablet, whose clay lies outside her cut, would come in with it). Her clay: the
    # areas lying mostly inside the cut; the altar's and the temple wall's, which the cut crosses beside her stole and
    # arm, lie mostly outside it
    n = ws.max() + 1
    hers = np.bincount(ws[inner], minlength=n) >= 0.5 * np.bincount(ws.ravel(), minlength=n)
    for x, y in HOME_CLAY:                # (a strip the lines now fill has no paper left to name)
        cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
        if (ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP] > 0).any():
            hers[at(ws, x, y)] = True
    # slivers the seal leaves unseeded (ws 0) are hers unless they touch an area not hers (taken whole, those outside
    # her outer lines left a rim of clay out to John's outline)
    lab, _ = ndi.label((ws == 0) & ~ink & inner)
    out = np.unique(ndi.maximum_filter(lab, size=3)[(ws > 0) & ~hers[ws]])
    hers[0] = False
    b = fig & inner & (hers[ws] | ((lab > 0) & ~np.isin(lab, out)))
    b = ndi.binary_fill_holes(b | (ink & keep & ndi.binary_dilation(b, iterations=2 * UP)))
    i = ink & keep & (ndi.distance_transform_edt(~b) <= NEAR * UP)
    lab, _ = ndi.label(i)
    i &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    info = lw.trace_svg(
        i, HOME_OUT, body=b, open_holes=~b, keep=b, weight="drawn", dots=pupils(i.shape) | (fills & keep & b),
        title="Iphigenia, priestess of Artemis, holding out a letter tablet and the temple key",
        desc="Line drawing after R. Jaene's 1849 lithograph of the Buckingham vase "
             "(Archäologische Zeitung 7, Taf. XII); cut out and retraced.")
    add_tone(HOME_OUT, [(wash & b, HATCH_OP)], info["box"])
    print(HOME_OUT, info)
    return info


def main(src, qa=None, dump=None):
    # (trace_svg's `keep` is the whole clay: its smoothing opening took the strips between lines 2-3 px apart, which
    # showed dark on the dark theme)
    g, gl, ink, contrast = lines(src)
    grid, wash, poly = checker(src, ink.shape)
    ink = (ink & ~poly) | grid
    walls = np.zeros_like(ink)
    for a, b in WALLS:
        for t in np.linspace(0, 1, 60):
            x, y = (np.array(a) + t * (np.array(b) - a) - (X0, Y0)) * UP
            walls[round(y), round(x)] = True
    walls = ndi.distance_transform_edt(~walls) <= PEN * UP / 2
    blue, green, mgrey, traced, yellow, fills, spots, over = marks(ink.shape, contrast)
    eye, box = eyes(ink.shape)            # the eyes are drawn by hand (EYE_*): John's strokes there are left out
    blue &= ~box
    ink = (ink & ~((ndi.distance_transform_edt(~blue) <= REPLACE * UP) & ~eye)) | blue
    # where he traced the whole area, his lines are the drawing there, with the plate's solid black (the waves)
    solid = ndi.binary_opening(gl < SOLID, structure=morphology.disk(SOLID_OPEN * UP))
    inside = ndi.binary_erosion(traced, iterations=UP)
    waves = np.zeros_like(ink)            # the waves inside the band's two edges (he traced the edges, not the waves)
    waves[sl(WAVE)] = True
    waves &= ndi.distance_transform_edt(~blue) > REPLACE * UP
    ink = (ink & ~(inside & ~waves)) | (blue & inside) | (solid & traced)
    ink &= ~yellow & ~over
    ink |= fills
    from scipy.interpolate import splev, splprep
    foot = []
    for pts in FOOT_LINES:
        tck, _ = splprep(((np.array(pts, float) - (X0, Y0)) * UP).T, s=0, k=3)
        x, y = splev(np.linspace(0, 1, 40 * len(pts)), tck)
        foot.append(np.c_[y, x])
    ink |= draw_paths(ink.shape, foot, [PEN * UP] * len(foot))
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
    fig |= traced | yellow
    ground &= ~(traced | yellow)
    wash |= mgrey
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
    # his green squiggles from LOCAL_FROM on: the paper under each, inside the lines
    near = (ndi.distance_transform_edt(~spots) <= LOCAL_R * UP) & ~ink
    lab, _ = ndi.label(near)
    spot = np.isin(lab, np.unique(lab[spots & near])) & (lab > 0)
    fig &= ~spot
    ground |= spot
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=ground, keep=fig & ~ground, weight="drawn", dots=pupils(ink.shape) | fills,
        title="Iphigenia in Tauris",
        desc="Line drawing after R. Jaene's 1849 lithograph of the Buckingham vase (Archäologische Zeitung 7, "
             "Taf. XII): Iphigenia handing her letter to Pylades before the temple, Orestes, Eros, Artemis and an "
             "attendant; retraced.")
    add_tone(OUT, [(wash, HATCH_OP)], info["box"])
    print(OUT, info)
    home = iphigenia(ink, fig, ws, wash, fills)
    if qa:  # optional: the drawings over their source, and as the dark theme shows them
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))
        q = Path(qa).with_name(Path(qa).stem + "_home.png")
        lw.qa_overlay(g, HOME_OUT, home["box"], q)
        lw.qa_dark(HOME_OUT, home["box"], q.with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
