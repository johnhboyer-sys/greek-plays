"""Eumenides: Orestes at Delphi, the whole of fig. 1 of Carl Bötticher's plate, Der Omphalos des Zeus zu Delphi
(Neunzehntes Programm zum Winckelmannsfest der Archäologischen Gesellschaft zu Berlin, Berlin, 1859), as scanned by
Heidelberg University Library (Public Domain Mark 1.0):
https://digi.ub.uni-heidelberg.de/iiif/2/bwpr1859%3A010a.jpg/full/full/0/default.jpg (1775 x 2341). The Munich copy
(MDZ bsb10221820, 2458 x 3192) is larger but softer; Heidelberg's is the sharper (John, 2026-10-12).
Bötticher (p. 15, note 66) copied the drawing from O. Jahn, Vasenbilder (Hamburg, 1839), Taf. I. The vase: the Black
Fury Painter's volute-krater, Naples, Museo Archeologico Nazionale 82270 (H 3249).

Made with PhotoCraft (John, 2026-10-07), as tools/rhesus.py: every image step runs in `photocraft-cli` (0.2.0) but the
levelling, a rotation by ANGLE in scipy (PhotoCraft has no free rotation). numpy only combines the masks PhotoCraft
made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing. A pen contour drawing on paper, no black ground (the vase's ground is black). John chose
(2026-10-12): the whole of fig. 1 (the two outer columns, the rules, the hanging objects, the ground line); the pen
lines traced at the plate's own weight (1.2 scan px); on the dark theme the figures' area filled as clay; the black
areas (the Fury, the hair, the stripes) solid, with a clay rim round them on the dark theme.

    python3 docs/redesign/drawings/tools/eumenides.py boetticher-1859-010a.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "eumenides.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# the scan leans: the top rule falls 8.5 px over 1470, the ground line 11 over 1200, the column flutes lean with
# them; turned back by their mean about the scan's centre (degrees, counter-clockwise)
ANGLE = 0.43
# crop in levelled scan px: the whole of fig. 1
X0, Y0, X1, Y1 = 236, 178, 1754, 892
UP = 4                                    # work at 4x the scan's px (the faces are 30-40 px tall)
BLUR = 0.4                                # scan px: the Gaussian before the line finder
CLOSE_R = 4                               # scan px: Maximum then Minimum, wider than a line (1-3 px)
LOW, HIGH = 22, 40                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 100                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 3, 0.5                     # a line's core: the darkest px within CORE_R scan px; half maximum
SMOOTH = 0.4                              # scan px: the line mask's Gaussian, cut at half
SPECK = 3                                 # scan px^2: smaller pieces of ink are specks of the print
SEAL = 4                                  # scan px: passages narrower than this do not join ground to figure
WEIGHT = 1.2 / (X1 - X0)                  # the plate's own line, 1.2 scan px (John, 2026-10-12)
RIM = 3                                   # scan px: the clay round the solid black on the dark theme (John chose a wider rim than 1.5, 2026-10-12)
SOLID_OPEN = 2                            # scan px: solid black is the ink an opening this wide leaves
# points on the ground (levelled scan px): the paper areas they fall in are vase ground; every other area the
# lines close is clay. The rules, the columns and the ground line close the whole field, so the field is listed too:
# the field round the Fury and between the Pythia and Apollo; by the Fury's snakes and head; behind the laver and
# below it; under the Pythia's hem; between her head and raised hand; between her shawl, her hem and Apollo; behind
# and between the tripod's legs; between Apollo's legs and under them; by the centre column's capital; the field
# round Orestes, by the column behind him, between his hair and the cloak; between the omphalos and the laurel and
# between the laurel's leaves; round Artemis, by her raised arm and between the spear and the right column;
# between her legs, the boots and the hounds
GROUND = [(727, 445), (454, 242), (456, 273), (481, 280), (508, 568), (506, 662), (476, 756), (712, 852),
          (648, 479), (712, 596), (746, 633), (714, 674), (734, 726), (742, 736), (806, 676), (782, 763),
          (779, 826), (804, 817), (838, 801), (836, 762), (920, 654), (883, 732), (902, 817), (788, 855),
          (1006, 251), (1054, 258), (1139, 349), (1022, 522), (1005, 501), (1164, 480), (1236, 600), (1215, 368),
          (1238, 402), (1249, 354), (1421, 346), (1503, 314), (1284, 590), (1492, 624), (1529, 496), (1541, 693),
          (1411, 721), (1440, 768), (1399, 779), (1335, 774), (1345, 721)]
# the rules along the top and the ground line run on the field: on the dark theme they get a clay rim (rows,
# levelled scan px)
RULES = [(178, 250), (866, 892)]
# the faces' eyes, brows, noses and mouths (boxes, levelled scan px): the faces are 30-40 px tall and their marks
# 1 px, so at one weight the eyes ran into blots. Inside these boxes the ink is found finer (FINE: less blur, a
# narrower core; no blur at all broke the lines and took in the paper's grain) and traced at its printed width
# (trace_svg's dots): the Pythia, Apollo, Orestes, Artemis. The main lines run MARGIN scan px into each box under
# the fine ones, so no seam shows where a box cuts a line or the hair
FEATURES = [(566, 438, 606, 480), (846, 336, 890, 378), (1088, 426, 1122, 466), (1340, 305, 1362, 345)]
FINE = dict(blur=0.25, half=0.55, smooth=0.35, core_r=2)
MARGIN = 3
FEATURE_SPECK = 2                         # scan px^2: smaller pieces inside a box are grain
# the laurel's leaves are narrower than the seal: inside these boxes the paper is sealed again at LEAF_SEAL, and
# its areas smaller than LEAF_MAX scan px^2 (not cut by the box) are clay (a closing of the ink rounded the leaves
# off and missed half): the laurel; the head of Artemis's spear; Apollo's latticed boot (its cells smaller than
# the seal went to the ground round it); Orestes's sword blade
LEAVES = [(1222, 252, 1296, 872), (1518, 590, 1556, 668), (830, 765, 905, 856), (1176, 440, 1204, 556)]
LEAF_SEAL, LEAF_MAX = 1.5, 250
# shafts too narrow for the seal (4-5 scan px between their edge lines): rough ends of each centre line (levelled
# scan px); the centre and width are fitted to the edge lines (`shaft`): Artemis's two spears from their butts to
# her hand, and the one shaft below her hand down to its head
SHAFTS = [((1438, 318), (1497, 466)), ((1447, 316), (1505, 466)), ((1503, 512), (1534, 596))]
SHAFT_REACH = 5
# the omphalos: its net's paper reaches the field through the gaps between the tassels, so the cone is outlined
# (levelled scan px, snapped to its printed outline by a least-cost path; straight across under the net's last
# row) and the paper inside is clay. The tassels below hang free, the field between them
OMPHALOS = [(1103, 585), (1150, 575), (1215, 575), (1235, 640), (1255, 700), (1268, 760), (1278, 805),
            (1282, 838), lw.STRAIGHT, (1056, 838), (1072, 760), (1085, 700), (1095, 640)]
# the net's hatching and rings (1 px strokes 3 px apart) ran together or broke at the house weight: inside the
# omphalos's outline and over its tassels (TASSELS, a box) the net is found by the faces' finer pass and traced at
# its printed width
TASSELS = (1050, 836, 1290, 872)
TASSEL_CLOSE = 1                           # scan px: each edge line is looked for this far from the rough centre
# specks of the print on the field: ink pieces under SPECK_MAX scan px^2 farther than NEAR scan px from the figures
SPECK_MAX, NEAR = 40, 3
# The Pythia alone, cut from this drawing for the Aeschylus home page (PYTHIA_OUT; John chose both uses,
# 2026-10-12). Her outline, Apollo's foot and the restored stripe are tools/pythia.py's (in unlevelled scan px,
# mapped through `level_pt`), with John's decisions there: both ends of her starred shawl kept, black folds and
# all; Apollo's raised back foot, which lies across her hem, erased and the hem left blank; the black stripe of her
# dress drawn on across the gap (a straight run of its last 40 px, tapering from 7.5 to 4.5 px)
PYTHIA_OUT = Path(__file__).resolve().parent.parent / "aeschylus-pythia.svg"
PYTHIA = [
    (483, 429), (494, 423), (505, 423), (515, 430), (517, 450), (521, 459), lw.STRAIGHT, (531, 457),
    (533, 440), (540, 428), (565, 420), (575, 414), (588, 416), (596, 423), (600, 428), (618, 438), (630, 446),
    (634, 451), lw.STRAIGHT,
    (641, 448), (638, 436), lw.STRAIGHT, (638, 409), lw.STRAIGHT, (684, 409), lw.STRAIGHT,
    (684, 430), (682, 445), (675, 465), (688, 483), (698, 498),
    (720, 496), (760, 498), (785, 496), (803, 506), (798, 521), (790, 527), (765, 530), (740, 530), (715, 530),
    (702, 535), (712, 542), (735, 548), (752, 553), (775, 570), (780, 582), (768, 594), (752, 612), (742, 617),
    (728, 609), (712, 600), (705, 608),
    (724, 634), (742, 656), (743, 690), (744, 725), (743, 760), (742, 777),
    (772, 786), (773, 801), (766, 815), (766, 840), (764, 864), (751, 874), (737, 860), (733, 845),
    (715, 841), (675, 838), (640, 852), lw.STRAIGHT, (600, 862), lw.STRAIGHT, (560, 865), (553, 862),
    (520, 865), (495, 864),
    (487, 854), (497, 844), (510, 831), (505, 801), (505, 761), (503, 735), (506, 708), (514, 682), (535, 671),
    (540, 631), (537, 590), (527, 560), (510, 551), (494, 546), (476, 540), (463, 530), (459, 515), (461, 498),
    (467, 480), (479, 460),
]
APOLLO_FOOT = [(696, 782), (740, 776), (772, 782), (775, 806), (764, 816), (735, 814), (700, 806), (692, 795)]
RESTORED = [((737, 777), (757, 819), 7.5, 4.5)]
PYTHIA_NEAR = 2                           # scan px: her ink lies within this of her body
SCAN_C = (887.0, 1170.0)                  # the scan's centre (px), about which `level` turns it

# John's corrections on pass 1 (2026-10-12), marked in PhotoCraft on the plate at MARKS_K x its levelled scan px over
# the crop (both his layers, the copy on top): blue is ink, green is paper; the ink is pass 1's less his green, plus
# his blue (read literally: in Orestes's and the Pythia's eyes he redrew the eye in blue and cleared the old blot
# with green; elsewhere blue joins breaks and adds faint lines the finder missed)
MARKS_FILES = [Path(__file__).with_name("eumenides_marks_1.png")]
MARKS_K = 2.5


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def level(src, out):
    """The scan turned by ANGLE about its centre (scipy, bicubic), saved as PNG."""
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    r = np.stack([ndi.rotate(a[..., k], -ANGLE, reshape=False, order=3, mode="nearest") for k in range(3)], -1)
    Image.fromarray(np.clip(r, 0, 255).round().astype(np.uint8)).save(out)


def masks(src, box=None, blur=BLUR, half=HALF, smooth=SMOOTH, core_r=CORE_R, speck=SPECK):
    """The plate's ink at UP (work px) in box (levelled scan px; the crop by default), and the plate in grey."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        level(src, t / "src.png")
        w, h = x1 - x0, y1 - y0
        pc(t / "src.png", t / "up.png",
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
        ink = apply_hysteresis_threshold(np.where(hm, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": smooth * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > speck * UP * UP)[lab]
    return g, gl, ink


def areas(ink, seal=SEAL):
    """The paper the ink closes off, sealed at seal (scan px): watershed labels (0 on ink)."""
    from skimage.segmentation import watershed
    paper = ~ink
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(seal * UP)))
    return watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)


def at(ws, x, y):
    """The area at a point (levelled scan px), the commonest label within 2 scan px if it lands on ink."""
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP]
    v, n = np.unique(win[win > 0], return_counts=True)
    assert len(v), f"no paper near {(x, y)}"
    return v[np.argmax(n)]


def sl(box):
    """A box (levelled scan px) as a slice of the work arrays."""
    x0, y0, x1, y1 = box
    return np.s_[(y0 - Y0) * UP:(y1 - Y0) * UP, (x0 - X0) * UP:(x1 - X0) * UP]


def shaft(gl, a, b):
    """A shaft's band (bool, work px), as tools/rhesus.py: the paper between its two edge lines, along the centre
    line fitted to the midpoints between them (read across the shaft every 2 scan px, the darkest px on each side of
    the rough centre within SHAFT_REACH), out to the edge lines' centres. Returns the band, its half-width and the
    fit's rms (scan px)."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a))
    n = np.array([-u[1], u[0]])
    mids, gaps = [], []
    for s in np.arange(0, np.hypot(*(b - a)), 2):
        p = a + s * u
        o = np.arange(-SHAFT_REACH, SHAFT_REACH + 0.01, 0.25)
        q = (p[None] + o[:, None] * n[None] - (X0, Y0)) * UP
        v = ndi.map_coordinates(gl, [q[:, 1], q[:, 0]], order=1)
        lo, hi = o < 0, o > 0
        i, j = np.argmin(np.where(lo, v, 1e9)), np.argmin(np.where(hi, v, 1e9))
        if v[i] < 170 and v[j] < 170 and 2 < o[j] - o[i] < 9:
            mids.append(p + (o[i] + o[j]) / 2 * n)
            gaps.append(o[j] - o[i])
    mids = np.array(mids)
    t = (mids - a) @ u
    f = np.polyfit(t, (mids - a) @ n, 1)
    res = (mids - a) @ n - np.polyval(f, t)
    hw = np.median(gaps) / 2
    band = np.zeros(gl.shape, bool)
    (cx0, cy0), (cx1, cy1) = [(np.floor((np.minimum(a, b) - 10 - (X0, Y0)) * UP)).astype(int).clip(0),
                              (np.ceil((np.maximum(a, b) + 10 - (X0, Y0)) * UP)).astype(int)]
    yy, xx = np.mgrid[cy0:cy1, cx0:cx1]
    px, py = (xx + 0.5) / UP + X0 - a[0], (yy + 0.5) / UP + Y0 - a[1]
    along_, across = px * u[0] + py * u[1], px * n[0] + py * n[1]
    band[cy0:cy1, cx0:cx1] = ((along_ >= 0) & (along_ <= np.hypot(*(b - a))) &
                              (np.abs(across - np.polyval(f, along_)) <= hw))
    return band, hw, float(np.sqrt(np.mean(res ** 2)))


def outline(gl, pts):
    """The area inside a closed outline through pts (levelled scan px), snapped to the plate's dark lines by
    linework.livewire, as a mask (work px)."""
    xy = np.array([p for p in pts if p != lw.STRAIGHT], float)
    x0, y0 = (xy.min(0) - 10).astype(int)
    x1, y1 = (xy.max(0) + 10).astype(int)
    b = sl((x0, y0, x1, y1))
    cost = 1 + 30 * np.clip(gl[b] / 255, 0, 1) ** 2
    work = [p if p == lw.STRAIGHT else ((p[0] - x0) * UP, (p[1] - y0) * UP) for p in pts]
    path = lw.livewire(cost, work, closed=True)
    m = np.zeros(gl.shape, bool)
    m[b] = lw.polygon_mask(cost.shape, path)
    return m


def figure(ink, ws, gl):
    """The figures' area: every paper area but the ground (GROUND, and the areas reaching the crop's edge), the
    laurel's leaves, and the ink touching them."""
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    ground = np.isin(ws, np.r_[out[out > 0], [at(ws, x, y) for x, y in GROUND]])
    for box in LEAVES:
        b = sl(box)
        w = areas(ink[b], LEAF_SEAL)
        small = np.bincount(w.ravel()) <= LEAF_MAX * UP * UP
        small[0] = False
        small[np.unique(np.r_[w[0], w[-1], w[:, 0], w[:, -1]])] = False
        ground[b] &= ~small[w]
    ground &= ~outline(gl, OMPHALOS)
    bands = np.zeros_like(ink)
    for a, b in SHAFTS:
        band, hw, rms = shaft(gl, a, b)
        print("shaft", a, b, "half-width", round(hw, 2), "rms", round(rms, 2))
        ground &= ~band
        bands |= band
    # paper the seal leaves without a seed (slivers the lines close: a sword's blade, a boot's lattice cells) is
    # clay, unless it reaches the crop's edge
    lab, _ = ndi.label((ws == 0) & ~ink)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    clay = ((ws > 0) | ((lab > 0) & ~np.isin(lab, edge))) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    # a shaft's band whole is clay, the lines drawn over it: the paper between its lines alone broke into bits
    return (fig & ~ground) | bands, ground


def level_pt(x, y):
    """A point in the scan as `level` moves it (unlevelled -> levelled scan px)."""
    a = np.radians(ANGLE)
    cx, cy = SCAN_C
    return (cx + np.cos(a) * (x - cx) - np.sin(a) * (y - cy), cy + np.sin(a) * (x - cx) + np.cos(a) * (y - cy))


def pythia(ink, dots, body, gl):
    """The Pythia alone, cut along PYTHIA by a least-cost path on the drawing's ink, written to PYTHIA_OUT at the
    same printed line (1.2 scan px)."""
    from skimage import draw
    w = lambda p: p if p == lw.STRAIGHT else (((level_pt(*p)[0] - X0) * UP), ((level_pt(*p)[1] - Y0) * UP))
    lines = ink | dots
    soft = ndi.gaussian_filter(lines.astype(np.float32), 1.5 * UP / 4)
    cost = 1 + 30 * (1 - np.clip(soft * 2, 0, 1))
    path, on_straight = lw.livewire(cost, [w(p) for p in PYTHIA], closed=True, flags=True)
    keep, inner, wall = lw.cut_masks(ink.shape, path, on_straight, rim=2 * UP)
    foot = lw.polygon_mask(ink.shape, np.array([w(p) for p in APOLLO_FOOT], float))
    cut = lambda m: m & keep & ~foot
    i, d = cut(ink), cut(dots)
    for a, b, wa, wb in RESTORED:
        (xa, ya), (xb, yb) = w(a), w(b)
        for t in np.linspace(0, 1, int(np.hypot(xb - xa, yb - ya)) + 1):
            rr, cc = draw.disk((ya + t * (yb - ya), xa + t * (xb - xa)), (wa + t * (wb - wa)) * UP / 2, shape=i.shape)
            i[rr, cc] = True
    # her hem behind the erased foot is hers: the body there filled
    b = (body & inner & ~lines) | (foot & ndi.binary_erosion(inner, iterations=UP))
    # her body is her clay inside the cut and the lines bordering it (the whole plate's body counts every line
    # touching clay: Apollo's shin line, whose clay lies outside her cut, came in with it)
    b = ndi.binary_fill_holes(b | (lines & ndi.binary_dilation(b, iterations=2 * UP)))
    # the outline runs down the front of Apollo's thigh, but the field between him and her is ground here: only ink
    # on or beside her body stays (his leg's lines go), and pieces that leaves smaller than a speck
    near = ndi.distance_transform_edt(~b) <= PYTHIA_NEAR * UP
    i &= near
    d &= near
    lab, _ = ndi.label(i)
    i &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    ys, xs = np.nonzero(i | d)
    longer = max(ys.max() - ys.min(), xs.max() - xs.min()) + 9
    info = lw.trace_svg(
        i, PYTHIA_OUT, body=b, open_holes=~b, dots=d, weight=1.2 * UP / longer,
        title="The Pythia, Apollo's priestess, fleeing in terror with her hands raised",
        desc="Line drawing after Carl Bötticher's 1859 drawing of an Apulian red-figure krater "
             "showing Orestes at Delphi (Naples); cut out and retraced.")
    print(PYTHIA_OUT, info)
    return info


def marks(shape):
    """John's marks on the work grid: (blue, green) bool masks, each file applied in order (a later file's green
    clears an earlier blue)."""
    blue, green = np.zeros(shape, bool), np.zeros(shape, bool)
    for f in MARKS_FILES:
        a = np.asarray(Image.open(f).convert("RGBA")).astype(np.float32)
        r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3] / 255
        size = (shape[1], shape[0])
        assert abs(a.shape[1] * UP / MARKS_K - shape[1]) <= UP and abs(a.shape[0] * UP / MARKS_K - shape[0]) <= UP
        up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(size, Image.BILINEAR)) >= 128
        bl = up(al * ((b > r + 40) & (b > g + 20)))
        gr = up(al * ((g > r + 40) & (g > b + 20)))
        blue = (blue & ~gr) | bl
        green = (green & ~bl) | gr
    return blue, green


def add_rim(rim, info):
    """The clay rim round the solid black, added to the body path after tracing: trace_svg takes clay off
    where it lies outside a line and no wider than one, which is what this rim is. Traced on the body's grid."""
    x0, y0, x1, y1 = info["box"]
    d, _ = lw.potrace_d(lw.resample_ink(rim[y0:y1, x0:x1], lw.TRACE_H), turdsize=0, alphamax=1.2)
    s = OUT.read_text()
    key = '<path class="body" fill="none" stroke="none" d="'
    assert key in s
    OUT.write_text(s.replace(key, key + d + " ", 1))


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    # the faces' marks, found finer and traced at their printed width
    dots = np.zeros_like(ink)
    for box in FEATURES:
        _, _, f = masks(src, box, speck=FEATURE_SPECK, **FINE)
        dots[sl(box)] = f
    net = outline(gl, OMPHALOS)
    net[sl(TASSELS)] = True
    xy = np.array([p for p in OMPHALOS if p != lw.STRAIGHT])
    nbox = (*(xy.min(0) - 4).astype(int).tolist(), *(np.maximum(xy.max(0), TASSELS[2:]) + 4).astype(int).tolist())
    _, _, f = masks(src, nbox, speck=FEATURE_SPECK, **FINE)
    m = np.zeros_like(ink)
    m[sl(nbox)] = f
    dots |= m & net
    blue, green = marks(ink.shape)
    fine = np.zeros_like(ink)
    for x0, y0, x1, y1 in FEATURES:
        fine[sl((x0 + MARGIN, y0 + MARGIN, x1 - MARGIN, y1 - MARGIN))] = True
    fine |= ndi.binary_erosion(net, iterations=MARGIN * UP)
    ink = (ink & ~green) | blue
    dots = (dots & ~green) | (blue & fine)
    ws = areas(ink)
    fig, ground = figure(ink, ws, gl)
    # specks on the field
    lab, n = ndi.label(ink)
    size = np.bincount(lab.ravel()) / UP / UP
    near = np.zeros(n + 1, bool)
    near[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    drop = (size < SPECK_MAX) & ~near
    drop[0] = False
    ink &= ~drop[lab]
    # (a speck by Apollo's nose lay on the field; the net's tassels hang on the field and stay: John, pass 2)
    dots &= ndi.binary_dilation(fig, iterations=UP) | net
    ink &= ~fine
    # the tassels hang on the field: each is clay inside its own lines (the net's marks closed over TASSEL_CLOSE
    # scan px and filled), or a pale one shows the ground through it on the dark theme (John, pass 2)
    t = sl(TASSELS)
    c = ndi.binary_closing(dots[t] | ink[t], structure=morphology.disk(TASSEL_CLOSE * UP))
    fig[t] |= ndi.binary_fill_holes(c)
    solid = ndi.binary_opening(ink, structure=morphology.disk(SOLID_OPEN * UP))
    rim = (ndi.distance_transform_edt(~solid) <= RIM * UP) & ~ink
    body = fig | solid
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig, body=body)
    rules = np.zeros_like(ink)
    for a, b in RULES:
        rules[(a - Y0) * UP:(b - Y0) * UP] = True
    info = lw.trace_svg(
        ink, OUT, body=body, open_holes=~body, rim_lines=rules & ink & ~fig, dots=dots, weight=WEIGHT,
        title="Orestes at Delphi",
        desc="Line drawing after Carl Bötticher's 1859 drawing of an Apulian red-figure volute-krater (Naples): "
             "the Pythia fleeing, the Fury, Apollo, Orestes at the omphalos, Artemis with her hounds; retraced.")
    add_rim(rim, info)
    print(OUT, info)
    pythia(ink, dots, body, gl)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
