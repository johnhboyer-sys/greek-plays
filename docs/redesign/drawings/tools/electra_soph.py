"""Electra (Sophocles): Orestes holds out the urn of his supposed ashes to Electra, veiled; Pylades stands
behind him with two spears. From A. de Laborde, Collection des vases grecs de M. le comte de Lamberg I
(Paris, 1813), pl. VIII, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/laborde1813bd1/4/Planche_07_8.jpg
(1952 x 2786, the leaf with pl. VII above and pl. VIII below; page
https://digi.ub.uni-heidelberg.de/diglit/laborde1813bd1/0122; the IIIF service gives nothing larger)
Laborde's text (pp. 8-10) reads it as the recognition of Orestes and Electra by Agamemnon's tomb, as in
Sophocles' Electra, and says the vase was found at Avella. The Kunsthistorisches Museum, Vienna
(Antikensammlung IV 689): a South Italian bell krater, about 350 BC, attributed to the Sydney Painter,
side A Pylades, Orestes and Electra; from the Lamberg collection, bought 1815.
The three figures, as the plate prints them.

Made with PhotoCraft (John, 2026-10-07), as tools/iphigenia_aulis.py: every image step runs in
`photocraft-cli` (0.2.0). The panel is squared (`level`, numpy and scipy: geometry, after
tools/phoenician_women.py); numpy only combines the masks PhotoCraft made and measures. The SVG is
written by linework.trace_svg.

Plate -> drawing, as for the Élite plates (a colour aquatint of the same kind: red figures on a dark
ground, the interior lines drawn):
  - The panel's four edges are fitted as lines and its corners mapped to a rectangle: the leaf's two
    panels are not quite square to the scan. Every point below is in the levelled frame.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of
    ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is every clay area the ground leaves larger than FIG_MIN that does not reach the crop's
    top, left or right edge. The figures stand on the panel's ground line, which is the cut (`ground_line`).
  - Lines: the plate's dark lines inside the figures (local contrast), the outline on the dark ground
    outside the clay, and the plate's solid paint.
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/electra_soph.py laborde1813bd1_pl07_8.jpg [qa.png]
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
import trojan_women_menelaus as tw  # noqa: E402
from trojan_women_menelaus import join_breaks  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "electra-soph.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# The panel's edges in the scan (px), each a line fitted to the first px that crosses EDGE_DARK going
# from START along the scan's rows or columns (STEP +1 or -1), on the stretches given: top, left and right
# from the paper into the dark; the bottom from the dark down into the clay band above the meander, at
# the band's two ends only (the band bows up by some 10 px under the figures). `level` maps the four
# corners they meet at to a rectangle MARGIN px inside the levelled frame
EDGE_DARK = 110
EDGES = dict(top=([(300, 1680)], 1200, 1), bottom=([(300, 410), (1580, 1680)], 2040, 1),
             left=([(1330, 2050)], 150, 1), right=([(1330, 2050)], 1850, -1))
MARGIN = 20
# The ground line (levelled px): the top of the clay band the figures stand on, the cut. Measured per
# column where the grey crosses EDGE_DARK going down from GROUND_FROM, on stretches clear of the feet and
# the spears (GROUND_CLEAR), and drawn straight between them. The cut runs GROUND_IN px above it: the
# band's soft top edge otherwise left a sliver of clay that ran from the feet along the band to the crop's
# edge, and the figure went with it
GROUND_FROM = 760
GROUND_IN = 1.5
GROUND_CLEAR = [(48, 158), (448, 508), (798, 848), (898, 1068), (1345, 1428)]
# crop in levelled px: the three figures, inside the dark on all sides, down past the ground line
X0, Y0, X1, Y1 = 60, 26, 1400, 812
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
SPECK = 20                                # plate px: clay pieces smaller than this, once the figures are cut, are grain
# pockets of ground the figures close in (a point in each, levelled px): inside Pylades' arm, his hand on his
# hip; under the arch of his back foot; the strip between Orestes' waist and the cloak over his arm; between
# the urn's foot and his thumb; between Electra's feet and her hem
POCKETS = [(280, 328), (361.7, 798.3), (837, 334), (920, 267), (1191, 779)]
WALL_W = 1.5
# dark printed a little lighter than the ground with no clay line round it (hair, as Helen's above her
# diadem): a polygon (levelled px), or none
CROWN = []
LINE_DARK = 100
LINE_MIN = 1.5
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
# hands (boxes, levelled px): fingers are clay strips with 1-3 px of ground between them; found at less
# blur and outlined finer (HAND_EDGE), as on Ion and Helen
HANDS = []
HAND_EDGE = 1.2
# the eyes (boxes, levelled px): the brow and the pupil are the plate's paint at its own width, darker
# than FACE_DARK after a light blur; the lids, paler and thinner, the plate darker than FACE_FAINT, its
# gaps closed over FACE_CLOSE px (at UP), drawn along their centres FACE_LINE wide (Helen). None here: the
# lid threshold took the aquatint's grain on the clay and scribbled the lids
FACES = []
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
FACE_LINE = 1.0                           # plate px: the lids' width, as printed
# Pylades' eye, drawn through points read off the plate's grey values (levelled px; Helen): the finder ran its
# lids and pupil into one blot. Its box, the lids (the crease, the upper lid's edge, the lower lid from the
# outer corner), the pupil (x, y, r); the brow above stays as found
EYE_BOX = (395, 119.8, 412, 130.5)
EYE_LINES = [[(397, 120.6), (401, 120.3), (404, 120.8), (407, 121.2), (410, 122)],
             [(398, 123), (402, 123.2), (406, 124), (409, 124.6)],
             [(396.5, 122), (397.5, 124), (399.5, 126.3), (401.5, 128), (403.5, 129)]]
EYE_PUPIL = (405.8, 125.8, 2.0)
# the hair prints as dark as the ground inside a thin clay line, found at fine blur in these boxes
# (levelled px) (Ion)
FINE = []
# lines of paint on the dark ground, a little darker than it, drawn along hand-placed points (levelled px)
# STRING_W plate px wide up to the clay (Iphigenia's bowstring); none so far
STRINGS = []
STRING_W = 2.0
# bands of solid paint that touch the ground and read as ground: a point in each (levelled px); the band
# is the thin part of the ground there, narrower than 2 BAND_R + 1 plate px (Iphigenia at Aulis)
PAINT = []
BAND_R = 8
# dark areas that run into the ground through a gap in their clay line (levelled px), walled along the
# line (Helen, Phoenician Women)
WALLS = []
MARKS_FILES = []
# the line weight, to be kept fixed at pass 1's (its median width, px over the longer side; Phoenician Women)
WEIGHT = "own"
# his marks left out (boxes, work px at UP), and clay areas the figures close in that are the vase's ground
# (a point in each, levelled px) (Phoenician Women)
DROP = []
OPEN = []
# Small dots paler than the lines: small marks darker than FACE_FAINT, no wider than DOT_W px and smaller
# than DOT_MAX px, whose core is darker than DOT_DARK, drawn at their own size as `dots` (Helen)
DOT_DARK, DOT_W, DOT_MAX = 60, 7, 30
# small marks standing alone: pieces of ink no wider than MARK_W px and smaller than MARK_MAX px go with
# the dots, at their printed width (Helen)
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
    """The panel's edge `name` as a line: (a, b) with y = a + b x (top, bottom) or x = a + b y (left,
    right), fitted to the first px that crosses EDGE_DARK going from START by STEP (into the dark for
    top, left and right; out of it for the ground line), outliers dropped."""
    stretches, start, step = EDGES[name]
    s = np.concatenate([np.arange(lo, hi, 2) for lo, hi in stretches])
    prof = g[:, s].T if name in ('top', 'bottom') else g[s, :]
    prof = prof[:, start::step] if step > 0 else prof[:, start::-1]
    hit = prof >= EDGE_DARK if name == 'bottom' else prof < EDGE_DARK
    i = np.argmax(hit, axis=1)
    r = np.arange(len(s))
    a_, b_ = prof[r, i - 1], prof[r, i]
    d = start + step * (i - 1 + (EDGE_DARK - a_) / (b_ - a_))   # sub-px, where the grey crosses EDGE_DARK
    ok = np.ones(len(s), bool)
    for _ in range(6):
        f = np.polyfit(s[ok], d[ok], 1)
        ok = np.abs(d - np.polyval(f, s)) < 1.5
    return f[1], f[0]


def level(g_rgb):
    """The scan with its panel mapped to a rectangle (a homography from the panel's four fitted
    corners), MARGIN px of the frame round it. Returns the levelled RGB image, the corners and the
    panel's size (as tools/phoenician_women.py)."""
    g = ndi.gaussian_filter(np.asarray(Image.fromarray(g_rgb).convert('L'), np.float32), 1.5)
    e = {k: fit_edge(g, k) for k in EDGES}

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
    return np.clip(out, 0, 255).astype(np.uint8), C, (Wp, Hp)


def ground_line(lev):
    """The ground line in the levelled frame: (x, y) of the top of the clay band, measured on GROUND_CLEAR,
    lightly smoothed."""
    g = ndi.gaussian_filter(np.asarray(Image.fromarray(lev).convert('L'), np.float32), 1.5)
    xs = np.concatenate([np.arange(a, b) for a, b in GROUND_CLEAR])
    prof = g[GROUND_FROM:, xs].T
    i = np.argmax(prof >= EDGE_DARK, axis=1)
    r = np.arange(len(xs))
    a_, b_ = prof[r, i - 1], prof[r, i]
    y = GROUND_FROM + i - 1 + (EDGE_DARK - a_) / (b_ - a_)
    return xs.astype(float), ndi.median_filter(y, 9, mode='nearest')


def upright(src):
    """The scan levelled, as an RGB array (printed upright: no turn)."""
    return level(np.asarray(Image.open(src).convert('RGB')))[0]


def boxes(shape, bxs):
    m = np.zeros(shape, bool)
    for box in bxs:
        bx0, by0, bx1, by1 = [round((v - o) * UP) for v, o in zip(box, (X0, Y0, X0, Y0))]
        m[by0:by1, bx0:bx1] = True
    return m


def main(src, qa=None, dump=None):
    lev = upright(src)
    gx, gy = ground_line(lev)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(lev).save(t / "lev.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "lev.png", t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
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
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
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

    # outside: below the ground line
    outside = (yy + 0.5) / UP - 0.5 + Y0 > np.interp((xx[0] + 0.5) / UP - 0.5 + X0, gx, gy - GROUND_IN)[None, :]

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
        # bands of paint read as ground: the thin parts of the ground (what an opening of BAND_R plate px
        # takes away, found at plate px) holding a PAINT point
        gp = ground[UP // 2::UP, UP // 2::UP]
        thin = gp & ~ndi.binary_opening(gp, structure=morphology.disk(BAND_R))
        tl, _ = ndi.label(thin)
        ks = [tl[round(y - Y0), round(x - X0)] for x, y in PAINT]
        assert all(ks), [p for p, k in zip(PAINT, ks) if not k]
        band = np.repeat(np.repeat(np.isin(tl, ks), UP, 0), UP, 1)[:H, :W]
        ground &= ~ndi.binary_dilation(band, iterations=UP)
        # (pieces the bands cut off from the ground are paint too: the ground is again what reaches its
        # large areas or a pocket)
        lab, _ = ndi.label(ground)
        size = np.bincount(lab.ravel())
        size[0] = 0
        keep = size > AUTO_GROUND * UP * UP
        for x, y in POCKETS:
            keep[lab[round((y - Y0) * UP), round((x - X0) * UP)]] = True
        keep[0] = False
        ground = keep[lab]
    if CROWN:
        ground &= ~lw.polygon_mask(g.shape, up(CROWN))
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    # (not clay that reaches the crop's top, left or right edge: the figures reach only its bottom)
    fig &= ~np.isin(lab, np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1]]))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)
    # the aquatint's light grain in the ground: specks the ridge kept, cut off from the figures by the
    # opening, which came out as outlined dots on the ground (by Pylades' hip)
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]

    string = np.zeros(g.shape, bool)
    for pts in STRINGS:
        string |= along(g.shape, polyline(pts), STRING_W)
    string &= ~fig & ~outside

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    _join = join_breaks(lines, closed - gl, ndi.distance_transform_edt(fig)) & fig
    # the joiner took a dress's large dots for the ends of broken lines (Iphigenia at Aulis) and
    # bridged pairs of them with strokes, or ran a line on to a dot: its pieces that touch only small marks
    # (under JOIN_SMALL px) or touch a dot (a small mark no longer than JOIN_DOT px) go
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
    face = boxes(g.shape, FACES)
    lids = ndi.binary_closing(face_faint & face, structure=morphology.disk(FACE_CLOSE)) & fig
    lab, _ = ndi.label(lids)
    lids &= (np.bincount(lab.ravel()) > 12)[lab]
    lids = ndi.distance_transform_edt(~morphology.skeletonize(lids)) <= FACE_LINE * UP / 2
    lines = np.where(face, (face_dark | lids) & fig, lines)
    # the eye's parts (brow, lids, pupil: pieces wholly inside a face box) keep their printed width: the
    # weight "own" sets every line to the median width, which ran the lids into the pupil. They go to
    # trace_svg with the dots, which are traced at their own size
    lab, _ = ndi.label(lines & face)
    eyes = (lines & face & ~np.isin(lab, np.unique(lab[face & ~ndi.binary_erosion(face)])))
    eyebox = boxes(g.shape, [EYE_BOX] if EYE_BOX else [])
    eyes &= ~eyebox
    for pts in EYE_LINES:
        eyes |= along(g.shape, polyline(pts), FACE_LINE)
    if EYE_PUPIL:
        px, py, pr = EYE_PUPIL
        eyes |= np.hypot((xx + 0.5) / UP + X0 - px, (yy + 0.5) / UP + Y0 - py) <= pr
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
    lab, n = ndi.label(face_faint & fig)
    sz = np.bincount(lab.ravel())
    dark_core = np.r_[False, np.array(ndi.minimum(g, lab, range(1, n + 1))) < DOT_DARK]
    small = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        small[i] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= DOT_W * UP
    dots = ((sz < DOT_MAX * UP * UP) & small & dark_core)[lab] & ~face | eyes
    # the local-contrast finder bridges a dot to the line beside it with a short thin stroke (the hem's
    # beads hung from the line above): its ink that the plate's paint does not hold goes near the dots
    lines &= ~(~_core & (ndi.distance_transform_edt(~dots) <= DOT_TAIL * UP) & ~dots)
    ink = lines | solid | edge | dots | string
    lab, _ = ndi.label(ink)
    ink &= np.where(face, (np.bincount(lab.ravel()) > 3 * UP * UP)[lab], (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]) | dots
    lab, n = ndi.label(ink)
    sz = np.bincount(lab.ravel())
    small = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        small[i] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) <= MARK_W * UP
    marks = ((sz < MARK_MAX * UP * UP) & small)[lab] & ink
    # (each drawn as the plate's paint at its own width, darker than FACE_DARK, where that holds it)
    own = ndi.binary_dilation(marks, iterations=UP) & face_dark & fig
    lab, n = ndi.label(marks)
    held = np.bincount(lab[own], minlength=n + 1) > 4 * UP * UP
    held[0] = False
    ink &= ~(held[lab] & marks)
    marks = (marks & ~held[lab]) | (own & ndi.binary_dilation(held[lab], iterations=UP))
    ink |= marks
    eyes |= marks   # (traced with the eyes, at their own width)
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
        # his lines kept at the width he drew them (traced with the dots, at their own size), on clay
        # so they keep it on the dark theme
        ink |= blue
        eyes |= blue
        dots |= blue
        fig |= ndi.binary_dilation(blue, iterations=UP)
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, dark=dark,
                            core=_core, thin=_thin, join=_join, edge=edge, dots=dots)

    lab, _ = ndi.label(fig & ~ink)
    for x, y in OPEN:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'open point {(x, y)} is not on clay'
        fig &= lab != k
    held = ~fig
    info = lw.trace_svg(
        ink & ~eyes, OUT, body=fig, open_holes=held, dots=dots, weight=WEIGHT,
        title='Pylades, Orestes and Electra',
        desc='Line drawing after the 1813 plate of a red-figure vase (Laborde, Collection des vases grecs de '
             'M. le comte de Lamberg I, pl. VIII); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


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
