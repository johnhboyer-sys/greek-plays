"""Trojan Women: Menelaus at Troy, his sword fallen at his feet, between Helen (right, her hand
raised) and a woman running from him (left), from the lower picture (fig. 4) of Gerhard,
Auserlesene griechische Vasenbilder III (1847), Taf. CLXIX, as scanned by Heidelberg University
Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_169.jpg/full/full/0/default.jpg
(2078 x 2869; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0216)
The vase: a red-figure belly amphora (type B) from Vulci, attributed to the Altamura Painter, c. 470-450
BC, now British Museum 1837,0609.71 (Cat. Vases E 263), bought from the Prince of Canino's sale in 1837.
Gerhard (text p. 55) places it in the Vatican's Museo Gregoriano; the BM's catalogue (1896, E 263) notes
the slip. Fig. 3 on the plate is the amphora's shape, fig. 4 the painting drawn here; the other side
(three maenads) is not on the plate.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the
crop, the enlargement, the grey, the blurs, the Maximum and Minimum filters and the thresholds.
numpy only combines the masks PhotoCraft made (labels, unions, the difference of two images,
hysteresis) and measures. The SVG is written by linework.trace_svg, as for every Gerhard plate.

Plate -> drawing, as for Hippolytus (tools/hippolytus.py): the plate prints the black ground
black, so the figures' outline comes free.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets
    of ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is the clay area the ground leaves, from SEEDS. Below the panel's lower edge is
    paper (BOTTOM): the soles stand on a thin strip of black above it.
  - Lines: the plate's dark lines inside the figures (local contrast: the plate's Maximum then
    Minimum, less the plate), the outline, and the plate's solid paint.
  - Dark theme: the figures' area is the body; the ground pockets stay open, as on the vase.

    python3 docs/redesign/drawings/tools/trojan_women_menelaus.py gerhard1847bd3_169.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "trojan-women.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 153, 1392, 1858, 2512    # crop in plate px: the panel, inside its left, top and right edges
# the panel's lower edge: the last row of its black, y = a + b x (plate px; fitted to every column,
# within 2.4 px); paper below it
BOTTOM = (2507.09, -0.005377)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the panel's edge, are ground
# her dress (left), his chest, Helen's dress, the sword's blade, the shield's rim (a black band
# parts it from the shield's face), the end of Helen's mantle between the shield and her, and the
# strip of it outside her zigzag hem (plate px)
SEEDS = [(500, 1980), (1020, 1840), (1540, 2180), (720, 2140), (1350, 1789), (1357, 2136), (1395, 2060)]
# pockets of ground the figures close in (a point in each, plate px): between Helen's arm and her side
POCKETS = [(1686, 2019)]
# Black borders that run into the ground: the band inside the shield's rim (at both ends, where the
# rim thins out to a faint clay line), Helen's zigzag hem (at both ends, and where it turns between
# two clay tips, and where a corner of it all but touches the ground), the hem of her overfold where it runs into the pocket at her side, and the left
# woman's zigzag hem (at its lower end, its tassel). WALLS (plate px) part them from the ground, WALL_W px wide: along the
# faint clay line, or across the border's end along the figure's edge.
WALLS = [[(1120, 1607), (1128, 1602), (1137, 1597)], [(1306, 2098), (1316, 2091), (1327, 2079)],
         [(1405, 2021.5), (1409.5, 2015)], [(1369.5, 2105.5), (1371.5, 2100), (1374, 2095)], [(1292, 2255), (1290, 2266)], [(1332, 2183), (1337, 2177)], [(1638, 2071), (1636, 2082)],
         [(395, 1899), (419, 1896)],
         [(444, 1546), (447, 1556)], [(466, 1533), (470, 1536)],
         [(649, 2203), (655, 2204)], [(662, 2203.5), (668.5, 2203)]]
WALL_W = 1.5
# The plate's lines print solid black (grey 6-40) on the clay (150-165), 1-3 px wide, but the finest
# folds only 1 px wide and grey 70-140. Lines are the plate's paint at its own width, darker than
# LINE_DARK after a light blur (local contrast, as on Hippolytus, ran the close lines of the faces
# together and drew every line heavier than printed); the faint folds the local-contrast finder
# picks up are added along their centres, LINE_MIN plate px wide.
LINE_DARK = 100
LINE_MIN = 1.5
# the raised hands (boxes, plate px): their fingers are clay strips 4-6 px wide, the ground between
# them 2-3 px. Here the ground is found at less blur, so the gaps stay ground, and the outline is
# drawn finer (HAND_EDGE plate px), so each finger keeps its clay inside it (as suppliants_aesch.py)
HANDS = [(785, 1485, 860, 1560), (1380, 1530, 1450, 1590)]
HAND_EDGE = 1.2
# Breaks in the thin lines where the print fades (the folds above all: they print faint and dotted),
# joined as libation_bearers.py joins them: line ends that face each other across a gap of at most
# JOIN_MAX plate px (the last JOIN_RUN plate px of each end's centre line point at the other end,
# within JOIN_ANGLE degrees), joined straight at the lines' width where the plate prints a line
# across the gap: along its middle 80% the plate's local contrast (grey) has a median of JOIN_C or
# more and stays under JOIN_LOW for no more than JOIN_FADE plate px together (a gap between the
# print's dots), and the join crosses no other line. Over the 50 facing pairs in the first pass,
# the fold breaks ran 10-24 (median); the true ends (the nose, a ribbon's tip, a line ending at the
# helmet) under 5, or unprinted for 6 px or more, or across other lines
# (a dot of the faint line's own print in the gap, under JOIN_DOT plate px^2, is no line crossed)
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C, JOIN_LOW, JOIN_FADE, JOIN_DOT = 30, 6, 20, 7, 3, 5, 30
# The faintest folds (John, 2026-10-07, circling 26 places on pass 1: "lines or sections that should
# have black ink. Some may be faint"): the plate prints them as dotted runs of grey 100-135 on clay
# 145-160. They are the plate's local contrast at fine blur (0.5 plate px; its Maximum then Minimum
# over 5 plate px, less it) above FAINT[0], joined to a point above FAINT[1]; a piece is a line if its
# long axis is FAINT_LEN plate px or more and 3 times its width (grain is rounder and shorter).
# Each piece is drawn along a smooth curve fitted to it (a quadratic across its long axis), LINE_MIN
# wide, so a dotted run of print comes out an even line; join_breaks then joins the pieces along a
# fold where the print breaks
FAINT, FAINT_LEN = (7, 14), 8
# A short piece must also run with the lines round it (within FAINT_ANGLE degrees of their direction,
# FAINT_NEAR plate px about): a dash across the folds is grain
FAINT_ANGLE, FAINT_NEAR = 25, 8
# and a piece lying along the figure's edge (its median distance from the ground under FAINT_EDGE plate
# px) is the darker band the print leaves inside the outline, not a line (it drew a line down the left
# woman's face, beside her profile)
FAINT_EDGE = 6
# Line ends that point straight at each other (within ALIGN_ANGLE degrees, both ways) are pieces of one
# dotted fold: joined across up to ALIGN_MAX plate px where the print between them is faint (median
# contrast ALIGN_C or more), however long its gaps
ALIGN_COS, ALIGN_C, ALIGN_MAX = np.cos(np.radians(10)), 4, 40
# faint lines the finders miss, traced along the plate's own line between hand-placed points (plate
# px), TRACED_W wide: a fold across the left woman's shoulder (a row of dots), Menelaus' ankle bone
# between its two printed strokes
TRACED = [[(522.5, 1668), (536, 1656), (547, 1647)], [(679, 2416.5), (675.5, 2420.5), (673, 2424)]]
# Two folds low on Helen's skirt print so faint (grey 125-150 on clay 145-160), and so close to darker
# lines, that the finders and a least-cost path both run onto their neighbours: drawn along a curve
# (x a quadratic in y) fitted to their centres, measured every 10 px (plate px; John circled them)
FOLDS = [[(1441, 2410), (1440, 2420), (1438, 2430), (1436, 2440), (1435, 2450), (1432, 2460), (1432, 2470)],
         [(1639, 2360), (1638, 2370), (1637, 2380), (1636, 2390), (1636, 2400), (1637, 2410), (1636, 2420)]]
TRACED_W = LINE_MIN
# small dark marks kept in the left woman's face (box, plate px): her nostril prints as a dot 3 px
# across, darker than FACE_DARK (lightly blurred) only at its centre
FACE = (530, 1540, 600, 1620)
FACE_DARK = 110
# Her profile from the nose to the jaw is drawn on John's line (2026-10-07: "Mouth needs to have the lips
# and chin distinct"; "Red line is where ink should go. Green pixels should not ink. They are
# background"), which he drew over the plate's pixels at 20x: the nose's tip and underside, the upper
# lip, the mouth (ground between the lips, outlined), the lower lip, the step under it, the straight
# chin, the jaw. The grey threshold had taken a pale strip along her lips and chin for clay and the
# mouth's ground for paint. Within PROFILE_BOX, clay lies left of the line, ground right, and the
# outline is drawn along it (centred), PROFILE_W plate px wide (the outline's own width elsewhere). Its
# two ends are moved a px onto the outline's centre beyond the box, so the line runs on without a step
PROFILE = [(571.1, 1570), (573.25, 1572), (574.5, 1573.75), (575.5, 1576.25), (576, 1578), (576.5, 1579.25),
           (576.6, 1582.75), (576, 1583.5), (570, 1583.5), (569.75, 1584.25), (569.5, 1588.5), (569.75, 1589.25),
           (564.75, 1589.15), (564.5, 1593), (568.75, 1593.5), (568.9, 1596.75), (568, 1598.5), (564.5, 1598.6),
           (564.5, 1606), (564, 1608), (562.5, 1610.25), (561.5, 1611.5), (555.5, 1613.2), (553.5, 1614.2)]
PROFILE_BOX = (548, 1570, 590, 1615)
PROFILE_W = 7 / 3
# the hair: dark paint inside the left woman's fillet, where its loop's ends come within a px of the
# clay beside them, and the tassel's black weight at the corner of her mantle are walled off from the
# ground (with WALLS above)
SOLES = 6.0                               # plate px: the strip of black under the soles, above the paper, is ground


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
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def join_breaks(lines, contrast, to_edge):
    """The breaks in `lines` (at UP) that JOIN_* describe, joined; `contrast` is the plate's local
    contrast (UP px)."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    dt = ndi.distance_transform_edt(lines)
    H, W = sk.shape

    def run_back(p):   # the end's last JOIN_RUN plate px of centre line, from the end inward
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

    runs = [run_back(p) for p in ends]
    lab = ndi.label(lines, structure=np.ones((3, 3)))[0]
    size = np.bincount(lab.ravel())
    out = np.zeros_like(lines)
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(ALIGN_MAX * UP),
                   key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or len(runs[i]) < JOIN_RUN * UP / 2 or len(runs[j]) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        t = np.linspace(0.1, 0.9, max(int(np.hypot(*(b - a))), 3))
        q = a[None] + t[:, None] * (b - a)[None]
        c = ndi.map_coordinates(contrast, q.T, order=1)
        low = np.r_[0, (c < JOIN_LOW).astype(int), 0]
        starts, stops = np.nonzero(np.diff(low) == 1)[0], np.nonzero(np.diff(low) == -1)[0]
        aligned = da @ u >= ALIGN_COS * np.hypot(*da) and db @ -u >= ALIGN_COS * np.hypot(*db)
        if not aligned and np.hypot(*(b - a)) > JOIN_MAX * UP:
            continue
        if aligned:   # a dotted fold: its pieces lie along one curve, so the print's gaps may be long
            # (not along the figure's edge, where the print's darker band beside the outline would pass
            # for a faint line: it joined a stroke straight down the left woman's face)
            if np.median(c) < ALIGN_C or np.median(ndi.map_coordinates(to_edge, q.T, order=1)) < FAINT_EDGE * UP:
                continue
        elif np.median(c) < JOIN_C or (len(starts) and (stops - starts).max() > JOIN_FADE * UP):
            continue
        mid = (np.hypot(*(q - a).T) > 2 * UP) & (np.hypot(*(q - b).T) > 2 * UP)
        hit = set(lab[tuple(q[mid].round().astype(int).T)]) - {0, lab[tuple(a.astype(int))], lab[tuple(b.astype(int))]}
        if any(size[k] >= JOIN_DOT * UP * UP for k in hit):   # it would cross another line (not a dot of its own)
            continue
        w = np.median([dt[tuple(r.astype(int))] for r in np.vstack([runs[i], runs[j]])]) * 2 / UP
        seg = np.linspace(a - 1.5 * u, b + 1.5 * u, int(np.hypot(*(b - a))) + 4)[:, ::-1] + 0.5
        out |= along(lines.shape, seg, max(w, 2.0))
        used |= {i, j}
    return out


def faint_lines(contrast, fig, lines):
    """The faint folds FAINT describes, each drawn along a quadratic fitted to it, LINE_MIN wide (UP px)."""
    m = apply_hysteresis_threshold(contrast, *FAINT) & fig & ~ndi.binary_dilation(lines, iterations=UP)
    lab, _ = ndi.label(m, structure=np.ones((3, 3)))
    to_edge = ndi.distance_transform_edt(fig)
    gy, gx = np.gradient(ndi.gaussian_filter(lines.astype(np.float32), UP))   # the lines' direction round
    jyy, jxx, jxy = (ndi.gaussian_filter(a, FAINT_NEAR * UP) for a in (gy * gy, gx * gx, gx * gy))
    out = np.zeros_like(m)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float) + (sl[0].start, sl[1].start)
        if len(p) < 3:
            continue
        c = p.mean(0)
        w, v = np.linalg.eigh(np.cov((p - c).T))
        long_ = 4 * np.sqrt(max(w[1], 0))
        if long_ < FAINT_LEN * UP or np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)) < 3:
            continue
        if np.median(to_edge[tuple(p.astype(int).T)]) < FAINT_EDGE * UP:
            continue
        if long_ < 3 * FAINT_LEN * UP:
            i, j = int(c[0]), int(c[1])
            ev, evec = np.linalg.eigh(np.array([[jyy[i, j], jxy[i, j]], [jxy[i, j], jxx[i, j]]]))
            if ev[1] > 0 and abs(evec[:, 0] @ v[:, 1]) < np.cos(np.radians(FAINT_ANGLE)):
                continue
        t, u = (p - c) @ v[:, 1], (p - c) @ v[:, 0]
        f = np.polyfit(t, u, 2 if long_ >= 3 * FAINT_LEN * UP else 1)
        tt = np.linspace(t.min(), t.max(), int(t.max() - t.min()) + 2)
        q = c + tt[:, None] * v[:, 1] + np.polyval(f, tt)[:, None] * v[:, 0]
        q = q.round().astype(int)
        ok = (q[:, 0] >= 0) & (q[:, 0] < m.shape[0]) & (q[:, 1] >= 0) & (q[:, 1] < m.shape[1])
        out[q[ok, 0], q[ok, 1]] = True
    return ndi.distance_transform_edt(~out) <= LINE_MIN * UP / 2


def traced(g, pts, width):
    """The plate's own dark line between hand-placed points (plate px), followed by a least-cost
    path along its darkest ridge, `width` plate px wide, at UP (as hippolytus.py)."""
    P = up(pts)
    pad = 10 * UP
    x0, y0 = int(P[:, 0].min()) - pad, int(P[:, 1].min()) - pad
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.7 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    path = lw.livewire(cost, [(x - x0, y - y0) for x, y in P])
    m = np.zeros(g.shape, bool)
    m[(path[:, 1] - 0.5).astype(int) + y0, (path[:, 0] - 0.5).astype(int) + x0] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def ink_lines(g_blur, closed, low, high):
    """lw.ink_lines on PhotoCraft's images: the blurred plate's closing (Maximum then Minimum)
    less the blurred plate, with hysteresis."""
    return apply_hysteresis_threshold(closed - g_blur, low, high)


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
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
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside: the paper below the panel (the first light row under the black strip, column by column)
    a, b = BOTTOM
    outside = (yy + 0.5) / UP - 0.5 + Y0 > a + b * ((xx + 0.5) / UP - 0.5 + X0) + 0.5

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP))
    hand = np.zeros(g.shape, bool)
    for box in HANDS:
        hx0, hy0, hx1, hy1 = [(v - o) * UP for v, o in zip(box, (X0, Y0, X0, Y0))]
        hand[hy0:hy1, hx0:hx1] = True
    dark = np.where(hand, ndi.binary_opening(fine, structure=morphology.disk(1)), dark)
    dark |= dark0 & (ndi.distance_transform_edt(~outside) <= SOLES * UP)   # under the soles the strip is thin
    dark &= ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2) | (yy >= H - 1)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: clay left out)
        if k not in keep and sz[k] > 50 * UP * UP:
            print('unseeded clay', sz[k] // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP,
                  X0 + sl[1].stop // UP, Y0 + sl[0].stop // UP)
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)
    # her profile on John's line (PROFILE)
    P = up(PROFILE)
    # (ground: right of the line, and below its end at the jaw)
    right = lw.polygon_mask(g.shape, np.vstack([P, [P[-1][0], P[-1][1] + 10 * UP],
                                                [P[0][0] + 60 * UP, P[-1][1] + 10 * UP], [P[0][0] + 60 * UP, P[0][1]]]))
    pb = np.zeros(g.shape, bool)
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(PROFILE_BOX, (X0, Y0, X0, Y0))]
    pb[by0:by1, bx0:bx1] = True
    near = along(g.shape, polyline(PROFILE), 12) & (yy < P[-1][1])   # within 6 plate px of the line
    fig = np.where(pb, ~right & (fig | near), fig)
    profile = along(g.shape, polyline(PROFILE), PROFILE_W)

    firm = ink_lines(gl, closed, 22, 34)
    thin = ndi.distance_transform_edt(~morphology.skeletonize(firm)) <= LINE_MIN * UP / 2
    lines = (core | thin) & fig
    lines |= faint_lines(faint_c, fig, lines) & fig
    for pts in TRACED:
        lines |= traced(g, pts, TRACED_W) & fig
    for pts in FOLDS:
        P = np.array(pts, float)
        yy_ = np.linspace(P[0, 1], P[-1, 1], int((P[-1, 1] - P[0, 1]) * UP) + 1)
        xx_ = np.polyval(np.polyfit(P[:, 1], P[:, 0], 2), yy_)
        lines |= along(g.shape, up(np.c_[xx_, yy_]), LINE_MIN) & fig
    lines |= join_breaks(lines, np.maximum(closed - gl, faint_c), ndi.distance_transform_edt(fig)) & fig
    # every line at least LINE_MIN wide, so no thin neck breaks when the weight is evened out
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= LINE_MIN * UP / 2) & fig
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(2.5 * UP))
    edge = np.where(hand, fig & ~ndi.binary_erosion(fig, iterations=round(HAND_EDGE * UP)), edge)
    edge = np.where(pb, profile, edge)
    face = np.zeros(g.shape, bool)
    fx0, fy0, fx1, fy1 = [(v - o) * UP for v, o in zip(FACE, (X0, Y0, X0, Y0))]
    face[fy0:fy1, fx0:fx1] = True
    ink = lines | solid | edge | (face & face_dark & fig)
    lab, _ = ndi.label(ink)
    ink &= np.where(face, (np.bincount(lab.ravel()) > 3 * UP * UP)[lab], (np.bincount(lab.ravel()) > 12 * UP * UP)[lab])
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint)

    # all outside the figures stays open in the dark theme (the ground, its pockets, and the sliver of
    # paper above the cut under the soles), so no clay rim strays onto it
    held = ~fig
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight="own",
        title='Menelaus dropping his sword at the sight of Helen',
        desc='Line drawing after the 1847 plate of a red-figure amphora (Gerhard, Auserlesene griechische '
             'Vasenbilder III, Taf. CLXIX, 4); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
