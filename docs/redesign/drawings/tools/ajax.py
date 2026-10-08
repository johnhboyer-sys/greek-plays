"""Ajax: Ajax carrying the body of Achilles, between Phoenix and Briseis (left) and two warriors
(right), from the lower picture (fig. 4) of Gerhard, Auserlesene griechische Vasenbilder III (1847),
Taf. CCXI-CCXII, as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_211_ROEM_212.jpg/full/full/0/default.jpg
(4178 x 2965, a double plate across a fold; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0253)

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0). Geometry
(levelling the two pages across the fold) is not image filtering: it is numpy/scipy here, as in
alcestis.py and libation_bearers.py.

The fold. The plate is printed across two pages, folded at x = FOLD; the fold is a ridge, not a
gutter (the lines bend at it, none are lost). The frame's edges are printed straight, but in the scan
the right page stands about 30 px higher next to the fold and is about 2% shorter (tilted away from
the camera), and both edges bend near the fold. Measured on the band's palmettes, the two pages have
the same horizontal scale (period 78.3 and 78.0 px), so the levelling is vertical only: column by
column, the band's upper edge goes to row T0 and the panel's lower edge to row T0 + HP.

    python3 docs/redesign/drawings/tools/ajax.py gerhard1847bd3_211_212.jpg [qa.png]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "ajax.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
UP = 3                          # work at 3x the levelled frame's px

FOLD = 2040                     # the fold in the scan (x), where both edges kink
SX0, SX1, SY0 = 1040, 3140, 1000   # the levelled frame: scan columns SX0-SX1, row 0 at scan row SY0 (before levelling)
EDGE_X = (1080, 3120)           # columns the edges are measured on
EDGE_T = 70                     # grey: an edge is where the plate falls below this
TOP_ROWS = (1020, 1090)         # the band's upper border line lies in these rows (scanned downward)
BOTTOM_ROWS = (2250, 2400)      # the panel's lower edge (the ground stripe's foot) in these (scanned upward)
T0, HP = 70.0, 1268.0           # the levelled band edge (row) and the frame's height (the left page's, far from the fold)
H_OUT = 1420                    # rows in the levelled frame
# the panel, as drawn (levelled px): just below the band's lower line (its foot wavers 223-229), the ground stripe's top edge, the side
# lines' inner edges (x a quartic in y, fitted within 1.8 px)
BAND_Y, STRIPE_Y = 230.0, 1325.0
LEFT = (-1.3019857e-10, 3.7734458e-07, -1.8266381e-04, -0.26672890, 237.789312)
RIGHT = (-1.2294879e-10, 4.5273646e-07, -7.5782171e-04, 0.69513261, 1786.830150)
BOX = (0, 180, 2100, 1330)      # the work box in the levelled frame (x0, y0, x1, y1)
# the dark mass over Ajax's shoulders rises into the band, right of the fold, up to MASS_TOP and no
# further right than MASS_X1 (levelled px); MASS_OPEN, the opening that parts it from the band's line
MASS_TOP, MASS_X1, MASS_OPEN = 180, 1300, 5
DARK, WHITE = 85, 172           # grey (lightly blurred): black below DARK, the added white above WHITE
WHITE_MIN = 20                  # levelled px^2: smaller white is a speck
AUTO_GROUND = 3000              # levelled px^2: clay areas this large are ground
POCKETS = []                    # pockets of ground the figures close in (a point in each, levelled px)
FIG_MIN = 400                   # levelled px^2: smaller pieces on the ground are inscriptions and specks
INC_T, INC_W = 28, 1.3          # incisions: lighter than the Minimum-then-Maximum by INC_T; drawn INC_W px wide
DL_T, DL_ABS, LINE_W = 28, 118, 1.5   # thin dark lines: darker than the Maximum-then-Minimum by DL_T and than DL_ABS
WHITE_LINE = 160                # grey: on the white, a line is darker than this
THIN = 3.0                      # levelled px: black parts thinner than this are drawn as lines
# joining broken lines: ends pointing at each other within JOIN_ANGLE degrees (over their last JOIN_RUN
# levelled px), at most JOIN_MAX apart, where the plate's contrast along the gap holds at JOIN_C; a free
# end runs on to the black when it points at it within REACH levelled px
JOIN_RUN, JOIN_ANGLE, JOIN_MAX, JOIN_C, REACH = 3, 15, 8, 12, 2
RIM = 1.5                       # levelled px: the clay round the figures on the dark theme
ANGLES = tuple(range(0, 180, 15))   # Motion Blur directions (degrees)
ALONG = 3                       # levelled px: the Motion Blur's length
LINE_R = 5                      # levelled px: the Minimum/Maximum radius that finds the thin lines


def edges(g):
    """The band's upper edge and the panel's lower edge at every column SX0-SX1 (scan px, sub-pixel),
    each side of the fold smoothed on its own (the fold bends them in a sharp V)."""
    gs = ndi.gaussian_filter(g, 0.8)

    def cross(p, start, step):    # first index where p falls below EDGE_T, sub-pixel
        i = np.where(p < EDGE_T)[0]
        if not len(i) or i[0] == 0:
            return np.nan
        i = i[0]
        return start + step * ((i - 1) + (p[i - 1] - EDGE_T) / (p[i - 1] - p[i]))

    xs = np.arange(*EDGE_X)
    top = np.array([cross(gs[TOP_ROWS[0]:TOP_ROWS[1], x], TOP_ROWS[0], 1) for x in xs])
    bot = np.array([cross(gs[BOTTOM_ROWS[1]:BOTTOM_ROWS[0]:-1, x], BOTTOM_ROWS[1], -1) for x in xs])
    cols = np.arange(SX0, SX1, dtype=float)
    out = []
    for e in (top, bot):
        full = np.empty_like(cols)
        for side in (xs <= FOLD, xs >= FOLD):
            x, v = xs[side], e[side]
            ok = ~np.isnan(v)
            # a column where a figure or a speck crosses the line reads off it: drop readings more than
            # 3 px from the running median, then smooth
            med = ndi.median_filter(np.interp(x, x[ok], v[ok]), 21)
            ok &= np.abs(v - med) <= 3
            sm = ndi.gaussian_filter1d(np.interp(x, x[ok], v[ok]), 4, mode='nearest')
            sel = (cols <= FOLD) if side[0] else (cols >= FOLD)
            full[sel] = np.interp(cols[sel], x, sm)
        out.append(full)
    return out


def level(img):
    """The scan levelled (see the docstring): columns SX0-SX1, H_OUT rows; the band's upper edge at
    row T0, the panel's lower edge at row T0 + HP."""
    g = np.asarray(Image.fromarray(img).convert('L'), np.float32)
    top, bot = edges(g)
    v = np.arange(H_OUT, dtype=float)
    X = np.broadcast_to(np.arange(SX0, SX1, dtype=float), (H_OUT, SX1 - SX0))
    Y = top[None] + (v[:, None] - T0) * (bot - top)[None] / HP
    out = np.stack([ndi.map_coordinates(img[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def plates(lev, box):
    """PhotoCraft's images of the levelled frame's `box` (x0, y0, x1, y1), at UP: the plate in grey (up),
    lightly blurred (gs); gs smoothed along the lines (along): Motion Blur over ALONG levelled px at
    ANGLES directions, of which each pixel keeps the one farthest from their mean (a line, dark or
    light, keeps its tone when blurred along itself and fades across), so close strokes of a hatching
    stay apart while each evens out (LESSONS: smooth along each stroke first); and its local contrast
    over LINE_R levelled px: its Minimum then Maximum (opened; along less it is the light lines) and
    its Maximum then Minimum (closed; it less along is the dark lines). The mean and the choice per
    pixel are numpy."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    r = LINE_R * UP // 2
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(lev).save(t / "lev.png")
        pc(t / "lev.png", t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        for i, a in enumerate(ANGLES):
            pc(t / "gs.png", t / f"mb{i}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ALONG * UP}))
        mean = sum(grey(t / f"mb{i}.png") for i in range(len(ANGLES))) / len(ANGLES)
        along, best = mean.copy(), np.zeros_like(mean)
        for i in range(len(ANGLES)):
            m = grey(t / f"mb{i}.png")
            far = np.abs(m - mean) > best
            along[far], best[far] = m[far], np.abs(m - mean)[far]
        Image.fromarray(np.clip(np.round(along), 0, 255).astype(np.uint8)).save(t / "along.png")
        pc(t / "along.png", t / "opened.png", ("filter.other.minimum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.maximum", {"radius": r, "preserve": "squareness"}))
        pc(t / "along.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        return {k: grey(t / f"{k}.png") for k in ("up", "gs", "along", "opened", "closed")}


def skeleton_paths(mask):
    """The centre lines of `mask` as ordered (y, x) paths, split where lines meet; a closed loop comes
    as one path whose ends are the same point."""
    sk = morphology.skeletonize(mask)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    node = sk & (nb != 2)                       # ends and junctions
    H, W = sk.shape
    seen = np.zeros_like(sk)
    steps = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def nbrs(y, x):
        return [(y + dy, x + dx) for dy, dx in steps if 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]]

    paths = []
    for y, x in np.argwhere(node):
        for q in nbrs(y, x):
            if node[q] and (q < (y, x)):
                paths.append(np.array([(y, x), q]))   # two nodes side by side: once
                continue
            if node[q] or seen[q]:
                continue
            path, prev, cur = [(y, x)], (y, x), q
            while True:
                path.append(cur)
                if node[cur]:
                    break
                seen[cur] = True
                nxt = [n for n in nbrs(*cur) if n != prev and not seen[n] and n not in path[-3:]]
                if not nxt:
                    break
                nn = [n for n in nxt if node[n]]
                prev, cur = cur, (nn or nxt)[0]
            paths.append(np.array(path))
    for y, x in np.argwhere(sk & ~node & ~seen):  # loops with no node
        if seen[y, x]:
            continue
        path, prev, cur = [], None, (y, x)
        while cur is not None and not seen[cur]:
            seen[cur] = True
            path.append(cur)
            nxt = [n for n in nbrs(*cur) if n != prev and not seen[n]]
            prev, cur = cur, (nxt[0] if nxt else None)
        path.append(path[0])
        paths.append(np.array(path))
    return paths


def smooth_path(p, sigma):
    """A path (y, x) smoothed along its length (Gaussian, `sigma` px), its ends kept where they are (a
    loop smoothed round)."""
    p = p.astype(float)
    if len(p) < 4:
        return p
    if (p[0] == p[-1]).all():
        q = ndi.gaussian_filter1d(p[:-1], sigma, axis=0, mode='wrap')
        return np.vstack([q, q[:1]])
    q = ndi.gaussian_filter1d(p, sigma, axis=0, mode='nearest')
    # pin the ends, easing the smoothing in over `sigma` px so a line still meets what it met
    t = np.minimum(np.arange(len(p)), np.arange(len(p))[::-1])[:, None]
    a = np.clip(t / max(2 * sigma, 1), 0, 1)
    return p * (1 - a) + q * a


def draw_paths(shape, paths, widths):
    """The paths (y, x at UP) drawn round-ended, each `widths[i]` work px wide: a pixel is ink when its
    centre lies within half the width of the path (measured to points 0.2 px apart along it)."""
    m = np.zeros(shape, bool)
    for w in sorted(set(widths)):
        pts = []
        for p, pw in zip(paths, widths):
            if pw != w:
                continue
            if len(p) == 1:
                pts.append(p.astype(float))
                continue
            seg = np.diff(p, axis=0)
            n = np.maximum(np.ceil(np.hypot(*seg.T) / 0.2).astype(int), 1)
            for a, d, k in zip(p[:-1], seg, n):
                pts.append(a + np.arange(k)[:, None] / k * d)
            pts.append(p[-1:].astype(float))
        if not pts:
            continue
        P = np.vstack(pts)
        r = w / 2
        near = np.zeros(shape, bool)
        ij = np.clip(P.round().astype(int), 0, np.array(shape) - 1)
        near[ij[:, 0], ij[:, 1]] = True
        near = ndi.binary_dilation(near, iterations=int(np.ceil(r)) + 1)
        cand = np.argwhere(near)
        d, _ = cKDTree(P).query(cand.astype(float), distance_upper_bound=r + 0.5)
        hit = cand[d <= r]
        m[hit[:, 0], hit[:, 1]] = True
    return m


def free_ends(paths, sk):
    """The free ends of the paths (ends of a skeleton line, not junctions): (path index, which end,
    point, outward unit direction over its last JOIN_RUN levelled px)."""
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    out = []
    for i, p in enumerate(paths):
        if len(p) < 3 or (p[0] == p[-1]).all():
            continue
        k = min(len(p) - 1, JOIN_RUN * UP)
        for end, q, r in ((0, p[0], p[k]), (1, p[-1], p[-1 - k])):
            if nb[tuple(q)] == 1:
                d = (q - r).astype(float)
                out.append((i, end, q.astype(float), d / max(np.hypot(*d), 1e-9)))
    return out


def join_and_reach(paths, sk, contrast, stop):
    """Segments that join a broken line and run a stopped one on: two free ends that point at each
    other (within JOIN_ANGLE degrees, both ways) across at most JOIN_MAX levelled px of plate whose
    `contrast` holds at JOIN_C or more (median) are joined straight; a free end that points at `stop`
    (the black) within REACH levelled px is run on to it. Returns the segments as paths (y, x)."""
    ends = free_ends(paths, sk)
    segs, used = [], set()
    if ends:
        P = np.array([e[2] for e in ends])
        cos = np.cos(np.radians(JOIN_ANGLE))
        pairs = sorted(cKDTree(P).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(P[ij[0]] - P[ij[1]])))
        for a, b in pairs:
            if a in used or b in used or ends[a][0] == ends[b][0]:
                continue
            v = P[b] - P[a]
            u = v / np.hypot(*v)
            if ends[a][3] @ u < cos or ends[b][3] @ -u < cos:
                continue
            t = np.linspace(0, 1, max(int(np.hypot(*v)), 2) + 1)
            q = P[a][None] + t[:, None] * v[None]
            if np.median(ndi.map_coordinates(contrast, q.T, order=1)) < JOIN_C:
                continue
            segs.append(q)
            used |= {a, b}
    H, W = stop.shape
    for k, (i, end, q, d) in enumerate(ends):
        if k in used:
            continue
        for step in range(2, REACH * UP + 1):
            y, x = np.round(q + step * d).astype(int)
            if not (0 <= y < H and 0 <= x < W):
                break
            if stop[y, x]:
                segs.append(np.linspace(q, q + step * d, step + 1))
                break
    return segs


def even_lines(mask, width, sigma=1.5, min_len=0, max_width=None, contrast=None, stop=None):
    """The lines in `mask` redrawn along their centre lines, smoothed along each line (`sigma` levelled
    px), at an even width (levelled px): `width`, or with max_width, each line's own median width
    (from its centre to its edge in the mask, in steps of a quarter px), no less than `width` and no
    more than `max_width`. A thresholded line's ragged edge and a pixel skeleton's zigzag both go.
    Paths shorter than `min_len` levelled px that end free at both ends are dropped (grain). With
    `contrast` and `stop`, broken lines are joined and stopped ones run on (join_and_reach)."""
    sk = morphology.skeletonize(mask)
    raw = skeleton_paths(mask)
    if contrast is not None:
        extra = join_and_reach(raw, sk, contrast, stop)
    keep = [p for p in raw if not min_len or len(p) >= min_len * UP or (p[0] == p[-1]).all()]
    if max_width:
        dt = ndi.distance_transform_edt(mask)
        widths = [round(4 * np.clip(np.median(2 * dt[tuple(p.T)] - 1) / UP, width, max_width)) / 4 * UP
                  for p in keep]
    else:
        widths = [width * UP] * len(keep)
    paths = [smooth_path(p, sigma * UP) for p in keep]
    if contrast is not None:
        paths += extra
        widths += [width * UP] * len(extra)
    return draw_paths(mask.shape, paths, widths)


def write_svg(lines, body, out, title, desc):
    """The house format (as linework.trace_svg writes it, and seven.py): 1000 units tall, the body path
    under the lines, traced at the work px."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda t: t.replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def main(src, qa=None, dump=None):
    lev = level(np.asarray(Image.open(src).convert('RGB')))
    P = plates(lev, BOX)
    g, gs, opened, closed, al = P['up'], P['gs'], P['opened'], P['closed'], P['along']
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + BOX[0], (yy + 0.5) / UP + BOX[1]    # levelled px
    disk = lambda r: morphology.disk(round(r * UP))  # noqa: E731

    # outside the panel: the band above its lower line, the ground stripe (the feet stand on its top
    # edge), the side lines and the paper beyond them
    outside = (py < BAND_Y) | (py >= STRIPE_Y) | (px < np.polyval(LEFT, py)) | (px > np.polyval(RIGHT, py))
    black0 = gs < DARK
    # but the dark mass rises into the band, right of the fold: its black there, opened so the band's
    # line and palmettes drop away, and grown back as far as the opening took it
    band = black0 & (py < BAND_Y) & (py >= MASS_TOP) & (px >= FOLD - SX0)
    seed = ndi.binary_opening(band, structure=disk(MASS_OPEN)) & (px < MASS_X1)
    lab, _ = ndi.label(seed)   # (only what runs down to the panel: the palmettes' bulbs stand clear of it)
    seed = np.isin(lab, np.unique(lab[seed & (py >= BAND_Y - 2)]))
    mass = ndi.binary_dilation(seed, structure=disk(MASS_OPEN)) & band
    outside &= ~mass

    white = ndi.binary_opening((gs > WHITE) & ~outside, structure=disk(1))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > WHITE_MIN * UP * UP)[lab]

    # ground: the clay, opened so thin lines do not join it; its large areas and the listed pockets
    clay = ndi.binary_opening(~black0 & ~white & ~outside, structure=disk(2))
    lab, _ = ndi.label(clay)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[round((y - BOX[1]) * UP), round((x - BOX[0]) * UP)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]

    # the figures: all else in the panel; specks on the ground (the inscriptions, stray marks) go
    fig = ndi.binary_fill_holes(~ground & ~outside) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=disk(0.5))
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) > FIG_MIN * UP * UP)[lab]
    white &= fig

    # incisions (light lines in the black) and the thin dark lines (on the white, the clay bands, the
    # ground inside the figures), each redrawn along its smoothed centre line at an even width
    solid = ndi.binary_opening(black0, structure=disk(2))
    inc_raw = ((al - opened) > INC_T) & ndi.binary_closing(black0, structure=disk(2)) & ~white & fig
    dark_raw = ((closed - al) > DL_T) & (al < DL_ABS) & ~solid & fig
    # and on the white (eyes, mouths, fingers), anything darker than WHITE_LINE
    dark_raw |= (al < WHITE_LINE) & ~solid & ndi.binary_erosion(ndi.binary_closing(white, structure=disk(2)), structure=disk(0.5)) & fig
    inc = even_lines(inc_raw, INC_W, min_len=2)
    darkl = even_lines(dark_raw, LINE_W, min_len=2, max_width=THIN, contrast=closed - al,
                       stop=ndi.binary_opening(black0, structure=disk(THIN / 2)))
    # the black: its parts wider than THIN (the thinner ones, hatching and spear shafts, are the lines
    # above), less the incisions
    black = ndi.binary_opening(black0, structure=disk(THIN / 2)) & ~inc
    # the white's outline where it meets the ground: a line just outside it (the plate prints a faint
    # line there), as in seven.py
    wline = ~white & ~solid & ~outside & ~ground & (ndi.distance_transform_edt(~white) <= LINE_W * UP)
    wline |= ~fig & ~outside & (ndi.distance_transform_edt(~white) <= LINE_W * UP)
    lines = ((black | darkl) & fig) | wline
    body = ndi.distance_transform_edt(~fig) <= RIM * UP
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, white=white, lines=lines,
                            inc_raw=inc_raw, dark_raw=dark_raw, black0=black0)

    info = write_svg(
        lines, body, OUT,
        title='Ajax carrying the body of Achilles',
        desc='Line drawing after the 1847 plate of an archaic black-figure amphora (Gerhard, Auserlesene '
             'griechische Vasenbilder III, Taf. CCXI-CCXII, 4); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
