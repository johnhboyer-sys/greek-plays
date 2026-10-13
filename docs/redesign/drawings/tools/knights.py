"""Knights (Aristophanes): two slaves haul an old master up the steps of a stage, one pulling him by the head
from the steps, the other pushing from behind; the stage's post and roof at the left, a patterned bundle on it.
From Lenormant and de Witte, Élite des monuments céramographiques II (Paris, 1857), pl. XCIV (lith. Bineteau,
A. Rey sc.), as scanned from the Getty Research Institute's copy on the Internet Archive:
https://archive.org/details/gri_33125009347440/page/n756/mode/1up (IIIF, turned 90 degrees: 3000 x 2245).
The vase: an Apulian red-figure bell-krater, British Museum F 151 (the "Chiron vase"); the old man is named
XIPΩN (Chiron) on it. The vase names no play: the drawing stands for the opening of Knights (an old master and
his two slaves) only as a theme. Readings differ: the Élite's, a parody of Apollo's arrival at Delphi with a
blind Chiron; Heydemann (JdI 1, 1886) and Bieber, a sick Chiron's journey with his slaves, one named Xanthias.
What it holds (John, 2026-10-13): the three actors, the stage and the steps: "leave out the youth", "and no
nymphs"; the post, brace and roof, the bundle with the shape behind it, and the curved band under the stage
with its hook stay; the painted names (ΘΙΑΣ, XIPΩN) go.

Made with PhotoCraft (John, 2026-10-07), as tools/iphigenia_aulis.py: every image step runs in `photocraft-cli`
(0.2.0). The panel is squared (`level`, numpy and scipy: geometry, as tools/ion.py); numpy only combines the
masks PhotoCraft made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing, as for Iphigenia at Aulis, with these differences:
  - The scan comes upright: no turn. Its panel, photographed a little askew, is mapped to a rectangle (ion.py's
    homography from the four edges, fitted on their straight stretches).
  - The scene is every clay area larger than FIG_MIN but the Nymphs and the line that frames them (NYMPHS, by
    each area's centre) and the painted names (NAMES, areas wholly inside). The youth at the right is cut off
    by the crop's right edge (X1, in the black between his robe and the pushing slave's heel). The roof and the
    post reach the panel's top and left: no edge rule.
  - The figures stand on the panel's lower black band, which is the cut (BOTTOM). Under the youth a clay strip
    lies on the band and runs under the slave's heel: cut off below the heel's sole (STRIP).
  - The added white (the old man's hair, brow, moustache and beard; the pushing slave's hair and beard) as
    Wealth's: `white` paths, outlined on the ground by a `day` path the dark theme hides.

    python3 docs/redesign/drawings/tools/knights.py chiron-elite-II-XCIV.jpg [qa.png]
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
from skimage import measure, morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import trojan_women_menelaus as tw  # noqa: E402
from trojan_women_menelaus import join_breaks  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "knights.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# The panel's edges in the scan (px): each a line fitted to the first dark px going in from the paper, on a
# straight stretch (clear of "T. II." and "PL. XCIV." above it and the signatures below it); each search
# starts on the paper (the binding shows at the scan's left, right and bottom). `level` maps the corners to a
# rectangle MARGIN px inside the levelled frame
EDGE_DARK = 90
STRETCH = dict(top=(600, 2300), bottom=(600, 2400), left=(300, 1500), right=(300, 1500))
FROM = dict(top=0, bottom=300, left=150, right=150)
MARGIN = 20
# crop in levelled px: from the panel's left and top edges to the black between the pushing slave's heel and
# the youth's robe, down to a little past the panel's lower edge (BOTTOM: MARGIN + the panel's height)
X0, Y0, X1, Y1 = 22, 22, 2082, 1424
BOTTOM = 1420
# the clay strip the youth stands on, lying on the band under the slave's heel: below the heel's sole line
# (row 1407) from here to the crop's right edge is outside
STRIP = (2000, 1408)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
# light flecks of the print in the pockets of ground: the hole fill makes them clay islands, drawn as dots on the
# black; clay pieces under SPECK plate px go once the figures are cut (Electra, SPECK)
SPECK = 30
# the Nymphs and the line framing them (levelled px): clay areas whose centre lies inside go
NYMPHS = [(1150, 0), (2100, 0), (2100, 690), (1700, 690), (1500, 560), (1400, 300), (1150, 100)]
# the painted names (boxes, levelled px): clay areas wholly inside go
NAMES = [(950, 120, 1110, 160), (1170, 285, 1370, 330)]
# pockets of ground the figures close in (a point in each, levelled px): under the stage inside the festoon, between
# the old man's stick and his face, the slave's arm and the ramp, between the old man's legs, between the pushing
# slave's legs (at the ground and between his thighs), between the post, its brace and the roof, and between the
# climbing slave's legs, the stick and the ramp (it reached the open ground only through the hem band, now walled)
POCKETS = [(473, 1147), (1129, 999), (1290, 1020), (1920, 1355), (1742, 1191), (231, 267), (1006, 888)]
WALL_W = 1.5
LINE_DARK = 100
LINE_MIN = 1.5
# faint lines (toes, fingers, folds, the ramp's lines: grey 100-150 on clay 200, about a plate px wide): the main
# finder's blur broke them into dashes or lost them (John, 2026-10-13: "don't ignore fainter lines (like on toes and
# fingers"). Found at less blur (FAINT_BLUR plate px) as the plate darker than its closing over FAINT_CLOSE plate px,
# by hysteresis (FAINT_LOW, FAINT_HIGH); pieces of centre line at least FAINT_LEN plate px long, lying at least
# FAINT_EDGE plate px inside the figure (the print's darker band along an outline passes for a line), drawn LINE_MIN
# wide along their centres
FAINT_BLUR, FAINT_CLOSE, FAINT_LOW, FAINT_HIGH, FAINT_LEN, FAINT_EDGE = 0.35, 5, 18, 35, 5, 2.5
# and fainter still (the finger divisions on the pushing slave's hand, the old man's toes, a fold: contrast 26-38): at
# FAINT2_LOW/HIGH, a stroke kept where it runs FAINT2_LEN plate px or more farther than 1.5 plate px from the lines
# already found (shorter ones were blobs of the print), with its centre line run back to them
FAINT2_LOW, FAINT2_HIGH, FAINT2_LEN = 12, 24, 5
# breaks left in the lines where the plate still prints a faint line (the ramp's long lines, folds, toes; John,
# 2026-10-13: "don't have broken ink lines"): centre-line ends within JF_MAX plate px that point at each other
# (within JF_ANGLE degrees, over their last JF_RUN plate px), and free ends that point at a line within JF_REACH
# plate px, joined straight where the fine contrast along the gap has a median of JF_C or more and nowhere falls
# under JF_LOW. Two rounds. Over the 44 joins of the first round sheeted on the plate, none crossed open clay
JF_RUN, JF_MAX, JF_ANGLE, JF_C, JF_LOW, JF_REACH = 4, 14, 30, 10, 4, 5
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
HANDS = []
HAND_EDGE = 1.2
FACES = []
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
FACE_LINE = 1.0
EYE_BOX = None
EYE_LINES = []
EYE_PUPIL = None
FINE = []
# bands of solid paint that touch the ground and read as ground (a point in each, levelled px; the band is the thin
# part of the ground there, narrower than 2 BAND_R + 1 plate px; sheeted on the plate, as Iphigenia at Aulis): the
# climbing slave's mask's beard and mouth; the old man's himation band and the black inside his hand at the hip (the
# climbing slave's tunic hem and the pushing slave's tunic stripe are walled: WALLS)
PAINT = [(976, 377), (1275, 929), (1196, 908)]
BAND_R = 8
# bands of paint that meet the ground where they are wider than the band test allows, walled along the clay's edge
# (levelled px; Phoenician Women's girdle): the climbing slave's tunic hem at its left end and at its right end
# (along the tips of the tunic and the layers under it); the pushing slave's tunic stripe where it runs out between
# the fold's tip and the layer under it
WALLS = [[(683.5, 652), (682.5, 668), (682, 684)],
         [(953.5, 673), (950.5, 683), (947.5, 692), (942, 699), (938, 705)],
         [(1901, 1093), (1896, 1102), (1892, 1112)]]
MARKS_FILES = []
WEIGHT = "own"
DROP = []
OPEN = []
# The added white: lighter than WHITE_L (grey, lightly smoothed) and not red (red less blue under WHITE_RB: the
# clay reads 80-105, the white 60-70), closed over its curl lines (WHITE_CLOSE plate px), on the figure (Wealth)
WHITE_L, WHITE_RB, WHITE_CLOSE = 180, 80, 1.5
WHITE_FILL = "#f7f3ea"
# only round the two white heads (levelled px): the old man's, the pushing slave's (the festoon's thin cord at the
# left prints pale enough to pass)
WHITE_BOXES = [(1060, 430, 1340, 750), (1420, 670, 1660, 850)]
DOT_DARK, DOT_W, DOT_MAX = 60, 7, 30
MARK_W, MARK_MAX = 10, 70
DOT_TAIL = 1.8
JOIN_SMALL, JOIN_DOT = 160, 14
assert tw.UP == UP


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def fit_edge(g, name):
    """The panel's edge `name` as a line: (a, b) with y = a + b x (top, bottom) or x = a + b y (left, right),
    fitted to the first px darker than EDGE_DARK going in from the paper, outliers dropped (ion.py)."""
    lo, hi = STRETCH[name]
    s = np.arange(lo, hi, 2)
    H, W = g.shape
    prof = g[:, s].T if name in ('top', 'bottom') else g[s, :]
    if name in ('bottom', 'right'):
        prof = prof[:, ::-1]
    prof = prof[:, FROM[name]:]
    d = np.argmax(prof < EDGE_DARK, axis=1).astype(float) + FROM[name]
    if name == 'bottom':
        d = H - 1 - d
    elif name == 'right':
        d = W - 1 - d
    ok = np.ones(len(s), bool)
    for _ in range(6):
        f = np.polyfit(s[ok], d[ok], 1)
        ok = np.abs(d - np.polyval(f, s)) < 1.5
    return f[1], f[0]


def level(g_rgb):
    """The scan with its panel mapped to a rectangle (a homography from the four fitted corners), MARGIN px of
    the frame round it (ion.py). Returns the levelled RGB image and the panel's size."""
    g = ndi.gaussian_filter(np.asarray(Image.fromarray(g_rgb).convert('L'), np.float32), 1.5)
    e = {k: fit_edge(g, k) for k in STRETCH}

    def corner(h, v):   # y = a + b x meets x = c + d y
        (a, b), (c, d) = e[h], e[v]
        y = (a + b * c) / (1 - b * d)
        return c + d * y, y
    C = np.array([corner('top', 'left'), corner('top', 'right'), corner('bottom', 'right'), corner('bottom', 'left')])
    Wp = round((np.hypot(*(C[1] - C[0])) + np.hypot(*(C[2] - C[3]))) / 2)
    Hp = round((np.hypot(*(C[3] - C[0])) + np.hypot(*(C[2] - C[1]))) / 2)
    D = np.array([(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)], float) + MARGIN
    A = []
    for (x, y), (u, v) in zip(D, C):   # homography from the levelled frame to the scan
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y, -u], [0, 0, 0, x, y, 1, -v * x, -v * y, -v]]
    h = np.linalg.svd(np.array(A))[2][-1].reshape(3, 3)
    yy, xx = np.mgrid[0:Hp + 2 * MARGIN, 0:Wp + 2 * MARGIN].astype(float)
    w = h[2, 0] * xx + h[2, 1] * yy + h[2, 2]
    X = (h[0, 0] * xx + h[0, 1] * yy + h[0, 2]) / w
    Y = (h[1, 0] * xx + h[1, 1] * yy + h[1, 2]) / w
    out = np.stack([ndi.map_coordinates(g_rgb[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8), (Wp, Hp)


def boxes(shape, bxs):
    m = np.zeros(shape, bool)
    for box in bxs:
        bx0, by0, bx1, by1 = [max((v - o) * UP, 0) for v, o in zip(box, (X0, Y0, X0, Y0))]
        m[by0:by1, bx0:bx1] = True
    return m


def main(src, qa=None, dump=None):
    lev, (_, Hp) = level(np.asarray(Image.open(src).convert('RGB')))
    assert MARGIN + Hp == BOTTOM, Hp
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(lev).save(t / "lev.png")
        del lev
        w, h = X1 - X0, Y1 - Y0
        pc(t / "lev.png", t / "upc.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "upc.png", t / "up.png", ("image.mode.grayscale", None))
        pc(t / "upc.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = (9 * UP) // 2
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        rf = (FAINT_CLOSE * UP) // 2
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": FAINT_BLUR * UP}))
        pc(t / "gf.png", t / "closedf.png", ("filter.other.maximum", {"radius": rf, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": rf, "preserve": "squareness"}))
        faint_c = grey(t / "closedf.png") - grey(t / "gf.png")
        g, gl, closed, rb = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "rb.png")
        gs = grey(t / "gs.png")
        dark0 = grey(t / "dark.png") < 128
        core = grey(t / "core.png") < 128
        fine = grey(t / "fine.png") < 128
        pc(t / "up.png", t / "facedark.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": FACE_DARK}))
        face_dark = grey(t / "facedark.png") < 128
        pc(t / "up.png", t / "facefaint.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": FACE_FAINT}))
        face_faint = grey(t / "facefaint.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    del xx, yy

    # outside: below the panel's lower edge, and the strip under the youth below the heel's sole
    outside = (py > BOTTOM + 0.5) | ((px > STRIP[0]) & (py > STRIP[1] + 0.5))

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP))
    hand = boxes(g.shape, HANDS)
    finebox = boxes(g.shape, HANDS + FINE)
    dark = np.where(finebox, ndi.binary_opening(fine, structure=morphology.disk(1)), dark)
    dark &= ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    if PAINT:
        gp = ground[UP // 2::UP, UP // 2::UP]
        thin = gp & ~ndi.binary_opening(gp, structure=morphology.disk(BAND_R))
        tl, _ = ndi.label(thin)
        ks = [tl[round(y - Y0), round(x - X0)] for x, y in PAINT]
        assert all(ks), [p for p, k in zip(PAINT, ks) if not k]
        band = np.repeat(np.repeat(np.isin(tl, ks), UP, 0), UP, 1)[:H, :W]
        ground &= ~ndi.binary_dilation(band, iterations=UP)
        lab, _ = ndi.label(ground)
        size = np.bincount(lab.ravel())
        size[0] = 0
        keep = size > AUTO_GROUND * UP * UP
        for x, y in POCKETS:
            keep[lab[round((y - Y0) * UP), round((x - X0) * UP)]] = True
        keep[0] = False
        ground = keep[lab]
    paint = dark & ~ground

    lab, n = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    keep = sz > FIG_MIN * UP * UP
    # (not the Nymphs and their line, by each area's centre; not the names, wholly inside their boxes)
    cy, cx = (np.array(c) for c in zip(*ndi.center_of_mass(np.ones_like(lab), lab, range(1, n + 1))))
    nym = measure.points_in_poly(np.c_[cx / UP + X0, cy / UP + Y0], np.array(NYMPHS, float))
    keep[1:] &= ~nym
    names = boxes(g.shape, NAMES)
    outn = np.bincount(lab[~names], minlength=n + 1) == 0
    keep &= ~outn
    keep[0] = False
    fig = keep[lab]
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)
    del ridge
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) >= SPECK * UP * UP)[lab]

    # the added white: light and not red, closed over its curl lines, on the figure (Wealth)
    white = ndi.binary_closing((gs > WHITE_L) & (rb < WHITE_RB), structure=morphology.disk(round(WHITE_CLOSE * UP)))
    white = ndi.binary_fill_holes(white) & fig & boxes(g.shape, WHITE_BOXES)
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > FIG_MIN * UP * UP)[lab]

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    _join = join_breaks(lines, closed - gl, ndi.distance_transform_edt(fig)) & fig
    lab, n = ndi.label(lines)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    small = sz < JOIN_SMALL * UP * UP
    dot = small.copy()
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        dot[i] &= max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= JOIN_DOT * UP
    dot[0] = False
    jl, nj = ndi.label(_join & ~lines)
    for i, sl in enumerate(ndi.find_objects(jl), 1):
        sl = tuple(slice(max(a.start - 2, 0), a.stop + 2) for a in sl)
        piece = ndi.binary_dilation(jl[sl] == i, iterations=2)
        ends = np.unique(lab[sl][piece])
        ends = ends[ends > 0]
        if len(ends) and (small[ends].all() or dot[ends].any()):
            _join[sl] &= ~piece
    lines |= _join
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_MIN * UP / 2) & fig
    sk = morphology.skeletonize(tw.apply_hysteresis_threshold(faint_c, FAINT_LOW, FAINT_HIGH)
                                & (ndi.distance_transform_edt(fig) >= FAINT_EDGE * UP))
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    sk &= (np.bincount(lab.ravel()) >= FAINT_LEN * UP)[lab]
    _faint = (ndi.distance_transform_edt(~sk) <= LINE_MIN * UP / 2) & fig
    lines |= _faint
    sk = morphology.skeletonize(tw.apply_hysteresis_threshold(faint_c, FAINT2_LOW, FAINT2_HIGH)
                                & (ndi.distance_transform_edt(fig) >= FAINT_EDGE * UP))
    far = sk & (ndi.distance_transform_edt(~lines) > 1.5 * UP)
    lab, _ = ndi.label(far, structure=np.ones((3, 3)))
    far &= (np.bincount(lab.ravel()) >= FAINT2_LEN * UP)[lab]
    sk &= ndi.binary_dilation(far, iterations=2 * UP)
    _faint2 = (ndi.distance_transform_edt(~sk) <= LINE_MIN * UP / 2) & fig
    lines |= _faint2
    _faint |= _faint2
    del sk, far
    face = boxes(g.shape, FACES)
    lids = ndi.binary_closing(face_faint & face, structure=morphology.disk(FACE_CLOSE)) & fig
    lab, _ = ndi.label(lids)
    lids &= (np.bincount(lab.ravel()) > 12)[lab]
    lids = ndi.distance_transform_edt(~morphology.skeletonize(lids)) <= FACE_LINE * UP / 2
    lines = np.where(face, (face_dark | lids) & fig, lines)
    lab, _ = ndi.label(lines & face)
    eyes = (lines & face & ~np.isin(lab, np.unique(lab[face & ~ndi.binary_erosion(face)])))
    eyebox = boxes(g.shape, [EYE_BOX] if EYE_BOX else [])
    eyes &= ~eyebox
    for pts in EYE_LINES:
        eyes |= along(g.shape, polyline(pts), FACE_LINE)
    if EYE_PUPIL:
        ex, ey, er = EYE_PUPIL
        eyes |= np.hypot(px - ex, py - ey) <= er
    lines &= ~eyebox
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the outline: EDGE_OUT plate px wide on the black ground outside the clay, not on the clay (John on
    # Ion, 2026-10-09), so every clay part keeps its full width
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & ~outside & (dt <= EDGE_OUT * UP)
    edge = np.where(hand, ~fig & ~outside & (dt <= HAND_EDGE * UP), edge)
    del dt
    _jf = np.zeros_like(lines)
    for _ in range(2):
        _jf |= join_faint(lines | solid | edge | _jf, faint_c, fig) & fig
    lines |= _jf
    del faint_c
    # the ground nearer the white than the clay: its outline is the `day` path (Wealth)
    day = ndi.distance_transform_edt(~white) < ndi.distance_transform_edt(~(fig & ~white))
    lab, n = ndi.label(face_faint & fig)
    sz = np.bincount(lab.ravel())
    dark_core = np.r_[False, np.array(ndi.minimum(g, lab, range(1, n + 1))) < DOT_DARK]
    small = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        small[i] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= DOT_W * UP
    dots = ((sz < DOT_MAX * UP * UP) & small & dark_core)[lab] & ~face | eyes
    lines &= ~(~_core & (ndi.distance_transform_edt(~dots) <= DOT_TAIL * UP) & ~dots)
    ink = lines | solid | edge | dots
    lab, _ = ndi.label(ink)
    ink &= np.where(face, (np.bincount(lab.ravel()) > 3 * UP * UP)[lab], (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]) | dots
    lab, n = ndi.label(ink)
    sz = np.bincount(lab.ravel())
    small = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        small[i] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= MARK_W * UP
    marks = ((sz < MARK_MAX * UP * UP) & small)[lab] & ink
    own = ndi.binary_dilation(marks, iterations=UP) & face_dark & fig
    lab, n = ndi.label(marks)
    held = np.bincount(lab[own], minlength=n + 1) > 4 * UP * UP
    held[0] = False
    ink &= ~(held[lab] & marks)
    marks = (marks & ~held[lab]) | (own & ndi.binary_dilation(held[lab], iterations=UP))
    ink |= marks
    eyes |= marks
    dots |= marks
    for mf in MARKS_FILES:
        m = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
        assert m.shape[:2] == ink.shape, (m.shape, ink.shape)
        r, gg, bb, al = (m[..., i] for i in range(4))
        green = (al > 40) & (gg > r + 40) & (gg > bb + 20)
        blue = (al > 40) & (bb > r + 40) & (bb > gg + 20)
        for bx0, by0, bx1, by1 in DROP:
            blue[by0:by1, bx0:bx1] = False
        green = ndi.binary_fill_holes(ndi.binary_closing(green, structure=morphology.disk(2 * UP)))
        gone = ndi.binary_dilation(green, iterations=UP)
        ink &= ~gone
        eyes &= ~gone
        dots &= ~gone
        ink |= blue
        eyes |= blue
        dots |= blue
        fig |= ndi.binary_dilation(blue, iterations=UP)
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, dark=dark,
                            core=_core, thin=_thin, join=_join, faint=_faint, jf=_jf, edge=edge, dots=dots, white=white, day=day, eyes=eyes)

    lab, _ = ndi.label(fig & ~ink)
    for x, y in OPEN:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'open point {(x, y)} is not on clay'
        fig &= lab != k
    held = ~fig
    info = lw.trace_svg(
        ink & ~eyes, OUT, body=fig, open_holes=held, dots=dots, weight=WEIGHT, day=day & ~fig,
        title='Two slaves haul an old man up the steps of a stage',
        desc='Line drawing after the 1857 plate of a red-figure vase (Lenormant and de Witte, Élite des '
             'monuments céramographiques II, pl. XCIV); cut out and retraced.')
    add_white(OUT, white, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it (the day path hidden)
        dk = Path(qa).with_suffix('.svg')
        dk.write_text(re.sub(r'<path class="white"[^>]*/>', "", OUT.read_text()))
        lw.qa_overlay(g, dk, info['box'], Path(qa))
        dk.write_text(re.sub(r'<path class="day"[^>]*/>', "", OUT.read_text()))
        lw.qa_dark(dk, info['box'], Path(qa).with_suffix('.dark.png'))
        dk.unlink()


def add_white(svg, white, box):
    """The added white as a path of class "white" in WHITE_FILL, between the body and the lines (Wealth)."""
    x0, y0, x1, y1 = box
    m = white[y0:y1, x0:x1]
    m = ndi.distance_transform_edt(~m) <= EDGE_OUT * UP / 2
    d, _ = lw.potrace_d(lw.resample_ink(m, lw.TRACE_H), turdsize=20, alphamax=1.0)
    s = svg.read_text().replace('<path class="lines"', f'<path class="white" fill="{WHITE_FILL}" stroke="none" d="{d}"/>'
                                '<path class="lines"', 1)
    svg.write_text(s)


def join_faint(lines, con, fig):
    """The breaks JF_* describe, joined (a mask, LINE_MIN plate px wide); `con` is the plate's fine local contrast."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    H, W = sk.shape

    def run_back(p):   # the end's last JF_RUN plate px of centre line, from the end inward
        path, seen = [tuple(p)], {tuple(p)}
        for _ in range(JF_RUN * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]
                   and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        return np.array(path, float)

    dirs = []
    for r in map(run_back, ends):
        d = r[0] - r[-1]
        n = np.hypot(*d)
        dirs.append(d / n if len(r) >= JF_RUN * UP / 2 and n > 0 else None)
    cos = np.cos(np.radians(JF_ANGLE))
    out = np.zeros_like(lines)

    def holds(a, b):   # the plate prints a line across the gap, and the gap lies on the figure
        t = np.linspace(0.15, 0.85, max(int(np.hypot(*(b - a))), 3))
        q = a[None] + t[:, None] * (b - a)[None]
        c = ndi.map_coordinates(con, q.T, order=1)
        return np.median(c) >= JF_C and c.min() >= JF_LOW and fig[tuple(q.round().astype(int).T)].all()

    def draw(a, b):
        u = (b - a) / max(np.hypot(*(b - a)), 1e-6)
        return along(lines.shape, np.linspace(a - u, b + u, int(np.hypot(*(b - a))) + 4)[:, ::-1] + 0.5, LINE_MIN)

    used = set()
    pairs = sorted(cKDTree(ends).query_pairs(JF_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or dirs[i] is None or dirs[j] is None:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        if dirs[i] @ u < cos or dirs[j] @ -u < cos or not holds(a, b):
            continue
        out |= draw(a, b)
        used |= {i, j}
    lab = ndi.label(lines, structure=np.ones((3, 3)))[0]
    for i, (p, d) in enumerate(zip(ends, dirs)):
        if i in used or d is None:
            continue
        a, left = p.astype(float), None
        for k in range(1, JF_REACH * UP + 1):
            q = np.round(a + d * k).astype(int)
            if not (0 <= q[0] < H and 0 <= q[1] < W):
                break
            if left is None:
                if not lines[tuple(q)]:
                    left = k
                continue
            if lines[tuple(q)]:
                if (lab[tuple(q)] != lab[tuple(p)] or k > 2 * UP) and holds(a, q.astype(float)):
                    out |= draw(a, q.astype(float))
                break
    return out


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def polyline(pts):
    """Hand-placed points (plate px) joined by straight lines, a point per UP px, (x, y) at UP."""
    P = up(pts)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (path[:, ::-1] - 0.5).astype(int)
    ok = (yx[:, 0] >= 0) & (yx[:, 0] < shape[0]) & (yx[:, 1] >= 0) & (yx[:, 1] < shape[1])
    m[yx[ok, 0], yx[ok, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


if __name__ == '__main__':
    main(*sys.argv[1:4])
