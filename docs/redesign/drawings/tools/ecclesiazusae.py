"""Assemblywomen (Aristophanes): three comic actors, Philotimides, Charis and Xanthias, on a stage before a door.
From H. Heydemann, Vase Caputi mit Theaterdarstellungen (Neuntes Hallisches Winckelmannsprogramm, Halle 1884), Taf. I,
at the vase's size, traced by Giulio Jatta; Heidelberg University Library's scan, hwpr1884 Tafel_01 (Tafel_01.jpg,
2449 x 2021, the largest it serves; Public Domain Mark 1.0):
https://digi.ub.uni-heidelberg.de/iiif/2/hwpr1884%3A022_Tafel_01.jpg/full/full/0/default.jpg
Heydemann (pp. 3-5): a bell-krater 0.33 m high, found at Ruvo in April 1883 in Francesco Caputi's excavations. A comedy
scene on a stage on three posts, in a room with a half-open door and a jug hung on the wall: Philotimides and Charis
hold a dish of cakes between them over a low table (he a string of figs), and behind her the slave Xanthias, turned
away, hides a cake he has stolen in the folds of his tunic. Now Milan, Civico Museo Archeologico A 0.9.2841 (the
"Cratere dei Ghiottoni"), Apulian red-figure, the Choregos Painter, about 380-370 BC (the museum's record, SIRBeC
G0560-00014; Trendall, Phlyax Vases (1967) no. 45). The vase names no play.

Made with PhotoCraft (John, 2026-10-07), as tools/persians.py: every image step runs in `photocraft-cli` (0.2.0).
Pillow only converts the JPEG to PNG and reads PhotoCraft's results; numpy and scipy only combine the masks
PhotoCraft made and measure. The SVG is written by linework.trace_svg.

Plate -> drawing. A contour plate in pen on cream paper (the same programme series and engraver's style as Persians).
John chose (2026-10-12): the three actors with the bench, the tray and the hanging flask, the stage and the door; the
painted names out; the hair as printed curls; Xanthias's beard as brushstrokes, a stepped wash (as Frogs' hair);
the style as Persians, the figures' area clay on the dark theme, but the lines heavier (1.6 plate px, John, 2026-10-13)
and redrawn crisp along their centres (John: "crisp and not staticy"). John ruled the ground areas by number on pass 1,
asked for the studs solid on pass 1 and the heads redrawn on pass 2, and marked pass 3 in PhotoCraft
(ecclesiazusae_marks_1.png). Approved by John on the fourth pass, 2026-10-13.

    python3 docs/redesign/drawings/tools/ecclesiazusae.py Tafel_01.jpg [qa.png] [dump.npz]
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

OUT = Path(__file__).resolve().parent.parent / "ecclesiazusae.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the door, the flask, the three actors and the stage on its posts, above the vase's frame line
X0, Y0, X1, Y1 = 20, 195, 2420, 1830
UP = 3                                    # work at 3x the plate's px, as Persians (the curls are 1 px strokes)
BLUR = 0.5                                # plate px: the Gaussian before the line finder
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 8, 20                         # local contrast (grey levels): a line starts at HIGH, runs on down to LOW (the
#                                           pen lines print paler than Persians': at 16, 34 the stage's posts broke into dashes)
SOLID = 120                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.4                   # a line's core: the darkest px within CORE_R plate px; the share of the way
#                                           from the paper to it (0.5 broke the paler lines: a 17 px gap in the stage's edge)
SMOOTH = 0.4                              # plate px: the line mask's Gaussian, cut at half (0.6 erased thin stretches)
SPECK = 3                                 # plate px^2: smaller pieces of ink are specks of the print
SEAL = 6                                  # plate px: passages narrower than this do not join ground to figure
# The heads (hair, curls, eyes, open mouths) at Persians' half maximum and smoothing (HEAD: at the plate's, the
# curls ran together); boxes, plate px: Philotimides, Charis, Xanthias. A finer finder (less blur, a narrower core, as
# Eumenides' faces) took the grey shading between the curls for strokes and came out speckled (2026-10-12)
HEADS = [(715, 420, 1010, 720), (1480, 405, 1700, 620), (1980, 480, 2200, 710)]
HEAD = dict(half=0.5, smooth=0.6)
# weighted and traced at TRACE_H tall, not the house 4000 px: at 4000 (2.4 px a plate px) the lines thinned to
# WEIGHT broke into dashes (Persians, at 5.9 px a plate px, the same)
TRACE_H = 7200
# Xanthias's beard is brushwork, not ink (John, 2026-10-12: "Make the beard into brushstrokes like with hair on other
# comedy plates"): inside BEARDS (polygons, plate px; the top edge between the lower lip's line, about y 644-647, and the beard's first strokes) the plate's lines go and its
# dark is a stepped wash in the line colour (BEARD_STEPS: grey under, the finder's 0.5 plate px blur; total opacity),
# as Frogs' hair and goatee; pieces under BEARD_MIN plate px^2 dropped
BEARDS = [[(2030, 650), (2045, 647), (2060, 646), (2085, 648), (2098, 649), (2112, 653), (2105, 668), (2095, 682), (2075, 695),
           (2058, 701), (2042, 698), (2033, 688), (2027, 672)]]
BEARD_STEPS = [(185, 0.25), (165, 0.45), (145, 0.62), (125, 0.76), (105, 0.86)]
BEARD_MIN = 1
# the painted names (boxes, plate px; John, 2026-10-12: out): ink pieces lying wholly inside are dropped
NAMES = [(800, 315, 1160, 365), (1488, 298, 1722, 348), (1978, 343, 2247, 414)]
# grey smudges of the print by and in the centre post under the stage (John, pass 1: drop them): ink pieces lying
# wholly inside these boxes (plate px) are dropped
SMUDGES = [(1200, 1650, 1240, 1695), (1235, 1690, 1260, 1738), (1268, 1695, 1305, 1738)]
# the vase's frame line, a double curve under the stage's posts (John chose the stage, not the frame): its upper line
# read off the plate between the posts (plate px; the first px 25 grey levels under the column's median): the ink
# below it, less FRAME_UP plate px, dropped (the posts end 4-7 px above it; dropping the pieces lying mostly below it
# kept the stretches the line finder joined to a post)
FRAME = [(20, 1810), (160, 1807), (410, 1786), (530, 1779), (650, 1774), (770, 1769), (890, 1764), (1010, 1758),
         (1130, 1752), (1190, 1749), (1440, 1747), (1560, 1749), (1680, 1753), (1800, 1756), (1860, 1758),
         (2040, 1768), (2100, 1771), (2360, 1794), (2420, 1798)]
FRAME_UP = 3                              # (at 1 the line's soft upper edge stayed under the centre post)
# The lines redrawn crisp (John, 2026-10-12, pass 1: "clean up the lines on the clothing so they are crisp and not
# staticy"): but for the beard, the studs and the hem band, each line is drawn along its centre (side spurs under SPUR
# plate px pruned, pieces under LINE_LEN plate px dropped) at its printed width smoothed along it (a Gaussian of
# WIDTH_S plate px), at least LINE_W plate px, as frogs.py: the hems' dark bands and Charis's cloak band stay wide, the
# blots along a line even out (kept as printed above a width, they cut the lines into dashes and spindles); the width
# is not read within JOINT plate px of a junction, where the distance to the edge swells
SPUR, LINE_LEN, LINE_W, WIDTH_S, JOINT = 6, 10, 1.5, 4, 3
# The heads redrawn crisp too (John, 2026-10-12, pass 2: "Redraw the heads too"): inside HEADS the same, with side
# spurs under HEAD_SPUR and pieces under HEAD_LEN plate px (the curls are short), and the small marks under HEAD_DOT
# plate px^2 (the dots of the curls) kept as printed, and inside EYES (boxes, plate px: Xanthias's pupils, joined to his
# lids) the ink as printed over the redrawn lines: a centre line drops them (a rule for solid marks took the hair's
# shading with them)
HEAD_SPUR, HEAD_LEN, HEAD_DOT = 2, 3, 25
EYES = [(2040, 586, 2056, 600), (2085, 586, 2102, 600)]
# Xanthias's hem band, which the plate stipples: a solid band, as Philotimides' (it came out a chain of beads, then
# ragged; its left half prints too pale for a level on the blurred plate): inside BANDS (boxes, plate px) the beads
# closed over BAND_CLOSE plate px, their holes under BAND_HOLE plate px^2 filled (a whole fill took the strip under the
# band too), then opened by BAND_OPEN plate px (the lines crossing it go, and are redrawn with the rest)
BANDS = [(1930, 1060, 2275, 1120)]
BAND_CLOSE, BAND_HOLE, BAND_OPEN = 1.5, 30, 1.5
# The door's studs, solid black discs (John, 2026-10-12, pass 1): inside STUDS (boxes, plate px, the six bands of
# studs on the two leaves) the plate blurred by STUD_BLUR plate px and darker than STUD_LEVEL, opened by STUD_OPEN
# plate px (the band's lines go), pieces of STUD_MIN plate px^2 or more, with the ring the plate draws round some of
# them (ink pieces lying wholly within STUD_RING plate px of a disc), filled
STUDS = [(185, 325, 320, 410), (185, 760, 340, 855), (225, 1435, 350, 1585), (465, 290, 635, 385),
         (460, 750, 625, 855), (460, 1405, 620, 1525)]
STUD_BLUR, STUD_LEVEL, STUD_OPEN, STUD_MIN, STUD_RING = 2, 175, 3, 300, 5
# small closed parts (boxes, plate px): the paper the ink closes there, after a closing by CLOSE plate px, is clay:
# Philotimides' open mouth (it reached the ground through a gap at the lips' end)
CLOSED = [(895, 585, 1000, 670)]
CLOSE = 5
# points on the ground (plate px): the paper areas they fall in are vase ground; every other area the lines close is
# clay; areas reaching the crop's edge are ground. John ruled them by number on pass 1's area map (2026-10-12): the
# open space under the tray between Philotimides and Charis, between the bench's top and its rail, under the bench;
# the doorway between the two leaves; by the tray, between his arm and the dish and inside the string of figs; under
# Charis's heel by the bench's leg; between Xanthias's legs; under the stage
GROUND = [(1223, 1012), (1249, 1323), (1371, 1482), (413, 1150), (1081, 796), (1163, 664), (1685, 1518),
          (2071, 1316), (1049, 1650)]
# specks of the print: ink pieces under SPECK_MAX plate px^2 farther than NEAR plate px from the figures (on the field:
# 40 left dashes of the frame line and the plate's number), and under SPECK_IN anywhere (dots of grain in the door's
# panels; a pupil is about 20)
SPECK_MAX, NEAR, SPECK_IN = 150, 6, 6
# John's marks in PhotoCraft over each pass, on the crop at MARKS_K x the plate px (his layer alone): blue is ink as
# he drew it, traced at its own size (as trace_svg's dots, so the pinned weight is not moved), sealing the areas and
# clay round it on the dark theme. Marks 1 (2026-10-13): pass 3, all blue (Philotimides' moustache and lips, his
# fingers and the string of figs, Xanthias's brow and beard's edge, his hem band's breaks, Charis's cloak band)
MARKS_FILES = [Path(__file__).with_name("ecclesiazusae_marks_1.png")]
MARKS_K = 2
MARKS_X0, MARKS_Y0 = X0, Y0                # the marks' grid: the whole crop
# a development run on part of the plate: ECCL_BOX="x0,y0,x1,y1" (plate px); the drawing goes to ECCL_OUT
if os.environ.get("ECCL_BOX"):
    X0, Y0, X1, Y1 = map(int, os.environ["ECCL_BOX"].split(","))
    OUT = Path(os.environ["ECCL_OUT"])
WEIGHT = 1.6 / max(X1 - X0, Y1 - Y0)      # 1.6 plate px (John, 2026-10-13, from 0.8, 1.2 and 1.6: 0.8 "looks too much like a
#                                           pencil drawing")


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src, box=None, blur=BLUR, half=HALF, smooth=SMOOTH, core_r=CORE_R, speck=SPECK):
    """The plate's ink at UP (work px) in box (plate px; the crop by default), and the plate in grey."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
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
        # half maximum: darker than halfway between the paper and the line's darkest px near it, so each line keeps
        # its printed width
        hm = (closed - gl) >= half * (closed - core)
        ink = apply_hysteresis_threshold(np.where(hm, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": smooth * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > speck * UP * UP)[lab]
    return g, gl, ink


def blurred_dark(src, box, r, level):
    """The plate in box (plate px) at UP, blurred by r plate px and darker than level (PhotoCraft), as a mask."""
    x0, y0, x1, y1 = box
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
        pc(t / "src.png", t / "d.png",
           ("image.crop", {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}),
           ("image.imageSize", {"width": (x1 - x0) * UP, "height": (y1 - y0) * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": r * UP}),
           ("image.adjustments.threshold", {"level": level}))
        return grey(t / "d.png") < 128


def studs(src, ink):
    """The door's studs as solid discs (work px), as STUDS says."""
    out = np.zeros_like(ink)
    for box in STUDS:
        if not (box[0] >= X0 and box[1] >= Y0 and box[2] <= X1 and box[3] <= Y1):
            continue
        b = sl(box)
        m = ndi.binary_fill_holes(ndi.binary_opening(blurred_dark(src, box, STUD_BLUR, STUD_LEVEL),
                                                     structure=morphology.disk(STUD_OPEN * UP)))
        lab, _ = ndi.label(m)
        m &= (np.bincount(lab.ravel()) >= STUD_MIN * UP * UP)[lab]
        near = ndi.binary_dilation(m, structure=morphology.disk(STUD_RING * UP))
        il, n = ndi.label(ink[b])
        inside = np.bincount(il[~near], minlength=n + 1) == 0
        inside[0] = False
        out[b] = ndi.binary_fill_holes(m | inside[il])
    return out


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as frogs.py)."""
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    sk = morphology.skeletonize(m)
    s = sk.copy()
    for _ in range(spur):
        s &= ~((ndi.convolve(s.astype(int), k, mode="constant") == 1) & s)
    front = (ndi.convolve(s.astype(int), k, mode="constant") == 1) & s
    for _ in range(spur):
        front = ndi.binary_dilation(front, structure=np.ones((3, 3))) & sk & ~s
        s |= front
    return morphology.remove_small_objects(s, max_size=min_len, connectivity=2)


def redraw(m, spur, min_len):
    """The lines of m drawn along their centres (side spurs under spur plate px pruned, pieces under min_len plate px
    dropped) at their width smoothed along them (WIDTH_S; not read within JOINT of a junction), at least LINE_W."""
    c = centre_lines(m, spur * UP, min_len * UP)
    w = 2 * ndi.distance_transform_edt(m)
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    joint = ndi.binary_dilation(c & (ndi.convolve(c.astype(int), k, mode="constant") >= 3),
                                structure=morphology.disk(JOINT * UP))
    read = c & ~joint
    num, den = (ndi.gaussian_filter(a, WIDTH_S * UP) for a in (np.where(read, w, 0.0), read.astype(np.float32)))
    half = np.where(c, np.maximum(num / np.maximum(den, 1e-6), LINE_W * UP) / 2, 0.0)
    d, (iy, ix) = ndi.distance_transform_edt(~c, return_indices=True)
    return d <= half[iy, ix]


def marks(shape):
    """John's blue at the work px (shape: the work arrays')."""
    blue = np.zeros(shape, bool)
    for mf in MARKS_FILES:
        a = np.asarray(Image.open(mf).convert("RGBA")).astype(int)
        r, g, b, al = (a[..., i] for i in range(4))
        on = (al > 40) & (b > r + 40) & (b > g + 20)
        x0, y0 = (X0 - MARKS_X0) * MARKS_K, (Y0 - MARKS_Y0) * MARKS_K   # (a development run's box inside it)
        on = on[y0:y0 + (Y1 - Y0) * MARKS_K, x0:x0 + (X1 - X0) * MARKS_K]
        blue |= np.asarray(Image.fromarray(on.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.NEAREST)) > 0
    return blue


def sl(box):
    """A box (plate px) as a slice of the work arrays, clipped to the crop."""
    x0, y0, x1, y1 = box
    c = lambda v, lo, hi: min(max((v - lo) * UP, 0), (hi - lo) * UP)  # noqa: E731
    return np.s_[c(y0, Y0, Y1):c(y1, Y0, Y1), c(x0, X0, X1):c(x1, X0, X1)]


def drop_inside(ink, boxes):
    """ink less the pieces lying wholly inside one of boxes (plate px)."""
    lab, n = ndi.label(ink)
    inside = np.zeros(ink.shape, bool)
    for b in boxes:
        inside[sl(b)] = True
    out = np.bincount(lab[~inside], minlength=n + 1) == 0
    out[0] = False
    return ink & ~out[lab]


def areas(ink, seal=SEAL):
    """The paper the ink closes off, sealed at seal (plate px): watershed labels (0 on ink)."""
    from skimage.segmentation import watershed
    paper = ~ink
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(seal * UP)))
    return watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)


def at(ws, x, y):
    """The area at a point (plate px), the commonest label within 2 plate px if it lands on ink."""
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP]
    v, n = np.unique(win[win > 0], return_counts=True)
    assert len(v), f"no paper near {(x, y)}"
    return v[np.argmax(n)]


def figure(ink, ws):
    """The figures' area: every paper area but the ground (GROUND, and the areas reaching the crop's edge), and the
    ink touching them."""
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    pts = [at(ws, x, y) for x, y in GROUND if X0 <= x < X1 and Y0 <= y < Y1]
    ground = np.isin(ws, np.r_[out[out > 0], pts])
    # paper the seal leaves without a seed is clay, unless it reaches the crop's edge
    lab, _ = ndi.label((ws == 0) & ~ink)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    clay = ((ws > 0) | ((lab > 0) & ~np.isin(lab, edge))) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~ground, ground


def add_tone(svg, steps, box):
    """The wash added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of class "tone"
    in the line colour, between the body and the lines, one per step [(mask, total opacity)], each drawn over the
    last at the opacity that brings the total to its own (as frogs.py)."""
    x0, y0, x1, y1 = box
    paths, below = [], 0.0
    for mask, total in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(lw.resample_ink(mask[y0:y1, x0:x1], TRACE_H), turdsize=20, alphamax=1.0)
        a = 1 - (1 - total) / (1 - below)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
        below = total
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    ink = drop_inside(ink, NAMES + SMUDGES)
    fx, fy = np.array(FRAME, float).T
    edge = (np.interp((np.arange(ink.shape[1]) + 0.5) / UP + X0, fx, fy) - FRAME_UP - Y0) * UP
    below = np.arange(ink.shape[0])[:, None] > edge[None, :]
    ink &= ~below
    for box in HEADS:
        if box[0] >= X0 and box[1] >= Y0 and box[2] <= X1 and box[3] <= Y1:
            ink[sl(box)] = masks(src, box, **HEAD)[2]
    beard = np.zeros_like(ink)
    for pts in BEARDS:
        beard |= lw.polygon_mask(ink.shape, (np.array(pts, float) - (X0, Y0)) * UP)
    ink &= ~beard
    # the studs and the hem band solid; the lines redrawn crisp along their centres
    stud = studs(src, ink)
    heads = np.zeros_like(ink)
    for box in HEADS:
        heads[sl(box)] = True
    band = np.zeros_like(ink)
    for box in BANDS:
        b = sl(box)
        c = ndi.binary_closing(ink[b], structure=morphology.disk(BAND_CLOSE * UP))
        hl, _ = ndi.label(ndi.binary_fill_holes(c) & ~c)
        c |= (np.bincount(hl.ravel()) < BAND_HOLE * UP * UP)[hl] & (hl > 0)
        band[b] = ndi.binary_opening(c, structure=morphology.disk(BAND_OPEN * UP))
    printed = ink                                     # (the areas are sealed on these as well: the redraw opens gaps)
    free = ink & ~stud & ~band
    lab, n = ndi.label(free & heads)
    dot = (np.bincount(lab.ravel(), minlength=n + 1) < HEAD_DOT * UP * UP)[lab] & (lab > 0)
    for box in EYES:
        dot[sl(box)] |= free[sl(box)]
    ink = (redraw(free & ~heads, SPUR, LINE_LEN) | (redraw(free & heads & ~dot, HEAD_SPUR, HEAD_LEN) & heads)
           | dot | stud | band)
    ink = drop_inside(ink, SMUDGES)                   # (again: redrawn, they part from the post's line)
    blue = marks(ink.shape)
    ws = areas(ink | printed | beard | blue)
    fig, ground = figure(ink | printed | beard | blue, ws)
    del printed
    fig |= beard | (ndi.binary_dilation(blue, iterations=UP) & ~ground)
    kept = np.zeros_like(fig)
    for box in CLOSED:
        b = sl(box)
        cl = ndi.binary_closing(ink[b], structure=morphology.disk(CLOSE * UP))
        kept[b] = ndi.binary_fill_holes(cl) & ~ink[b]   # (the paper the closing covers too: the lip is narrow)
    fig |= kept
    # specks on the field
    lab, n = ndi.label(ink)
    size = np.bincount(lab.ravel()) / UP / UP
    near = np.zeros(n + 1, bool)
    near[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    drop = ((size < SPECK_MAX) & ~near) | (size < SPECK_IN)
    drop[0] = False
    ink &= ~drop[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    lw.WORK_H = TRACE_H
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, trace_h=TRACE_H, keep=kept, dots=blue,
        title="Three comic actors: Philotimides, Charis and Xanthias",
        desc="Line drawing after the 1884 plate of the Caputi vase (Heydemann, Hallisches Winckelmannsprogramm 9); "
             "retraced.")
    steps = []
    for level, opacity in BEARD_STEPS:
        m = beard & (gl < level)
        lab, _ = ndi.label(m)
        steps.append((m & (np.bincount(lab.ravel()) >= BEARD_MIN * UP * UP)[lab], opacity))
    add_tone(OUT, steps, info["box"])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
