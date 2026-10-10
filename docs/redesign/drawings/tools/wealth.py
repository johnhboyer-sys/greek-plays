"""Wealth (Aristophanes): Plutos, an old man with white hair and beard, holding a long sceptre and a cornucopia.
From Lenormant and de Witte, Élite des monuments céramographiques III (Paris, 1858), pl. LVIII, as scanned by
Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/diglitData/image/lenormant1858bd3/4/303_Planche_ROEM_058.jpg
(4272 x 2818, a double plate printed upright; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0387)
The figure at the far left of the plate's frieze, alone: the woman next to him stays out (whole figures only).
A thin pale line runs down the plate through his head: a crease in the paper (it runs on through the margins
above and below the panel, dark on the paper), not printed; it reads as ground or clay and draws nothing.

Made with PhotoCraft (John, 2026-10-07), as tools/phoenician_women.py: every image step runs in `photocraft-cli`
(0.2.0). The panel is squared (`level`, numpy and scipy: geometry); numpy only combines the masks PhotoCraft
made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing, as for Phoenician Women, with these differences:
  - The plate is printed upright, a double plate across two pages; he stands on the left page. `level` maps the
    left page's part of the panel to a rectangle: its top, bottom and left edges fitted as lines, the right side
    taken upright at x = XR (near the fold, which is far to his right).
  - His hair and beard are added white over the black ground, with black curl lines printed in it. The white
    (light, and not red: red less blue, PhotoCraft's Channel Mixer) is part of the figure, drawn as a path of
    class "white" (fill #f7f3ea, as Clouds) under the lines (John, 2026-10-10: "B: white paths"). Where the white
    meets the ground it has no black outline on the vase; the outline there is a path of its own, class "day",
    in the line colour, which the dark theme hides (John, 2026-10-10: "white hair, but black outline of the top
    for day mode"; "Day mode only").

    python3 docs/redesign/drawings/tools/wealth.py lenormant1858bd3_pl58.jpg [qa.png]
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
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import trojan_women_menelaus as tw  # noqa: E402
from trojan_women_menelaus import join_breaks  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "wealth.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# The panel's edges in the scan (px): each a line fitted to the first dark px going in from the paper, on a
# straight stretch of the left page (clear of "T. III" above the top left corner, the signature below the
# bottom left corner, and the library's footer, which the bottom search starts above); `level` maps the
# corners to a rectangle MARGIN px inside the levelled frame, the right side upright at x = XR
EDGE_DARK = 90
STRETCH = dict(top=(300, 1850), bottom=(400, 1850), left=(500, 1800))
FROM = dict(top=0, bottom=400, left=0)
XR = 2050
MARGIN = 20
# crop in levelled px: from the panel's left edge to the ground right of the cornucopia's leaves (the woman
# next to him reaches the crop's right edge and drops out), down to a little past the panel's lower edge
# (BOTTOM: MARGIN + the panel's height), which is the cut: his feet stand on it
X0, Y0, X1, Y1 = 24, 200, 800, 1484
BOTTOM = 1478
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
# pockets of ground the figures close in (a point in each, levelled px)
POCKETS = []
WALL_W = 1.5
# dark printed a little lighter than the ground with no clay line round it (hair, as Helen's above her
# diadem): a polygon (levelled px), or none
CROWN = []
LINE_DARK = 100
LINE_MIN = 1.5
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
# hands (boxes, levelled px): fingers are clay strips with 1-3 px of ground between them; found at less
# blur and outlined finer (HAND_EDGE), as on Ion and Helen
HANDS = []   # (a box round the hand under the cornucopia lost its thumb: none)
HAND_EDGE = 1.2
# the eyes (boxes, levelled px): the brow and the pupil are the plate's paint at its own width, darker
# than FACE_DARK after a light blur; the lids, paler and thinner, the plate darker than FACE_FAINT, its
# gaps closed over FACE_CLOSE px (at UP), drawn along their centres FACE_LINE wide (Helen)
FACES = []   # (a box round his eye broke the lid into pieces and swelled the pupil: none)
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
FACE_LINE = 1.4                           # plate px: the lids' width, as printed
# the eye drawn through points read off the plate's grey values (levelled px; darker than 100 along each line's
# middle), at FACE_LINE: the finder ran the crease above the lid into the lid as one wedge (Helen). Its box,
# the lines (the crease, the lid, the lower lid), the pupil (x, y, r)
EYE_BOX = (480, 418, 508, 439)
EYE_LINES = [[(483.5, 423.5), (486, 422), (490, 421), (495, 420.5), (499, 421.5), (502, 423), (505, 425)],
             [(482, 426), (486, 425.5), (490, 424.8), (495, 424.5), (500, 425), (503.5, 426)],
             [(485, 427), (486, 429.5), (487, 431.5), (488, 433), (489.5, 435), (492, 436), (494.5, 437)]]
EYE_PUPIL = (493.6, 428.3, 2.0)
# dark found at fine blur in these boxes (levelled px) (Ion); none so far
FINE = []
# black paint that runs into the ground (levelled px), walled along the plate's edge: the sceptre's black
# bands, where it crosses the ground above his shoulder and below his hem, walled along both its edges, a px
# out from the edge (each edge a line fitted to where the grey crosses 80, rows clear of the bands, residuals
# under 0.8 px; the staff is about 10 px wide at the top and 13 at the foot)
SCEPTRE = [((326, 520), (124.906, 0.3319), (131.184, 0.3415)), ((1150, 1336), (126.142, 0.3312), (138.508, 0.3320))]
WALLS = [[(a + b * y + side, y) for y in ys] for ys, *edges in SCEPTRE
         for (a, b), side in zip(edges, (-1.0, 1.0))]
# boxes (levelled px) where the line finder drew a line the plate does not print: down the sceptre's head, from
# the right leaf's inner edge down the stem to its right outline, two boxes clear of that outline (John, pass 1: "there's a vertical line in the spear/scepter at the spear head.
# remove it"); the outline, found apart from the lines, stays
LINES_OFF = [(229, 281, 241, 304), (238, 304, 245, 321)]
# John's marks, drawn in PhotoCraft over a pass on the crop at UP px (1:1 with the work px): green takes the
# ink out, blue is ink as he drew it; none so far
MARKS_FILES = []
# the line weight pass 1 had (its median width, px over the longer side), kept fixed, so John's marks cannot move
# the median and thin every line (Phoenician Women)
WEIGHT = 5.0 / 3685
# his marks left out (boxes, work px at UP); none so far
DROP = []
# clay areas the figure closes in that are the vase's ground (a point in each, levelled px); none so far
OPEN = []
# The added white (hair and beard): lighter than WHITE_L (grey, lightly smoothed) and not red (red less blue
# under WHITE_RB: the clay reads 120 and up, the white under 60), closed over its curl lines (WHITE_CLOSE
# plate px), on the figure. Drawn as `white` paths in WHITE_FILL (as Clouds), outlined on the ground by a
# `day` path the dark theme hides
WHITE_L, WHITE_RB, WHITE_CLOSE = 150, 90, 1.5
WHITE_FILL = "#f7f3ea"
# Small dots paler than the lines: small marks darker than FACE_FAINT, no wider than DOT_W px and smaller
# than DOT_MAX px, whose core is darker than DOT_DARK, drawn at their own size as `dots` (Helen)
DOT_DARK, DOT_W, DOT_MAX = 60, 7, 30
# small marks standing alone: pieces of ink no wider than MARK_W px and smaller than MARK_MAX px go with
# the dots, at their printed width (Helen)
MARK_W, MARK_MAX = 10, 70
DOT_TAIL = 1.8
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
    """The panel's edge `name` as a line: (a, b) with y = a + b x (top, bottom) or x = a + b y (left),
    fitted to the first px darker than EDGE_DARK going in from the paper, outliers dropped."""
    lo, hi = STRETCH[name]
    s = np.arange(lo, hi, 2)
    H, W = g.shape
    prof = g[:, s].T if name in ('top', 'bottom') else g[s, :]
    if name == 'bottom':
        prof = prof[:, ::-1]
    prof = prof[:, FROM[name]:]
    d = np.argmax(prof < EDGE_DARK, axis=1).astype(float) + FROM[name]
    if name == 'bottom':
        d = H - 1 - d
    ok = np.ones(len(s), bool)
    for _ in range(6):
        f = np.polyfit(s[ok], d[ok], 1)
        ok = np.abs(d - np.polyval(f, s)) < 1.5
    return f[1], f[0]


def level(g_rgb):
    """The scan with the left page's part of the panel mapped to a rectangle (a homography from its corners:
    the top and bottom edges meet the left edge, and the line x = XR), MARGIN px of the frame round it.
    Returns the levelled RGB image."""
    g = ndi.gaussian_filter(np.asarray(Image.fromarray(g_rgb).convert('L'), np.float32), 1.5)
    e = {k: fit_edge(g, k) for k in STRETCH}

    def corner(h, v):   # y = a + b x meets x = c + d y
        (a, b), (c, d) = e[h], e[v]
        y = (a + b * c) / (1 - b * d)
        return c + d * y, y
    def at_xr(h):
        a, b = e[h]
        return XR, a + b * XR
    C = np.array([corner('top', 'left'), at_xr('top'), at_xr('bottom'), corner('bottom', 'left')])
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


def upright(src):
    """The scan (printed upright) levelled, as an RGB array."""
    return level(np.asarray(Image.open(src).convert('RGB')))


def boxes(shape, bxs):
    m = np.zeros(shape, bool)
    for box in bxs:
        bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        m[by0:by1, bx0:bx1] = True
    return m


def main(src, qa=None, dump=None):
    lev, _, (_, Hp) = upright(src)
    assert MARGIN + Hp == BOTTOM, Hp
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(lev).save(t / "lev.png")
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

    # outside: below the panel's lower edge
    outside = (yy + 0.5) / UP - 0.5 + Y0 > BOTTOM + 0.5

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
    if CROWN:
        ground &= ~lw.polygon_mask(g.shape, up(CROWN))
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    # (not clay that reaches the crop's top, left or right edge: the group reaches only its bottom)
    fig &= ~np.isin(lab, np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1]]))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    # the added white: light and not red, closed over its curl lines, on the figure
    white = ndi.binary_closing((gs > WHITE_L) & (rb < WHITE_RB), structure=morphology.disk(round(WHITE_CLOSE * UP)))
    white = ndi.binary_fill_holes(white) & fig
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > FIG_MIN * UP * UP)[lab]

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    _join = join_breaks(lines, closed - gl, ndi.distance_transform_edt(fig)) & fig
    lines |= _join
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_MIN * UP / 2) & fig
    lines &= ~boxes(g.shape, LINES_OFF)
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
    # the ground nearer the white than the clay: its outline is the `day` path
    day = ndi.distance_transform_edt(~white) < ndi.distance_transform_edt(~(fig & ~white))
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
    ink = lines | solid | edge | dots
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
                            core=_core, thin=_thin, join=_join, edge=edge, dots=dots, white=white, day=day, eyes=eyes)

    lab, _ = ndi.label(fig & ~ink)
    for x, y in OPEN:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'open point {(x, y)} is not on clay'
        fig &= lab != k
    held = ~fig
    info = lw.trace_svg(
        ink & ~eyes, OUT, body=fig, open_holes=held, dots=dots, weight=WEIGHT, day=day & ~fig,
        title='Plutos with the cornucopia',
        desc='Line drawing after the 1858 plate of a red-figure vase (Lenormant and de Witte, Élite des '
             'monuments céramographiques III, pl. LVIII); cut out and retraced.')
    add_white(OUT, white, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it (the day path hidden)
        dark = Path(qa).with_suffix('.svg')
        dark.write_text(re.sub(r'<path class="white"[^>]*/>', "", OUT.read_text()))
        lw.qa_overlay(g, dark, info['box'], Path(qa))
        dark.write_text(re.sub(r'<path class="day"[^>]*/>', "", OUT.read_text()))
        lw.qa_dark(dark, info['box'], Path(qa).with_suffix('.dark.png'))
        dark.unlink()


def add_white(svg, white, box):
    """The added white as a path of class "white" in WHITE_FILL, between the body and the lines (as Clouds),
    at the size the lines are traced at. It runs half a line onto the ground, under the day outline, so the
    body's edge, which the tracer sets half a line under the outline, shows no clay on the dark theme."""
    x0, y0, x1, y1 = box
    m = white[y0:y1, x0:x1]
    m = ndi.distance_transform_edt(~m) <= EDGE_OUT * UP / 2
    d, _ = lw.potrace_d(lw.resample_ink(m, lw.TRACE_H), turdsize=20, alphamax=1.0)
    s = svg.read_text().replace('<path class="lines"', f'<path class="white" fill="{WHITE_FILL}" stroke="none" d="{d}"/>'
                                '<path class="lines"', 1)
    svg.write_text(s)


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
