"""Sophocles: the shepherd Euphorbos carrying the infant Oedipus, from Karl Reichhold's drawing of the
neck-amphora in Paris in Furtwängler and Reichhold, Griechische Vasenmalerei III (Munich, F. Bruckmann,
1927 at the plate's foot), Taf. 167, 1 ("Amphora in Paris", "Euphorbos mit dem Ödipuskind"), as
photographed by the Williams College Visual Resources Center (JSTOR, Furtwängler Griechische
Vasenmalerei, https://www.jstor.org/stable/community.16364348): the whole plate (3440 x 2615) and a view
of Euphorbos at twice its scale (3440 x 2518), which cuts off the crown of his head.
The vase: Attic red-figure neck-amphora attributed to the Achilles Painter, from Vulci, Paris, Cabinet
des médailles 372 (ARV2 987.4; BAPD 213824). Their names are painted beside them: ΕΥΦΟΡΒΟΣ, ΟΙΔΙΠΟΔΑΣ.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop,
the enlargement, the grey, the blurs, Minimum and Maximum, and the thresholds. Two steps stay in numpy and
scipy: the crown, resampled from the whole plate into a strip above the view (a scale and shift fitted by
SIFT, 0.22 px rms), and the masks' arithmetic (labels, unions, distances, fills, centre lines). The SVG
is written by linework.trace_svg.

Plate -> drawing, Furtwängler-Reichhold, red figures on the black ground (as bacchae.py):
  - Ground: the plate's dark, thin lines opened away; the large areas reaching the crop's edge, and the
    pockets the figures close in (POCKETS). Smaller dark areas inside the figures are paint (the hair).
  - Lines: the plate's black lines (local contrast), redrawn along their centres at WEIGHT (the F-R
    weight, 0.11%); the outline on the ground just outside the clay, as wide.

    python3 docs/redesign/drawings/tools/euphorbos.py view.jpg plate.jpg [qa.png]
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
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sophocles-euphorbos.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# Coordinates are the view's px ("scan px"); y < 0 is the crown strip, taken from the whole plate.
VIEW_TO_PLATE = (0.500709, 1559.130, 771.911)   # plate = s * view + (dx, dy) (SIFT, 870 matches, 0.22 px rms)
CROWN = 80                                       # scan px of strip above the view (the hair's top is at -38)
# Levelling: the panel's ruled edges lean (x = 979 - 0.0098 y on the left, 2433 - 0.0127 y on the right) and the
# meander band's top edge slopes (0.0019, fitted on 37 columns where the ground lies over it): a shear each way, about (LEVEL_C) them, makes
# the edges upright and the band level (a plain turn would not do both)
LEVEL_X, LEVEL_Y, LEVEL_C = 0.0112, 0.0019, (1700, 1000)
X0, Y0, X1, Y1 = 800, -60, 3070, 2085            # the crop: the figure and the spear, its butt to its blade
# the black panel's ruled edges, after levelling (x = a + b y, fitted at 42 rows each, 0.4-0.5 px rms): the
# spear runs past both onto the paper, where its own outline closes it (John, 2026-10-12: as printed, "then we
# can cut down to b if need be")
PANEL_L, PANEL_R = (968.87, 0.00199), (2419.38, -0.00136)
# where the spear crosses the panel's edges its outline (on the ground) meets its printed lines (on the paper)
# a px or two apart, and jogged: within SEAM scan px of each edge the two lines are redrawn straight between
# their centres measured just outside that band (rows: the spear's span at each edge, scan px)
SEAMS = [(1080, 1140), (940, 1000)]              # left edge, right edge
SEAM = 6
PAPER_T = 150                                    # outside the panel: paper lighter than this, reaching the
                                                 # crop's edge, is ground
FLOOR = 2075                                     # below this, out: the meander band (its top edge at
                                                 # 2080.7-2083.7 after levelling) and the ground over it;
                                                 # the soles' clay ends at 2074-2075, and their outline
                                                 # is drawn below the cut
UP = 2                                           # work at 2x the scan's px
SEEDS = [(1500, 1500), (1900, 300)]
DARK = 85                                        # ground and paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 8000                               # scan px: dark areas this large reaching the crop's edge
# ground the figures close in (a point in each, scan px): between the chiton and the mantle, above and below
# the spear; between the hem and the spear behind his hand
POCKETS = [(1840, 1010), (1837, 1075), (1550, 1070)]
LINE_R = 3.0                                     # scan px: the closing for the lines' local contrast
LINE_LO, LINE_HI = 22, 34
# Fine lines the finder broke or lost (John, 2026-10-12, on pass 1: "Find broken fine lines and complete them"):
# the plate's local contrast at a looser hysteresis (FAINT), drawn along its centres like the rest, where the
# drawing has no line (more than a line's width away); a piece is kept if it runs on from a drawn line's end
# (FAINT_TOUCH scan px of new line or more; one meeting a line along its side made ticks) or stands alone
# FAINT_LEN scan px or more (shorter ones were the print's grain, as hooks). Then line ends facing each other across JOIN_MAX scan px or less (the last JOIN_RUN scan px
# of each end pointing at the other within JOIN_ANGLE degrees) are joined straight where the plate's contrast
# holds at JOIN_C or more across the gap's middle 70%
FAINT, FAINT_TOUCH, FAINT_LEN = (12, 20), 6, 25
FAINT_SPUR = 6                                   # scan px: its spurs pruned (they made Y's on the lines)
# no faint lines in these boxes (scan px): the loose thong at the right ankle, a brushy stroke the finder drew
# as loops; the child's hair at the back of his head
FAINT_OFF = [(1700, 1700, 1800, 1850), (1795, 170, 1845, 210)]
FAINT_DARK = 70                                  # none within 3 scan px of the plate's broad dark strokes
                                                 # (darker than this): there they ran round the strokes
FAINT_R = 5                                      # scan px: its closing, wider than LINE_R (the wrappings'
                                                 # greyer lines are broad brushstrokes, 4-6 scan px)
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C = 12, 6, 35, 9
PAINT_NEAR, PAINT_CORE, PAINT_MIN = 1, 45, 80                  # (paint: the dark areas wider than the opening, with a core
                                                 # darker than PAINT_CORE; at 6 scan px round them, as on
                                                 # Bacchae, the pen lines near them came out ragged;
                                                 # smaller than PAINT_MIN scan px, the blots where lines
                                                 # cross: lines)
LINE_W = 2.2                                     # scan px: the lines' width, the plate's pen (its lines'
                                                 # half-maximum width, 2-2.5 scan px)
# faces and hands (boxes, scan px): Euphorbos' eye, nose and lips; the child's face; the child's hand on the
# chiton. At LINE_W the child's eye and mouth ran into blots and the fingers merged. Inside each box the
# lines are the plate darker than FACE_T (blurred FACE_BLUR scan px: the lines' cores 45-70, the clay
# 170-190), at their printed width, traced at their own size; specks under FACE_SPECK scan px dropped
FACES = [(1868, 113, 1995, 215), (1826, 268, 1935, 352), (1738, 380, 1860, 468),
         (1712, 718, 1822, 772),                              # (and the belt's two rows of triangles,
         (2876, 939, 2934, 951, 150)]                         # and the five dots on the spear's socket,
                                                              # paler: darker than 150)
# the sandals' straps and lattices (boxes, scan px): broad
# brushstrokes; at FACE_BLUR their edges came out ragged and broken by the print's grain, so here the plate
# blurred SANDAL_BLUR scan px, darker than SANDAL_T, its pinholes filled and its specks (under SANDAL_SPECK
# scan px) dropped. (The leg wrappings' greyer lines are the finder's: in a box like these they broke up)
SANDALS = [(1236, 1960, 1565, 2076), (1676, 1960, 2032, 2076)]
SANDAL_BLUR, SANDAL_T, SANDAL_SPECK = 1.2, 112, 8
# (pass 3: "make it better": the lattices at the heels came out as blots, the threshold running the strokes
# together; there the strokes are thin: the broad straps stay as found (what an opening of SANDAL_BROAD scan
# px leaves), and the rest is the plate's ridges (scikit-image's sato, sigmas 1-2 scan px, over SANDAL_RIDGE;
# pieces SANDAL_RLEN scan px or longer) drawn along their centres at the line width)
SANDAL_BROAD, SANDAL_RIDGE, SANDAL_RLEN = 1.8, 12, 8
# the petasos' thinned paint (a polygon round the crown and the cord, scan px): a wash whose opacity follows
# how much darker the plate is (blurred 1 scan px) than the hat's clay (HAT_CLAY, read at five points:
# 172-186), from HAT_A[0] at HAT_D[0] darker to HAT_A[1] at HAT_D[1]; the cord's broad brushstroke (darker
# than CORD_T, wider than 4 scan px) takes no lines
HAT = [(1415, 205), (1470, 188), (1560, 198), (1572, 260), (1545, 330), (1520, 385), (1470, 398), (1425, 392),
       (1398, 350), (1405, 290), (1435, 240)]
HAT_CLAY, HAT_D, HAT_A, CORD_T = 178, (22, 120), (0.15, 0.85), 115
HAT_SIGMA = 8                                    # scan px: the crown's grey smoothed (the cord's 1 px)
# (pass 4: the brim's two pen lines came out broken, taken for the cord where they touch it: the cord is only
# paint broader than CORD_W scan px; and the crown's wash, mottled and with a grey halo along the lines, is the
# depth averaged over the crown's own clay (lines and cord left out) over CROWN_SIGMA scan px)
CORD_W, CROWN_SIGMA = 5.5, 3
FACE_T, FACE_BLUR, FACE_SPECK = 100, 0.35, 3
# Euphorbos' hair (a polygon round it, scan px): the plate darker than HAIR_T (lightly smoothed; the hair
# 30-110, the clay line round it and the face 170 and over) joined to the paint's dark cores, its holes under
# HAIR_HOLE scan px filled. HAIR_STYLE "solid" (as Bacchae) or "wash": a tone whose opacity follows the
# plate, from HAIR_A[0] at grey HAIR_G[0] to HAIR_A[1] at HAIR_G[1]
HAIR = [(1620, -45), (2000, -45), (2000, 112), (1890, 112), (1875, 140), (1850, 150), (1815, 165), (1790, 240),
        (1620, 240)]
HAIR_T, HAIR_HOLE = 130, 6
# the curls' loose tips below the mass (grey strokes on the clay at the neck, apart from the paint's cores):
# wash too, if larger than TIP_MIN scan px and paler at their darkest than TIP_CORE (a pen line's core is darker)
TIP_MIN, TIP_CORE = 8, 60
HAIR_STYLE = "wash"                               # John, 2026-10-12: "Wash"
HAIR_A, HAIR_G = (0.45, 1.0), (130, 45)
# the child's curls, stippled in thinned paint (John on pass 2: "Back of child's head": no pale rim, curls not
# blotches, an outline at the back): the curls' mass (the plate darker than CHILD_T, blurred CHILD_SIGMA scan
# px; John on the style test, "don't have hair bleed into face") a flat wash at WASH_A[0]; on it each curl a
# stroke at WASH_A[1], CURL_W scan px wide, along the centre of the plate's darker marks (darker than their
# surroundings, closed over CURL_R scan px, by CURL_D or more; pieces CURL_MIN scan px long or more); where
# the mass meets the clay at the back of the head (left of CHILD_BACK), a line; no other lines inside but long
# strokes (the chin beside it), longer than CHILD_LONG scan px
CHILD_HAIR = [(1800, 246), (1835, 244), (1858, 254), (1868, 238), (1876, 219), (1900, 216), (1922, 224),
              (1937, 240), (1950, 262), (1950, 292), (1925, 286), (1905, 283), (1890, 280), (1880, 276),
              (1862, 275), (1852, 290), (1830, 306), (1800, 306), (1796, 280)]
WASH_R, WASH_D, WASH_A = 10, 20, (0.4, 0.85)
CURL_R, CURL_D, CURL_W, CURL_MIN = 3, 22, 1.8, 4
CHILD_SIGMA, CHILD_T, CHILD_LONG, CHILD_BACK = 1.0, 135, 25, 1845
# a strand of the child's hair down his nape against the black, printed paler (grey 80-140) than the mass and
# partly read as ground (John on pass 5: "the child's hair where you missed a spot"): inside HAIR_SPOT (scan
# px) the plate lighter than SPOT_T (blurred 1 scan px; the ground 25-35) is figure and hair wash
HAIR_SPOT = [(1912, 240), (1925, 236), (1933, 250), (1938, 262), (1942, 272), (1945, 282), (1934, 284),
             (1926, 276), (1919, 266), (1914, 255)]
SPOT_T, SPOT_CLOSE = 55, 4
# lines the finder broke or lost, drawn through hand-placed points (scan px) along the plate's darkest path
# (John on pass 2: "some incomplete lines with breaks"): Euphorbos' jaw over the child's hair; the child's cheek;
# the line from the child's neck to his shoulder
HAND_LINES = [[(1800, 225), (1815, 238), (1830, 247), (1845, 253), (1852, 254), (1858, 252), (1863, 247),
               (1867, 238), (1870, 225), (1872, 220)],
              [(1915, 303), (1916, 310), (1917, 316)],
              [(1937, 322), (1931, 329), (1925, 337), (1920, 345)]]
# the child's eye and nostril (John on pass 3: "Child's nose and eyes could be better. Fine lines are complete
# there in original"): inside these boxes (scan px) the lines are only these, drawn as smooth curves through
# points read off the levelled plate at 10-14x, CHILD_FACE_W scan px wide; the pupil is the plate darker than
# PUPIL_T inside the eye's contour
CHILD_FACE_BOXES = [(1852, 272, 1880, 302), (1870, 307, 1888, 325)]
CHILD_FACE_LINES = [[(1866, 276), (1863, 277.5), (1861, 279.5), (1859, 282), (1857.5, 285), (1856.8, 288),
                     (1856.5, 291), (1856.7, 293)],                                                # brow
                    [(1873.5, 279.5), (1870.5, 281.3), (1868, 282.8), (1866, 285), (1864.5, 287.5), (1863, 291),
                     (1862, 294.5)],                                                               # upper lid
                    [(1873.5, 279.5), (1874, 283), (1873.8, 286), (1872.5, 289.5), (1870.5, 292.5), (1868, 295),
                     (1866.5, 297), (1866, 298.5)],                                                # lower lid
                    [(1875, 317), (1875.5, 312), (1878, 310), (1881, 311), (1883, 314), (1882, 318),
                     (1880, 319.5)]]                                                               # nostril
# the child's nose, bridge to tip (John on pass 3: "make sure nose lines are fully drawn"): drawn whole through
# these points (read off the levelled plate at 14x): inside NOSE_AREA these lines only
CHILD_NOSE = [[(1838, 312), (1840, 308), (1842.5, 305), (1846, 304), (1849, 304.5), (1853, 308), (1857, 312),
               (1862, 316), (1866, 321), (1869, 325), (1872, 327), (1874.5, 326), (1876, 323)],
              [(1849, 305.5), (1847.5, 308), (1846, 311), (1845.5, 314)],                 # the tip's inner line
              [(1838, 313.5), (1841, 314.5), (1845, 314.8), (1847.5, 316), (1849, 318)]]  # the tip's base
NOSE_AREA = [(1838, 302), (1856, 300), (1876, 306), (1886, 308), (1886, 323), (1878, 331), (1866, 331),
             (1852, 319), (1846, 319), (1837, 314)]                                       # (scan px)
NOSE_DARK = 60                                   # the black paint printed in the tip (darker than this): solid
CHILD_FACE_W, PUPIL_T = 1.8, 48
# the child's iris (John on pass 3: "The child's eyes! I want the iris and pupils!"): a circle fitted to the
# plate's dark disc (darker than 100: its edge read at four points), drawn at IRIS_W scan px inside the lids;
# the pupil is the plate darker than PUPIL_T inside it, solid. The lids drawn at EYE_LW scan px
IRIS, IRIS_W, EYE_LW = (1865.0, 291.3, 3.6), 1.0, 1.4


# John's marks on pass 4, in PhotoCraft over the plate (euphorbos_marks_1.png: his layer alone, on the tool's work
# grid; 2026-10-12): all blue, ink to add (Euphorbos' upper lids, his chin closed against the child's head, the
# child's eye, nose, mouth, and the grey stroke down the child's back, the child's fingers, the cord round the
# petasos outlined, short lines at the belt). His strokes are drawn at the line width along their centres; his
# blue wider than MARK_SOLID work px stays solid as painted
MARKS_FILES = [Path(__file__).parent / "euphorbos_marks_1.png"]
MARK_SOLID = 4


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def composite(view, plate, out):
    """The view with the crown strip above it, resampled (cubic) from the whole plate; then levelled (cubic).
    Rows: CROWN px of strip, then the view."""
    v = np.asarray(Image.open(view).convert("RGB")).astype(np.float32)
    p = np.asarray(Image.open(plate).convert("RGB")).astype(np.float32)
    s, dx, dy = VIEW_TO_PLATE
    yy, xx = np.mgrid[-CROWN:0, 0:v.shape[1]].astype(np.float32)
    strip = np.stack([ndi.map_coordinates(p[..., c], [s * yy + dy, s * xx + dx], order=3, mode='nearest')
                      for c in range(3)], -1)
    c = np.r_[strip, v]
    cx, cy = LEVEL_C
    yy, xx = np.mgrid[0:c.shape[0], 0:c.shape[1]].astype(np.float32)   # levelled px (y with the strip)
    sx = xx - LEVEL_X * (yy - CROWN - cy)
    sy = yy + LEVEL_Y * (sx - cx)
    c = np.stack([ndi.map_coordinates(c[..., k], [sy, sx], order=3, mode='nearest') for k in range(3)], -1)
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(out)


def poly(px, py, pts):
    """Work-px mask of a polygon given in scan px."""
    x0, y0 = px[0, 0], py[0, 0]   # (the work grid's first px centre)
    P = np.array(pts, float)
    return lw.polygon_mask(px.shape, np.c_[(P[:, 0] - x0) * UP, (P[:, 1] - y0) * UP])


def add_tone(svg, alpha, box, step=0.05):
    """Paths of class "tone" in the line colour between the body and the lines, traced at the lines' own
    size: `alpha` (work px, 0 for none) in steps, each step's area drawn over the one below at the opacity
    that brings the total there to the step's, so no seam shows (as add_tone in andromache.py)."""
    x0, y0, x1, y1 = box
    a = alpha[y0:y1, x0:x1]
    lo = a[a > 0].min() if (a > 0).any() else 1
    paths, below = '', 0.0
    for v in np.arange(np.floor(lo / step) * step, a.max() + 1e-9, step):
        m = (a > 0) & (a >= v - step / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        op = 1.0 if v >= 1 - 1e-9 else 1 - (1 - v) / (1 - below)
        paths += f'<path class="tone" fill="currentColor" fill-opacity="{op:.3f}" stroke="none" d="{d}"/>'
        below = min(v, 0.999)
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def join_breaks(lines, contrast, tw, where):
    """The breaks in `lines` (work px) that JOIN_* describe, joined straight at width tw (as libation_bearers.py);
    `contrast` is the plate's local contrast (work px); only ends inside `where` are joined, but a free end
    may run on to any line (the outline too)."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1) & where)
    H, W = sk.shape

    def run_back(p):   # the end's last JOIN_RUN scan px of centre line, from the end inward
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

    out = np.zeros_like(lines)
    if len(ends) < 2:
        return out
    runs = [run_back(p) for p in ends]
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or len(runs[i]) < JOIN_RUN * UP / 2 or len(runs[j]) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        t = np.linspace(0.15, 0.85, max(int(np.hypot(*(b - a))), 3))
        q = a[None] + t[:, None] * (b - a)[None]
        if ndi.map_coordinates(contrast, q.T, order=1).min() < JOIN_C:
            continue
        n = int(np.hypot(*(b - a))) * 2 + 2
        for y, x in np.linspace(a, b, n):
            out[int(round(y)), int(round(x))] = True
        used |= {i, j}
    # then each end left free, run on straight along its own direction to the first line it meets within
    # JOIN_MAX scan px (a wrapping's line stopping short of the leg's outline), where the contrast holds
    for i, p in enumerate(ends):
        if i in used or len(runs[i]) < JOIN_RUN * UP / 2:
            continue
        d = runs[i][0] - runs[i][-1]
        d /= max(np.hypot(*d), 1e-6)
        hit = None
        for k in range(round(tw) + 1, JOIN_MAX * UP):
            y, x = np.round(p + k * d).astype(int)
            if not (0 <= y < H and 0 <= x < W):
                break
            if lines[y, x]:
                hit = k
                break
        if hit is None:
            continue
        q = p[None] + np.linspace(1, hit, hit * 2)[:, None] * d[None]
        if ndi.map_coordinates(contrast, q.T, order=1).min() < JOIN_C:
            continue
        for y, x in np.round(q).astype(int):
            out[y, x] = True
    return ndi.distance_transform_edt(~out) <= tw / 2 if out.any() else out


def smooth_line(pts, shape, x0, y0):
    """A smooth curve (a cubic spline, no smoothing) through points in scan px, as a 1 px mask at UP."""
    from scipy.interpolate import splprep, splev
    P = np.array(pts, float)
    tck, _ = splprep([(P[:, 0] - x0) * UP, (P[:, 1] - y0) * UP], s=0, k=min(3, len(P) - 1))
    n = int(np.hypot(*np.diff(P, axis=0).T).sum() * UP * 4) + 2
    x, y = splev(np.linspace(0, 1, n), tck)
    m = np.zeros(shape, bool)
    m[np.clip(np.round(y).astype(int), 0, shape[0] - 1), np.clip(np.round(x).astype(int), 0, shape[1] - 1)] = True
    return m


def masks(src, box=None):
    """Everything up to the ink: returns a dict of work-px arrays for the crop (or `box`, scan px)."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    w, h = x1 - x0, y1 - y0
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        pc(src, t / "up.png",
           ("image.crop", {"x": x0, "y": y0 + CROWN, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = round(LINE_R * UP)
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        r = round(FAINT_R * UP)
        pc(t / "gl.png", t / "closed5.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
        r = WASH_R * UP
        pc(t / "gw.png", t / "wclosed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": FACE_BLUR * UP}))
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        g, gl, closed, gs, gw, wclosed = (grey(t / f"{n}.png") for n in ("up", "gl", "closed", "gs", "gw", "wclosed"))
        closed5 = grey(t / "closed5.png")
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
        gf = grey(t / "gf.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + x0 - 0.5, (yy + 0.5) / UP + y0 - 0.5
    return dict(closed5=closed5, gf=gf, g=g, gl=gl, closed=closed, gs=gs, gw=gw, wclosed=wclosed, dark0=dark0, fine=fine, px=px, py=py, box=(x0, y0, x1, y1))


def main(view, plate, qa=None, box=None, out=OUT, dump=None):
    with tempfile.TemporaryDirectory() as td:
        comp = Path(td) / "comp.png"
        composite(view, plate, comp)
        m = masks(comp, box)
    g, gl, closed, gs, dark0, fine, px, py = (m[k] for k in ("g", "gl", "closed", "gs", "dark0", "fine", "px", "py"))
    x0, y0, x1, y1 = m['box']
    outside = py > FLOOR
    panel = (px > PANEL_L[0] + PANEL_L[1] * py) & (px < PANEL_R[0] + PANEL_R[1] * py)

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP), border_value=1) & ~outside & panel
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside | ~panel, iterations=2)]])
    is_ground = (size > (AUTO_GROUND if box is None else 400) * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        if not (x0 <= x < x1 and y0 <= y < y1):
            continue
        r = 15 * UP
        cy, cx = round((y - y0) * UP), round((x - x0) * UP)
        win = lab[max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
        dist = np.hypot(*np.mgrid[0:win.shape[0], 0:win.shape[1]] - np.array([[[min(r, cy)]], [[min(r, cx)]]]))
        iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
        assert win[iy, ix], f'no dark area near {(x, y)}'
        is_ground[win[iy, ix]] = True
    ground = is_ground[lab]
    inground = ground.copy()                     # (the panel's ground, where the outline is drawn)
    lab, _ = ndi.label((gs > PAPER_T) & ~panel & ~outside)
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    ground |= np.isin(lab, rim[rim > 0])

    fig = ~ground & ~outside
    lab, _ = ndi.label(fig)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = np.isin(lab, np.nonzero(sz > 2000 * UP * UP)[0])
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    # (on the paper the spear's printed outline is its lines, not its clay: the clay is the paper inside them)
    paper_lines = fig & ~panel & ~(gs > PAPER_T)
    fig &= panel | (gs > PAPER_T)
    fig = morphology.remove_small_objects(fig, max_size=200 * UP * UP)   # (slivers of paper at the panel's edge)
    spot = poly(px, py, HAIR_SPOT) & ndi.binary_opening(ndi.gaussian_filter(m['g'], UP) > SPOT_T,
                                                        structure=morphology.disk(UP))
    # (no cut into it: its darker streak is hair, and the edge runs smooth along the black, John: "NO. there is
    # no cut in": the strand with the figure closed over SPOT_CLOSE scan px and filled, inside HAIR_SPOT)
    sp = poly(px, py, HAIR_SPOT)
    spot = ndi.binary_fill_holes(ndi.binary_closing(spot | fig, structure=morphology.disk(SPOT_CLOSE * UP))) & sp
    fig |= spot
    ground &= ~spot
    inground &= ~spot

    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    solid = morphology.remove_small_objects(solid, max_size=PAINT_MIN * UP * UP)
    paint = fine & ndi.binary_dilation(solid, iterations=PAINT_NEAR * UP) & fig
    head = poly(px, py, HAIR)
    lab, n = ndi.label((gs < HAIR_T) & fig & head)
    hair = np.bincount(lab[solid & head].ravel(), minlength=n + 1) > 0
    hair[0] = False
    hair = hair[lab]
    holes = ndi.binary_fill_holes(hair) & ~hair
    hair |= holes & ~morphology.remove_small_objects(holes, max_size=HAIR_HOLE * UP * UP)
    lab, n = ndi.label((gs < HAIR_T) & fig & head & ~hair)
    if n:
        core = np.r_[0, np.array(ndi.minimum(gs, lab, range(1, n + 1)))]
        size = np.bincount(lab.ravel(), minlength=n + 1)
        tip = (core > TIP_CORE) & (size >= TIP_MIN * UP * UP)
        tip[0] = False
        hair |= tip[lab]
    paint &= ~head
    tone = np.zeros(g.shape, np.float32)
    if HAIR_STYLE == "solid":
        paint |= hair
    else:
        a0, a1 = HAIR_A
        gh = ndi.gaussian_filter(gs, UP)
        tone = np.where(hair, a0 + (a1 - a0) * np.clip((HAIR_G[0] - gh) / (HAIR_G[0] - HAIR_G[1]), 0, 1), 0)
    # the child's curls: a wash
    ch = poly(px, py, CHILD_HAIR) & fig
    depth = m['wclosed'] - m['gw']
    cw = ch & (ndi.gaussian_filter(m['g'], CHILD_SIGMA * UP) < CHILD_T)
    cw = ndi.binary_opening(cw, structure=morphology.disk(UP))
    cw = morphology.remove_small_objects(cw, max_size=20 * UP * UP)
    cw |= spot
    cw |= ndi.binary_fill_holes(cw) & ~morphology.remove_small_objects(ndi.binary_fill_holes(cw) & ~cw,
                                                                       max_size=40 * UP * UP)
    gc = ndi.gaussian_filter(m['g'], 0.5 * UP)
    rr = CURL_R * UP
    cd = ndi.grey_closing(gc, footprint=np.hypot(*np.mgrid[-rr:rr + 1, -rr:rr + 1]) <= rr) - gc
    csk = morphology.skeletonize((cd > CURL_D) & cw)
    lab, n = ndi.label(csk, structure=np.ones((3, 3)))
    csk &= (np.bincount(lab.ravel()) >= CURL_MIN * UP)[lab]
    curl = (ndi.distance_transform_edt(~csk) <= CURL_W * UP / 2) & cw if csk.any() else csk
    tone = np.where(cw, WASH_A[0], tone)
    tone = np.where(curl, WASH_A[1], tone)
    hat = poly(px, py, HAT) & fig
    cord = ndi.binary_opening((m['gw'] < CORD_T) & hat, structure=morphology.disk(round(CORD_W * UP / 2)))
    cord = ndi.binary_dilation(cord, iterations=UP) & (m['gw'] < CORD_T) & hat
    paint &= ~hat
    paint &= ~ch

    tw = LINE_W * UP - 1      # (a centre line grown by tw / 2 comes out tw + 1 px wide)
    firm = apply_hysteresis_threshold(closed - gl, LINE_LO, LINE_HI)
    black = firm & (fig | paper_lines) & ~ndi.binary_dilation(paint, iterations=UP) & \
        ~(head & ndi.binary_dilation(hair, iterations=3 * UP))   # (strand ends at the fringe: the wash's)
    lab, n = ndi.label(black & ch)
    sk = np.bincount(lab[morphology.skeletonize(black & ch)].ravel(), minlength=n + 1)
    black &= ~(ch & ~(sk > CHILD_LONG * UP)[lab])
    black &= ~ndi.binary_dilation(spot, iterations=UP)   # (the strand's darker streak is a curl in the wash)
    lines = centre_lines(black, tw, 3 * UP, 2 * tw) | paint
    faces = np.zeros_like(fig)
    face_t = np.full(fig.shape, FACE_T, np.float32)
    dotbox = np.zeros_like(fig)                  # (boxes with their own threshold add dots only, pieces
    for b in FACES:                              # under 20 scan px, to the lines, which they keep)
        inb = (px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3])
        faces |= inb
        if len(b) > 4:
            face_t[inb] = b[4]
            dotbox |= inb
    sandals = np.zeros_like(fig)
    for b in SANDALS:
        sandals |= (px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3])
    faces |= sandals
    fl = (m["gf"] < face_t) & faces & ~sandals & (fig | paper_lines) & ~ch
    sd = (ndi.gaussian_filter(m['g'], SANDAL_BLUR * UP) < SANDAL_T) & sandals & fig
    sd |= ndi.binary_fill_holes(sd) & ~morphology.remove_small_objects(ndi.binary_fill_holes(sd) & ~sd, max_size=3 * UP * UP)
    sd = morphology.remove_small_objects(sd, max_size=SANDAL_SPECK * UP * UP)
    broad = ndi.binary_opening(sd, structure=morphology.disk(round(SANDAL_BROAD * UP)))
    broad = ndi.binary_dilation(broad, iterations=UP // 2) & sd
    if sandals.any():
        from skimage.filters import sato
        ys_, xs_ = np.nonzero(sandals)
        bsl = (slice(ys_.min(), ys_.max() + 1), slice(xs_.min(), xs_.max() + 1))
        rid = np.zeros_like(sd)
        rid[bsl] = sato(m['g'][bsl], sigmas=[UP, 1.5 * UP, 2 * UP], black_ridges=True) > SANDAL_RIDGE
        rid &= sandals & fig & (ndi.gaussian_filter(m['g'], 0.75 * UP) < 150) & \
            ndi.binary_erosion(fig, iterations=round(1.5 * UP))
        rsk = morphology.skeletonize(rid & ~broad)
        lab, n = ndi.label(rsk, structure=np.ones((3, 3)))
        rsk &= (np.bincount(lab.ravel()) >= SANDAL_RLEN * UP)[lab]
        thin = ndi.distance_transform_edt(~rsk) <= tw / 2 if rsk.any() else rsk
    else:
        thin = np.zeros_like(sd)
    fl |= broad | thin
    holes = ndi.binary_fill_holes(fl) & ~fl
    fl |= holes & ~morphology.remove_small_objects(holes, max_size=UP * UP)
    fl = morphology.remove_small_objects(fl, max_size=FACE_SPECK * UP * UP)
    fl &= ~(dotbox & morphology.remove_small_objects(fl & dotbox, max_size=20 * UP * UP))
    lines = (lines & ~(faces & ~dotbox)) | fl
    lines &= ~ndi.binary_dilation(cord, iterations=UP)
    hd = HAT_CLAY - ndi.gaussian_filter(m['gw'], UP)
    own = hat & ~ndi.binary_dilation(lines | cord, iterations=2 * UP)
    cs_ = CROWN_SIGMA * UP
    hda = ndi.gaussian_filter(np.where(own, hd, 0), cs_) / np.maximum(ndi.gaussian_filter(own.astype(np.float32), cs_), 1e-6)
    hd = np.where(cord, hd, hda)
    hw = hat & (hd > HAT_D[0]) & ~ndi.binary_dilation(lines & ~cord, iterations=UP // 2)
    hw = morphology.remove_small_objects(ndi.binary_opening(hw, structure=morphology.disk(UP)), max_size=30 * UP * UP)
    hh = ndi.binary_fill_holes(hw) & ~hw & ~lines   # (pale holes in the crown's wash: wash too)
    hw |= hh & ~morphology.remove_small_objects(hh, max_size=300 * UP * UP)
    lab, n = ndi.label(lines & hat & ~cord)       # (and specks of line inside it go)
    lines &= ~(hat & (np.bincount(lab.ravel(), minlength=n + 1) < 12 * UP * UP)[lab] & (lab > 0))
    # (the crown's grey smoothed over HAT_SIGMA within the wash only, so the clay round it does not pale its
    # edge; the cord, broader dark, kept sharp)
    sg = HAT_SIGMA * UP
    crown = hw & ~ndi.binary_dilation(cord, iterations=UP)
    hs = ndi.gaussian_filter(np.where(crown, hd, 0), sg) / np.maximum(ndi.gaussian_filter(crown.astype(np.float32), sg), 1e-6)
    hd = np.where(crown, hs, hd)
    tone = np.where(hw, HAT_A[0] + (HAT_A[1] - HAT_A[0]) * np.clip((hd - HAT_D[0]) / (HAT_D[1] - HAT_D[0]), 0, 1), tone)
    tone = np.round(tone / 0.05) * 0.05
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & (dt <= tw) & ndi.binary_dilation(inground | outside, iterations=UP) & panel
    ink = (lines & (fig | paper_lines)) | edge
    # (the back of the child's head: a line along the curls' mass where it meets the clay)
    back = cw & ~ndi.binary_erosion(cw, iterations=round(tw)) & (px < CHILD_BACK) & \
        ndi.binary_dilation(fig & ~cw, iterations=round(tw) + 1)
    ink |= back
    # (the child's eye, nose and nostril: only the hand-placed lines inside their areas)
    cfb = np.zeros_like(ink)
    eye_marks = np.zeros_like(ink)               # (traced at their own size: the hand lines in cfb are not)
    hand = None                                  # (cfb's own ink, laid in again after the later finders)
    for b in CHILD_FACE_BOXES:
        cfb |= (px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3])
    cfb |= poly(px, py, NOSE_AREA)
    if all(x0 <= b[0] and b[2] <= x1 and y0 <= b[1] and b[3] <= y1 for b in CHILD_FACE_BOXES):
        ink &= ~cfb
        eye_c = np.zeros_like(ink)
        for k, pts in enumerate(CHILD_FACE_LINES + CHILD_NOSE):
            seg = smooth_line(pts, ink.shape, x0, y0)
            ink |= ndi.distance_transform_edt(~seg) <= (EYE_LW if k in (1, 2) else CHILD_FACE_W) * UP / 2
            if k in (1, 2):
                eye_c |= seg
        g05 = ndi.gaussian_filter(m['g'], 0.5 * UP)
        lo = smooth_line([CHILD_FACE_LINES[1][-1], CHILD_FACE_LINES[2][-1]], ink.shape, x0, y0)  # (closes the fill)
        inside = ndi.binary_fill_holes(ndi.binary_dilation(eye_c | lo, iterations=1))
        ix, iy, ir = IRIS
        dc = np.hypot(px - ix, py - iy)
        iris = inside & (np.abs(dc - ir) <= IRIS_W / 2)
        pupil = inside & (dc < ir) & (g05 < PUPIL_T)
        pupil = ndi.binary_fill_holes(ndi.binary_closing(pupil, structure=morphology.disk(UP)))
        ink |= iris | pupil
        eye_marks = iris | pupil
        ink |= ndi.binary_opening(poly(px, py, NOSE_AREA) & (g05 < NOSE_DARK), structure=morphology.disk(UP // 2 + 1))
        hand = ink & cfb
    # (hand-placed lines)
    hc = ndi.gaussian_filter(m['g'], 0.7 * UP)
    hcost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(hc, size=(5 * UP, 5 * UP)) - hc, 0, None) / 12)
    for pts in HAND_LINES:
        if not all(x0 <= x < x1 and y0 <= y < y1 for x, y in pts):   # (a test box that leaves it out)
            continue
        P = [((x - x0) * UP, (y - y0) * UP) for x, y in pts]
        xy = lw.livewire(hcost, P)
        seg = np.zeros_like(ink)
        seg[np.clip(xy[:, 1].astype(int), 0, ink.shape[0] - 1), np.clip(xy[:, 0].astype(int), 0, ink.shape[1] - 1)] = True
        near = ndi.binary_dilation(seg, iterations=3 * UP) & ~ndi.binary_dilation(seg, iterations=round(tw / 2) + 1)
        ink &= ~(near & ink & ~edge & ndi.binary_dilation(seg, iterations=3 * UP)) | ~near
        ink |= ndi.distance_transform_edt(~seg) <= tw / 2
    # (fine lines the finder broke or lost: FAINT, JOIN)
    zone = (fig | paper_lines) & ~head & ~ch & ~hat & ~(faces & ~dotbox)
    contrast = m['closed5'] - gl
    loose = apply_hysteresis_threshold(contrast, *FAINT) & zone & ~ndi.binary_dilation(paint, iterations=UP)
    for b in FAINT_OFF:
        loose &= ~((px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3]))
    lcl = centre_lines(loose, tw, 3 * UP, FAINT_SPUR * UP)
    new = lcl & ~ndi.binary_dilation(ink, iterations=round(tw)) & zone
    lab, n = ndi.label(new)
    if n:
        length = np.bincount(lab[morphology.skeletonize(new)].ravel(), minlength=n + 1) / UP
        touch = np.zeros(n + 1, bool)
        isk = morphology.skeletonize(ink)
        nb = ndi.convolve(isk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
        tips = ndi.binary_dilation(isk & (nb == 1), iterations=round(tw) + 3)
        touch[np.unique(lab[tips & new])] = True
        dark_near = ndi.binary_dilation(ndi.binary_opening(gs < FAINT_DARK, structure=morphology.disk(UP)),
                                        iterations=3 * UP)
        near = np.zeros(n + 1, bool)
        near[np.unique(lab[dark_near & new])] = True
        keep = ((touch & (length >= FAINT_TOUCH)) | (length >= FAINT_LEN)) & ~near
        keep[0] = False
        added = keep[lab]
        added |= lcl & ndi.binary_dilation(added, iterations=round(tw) + 2)   # (run back to the line it left)
    else:
        added = np.zeros_like(ink)
        dark_near = np.zeros_like(ink)
    ink |= added
    joins = join_breaks(ink, contrast, tw, zone & ~dark_near) & (fig | paper_lines)
    ink |= joins
    for (ya, yb), (a, b) in zip(SEAMS, (PANEL_L, PANEL_R)):
        rows = (py >= ya) & (py < yb)
        xe = a + b * (ya + yb) / 2
        band = rows & (np.abs(px - xe) < SEAM)
        cols = [round((xe - SEAM - 1 - x0) * UP), round((xe + SEAM + 1 - x0) * UP)]
        r0, r1 = round((ya - y0) * UP), round((yb - y0) * UP)
        if not (0 <= cols[0] and cols[1] < ink.shape[1] and r0 >= 0 and r1 <= ink.shape[0]):
            continue
        cen = []
        for c in cols:
            lab_, n_ = ndi.label(ink[r0:r1, c])
            cen.append(sorted(ndi.center_of_mass(ink[r0:r1, c], lab_, range(1, n_ + 1))))
        if len(cen[0]) != 2 or len(cen[1]) != 2:
            continue
        ink &= ~band
        for (ca,), (cb,) in zip(cen[0], cen[1]):
            seg = np.zeros_like(ink)
            for t in np.linspace(0, 1, 4 * (cols[1] - cols[0])):
                seg[round(r0 + ca + t * (cb - ca)), round(cols[0] + t * (cols[1] - cols[0]))] = True
            ink |= ndi.distance_transform_edt(~seg) <= tw / 2
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]
    # (small marks left loose inside the hair's wash: strand ends, not lines)
    lab, n = ndi.label(ink)
    size = np.bincount(lab.ravel(), minlength=n + 1)
    inh = np.bincount(lab[head].ravel(), minlength=n + 1)
    loose = (inh == size) & (size < 60 * UP * UP)
    loose[0] = False
    ink &= ~loose[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, firm=firm & fig,
                            added=added, joins=joins, tone=tone.astype(np.float16),
                            gs=gs.astype(np.uint8))
    if hand is not None:
        ink = (ink & ~cfb) | hand
    if box is None:
        blue = np.zeros_like(ink)
        for mf in MARKS_FILES:
            mk = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
            assert mk.shape[:2] == ink.shape, (mk.shape, ink.shape)
            r_, g_, b_, a_ = (mk[..., i] for i in range(4))
            blue |= (a_ > 40) & (b_ > r_ + 40) & (b_ > g_ + 20)
        if blue.any():
            marks = ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= tw / 2
            marks |= ndi.binary_opening(blue, structure=morphology.disk(MARK_SOLID))
            ink |= marks
            eye_marks |= marks          # (traced at their own size)
    info = lw.trace_svg(
        ink, Path(out), body=fig, open_holes=~fig, weight="drawn", dots=(fl & ~cfb | eye_marks) & ink,
        title='The shepherd Euphorbos carrying the infant Oedipus',
        desc='Line drawing after Karl Reichhold\'s drawing of the neck-amphora by the Achilles Painter, Paris, '
             'Cabinet des médailles 372 (Furtwängler and Reichhold, Griechische Vasenmalerei III, Taf. 167); '
             'cut out and retraced.')
    if tone.any():
        add_tone(Path(out), tone, info['box'])
    print(out, info)
    if qa:
        lw.qa_overlay(g, Path(out), info['box'], Path(qa))
        lw.qa_dark(Path(out), info['box'], Path(qa).with_suffix('.dark.png'))
    return info


if __name__ == '__main__':
    main(*sys.argv[1:4])
