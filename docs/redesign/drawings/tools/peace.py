"""Peace (Aristophanes): three comic actors on a stage, a seated scribe, a slave with a writing tablet and an old
countryman with his stick and his bundle on a carrying fork.
From F. Wieseler, "Monumenti scenici", Annali dell'Instituto di corrispondenza archeologica 25 (1853), 27-50, tav.
d'agg. C-D, fig. 6; the DAI's scan in Arachne (image 2584539, BOOK-1317343-0294; 4500 x 3065, the whole plate C-D):
https://arachne.dainst.org/data/image/2584539
Wieseler (pp. 43-47): a comedy scene on a krater from Ruvo, then owned by the Marchese Campana in Rome: on a rough
wooden stage an old man from the country, leaning on his stick, his bundle clamped in a carrying fork behind him; his
slave, a writing tablet on his arm, turns back to him with a raised finger; a scribe, seated, a tablet on his arm,
holds his stylus to his mouth. Now St Petersburg, Hermitage St. 1779, Apulian red-figure bell-krater, the name vase
of the Reckoning Painter, about 380-370 BC (Bieber, Denkmäler zum Theaterwesen (1920) no. 115, "Abrechnung";
Trendall, Phlyax Vases (1967) no. 33). The plate leaves out the slave's phallus, which Wieseler names and
Furtwängler-Reichhold II pl. 110, 1 shows; drawn as printed (John, 2026-10-15).

Made with PhotoCraft (John, 2026-10-07), as tools/ecclesiazusae.py: every image step runs in `photocraft-cli` (0.2.0).
Pillow only converts the JPEG to PNG and reads PhotoCraft's results; numpy and scipy only combine the masks
PhotoCraft made and measure. The SVG is written by linework.trace_svg.

Plate -> drawing. A contour engraving in black on cream paper, the dark parts (the tablets, the bands, the hair)
hatched. John chose (2026-10-15): the three actors, the stage and its three posts, the bundle on its fork; the
ornament bands and the reverse (6b) out.

    python3 docs/redesign/drawings/tools/peace.py annali-1853-CD-arachne-2584539.jpg [qa.png] [dump.npz]
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

OUT = Path(__file__).resolve().parent.parent / "peace.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the bundle, the three actors and the stage on its posts, below the egg moulding (its lower line
# y 765-769; the slave's crown at 779: a crop from 782 cut it and his face ran out to the edge) and above the meander's
# frame line (y 2460)
X0, Y0, X1, Y1 = 630, 773, 3925, 2420
UP = 2                                    # work at 2x the plate's px (the pen lines print 2.5-3 px, the hatching 1.5)
BLUR = 0.5                                # plate px: the Gaussian before the line finder
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 10, 28                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW (the
#                                           pen lines print 24-50 on paper 205; at 15, 40 the old man's crown and the faces'
#                                           paler lines dropped out; the paper's grain this lets in goes in the redraw)
SOLID = 90                                # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.5                   # a line's core: the darkest px within CORE_R plate px; the share of the way
#                                           from the paper to it
SMOOTH = 0.4                              # plate px: the line mask's Gaussian, cut at half
SPECK = 3                                 # plate px^2: smaller pieces of ink are specks of the print
SEAL = 6                                  # plate px: passages narrower than this do not join ground to figure
# The hatched parts (the hair, the bands, the tablets' panels, the bundle's stripes, the pupils) solid black (John,
# 2026-10-15, from a test of solid, wash and even hatch): the strokes print about 1 plate px apart, too fine to trace one
# by one. Found as the plate blurred by HAT_BLUR plate px darker than HAT_LEVEL, opened by HAT_OPEN plate px, pieces of
# HAT_MIN plate px^2 or more, holes under HAT_HOLE plate px^2 filled (flecks of paper between the strokes)
HAT_BLUR, HAT_LEVEL, HAT_OPEN, HAT_MIN, HAT_HOLE = 2.5, 150, 2, 200, 300
# the scribe's tablet panels blur to 135-150 and came out flecked at HAT_LEVEL: inside PANELS (boxes, plate px) the
# level is PANEL_LEVEL (over the whole plate it turned close pairs of face lines, brows and lips, into blots)
PANELS, PANEL_LEVEL = [(3240, 1370, 3720, 1545)], 175
# the edges of the hatched parts from the printed strokes, not the blur (whose edge rounded the tablets' corners): the
# line finder's ink closed by HAT_JOIN plate px within HAT_NEAR plate px of the blurred area
HAT_JOIN, HAT_NEAR = 1.5, 3
# no hatching inside NO_HAT (boxes, plate px): the scribe's eyes, whose close arcs blurred as dark as hatching and ran
# into bars over the eyes (John, pass 1: "fix the known faults first")
NO_HAT = [(3362, 985, 3490, 1052)]     # (a box to x 3565 took in his hair, which came out striped)
# the reverse (6b) and its label, bottom left (John, 2026-10-15: out): ink pieces lying wholly inside are dropped
DROP = [(560, 1880, 1025, 2490),
        (640, 880, 760, 1000)]            # (and faint strokes on the field by the bundle, offset from the facing plate)
# ink pieces touching the crop's top row are the egg moulding's lower edge (the plate sits a little lower at the left)
# The fold's crease, a pale grey line down the plate at x 2949-2953 (grey 160-190 on paper 210): inside CREASE (x range,
# plate px) only ink whose local contrast reaches CREASE_C is kept (the pen lines it crosses read 100 and up)
CREASE, CREASE_C = (2944, 2960), 60
# walls (polylines, plate px) that close an area for the fill only, not drawn: the old man's crown, where the outline
# stops at his tufts (his hair ran out to the ground); the stage's right end, where its lower lines stop open (the front
# strip ran to ground)
WALLS = [[(1386, 936), (1376, 966), (1372, 982)],
         [(3902, 2160), (3890, 2195), (3891, 2240)]]
# points on the ground (plate px): the paper areas they fall in are vase ground; every other area the lines close is
# clay; areas reaching the crop's edge are ground
# John (2026-10-15, pass 1): "Furtwängler's plate to identify/verify ground v clay": FR II pl. 110, 1a (Reichhold's
# drawing of the vase, black ground) shows ground in the open space between the old man's hanging mantle, his stick and
# the stage; inside the scribe's raised arm (between forearm, hand, chin and shoulder); under the seat bar, between the
# scribe's strapped shin and the chair's front leg, down to the stage
GROUND = [(1684, 1844), (3240, 1130), (3330, 1800)]
# small closed parts (boxes, plate px): the paper the ink closes there, after a closing by CLOSE plate px, is clay: the
# old man's open mouth (it reached the ground between his lips), as Philotimides' in ecclesiazusae.py
CLOSED = [(1525, 1100, 1620, 1175)]
CLOSE = 5
# specks of the print: ink pieces under SPECK_MAX plate px^2 farther than NEAR plate px from the figures, and under
# SPECK_IN anywhere
SPECK_MAX, NEAR, SPECK_IN = 150, 6, 6
# but not inside SPARE (boxes, plate px): the old man's four hair tufts, which stand off his crown on the ground
SPARE = [(1355, 920, 1445, 975)]
TRACE_H = 4000
# John's marks in PhotoCraft over each pass, on the crop at the plate's px (his layer alone, exported from the .pcraft):
# blue is ink as he drew it, added to mine (John, 2026-10-15: "Add"), traced at its own size (trace_svg's dots, so the
# pinned weight is not moved) and sealing the areas, clay round it; yellow takes the ink under it out and is clay (stray
# dashes, solids run past their edges); green takes the ink under it out and is ground (specks, a stray line).
# Marks 1 (2026-10-15): pass 2
MARKS_FILES = [Path(__file__).with_name("peace_marks_1.png")]
MARKS_X0, MARKS_Y0 = 630, 773              # the marks' grid: the whole crop, one px a plate px
# The lines redrawn crisp along their centres, as ecclesiazusae.py (John's "crisp and not staticy" there): but for the
# hatched parts, each line drawn along its centre (side spurs under SPUR plate px pruned, pieces under LINE_LEN plate px
# dropped: the grain's specks) at its printed width smoothed along it (a Gaussian of WIDTH_S plate px), at least LINE_W
# plate px; the width not read within JOINT plate px of a junction
SPUR, LINE_LEN, LINE_W, WIDTH_S, JOINT = 4, 8, 1.5, 4, 3
# a development run on part of the plate: PEACE_BOX="x0,y0,x1,y1" (plate px); the drawing goes to PEACE_OUT
if os.environ.get("PEACE_BOX"):
    X0, Y0, X1, Y1 = map(int, os.environ["PEACE_BOX"].split(","))
    OUT = Path(os.environ["PEACE_OUT"])
WEIGHT = 2.3 / max(X1 - X0, Y1 - Y0)      # 2.3 plate px, the plate's printed weight (John, 2026-10-15, from 2.3 and 1.6)


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
        cx = (np.arange(ink.shape[1]) + 0.5) / UP + x0
        ink &= ~(((cx >= CREASE[0]) & (cx < CREASE[1]))[None, :] & ((closed - gl) < CREASE_C))
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


def hatched(src, ink):
    """The hatched parts, solid (work px), as HAT_* say; ink: the line finder's (for their edges)."""
    dark = blurred_dark(src, (X0, Y0, X1, Y1), HAT_BLUR, HAT_LEVEL)
    for box in PANELS:
        if box[0] >= X0 and box[1] >= Y0 and box[2] <= X1 and box[3] <= Y1:
            dark[sl(box)] = blurred_dark(src, box, HAT_BLUR, PANEL_LEVEL)
    for box in NO_HAT:
        dark[sl(box)] = False
    m = ndi.binary_opening(dark, structure=morphology.disk(HAT_OPEN * UP))
    lab, _ = ndi.label(m)
    m &= (np.bincount(lab.ravel()) >= HAT_MIN * UP * UP)[lab]
    near = ndi.binary_dilation(m, structure=morphology.disk(HAT_NEAR * UP))
    m |= ndi.binary_closing(ink & near, structure=morphology.disk(HAT_JOIN * UP)) & near
    m = ndi.binary_opening(m, structure=morphology.disk(HAT_OPEN * UP)) & near
    lab, _ = ndi.label(m)
    m &= (np.bincount(lab.ravel()) >= HAT_MIN * UP * UP)[lab]
    hl, _ = ndi.label(ndi.binary_fill_holes(m) & ~m)
    return m | ((np.bincount(hl.ravel()) < HAT_HOLE * UP * UP)[hl] & (hl > 0))


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


def marks(shape):
    """John's blue, yellow and green at the work px (shape: the work arrays')."""
    out = [np.zeros(shape, bool) for _ in range(3)]
    for mf in MARKS_FILES:
        a = np.asarray(Image.open(mf).convert("RGBA")).astype(int)
        r, g, b, al = (a[..., i] for i in range(4))
        on = al > 40
        cols = (on & (b > r + 40) & (b > g + 20), on & (r > 150) & (g > 150) & (b < 100), on & (g > r + 40) & (g > b + 20))
        x0, y0 = X0 - MARKS_X0, Y0 - MARKS_Y0          # (a development run's box inside it)
        for o, c in zip(out, cols):
            c = c[y0:y0 + (Y1 - Y0), x0:x0 + (X1 - X0)]
            o |= np.asarray(Image.fromarray(c.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.NEAREST)) > 0
    return out


def walls(shape):
    """WALLS rasterised (work px), a plate px wide."""
    from skimage.draw import line
    m = np.zeros(shape, bool)
    for pts in WALLS:
        q = (np.array(pts, float) - (X0, Y0)) * UP
        for (xa, ya), (xb, yb) in zip(q[:-1], q[1:]):
            rr, cc = line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
            m[rr[ok], cc[ok]] = True
    return ndi.binary_dilation(m, iterations=UP // 2)


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


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    hat = hatched(src, ink)
    ink = drop_inside(ink | hat, DROP)
    lab, _ = ndi.label(ink)
    ink &= ~np.isin(lab, lab[0][lab[0] > 0])
    hat &= ink
    printed = ink                                     # (the areas are sealed on these as well: the redraw opens gaps)
    ink = (redraw(ink & ~hat, SPUR, LINE_LEN) & ~hat) | hat
    blue, yellow, green = marks(ink.shape)
    ink &= ~(yellow | green)
    printed &= ~(yellow | green)
    wall = walls(ink.shape)
    ws = areas(ink | printed | wall | blue)
    fig, ground = figure(ink | printed | wall | blue, ws)
    fig = (fig | yellow | (ndi.binary_dilation(blue, iterations=UP) & ~ground)) & ~green
    del printed
    kept = np.zeros_like(fig)
    for box in CLOSED:
        b = sl(box)
        cl = ndi.binary_closing(ink[b], structure=morphology.disk(CLOSE * UP))
        kept[b] = ndi.binary_fill_holes(cl) & ~ink[b]
    fig |= kept
    # specks on the field
    lab, n = ndi.label(ink)
    size = np.bincount(lab.ravel()) / UP / UP
    near = np.zeros(n + 1, bool)
    near[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    for box in SPARE:
        near[lab[sl(box)]] = True
    drop = ((size < SPECK_MAX) & ~near) | (size < SPECK_IN)
    drop[0] = False
    ink &= ~drop[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    lw.WORK_H = TRACE_H
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, trace_h=TRACE_H, keep=kept, dots=blue,
        title="Three comic actors: a scribe, a slave and an old countryman",
        desc="Line drawing after the 1853 plate of the Reckoning Painter's krater (Wieseler, Annali dell'Instituto "
             "25, tav. d'agg. C-D, 6); retraced.")
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
