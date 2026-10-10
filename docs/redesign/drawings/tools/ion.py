"""Ion (Euripides): Apollo seated on the Delphic tripod with a bowl and a bow, between a girl at the
left (the Élite's Manto or Creusa) and the Pythia at the right with a jug, a laurel behind the
tripod, from Lenormant and de Witte, Élite des monuments céramographiques II (Paris, 1857),
pl. XLVI, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1857bd2%3A455a_Planche_046.jpg/full/full/0/default.jpg
(1720 x 2728, printed sideways; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1857bd2/0568)
The Élite's text (p. 142) takes the painting from Hamilton's second collection (Tischbein I,
pl. XXVIII, Florence edition) and names the figures: Apollo on the tripod, with the bow and a phiale
of wine; the Pythia (or Phemonoe), who has just poured it from the oinochoe in her left hand; the
girl before him, 'Manto ou bien Créuse', come to consult the oracle; a laurel behind the tripod.

Made with PhotoCraft (John, 2026-10-07), as tools/heracles.py: every image step runs in
`photocraft-cli` (0.2.0). The scan is turned upright and its panel squared (`level`, numpy and scipy:
geometry); numpy only combines the masks PhotoCraft made and measures. The SVG is written by
linework.trace_svg.

Plate -> drawing, as for Suppliant Women (tools/suppliants_aesch.py) and Heracles:
  - The scan is turned upright (90 degrees clockwise) and the black panel mapped to a rectangle:
    its four edges, fitted as straight lines on their straight stretches, lean by 0.6-1.1 degrees
    (the page photographed a little askew). Every point below is in the levelled frame.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of
    ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is every clay area the ground leaves larger than FIG_MIN: the panel holds no other.
    The figures stand on the panel's lower edge, which is the cut (BOTTOM).
  - Lines: the plate's dark lines inside the figures (local contrast), the outline, and the plate's
    solid paint.
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/ion.py lenormant1857bd2_pl46.jpg [qa.png]
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
from heracles import faint_lines, add_tone  # noqa: E402,F401

OUT = Path(__file__).resolve().parent.parent / "ion.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# The panel's edges in the upright scan (px): each a line fitted to the first dark px going in from
# the paper, on a straight stretch (the corners curl); `level` maps the four corners they meet at
# to a rectangle MARGIN px inside the levelled frame
EDGE_DARK = 90
STRETCH = dict(top=(700, 2300), bottom=(500, 2300), left=(500, 1400), right=(500, 1400))
# the search for each edge starts this far in from the scan's edge, on the paper (the scan's own top
# edge and the library's strip at the left are dark)
FROM = dict(top=60, bottom=0, left=300, right=0)
MARGIN = 20
# crop in levelled px: the panel, inside its left, top and right edges, down to a little past its lower
# edge (BOTTOM, the row the panel's black ends on: MARGIN + the panel's height), which is the cut
X0, Y0, X1, Y1 = 30, 30, 1999, 1345
BOTTOM = 1339
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are specks of the print
# pockets of ground the figures close in (a point in each, levelled px): between the girl's arm and her
# mantle, behind Apollo's back inside the bow, under the seat and between the tripod's rings either
# side of its post, and between the Pythia's fingers and the jug's handle
POCKETS = [(547, 803), (1174, 478), (950, 787), (1068, 786), (950, 1050), (1065, 1050), (1836, 722)]
WALL_W = 1.5
LINE_DARK = 100
LINE_MIN = 1.5
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
# the girl's raised hand (box, levelled px): its fingers are clay strips 3-5 px wide with 1-3 px of
# ground between them; found at less blur and outlined finer (HAND_EDGE), as on Trojan Women (the same
# box on the Pythia's lowered fingers dropped two of them as ground)
HANDS = [(600, 455, 685, 525)]
HAND_EDGE = 1.2
# the eyes (boxes, levelled px: the girl's, Apollo's, the Pythia's): the local-contrast finder drew
# each eye as a heavy loop. Here the brow and the pupil are the plate's paint at its own width,
# darker than FACE_DARK after a light blur (as heracles.py); the lids print pale brown and dotted
# (grey 100-150), and no threshold gives them whole: the plate darker than FACE_FAINT, its gaps
# closed over FACE_CLOSE px (at UP), is drawn along its centre LINE_MIN wide
FACES = [(414, 386, 452, 428), (1003, 168, 1048, 202), (1503, 234, 1542, 268)]
FACE_DARK, FACE_FAINT, FACE_CLOSE = 85, 150, 2
# The girl's and Apollo's hair print as dark as the ground inside a thin clay line 1-3 px wide, which
# the ground's blur and opening bridged: the hair dropped out as ground. In these boxes (levelled px)
# the ground is found at less blur (as the hands on Trojan Women), and the line holds
FINE = [(235, 315, 480, 665), (935, 75, 1190, 365)]
# where it still does not: Apollo's line over the brow ends a px short of the forehead, and the line
# beside his front lock fades where it meets his shoulder
WALLS = [[(999.5, 145.5), (1003, 148.5)], [(988, 266), (986, 272), (984.5, 278)]]
# A very faint thin line on the black, from under the Pythia's fingers straight down to the laurel's top,
# is left out: the Élite's text does not mention it, and John took it for a flaw in the print
# (2026-10-09: "Leave it out")
# no faint lines on the tripod's legs and post (box, levelled px): they are plain clay on the plate, and
# the grain made short dashes on them; its rings' lines print black and are kept
NO_FAINT = (860, 760, 1160, 1300)
# No faint-line finder at all (John, 2026-10-09, on pass 1: "you added a lot of strokes that weren't in
# the original"; 17 marked in the girl's mantle and Apollo's lap and the tripod's bowl, 85% of them its
# pieces): this plate prints its lines solid, and what the finder found was the paper's grain
FAINT_ON = False
# John's marks (2026-10-09), drawn in PhotoCraft over the plate at UP (this crop's px, so they register
# at zero offset): green = ink to take out, blue = ink to add; on passes 1, 3 and 4 (on pass 3 some drawn on
# the drawing's layer, picked out by colour). Applied in order: green clears the drawing's ink under it
# (and 1 plate px round it); each blue stroke is drawn along its centre, LINE_MIN wide, and a blue dot
# wider than that (a pupil) is drawn as marked
MARKS_FILES = [Path(__file__).parent / f for f in ("ion_marks.png", "ion_marks_3.png", "ion_marks_4.png")]
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
    right), fitted to the first px darker than EDGE_DARK going in from the paper, outliers (a figure
    touching the edge) dropped."""
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


def main(src, qa=None, dump=None):
    lev, _, _ = upright(src)
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
        rf = (5 * UP) // 2
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "gf.png", t / "closedf.png", ("filter.other.maximum", {"radius": rf, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": rf, "preserve": "squareness"}))
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        faint_c = grey(t / "closedf.png") - grey(t / "gf.png")
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
    hand = np.zeros(g.shape, bool)
    finebox = np.zeros(g.shape, bool)
    for box in HANDS + FINE:
        hx0, hy0, hx1, hy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        finebox[hy0:hy1, hx0:hx1] = True
        if box in HANDS:
            hand[hy0:hy1, hx0:hx1] = True
    dark = np.where(finebox, ndi.binary_opening(fine, structure=morphology.disk(1)), dark)
    dark &= ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    # (large and reaching the crop's edge: the girl's and Apollo's hair are dark areas larger than
    # AUTO_GROUND, closed in by their clay lines)
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    # (not the paper of the panel's curled top left corner: clay that reaches the crop's top, left or
    # right edge; the figures reach only its bottom)
    fig &= ~np.isin(lab, np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1]]))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = tw.ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    _core, _thin = core & fig, thin & fig
    nf = np.zeros(g.shape, bool)
    nx0, ny0, nx1, ny1 = [(v - o) * UP for v, o in zip(NO_FAINT, (X0, Y0, X0, Y0))]
    nf[ny0:ny1, nx0:nx1] = True
    _faint = (faint_lines(faint_c, fig, lines) & fig & ~nf) if FAINT_ON else np.zeros_like(fig)
    lines |= _faint
    _join = join_breaks(lines, np.maximum(closed - gl, faint_c) if FAINT_ON else closed - gl,
                        ndi.distance_transform_edt(fig)) & fig
    lines |= _join
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_MIN * UP / 2) & fig
    face = np.zeros(g.shape, bool)
    for box in FACES:
        fx0, fy0, fx1, fy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        face[fy0:fy1, fx0:fx1] = True
    lids = ndi.binary_closing(face_faint & face, structure=morphology.disk(FACE_CLOSE)) & fig
    lab, _ = ndi.label(lids)
    lids &= (np.bincount(lab.ravel()) > 12)[lab]
    lids = ndi.distance_transform_edt(~morphology.skeletonize(lids)) <= LINE_MIN * UP / 2
    lines = np.where(face, (face_dark | lids) & fig, lines)
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the outline: EDGE_OUT plate px wide on the black ground outside the clay, not on the clay (John,
    # 2026-10-09: "the black lines for the outer clay bands should be drawn on the black background,
    # not on the clay itself"; every outline), so every clay part keeps its full width
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & ~outside & (dt <= EDGE_OUT * UP)
    edge = np.where(hand, ~fig & ~outside & (dt <= HAND_EDGE * UP), edge)
    del dt
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    ink &= np.where(face, (np.bincount(lab.ravel()) > 3 * UP * UP)[lab], (np.bincount(lab.ravel()) > 12 * UP * UP)[lab])
    for mf in MARKS_FILES:
        m = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
        assert m.shape[:2] == ink.shape, (m.shape, ink.shape)
        r, gg, bb, al = (m[..., i] for i in range(4))
        green = (al > 40) & (gg > r + 40) & (gg > bb + 20)
        blue = (al > 40) & (bb > r + 40) & (bb > gg + 20)
        green = ndi.binary_fill_holes(ndi.binary_closing(green, structure=morphology.disk(2 * UP)))   # a ring (not quite closed) round a mark takes out what it encloses
        ink &= ~ndi.binary_dilation(green, iterations=UP)
        ink |= ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= LINE_MIN * UP / 2
        ink |= ndi.binary_opening(blue, structure=morphology.disk(round(LINE_MIN * UP)))
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, dark=dark, core=_core, thin=_thin, faint=_faint, join=_join)

    held = ~fig
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight="own",
        title='Apollo on the Delphic tripod, between the Pythia and a girl come to consult him',
        desc='Line drawing after the 1857 plate of a red-figure vase (Lenormant and de Witte, Élite des '
             'monuments céramographiques II, pl. XLVI); cut out and retraced.')
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
