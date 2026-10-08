"""Acharnians: a seated warrior in a crested helmet, his round shield at his side and his right hand
raised, from a comic "departure of the warrior" played on a stage, on the Apulian red-figure
bell-krater Würzburg, Martin von Wagner Museum H 4689, side A (Beazley Archive 1006966: Apulian,
red-figure, bell-krater, HA4689; CVA Würzburg 4, pp. 12-13, Beilage 1.3, pl. 3.1-4). Attributed to the
McDaniel Painter, c. 380-370 BC (RVAp 4/245), as the photographer's file description gives it; the
museum has no public object record, and the CVA text was not read. He is the type of Lamachus, the
crested general of Acharnians, whose slave brings out his spear as he arms (1118-1120); the old man
at the door here holds out a spear. The link is the type, not an identification of this vase with the
play. Photos: ArchaiOptix, CC BY-SA 4.0; _07 is the drawing's source, _04, _05 and _06 serve the vase's
shape (and _06 its shield rim under the sheen). The drawing traces only the ancient painting, so it
carries no licence (John, 2026-10-08); the photographer is credited.
https://commons.wikimedia.org/wiki/File:McDaniel_Painter_-_RVAp_4-245_-_departure_of_warrior_as_phlyax_play_-_draped_youths_-_W%C3%BCrzburg_MvWM_H_4689_-_07.jpg

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop,
the R-B channel (Channel Mixer), the grey, the blurs, the cap on the grey (Levels), the Maximum and
Minimum filters and the thresholds. numpy only combines the masks PhotoCraft made (labels, unions, hysteresis) and measures.
Two steps are geometry, not image filtering, and stay in numpy/scipy: taking the painting off the
vase's curve (vase_unroll.py) and fitting the vase (--refit). The SVG is written by
linework.trace_svg.

Photo -> drawing:
  - The vase is taken off its curve (vase_unroll.py, as for Euphorbos and Antigone). Its profile and
    the cameras of 07, 04, 05 and 06 were fitted together (MODEL): to the upper edge of the meander
    band under the stage (a painted circle) in all four, the vase's outline in 04, 05 and 06, and
    points of the painting matched between 07 and the other three (SIFT). All four were taken on an
    EOS 6D: 07 at 50 mm, 04 at 40 mm, 05 and 06 at 28 mm (EXIF), so the focal lengths are fixed;
    07 and 04 are uncropped, 05 and 06 cropped (their centres fitted). The vase is flattened
    without shear (vase_unroll.flatten) about his axis and 07 laid onto it at 07's own scale at his
    waist. His head checked against 06 laid onto the same flat: they agree within 1-2 px.
  - Clay against glaze by red less blue (R-B), in which the glaze's white sheen reads as glaze.
    He is the clay joined to SEEDS: the old man's spear tip, at the left, is a separate shape and
    left out. The stage he sits on is cut away along its top edge (STAGE): the back foot stands on
    the stage's painted line, which is kept as its sole; the stool's right leg runs into the plank.
  - The shield's rim lies under the glaze's sheen at the top right: checked on photo 06 laid onto the
    same flat, and walled (WALLS) where a black dot and the top ray, painted up to the rim, met the
    ground's black.
  - Lines: the painting's dark lines inside him, by grey (luminance; scratches in the clay are
    light, not dark): the paint at its own width, the outline, and the solid black (hair, beard, the
    helmet's inside). Lines broken where the glaze flaked are joined (JOIN_*, JOINS); faint strokes of
    thinned glaze are found by local contrast and drawn along fitted curves (FAINT); the mended break
    across his lap and shield leaves no line (MEND).

    python3 docs/redesign/drawings/tools/acharnians.py H4689-07.jpg H4689-03.jpg H4689-02.jpg [qa.png]
    python3 docs/redesign/drawings/tools/acharnians.py H4689-07.jpg H4689-04.jpg H4689-05.jpg H4689-06.jpg --refit
    python3 docs/redesign/drawings/tools/acharnians.py H4689-03.jpg H4689-04.jpg --refit03
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
from scipy.interpolate import CubicSpline, LinearNDInterpolator, RegularGridInterpolator
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "acharnians.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit again; it prints these
# numbers). World units are arbitrary (camera 07's D fixes them); y = 0 on the meander band's upper
# edge, up the vase.
CAMERAS = {
    "07": dict(D=2100, H=366.13, b=-0.0631696, p=0.119942, g=0.0606851, f=7600, cx=1824, cy=2736),
    "04": dict(D=2779.2, H=653.395, b=0.0699611, p=-0.0052447, g=-0.0146033, f=6080, cx=2736, cy=1824),
    "05": dict(D=3445.33, H=-596.409, b=-0.316352, p=0.0454717, g=0.0236176, f=4256, cx=1922.29, cy=1768.52),
    "06": dict(D=3540.23, H=1197.65, b=0.0915277, p=0.0334136, g=0.0325088, f=4256, cx=1789.03, cy=1022.63),
    # the old man's photo, fitted to the model above with the profile and the other cameras held: points
    # matched between 03 and 04 (which shows both figures), taken onto the vase through 04's camera
    # (fit_03; median 2.7 px). It agrees with 07 at the spear's tip, which both show, within 2.5 px.
    "03": dict(D=2100.74, H=422.538, b=-0.0586314, p=-0.0949274, g=0.0289648, f=7600, cx=1824, cy=2736),
    # photo 02 (EF 40 mm, uncropped; a later shoot), fitted as 03 is, to points matched with 04 (median 2.0 px):
    # sharp where 03 is not, at the old man's back foot and his white hair and beard
    "02": dict(D=2759.23, H=518.207, b=0.0208488, p=-0.0429247, g=-0.0657326, f=6080, cx=2736, cy=1824),
}
PROFILE_Y = [-300, -100, 100, 300, 500, 700, 900, 1100, 1300, 1500]
PROFILE_R = [410.7, 615.6, 714.8, 764.3, 789.0, 813.6, 858.0, 902.3, 946.7, 991.1]
TURNS = {"04": 17.668, "05": 4.449, "06": 1.373, "03": 12.2913, "02": 46.4725}  # degrees each photo is turned from 07
PITCH = 10.0 / 1520.0  # mm per px on the 6D's sensor (EXIF focal plane resolution)
FOCAL_MM = {"07": 50, "04": 40, "05": 28, "06": 28, "03": 50}
CROPPED = {"07": False, "04": False, "05": True, "06": True}
# The data for fit_model: rough guides (photo px) to the meander band's upper edge in each photo,
# rough guides to the vase's left (0) and right (1) outline where it stands clear of the handles, the
# little lekythos beside it and the chair behind it, and the scale at which each photo is matched
# to 07 (07 at MATCH_07).
FIT_BAND = {"07": [(100, 5150), (1500, 5115), (2500, 5050), (2900, 5005)],
            "04": [(1500, 3150), (2200, 3185), (2900, 3195), (3600, 3180), (4100, 3130)],
            "05": [(920, 2280), (1700, 2224), (2420, 2280)],
            "06": [(1000, 2305), (1650, 2350), (2300, 2290)]}
FIT_BAND_SCALE = {"07": 1.0, "04": 0.75, "05": 0.6, "06": 0.6}   # the band's width against 07's
FIT_OUTLINE = {"05": {0: [(783, 1700), (817, 2000), (933, 2400), (1217, 2800), (1333, 3000)],
                      1: [(2633, 1820), (2593, 2000), (2467, 2400), (2183, 2800), (2067, 3000)]},
               "06": {0: [(685, 1480), (796, 1950)],
                      1: [(2567, 1450), (2519, 1800), (2452, 2000), (2352, 2200), (2185, 2400)]},
               "04": {0: [(1083, 1900), (1194, 2400), (1306, 2800)],
                      1: [(4444, 2400), (4361, 2800), (4139, 3200)]}}
MATCH_07, FIT_MATCH = 0.25, {"04": 0.5, "05": 1.0, "06": 1.0}


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def band_edge(rgb, rough, sc, half=70, step=8):
    """(u, v) along the meander band's upper edge: per column near the rough guide, the step from the
    black strip above (R-B under 45 for 60 px, scaled by sc) to the clay strip below, to a fraction
    of a px; kept where the points lie on one smooth curve."""
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5)
    r = np.array(rough, float)
    f = np.polyfit(r[:, 0], r[:, 1], min(2, len(r) - 1))
    dk, cl = int(60 * sc), int(14 * sc)
    out = []
    for u in range(int(r[0, 0]), int(r[-1, 0]), step):
        vg, col, best = int(np.polyval(f, u)), RB[:, u], None
        for v in range(vg - half, vg + half):
            above, below = col[v - dk:v - 4].mean(), col[v + 3:v + 3 + cl].mean()
            if above < 45 and below > 85 and col[v - dk:v - 4].max() < 80 and (best is None or below - above > best[0]):
                best = (below - above, v, above, below)
        if best:
            _, v, above, below = best
            mid, seg = (above + below) / 2, col[v - 8:v + 9]
            k = np.nonzero((seg[:-1] < mid) & (seg[1:] >= mid))[0]
            if len(k):
                k = k[np.argmin(abs(k - 8))]
                out.append((u, v - 8 + k + (mid - seg[k]) / (seg[k + 1] - seg[k])))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 3), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 2]


def outline(rgb, rough, half=70, step=8):
    """(side, u, v): the vase's outline row by row near the rough guides, where the light background
    meets the dark vase (the strongest step), to a fraction of a px."""
    L = ndi.gaussian_filter(rgb.mean(2), 1.5)
    out = []
    for side, pts in rough.items():
        p = np.array(pts, float)
        s = 1 if side == 0 else -1   # inward
        for v in range(int(p[0, 1]), int(p[-1, 1]), step):
            u0 = int(np.interp(v, p[:, 1], p[:, 0])) - half
            g = np.gradient(L[v, u0:u0 + 2 * half]) * -s
            x = u0 + int(np.argmax(g))
            if g.max() < 4:
                continue
            mid = (np.median(L[v, x - 20 * s:x - 6 * s:s]) + np.median(L[v, x + 6 * s:x + 20 * s:s])) / 2
            xs = np.arange(x - 6, x + 7)
            kk = np.nonzero(np.diff(np.sign(L[v, xs] - mid)))[0]
            if len(kk):
                kk = kk[np.argmin(abs(kk - 6))]
                out.append((side, xs[kk] + (mid - L[v, xs[kk]]) / (L[v, xs[kk] + 1] - L[v, xs[kk]]), v))
    return np.array(out)


def fit_model(photos: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit). Needs opencv for SIFT."""
    import cv2
    names = ["07", "04", "05", "06"]
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in names}
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(n, k):
        g = cv2.resize(cv2.cvtColor(rgb[n].astype(np.uint8), cv2.COLOR_RGB2GRAY), None, fx=k, fy=k,
                       interpolation=cv2.INTER_AREA)
        kp, d = sift.detectAndCompute(g, None)
        return np.array([p.pt for p in kp]) / k, d

    k7, d7 = feats("07", MATCH_07)
    matches = {}
    for n, k in FIT_MATCH.items():
        kn, dn = feats(n, k)
        m = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(d7, dn)
        a, b = np.float32([k7[x.queryIdx] for x in m]), np.float32([kn[x.trainIdx] for x in m])
        _, inl = cv2.findHomography(a, b, cv2.RANSAC, 25.0 / k, maxIters=5000)
        inl = inl.ravel().astype(bool)
        matches[n] = np.hstack([a[inl], b[inl]])
    views = {}
    for n in names:
        sil = outline(rgb[n], FIT_OUTLINE[n]) if n in FIT_OUTLINE else np.zeros((0, 3))
        views[n] = dict(size=rgb[n].shape[1::-1], f=FOCAL_MM[n] / PITCH, crop=CROPPED[n],
                        band=band_edge(rgb[n], FIT_BAND[n], FIT_BAND_SCALE[n]), sil=[tuple(r) for r in sil])
    x0 = []
    for n in names:
        x0 += [2100.0, 600.0, 0.15, 0.0, 0.0, FOCAL_MM[n] / PITCH, 0.0, 0.0]
    x0 += [800.0] * len(PROFILE_Y) + [0.0, 0.0] + [0.0] * len(FIT_MATCH)
    cams, R, _, turns, report, _ = vu.fit(views, np.array(PROFILE_Y, float), matches=matches, d0=2100.0,
                                          x_start=np.array(x0), nfev=600, outlier=30, rounds=3)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


# ---------------------------------------------------------------- the flat

# The vase flattened over FLAT_THETA x FLAT_Y (start, stop, step), the meridian through CENTRE_07 (a
# point of photo 07 at his waist) straight up; G px per world unit (07's own scale there, up the
# vase). The frame is the flat image of the photo-07 box BOX07 around him, MARGIN units wider.
FLAT_THETA, FLAT_Y = (-1.2, 1.2001, 0.008), (-200.0, 1500.1, 8.0)
CENTRE_07, BOX07, MARGIN = (1650.0, 2600.0), (60, 420, 3200, 4700), 30.0


def frame():
    """The flat and its frame: (cams, R, inv, X0, Y1, G, W, H); inv maps flat world (x, y) to (theta,
    y) on the vase."""
    cams, R = vase()
    c = cams["07"]
    th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    yr = (yy[0], yy[-1])
    t0 = vu.photo_to_surface(c, R, np.array([CENTRE_07]), yr)[0]
    P = vu.project(c, vu.surface(R, np.array([t0[1], t0[1] + 1.0]), np.array([t0[0], t0[0]])))
    G = float(np.hypot(*(P[1] - P[0])))
    XY = vu.flatten(R, th, yy, centre=float(t0[0]))
    TH, Y = np.meshgrid(th, yy)
    inv = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))
    fwd = [RegularGridInterpolator((yy, th), XY[..., k]) for k in (0, 1)]
    x0, y0, x1, y1 = BOX07
    s = np.linspace(0, 1, 20)
    edge = np.vstack([np.c_[x0 + s * (x1 - x0), np.full(20, y0)], np.c_[x0 + s * (x1 - x0), np.full(20, y1)],
                      np.c_[np.full(20, x0), y0 + s * (y1 - y0)], np.c_[np.full(20, x1), y0 + s * (y1 - y0)]])
    cr = vu.photo_to_surface(c, R, edge, yr)
    q = np.c_[cr[:, 1], cr[:, 0]]
    fx, fy = fwd[0](q), fwd[1](q)
    X0, X1, Y0, Y1 = fx.min() - MARGIN, fx.max() + MARGIN, fy.min() - MARGIN, fy.max() + MARGIN
    W, H = int((X1 - X0) * G), int((Y1 - Y0) * G)
    return cams, R, inv, X0, Y1, G, W, H


def flat_image(p07):
    """Photo 07 laid onto the flat frame (H x W x 3, uint8)."""
    cams, R, inv, X0, Y1, G, W, H = frame()
    c = cams["07"]
    step = 4
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    tq = inv(np.stack([X0 + gx.ravel() / G, Y1 - gy.ravel() / G], -1))
    uv = vu.project(c, vu.surface(R, tq[:, 1], tq[:, 0])).reshape(gx.shape + (2,))
    u = ndi.zoom(np.nan_to_num(uv[..., 0], nan=-1e4), step, order=1)[:H, :W]
    v = ndi.zoom(np.nan_to_num(uv[..., 1], nan=-1e4), step, order=1)[:H, :W]
    a = np.asarray(Image.open(p07).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


def flat_region(src, name, region):
    """Photo `name` laid onto the flat, over `region` (x0, y0, x1, y1) of the widened frame (WIDE)."""
    cams, R, inv, X0f, Y1f, G, _, _ = frame()
    rx0, ry0, rx1, ry1 = region
    w, h, step = rx1 - rx0, ry1 - ry0, 4
    gx, gy = np.meshgrid(np.arange(rx0, rx1 + step, step) - WIDE[0], np.arange(ry0, ry1 + step, step) - WIDE[1])
    tq = inv(np.stack([X0f + gx.ravel() / G, Y1f - gy.ravel() / G], -1))
    th = tq[:, 0] + np.radians(TURNS.get(name, 0.0))
    uv = vu.project(cams[name], vu.surface(R, tq[:, 1], th)).reshape(gx.shape + (2,))
    u = ndi.zoom(np.nan_to_num(uv[..., 0], nan=-1e4), step, order=1)[:h, :w]
    v = ndi.zoom(np.nan_to_num(uv[..., 1], nan=-1e4), step, order=1)[:h, :w]
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


# The old man stands to the warrior's left, mostly outside photo 07: the flat is widened by WIDE flat px
# to the left and at the top (widened px = the warrior's flat px + WIDE), and photo 03 laid onto it there.
WIDE = (2600, 300)

# ---------------------------------------------------------------- him

X0, Y0, X1, Y1 = 480, 450, 4000, 4900     # crop of the flat (flat px) round him
CLAY = 50                                 # clay: R-B above this (lightly blurred); glaze and its sheen under it
SEEDS = [(1700, 3400)]                    # his thigh (flat px)
LINE_DARK = 85                            # his painted lines: grey darker than this (lightly blurred)
# Ground: the glaze, its painted lines (up to OPEN*2 px wide) opened away; the large areas reaching the
# frame's edge. Smaller glaze areas inside him are paint (hair, beard).
OPEN, AUTO_GROUND = 14, 40000
# where the ground between his parts is narrower than that (fingers), it is found at FINE_OPEN (boxes,
# flat px)
FINE = [(1050, 500, 1700, 1000)]
FINE_OPEN = 3
# His edge follows the clay's worn border: smoothed (Gaussian, SMOOTH flat px; FINE_SMOOTH in FINE), and
# drawn EDGE flat px wide: the house weight (0.22% of his height), as on Mika; the painted lines keep
# their own width (median 15 px, 0.37%): this painter's relief lines are bold
SMOOTH, FINE_SMOOTH, EDGE = 3.0, 1.5, 9
# A black dot on the shield's rim touches the ground in 07, where the glaze's sheen greys the thin clay
# strip of the rim outside it; photo 06, laid onto the same flat, shows the strip (and the rim there
# agrees with 07's to a few px). WALLS (flat px) mark the strip as clay, WALL_W px wide, its outer side
# on 06's rim, so the dot stays paint inside the shield. Above it, the shield's top ray is painted black
# up to the rim, where the ground's black meets it, and the drawing took it for ground (an outlined
# sliver of rim beside it; John, 2026-10-08: "this circled part should be black ink", "that part of the
# shield's design"): its wall runs along the rim, a quadratic fitted to the rim's outer edge on either
# side (x 3150-3325 and 3580-3650; the sheen hides it between), 3 px in from it, and meets the dot's.
WALLS = [[(3317, 2215), (3347, 2244), (3377, 2275), (3407, 2307), (3437, 2341), (3467, 2376), (3497, 2413),
          (3527, 2451), (3543, 2468)],
         [(3543, 2468), (3553, 2484), (3562, 2501), (3570, 2516)]]
WALL_W = 8
# Lines are drawn at least LINE_MIN px wide.
LINE_MIN = 6
# Faint strokes of thinned glaze (crest feathers, a stroke on the shield, a few folds), too light for
# LINE_DARK: the grey's local contrast at fine scale (PhotoCraft: the grey lightly blurred, clipped at
# FAINT_CAP by Levels, so white scratches do not make the clay beside them look dark; its Maximum then
# Minimum over FAINT_R px, less it), with hysteresis (FAINT, on the Levels scale), FAINT_EDGE px or more
# inside his edge and off the mended break (MEND, flat y), kept where a piece is FAINT_LEN px long or
# more and FAINT_RATIO times longer than wide; each drawn along a curve fitted to it, LINE_MIN wide
FAINT_CAP, FAINT_R, FAINT, FAINT_EDGE, FAINT_LEN, FAINT_RATIO = 140, 6, (16, 34), 18, 30, 4
MEND = (3465, 3575)
# the line weight, pinned at the first full pass's own (0.213% of the longer side), so later changes to
# a few lines do not re-weight them all (as libation_bearers.py)
WEIGHT = 0.00213
# Painted lines broken where the glaze has flaked off (the clay shows through): line ends whose last
# JOIN_RUN px point at each other within JOIN_ANGLE degrees, across at most JOIN_MAX px, joined straight
# at the lines' width, where the join crosses no other line and keeps EDGE px off his edge
JOIN_RUN, JOIN_ANGLE, JOIN_MAX = 18, 20, 45
# and breaks the rule above misses (longer, or the ends bent by the flaking), each checked over the photo:
# line ends (flat px; a polyline where the line runs on through thin dashes), joined at the lines' width: the belt (across a short dash), a
# fold across the mend, the lines across the white scratches on his chest and lap, a faint stroke on the
# shield, a crest feather, a fine line at his shoulder
JOINS = [((2470, 3193), (2554, 3199)), ((2471, 3514), (2469, 3529)), ((2601, 2322), (2600, 2366), (2593, 2395), (2591, 2412)),
         ((3382, 3637), (3433, 3655)), ((2668, 2132), (2639, 2185)), ((2578, 3260), (2536, 3325)),
         ((1692, 1620), (1686, 1624)), ((2784, 1021), (2792, 1026))]
# specks of glaze on the clay (not lines): ink pieces under SPECK px^2 standing alone; the face (FACE,
# flat px) keeps its small marks
SPECK, FACE = 150, (2050, 1200, 2950, 2000)
# and flecks of clay the ink closes in, under FLECK px^2, are inked (where the rim strip tapers to its point
# between the shield's top ray and the outline; the rest are a few px); real pockets are 500 px^2 or more
FLECK = 200
# The stage: its top edge is a painted line, which the back foot's sole runs along to its left tip and
# the stool's right leg stands on. Below the line's lower edge is stage (cut away); the line stays,
# as their sole. Its lower edge, measured every 25 flat px (the half-way crossing from the line to
# the plank's clay under it), x from STAGE_X0; smoothed over 5 points; flat beyond its ends.
STAGE_X0 = 1330
STAGE = [4782.3, 4795.6, 4793.4, 4788.9, 4785.2, 4783.1, 4777.3, 4779.9, 4775.5, 4772.0, 4773.0, 4768.3, 4764.4,
         4765.2, 4761.6, 4758.5, 4756.8, 4754.6, 4753.6, 4754.9, 4753.3, 4752.1, 4751.4, 4749.2, 4749.8, 4750.4,
         4750.2, 4749.7, 4749.8, 4748.7, 4749.2, 4749.9, 4751.1, 4751.9, 4752.8, 4754.3, 4757.7, 4758.6, 4759.0,
         4760.7, 4762.4, 4764.2, 4765.3, 4765.6, 4765.7, 4766.1, 4765.9, 4767.0, 4767.4, 4766.6, 4766.6, 4765.3,
         4764.9, 4765.7, 4765.3, 4765.1, 4765.5, 4766.7, 4768.0, 4768.6, 4770.2, 4769.6, 4769.0, 4769.6, 4771.2,
         4772.0, 4772.7, 4771.6, 4773.0, 4773.2, 4771.5]

def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def along(shape, pts, width, origin=None):
    """A line `width` px wide along hand-placed points (flat px), at the crop's px (the crop's corner
    `origin`, the warrior's by default)."""
    ox, oy = origin or (X0, Y0)
    P = np.array([(x - ox, y - oy) for x, y in pts], float)
    path = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])])
    m = np.zeros(shape, bool)
    m[path[:, 1].round().astype(int), path[:, 0].round().astype(int)] = True
    return ndi.distance_transform_edt(~m) <= width / 2


def join_breaks(lines, inner):
    """The breaks in `lines` that JOIN_* describe, joined (a mask of the joins); `inner` is where
    joins may run."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    ends = np.argwhere(sk & (nb == 1))
    dt = ndi.distance_transform_edt(lines)
    H, W = sk.shape

    def run_back(p):   # the end's last JOIN_RUN px of centre line, from the end inward
        path, seen = [tuple(p)], {tuple(p)}
        for _ in range(JOIN_RUN):
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
    out = np.zeros_like(lines)
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or len(runs[i]) < JOIN_RUN // 2 or len(runs[j]) < JOIN_RUN // 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        q = a[None] + np.linspace(0, 1, int(np.hypot(*(b - a))) + 2)[:, None] * (b - a)[None]
        qi = tuple(q.round().astype(int).T)
        if not inner[qi].all():
            continue
        if set(lab[qi]) - {0, lab[tuple(ends[i])], lab[tuple(ends[j])]}:   # it would cross another line
            continue
        w = np.median([dt[tuple(r.astype(int))] for r in np.vstack([runs[i], runs[j]])]) * 2
        m = np.zeros_like(lines)
        m[qi] = True
        out |= ndi.distance_transform_edt(~m) <= max(w, LINE_MIN) / 2
        used |= {i, j}
    return out


def faint_lines(contrast, inside, lines):
    """The faint strokes FAINT_* describe, each drawn along a quadratic fitted to it, LINE_MIN wide."""
    from skimage.filters import apply_hysteresis_threshold
    m = apply_hysteresis_threshold(contrast, *FAINT) & inside & ~ndi.binary_dilation(lines, iterations=4)
    lab, _ = ndi.label(m, structure=np.ones((3, 3)))
    out = np.zeros_like(m)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float) + (sl[0].start, sl[1].start)
        if len(p) < 20:
            continue
        c = p.mean(0)
        w, v = np.linalg.eigh(np.cov((p - c).T))
        if 4 * np.sqrt(max(w[1], 0)) < FAINT_LEN or np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)) < FAINT_RATIO:
            continue
        t, u = (p - c) @ v[:, 1], (p - c) @ v[:, 0]
        f = np.polyfit(t, u, 2)
        tt = np.linspace(t.min(), t.max(), int(t.max() - t.min()) + 2)
        q = (c + tt[:, None] * v[:, 1] + np.polyval(f, tt)[:, None] * v[:, 0]).round().astype(int)
        out[q[:, 0], q[:, 1]] = True
    return ndi.distance_transform_edt(~out) <= LINE_MIN / 2


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def warrior(src):
    """The warrior: (ink, figure, grey), in his crop of the flat (X0, Y0, X1, Y1)."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(flat_image(src)).save(t / "flat.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "flat.png", t / "c.png", ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}))
        pc(t / "c.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}), ("image.adjustments.threshold", {"level": CLAY}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 1.0}),
           ("image.adjustments.levels", {"inWhite": FAINT_CAP}))
        pc(t / "gf.png", t / "cf.png", ("filter.other.maximum", {"radius": FAINT_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": FAINT_R, "preserve": "squareness"}))
        g = grey(t / "g.png")
        faint_c = grey(t / "cf.png") - grey(t / "gf.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    sy = np.convolve(np.pad(STAGE, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    outside = yy + Y0 > np.interp(xx + X0, STAGE_X0 + 25 * np.arange(len(sy)), sy)
    dark = ~clay & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, pts, WALL_W)
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN))
    fine = np.zeros(g.shape, bool)
    for bx0, by0, bx1, by1 in FINE:
        fine[by0 - Y0:by1 - Y0, bx0 - X0:bx1 - X0] = True
    ground0 = np.where(fine, ndi.binary_opening(dark, structure=morphology.disk(FINE_OPEN)), ground0)
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    ground = ((size > AUTO_GROUND) & np.isin(np.arange(len(size)), rim))[lab]
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[y - Y0, x - X0] for x, y in SEEDS}
    assert 0 not in keep
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground
    f = fig.astype(np.float32)
    fig = np.where(fine, ndi.gaussian_filter(f, FINE_SMOOTH), ndi.gaussian_filter(f, SMOOTH)) > 0.5
    paint = dark & fig
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE)
    lines = (core | paint) & fig & ~edge
    face = np.zeros(g.shape, bool)
    face[FACE[1] - Y0:FACE[3] - Y0, FACE[0] - X0:FACE[2] - X0] = True
    lab, _ = ndi.label(lines, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    touch = np.unique(lab[ndi.binary_dilation(edge, iterations=2)])
    small = (sz < SPECK) & ~np.isin(np.arange(len(sz)), touch)
    lines &= ~(small[lab] & ~face)   # (before the joins: a speck in a gap would block its join)
    mend = (yy + Y0 > MEND[0]) & (yy + Y0 < MEND[1])
    lines |= faint_lines(faint_c, (to_edge > FAINT_EDGE) & ~mend, lines) & fig
    lines |= join_breaks(lines & (to_edge > EDGE + 2), to_edge > EDGE + 2)
    dt = ndi.distance_transform_edt(lines)
    for pts in JOINS:
        P = np.array(pts, float)
        ua, ub = (P[0] - P[1]) / np.hypot(*(P[0] - P[1])), (P[-1] - P[-2]) / np.hypot(*(P[-1] - P[-2]))
        near = [dt[int(p[1]) - Y0 - 6:int(p[1]) - Y0 + 7, int(p[0]) - X0 - 6:int(p[0]) - X0 + 7].max() for p in (P[0], P[-1])]
        lines |= along(g.shape, [P[0] + 3 * ua, *P[1:-1], P[-1] + 3 * ub], max(2 * np.median(near), LINE_MIN)) & fig
    ink = lines | edge
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    return ink, fig, g

def fit_03(p03, p04) -> None:
    """Fit camera 03 (and its turn) to the model, everything else held, and print it: points matched
    between 03 and 04, taken onto the vase through 04's camera. Needs opencv for SIFT."""
    import cv2
    from scipy.optimize import least_squares
    cams, R = vase()
    yr = (FLAT_Y[0], FLAT_Y[1])
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(path, k):
        g = cv2.resize(cv2.imread(str(path), cv2.IMREAD_GRAYSCALE), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        kp, d = sift.detectAndCompute(g, None)
        return np.array([p.pt for p in kp]) / k, d

    k3, d3 = feats(p03, 0.25)
    k4, d4 = feats(p04, 0.5)
    m = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(d3, d4)
    a, b = np.float32([k3[x.queryIdx] for x in m]), np.float32([k4[x.trainIdx] for x in m])
    _, inl = cv2.findHomography(a, b, cv2.RANSAC, 50.0, maxIters=5000)
    inl = inl.ravel().astype(bool)
    ty = vu.photo_to_surface(cams["04"], R, b[inl].astype(float), yr)
    O = np.c_[ty[:, 0] - np.radians(TURNS["04"]), ty[:, 1], a[inl]]
    O = O[(O[:, 1] > yr[0] + 5) & (O[:, 1] < yr[1] - 5)]

    def res(x):
        c = dict(D=x[0], H=x[1], b=x[2], p=x[3], g=x[4], f=FOCAL_MM["03"] / PITCH, cx=1824, cy=2736)
        return (vu.project(c, vu.surface(R, O[:, 1], O[:, 0] + x[5])) - O[:, 2:]).ravel()

    best = min((least_squares(res, [2100, 400, -0.06, 0.1, 0.06, t], loss="soft_l1", f_scale=5, x_scale="jac",
                              max_nfev=2000) for t in (0.2, 0.35, 0.5)), key=lambda r: r.cost)
    for _ in range(2):
        e = np.hypot(*res(best.x).reshape(-1, 2).T)
        O = O[e < 30]
        best = least_squares(res, best.x, loss="soft_l1", f_scale=5, x_scale="jac", max_nfev=2000)
    e = np.hypot(*res(best.x).reshape(-1, 2).T)
    print(f"{len(O)} points, median {np.median(e):.1f} px, 90% {np.percentile(e, 90):.1f}")
    print('    "03": dict(' + ", ".join(f"{k}={v:.6g}" for k, v in zip("DHbpg", best.x[:5])) + "),",
          "turn", round(float(np.degrees(best.x[5])), 4))


# ---------------------------------------------------------------- the old man

# The old man (widened px, WIDE): a phlyax with white hair and beard, stepping out of the door and holding
# the spear out to the warrior. Photo 03, laid onto the widened flat. The same steps as the warrior's.
OX0, OY0, OX1, OY1 = 700, 200, 4000, 5520     # his crop
OLD_SEEDS = [(1680, 3150), (2266, 4366), (3400, 2856), (2793, 3407)]   # his tunic; his legs and feet (the hem parts them); the spear below his fist; a finger
# His hair and beard are white, which red less blue reads with the glaze: inside HAIR (boxes) anything
# lighter than HAIR_L (grey) is him too (the ground round his head is black, without sheen)
HAIR, HAIR_L = [(1000, 1050, 2150, 1950)], 150
# His white hair and beard get a half tone, as Philoctetes' hair and beard (John, 2026-10-08, asked how:
# "Grey wash, as Philoctetes"): the white paint inside HAIR (below), on him, off his lines,
# lightly smoothed (TONE_SMOOTH px), drawn as a third path in the line colour at TONE opacity, under the lines
TONE, TONE_SMOOTH = 0.3, 3.0
# Where the white lies is read on photo 02, laid onto the same flat: in 03 it is soft and worn, and its pale
# clay at the jaw passes for white. White: lighter than TONE_L and red less blue under TONE_RB (both lightly
# blurred), closed over its worn gaps (TONE_CLOSE px) and filled, kept in pieces of TONE_MIN px^2 or more
# (the hair, the beard round his mouth; not specks on his neck)
TONE_L, TONE_RB, TONE_CLOSE, TONE_MIN = 185, 55, 6, 3000
# the spear's square top end stops 15 px under a thin strip of the border band: the glaze between found at
# FINE_OPEN. (Not at his hands: their fingers are parted by painted lines, which the fine opening took for
# ground, and the black contour where the spear enters his fist with them.)
OLD_FINE = [(1550, 290, 1800, 345)]
# above OLD_TOP (widened y) is the border band, left out
OLD_TOP = 300
# The door's pillar (left out): his back foot is raised on its toes, and its heel overlaps the pillar,
# outlined on it by a black heel line, which turns into the line of the sole. Photo 03 is out of focus
# there; photo 02 (fitted as 03 is; it is sharp there) shows the lines, which sit 5-10 px from 03's on the
# flat, so the cut is placed on 03's own pixels: along the outer edge of the heel line and the sole, 4 px
# off their centres, from the end of the ground between the pillar and his leg to the ground under his
# arch, then down the pillar's own edge (where red less blue falls under 60, row by row) to the stage. Everything on the pillar's side of it is out.
PILLAR = [(1150, 4975), (1123, 4977), (1087, 4999), (1052, 5019), (1027, 5042), (1008, 5068), (996, 5100),
          (991, 5128), (997, 5140), (1061, 5161), (1124, 5176), (1174, 5191), (1169, 5210), (1161, 5225),
          (1158, 5240), (1160, 5255), (1161, 5270), (1163, 5285), (1169, 5300), (1172, 5315), (1177, 5330), (1180, 5345),
          (1186, 5360), (1202, 5375), (1208, 5390), (1208, 5700), (0, 5700), (0, 0), (900, 0), (1050, 4700)]
# the ground under his raised arch, closed in by the sole, the pillar and the stage, is ground (a point in it)
OLD_GROUND = [(1200, 5300)]
# The stage under him, cut along the top of its plank (the thin line his toes stand on stays, as their
# sole): a quadratic through the plank's top edge, measured on 03 where it is sharp and on 02 (moved by
# 02's offset, +9 px) under his back toes, widened px
OLD_STAGE = [(1250, 5382), (1300, 5378), (1350, 5369), (1400, 5362), (1600, 5322), (1800, 5296), (1850, 5290),
             (1900, 5288), (1950, 5283), (2000, 5276), (2450, 5214), (2500, 5210), (2600, 5201), (2650, 5198),
             (2700, 5194), (2750, 5183), (2800, 5175), (2850, 5169), (2900, 5162), (2950, 5159), (3000, 5154),
             (3050, 5149), (3100, 5146)]
OLD_MEND = None                                # (widened y) the mended break, if it crosses him
# The black band along his tunic's hem runs out into the ground's black at both ends, and the drawing took
# it for ground: walled across its ends along the line of the tunic's edge (widened px), WALL_W wide
OLD_WALLS = [[(1157, 3812), (1168, 3888)], [(2387, 3472), (2402, 3528)],
             # the ground seen between his legs: the lower knee stroke's black head meets it, and the drawing
             # took the head for ground, outlined (John, 2026-10-08: "need to fix this area"). Walled along
             # the ground's right edge (grey's half-way crossing, row by row; between y 4165 and 4185 the
             # stroke hides it, interpolated), 4 px to the clay's side, so the head is paint
             [(2162, 4108), (2166, 4120), (2169, 4130), (2171, 4140), (2167, 4150), (2164, 4160), (2161, 4170),
              (2158, 4180), (2156, 4190), (2155, 4200), (2154, 4210)]]
# The spear's shaft, from under its top end to his fist, is straight: its edges (where red less blue
# falls to 60, row by row, every 60 px) fitted by straight lines, x = a y + b (widened px). Between them is
# the shaft; the shaft's photo edges wobble by the blur of 03, and a faint brown streak runs beside it near
# his hand (left out)
SPEAR_Y, SPEAR_LEFT, SPEAR_RIGHT = (340, 2030), (0.666683, 1440.83), (0.668623, 1547.50)
# Breaks where a fold thins to a faint run, each checked over the photo (line ends and the run's darkest
# point, row by row, between them; widened px): two folds on his chest, the crease across his shin, and a
# knee stroke
OLD_JOINS = [((1572, 2435), (1567, 2446), (1561, 2462), (1564, 2464)),
             ((1982, 2343), (1976, 2354), (1971, 2366), (1967, 2377)),
             ((1545, 4521), (1585, 4517), (1624, 4524)),
             # the upper knee stroke, flaked at its head: on to the edge of the ground between his legs
             ((2168, 4127), (2200, 4125), (2234, 4121))]
# the specks of glaze left at the flaked head of that knee stroke, under its line (they drew a hook): erased
# (box, widened px), and the stroke drawn through (OLD_JOINS)
OLD_ERASE = [(2168, 4129, 2205, 4152)]
# The two figures together are wider than the warrior alone, so weight "own" (a share of the longer
# side) thinned every line, and the warrior's belt broke. The weight is pinned so his lines keep the
# width John approved: WEIGHT on the warrior's longer side alone (4232 px), on the pair's (5443 px)
PAIR_WEIGHT = WEIGHT * 4232 / 5443
# Traced at 0.4 of the flat's px, the pair's ink loses any neck thinner than about 2 trace px: a fold's
# thin middle, a flaked run of the belt (eight breaks with ink across them). Every line is thickened to at
# least NECK flat px along its centre line first
NECK = 7


def old_man(src, src02):
    """The old man: (ink, figure, grey, half tone), in his crop of the widened flat (OX0, OY0, OX1, OY1)."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(flat_region(src, "03", (OX0, OY0, OX1, OY1))).save(t / "c.png")
        Image.fromarray(flat_region(src02, "02", (OX0, OY0, OX1, OY1))).save(t / "c02.png")
        pc(t / "c02.png", t / "rb02.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}), ("image.adjustments.threshold", {"level": TONE_RB}))
        pc(t / "c02.png", t / "l02.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 2}),
           ("image.adjustments.threshold", {"level": TONE_L}))
        white02 = (grey(t / "l02.png") >= 128) & (grey(t / "rb02.png") < 128)
        pc(t / "c.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}), ("image.adjustments.threshold", {"level": CLAY}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "light.png", ("filter.blur.gaussianBlur", {"radius": 2}),
           ("image.adjustments.threshold", {"level": HAIR_L}))
        pc(t / "g.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 1.0}),
           ("image.adjustments.levels", {"inWhite": FAINT_CAP}))
        pc(t / "gf.png", t / "cf.png", ("filter.other.maximum", {"radius": FAINT_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": FAINT_R, "preserve": "squareness"}))
        g = grey(t / "g.png")
        faint_c = grey(t / "cf.png") - grey(t / "gf.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        light = grey(t / "light.png") >= 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx + OX0 >= b[0]) & (yy + OY0 >= b[1]) & (xx + OX0 < b[2]) & (yy + OY0 < b[3]) for b in bs], 0)
    white = light & ~clay & box(HAIR)   # the white paint: light, but not red (clay is)
    clay |= white
    S = np.array(OLD_STAGE, float)
    outside = yy + OY0 > np.polyval(np.polyfit(S[:, 0], S[:, 1], 2), xx + OX0)
    outside |= lw.polygon_mask(g.shape, np.array(PILLAR, float) - (OX0, OY0))
    outside |= yy + OY0 < OLD_TOP
    dark = ~clay & ~outside
    for pts in OLD_WALLS:
        dark &= ~along(g.shape, pts, WALL_W, origin=(OX0, OY0))
    fine = box(OLD_FINE)
    ground0 = np.where(fine, ndi.binary_opening(dark, structure=morphology.disk(FINE_OPEN)),
                       ndi.binary_opening(dark, structure=morphology.disk(OPEN)))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND) & np.isin(np.arange(len(size)), rim)
    for x, y in OLD_GROUND:
        assert lab[y - OY0, x - OX0], f"ground point {(x, y)} is not on glaze"
        is_ground[lab[y - OY0, x - OX0]] = True
    ground = is_ground[lab]
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[y - OY0, x - OX0] for x, y in OLD_SEEDS}
    assert 0 not in keep
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: clay left out)
        if k not in keep and sz[k] > 2000:
            py, px = np.argwhere(lab[sl] == k)[np.sum(lab[sl] == k) // 2]
            print("unseeded clay", sz[k], OX0 + sl[1].start, OY0 + sl[0].start, OX0 + sl[1].stop, OY0 + sl[0].stop,
                  "e.g.", (OX0 + sl[1].start + px, OY0 + sl[0].start + py))
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground
    f = fig.astype(np.float32)
    fig = np.where(fine, ndi.gaussian_filter(f, FINE_SMOOTH), ndi.gaussian_filter(f, SMOOTH)) > 0.5
    Y, X = yy + OY0, xx + OX0
    left, right = SPEAR_LEFT[0] * Y + SPEAR_LEFT[1], SPEAR_RIGHT[0] * Y + SPEAR_RIGHT[1]
    zone = (Y >= SPEAR_Y[0]) & (Y < SPEAR_Y[1]) & (X > left - 40) & (X < right + 40)
    fig = np.where(zone, (X >= left) & (X <= right), fig)
    lab, _ = ndi.label(fig)   # (the streak's end, cut off from him by the shaft's edge, goes)
    fig = np.isin(lab, [lab[y - OY0, x - OX0] for x, y in OLD_SEEDS])
    # paint is dark in grey too: worn patches where the clay's surface has gone (pale, as on his forearm)
    # read as glaze by red less blue
    paint = dark & fig & core
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE)
    lines = (core | paint) & fig & ~edge & ~zone   # (the shaft carries no painted lines)
    lab, _ = ndi.label(lines, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    touch = np.unique(lab[ndi.binary_dilation(edge, iterations=2)])
    lines &= ~((sz < SPECK) & ~np.isin(np.arange(len(sz)), touch))[lab]
    mend = np.zeros(g.shape, bool) if OLD_MEND is None else (yy + OY0 > OLD_MEND[0]) & (yy + OY0 < OLD_MEND[1])
    lines |= faint_lines(faint_c, (to_edge > FAINT_EDGE) & ~mend, lines) & fig
    lines |= join_breaks(lines & (to_edge > EDGE + 2), to_edge > EDGE + 2)
    for bx0, by0, bx1, by1 in OLD_ERASE:
        lines[by0 - OY0:by1 - OY0, bx0 - OX0:bx1 - OX0] = False
    for pts in OLD_JOINS:
        lines |= along(g.shape, pts, LINE_MIN, origin=(OX0, OY0)) & fig
    ink = lines | edge
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    w2 = ndi.binary_fill_holes(ndi.binary_closing(white02 & box(HAIR), structure=morphology.disk(TONE_CLOSE)))
    lab, _ = ndi.label(w2)
    w2 &= (np.bincount(lab.ravel()) >= TONE_MIN)[lab]
    tone = ndi.gaussian_filter((w2 & fig).astype(np.float32), TONE_SMOOTH) > 0.5
    tone &= fig & ~ink
    return ink, fig, g, tone


def add_tone(svg, tone, box):
    """The half tone added to a drawing written by lw.trace_svg (box: the crop box it returned) as a third
    path, class "tone", in the line colour at TONE opacity, between the body and the lines (as
    philoctetes.py)."""
    x0, y0, x1, y1 = box
    d, _ = lw.potrace_d(lw.resample_ink(tone[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
    s = svg.read_text().replace('<path class="lines"', f'<path class="tone" fill="currentColor" fill-opacity="{TONE}" '
                                f'stroke="none" d="{d}"/><path class="lines"', 1)
    svg.write_text(s)


# ---------------------------------------------------------------- the two together

def main(src07, src03, src02, qa=None, dump=None):
    w_ink, w_fig, w_g = warrior(src07)
    o_ink, o_fig, o_g, o_tone = old_man(src03, src02)
    # one canvas over both crops, widened px
    wx0, wy0 = X0 + WIDE[0], Y0 + WIDE[1]
    cx0, cy0 = min(OX0, wx0), min(OY0, wy0)
    cx1, cy1 = max(OX1, X1 + WIDE[0]), max(OY1, Y1 + WIDE[1])
    shape = (cy1 - cy0, cx1 - cx0)
    ink, fig, g = np.zeros(shape, bool), np.zeros(shape, bool), np.full(shape, 255.0, np.float32)
    tone = np.zeros(shape, bool)
    tone[OY0 - cy0:OY0 - cy0 + o_tone.shape[0], OX0 - cx0:OX0 - cx0 + o_tone.shape[1]] = o_tone
    for a_ink, a_fig, a_g, (ax, ay) in ((o_ink, o_fig, o_g, (OX0, OY0)), (w_ink, w_fig, w_g, (wx0, wy0))):
        sl = (slice(ay - cy0, ay - cy0 + a_ink.shape[0]), slice(ax - cx0, ax - cx0 + a_ink.shape[1]))
        ink[sl] |= a_ink
        fig[sl] |= a_fig
        g[sl] = a_g
    ink |= (ndi.distance_transform_edt(~morphology.skeletonize(ink)) <= NECK / 2) & fig
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ink=ink, origin=np.array([cx0, cy0]))
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight=PAIR_WEIGHT,
                        title='A seated warrior raising his hand as an old man holds out his spear: a comic "departure of the warrior"',
                        desc="Line drawing after the Apulian red-figure bell-krater Würzburg H 4689; traced from "
                             "photographs by ArchaiOptix (CC BY-SA 4.0), taken off the vase's curve, changed.")
    add_tone(OUT, tone & ~ink, info["box"])
    print(OUT, info, "canvas origin (widened px)", (cx0, cy0))
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--refit" in sys.argv:
        fit_model(dict(zip(["07", "04", "05", "06"], sys.argv[1:5])))
    elif "--refit03" in sys.argv:
        fit_03(*sys.argv[1:3])
    else:
        main(*sys.argv[1:6])
