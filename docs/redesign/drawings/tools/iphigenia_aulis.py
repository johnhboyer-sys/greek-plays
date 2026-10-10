"""Iphigenia at Aulis (Euripides): Artemis draws her bow at a woman who flees with a child in her arms.
From Lenormant and de Witte, Élite des monuments céramographiques II (Paris, 1857), pl. XC, as scanned by
Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1857bd2%3A455a_Planche_090.jpg/full/full/0/default.jpg
(3475 x 2853, a double leaf printed upright; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1857bd2/0618)
The Élite's plate list (p. xliii) reads it as Diana pursuing Helen, who carries the infant Iphigenia: a
Panathenaic amphora of the Prince of Canino's collection, then the comte de Laborde's in Paris (text
p. 294; its other side, pl. XCI, they read as Apollo and Hemithea). The Beazley Archive (206990): an
Attic red-figure belly amphora (type B) from Vulci, attributed to the Niobid Painter, A Artemis and Niobe
fleeing with a child (a Niobid), B a merchant (?) selling oil, a seated woman and a youth; ex Canino,
Laborde and Baron Seillière, last recorded in a private collection in Paris (ARV2 604.51).
The whole plate, both figures (John, 2026-10-10).

Made with PhotoCraft (John, 2026-10-07), as tools/helen.py: every image step runs in `photocraft-cli`
(0.2.0). The scan is levelled across the fold (`level`, numpy and scipy: geometry, after
tools/alcestis.py); numpy only combines the masks PhotoCraft made and measures. The SVG is written by
linework.trace_svg.

Plate -> drawing, as for Helen:
  - The double leaf is levelled as Alcestis' (Élite II, pl. LIV): the panel's top and bottom edges,
    printed straight, are straightened column by column, each page's tilt taken out, and each column
    stretched to the panel's height. Not Alcestis' perspective widening: here the fold costs the panel
    13 px of its 2156 (Alcestis lost far more), and only the tip of the bow and the ground lie near it.
    Every point below is in the levelled frame.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of
    ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is every clay area the ground leaves larger than FIG_MIN that does not reach the crop's
    top, left or right edge. The figures stand on the panel's lower edge, which is the cut (BOTTOM).
  - Lines: the plate's dark lines inside the figures (local contrast), the outline on the black ground
    outside the clay, and the plate's solid paint. No faint-line finder: the Élite prints its lines
    solid (Ion). The bowstring crosses the ground as black paint a little darker than it (STRINGS).
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/iphigenia_aulis.py lenormant1857bd2_pl90.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "iphigenia-at-aulis.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# levelling (scan px), as tools/alcestis.py
FOLD = 1745                     # the crease in the scan, where the two pages meet (the frame dips most)
BLEND = 60                      # px either side of the fold over which the two tilts blend
FLAT_L = (200, 1350)            # columns where each page lies flat: its tilt is fitted there
FLAT_R = (1950, 3300)
PANEL_X = (120, 3370)           # columns read for the panel's edges (inside its left and right ends)
ROWS = (100, 2362)              # rows searched for them (above the signatures under the panel)
NEAR_FOLD = 450                 # columns this near the fold are stretched to the panel's height
MARGIN = 20                     # the levelled panel's top edge
HP = 2156                       # and its height (the flat pages' height)
# crop in levelled px: both figures, from the ground left of Artemis' foot to the ground right of the
# woman's back, down to a little past the panel's lower edge (BOTTOM, the row the panel's black ends
# on: MARGIN + HP), which is the cut: the feet stand on it
X0, Y0, X1, Y1 = 260, 150, 3200, 2182
BOTTOM = MARGIN + HP
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
# pockets of ground the figures close in (a point in each, levelled px): between Artemis' raised arm, the
# arrow she draws and her back
POCKETS = [(720, 420)]
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
# gaps closed over FACE_CLOSE px (at UP), drawn along their centres FACE_LINE wide (Helen): Artemis', the
# woman's, the child's
FACES = [(1022, 354, 1062, 395), (2748, 348, 2790, 390), (3030, 522, 3060, 548)]
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
FACE_LINE = 1.0                           # plate px: the lids' width, as printed
# an eye drawn through points read off the plate's grey values (levelled px), where the finder drew the
# pupil as a ring (Helen): its box, the lids, the pupil (x, y, r); none so far
EYE_BOX = None
EYE_LINES = []
EYE_PUPIL = None
# the hair prints as dark as the ground inside a thin clay line, found at fine blur in these boxes
# (levelled px: Artemis' head, the woman's) (Ion)
FINE = [(2830, 250, 3000, 380)]
# the bowstring, a line of black paint on the black ground, printed a little darker than it (grey 3-6
# against 7-9): two straight runs (levelled px), from the bow's upper tip to her forearm and from under
# it to the lower tip, each placed where the mean grey along it is least (searched over half-px shifts
# of its ends); drawn STRING_W plate px wide up to the clay (heracles.py's STRINGS, here dark). Where it
# crosses her forearm the plate prints it as a line on the clay, found with the rest
STRINGS = [[(1566.2, 222), (1580.4, 535)], [(1601.6, 615), (1634.2, 808)]]
STRING_W = 2.0
# black areas that run into the ground through a gap in their clay line (levelled px), walled along the
# line (each gap found by a least-cost path through the dark from the hair to the ground, cut at its
# narrowest and searched again until none was left): the woman's bun, where its line stops short of the
# band, where its scallops reach the line at the top, and where its line meets the crown's; Artemis' front curl, where its line meets the
# band's end; her hair at the back, where its line meets the ribbon's loop. And bands of solid paint that
# cross a clay part and so touch the ground (Phoenician Women's girdle), walled along the clay's edge,
# measured above and below each band: the two bracelets on Artemis' raised arm (both edges); the
# bowstring where it crosses her forearm and the bracelets by her wrist (both edges); the bow's grip
# bands above her hand (both edges)
WALLS = [[(2964, 359), (2959.5, 363.5), (2955, 367)], [(2945, 277), (2957, 276), (2966, 275)],
         [(2933.5, 284), (2936, 282), (2938, 280)],
         [(1068, 301), (1074, 297.5), (1080, 296.5)], [(886.5, 333), (884, 336.5), (881.5, 339.5)],
         [(600.5, 455), (598, 466), (595, 476), (592.5, 486), (590.5, 496), (589.5, 503)],
         [(660.5, 482), (660, 494), (659.5, 506), (659, 515), (658.5, 524)],
         [(1576, 531), (1600, 528), (1622, 524), (1640, 516.5), (1650, 513), (1660, 511), (1670, 507.5), (1680, 503)],
         [(1572, 626.5), (1590, 615.5), (1603, 608.5), (1620, 597), (1630, 590.5), (1640, 586.5), (1648, 581.5),
          (1655, 576.5), (1662, 572), (1672, 567)],
         [(1742.5, 378), (1744, 392), (1745.5, 402), (1744.5, 416)],
         [(1763, 378), (1764.5, 392), (1766.5, 402), (1767.5, 414)]]
MARKS_FILES = []
# the line weight, kept fixed after pass 1 (its median width, px over the longer side; Phoenician Women)
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
JOIN_SMALL = 160
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


def edges(g, run=5):
    """The panel's top and bottom edge at every column (scan px): the first and the last run of
    `run` px darker than 80 in ROWS; lightly smoothed (the fold bends them in a V); nan off the panel."""
    gs = ndi.gaussian_filter(g, 1.0)
    W = g.shape[1]
    top = np.full(W, np.nan)
    bot = np.full(W, np.nan)
    r0, r1 = ROWS
    dark = ndi.minimum_filter1d((gs[r0:r1] < 80).astype(np.uint8), run, axis=0, origin=-(run // 2)) > 0
    for x in range(PANEL_X[0], PANEL_X[1] + 1):
        d = np.where(dark[:, x])[0]
        if len(d):
            top[x], bot[x] = r0 + d.min(), r0 + d.max() + run - 1
    ok = ~np.isnan(top)
    for e in (top, bot):
        e[ok] = ndi.gaussian_filter1d(ndi.median_filter(e[ok], 7), 1.5)
    return top, bot


def level(img, margin=20):
    """The scan levelled (alcestis.py's `level` without the widening): rows 0 to MARGIN + HP + margin,
    the panel's top edge on row MARGIN; columns as the scan's, stretched near the fold."""
    g = np.asarray(Image.fromarray(img).convert('L'), np.float32)
    top, bot = edges(g)
    W = g.shape[1]
    xs = np.arange(W, dtype=float)
    ok = ~np.isnan(top)
    slope = {}
    for name, (a, b) in (('L', FLAT_L), ('R', FLAT_R)):
        sel = (xs >= a) & (xs <= b)
        slope[name] = (np.polyfit(xs[sel], top[sel], 1)[0] + np.polyfit(xs[sel], bot[sel], 1)[0]) / 2
    t = np.clip((xs - (FOLD - BLEND)) / (2 * BLEND), 0, 1)
    t = t * t * (3 - 2 * t)
    lean = slope['L'] * (1 - t) + slope['R'] * t      # dy/dx of the page at each column
    k = np.ones(W)
    k[ok] = HP / (bot[ok] - top[ok])
    k[np.abs(xs - FOLD) >= NEAR_FOLD] = 1.0
    ucol = np.cumsum(k) - k[0]                        # output column of each scan column
    v = np.arange(0, MARGIN + HP + margin, dtype=float)
    U, V = np.meshgrid(np.interp(np.arange(0, ucol[-1] + 1), ucol, xs), v)
    # a vertical line in the plate runs at dx/dy = -lean on the page; the edges are read at the
    # source column, which the lean moves: solve for it in turn
    sU = np.interp(U, xs, lean)
    X = U.copy()
    for _ in range(4):
        tt = np.interp(X, xs[ok], top[ok])
        bb = np.interp(X, xs[ok], bot[ok])
        Y = tt + (V - MARGIN) * (bb - tt) / HP
        X = U - sU * (Y - (tt + bb) / 2)
    out = np.stack([ndi.map_coordinates(img[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)


def upright(src):
    """The scan levelled, as an RGB array (printed upright: no turn)."""
    return level(np.asarray(Image.open(src).convert('RGB')))


def boxes(shape, bxs):
    m = np.zeros(shape, bool)
    for box in bxs:
        bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        m[by0:by1, bx0:bx1] = True
    return m


def main(src, qa=None, dump=None):
    lev = upright(src)
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
    # (not clay that reaches the crop's top, left or right edge: the figures reach only its bottom)
    fig &= ~np.isin(lab, np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1]]))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    string = np.zeros(g.shape, bool)
    for pts in STRINGS:
        string |= along(g.shape, polyline(pts), STRING_W)
    string &= ~fig & ~outside

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    _join = join_breaks(lines, closed - gl, ndi.distance_transform_edt(fig)) & fig
    # the joiner took the dots on Artemis' dress (larger than the dots below) for the ends of broken lines and
    # bridged pairs of them with strokes: its pieces that touch only small marks (under JOIN_SMALL px) go
    lab, _ = ndi.label(lines)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    jl, nj = ndi.label(_join & ~lines)
    for i, sl in enumerate(ndi.find_objects(jl), 1):
        sl = tuple(slice(max(a.start - 2, 0), a.stop + 2) for a in sl)
        piece = ndi.binary_dilation(jl[sl] == i, iterations=2)
        ends = np.unique(lab[sl][piece])
        ends = ends[ends > 0]
        if len(ends) and (sz[ends] < JOIN_SMALL * UP * UP).all():
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
        title='Artemis drawing her bow at Niobe, who flees with her child',
        desc='Line drawing after the 1857 plate of a red-figure vase (Lenormant and de Witte, Élite des '
             'monuments céramographiques II, pl. XC); cut out and retraced.')
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
