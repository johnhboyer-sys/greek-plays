"""Medea: the whole picture on side A of the Lucanian red-figure calyx-krater near the Policoro Painter,
c. 400 BCE, Cleveland Museum of Art 1991.1 (Leonard C. Hanna Jr. Fund; CC0), handle to handle (John,
2026-10-09: "For medea, render the whole plate"): Medea in the serpent chariot in the sun disk with its
rays; at the left a Fury above Jason, a plant and a spotted cat; under the disk an amphora and a plant;
at the right the dead children on the altar, the nurse, the tutor and a Fury above them. The ornament
bands above and below the picture are left out.

Redrawn with PhotoCraft (John, 2026-10-09); the first tool of this name (the phase 1 test, 2026-10-02,
Medea and the serpents only, from alt3 alone) is in git history.

Photos (Cleveland Open Access, CC0; Gary Kirchenbauer, Sinar p3 / f3):
  main  1991.1_full.tif, the whole vase, side A (4992 x 5363): the frame
  a4    1991.1_alt4_full.tif, the left: Fury and Jason (4839 x 6564)
  a3    1991.1_alt3_full.tif, the middle: Medea in the disk (4992 x 6165)
  a5    1991.1_alt5_full.tif, the right: Fury, nurse, tutor, altar (4992 x 6668)
  https://openaccess-cdn.clevelandart.org/1991.1/<file>

Photos -> flat (vase_unroll.py; geometry, so numpy and scipy, not PhotoCraft):
  - The TIFFs carry no focal length (a view camera, the frames cropped), so the focal lengths are fitted.
    The profile and the four cameras were fitted together (MODEL, --refit): to the vase's outline in
    main (rows 1360-2380, above the handles, where the dark grey background meets the black glaze), the
    upper border of the wave band under the picture (a painted circle, y = 0) in main, a4 and a5, and
    points matched between main and each close-up (SIFT). Median misfit: main's outline 7.8 px, the band
    2.0 px; the matches 4.4 (a4), 1.9 (a3) and 3.4 px (a5), in close-up px (about 3 to the main's 1).
  - The vase is flattened without shear (vase_unroll.flatten) about main's axis and each photo laid onto
    it through its own camera, at G px per world unit (world units: about main's px at the vase).
  - The close-ups are joined along seams through the black ground (least clay, in columns where both
    photos agree within 2 px: SEAM_L, SEAM_R): a4 left of the left seam, a3 between, a5 right of the
    right one; anything no close-up covers comes from main.

Flat -> drawing: every image step runs in PhotoCraft (`photocraft-cli` 0.2.0): the crop, the grey, the
clay map (Channel Mixer, red less blue), the blurs, the Maximum and Minimum filters and the thresholds.
numpy only combines PhotoCraft's masks and measures. The SVG is written by linework.trace_svg.

    python3 docs/redesign/drawings/tools/medea.py 1991.1_full.tif 1991.1_alt4_full.tif 1991.1_alt3_full.tif 1991.1_alt5_full.tif [qa.png]
    python3 docs/redesign/drawings/tools/medea.py <the four> --refit
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
from scipy.interpolate import CubicSpline, LinearNDInterpolator
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "medea.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None
NAMES = ("main", "a4", "a3", "a5")
SIDES = ("a1", "a2")   # the handle views, left and right

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (--refit prints these). World units: about main's px at
# the vase (main's D fixes them); y = 0 on the wave band's upper border, up the vase; theta = 0 faces main.
CAMERAS = {
    "main": dict(D=20000, H=2548.59, b=0.106855, p=-0.00028542, g=0.00751787, f=21263.5, cx=2496, cy=2681.5),
    "a4": dict(D=4128.51, H=701.928, b=-0.0482712, p=-0.0574665, g=0.000153322, f=10477.8, cx=2419.5, cy=3282),
    "a3": dict(D=6699.25, H=1016.08, b=-0.0186005, p=-0.0149755, g=-0.000524339, f=17304.3, cx=2496, cy=3082.5),
    "a5": dict(D=5100.15, H=668.963, b=-0.0334542, p=-0.000328622, g=0.00335336, f=14456.1, cx=2496, cy=3334),
    # the handle views, fitted to the model above with the profile and the other cameras held (fit_side,
    # --refit-sides): points matched with a4 (a1; 398, median 3.3 px) and a5 (a2; 164, median 1.4 px)
    "a1": dict(D=55837.3, H=5823.71, b=0.0984772, p=0.0013473, g=-0.00292521, f=61912.4, cx=2324.5, cy=2464.0),
    "a2": dict(D=19234.7, H=2861.93, b=0.130118, p=-0.000896603, g=-0.0094367, f=20508.1, cx=2413.5, cy=2587.5),
}
PROFILE_Y = [-200, 100, 400, 700, 1000, 1300, 1600, 1900, 2200]
PROFILE_R = [1115.2, 1118.1, 1146.4, 1165.4, 1193.7, 1229.0, 1283.4, 1338.3, 1393.2]
TURNS = {"main": 0.0, "a4": 47.312, "a3": -2.396, "a5": -42.431, "a1": 92.4433, "a2": -91.4157}   # degrees each photo is turned from main
# The data for fit_model: rough guides (photo px) to the wave band's upper border; main's outline rows; the
# scales the photos are matched at
FIT_BAND = {"main": [(1450, 3195), (2000, 3215), (2500, 3225), (3000, 3220), (3500, 3200)],
            "a4": [(2200, 6235), (3000, 6230), (3800, 6225), (4700, 6210)],
            "a5": [(50, 6175), (1000, 6200), (2000, 6215), (3000, 6215), (4000, 6200), (4800, 6170)]}
FIT_ROWS, FIT_START = (1360, 2380), (1000, 4050)
MATCH_MAIN, MATCH_CLOSE = 0.5, 0.16


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def rgb(p):
    return np.asarray(Image.open(p).convert("RGB"))


def outline(a, v0, v1, step=8, start=FIT_START):
    """(side, u, v): the vase's outline row by row, where the dark grey background, read inward from
    `start`, first falls 12 grey levels for 6 px, at the half-way crossing."""
    L = ndi.gaussian_filter(a.mean(2).astype(np.float32), 2.0)
    out = []
    for v in range(v0, v1, step):
        for side, x0, s in ((0, start[0], 1), (1, start[1], -1)):
            row = L[v]
            bg = np.median(row[x0 - 40:x0] if s == 1 else row[x0:x0 + 40])
            x = x0
            while 0 < x < row.size - 1 and not (row[x:x + 6 * s:s] < bg - 12).all():
                x += s
            mid = (bg + np.median(row[x + 6 * s:x + 20 * s:s])) / 2
            xs = np.arange(x - 8, x + 9)
            k = np.nonzero(np.diff(np.sign(row[xs] - mid)))[0]
            if len(k):
                k = k[np.argmin(abs(k - 8))]
                out.append((side, xs[k] + (mid - row[xs[k]]) / (row[xs[k] + 1] - row[xs[k]]), v))
    return np.array(out)


def fit_model(paths: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit). Needs opencv for SIFT."""
    import cv2
    img = {n: rgb(paths[n]) for n in NAMES}
    sil = outline(img["main"], *FIT_ROWS)
    band = {n: vu.band_line(img[n].astype(np.float32), r, half=60, clay_rb=90, widths=(4, 14) if n == "main" else (12, 45))
            for n, r in FIT_BAND.items()}
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(a, k):
        g = cv2.resize(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        kp, d = sift.detectAndCompute(g, None)
        return np.array([p.pt for p in kp]) / k, d

    km, dm = feats(img["main"], MATCH_MAIN)
    matches = {}
    for n in NAMES[1:]:
        kn, dn = feats(img[n], MATCH_CLOSE)
        good = [x for x, y in cv2.BFMatcher(cv2.NORM_L2).knnMatch(dm, dn, k=2) if x.distance < 0.8 * y.distance]
        a, b = np.float32([km[x.queryIdx] for x in good]), np.float32([kn[x.trainIdx] for x in good])
        _, inl = cv2.findHomography(a, b, cv2.RANSAC, 60.0, maxIters=5000)
        inl = inl.ravel().astype(bool)
        matches[n] = np.hstack([a[inl], b[inl]])
    views = {"main": dict(size=img["main"].shape[1::-1], sil=[tuple(r) for r in sil], band=band["main"])}
    for n in NAMES[1:]:
        views[n] = dict(size=img[n].shape[1::-1], sil=[], band=band.get(n, np.zeros((0, 2))))
    knots = np.array(PROFILE_Y, float)
    half = {}
    for side, u, v in sil:
        half.setdefault(round(v), []).append(u)
    rows = [v for v, us in half.items() if len(us) == 2]
    x0 = []
    for n in NAMES:
        x0 += [20000.0, 1500.0, np.radians(4.0), 0.0, 0.0, 20000.0 if n == "main" else 60000.0, 0.0, 0.0]
    for y in knots:   # the profile's start: the outline's half-width at about that height
        v = min(rows, key=lambda r: abs(r - (3220 - y)))
        x0.append(abs(half[v][1] - half[v][0]) / 2)
    x0 += [0.0, 0.0] + [np.radians(-35), 0.0, np.radians(35)]
    cams, R, _, turns, report, _ = vu.fit(views, knots, matches=matches, d0=20000.0, x_start=np.array(x0),
                                          nfev=800, outlier=40, rounds=3)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


def fit_side(p_side, p_ref, ref, name) -> None:
    """Fit a handle view's camera (its focal length and turn too) to the model, everything else held, and
    print it: points matched between it and the close-up `ref`, taken onto the vase through ref's camera.
    Needs opencv for SIFT."""
    import cv2
    from scipy.optimize import least_squares
    cams, R = vase()
    yr = (FLAT_Y[0], FLAT_Y[1])
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(a, k):
        g = cv2.resize(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        kp, d = sift.detectAndCompute(g, None)
        return np.array([p.pt for p in kp]) / k, d

    A, B = rgb(p_side), rgb(p_ref)
    ka, da = feats(A, 0.25)
    kb, db = feats(B, 0.16)
    good = [x for x, y in cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2) if x.distance < 0.8 * y.distance]
    a, b = np.float32([ka[x.queryIdx] for x in good]), np.float32([kb[x.trainIdx] for x in good])
    _, inl = cv2.findHomography(a, b, cv2.RANSAC, 60.0, maxIters=5000)
    inl = inl.ravel().astype(bool)
    ty = vu.photo_to_surface(cams[ref], R, b[inl].astype(float), yr)
    O = np.c_[ty[:, 0] - np.radians(TURNS[ref]), ty[:, 1], a[inl]]
    O = O[(O[:, 1] > yr[0] + 5) & (O[:, 1] < yr[1] - 5) & np.isfinite(O).all(1)]
    W, H = A.shape[1], A.shape[0]
    t0 = np.radians(TURNS[ref]) * 1.9

    def res(x):
        c = dict(D=x[0], H=x[1], b=x[2], p=x[3], g=x[4], f=x[5], cx=W / 2, cy=H / 2)
        return (vu.project(c, vu.surface(R, O[:, 1], O[:, 0] + x[6])) - O[:, 2:]).ravel()

    best = min((least_squares(res, [d, 1000, 0.05, 0, 0, f, t0], loss="soft_l1", f_scale=5, x_scale="jac", max_nfev=4000)
                for d in (8000, 20000) for f in (15000, 40000)), key=lambda r: r.cost)
    for _ in range(2):
        e = np.hypot(*res(best.x).reshape(-1, 2).T)
        O = O[e < 30]
        best = least_squares(res, best.x, loss="soft_l1", f_scale=5, x_scale="jac", max_nfev=4000)
    e = np.hypot(*res(best.x).reshape(-1, 2).T)
    print(f"{name}: {len(O)} points, median {np.median(e):.1f} px, 90% {np.percentile(e, 90):.1f}")
    print(f'    "{name}": dict(' + ", ".join(f"{k}={v:.6g}" for k, v in zip("DHbpgf", best.x[:6])) + f", cx={W / 2}, cy={H / 2}),",
          "turn", round(float(np.degrees(best.x[6])), 4))


# ---------------------------------------------------------------- the flat

# The vase flattened over FLAT_THETA x FLAT_Y (start, stop, step) about main's axis; the flat image covers
# BOX (world x0, y0, x1, y1 on the flat: the picture between the handles, from the wave band's border to
# the ledge under the palmettes) at G px per world unit.
FLAT_THETA, FLAT_Y = (-1.5, 1.5001, 0.006), (-100.0, 2100.1, 6.0)
BOX, G = (-2350.0, -15.0, 2100.0, 1700.0), 2.0
# Seams: each a band of flat columns (world x) the least-clay path between two close-ups runs in, where
# they agree within 2 px (a4 against a3 from x -880; a3 against a5 everywhere they overlap)
SEAM_L, SEAM_R = (-880.0, -650.0), (180.0, 680.0)
# a photo is used only where the vase's surface faces it at less than acos(FACING) (60 degrees): beyond,
# the main photo's view of the vase's sides is a smear
FACING = 0.5


def frame():
    """The flat's grid: (step, grid shape, (theta, y) on the vase at each grid point, W, H)."""
    _, R = vase()
    th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    XY = vu.flatten(R, th, yy, centre=0.0)
    TH, Y = np.meshgrid(th, yy)
    inv = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))
    x0, y0, x1, y1 = BOX
    W, H, step = int((x1 - x0) * G), int((y1 - y0) * G), 4
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    return step, gx.shape, inv(np.stack([x0 + gx.ravel() / G, y1 - gy.ravel() / G], -1)), W, H


def vase_y():
    """The height up the vase (world y) of each flat px (H x W)."""
    step, shape, tq, W, H = frame()
    return ndi.zoom(np.nan_to_num(tq[:, 1].reshape(shape), nan=-1e4), step, order=1)[:H, :W]


def flat_images(paths):
    """Each photo laid onto the flat (dict of H x W x 3 float32, 0 where the photo does not reach)."""
    cams, R = vase()
    step, shape, tq, W, H = frame()
    gx = np.zeros(shape)
    out = {}
    for n in NAMES + SIDES:
        t = tq[:, 0] + np.radians(TURNS[n])
        uv = vu.project(cams[n], vu.surface(R, tq[:, 1], t)).reshape(shape + (2,))
        # only where the vase faces the camera squarely enough (FACING), inside the photo's frame (6 px in)
        a = rgb(paths[n]).astype(np.float32)
        ok = ((np.cos(t) > FACING).reshape(shape) & (uv[..., 0] > 6) & (uv[..., 1] > 6)
              & (uv[..., 0] < a.shape[1] - 7) & (uv[..., 1] < a.shape[0] - 7))
        ok = ndi.zoom(ok.astype(np.float32), step, order=0)[:H, :W] > 0.5
        u = ndi.zoom(np.nan_to_num(uv[..., 0], nan=-1e5), step, order=1)[:H, :W]
        v = ndi.zoom(np.nan_to_num(uv[..., 1], nan=-1e5), step, order=1)[:H, :W]
        im = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1).clip(0, 255)
        im[~ok] = 0
        out[n] = im
    return out


def seam(A, B, cols, move=3):
    """A top-to-bottom path of least clay (the larger of red less blue and a third of the grey, in either
    photo, lightly smoothed) through flat columns `cols` (world x), where both photos reach. Returns its
    column (flat px) per row."""
    c0, c1 = (int((x - BOX[0]) * G) for x in cols)

    def clay(a):
        a = a[:, c0:c1]
        return ndi.gaussian_filter(np.clip(a[..., 0] - a[..., 2], 0, None) + 0.3 * a.mean(2), 2)

    c = np.maximum(clay(A), clay(B))
    c[(A[:, c0:c1].max(2) < 1) | (B[:, c0:c1].max(2) < 1)] = 1e4
    acc, back = c.copy(), np.zeros(c.shape, int)
    for y in range(1, len(c)):
        best, arg = np.full(c.shape[1], np.inf), np.zeros(c.shape[1], int)
        for d in range(-move, move + 1):
            sh = np.roll(acc[y - 1], d)
            if d > 0:
                sh[:d] = np.inf
            elif d < 0:
                sh[d:] = np.inf
            better = sh < best
            best[better], arg[better] = sh[better], d
        acc[y], back[y] = c[y] + best, arg
    x = np.zeros(len(c), int)
    x[-1] = int(np.argmin(acc[-1]))
    for y in range(len(c) - 1, 0, -1):
        x[y - 1] = x[y] - back[y, x[y]]
    return x + c0


def joined(paths):
    """The close-ups joined on the flat (H x W x 3 uint8), main where none reaches."""
    f = flat_images(paths)
    xl, xr = seam(f["a4"], f["a3"], SEAM_L), seam(f["a3"], f["a5"], SEAM_R)
    xx = np.arange(f["main"].shape[1])[None, :]
    out = np.where((xx < xl[:, None])[..., None], f["a4"], np.where((xx < xr[:, None])[..., None], f["a3"], f["a5"]))
    # where the close-up does not reach: the handle view on that side (the Furies' outer wings), then main
    for side, cond in (("a1", xx < xl[:, None]), ("a2", xx >= xr[:, None])):
        gap = (out.max(2) < 1) & cond
        out[gap] = f[side][gap]
    gap = out.max(2) < 1
    out[gap] = f["main"][gap]
    return out.round().astype(np.uint8)


# ---------------------------------------------------------------- the drawing

# The picture lies between the wave band's upper border (y = 0; the band's clay line reaches Y_BOT) and the
# lower edge of the clay ledge under the palmettes (Y_TOP), both circles on the vase (world y)
Y_BOT, Y_TOP = 6.0, 1720.0   # (the ledge itself is brown glaze, ground by colour; the photos put its edge at y 1620-1700)
# and pieces of clay lying wholly above Y_ORN (bits of the palmette band over the ledge, which Y_TOP lets in
# where the ledge sits low) are not figures; the rays' tips that reach the ledge belong to their rays
Y_ORN = 1640.0
# Clay: red less blue (lightly blurred) above CLAY (the glaze reads near 0, the clay about 90, the added
# yellow 100-160); the added white (the nurse's hair, the serpents' bellies) is grey, not red: anything
# lighter than WHITE_L (grey) is clay too
CLAY, WHITE_L = 40, 140
# Ground: the dark with its painted lines (up to 2 * OPEN flat px wide) opened away, in areas over
# AUTO_GROUND flat px^2 (the black ground round the figures and inside the disk), and the ground seen
# through the figures (between the wheels' spokes, inside the serpents' coils, between legs and wings):
# enclosed dark areas over POCKET flat px^2, unless they are paint (PAINT_SEEDS: hair)
OPEN, AUTO_GROUND, POCKET = 5, 40000, 1500
PAINT_SEEDS = []
EDGE_R = 6                      # flat px: the figure's edge where the clay map falls to half the clay's level nearby
FIG_SIGMA = 3.0                 # flat px: the figure's area smoothed along its length
EDGE = 4.0                      # flat px: the outline, drawn inside the figure's edge
# Lines (as antigone.py): local contrast in the grey (the blurred map's Maximum then Minimum over
# CLOSE_W flat px, less the blurred map), hysteresis (LINE_LOW, LINE_HIGH), drawn along their centres at
# their own width (where the contrast is at least half the strongest within HALF_R px), smoothed along the
# line over WIDTH_SIGMA px, never thinner than LINE_MIN
LINE_LOW, LINE_HIGH, HALF_R, LINE_MIN = 25, 55, 3, 2.5
CLOSE_W = 11
LINE_LEN, SHORT_LEN, SHORT_C = 30, 80, 90
# Clean, crisp lines (John, 2026-10-10: "I don't want this rough. Nice and clean and crisp"): each line is
# redrawn as one stroke along its centre, the centre's path smoothed (Gaussian over STROKE_SIGMA flat px
# along the line, its ends kept), at one even width, STROKE_W flat px; the brush's ragged edges, the grain
# and the photo's texture do not come through
STROKE_SIGMA, STROKE_W = 4.0, 4.5
# Faces (flat px boxes): Medea, the Furies, Jason, the nurse, the tutor, the elder child. Their lines are
# finer and closer: drawn FACE_W wide, found at the lower FACE_LOW/FACE_HIGH, kept down to FACE_LEN px long
# with spurs under FACE_SPUR pruned, smoothed over FACE_SIGMA; dots there (pupils) at most FACE_DOT px^2,
# larger dark marks are lines
FACES = {"medea": (4850, 430, 5000, 600), "fury_l": (2300, 470, 2500, 660), "jason": (2560, 1640, 2760, 1860),
         "fury_r": (6600, 440, 6820, 650), "nurse": (6180, 1900, 6380, 2060), "tutor": (7240, 1680, 7420, 1830),
         "child": (5650, 2520, 5770, 2650)}
FACE_W, FACE_LOW, FACE_HIGH, FACE_LEN, FACE_SPUR, FACE_SIGMA, FACE_DOT = 3.0, 18, 40, 10, 3, 2.0, 140
# Hair and beards of thinned brown glaze (Jason, the tutor, the children): drawn as a wash in the line colour,
# as Philoctetes' and the Acharnians old man's (paths of class "tone" under the lines), not as lines, which
# made blots of the curls. Inside HAIR (flat px boxes) the wash is the figure where the grey, smoothed over
# WASH_SIGMA px, lies between WASH_G (black glaze under it, clay over it), wider than a line (opened over
# WASH_OPEN px); no lines are drawn in it. Its opacity follows the darkness in steps (WASH_STEPS: grey under,
# total opacity), each step over the one below (no seams)
HAIR = {"jason": (2400, 1540, 2820, 1900), "tutor": (7200, 1560, 7500, 1800), "child_r": (5560, 2520, 5800, 2740),
        "child_l": (4930, 2370, 5170, 2620)}
WASH_SIGMA, WASH_G, WASH_OPEN = 3.0, (47, 125), 4
WASH_STEPS, STEP_SIGMA = [(125, 0.3), (90, 0.5), (65, 0.7)], 6.0   # (the steps follow the grey smoothed over STEP_SIGMA px)
HOLE, MASK_SIGMA, SPUR, WIDTH_SIGMA = 12, 1.2, 8, 6.0
# Dots (the serpents' spots, the dots on the Furies' wings and dresses, the cat's spots): compact dark marks,
# DOT_AREA flat px^2, under DOT_RATIO times as long as wide, found by the same contrast at DOT_C or more;
# drawn as their own filled shapes (smoothed), not as centre lines (which made crumbs of them)
DOT_AREA, DOT_RATIO, DOT_C = (60, 900), 2.6, 30
# Each dot is drawn as the ellipse fitted to it (same area, centre and axes), so spots come out clean, not
# ragged. On the serpents' added yellow (YELLOW: grey over YELLOW_G and red less blue over YELLOW_RB, smoothed
# over 8 px) the paint's texture breaks into crumbs: there a line must be YELLOW_LEN px long and reach YELLOW_C
YELLOW_G, YELLOW_RB, YELLOW_LEN, YELLOW_C = 150, 50, 50, 55
DOT_BIG = 260
# solid paint (hair, the black borders and bands of the clothes): red less blue under PAINT, wider than
# 2 * PAINT_WIDE flat px
PAINT, PAINT_WIDE = 25, 4
# Breaks in a line (flaked glaze, a crack, a highlight) joined (John, 2026-10-09: "we want these ink strokes
# to be clean, not cracked or jagged"; as antigone.py)
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C, ALIGN_MAX, ALIGN_C = 18, 8, 20, 10, 36, 6
ALIGN_COS = np.cos(np.radians(10))
# lines are drawn at this weight (pinned once the first pass is approved)
WEIGHT = "drawn"   # (the strokes are drawn at their width already; resampling would soften them)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def smooth_mask(m, sigma, t):
    """m blurred over sigma px in PhotoCraft and cut at half."""
    Image.fromarray((m * 255).astype(np.uint8)).save(t / "m.png")
    pc(t / "m.png", t / "ms.png", ("filter.blur.gaussianBlur", {"radius": sigma}))
    return grey(t / "ms.png") >= 128


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as clouds.py)."""
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


def _walk(cl, x, y, n):
    """Up to n skeleton px from the end (x, y), stopping where the line branches; (x, y) points, the end first."""
    H, W = cl.shape
    path, seen = [(x, y)], {(x, y)}
    for _ in range(n - 1):
        nxt = [(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
               if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H and cl[y + dy, x + dx] and (x + dx, y + dy) not in seen]
        if len(nxt) != 1:
            if len(nxt) == 2 and abs(nxt[0][0] - nxt[1][0]) + abs(nxt[0][1] - nxt[1][1]) == 1:
                nxt = sorted(nxt, key=lambda q: abs(q[0] - x) + abs(q[1] - y))[:1]
            else:
                break
        x, y = nxt[0]
        seen.add((x, y))
        path.append((x, y))
    return np.array(path, float)


def join_breaks(c, contrast, inner):
    """Joins (1-px lines) for the breaks in centre lines c that JOIN_* describe (as antigone.py)."""
    from scipy.spatial import cKDTree
    from skimage.draw import line
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere(c & (ndi.convolve(c.astype(int), k, mode="constant") == 1))
    out = np.zeros_like(c)
    if len(ends) < 2:
        return out
    runs = [_walk(c, int(x), int(y), JOIN_RUN)[:, ::-1] for y, x in ends]
    lab = ndi.label(c, structure=np.ones((3, 3)))[0]
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    for i, j in sorted(cKDTree(ends).query_pairs(ALIGN_MAX), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]]))):
        if i in used or j in used or len(runs[i]) < JOIN_RUN / 2 or len(runs[j]) < JOIN_RUN / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        aligned = da @ u >= ALIGN_COS * np.hypot(*da) and db @ -u >= ALIGN_COS * np.hypot(*db)
        if not aligned and np.hypot(*(b - a)) > JOIN_MAX:
            continue
        q = a[None] + np.linspace(0.1, 0.9, max(int(np.hypot(*(b - a))), 3))[:, None] * (b - a)[None]
        qi = tuple(q.round().astype(int).T)
        if not inner[qi].all() or np.median(ndi.map_coordinates(contrast, q.T, order=1)) < (ALIGN_C if aligned else JOIN_C):
            continue
        if set(lab[qi]) - {0, lab[tuple(ends[i])], lab[tuple(ends[j])]}:
            continue
        rr, cc = line(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        out[rr, cc] = True
        used |= {i, j}
    return out


def strokes_from(c, width=None, sigma=None):
    """The centre lines c (a skeleton) redrawn clean: split into branches at their junctions, each
    branch's path smoothed (STROKE_SIGMA) and drawn STROKE_W wide (or `width`, `sigma`); the junctions kept."""
    width, sigma = width or STROKE_W, sigma or STROKE_SIGMA
    from skimage.draw import line
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    nb = ndi.convolve(c.astype(int), k, mode="constant")
    junc = ndi.binary_dilation(c & (nb >= 3), structure=np.ones((3, 3))) & c
    branches = c & ~junc
    lab, n = ndi.label(branches, structure=np.ones((3, 3)))
    centre = junc.copy()
    H, W = c.shape
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab[sl] == i
        pts = np.argwhere(m)
        if len(pts) < 3:
            centre[sl] |= m
            continue
        mk = ndi.convolve(m.astype(int), k, mode="constant")
        ends = np.argwhere(m & (mk == 1))
        start = tuple(ends[0]) if len(ends) else tuple(pts[0])
        path, seen = [start], {start}
        while True:   # walk the branch from one end to the other
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx)
                   and 0 <= y + dy < m.shape[0] and 0 <= x + dx < m.shape[1] and m[y + dy, x + dx] and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            nxt.sort(key=lambda q: abs(q[0] - y) + abs(q[1] - x))
            path.append(nxt[0])
            seen.add(nxt[0])
        P = np.array(path, float) + (sl[0].start, sl[1].start)
        if len(P) > 4:
            Q = np.stack([ndi.gaussian_filter1d(P[:, j], sigma, mode="nearest") for j in (0, 1)], -1)
            Q[0], Q[-1] = P[0], P[-1]
            P = Q
        for (ya, xa), (yb, xb) in zip(P[:-1], P[1:]):
            rr, cc = line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            centre[rr[ok], cc[ok]] = True
    return ndi.distance_transform_edt(~centre) <= width / 2


def drawing(flat, t):
    """The lines (ink) and figures' area (fig) on the flat, and its grey."""
    from skimage.filters import apply_hysteresis_threshold
    Image.fromarray(flat).save(t / "flat.png")
    pc(t / "flat.png", t / "g.png", ("image.mode.grayscale", None))
    pc(t / "g.png", t / "gp.png", ("filter.blur.gaussianBlur", {"radius": 1.0}))
    pc(t / "flat.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
       ("filter.blur.gaussianBlur", {"radius": 1.0}))
    g, gp, rb = grey(t / "g.png"), grey(t / "gp.png"), grey(t / "rb.png")
    vy = vase_y()
    outside = (vy < Y_BOT) | (vy > Y_TOP) | (flat.max(2) < 1)
    white = gp > WHITE_L
    # the clay map: red less blue, with the added white as clay
    cm = np.where(white, np.maximum(rb, 120), rb)
    Image.fromarray(cm.clip(0, 255).astype(np.uint8)).save(t / "cm.png")
    pc(t / "cm.png", t / "cmax.png", ("filter.other.maximum", {"radius": EDGE_R, "preserve": "roundness"}))
    cmmax = grey(t / "cmax.png")
    clay = cm > CLAY
    dark = ~clay & ~outside
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    ground = (size > AUTO_GROUND)[lab]
    # the figures: what the ground leaves; enclosed dark areas over POCKET are ground seen through them
    fig = ndi.binary_fill_holes(~ground & ~outside) & ~ground & ~outside
    holes = fig & ground0
    lab, _ = ndi.label(holes)
    size = np.bincount(lab.ravel())
    size[0] = 0
    pocket = size > POCKET
    for x, y in PAINT_SEEDS:
        pocket[lab[y, x]] = False
    hz = np.zeros(fig.shape, bool)   # (in the hair boxes the dark is hair, not ground seen through)
    for x0, y0, x1, y1 in HAIR.values():
        hz[y0:y1, x0:x1] = True
    inhair = ndi.mean(hz.astype(float), lab, np.arange(len(pocket))) > 0.5
    pocket &= ~inhair
    fig &= ~pocket[lab]
    fig &= ~((ndi.distance_transform_edt(fig) <= EDGE_R) & (cm < 0.5 * cmmax))
    fig = smooth_mask(fig, FIG_SIGMA, t) & ~outside
    fig = morphology.remove_small_objects(fig, max_size=200)
    lab, n = ndi.label(fig)
    low = ndi.minimum(vy, lab, np.arange(n + 1))
    fig &= ~(low > Y_ORN)[lab]
    # lines by local contrast in the grey (the spots on the serpents' added yellow are brown, as red as the
    # yellow, so red less blue loses them), everything off the figures turned white
    Image.fromarray(np.where(fig, g, 255).clip(0, 255).astype(np.uint8)).save(t / "cw.png")
    pc(t / "cw.png", t / "cl.png", ("filter.blur.gaussianBlur", {"radius": 0.8}))
    r = CLOSE_W // 2
    pc(t / "cl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
       ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
    contrast = (grey(t / "closed.png") - grey(t / "cl.png")).clip(0, None)
    Image.fromarray(contrast.clip(0, 255).astype(np.uint8)).save(t / "c.png")
    pc(t / "c.png", t / "cx.png", ("filter.other.maximum", {"radius": HALF_R, "preserve": "roundness"}))
    cmax = grey(t / "cx.png")
    to_edge = ndi.distance_transform_edt(fig)
    firm = apply_hysteresis_threshold(contrast, LINE_LOW, LINE_HIGH) & fig & (to_edge > EDGE)
    lab, n = ndi.label(firm, structure=np.ones((3, 3)))
    length = np.bincount(lab[morphology.skeletonize(firm)], minlength=n + 1)
    top = ndi.maximum(contrast, lab, np.arange(n + 1))
    firm &= ~((length < SHORT_LEN) & (top < SHORT_C))[lab]
    face = np.zeros(fig.shape, bool)
    for x0, y0, x1, y1 in FACES.values():
        face[y0:y1, x0:x1] = True
    firm = np.where(face, apply_hysteresis_threshold(contrast, FACE_LOW, FACE_HIGH) & fig & (to_edge > EDGE), firm)
    # the dots, taken out before the lines
    dm = (contrast >= DOT_C) & fig & (to_edge > EDGE)
    lab, n = ndi.label(dm)
    dots = np.zeros_like(dm)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float)
        if not DOT_AREA[0] <= len(p) <= (FACE_DOT if face[sl][lab[sl] == k].any() else DOT_AREA[1]):
            continue
        w = np.linalg.eigvalsh(np.cov(p.T)) if len(p) > 2 else np.array([1.0, 1.0])
        if np.sqrt(max(w[1], 1e-6) / max(w[0], 0.25)) < DOT_RATIO:
            dots[sl] |= lab[sl] == k
    from skimage.draw import ellipse
    lab, n = ndi.label(dots)
    dots = np.zeros_like(dots)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float) + (sl[0].start, sl[1].start)
        if len(p) > DOT_BIG:   # (larger marks, an eye, a pupil: their own shape, smoothed)
            dots[sl] |= ndi.gaussian_filter((lab[sl] == k).astype(float), 1.5) > 0.5
            continue
        cy, cx = p.mean(0)
        w, v = np.linalg.eigh(np.cov(p.T) + np.eye(2) * 0.25)
        a, b = 2 * np.sqrt(w[1]) + 0.5, 2 * np.sqrt(w[0]) + 0.5
        rr, cc = ellipse(cy, cx, a, b, shape=dots.shape, rotation=np.arctan2(v[1, 1], v[0, 1]))
        dots[rr, cc] = True
    dots &= fig
    firm &= ~ndi.binary_dilation(dots, iterations=2)
    yellow = ndi.gaussian_filter(((g > YELLOW_G) & (cm > YELLOW_RB)).astype(float), 8) > 0.5
    lab, n = ndi.label(firm, structure=np.ones((3, 3)))
    length = np.bincount(lab[morphology.skeletonize(firm)], minlength=n + 1)
    top = ndi.maximum(contrast, lab, np.arange(n + 1))
    iny = ndi.mean(yellow.astype(float), lab, np.arange(n + 1)) > 0.5
    firm &= ~(iny & ((length < YELLOW_LEN) | (top < YELLOW_C)))[lab]
    own = firm & (contrast >= 0.5 * cmax)
    m = morphology.remove_small_holes(firm | own, max_size=HOLE)
    m = smooth_mask(m, MASK_SIGMA, t)
    c = centre_lines(m & ~face, SPUR, LINE_LEN)
    c |= join_breaks(c, contrast, fig & (to_edge > EDGE))
    cf = centre_lines(m & face, FACE_SPUR, FACE_LEN)
    lines = (strokes_from(c) | strokes_from(cf, FACE_W, FACE_SIGMA)) & fig
    # the hair washes
    gs = ndi.gaussian_filter(g, WASH_SIGMA)
    wash = ndi.binary_opening((gs >= WASH_G[0]) & (gs < WASH_G[1]) & fig & hz, structure=morphology.disk(WASH_OPEN))
    wash = smooth_mask(wash, 2.0, t) & fig & hz
    lines &= ~wash
    paint = (cm < PAINT) & fig
    paint &= ndi.binary_dilation(ndi.binary_opening(paint, structure=morphology.disk(PAINT_WIDE)), iterations=1)
    paint = smooth_mask(paint, 2.0, t) & fig   # (its edge smooth too)
    paint &= ~wash
    edge = fig & (ndi.distance_transform_edt(fig) <= STROKE_W)
    ink = lines | paint | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 40)[lab]
    dots &= ~wash
    ink |= dots
    steps = []
    gw = ndi.gaussian_filter(g, STEP_SIGMA)
    for level, opacity in WASH_STEPS:
        m = wash & (gw < level) & ~ink
        m = morphology.remove_small_objects(smooth_mask(m, 2.0, t) & wash, max_size=80)
        steps.append((m, opacity))
    return ink, fig, g, dict(contrast=contrast, cm=cm, c=c, ground=ground, dots=dots, steps=steps)


def add_tone(svg, steps, box):
    """The hair washes added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of
    class "tone" in the line colour, between the body and the lines (as acharnians.py): one per step
    [(mask, total opacity)], each drawn over the last at the opacity that brings the total to its own."""
    x0, y0, x1, y1 = box
    paths, below = [], 0.0
    for mask, total in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(mask[y0:y1, x0:x1], turdsize=20, alphamax=1.0)
        a = 1 - (1 - total) / (1 - below)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
        below = total
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def main(paths, qa=None, dump=None):
    if "--refit" in sys.argv:
        fit_model(paths)
        return
    if "--refit-sides" in sys.argv:
        fit_side(paths["a1"], paths["a4"], "a4", "a1")
        fit_side(paths["a2"], paths["a5"], "a5", "a2")
        return
    cached = os.environ.get("MEDEA_FLAT")   # (development: a flat saved by an earlier run's dump)
    flat = np.asarray(Image.open(cached).convert("RGB")) if cached else joined(paths)
    if dump and not cached:
        Image.fromarray(flat).save(str(dump) + ".flat.png")
    with tempfile.TemporaryDirectory() as td:
        ink, fig, g, extra = drawing(flat, Path(td))
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ink=ink, c=extra["c"], ground=extra["ground"],
                            contrast=extra["contrast"].clip(0, 255).astype(np.uint8), cm=extra["cm"].clip(0, 255).astype(np.uint8))
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=extra["dots"],
        title="Medea in the serpent chariot in the sun disk, with the Furies, Jason, the nurse, the tutor and the dead children",
        desc="Line drawing after the Lucanian red-figure calyx-krater near the Policoro Painter, c. 400 BCE, Cleveland "
             "Museum of Art 1991.1, side A; traced from the museum's photographs (CC0), taken off the vase's curve, changed.")
    add_tone(OUT, extra["steps"], info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(dict(zip(NAMES + SIDES, args[:6])), *args[6:8])
