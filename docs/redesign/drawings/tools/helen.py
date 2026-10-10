"""Helen (Euripides): Menelaus, bearded, bare-chested, in an armoured skirt, with a spear, leads away
Helen, veiled; his hand on her shoulder. From Lenormant and de Witte, Élite des monuments
céramographiques III (Paris, 1858), pl. LVII B, as scanned by Heidelberg University Library (Public
Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1858bd3%3A303_Planche_ROEM_057_B.jpg/full/full/0/default.jpg
(1826 x 2768, printed sideways; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0386)
The pair only: the winged figure at their left (the tip of its wing and its staff come near Helen, with
ground between) and the youth beyond it are left out.

Made with PhotoCraft (John, 2026-10-07), as tools/ion.py: every image step runs in `photocraft-cli`
(0.2.0). The scan is turned upright and its panel squared (`level`, numpy and scipy: geometry); numpy
only combines the masks PhotoCraft made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing, as for Ion:
  - The scan is turned upright (90 degrees clockwise) and the black panel mapped to a rectangle (its
    four edges fitted as straight lines on their straight stretches). Every point below is in the
    levelled frame.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of
    ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is every clay area the ground leaves larger than FIG_MIN that does not reach the crop's
    top, left or right edge (the winged figure's wing and staff cross the left edge). The figures stand
    on the panel's lower edge, which is the cut (BOTTOM).
  - Lines: the plate's dark lines inside the figures (local contrast), the outline on the black ground
    outside the clay, and the plate's solid paint. No faint-line finder: the Élite prints its lines
    solid (Ion).
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/helen.py lenormant1858bd3_pl57b.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "helen.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# The panel's edges in the upright scan (px): each a line fitted to the first dark px going in from
# the paper, on a straight stretch (clear of the plate's labels above the corners); `level` maps the
# four corners they meet at to a rectangle MARGIN px inside the levelled frame
EDGE_DARK = 90
STRETCH = dict(top=(700, 2200), bottom=(700, 2200), left=(400, 1300), right=(400, 1300))
# the search for each edge starts this far in from the scan's edge, on the paper (the library's strip
# at the left is dark)
FROM = dict(top=0, bottom=0, left=300, right=0)
MARGIN = 20
# crop in levelled px: the pair, from the ground left of Helen (the wing's tip and the staff cross the
# crop's left edge) to the ground right of the spear, down to a little past the panel's lower edge
# (BOTTOM, the row the panel's black ends on: MARGIN + the panel's height), which is the cut
X0, Y0, X1, Y1 = 990, 200, 1730, 1115
BOTTOM = 1109
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
# pockets of ground the figures close in (a point in each, levelled px): between the two arms, Helen's
# side and his; between Helen's top two fingers on his skirt (John, pass 1: it came out as black paint)
POCKETS = [(1300, 510), (1398, 572)]
WALL_W = 1.5
# Helen's hair above her diadem, round the two leaves (John, pass 1: "is there hair above the crown?"):
# no clay line bounds it, but the plate prints it as it prints the hair and the diadem's band (grey 17-40)
# and the ground darker (5-10). Its edge (levelled px), measured column by column where the plate turns
# lighter than the ground: from the veil along y 262.5-263.5 to the right leaf, then down the leaf's edge
CROWN = [(1143, 262.5), (1157, 262.5), (1172, 263.5), (1184, 263.5), (1184, 281), (1143, 281)]
LINE_DARK = 100
LINE_MIN = 1.5
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
# Helen's hand on his skirt (box, levelled px): its fingers are clay strips with 1-3 px of ground between
# them, which came out as clay with a line each side; found at less blur and outlined finer (HAND_EDGE),
# as on Ion and Trojan Women
HANDS = [(1375, 555, 1420, 592)]
HAND_EDGE = 1.2
# the eyes (boxes, levelled px: Helen's, Menelaus'): the local-contrast finder drew each eye as a heavy
# loop, the pupil run into the lids. Here the brow and the pupil are the plate's paint at its own width,
# darker than FACE_DARK after a light blur; the lids, paler and thinner, the plate darker than
# FACE_FAINT, its gaps closed over FACE_CLOSE px (at UP), drawn along their centres FACE_LINE wide
FACES = [(1162, 312, 1186, 334), (1413, 301, 1441, 326)]
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
FACE_LINE = 1.0                           # plate px: the lids' width, as printed
# Helen's eye: even so its pupil came out a ring. Drawn instead through points read off the plate's
# grey values (levelled px): the lids, FACE_LINE wide, round the almond, and the pupil a dot (x, y, r)
# under the upper lid; the brow stays as found
EYE_BOX = (1165, 325, 1186, 337)
EYE_LINES = [[(1167, 332.6), (1168.5, 331.3), (1170, 330), (1172, 328.7), (1174, 327.8), (1176, 327.2),
              (1178, 327.1), (1180, 327.3), (1182.5, 328.4), (1181.5, 330), (1180.5, 331.3), (1179, 332.6),
              (1177, 333.8), (1174, 334.2), (1171, 334), (1169, 333.4), (1167, 332.6)]]
EYE_PUPIL = (1176.2, 330.6, 1.4)
FINE = []
# Black areas that run into the ground through a gap in their clay line (levelled px): Helen's hair,
# where the lower line of her diadem stops 3 px short of her forehead; the lower black stripe of her
# mantle's border, where it runs out to the mantle's edge (walled along the edge)
WALLS = [[(1183.5, 296.5), (1183, 301.5)], [(1035.5, 941), (1037.5, 951), (1039.5, 958)]]
MARKS_FILES = []
# The dots on Helen's veil and the beads on her hem print 2-4 px across and paler than the lines (the
# line threshold kept a third of them): small marks darker than FACE_FAINT, no wider than DOT_W px and
# smaller than DOT_MAX px, whose core is darker than DOT_DARK (the dots' cores read 0-30; specks of the
# print 90 and up), drawn at their own size and passed to trace_svg as `dots`
DOT_DARK, DOT_W, DOT_MAX = 60, 7, 30
# The crosses, stars and rings on her dress are small marks standing alone: thickened to the median
# width with the rest they came out blobby. Pieces of ink no wider than MARK_W px and smaller than
# MARK_MAX px go with the dots, at their printed width
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
    """The panel's edge `name` as a line: (a, b) with y = a + b x (top, bottom) or x = a + b y (left,
    right), fitted to the first px darker than EDGE_DARK going in from the paper, outliers dropped."""
    lo, hi = STRETCH[name]
    s = np.arange(lo, hi, 2)
    H, W = g.shape
    if name in ('top', 'bottom'):
        prof = g[:, s].T
    else:
        prof = g[s, :]
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
    """The upright scan with its panel mapped to a rectangle (a homography from the panel's four
    fitted corners), MARGIN px of the frame round it. Returns the levelled RGB image."""
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
    return np.clip(out, 0, 255).astype(np.uint8), C, (Wp, Hp)


def upright(src):
    """The scan turned upright (90 degrees clockwise) and levelled, as an RGB array."""
    img = np.asarray(Image.open(src).convert('RGB').transpose(Image.Transpose.ROTATE_270))
    return level(img)


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
    ground = is_ground[lab] & ~lw.polygon_mask(g.shape, up(CROWN))
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    # (not the wing and the staff of the figure at the left: clay that reaches the crop's top, left or
    # right edge; the pair reaches only its bottom)
    fig &= ~np.isin(lab, np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1]]))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    _join = join_breaks(lines, closed - gl, ndi.distance_transform_edt(fig)) & fig
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
    eyebox = boxes(g.shape, [EYE_BOX])
    eyes &= ~eyebox
    for pts in EYE_LINES:
        eyes |= along(g.shape, polyline(pts), FACE_LINE)
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
        green = ndi.binary_fill_holes(ndi.binary_closing(green, structure=morphology.disk(2 * UP)))
        ink &= ~ndi.binary_dilation(green, iterations=UP)
        ink |= ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= LINE_MIN * UP / 2
        ink |= ndi.binary_opening(blue, structure=morphology.disk(round(LINE_MIN * UP)))
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, dark=dark,
                            core=_core, thin=_thin, join=_join, edge=edge, dots=dots)

    held = ~fig
    info = lw.trace_svg(
        ink & ~eyes, OUT, body=fig, open_holes=held, dots=dots, weight="own",
        title='Menelaus leading Helen away',
        desc='Line drawing after the 1858 plate of a red-figure vase (Lenormant and de Witte, Élite des '
             'monuments céramographiques III, pl. LVII B); cut out and retraced.')
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
