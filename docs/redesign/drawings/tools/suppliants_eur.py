"""Suppliant Women (Euripides): Aithra holds out a phiale to her son Theseus, armed for his first deeds, a second
phiale in her other hand; a youth leaning on his staff stands beyond him. From Gerhard, Auserlesene griechische
Vasenbilder III (1847), Taf. CLVIII (text pp. 31-32, "Theseus und Äthra"), as scanned by Heidelberg University
Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_158.jpg/full/full/0/default.jpg
(2078 x 2911; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0205)
The vase: a red-figure calyx-krater from Vulci, in Gerhard's day in the Palagi collection at Milan; now Bologna,
Museo Civico Archeologico PU 285, attributed to the Methyse Painter (Beazley Archive 207341; ARV2 633.6). The names
are written on the vase: ΑΙΘΡΑ and ΘΕΣΕΥΣ. Gerhard reads the youth as Peirithoos; the Beazley Archive calls him a
draped youth leaning on a staff. The vase's shape drawing below the panel, the plate number and the painted names
are left out.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop, the
enlargement, the grey, the blurs, the Maximum and Minimum filters and the thresholds. numpy only combines the masks
PhotoCraft made (labels, unions, distances, skeletons) and measures. The SVG is written by linework.trace_svg.

Plate -> drawing, as for Trojan Women (tools/trojan_women_menelaus.py) and Helen (tools/helen.py):
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets of ground the
    figures close in (POCKETS). Smaller dark areas inside the figures are paint (the hair, the cuirass's bands).
  - The scene is every clay area the ground leaves larger than FIG_MIN (the painted names are smaller). The
    figures stand on the panel's lower edge (BOTTOM), which is the cut: paper below.
  - Lines (John, 2026-10-13: "be sure to get all those clothing lines without breaks"): the plate's dark lines
    inside the figures, found at half maximum and by the plate's paint, redrawn along their centres LINE_W plate
    px wide, the print's breaks joined; the outline on the black ground outside the clay; the solid paint.
  - Dark theme: the figures' area is the body; the ground stays open, as on the vase.

    python3 docs/redesign/drawings/tools/suppliants_eur.py gerhard1847bd3_Tafel_CLVIII.jpg [qa.png]
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
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import oedipus_tyrannus as ot  # noqa: E402
import trojan_women_menelaus as tw  # noqa: E402
from trojan_women_menelaus import join_breaks  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "suppliants-eur.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the panel, inside its left, top and right edges, down past its lower edge
X0, Y0, X1, Y1 = 264, 278, 1860, 1486
# the panel's lower edge: its last dark row, y = a + b x (plate px; fitted to the row above the paper in 1496 of
# 1586 columns, within 1.5 px); paper below it. The figures stand on a thin dark line along it
BOTTOM = (1471.08, 0.005208)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the crop's edge, are ground
FIG_MIN = 200                             # plate px: clay areas smaller than this are the names and specks
# pockets of ground the figures close in (a point in each, plate px): the wedge between the two hanging ends of
# Theseus' chlamys by his spear; under Aithra's upper phiale, between its rim and her palm; under the lower one,
# between it and her thumb; between her hem and her right foot
POCKETS = [(1283, 760), (740, 723), (610, 819), (423, 1450)]
# black that runs into the ground through a gap (plate px polylines): Aithra's hair below her cap band, which the
# plate prints a shade lighter than the ground with a darker rim between, and no clay line: at the back of her neck,
# and in front, where the end of the band's loop all but meets her forehead
WALLS = [[(439, 463), (437.5, 474), (436, 485)], [(532, 448), (527.5, 452.5), (526.5, 457)]]
WALL_W = 1.5
LINE_DARK = 100                           # the plate's line paint: darker than this after a light blur
# The interior lines print 1-2 px wide, black to grey 120, in places as dashes, and in the kilt and on Aithra's skirt
# only 2-4 px apart: local contrast (Trojan Women's finder) ran neighbours together, and their centre lines came out
# with rungs between them; the plate at half maximum kept them apart but broke the dashed ones into pieces. So the
# plate is first blurred along its own lines: PhotoCraft's Motion Blur at each of ANGLES (degrees, over DIST plate
# px), each px taken from the blur nearest the lines' direction there (measured in numpy: the structure tensor of the
# plate blurred BLUR, smoothed over TENSOR plate px), which runs a dashed fold into one line and leaves its neighbours
# apart. A line is that image at half maximum (as oedipus_tyrannus.py): darker than HALF of the way from the clay (its
# Maximum then Minimum over CLOSE_R plate px) to the line's darkest px within CORE_R, with local contrast above LOW,
# joined to HIGH; with the plate's own line paint (LINE_DARK: the short marks the blur would smear, the faces, the
# cuirass's ornaments); drawn along its centre (side spurs under SPUR plate px pruned, pieces under MIN_LEN dropped),
# LINE_W plate px wide; parts printed wider than that keep their width
BLUR, CLOSE_R, CORE_R, HALF, LOW, HIGH = 0.4, 4, 1.5, 0.5, 12, 24
ANGLES, DIST, TENSOR = tuple(range(0, 180, 15)), 5, 4
# The blur along the lines smears short marks (the cuirass's scales and hatching, the faces, the tassels): it is used
# only where the plate's lines run parallel, as the structure tensor's coherence measures it (drapery 0.8-0.95, the
# scales, the hatching and the faces 0.4-0.5 at the median), blended from none at COH[0] to all at COH[1]
COH = (0.6, 0.85)
# The short marks (the cuirass's hatching, scales and tassels, the faces, the phialai's drops): the blur along the
# lines smears them, even where coherent lines run beside them (the cuirass's verticals). They are taken from the
# plate itself at half maximum (not blurred along: LOW_D and HIGH_D), at their printed width; each piece that the lines
# drawn along their centres already hold (COVERED of it within a line's width of them) goes, so a pleat is not drawn
# twice. Pieces under SPECK plate px^2 are the print's specks
LOW_D, HIGH_D, SPECK, COVERED = 22, 45, 4, 0.6
# and the lines drawn along their centres keep only the pieces of centre line LONG plate px or longer that lie mostly
# (mean blend weight PARALLEL or more) where lines run parallel: the shorter pieces, and the cuirass's scales, were the
# blur's smears of short marks, which held the sharp marks out
LONG, PARALLEL = 15, 0.3
SPUR, MIN_LEN = 2, 5
LINE_W = 1.5                              # plate px: the interior lines, redrawn along their centres
EDGE_OUT = 2.0                            # plate px: the outline's width, on the ground
TRACE_H = 7200                            # traced tall, as oedipus_tyrannus.py (thin lines break into dashes at 4000)
# No faint-line finder (Trojan Women's): it drew the clay's grain and the JPEG's ringing beside the pleats as short
# strokes, as on Ion. The few runs that print faint and dotted are traced by hand: the plate's own line between
# hand-placed points (plate px), LINE_W wide. The neckline of Aithra's chiton across her throat, a row of dots between
# its two solid stretches
TRACED = [[(440, 554.5), (452, 557.5), (461, 563), (468, 569.5)],
          # two of the cuirass's thin verticals, printed as dashes, from the band under the breasts to its lower edge
          [(1055.5, 658), (1052, 700), (1049.5, 730), (1047, 762)], [(1073, 658), (1070, 700), (1068, 730), (1065.5, 762)]]
# the tassels' dots on the cuirass (x, y, r, plate px), round blobs too small for paint and too dark and round for the
# mark finder's half maximum, which took only their rims: drawn as discs at their printed size
DOTS = [(1025.7, 724.3, 2.4), (1035.7, 725, 2.4), (1044, 721.4, 2.4), (1067.6, 721.4, 2.4), (1074.3, 727, 2.4),
        (1085, 727.9, 2.4)]
# Faint folds whose print fades or breaks short of where it runs on (John: "without breaks"): each line end is followed
# on along the plate's own line, a step at a time onto the darkest of the three px ahead, while the plate's local
# contrast (the mean over the last GROW_RUN steps) stays at GROW_C or more (the clay's grain reads 14-18 at the 90th
# percentile), for at most GROW_MAX plate px, stopping where it meets other ink. Ends within GROW_EDGE plate px of the
# ground (at the outline) are not followed
GROW_C, GROW_RUN, GROW_MAX, GROW_EDGE = 18, 4, 12, 3
# John's corrections, marked in PhotoCraft over pass 1 (2026-10-13), as RGBA over the crop at MARKS_K x the plate's px:
# green, ink to take out (inside the figures; the outline stays); blue, ink to add, drawn along the plate's own line
# through points read off his stroke every MARK_STEP plate px (as TRACED), LINE_W wide. Some of his green landed on the
# red pass layer; both layers are merged into the one file
MARKS_FILES = [Path(__file__).parent / "suppliants_eur_marks_1.png"]
MARKS_K, MARK_STEP, MARK_NEAR = 2, 4, 2.5   # (the line kept within MARK_NEAR plate px of his stroke)
# inside REPLACE (boxes, plate px) his blue strokes replace the lines there, the ink within MARK_NEAR plate px of them
# taken out first: the fingers of Aithra's lower hand, which print faint and came out as broken wiggles beside them
REPLACE = [(605, 800, 662, 836)]
# the line weight, pinned after pass 1 (its median width over the longer side), so the marks change only where they lie
WEIGHT = 5.0 / 4621
assert tw.UP == UP
# The gap joiner (trojan_women_menelaus.join_breaks) as Trojan Women set it joined line ends that point at each other
# across 40 plate px of bare clay (median contrast 4 asked; the clay's grain reads 7 at the median, 14-18 at the 90th
# percentile): it drew straight strokes across Theseus' face. Here a join must run over print: median contrast JOIN_C
# along the gap (the dashed lines' gaps read 20 and up), across at most JOIN_MAX (ALIGN_MAX for ends pointing straight
# at each other) plate px
tw.JOIN_C = tw.ALIGN_C = 15
tw.JOIN_MAX, tw.ALIGN_MAX = 20, 30


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


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


def traced(g, P, width, near=None):
    """The plate's own dark line through hand-placed points P (x, y at UP), followed by a least-cost path along
    its darkest ridge, `width` plate px wide (as trojan_women_menelaus.py); kept within `near` (a mask at UP) if given."""
    pad = 10 * UP
    x0, y0 = max(int(P[:, 0].min()) - pad, 0), max(int(P[:, 1].min()) - pad, 0)
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.7 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    if near is not None:
        cost = np.where(near[y0:y1, x0:x1], cost, 1e6)
    path = lw.livewire(cost, [(x - x0, y - y0) for x, y in P])
    m = np.zeros(g.shape, bool)
    m[(path[:, 1] - 0.5).astype(int) + y0, (path[:, 0] - 0.5).astype(int) + x0] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def grow_ends(lines, contrast, fig, width):
    """The line ends of `lines` followed on along the plate's line (GROW_*), drawn `width` plate px wide (at UP)."""
    sk = morphology.skeletonize(lines)
    n8 = np.ones((3, 3), np.uint8)
    nb = ndi.convolve(sk.astype(np.uint8), n8, mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    H, W = sk.shape
    to_ground = ndi.distance_transform_edt(fig)
    c = ndi.gaussian_filter(contrast.astype(np.float32), 0.5 * UP)
    lab = ndi.label(lines, structure=n8)[0]
    out = np.zeros_like(lines)
    for p in ends:
        if to_ground[tuple(p)] < GROW_EDGE * UP:
            continue
        path, seen = [tuple(p)], {tuple(p)}   # the end's last 4 plate px of centre line give its direction
        for _ in range(4 * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx] and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        if len(path) < 2 * UP:
            continue
        d = np.array(path[0], float) - np.array(path[-1], float)
        d /= np.hypot(*d)
        own = lab[tuple(p)]
        q = np.array(p, float)
        run, grown = [], []
        for _ in range(GROW_MAX * UP):
            perp = np.array([-d[1], d[0]])
            cand = [q + d + k * 0.7 * perp for k in (-1, 0, 1)]
            vals = [ndi.map_coordinates(c, np.array([v]).T, order=1)[0] for v in cand]
            k = int(np.argmax(vals))
            nq = cand[k]
            iy, ix = int(round(nq[0])), int(round(nq[1]))
            if not (0 <= iy < H and 0 <= ix < W) or not fig[iy, ix]:
                break
            run.append(vals[k])
            if len(run) >= GROW_RUN * UP and np.mean(run[-GROW_RUN * UP:]) < GROW_C:
                grown = grown[:max(len(grown) - GROW_RUN * UP, 0)]   # (back to where the print was still there)
                break
            if lab[iy, ix] and lab[iy, ix] != own:   # met other ink: joined
                grown.append((iy, ix))
                break
            grown.append((iy, ix))
            d = 0.8 * d + 0.2 * (nq - q)
            d /= np.hypot(*d)
            q = nq
        for iy, ix in grown:
            out[iy, ix] = True
    return ndi.distance_transform_edt(~out) <= width * UP / 2 if out.any() else out


def marks(mf, shape):
    """John's green and blue in a marks file, at the work px (shape: the work arrays')."""
    a = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
    assert a.shape[:2] == ((Y1 - Y0) * MARKS_K, (X1 - X0) * MARKS_K), a.shape
    r, gg, b, al = (a[..., i] for i in range(4))
    on = al > 40
    out = []
    for m in (on & (gg > r + 40) & (gg > b + 20), on & (b > r + 40) & (b > gg + 20)):
        out.append(np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.NEAREST)) > 0)
    green = ndi.binary_fill_holes(ndi.binary_closing(out[0], structure=morphology.disk(2 * UP)))
    return green, out[1]


def strokes(blue):
    """Each of John's blue strokes as points along its centre line from end to end (the longest path through its
    skeleton), MARK_STEP plate px apart, (x, y) at UP; and the marks too small to be strokes (dots), as painted."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import shortest_path
    sk = morphology.skeletonize(blue)
    lab, n = ndi.label(blue, structure=np.ones((3, 3)))
    out, dots = [], np.zeros_like(blue)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        pts = np.argwhere(sk[sl] & (lab[sl] == k)) + (sl[0].start, sl[1].start)
        if len(pts) < 3 * UP:
            dots |= lab == k
            continue
        idx = {tuple(p): i for i, p in enumerate(pts)}
        rows, cols, vals = [], [], []
        for i, (y, x) in enumerate(pts):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    j = idx.get((y + dy, x + dx))
                    if (dy or dx) and j is not None:
                        rows.append(i); cols.append(j); vals.append(np.hypot(dy, dx))
        G = csr_matrix((vals, (rows, cols)), shape=(len(pts), len(pts)))
        d0 = shortest_path(G, indices=0)
        a = int(np.argmax(np.where(np.isfinite(d0), d0, -1)))
        da, pred = shortest_path(G, indices=a, return_predecessors=True)
        b = int(np.argmax(np.where(np.isfinite(da), da, -1)))
        path = [b]
        while path[-1] != a:
            path.append(pred[path[-1]])
        path = pts[path]
        sel = np.unique(np.r_[np.arange(0, len(path), MARK_STEP * UP), len(path) - 1])
        out.append(np.array([(path[i][1] + 0.5, path[i][0] + 0.5) for i in sel], float))
    return out, dots


def masks(src, box=None):
    """The plate's masks at UP over the crop (or a sub-box of it, plate px, for quick runs)."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = x1 - x0, y1 - y0
        pc(src, t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": BLUR * UP}))
        g, gl = grey(t / "up.png"), grey(t / "gl.png")
        # the lines' direction (degrees anticlockwise from the horizontal, image y down): across the structure
        # tensor's dominant gradient
        gy, gx = np.gradient(ndi.gaussian_filter(gl, UP))
        jxx, jyy, jxy = (ndi.gaussian_filter(v, TENSOR * UP) for v in (gx * gx, gy * gy, gx * gy))
        line = np.degrees(-(0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2)) % 180
        coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
        wt = np.clip((coh - COH[0]) / (COH[1] - COH[0]), 0, 1)
        del gy, gx, jxx, jyy, jxy, coh
        step = 180 / len(ANGLES)
        pick = np.rint(line / step).astype(int) % len(ANGLES)
        o = np.zeros_like(gl)
        for i, a in enumerate(ANGLES):
            pc(t / "gl.png", t / "mb.png", ("filter.blur.motionBlur", {"angle": a, "distance": DIST * UP}))
            o = np.where(pick == i, grey(t / "mb.png"), o)
        o = wt * o + (1 - wt) * gl
        Image.fromarray(o.clip(0, 255).astype(np.uint8)).save(t / "along.png")
        r = CLOSE_R * UP
        pc(t / "along.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "along.png", t / "lcore.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        pc(t / "gl.png", t / "closed0.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "lcore0.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        return dict(g=g, gl=gl, along=grey(t / "along.png"), closed=grey(t / "closed.png"),
                    lcore=grey(t / "lcore.png"), closed0=grey(t / "closed0.png"), lcore0=grey(t / "lcore0.png"),
                    wt=wt, dark0=grey(t / "dark.png") < 128, core=grey(t / "core.png") < 128)


def main(src, qa=None, dump=None, box=None):
    bx0, by0, bx1, by1 = box or (X0, Y0, X1, Y1)
    M = masks(src, box)
    g, gl, closed, dark0, core = (M[k] for k in ("g", "gl", "closed", "dark0", "core"))
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP - 0.5 + bx0, (yy + 0.5) / UP - 0.5 + by0   # plate px

    def at(pts):   # plate px -> (x, y) at UP in this box
        return np.array([((x - bx0) * UP, (y - by0) * UP) for x, y in pts], float)

    a, b = BOTTOM
    outside = py > a + b * px + 0.5          # the paper below the panel
    del px, py

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP))
    dark &= ~outside
    for pts in WALLS:
        P = at(pts)
        path = np.vstack([np.linspace(p, q, int(np.hypot(*(q - p))) + 2) for p, q in zip(P[:-1], P[1:])]) + 0.5
        dark &= ~along(g.shape, path, WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        if bx0 <= x < bx1 and by0 <= y < by1:
            k = lab[round((y - by0) * UP), round((x - bx0) * UP)]
            assert k, f'pocket point {(x, y)} is not on dark'
            is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = (sz > FIG_MIN * UP * UP)[lab]
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)
    # (the specks of clay that the refilling leaves in the thin dark line along the panel's lower edge)
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) > FIG_MIN * UP * UP)[lab]

    # the interior lines (LOW, HIGH, HALF ...): the plate at half maximum, and its line paint, along their centres
    c = closed - M['along']
    hm = apply_hysteresis_threshold(np.where(c >= HALF * (closed - M['lcore']), c, 0), LOW, HIGH)
    found = (hm | core) & fig & ~paint
    centre = ot.centre_lines(found, SPUR * UP, MIN_LEN * UP)
    lab, n = ndi.label(centre, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    par = np.bincount(lab.ravel(), weights=M['wt'].ravel(), minlength=n + 1) / np.maximum(sz, 1)
    centre &= ((sz >= LONG * UP) & (par >= PARALLEL))[lab]
    t = LINE_W * UP
    wide = ndi.binary_opening(found, structure=morphology.disk(int(np.ceil(t / 2)) + 1))
    wide = found & ndi.binary_dilation(wide, iterations=2) & ndi.binary_dilation(centre, iterations=round(t))
    lines = (wide | (ndi.distance_transform_edt(~centre) <= t / 2)) & fig
    _found = found
    for pts in TRACED:
        lines |= traced(g, at(pts), LINE_W) & fig
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the short marks (LOW_D ...), at their printed width, but for what the lines already hold; small paint (the
    # tassels' dots) is a mark
    c0 = M['closed0'] - gl
    det = apply_hysteresis_threshold(np.where(c0 >= HALF * (M['closed0'] - M['lcore0']), c0, 0), LOW_D, HIGH_D)
    det &= fig & ~solid
    lab, n = ndi.label(det)
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    held = np.bincount(lab[ndi.binary_dilation(lines, iterations=UP) & det], minlength=n + 1)
    det &= ((sz > SPECK * UP * UP) & (held < COVERED * sz))[lab]
    # the print's breaks joined, in the lines and between the marks (a thin line printed as dashes)
    _join = join_breaks(lines | det, c0, ndi.distance_transform_edt(fig)) & fig
    lines |= det | _join
    det |= _join
    # the faint folds followed on where their print fades or breaks (GROW_*)
    _grow = grow_ends(lines, c0, fig, LINE_W) & fig
    lines |= _grow
    for x, y, r in DOTS:
        cx, cy = at([(x, y)])[0]
        disc = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) <= r * UP
        lines |= disc
        det |= disc
    _det = det
    # the outline: EDGE_OUT plate px wide on the black ground outside the clay, not on the clay (John on Ion,
    # 2026-10-09), so every clay part keeps its full width
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & ~outside & (dt <= EDGE_OUT * UP)
    del dt
    # where a figure stands on the cut (the soles, the hem), the outline closes along it, on the clay
    edge |= fig & (ndi.distance_transform_edt(~outside) <= EDGE_OUT * UP)
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab] | det   # (the short marks are small)
    for mf in ([] if box else MARKS_FILES):
        green, blue = marks(mf, g.shape)
        ink &= ~(ndi.binary_dilation(green, iterations=UP) & fig & ~edge)
        lines_, dots_ = strokes(blue)
        near = ndi.distance_transform_edt(~blue) <= MARK_NEAR * UP
        rep = np.zeros_like(near)
        for rx0, ry0, rx1, ry1 in REPLACE:
            rep[(ry0 - by0) * UP:(ry1 - by0) * UP, (rx0 - bx0) * UP:(rx1 - bx0) * UP] = True
        ink &= ~(near & rep & fig & ~edge)
        for P in lines_:
            ink |= traced(g, P, LINE_W, near) & fig
        ink |= dots_ & fig
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint,
                            found=_found, det=_det, join=_join, grow=_grow, contrast=np.clip(c, 0, 255).astype(np.uint8), edge=edge, lines=lines)
    if box:
        return
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, trace_h=TRACE_H,
        title='Aithra holding out a phiale to Theseus',
        desc='Line drawing after the 1847 plate of a red-figure calyx-krater (Gerhard, Auserlesene griechische '
             'Vasenbilder III, Taf. CLVIII); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
