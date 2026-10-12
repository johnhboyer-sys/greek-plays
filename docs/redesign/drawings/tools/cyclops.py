"""Cyclops: Odysseus' men driving the stake into the eye of the sleeping Polyphemus, from E. Saglio, "Polyphème",
Gazette archéologique 12 (Paris, 1887), pl. 1, as photographed for the Internet Archive (published 1887, public
domain): item gazette-archeologique_1887_12, the original capture of leaf 419,
gazette-archeologique_1887_12_orig_0419.jp2 (6000 x 4000, the book photographed upside down; converted to PNG
for PhotoCraft, which cannot read JPEG 2000).
Saglio's text (pp. 1-7): an oinochoe with a trefoil mouth from the Campana collection (no. 954 of its Rome
catalogue), in the Louvre since 1862, unpublished till then. Polyphemus, nude, half-reclines on a rock (traces of
its white remain), his club on his left arm, his eye shut; two men drive the stake, its tip smoking (close
brushstrokes); a third, turned away, plunges the end of a stake into the brazier (quick brushstrokes, the clay
showing through); added red, much faded, on the Greeks' hair and beards and belts; ivy above.
John's pick (Plate Picks 28-7Da, 2026-10-10); the drawing (2026-10-12): the group, the ivy and the fire.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the half-turn, the
crop, the enlargement, the grey, the warm channel (Channel Mixer), the blurs, Minimum and Maximum. numpy only
combines the masks PhotoCraft made (labels, unions, distances, fills) and measures. The SVG is written in the
house format directly, as hecuba.py.

Plate -> drawing, black-figure, drawn as a silhouette (John, 2026-10-12: "as Hecuba"):
  - Ground: the orange clay (warm: red less blue over WARM_T, and lighter than CLAY_L), its large areas.
  - The figures: all else that is not ground, inside the cuts.
  - The black is drawn black. Open in it: the incisions (light marks, at least LINE_W wide), and the added
    white (the rock), with an outline LINE_W wide where the white meets the ground.
  - The thinned glaze (the smoke at the stake's tip, the fire): a `tone` path, the line colour at the opacities SMOKE_STEPS.
  - Dark theme: the figures' area is clay, a RIM wider than the black, so the black reads on the dark page.

    python3 docs/redesign/drawings/tools/cyclops.py leaf0419.png [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "cyclops.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# plate px: the leaf turned upright (a half-turn of the capture); the crop: the panel inside its border bands
X0, Y0, X1, Y1 = 1730, 1440, 4170, 2615
if os.environ.get("CYCLOPS_BOX"):          # (a sub-crop, for working on one part: the same steps on a box)
    X0, Y0, X1, Y1 = (int(v) for v in os.environ["CYCLOPS_BOX"].split(","))
UP = 3                                     # work at 3x the plate's px
# The cuts. TOP: 2 px below the lower edge of the red band over the picture (measured every 100 columns). FLOOR: the top of the red ground line
# (measured where clay stands above it). LEFT: just right of the inner line of the left border band (its right edge read
# off the plate every 200 rows; the fire's black meets it, with only the print's stipple between). RIGHT: 1 px left
# of the right border band's first line (its edge read off the plate; the ivy's stems end on it), then through the
# clay strip between the picture and the band (its runs measured every 40 rows), round the end
# of Polyphemus' club, which lies over the band (CLUB, a least-cost path along the clay round it, straight
# across where the band's lines meet it)
TOP = (1453 + 2, 1900, 16 / 2000)          # y = TOP[0] + (x - TOP[1]) * TOP[2]: the band edge slopes 16 px over 2000
FLOOR = [(1730, 2602), (2160, 2601), (2620, 2601), (3150, 2601), (3920, 2605), (4170, 2606)]
FLOOR_CLEAR = 1.0
LEFT = [(1842, 1440), (1834, 1500), (1814, 1600), (1795, 1690), (1771, 1800), (1754, 2000), (1747, 2200), (1739, 2440), (1737, 2620)]
RIGHT = [(3959, 1462), lw.STRAIGHT, (3967, 1520), lw.STRAIGHT, (3974, 1570), lw.STRAIGHT, (3979, 1610), lw.STRAIGHT,
         (3984, 1650), lw.STRAIGHT, (3989, 1690), lw.STRAIGHT, (4001, 1760), lw.STRAIGHT, (4008, 1880), lw.STRAIGHT,
         (4007, 1960), lw.STRAIGHT, (4005, 2000), lw.STRAIGHT, (4002, 2030), lw.STRAIGHT]
# the club's end over the band: its outline read off the plate at 3x (plate px), along the clay round it, straight
# across where the band's lines meet it; inside it all is club (the band's clay there is the print's gap round it)
CLUB = [(4000, 2038), (4020, 2029), (4040, 2020), (4060, 2018), (4080, 2016), (4090, 2011), (4100, 2001), (4110, 1993), (4125, 1988),
        (4140, 1988), (4151, 1994), (4155, 2010), (4151, 2035), (4141, 2052), (4125, 2065), (4100, 2080), (4080, 2088),
        (4060, 2096), (4040, 2103), (4020, 2110), (4000, 2118), (3997, 2125)]
CLUB_CLEAR = 5                             # plate px: no light marks this near the club's read outline
KNOB = (4085, 1985, 4160, 2015)            # plate px: nor here (the band's clay that cuts into the knob's top)
RIGHT_LOW = [(3992, 2200), (3978, 2300), (3970, 2440), (3950, 2540), (3930, 2620)]
WARM_T, CLAY_L = 35, 45                    # clay: red less blue over WARM_T, grey over CLAY_L (clay 81-92, under the smoke 50-65)
BLACK_T = 45                               # light marks in the black: lighter than this (or by the top-hat)
MARK_T = 18
# light marks: the white top-hat (the plate less its Minimum then Maximum over 1 plate px) over MARK_T, taken on the
# plate smoothed along its own strokes (Motion Blur ORIENT_D plate px long, at every ORIENT_STEP degrees, as hecuba.py):
# the thinnest incisions (the hat's rim, the lids) print as dashes
ORIENT_D, ORIENT_STEP = 4, 15
JOIN_MAX, JOIN_RUN, JOIN_ANGLE = 7, 4, 30   # plate px, plate px, degrees: see join_marks
# the smoke at the stake's tip: a soft wash on the clay, redder than it (red less 1.6 green, PhotoCraft's Channel
# Mixer: the smoke 0-18, the clay -9-0, the black -11, so no mix of black and clay passes), smoothed by TONE_BLUR
# plate px, in areas wider than TONE_OPEN plate px and larger than TONE_MIN plate px^2, in steps (SMOKE_STEPS: the
# redness over each threshold at that opacity, as Andromache's blood; John chose the steps, 2026-10-12). The clay
# under it is ground; the figures there are only the black paint (grey under BLACK_CORE: the ivy's dots, the stake)
TONE_BLUR, TONE_OPEN, TONE_MIN = 4, 3, 300
SMOKE_STEPS = [[5, 0.12], [9, 0.22], [13, 0.32], [17, 0.42]]
BLACK_CORE = 35
SMOKE = [(3380, 1560), (3620, 1560), (3640, 1800), (3380, 1800)]   # plate px: the smoke lies inside this
# the hats' brims prolonged (Saglio: worn on the vase, seen only close to): thin brown lines on the clay round the
# hats, grey 45-60 on clay 75-83, too faint and broken to find whole. Each is a least-cost path along the dark (the
# plate darker than the clay round it: PhotoCraft's Maximum then Minimum over BRIM_R plate px, less the plate) through
# points read off the plate at 3x (plate px), drawn BRIM_W wide in the darkest step of the wash
BRIMS = [
    [(1960, 1551), (1990, 1552), (2020, 1561), (2036, 1564)],                    # first man: to the left
    [(2141, 1466), (2150, 1480), (2148, 1499)],                                  # above the crown
    [(2223, 1530), (2265, 1508), (2307, 1481)],                                  # to the right, rising
    [(2228, 1552), (2245, 1560), (2258, 1568)],                                  # to the right, low
    [(2505, 1461), (2528, 1474), (2550, 1483)],                                  # second man: two, to the left
    [(2515, 1482), (2542, 1498), (2582, 1521)],
    [(2884, 1487), (2892, 1496), (2900, 1503)],                                  # third man: to the left
]
BRIM_R, BRIM_W, BRIM_SMOOTH = 3, 2.5, 4
# the fire (FIRE, plate px): the brazier and its flames are quick brushstrokes, the clay showing through the black
# (Saglio); the print gives the flames as dark stipple and the brazier's loops nearly as dark, so the whole fire is a
# wash in steps by darkness (grey smoothed by FIRE_BLUR under each threshold, FIRE_STEPS). Black in it is only the
# solid black (grey under FIRE_BLACK, opened by FIRE_OPEN plate px, pieces under FIRE_SPECK plate px^2 dropped, closed
# by FIRE_OPEN over the print's dot screen, grown a px into the black): the brazier's loops, the man's leg and foot
# and the stake he holds; the flames' stipple goes to the wash
FIRE = [(1737, 1690), (1920, 1690), (2040, 2050), (2110, 2250), (2270, 2280), (2290, 2620), (1737, 2620)]
FIRE_STEPS = [[72, 0.15], [60, 0.3], [48, 0.45], [38, 0.6], [30, 0.75]]
FIRE_BLACK, FIRE_OPEN, FIRE_SPECK = 26, 3, 150
# John, pass 1 ("Clean the fire"): the loops came out ragged and pinholed where the print's dots run into them, and the
# wash's steps blotchy. The loops are smoothed (FIRE_SMOOTH plate px, Gaussian Blur then Threshold at half) with holes
# under FIRE_HOLE plate px^2 filled; the wash is read on the plate blurred FIRE_BLUR plate px, each step's islands and
# holes under FIRE_HOLE dropped and filled, its edge smoothed FIRE_SMOOTH
FIRE_BLUR, FIRE_SMOOTH, FIRE_HOLE = 7, 1.5, 60
# the rock's added white: light, and not warm
WHITE_L, WHITE_WARM = 115, 30
WHITE_FILL = "#f7f3ea"
AUTO_GROUND = 60                           # plate px^2: clay areas this large are ground
DOT_MIN = 12                               # plate px^2: dark marks on the ground smaller than this are grain
LINE_W = 2.0                               # plate px: the outline and the thinnest mark
RIM = 2.0                                  # plate px: the clay round the black on the dark theme
GRAIN = 4                                  # plate px^2: light specks in the black smaller than this are grain
EDGE_CLEAR = 1.5                           # plate px: no light marks this near the figures' edge
SMOOTH = 0.4                               # plate px: every edge smoothed (Gaussian Blur, Threshold at half)


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


def poly(shape, pts):
    """A polygon given in plate px, as a mask at UP."""
    return lw.polygon_mask(shape, np.array([((x - X0) * UP + 0.5, (y - Y0) * UP + 0.5) for x, y in pts]))


def join_marks(marks):
    """Breaks in the incisions joined (the print's dark specks cut the thinnest into dashes): skeleton ends facing
    each other (each end's last JOIN_RUN plate px of centre line points within JOIN_ANGLE degrees of the other end)
    across at most JOIN_MAX plate px, joined by a stroke LINE_W wide that crosses no other mark."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(marks)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    ends = np.argwhere(sk & (nb == 1))
    out = np.zeros_like(marks)
    if len(ends) < 2:
        return out
    H, W = sk.shape

    def run_back(p):
        path, seen = [tuple(p)], {tuple(p)}
        for _ in range(JOIN_RUN * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]
                   and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        return np.array(path, float)

    lab = ndi.label(marks, structure=np.ones((3, 3)))[0]
    cos = np.cos(np.radians(JOIN_ANGLE))
    used = set()
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used:
            continue
        ri, rj = run_back(ends[i]), run_back(ends[j])
        if len(ri) < JOIN_RUN * UP / 2 or len(rj) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        da, db = ri[0] - ri[-1], rj[0] - rj[-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        q = np.linspace(a, b, int(np.hypot(*(b - a))) + 2)
        hit = set(lab[tuple(q.round().astype(int).T)]) - {0, lab[tuple(ends[i])], lab[tuple(ends[j])]}
        if hit:
            continue
        m = np.zeros_like(marks)
        m[tuple(q.round().astype(int).T)] = True
        out |= ndi.distance_transform_edt(~m) <= LINE_W * UP / 2
        used |= {i, j}
    return out


def oriented(t, src_png, name):
    """src_png smoothed along its own strokes (ORIENT_*): PhotoCraft's Motion Blur at each angle; numpy picks,
    per pixel, the blur at the strokes' direction (as hecuba.py)."""
    g = grey(src_png)
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(src_png, t / f"{name}{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    mb = np.stack([grey(t / f"{name}{a}.png") for a in angs])
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    out = np.take_along_axis(mb, i[None], 0)[0]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(t / f"{name}.png")
    return t / f"{name}.png"


def write_svg(lines, body, tone, white, out, title, desc):
    """The house format (as hecuba.py): 1000 units tall, the body path under the `tone` paths (steps) under the
    added white (class "white", as wealth.py) under the lines."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    tp = ""
    for group in tone:
        below = 0.0
        for m, a in group:   # each step over the larger one below it, at the opacity that brings the total to a
            td, _ = lw.potrace_d(m[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
            tp += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                   f'stroke="none" d="{td}"/>')
            below = a
    wd, _ = lw.potrace_d(white[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'{tp}<path class="white" fill="{WHITE_FILL}" stroke="none" d="{wd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def main(src, qa=None, dump=None):
    out = Path(os.environ.get("CYCLOPS_OUT", OUT))
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png", ("image.imageRotation.180", None),
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        pc(t / "up.png", t / "warm.png", ("image.adjustments.channelMixer", {"gray": [100, 0, -100, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 0.4 * UP}))
        Lo = oriented(t, t / "L.png", "Lo")
        pc(Lo, t / "L_open.png", ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}))
        pc(t / "L.png", t / "L_close.png", ("filter.other.maximum", {"radius": BRIM_R * UP, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": BRIM_R * UP, "preserve": "roundness"}))
        pc(t / "L.png", t / "Lf.png", ("filter.blur.gaussianBlur", {"radius": FIRE_BLUR * UP}))
        pc(t / "L.png", t / "Lb.png", ("filter.blur.gaussianBlur", {"radius": TONE_BLUR * UP}))
        pc(t / "up.png", t / "red.png", ("image.adjustments.channelMixer", {"gray": [100, -160, 0, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": TONE_BLUR * UP}))
        L, W, R, Lb = grey(t / "L.png"), grey(t / "warm.png"), grey(t / "red.png"), grey(t / "Lb.png")
        Lf = grey(t / "Lf.png")
        light_hat = grey(Lo) - grey(t / "L_open.png")
        dark_hat = grey(t / "L_close.png") - L

    H, Wd = L.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0

    # the cuts (least-cost paths follow the light: the clay strips and the clay round the club)
    cost = 1.0 / (0.03 + (L / 255.0) ** 3)
    wire = lambda pts: lw.livewire(cost, [q if q == lw.STRAIGHT else ((q[0] - X0) * UP, (q[1] - Y0) * UP) for q in pts])
    plate = lambda xy: [(x / UP - 0.5 + X0 + 0.5 / UP, y / UP - 0.5 + Y0 + 0.5 / UP) for x, y in xy]
    clip = lambda pts: [q if q == lw.STRAIGHT else (min(max(q[0], X0 + 1), X1 - 2), min(max(q[1], Y0 + 1), Y1 - 2))
                        for q in pts]
    club_line = [q for p in CLUB for q in (p, lw.STRAIGHT)]
    rpath = plate(wire(clip(RIGHT + club_line + RIGHT_LOW)))
    club = poly(L.shape, [(3985, 2045)] + CLUB + [(3985, 2128)])
    outside = poly(L.shape, rpath + [(X1 + 2, Y1 + 2), (X1 + 2, Y0 - 2)])
    outside |= poly(L.shape, LEFT + [(X0 - 2, Y1 + 2), (X0 - 2, Y0 - 2)])
    outside |= (py < TOP[0] + (px - TOP[1]) * TOP[2]) | (py > np.interp(px, *zip(*FLOOR)) - FLOOR_CLEAR)

    # ground: the clay, opened so thin marks do not join it; its large areas
    clay = (W > WARM_T) & (L > CLAY_L)
    ground0 = ndi.binary_opening(clay & ~outside, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    ground = (size > AUTO_GROUND * UP * UP)[lab]
    black = L < BLACK_CORE

    # the smoke: redness steps
    steps = []
    for th, a in SMOKE_STEPS:
        m = ndi.binary_opening(R > th, structure=morphology.disk(round(TONE_OPEN * UP)))
        lab, _ = ndi.label(m)
        steps.append(m & (np.bincount(lab.ravel()) > TONE_MIN * UP * UP)[lab] & ~black & ~outside & poly(L.shape, SMOKE))
    # the fire: darkness steps inside FIRE; there the figures are only the black paint
    fire = poly(L.shape, FIRE) & ~outside
    fblack = ndi.binary_opening((L < FIRE_BLACK) & ~outside, structure=morphology.disk(round(FIRE_OPEN * UP)))
    lab, _ = ndi.label(fblack)
    fblack &= (np.bincount(lab.ravel()) >= FIRE_SPECK * UP * UP)[lab]
    fblack = ndi.binary_closing(fblack, structure=morphology.disk(round(FIRE_OPEN * UP)))
    fblack = ndi.binary_dilation(fblack, structure=morphology.disk(UP)) & black & fire
    # (the leg's incisions, closed here, are found again from the plate with the other light marks)
    fblack = smooth(morphology.remove_small_holes(fblack, max_size=FIRE_HOLE * UP * UP), FIRE_SMOOTH) & fire
    fsteps = []
    for th, a in FIRE_STEPS:
        m = morphology.remove_small_objects((Lf < th) & fire, max_size=FIRE_HOLE * UP * UP)
        m = morphology.remove_small_holes(m, max_size=FIRE_HOLE * UP * UP)
        fsteps.append(smooth(m, FIRE_SMOOTH) & fire)   # (under the loops: no seam of paper between them)
    soft = steps[0] | (fire & ~fblack)

    # the figures: all else, but specks of the print on the ground
    fig = ~ground & ~soft & ~outside
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) >= DOT_MIN * UP * UP)[lab]
    fig = ndi.binary_fill_holes(fig) & ~ground & ~soft & ~outside
    fig |= club & ~outside

    # the brims
    dcost = 1.0 / (0.05 + np.clip(dark_hat / 40.0, 0, 1))
    brim = np.zeros(L.shape, bool)
    for pts in BRIMS:
        if all(X0 < x < X1 - 1 and Y0 < y < Y1 - 1 for x, y in pts):
            path = np.array(lw.livewire(dcost, [((x - X0) * UP, (y - Y0) * UP) for x, y in pts]), float)
            # (smoothed along its length, BRIM_SMOOTH plate px: the path follows the print's grain)
            path = ndi.gaussian_filter1d(path, BRIM_SMOOTH * UP, axis=0, mode="nearest")
            path = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(path[:-1], path[1:])])
            path = path.round().astype(int)
            brim[path[:, 1], path[:, 0]] = True
    brim = (ndi.distance_transform_edt(~brim) <= BRIM_W * UP / 2) & ~fig
    steps = [m | brim for m in steps]

    # the rock's added white
    white = ndi.binary_opening((L > WHITE_L) & (W < WHITE_WARM) & fig, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > 20 * UP * UP)[lab]

    # the light marks in the black (incisions), at least LINE_W wide; not along the figures' edge
    clear = ndi.distance_transform_edt(fig) > EDGE_CLEAR * UP
    clear &= ndi.distance_transform_edt(~white) > 2 * UP
    clear &= ~(club & (ndi.distance_transform_edt(club) <= CLUB_CLEAR * UP))   # (the clay round the club's end)
    clear &= ~((px >= KNOB[0]) & (px < KNOB[2]) & (py >= KNOB[1]) & (py < KNOB[3]))
    marks = fig & ~white & clear & ((L > BLACK_T) | (light_hat > MARK_T))
    lab, _ = ndi.label(marks)
    marks &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    marks = (marks | (ndi.distance_transform_edt(~morphology.skeletonize(marks)) <= LINE_W * UP / 2)) & fig & clear
    marks |= join_marks(marks) & fig

    lines = smooth(fig & ~marks & ~white, SMOOTH)
    tones = [[(smooth(m, SMOOTH) & ~lines, a) for m, (_, a) in zip(steps, SMOKE_STEPS)],
             [(smooth(m, SMOOTH) & ~lines, a) for m, (_, a) in zip(fsteps, FIRE_STEPS)]]
    body = ndi.distance_transform_edt(~(fig | tones[0][0][0] | tones[1][0][0])) <= RIM * UP
    if dump:
        np.savez_compressed(dump, L=L.astype(np.uint8), W=W.astype(np.uint8), fig=fig, lines=lines, ground=ground,
                            marks=marks, white=white, fire=fire)
    info = write_svg(
        lines, body, tones, ndi.binary_dilation(white, iterations=UP) & ~lines, out,
        title='The blinding of Polyphemus',
        desc='Line drawing after the 1887 plate of a black-figure oinochoe in the Louvre (Gazette archéologique '
             '12, pl. 1): three of Odysseus\' men, two driving a stake into the eye of the sleeping Polyphemus, '
             'one heating a stake in the fire, with ivy above; cut out and retraced.')
    print(out, info)
    if qa:
        lw.qa_overlay(L, out, info['box'], Path(qa))
        lw.qa_dark(out, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
