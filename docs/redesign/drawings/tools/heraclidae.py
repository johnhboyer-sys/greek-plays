"""Children of Heracles: Heracles brings the Erymanthian boar to Eurystheus, who hides in a storage jar, with a
nymph and Iolaos at the left and Athena and Hermes at the right, from Gerhard, Auserlesene griechische Vasenbilder
II (Berlin, 1843), Taf. XCVII, fig. 1, as scanned by Heidelberg University Library (Public Domain Mark): the panel
of fig. 1 alone, taken from the IIIF server as the region 176,244,1572,1058 of the plate's 1963 x 2767 scan
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_097.jpg/176,244,1572,1058/full/0/default.jpg
(page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0223; the server offers no PNG). Plate px below are
px of that region.
Gerhard's text (pp. 46-47, "Der erymanthische Eber"): an archaic amphora of the Candelori collection; Eurystheus
raises his arm to beg Heracles to spare him the sight; Athena and Hermes at the right, Iolaos and the nymph of the
Erymanthian valley at the left; on the reverse Ajax carries Achilles' body, Briseis ahead, a hoplite and an archer
behind. The amphora "jetzt zu München" in his note 34 (d) is another Candelori vase (Munich 1562, named figures).
Present location not confirmed: New York, Metropolitan Museum 56.171.20 (Antimenes Painter, about 520 BC) pairs the
same two pictures in the same order of figures, and may be it.
John's pick (2026-10-13); the crop (John, 2026-10-15): the whole panel, the figure numbers and the small vase
drawings below it left out. The faint head Gerhard prints in thin brown lines on the clay between Iolaos and
Heracles, the line curling up from the club and the line by the boar's hind leg are left out (John, 2026-10-15).
Approved by John on pass 3, 2026-10-16, after two rounds of his marks in PhotoCraft.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the enlargement, the
grey, the warm channel (Channel Mixer), the blurs, Motion Blur, Minimum and Maximum, and the thresholds. numpy and
scipy only combine the masks PhotoCraft made (labels, unions, openings, distances, fills) and measure. The SVG is
written in the house format directly, as for Seven, Lysistrata and Hecuba.

Plate -> drawing, black-figure, drawn as silhouettes (as Seven, Ajax, Lysistrata, Hecuba, Cyclops and Birds):
  - Out: the paper round the panel (EDGES, the panel's four edges, measured; the panel prints a little askew).
  - Ground: the orange clay (warm: red less blue over WARM_T, and lighter than CLAY_L), its large areas.
  - The added purple, which Gerhard prints as fine black hatching on the clay (beards, the nymph's mantle, the
    diadem, the crest-holder, the club): found as the close thin lines (PURPLE_*), part of the figures, and drawn as
    printed, its strokes black, open on the ground (John's choice from a test against a grey wash, 2026-10-15).
  - The figures: all else in the panel, joined to SEEDS (the faint lines on the clay join none of them).
  - The black is drawn black. Open in it: the incisions and the clay dots (light marks, at least LINE_W wide),
    and the added white (skin, dots), with the dark lines printed on it (found on a Levels-stretched copy: John,
    "play with levels to help reveal lines"). Where the white meets the ground, one even contour LINE_W wide just
    inside its edge, over Gerhard's printed contour (John: "Not a clean single line for outline").
  - John's marks, two rounds in PhotoCraft (MARKS_FILES, apply_marks): blue lines, green no ink, yellow clay.
  - Dark theme: the figures' area is clay, a RIM wider than the black, so the black reads on the dark page; the
    marks and the white show clay.

    python3 docs/redesign/drawings/tools/heraclidae.py gerhard-AV-II-XCVII-1.jpg [qa.png] [dump.npz]
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

OUT = Path(__file__).resolve().parent.parent / "heraclidae.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 0, 0, 1572, 1058          # crop in plate px: the whole region
UP = 3                                     # work at 3x the plate's px
# the panel's edges (plate px), measured where the clay meets the paper: top y = a x + b, left x = a y + b,
# right x = a y + b, bottom y = a x + b; outside them (and EDGE_IN inside), paper
EDGES = {"top": (-0.0133, 16.3), "left": (0.0110, -2.7), "right": (0.0117, 1563.8), "bottom": (-0.0098, 1060.9)}
EDGE_IN = 2.0
# the faint brown lines on the clay are left out (John, 2026-10-15: the head between Iolaos and Heracles, the line
# curling up from the club, the line down from the boar's hind leg); they join no figure but the last, which runs
# into the hoof: its stretch beside the hoof, out (DROP, polygons in plate px)
DROP = [[(974, 377.5), (980, 377.5), (993, 356), (987, 353)]]
WARM_T, CLAY_L = 80, 120                   # clay: red less blue over WARM_T, grey over CLAY_L
DARK_T = 110                               # the black and the printed lines: darker than this
BLACK_T = 95                               # light marks in the black: lighter than this (or by the top-hat)
# the purple's hatching: dark strokes no wider than PURPLE_THIN plate px, closed over PURPLE_GAP plate px into an
# area, at least PURPLE_MIN plate px^2, under PURPLE_DARK dark and under PURPLE_WHITE added white
PURPLE_THIN, PURPLE_GAP, PURPLE_MIN, PURPLE_DARK, PURPLE_WHITE = 1.5, 2.5, 60, 0.65, 0.3
# the added white: lighter than WHITE_T, red less blue under WHITE_WARM, then out to WHITE_EDGE beside it
WHITE_T, WHITE_WARM, WHITE_EDGE = 175, 75, 150
WHITE_MIN = 6                              # plate px^2
WHITE_SMALL, WHITE_LINE = 40, 3
WHITE_LEVELS, WHITE_LINE_T, WHITE_LINE_W = (130, 235), 40, 1.3
EDGE_LINE, SKIN_SMOOTH = 2.5, 1.0               # plate px
AUTO_GROUND = 30                           # plate px^2: clay areas this large are ground
WIDE_CLAY = 2.5
POCKETS = []
SEEDS = [(200, 650), (380, 700), (650, 700), (880, 900), (1130, 700), (1350, 600)]
LINE_W = 1.5                               # plate px: the outline and the thinnest mark
RIM = 1.5                                  # plate px: the clay round the black on the dark theme
GRAIN = 6                                  # plate px^2: light specks in the black smaller than this are grain
MARK_T = 25
# the black worn to a speckle (the jar and Eurystheus over its rim; the lower end of Athena's dress): boxes (plate px)
# where a light mark counts only if it runs WORN_SPAN plate px or more, or is a dot as light as WORN_DOT (wear leaves
# no line)
WORN = [(860, 830, 1150, 1058), (950, 745, 1070, 830), (1140, 690, 1205, 980)]
WORN_SPAN, WORN_DOT = 12, 200
ORIENT_D, ORIENT_STEP = 4, 15
NEAR_WHITE = 2.5
EDGE_CLEAR = 1.5
SMOOTH = 0.4
# John's marks on pass 1, in PhotoCraft over the full-res export (heraclidae_marks_1.png, his layer alone, on the
# tool's grid; 2026-10-15): blue lines replace mine (the beard's hatching, the nymph's arms and feet, the hand clasp,
# the pockets by her neck and in the boar's leg, a toe), green takes ink out (my black past the plate's edge on the
# bow and quiver, the faint head's ear where it touched the bow, the incisions on Heracles' head and Iolaos'
# moustache). Round 2, on pass 2 (heraclidae_marks_2.png, his three layers merged; 2026-10-16): blue and green as
# round 1, and yellow for clay with no ink (John: "clay no ink"): Athena's profile redrawn, Hermes' ear, beard and
# cloak hatching, the incisions on a black hand, the spear and leg edges by Hermes, the nymph's fingers and feet
MARKS_FILES = [Path(__file__).parent / "heraclidae_marks_1.png", Path(__file__).parent / "heraclidae_marks_2.png"]
REPLACE = 2.5                              # plate px
OPEN_MAX = 60                              # plate px^2
SLIVER = 20                                # plate px^2
PINHOLE = 3                                # plate px^2
COVER = 0.5
LOOP_MIN = 30                              # plate px^2
# the hatching's strokes: the dark top-hat (the plate less its Maximum then Minimum over 1 plate px) over HATCH_T,
# taken on the plate smoothed along its strokes and stretched by Levels (LEVELS: input black and white), so the
# paler strokes at the purple's edges (Iolaos' beard tip; John, 2026-10-15: "you are omitting part of the beard")
# stand out as well as the dark ones (John: "play with levels to help reveal lines"); drawn at their printed width
LEVELS = (100, 180)
HATCH_T = 60


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def pc_mask(m, *steps):
    """A mask run through PhotoCraft (steps as for pc), back as a mask (grey 128 and over)."""
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "m.png", Path(td) / "o.png"
        Image.fromarray(m.astype(np.uint8) * 255).save(a)
        pc(a, b, *steps)
        return grey(b) >= 128


def smooth(m, r):
    """m with its edges smoothed: PhotoCraft's Gaussian Blur r plate px, then Threshold at half."""
    return pc_mask(m, ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": r * UP}),
                   ("image.adjustments.threshold", {"level": 128}))


def thick(m, w):
    """m, every part at least w plate px wide (thin marks widened along their centres)."""
    return m | (ndi.distance_transform_edt(~morphology.skeletonize(m)) <= w * UP / 2)


def at(x, y):
    """Plate px -> work px (row, col)."""
    return round((y - Y0) * UP), round((x - X0) * UP)


def oriented(t, src_png, name):
    """src_png smoothed along its own strokes (ORIENT_*): PhotoCraft's Motion Blur at each angle; numpy picks,
    per pixel, the blur at the strokes' direction (as hecuba.py)."""
    g = grey(src_png)
    angs = list(range(0, 180, ORIENT_STEP))
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    del gx, gy
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    out = np.zeros_like(g)
    for k, a in enumerate(angs):                   # (one blur at a time: the whole stack does not fit)
        pc(src_png, t / f"{name}{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
        out = np.where(i == k, grey(t / f"{name}{a}.png"), out)
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(t / f"{name}.png")
    return t / f"{name}.png"


def apply_marks(lines, fig, ground, white, purple, path):
    """John's marks (his PhotoCraft layer alone, on the tool's grid) laid in. Green takes ink out as painted (where it
    opens onto the ground, that is ground). Blue (John, round 1: "Replace"): his strokes are drawn LINE_W wide along
    their centres, and a sliver of clay mostly under his paint is black (by the toe);
    within REPLACE of them my thin lines on and by the white go (not the solid black, or a slit of clay opened along
    his line on the black's edges); inside a loop he
    closes, my ink goes (the pockets). Yellow (round 2) is clay with no ink. In the hatching his strokes are the ones I missed, between mine: added, mine
    kept. (A rule making the ground side of each stroke ground took the wrong side on the black's edges: not used.)"""
    m = np.asarray(Image.open(path).convert("RGBA")).astype(int)
    assert m.shape[:2] == lines.shape, (m.shape, lines.shape)
    r, g, b, a = (m[..., i] for i in range(4))
    green = (a > 40) & (g > r + 40) & (g > b + 20)
    blue = (a > 40) & (b > r + 40) & (b > g + 20)
    blue = morphology.remove_small_holes(blue, max_size=PINHOLE * UP * UP)   # (pinholes in his paint)
    # (yellow, round 2: clay, no ink, never ground. Along the black it opens a clay line LINE_W wide on his stroke's
    # centre (his brush is broader than an incision); on and by the white it clears my ink as painted)
    yellow = (a > 40) & (r > 150) & (g > 150) & (b < 100)
    by_white = ndi.distance_transform_edt(~white) <= 2 * REPLACE * UP
    clay_line = (ndi.distance_transform_edt(~morphology.skeletonize(yellow)) <= LINE_W * UP / 2) | (yellow & by_white)
    sk = morphology.skeletonize(blue)
    lines0 = lines
    near = ndi.distance_transform_edt(~blue) <= REPLACE * UP
    # (beside his strokes, not past their ends: cleared there too, my line was cut where his short strokes meet it)
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    tips = sk & (nb == 1)
    if tips.any():
        near &= ~(ndi.distance_transform_edt(~tips) <= ndi.distance_transform_edt(~sk) + 1)
    solid = ndi.binary_opening(lines, structure=morphology.disk(round(LINE_W * UP)))
    thin = lines & ~ndi.binary_dilation(solid, structure=morphology.disk(UP))
    # (a loop is a pocket's edge: the clay reaches its centre line, the black outside it is the line)
    # (only a loop round more than LOOP_MIN plate px^2: the skeleton of a broad dab rings a few px, and cleared they
    # came out slits of clay in the black)
    loops = ndi.binary_fill_holes(sk) & ~sk
    loops = ndi.binary_dilation(morphology.remove_small_objects(loops, max_size=LOOP_MIN * UP * UP), structure=np.ones((3, 3), bool)) & ndi.binary_fill_holes(sk) & ~purple
    line = (ndi.distance_transform_edt(~sk) <= LINE_W * UP / 2) & ~loops
    cut = near & thin & ~purple & (ndi.distance_transform_edt(~white) <= 2 * REPLACE * UP)
    # (where my line meets his stroke side-on, as at the clasp, grow it back through the cut until it meets his line
    # (at most REPLACE): cut whole, it stopped short of his stroke)
    keep = lines & ~cut
    grown = keep.copy()
    for _ in range(round(REPLACE * UP)):
        grown = grown | (ndi.binary_dilation(grown) & cut & ~line)
    lines = grown & ~green
    # (a sliver of clay (in my pass) mostly under his paint, under SLIVER plate px^2, is black: the false slits along the black's
    # edges he painted over (the hair, a toe); the pockets he outlined in his broad brush stay clay)
    lab, n = ndi.label(~lines0)
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    cov = np.bincount(lab[blue].ravel(), minlength=n + 1)
    fill = (sz <= SLIVER * UP * UP) & (cov >= COVER * sz)
    fill[0] = False
    lines |= fill[lab] & ~purple
    lines = (lines | line) & ~loops
    # (black his stroke closes off against the ground, at most OPEN_MAX plate px^2: ground, as the clay wedge's tip
    # under his peak on Hermes' cloak)
    shut = ndi.binary_fill_holes(line | ground) & ~line & ~ground
    lab, n = ndi.label(shut)
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    hit = np.zeros(n + 1, bool)
    hit[np.unique(lab[near & shut])] = True
    # (and wider than a line: the strip his line pinched off against the ground's edge came out a slit of clay)
    wide = ndi.maximum(ndi.distance_transform_edt(shut), lab, np.arange(n + 1)) > LINE_W * UP
    shut = ((sz <= OPEN_MAX * UP * UP) & hit & wide)[lab] & (lab > 0)
    lines &= ~shut & ~clay_line
    # (green that opens onto the ground is ground; green inside the black stays the figure's clay)
    lab, _ = ndi.label((green & ~lines) | ground | shut)
    fig = fig & ~shut & ~(green & np.isin(lab, np.unique(lab[ground])))
    return lines, fig | lines


def write_svg(lines, body, out, title, desc):
    """The house format (as linework.trace_svg writes it): 1000 units tall, the body path under the lines, traced
    at the work px (as hecuba.py)."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        pc(t / "up.png", t / "warm.png", ("image.adjustments.channelMixer", {"gray": [100, 0, -100, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        Lo = oriented(t, t / "L.png", "Lo")
        pc(Lo, t / "Lo_open.png", ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}))
        pc(Lo, t / "Lv.png", ("image.adjustments.levels", {"inBlack": LEVELS[0], "inWhite": LEVELS[1]}))
        pc(t / "Lv.png", t / "Lv_close.png", ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}))
        L, W = grey(t / "L.png"), grey(t / "warm.png")
        light_hat = grey(Lo) - grey(t / "Lo_open.png")
        dark_hat = grey(t / "Lv_close.png") - grey(t / "Lv.png")
        pc(Lo, t / "Lw.png", ("image.adjustments.levels", {"inBlack": WHITE_LEVELS[0], "inWhite": WHITE_LEVELS[1]}))
        pc(t / "Lw.png", t / "Lw_close.png", ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}))
        white_hat = grey(t / "Lw_close.png") - grey(t / "Lw.png")
    H, Wd = L.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    del xx, yy

    # out: the paper round the panel
    e = EDGES
    outside = ((py < np.polyval(e["top"], px) + EDGE_IN) | (py > np.polyval(e["bottom"], px) - EDGE_IN)
               | (px < np.polyval(e["left"], py) + EDGE_IN) | (px > np.polyval(e["right"], py) - EDGE_IN))
    for pts in DROP:
        outside |= lw.polygon_mask(L.shape, np.array([((x - X0) * UP + 0.5, (y - Y0) * UP + 0.5) for x, y in pts]))

    # the purple's hatching: thin dark strokes (the dark top-hat over HATCH_T, off the black), closed
    # into areas; an area that is mostly dark is the black between close incisions, not hatching
    clay = (W > WARM_T) & (L > CLAY_L)
    dark = (L < DARK_T) & ~outside
    # (the black without the thin strokes: where the strokes print close, the dark alone runs them into a solid)
    solid = ndi.binary_opening(dark & ~(dark_hat > HATCH_T), structure=morphology.disk(round(PURPLE_THIN * UP)))
    strokes = (dark_hat > HATCH_T) & ~ndi.binary_dilation(solid, structure=morphology.disk(UP)) & ~outside
    purple = ndi.binary_closing(strokes, structure=morphology.disk(round(PURPLE_GAP * UP)))
    purple = ndi.binary_fill_holes(ndi.binary_opening(purple, structure=morphology.disk(round(PURPLE_THIN * UP))))
    lab, n = ndi.label(purple)
    area = np.bincount(lab.ravel(), minlength=n + 1)
    darkf = np.bincount(lab.ravel(), weights=dark.ravel(), minlength=n + 1) / np.maximum(area, 1)
    # (and one lying on the added white is lines printed on it, a necklace, not hatching)
    whitef = np.bincount(lab.ravel(), weights=((L > WHITE_T) & (W < WHITE_WARM)).ravel(), minlength=n + 1) / np.maximum(area, 1)
    ok = (area > PURPLE_MIN * UP * UP) & (darkf < PURPLE_DARK) & (whitef < PURPLE_WHITE)
    ok[0] = False
    purple = ok[lab] & ~solid

    # ground: the clay, opened so thin marks do not join it; its large areas
    ground0 = ndi.binary_opening(clay & ~outside & ~purple, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[at(x, y)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]
    core = ndi.distance_transform_edt(clay) > WIDE_CLAY / 2 * UP
    ground = ndi.binary_propagation(ground, mask=clay & ~outside & ~purple
                                    & (ndi.distance_transform_edt(~core) <= WIDE_CLAY / 2 * UP))
    del core

    # the figures: all else, joined to the seeds
    lab, _ = ndi.label(ndi.binary_opening(~ground & ~outside, structure=morphology.disk(UP)))
    keep = {lab[at(x, y)] for x, y in SEEDS}
    assert 0 not in keep, 'a seed is off the figures'
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: what is left out)
        if sl is not None and k not in keep and sz[k] > 20 * UP * UP:
            print('left out', sz[k] // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP,
                  X0 + sl[1].stop // UP, Y0 + sl[0].stop // UP)
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground & ~outside
    purple &= fig
    # (the clay between the hatching's last stroke and the black beside it is purple too)
    purple |= fig & ~solid & (ndi.distance_transform_edt(~purple) <= PURPLE_GAP * UP)

    # the added white
    white = ndi.binary_opening((L > WHITE_T) & (W < WHITE_WARM) & fig, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > WHITE_MIN * UP * UP)[lab]
    # (a pale speck of the print in a light line is not added white: John, pass 1, "Why do these ink 'joins' appear
    # between black ink areas?" The guard round the white then cut the line. A white patch under WHITE_SMALL plate
    # px^2 goes when the light area it lies in (lighter than BLACK_T) is over WHITE_LINE times its size and holds no
    # larger white: a line, not a dot, nor an eye's white in a face)
    lab, n = ndi.label(white)
    wsize = np.bincount(lab.ravel(), minlength=n + 1)
    small = wsize < WHITE_SMALL * UP * UP
    llab, ln = ndi.label((L > BLACK_T) & fig)
    lsize = np.bincount(llab.ravel(), minlength=ln + 1)
    big = np.zeros(ln + 1, bool)
    big[np.unique(llab[(lab > 0) & ~small[lab]])] = True
    host = np.zeros(n + 1, int)
    host[lab[lab > 0]] = llab[lab > 0]
    drop = small & (lsize[host] > WHITE_LINE * wsize) & ~big[host]
    drop[0] = True
    white &= ~drop[lab]
    white |= fig & (L > WHITE_EDGE) & (W < WHITE_WARM) & (ndi.distance_transform_edt(~white) <= NEAR_WHITE * UP)
    # the thin brown lines printed on the white (brows, lids, mouths, fingers, the necklaces): the dark top-hat of
    # the plate stretched over the white's range by Levels (WHITE_LEVELS), over WHITE_LINE_T, in the white or at
    # its edge; they are black, drawn at their printed width
    wl = (white_hat > WHITE_LINE_T) & ndi.binary_dilation(white, structure=morphology.disk(UP)) & fig
    wl = thick(wl, WHITE_LINE_W) & fig            # (at least WHITE_LINE_W wide: thinner, the smoothing broke them)
    white &= ~wl
    # the white's contour where it meets the ground: one even line (John, 2026-10-15, on pass 1's faces: "Not a clean
    # single line for outline"). The plate prints a brown contour along the white's edge, and an outline beside it
    # drew it twice: the white is taken out over that printed contour (the lines on the white within EDGE_LINE
    # plate px of the ground) to the figure's edge, smoothed (SKIN_SMOOTH), and the contour drawn LINE_W wide inside
    # its edge where it meets the ground; the figure's ragged px beside it go
    near_g = ndi.distance_transform_edt(fig) <= EDGE_LINE * UP
    edge_wl = wl & near_g
    wl &= ~edge_wl
    sk0 = white | edge_wl
    skin = smooth(sk0, SKIN_SMOOTH) & ndi.binary_dilation(sk0, structure=morphology.disk(UP)) & ~outside
    rag = near_g & ~skin & ndi.binary_dilation(skin, structure=morphology.disk(round(EDGE_LINE * UP)))
    fig = (fig & ~rag) | skin
    contour = skin & (ndi.distance_transform_edt(fig) <= LINE_W * UP)
    white = skin & ~contour & ~wl
    # the light marks in the black (incisions, the clay and white dots), at least LINE_W wide
    clear = (ndi.distance_transform_edt(~white) > NEAR_WHITE * UP) & (ndi.distance_transform_edt(fig) > EDGE_CLEAR * UP)
    marks = fig & ~white & ~purple & clear & ((L > BLACK_T) | (light_hat > MARK_T))
    lab, _ = ndi.label(marks)
    marks &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    # (in the worn black, only the long incisions and the bright dots)
    worn = np.zeros_like(marks)
    for bx0, by0, bx1, by1 in WORN:
        worn |= (px >= bx0) & (px < bx1) & (py >= by0) & (py < by1)
    lab, n = ndi.label(marks & worn)
    span = np.zeros(n + 1)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        span[k] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) / UP
    bright = ndi.maximum(L, lab, np.arange(n + 1)) >= WORN_DOT
    ok = (span >= WORN_SPAN) | bright
    ok[0] = True
    marks &= ok[lab]
    marks = thick(marks, LINE_W) & fig & ~white & ~purple & clear
    # the black: all the rest of the figures (the white's contour with it). The purple
    # is drawn as printed: its strokes black at their printed width, the clay between, and no outline where it
    # meets the ground (John, 2026-10-15, from a test against a grey wash: "hatching as printed", "open, as
    # printed")
    black = fig & ~marks & ~white & ~purple
    lines = smooth(black | (purple & strokes), SMOOTH)
    for mf in MARKS_FILES:
        lines, fig = apply_marks(lines, fig, ground, white, purple, mf)
    body = ndi.distance_transform_edt(~fig) <= RIM * UP
    if dump:
        np.savez_compressed(dump, L=L.astype(np.uint8), dhat=dark_hat.astype(np.int16), fig=fig, white=white, lines=lines, ground=ground,
                            marks=marks, purple=purple, outside=outside)

    info = write_svg(
        lines, body, OUT,
        title='Heracles brings the Erymanthian boar to Eurystheus',
        desc='Line drawing after the 1843 plate of a black-figure amphora (Gerhard, Auserlesene griechische '
             'Vasenbilder II, Taf. XCVII, 1): Heracles brings the boar to Eurystheus, who hides in a storage jar, '
             'with a nymph and Iolaos at the left and Athena and Hermes at the right; retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
