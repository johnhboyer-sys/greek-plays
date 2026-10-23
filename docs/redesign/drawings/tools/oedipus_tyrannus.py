"""Oedipus Tyrannus (Sophocles): the lower row of the Sbani vase: a woman with a mirror by a basin on its stand, a
bearded king enthroned with a sceptre, an old man in a rich robe with a staff, and a boy with a laurel branch.
From D. Raoul-Rochette, Monumens inédits d'antiquité figurée I (Paris 1833), pl. LXXVIII, the plate Benndorf copied in
the Wiener Vorlegeblätter (Serie 1889, Taf. IX, 6); Heidelberg University Library's scan, rochette1833bd1 Tafel_87
(2173 x 3162, the largest it serves):
https://digi.ub.uni-heidelberg.de/iiif/2/rochette1833bd1%3ATafel_87.jpg/full/full/0/default.jpg
Raoul-Rochette (pp. 409-410): a vase of D. Aniello Sbani at Naples, read as an Eleusinian initiation (a priest-king, a
priestess with the lustral basin and the mirror, an old mystagogue leading a boy initiate). Overbeck, Die Bildwerke zum
thebischen und troischen Heldenkreis (1853), p. 62 no. 75, after K. O. Müller and Welcker: Oedipus with the eagle
sceptre, Teiresias led by a boy, Jocasta with the mirror (OT 300 ff.). Benndorf (Verzeichniss, Taf. IX, 6): "Amphora der
Sammlung Sbani zu Neapel".

Made with PhotoCraft (John, 2026-10-07), as tools/ecclesiazusae.py: every image step runs in `photocraft-cli` (0.2.0).
Pillow only converts the JPEG to PNG and reads PhotoCraft's results; numpy and scipy only combine the masks
PhotoCraft made and measure. The SVG is written by linework.trace_svg. The plate is drawn as printed, not levelled.

Plate -> drawing. A lithographed contour plate, black pen lines on cream paper. John chose (2026-10-13): the whole lower
row with the plant between the woman and the throne; the upper row, the beaded line between the rows and the ribbons
hanging from the upper row's garland left out; one ground line (the upper of the two over the meander) drawn; the lines
redrawn along their centres at 2.0 plate px (from 1.6, 2.0 and 2.4), the hair and broad bands solid as printed. John
ruled the ground areas by number on pass 1, marked pass 1 in PhotoCraft (oedipus_tyrannus_marks_1.png) and named one
more bit of ground on pass 3. Approved by John on the fourth pass, 2026-10-13. It replaces the drawing from the Syracuse
krater (tools/oedipus_syracuse.py; John, 2026-10-09: "too damaged", "too crude").

    python3 docs/redesign/drawings/tools/oedipus_tyrannus.py rochette1833-pl78.jpg [qa.png] [dump.npz]
"""
import json
import os
import shutil
import re
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

OUT = Path(__file__).resolve().parent.parent / "oedipus-tyrannus.svg"
# the drawing levelled by its ground line (John, 2026-10-22): turned by LEVEL degrees about LEVEL_C, its view box cut
# to LEVEL_VIEW so no corner of the turn shows
LEVEL, LEVEL_C, LEVEL_VIEW = 1.586, (1090.85, 500), "0 17 2180 953"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: from the gutter's edge to the plate's right edge; from above the old man's head to below the ground
X0, Y0, X1, Y1 = 56, 1150, 2170, 2140
UP = 3                                    # work at 3x the plate's px
BLUR = 0.5                                # plate px: the Gaussian before the line finder
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 10, 24                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 110                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.45                  # a line's core: the darkest px within CORE_R plate px; the share of the way
#                                           from the paper to it
SMOOTH = 0.4                              # plate px: the line mask's Gaussian, cut at half
SPECK = 3                                 # plate px^2: smaller pieces of ink are specks of the print
SEAL = 6                                  # plate px: passages narrower than this do not join ground to figure
# the heads (hair, wreaths, eyes), boxes in plate px: the woman, the king, the old man, the boy
HEADS = [(455, 1235, 650, 1385), (945, 1310, 1105, 1475), (1615, 1175, 1770, 1350), (1975, 1455, 2140, 1610)]
HEAD = dict(half=0.5, smooth=0.6)
TRACE_H = 7200                            # traced tall, as ecclesiazusae.py (thin lines break into dashes at 4000)
# The upper row and the beaded line: ink pieces whose lowest point lies above ROW (a polyline, plate px, under the
# beads; the beaded line steps up at the left ribbon) are dropped, but for those lying wholly inside KEEP (boxes, plate
# px: the woman's head, the old man's head, the top of his staff, which rise through the beads; a rule keeping every
# piece that touched them kept the shield and Demeter's feet); and the beads themselves: small round pieces (under BEAD
# plate px^2, no side over BEAD_W plate px) within BEAD_D plate px of BEADS (a polyline through their centres)
ROW = [(56, 1312), (840, 1318), (860, 1284), (1450, 1280), (1700, 1282), (2170, 1282)]
KEEP = [(452, 1232, 650, 1335), (1615, 1150, 1810, 1335), (1350, 1255, 1445, 1335)]
BEADS = [(56, 1300), (300, 1306), (600, 1313), (740, 1317), (830, 1306), (870, 1285), (1300, 1272), (1700, 1270),
         (2170, 1272)]
BEAD, BEAD_W, BEAD_D = 50, 10, 9
# ink cut away outright inside CUTS (polygons, plate px): the ribbons hanging from the garland (John, 2026-10-13: out;
# they end at y 1380, the winged figures on the throne start at 1395), and the hem of Demeter's robe where the old man's
# staff top (its roof's apex at 1397, 1262) reaches it
CUTS = [[(835, 1150), (895, 1150), (895, 1388), (835, 1388)], [(1150, 1150), (1200, 1150), (1200, 1388), (1150, 1388)],
        [(1290, 1150), (1600, 1150), (1600, 1272), (1437, 1272), (1397, 1258), (1355, 1272), (1290, 1272)]]
# ink pieces lying wholly inside EDGES (boxes, plate px): the page's gutter at the left, the plate's border at the right
EDGES = [(56, 1150, 67, 2140), (2124, 1300, 2170, 1545)]
# the ground line: the upper of the two printed over the meander, its centre followed column by column; the ink below
# it, more than GROUND_DOWN plate px under its centre, dropped (the lower line, the meander)
GROUND_LINE = [(204, 2122), (240, 2120), (340, 2113), (440, 2106), (540, 2101), (640, 2096), (740, 2093), (840, 2089),
               (940, 2086), (1040, 2082), (1140, 2079), (1240, 2075), (1340, 2072), (1440, 2070), (1540, 2068),
               (1640, 2068), (1740, 2076), (1840, 2072), (2170, 2060)]
GROUND_DOWN = 4
# the lines redrawn crisp along their centres (as ecclesiazusae.py); inside HEADS with shorter spurs and pieces (the
# curls are short)
SPUR, LINE_LEN, LINE_W, WIDTH_S, JOINT = 6, 10, 1.5, 4, 3
HEAD_SPUR, HEAD_LEN = 2, 3
# but kept as printed: the solid black (the hair, the beards' curls, the broad bands), what an opening by SOLID_R plate
# px leaves of the ink (the pen lines are about 2 plate px wide), grown back by a work px over the ink; and small marks
# under DOT plate px^2 (the dots of the king's mantle, the wreaths' berries), which a centre line drops; and inside EYES
# (boxes, plate px) the ink as printed
SOLID_R, DOT = 1.5, 40
EYES = []
# small closed parts (boxes, plate px): the paper the ink closes there, after a closing by CLOSE plate px, is clay
CLOSED = []
CLOSE = 5
# points on the ground (plate px): the paper areas they fall in are vase ground; every other area the lines close is
# clay; areas reaching the crop's edge are ground. John ruled them by number on pass 1's area map (2026-10-13): behind
# the old man between his staff and the boy; between the staff and the throne; under the woman's mirror hand; between
# the basin's stand and her robe; between the throne's legs (two); between the throne and the footstool; between the
# footstool's feet (two); and on pass 3 ("one little bit of ground is still clay. by the child's branch"): between the
# branch's lower leaves and the old man's wrist
GROUND = [(1909, 1944), (1428, 1898), (285, 1570), (425, 1776), (982, 1910), (992, 2027), (1183, 2054), (1362, 2057),
          (1288, 2059), (1909, 1566)]
# specks of the print: ink pieces under SPECK_MAX plate px^2 farther than NEAR plate px from the figures, and under
# SPECK_IN anywhere
SPECK_MAX, NEAR, SPECK_IN = 150, 6, 6
# John's marks in PhotoCraft over each pass, on the crop at MARKS_K x the plate px (his layer alone): blue is ink as he
# drew it, traced at its own size (as trace_svg's dots, so the pinned weight is not moved); green rules the area it lies
# in ground, yellow clay (John, 2026-10-13: "green = ground; yellow = that area bounded by ink lines is clay; blue =
# ink"). A mark rules the areas holding at least MARK_SHARE of its largest share, so a stroke that strays over a line
# into the next area does not rule that one too. Marks 1 (2026-10-13), on pass 1: gaps closed in the old man's head and
# hands, Oedipus' eye and beard, the woman's head; ground between the plant's leaves, the throne's legs, the woman's
# fillets, the boy's branch, the old man's fingers; clay in the staff top's frame, the bird on the sceptre, the hems
MARKS_FILES = [Path(__file__).with_name("oedipus_tyrannus_marks_1.png")]
MARK_SHARE = 0.3
MARKS_K = 2
MARKS_X0, MARKS_Y0 = X0, Y0                # the marks' grid: the whole crop
# a development run on part of the plate: OT_BOX="x0,y0,x1,y1" (plate px); the drawing goes to OT_OUT
if os.environ.get("OT_BOX"):
    X0, Y0, X1, Y1 = map(int, os.environ["OT_BOX"].split(","))
    OUT = Path(os.environ["OT_OUT"])
WEIGHT = float(os.environ.get("OT_WEIGHT", 2.0)) / max(X1 - X0, Y1 - Y0)   # 2.0 plate px, about the plate's own pen
#                                           width (John, 2026-10-13, from 1.6, 2.0 and 2.4 on Oedipus' head)


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
    """John's blue, green and yellow at the work px (shape: the work arrays')."""
    out = [np.zeros(shape, bool) for _ in range(3)]
    for mf in MARKS_FILES:
        a = np.asarray(Image.open(mf).convert("RGBA")).astype(int)
        r, g, b, al = (a[..., i] for i in range(4))
        on = al > 40
        x0, y0 = (X0 - MARKS_X0) * MARKS_K, (Y0 - MARKS_Y0) * MARKS_K   # (a development run's box inside it)
        for m, c in zip(out, (on & (b > r + 40) & (b > g + 20), on & (g > r + 40) & (g > b + 20),
                              on & (r > b + 60) & (g > b + 60))):
            c = c[y0:y0 + (Y1 - Y0) * MARKS_K, x0:x0 + (X1 - X0) * MARKS_K]
            m |= np.asarray(Image.fromarray(c.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.NEAREST)) > 0
    return out


def ruled(mark, labels):
    """The labels a mark rules: for each piece of the mark, those under it holding at least MARK_SHARE of the largest
    count (label 0, the ink, never)."""
    hit = set()
    lab, n = ndi.label(mark)
    for i, s in enumerate(ndi.find_objects(lab), 1):
        v, c = np.unique(labels[s][(lab[s] == i) & (labels[s] > 0)], return_counts=True)
        if len(v):
            hit |= set(v[c >= MARK_SHARE * c.max()].tolist())
    return list(hit)


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


def line_y(pts, shape):
    """A polyline (plate px) as its height in work px at every work column."""
    px, py = np.array(pts, float).T
    return (np.interp((np.arange(shape[1]) + 0.5) / UP + X0, px, py) - Y0) * UP


def upper_row(ink):
    """ink less the upper row and the beads (ROW, KEEP, BEADS)."""
    lab, n = ndi.label(ink)
    rows = np.arange(ink.shape[0])[:, None]
    low = np.full(n + 1, -1)
    np.maximum.at(low, lab[ink], np.broadcast_to(rows, ink.shape)[ink])
    keep = np.zeros(ink.shape, bool)
    for b in KEEP:
        keep[sl(b)] = True
    kept = np.bincount(lab[~keep & ink], minlength=n + 1) == 0
    cols = np.zeros(n + 1, int)
    cols[lab[ink]] = np.nonzero(ink)[1]
    above = (low < line_y(ROW, ink.shape)[cols]) & ~kept
    # the beads: small round pieces near their line
    size = np.bincount(lab.ravel(), minlength=n + 1)
    objs = ndi.find_objects(lab)
    by = line_y(BEADS, ink.shape)
    bead = np.zeros(n + 1, bool)
    for i, s in enumerate(objs, 1):
        if s is None or size[i] >= BEAD * UP * UP:
            continue
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        cy, cx = (s[0].start + s[0].stop) / 2, (s[1].start + s[1].stop) / 2
        bead[i] = max(h, w) <= BEAD_W * UP and abs(cy - by[int(cx)]) <= BEAD_D * UP
    drop = above | bead
    drop[0] = False
    return ink & ~drop[lab]


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


def figure(ink, ws, green, yellow):
    """The figures' area: every paper area but the ground (GROUND, the areas reaching the crop's edge, and those John
    marked green; but those he marked yellow are clay), and the ink touching them."""
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    pts = [at(ws, x, y) for x, y in GROUND if X0 <= x < X1 and Y0 <= y < Y1]
    # paper the seal leaves without a seed is clay, unless it reaches the crop's edge or John marked it
    lab, _ = ndi.label((ws == 0) & ~ink)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    yw, yl = ruled(yellow, ws), ruled(yellow, lab)
    ground = ((np.isin(ws, np.r_[out[out > 0], pts, ruled(green, ws)]) & ~np.isin(ws, yw))
              | np.isin(lab, ruled(green, lab)))
    clay = ((ws > 0) | ((lab > 0) & ~np.isin(lab, edge)) | np.isin(lab, yl)) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~ground, ground


def level_svg(svg):
    """The levelling turn (LEVEL) round the drawing, and its view box cut to LEVEL_VIEW."""
    s = svg.read_text()
    s = re.sub(r'viewBox="[^"]+"', f'viewBox="{LEVEL_VIEW}"', s, count=1)
    s = s.replace('<g transform="scale(', f'<g transform="rotate({LEVEL} {LEVEL_C[0]:g} {LEVEL_C[1]:g})"><g transform="scale(', 1)
    head, _, tail = s.rpartition("\n</svg>")
    svg.write_text(head + "\n</g></svg>" + tail)


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    for box in HEADS:
        b = sl(box)
        if ink[b].size:
            x0, y0, x1, y1 = box
            hb = (max(x0, X0), max(y0, Y0), min(x1, X1), min(y1, Y1))
            ink[sl(hb)] = masks(src, hb, **HEAD)[2]
    for pts in CUTS:
        ink &= ~lw.polygon_mask(ink.shape, (np.array(pts, float) - (X0, Y0)) * UP)
    ink = drop_inside(upper_row(ink), EDGES)
    below = np.arange(ink.shape[0])[:, None] > line_y(GROUND_LINE, ink.shape)[None, :] + GROUND_DOWN * UP
    ink &= ~below
    heads = np.zeros_like(ink)
    for box in HEADS:
        heads[sl(box)] = True
    printed = ink                                     # (the areas are sealed on these as well: the redraw opens gaps)
    lab, n = ndi.label(ink)
    dot = (np.bincount(lab.ravel(), minlength=n + 1) < DOT * UP * UP)[lab] & (lab > 0)
    for box in EYES:
        dot[sl(box)] |= ink[sl(box)]
    solid = ink & ndi.binary_dilation(ndi.binary_opening(ink, structure=morphology.disk(SOLID_R * UP)))
    ink = (redraw(ink & ~heads & ~dot, SPUR, LINE_LEN) | (redraw(ink & heads & ~dot, HEAD_SPUR, HEAD_LEN) & heads)
           | dot | solid)
    blue, green, yellow = marks(ink.shape)
    ws = areas(ink | printed | blue)
    fig, ground = figure(ink | printed | blue, ws, green, yellow)
    del printed
    fig |= ndi.binary_dilation(blue, iterations=UP) & ~ground
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
    drop = ((size < SPECK_MAX) & ~near) | (size < SPECK_IN)
    drop[0] = False
    ink &= ~drop[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    lw.WORK_H = TRACE_H
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, trace_h=TRACE_H, keep=kept, dots=blue,
        title="Oedipus enthroned, Teiresias led by a boy, and Jocasta with a mirror",
        desc="Line drawing after Raoul-Rochette's 1833 plate of the Sbani vase (Monumens inédits, pl. 78); retraced.")
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))
    level_svg(OUT)                        # last: the check images are drawn on the unturned grid


if __name__ == "__main__":
    main(*sys.argv[1:4])
