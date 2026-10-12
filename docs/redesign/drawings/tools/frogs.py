"""Frogs: the whole of side A of an Apulian red-figure bell-krater, Cleveland Museum of Art 1989.73, attributed to
the Choregos Painter, about 390-380 BC (the museum's record): a colossal bust of Dionysos in a fillet and laurel
wreath, his thyrsos with its vine over his shoulder, between two comic actors in masks and padded costumes, the left
one reaching for a bunch of grapes, the right one holding a large skyphos. The vase is no scene of the play and is
some fifteen years later than Frogs (405 BC): Dionysos is the play's hero and the god of the theatre, so the link
is thematic only. Photos: the museum's own (CC0, open access): "1989.73_full.tif" (the main view, side A) is the
drawing's source; "alt1" (the right handle to the camera) and "alt2" (side A from above) serve the vase's shape.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0). Two steps are
geometry, not image filtering, and stay in numpy/scipy: taking the painting off the vase's curve
(vase_unroll.py) and fitting the vase (--refit). The SVG is written by linework.trace_svg.

    python3 docs/redesign/drawings/tools/frogs.py front.tif [qa.png]
    python3 docs/redesign/drawings/tools/frogs.py front.tif alt1.jpg alt2.jpg --refit [focal]
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
from scipy.interpolate import CubicSpline
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "frogs.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------- the vase

# The photos carry no focal length. The prints ("alt1", "alt2") are the full TIFs scaled down (2627 px wide against
# 4343 and 4384); the full TIFs are crops of one camera's frame, so each print's focal length is the front's times
# its scale (PRINT_K)
PRINT_K = {"front": 1.0, "alt1": 2627 / 4343, "alt2": 2627 / 4384}
D0 = 10000.0
# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit again; it prints these numbers).
# World units are arbitrary (the front camera's D fixes them); y = 0 on the meander band's lower edge, up.
FOCAL = 20000.0
CAMERAS = {
    "front": dict(D=10000, H=894.313, b=0.0386471, p=-0.000249342, g=0.0015661, f=20000, cx=2196.5, cy=2842.5),
    "alt1": dict(D=9994.03, H=1046.08, b=0.0586623, p=0.00178762, g=0.00729805, f=12097.6, cx=1313.5, cy=1700),
    "alt2": dict(D=9615.62, H=2595.54, b=0.231054, p=-0.000294402, g=0.00405461, f=11984.5, cx=1313.5, cy=1700),
}
PROFILE_R = [237.08, 388.18, 533.05, 580.65, 608.61, 614.53, 616.68, 618.41, 640.36, 662.43, 684.46]
TURNS = {"alt1": -94.784, "alt2": 1.905}
# The data for fit_model: the rows (photo px) where each photo's outline is the vase's own (clear of the handles
# and the rim's lip), and rough guides to the meander band's lower edge (y = 0 on it)
FIT_ROWS = {"front": [(2010, 2240), (3080, 4700)], "alt1": [(1090, 2800)], "alt2": [(1850, 2600)]}
FIT_BAND = {"front": [(1000, 3930), (2200, 3957), (3400, 3930)], "alt1": [(780, 2290), (1300, 2318), (2000, 2300)],
            "alt2": [(830, 2195), (1350, 2245), (1950, 2190)]}
BAND_V = 3961   # the band's row in the front photo at the axis, roughly (the profile's start)
PROFILE_PX = [-750, -450, -150, 150, 450, 750, 1050, 1350, 1650, 1950, 2150]   # knots, in front px above the band


def outline(rgb, rows, step=20, drop=25):
    """(side, u, v): the vase's outline in rows `rows` [(v0, v1)]: per row, the background's level is the median of
    the row's outer 140 px (the museum's grey runs from 70 to 130 down the frame); the vase starts where the grey
    (blurred 1 px) stays `drop` under it for 30 px; the edge is where it crosses half way, to a fraction of a px."""
    L = ndi.gaussian_filter(rgb.mean(2), 1.0)
    W = L.shape[1]
    out = []
    for v0, v1 in rows:
        for v in range(v0, v1 + 1, step):
            for side in (0, 1):
                row = L[v] if side == 0 else L[v, ::-1]
                bg = np.median(row[10:150])
                run = np.convolve(row < bg - drop, np.ones(30), "valid") == 30
                if not run.any():
                    continue
                x = int(np.argmax(run))
                mid = (bg + np.median(row[x + 10:x + 40])) / 2
                xs = np.arange(max(x - 15, 1), x + 10)
                k = np.nonzero((row[xs] >= mid) & (row[xs + 1] < mid))[0]
                if not len(k):
                    continue
                k = xs[k[-1]]
                u = k + (row[k] - mid) / (row[k] - row[k + 1])
                out.append((side, u if side == 0 else W - 1 - u, v))
    return np.array(out)


def band_edge(rgb, rough, half=60, step=10):
    """(u, v) along the meander band's lower edge: per column near the rough guide, the step from the clay strip
    above (red less blue, blurred 1.5 px, over 60) to the black below (under 40 for 50 px), at half way, to a fraction
    of a px; kept where the points lie on one smooth curve."""
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5)
    r = np.array(rough, float)
    f = np.polyfit(r[:, 0], r[:, 1], min(2, len(r) - 1))
    out = []
    for u in range(int(r[0, 0]), int(r[-1, 0]), step):
        vg, col, best = int(np.polyval(f, u)), RB[:, u], None
        for v in range(vg - half, vg + half):
            above, below = col[v - 14:v - 3].mean(), col[v + 4:v + 54].mean()
            if above > 60 and below < 40 and col[v + 4:v + 54].max() < 70 and (best is None or above - below > best[0]):
                best = (above - below, v, above, below)
        if best:
            _, v, above, below = best
            mid, seg = (above + below) / 2, col[v - 8:v + 9]
            k = np.nonzero((seg[:-1] >= mid) & (seg[1:] < mid))[0]
            if len(k):
                k = k[np.argmin(abs(k - 8))]
                out.append((u, v - 8 + k + (seg[k] - mid) / (seg[k] - seg[k + 1])))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 3), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 2]


START_F = 20000.0
START = {"front": dict(D=10000, H=894.313, b=0.0386471, p=-0.000249342, g=0.0015661),
         "alt1": dict(D=9994.03, H=1046.08, b=0.0586623, p=0.00178762, g=0.00729805),
         "alt2": dict(D=9615.62, H=2595.54, b=0.231054, p=-0.000294402, g=0.00405461)}
START_R = [237.08, 388.18, 533.05, 580.65, 608.61, 614.53, 616.68, 618.41, 640.36, 662.43, 684.46]
START_TURNS = {"alt1": -94.784, "alt2": 1.905}


def fit_model(photos: dict, focal: float) -> None:
    """Fit the vase's profile and the three cameras at the front's focal length `focal` (px) and print them (see
    vase_unroll.fit). Needs opencv for SIFT."""
    import cv2
    names = ["front", "alt1", "alt2"]
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in names}
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(n, k, box):
        g = cv2.cvtColor(rgb[n].astype(np.uint8), cv2.COLOR_RGB2GRAY)
        m = np.zeros_like(g)
        m[box[1]:box[3], box[0]:box[2]] = 255
        g = cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
        kp, d = sift.detectAndCompute(g, m)
        return np.array([p.pt for p in kp]) / k, d

    kf, df = feats("front", 0.21, (900, 2050, 3500, 3980))   # (the scene and the band; matched at the prints' scale)
    matches = {}
    uc, rr = 2197.0, 1150.0   # the vase's axis and radius at the scene in the front photo, roughly
    centre = {"alt1": (1285.0, 700.0), "alt2": (1310.0, 680.0)}   # the same in each print
    for n, turn in (("alt1", -110.0), ("alt2", 0.0)):
        kn, dn = feats(n, 0.35, (500, 900, 2300, 2400))
        good = [a for a, b in cv2.BFMatcher(cv2.NORM_L2).knnMatch(df, dn, k=2) if a.distance < 0.8 * b.distance]
        a, b = np.float32([kf[x.queryIdx] for x in good]), np.float32([kn[x.trainIdx] for x in good])
        # keep the matches a turn of about `turn` explains (on a cylinder; the arcsine saturates near the sides, so
        # alt1's turn reads about -110 here, the fit finds it)
        cu, cr = centre[n]
        d = np.degrees(np.arcsin(np.clip((b[:, 0] - cu) / cr, -1, 1)) - np.arcsin(np.clip((a[:, 0] - uc) / rr, -1, 1)))
        matches[n] = np.hstack([a, b])[np.abs(d - turn) < 25]
        print(n, "matches", len(good), "kept", len(matches[n]))
    views = {}
    for n in names:
        views[n] = dict(size=rgb[n].shape[1::-1], sil=[tuple(r) for r in outline(rgb[n], FIT_ROWS[n])],
                        band=band_edge(rgb[n], FIT_BAND[n]), f=focal * PRINT_K[n])
    k = D0 / focal
    knots = np.array(PROFILE_PX, float) * k
    # the start: the fit at 20000 px (START), its lengths scaled to this focal length (at longer ones a start from
    # the outline alone let alt1's turn slide to a false -164 degrees)
    q = START_F / focal
    x0 = []
    for n in names:
        c = START[n]
        x0 += [c["D"], c["H"] * q, c["b"], c["p"], c["g"], focal, 0.0, 0.0]
    x0 += list(np.array(START_R) * q) + [0.0, 0.0]
    x0 += [np.radians(START_TURNS["alt1"]), np.radians(START_TURNS["alt2"])]
    cams, R, _, turns, report, _ = vu.fit(views, knots, matches=matches, d0=D0, rounds=3, outlier=30, nfev=1500,
                                          x_start=np.array(x0))
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{q}={c[q]:.6g}" for q in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 2) for y in knots])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


# ---------------------------------------------------------------- the flat

# As wasps.py (John's choice there, 2026-10-10): the flat keeps the vase's rings straight and its meridians upright,
# x = R_C (theta - theta_C), y = the arc length up the profile, R_C the radius at CENTRE (a front-photo point at the
# scene's middle, Dionysos's chin). G px per world unit is the front photo's own scale at CENTRE. The frame is the
# flat image of the front-photo box BOX, MARGIN units wider.
CENTRE, BOX, MARGIN = (2200.0, 3000.0), (880, 2040, 3520, 3990), 10.0


def vase():
    k = D0 / FOCAL
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(np.array(PROFILE_PX) * k, PROFILE_R)


def frame():
    """(cams, R, theta_C, R_C, arc table (y, t), X0, Y1, G, W, H)."""
    cams, R = vase()
    c = cams["front"]
    k = D0 / FOCAL
    yr = (PROFILE_PX[0] * k, PROFILE_PX[-1] * k)
    t0 = vu.photo_to_surface(c, R, np.array([CENTRE]), yr)[0]
    P = vu.project(c, vu.surface(R, np.array([t0[1], t0[1] + 1.0]), np.array([t0[0], t0[0]])))
    G = float(np.hypot(*(P[1] - P[0])))
    rc = float(R(t0[1]))
    yt, tt = vu.arc_table(R, *yr)
    x0, y0, x1, y1 = BOX
    s = np.linspace(0, 1, 40)
    edge = np.vstack([np.c_[x0 + s * (x1 - x0), np.full(40, y0)], np.c_[x0 + s * (x1 - x0), np.full(40, y1)],
                      np.c_[np.full(40, x0), y0 + s * (y1 - y0)], np.c_[np.full(40, x1), y0 + s * (y1 - y0)]])
    cr = vu.photo_to_surface(c, R, edge, yr)
    fx, fy = rc * (cr[:, 0] - t0[0]), np.interp(cr[:, 1], yt, tt)
    X0, X1, Y0, Y1 = fx.min() - MARGIN, fx.max() + MARGIN, fy.min() - MARGIN, fy.max() + MARGIN
    return cams, R, float(t0[0]), rc, (yt, tt), X0, Y1, G, int((X1 - X0) * G), int((Y1 - Y0) * G)


def flat_image(src, cam="front"):
    """A photo laid onto the flat frame through camera `cam` (H x W x 3, uint8)."""
    cams, R, th0, rc, (yt, tt), X0, Y1, G, W, H = frame()
    gx, gy = np.meshgrid(np.arange(W), np.arange(H))
    th = th0 + (X0 + gx / G) / rc + np.radians(TURNS.get(cam, 0.0))
    y = np.interp(Y1 - gy / G, tt, yt)
    uv = vu.project(cams[cam], vu.surface(R, y.ravel(), th.ravel())).reshape(gx.shape + (2,))
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [uv[..., 1], uv[..., 0]], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


# ---------------------------------------------------------------- the scene

CLAY = 60                     # clay: red less blue above this (blurred 2 px); glaze under it
LINE_DARK = 85                # painted lines: grey darker than this (blurred 1.5 px)
WHITE_L, WHITE_RB = 200, 60   # the added white: lighter than this (grey blurred 2 px) and less red (clay is redder)
# Ground: the glaze, its painted strokes (up to OPEN*2 px wide) opened away; the large areas. Smaller glaze areas
# inside the figures are paint
OPEN, AUTO_GROUND = 14, 40000
SMOOTH = 2.0
# The outline: EDGE_OUT flat px wide on the black ground outside the clay, not on the clay (John on Ion, 2026-10-09;
# here, 2026-10-12: "the vine should not be ink, but ground with outline"), so thin clay (the vine, the stalks)
# keeps its full width; and along the floor, inside the clay (the soles). No lines are looked for within EDGE_IN px
# inside the clay's edge (its soft rim)
EDGE_OUT, EDGE_IN = 5, 4
SPECK, FLECK = 150, 200
# Lines, as wasps.py: the grey's local contrast (PhotoCraft: blurred 1 px, capped at the clay's level by Levels,
# input white LC_CAP; its Maximum then Minimum over LC_R px, less it), with hysteresis (LC_LOW, LC_HIGH), LINE_LEN px
# or longer along the centre, each line redrawn along its centre at the paint's own width (half maximum), smoothed
# along the line over WIDTH_SIGMA px, at least LINE_MIN wide; the mask smoothed first (Gaussian MASK_SIGMA, cut at
# half), pinholes under HOLE px^2 filled, side spurs under SPUR px pruned. Solid paint: the dark (LINE_DARK) opened
# over SOLID_R px, drawn at its own shape
LC_CAP, LC_R, LC_LOW, LC_HIGH = 175, 8, 30, 50
LINE_LEN, HALF_R, WIDTH_SIGMA, LINE_MIN = 25, 6, 6.0, 3.0
# The faces' finer lines (John, 2026-10-12: "you're missing some of the finer lines on the face"): inside FACES
# (boxes, flat px: Dionysos, the left actor's mask, the right actor's) the paler brown lines too (FACE_LC
# hysteresis) and shorter ones (FACE_LEN px)
FACES = [(1385, 700, 1835, 1300), (540, 400, 790, 600), (2350, 660, 2520, 850)]
FACE_LC, FACE_LEN = (16, 28), 8
# In the faces, lines near half maximum (as libation_bearers.py's eyes): darker than HM_FR of the way from their core
# (PhotoCraft's Minimum over HM_CORE px of the grey blurred 1 px) to the clay round them (its Maximum over HM_R px),
# where that dip is over HM_DEPTH; smoothed (HM_SMOOTH, cut at half); pieces under HM_MIN px^2, or whose darkest px
# is lighter than HM_DARK (the clay's mottling), dropped. Redrawn along their centres the short faint strokes
# smeared into blots
HM_R, HM_CORE, HM_FR, HM_DEPTH, HM_SMOOTH, HM_MIN, HM_DARK = 8, 2, 0.42, 40, 0.8, 10, 110
# (the grey capped at the clay's level first, LC_CAP, so the white paint beside a line does not widen it; HM_DEPTH
# is on that scale)
HOLE, MASK_SIGMA, SPUR, SOLID_R = 12, 1.5, 7, 6
# The thinned brown glaze (the irises, the hair's lighter curls, the tail): darker than the clay, still red; a
# stepped wash (grey under, blurred 1 px; total opacity)
BROWN_STEPS = [(150, 0.18), (125, 0.32), (100, 0.46)]
BROWN_RB, BROWN_MIN = 60, 30
# The hair is brushwork: black curls over dark brown glaze, curls close together. Where the paint is dense (its
# share within a HAIR_SIGMA px blur over HAIR_DENS) its black (grey under HAIR_INK, blurred 1 px; smoothed by
# HAIR_SMOOTH, cut at half) is ink at its own shape, traced at its own size, not redrawn along centres (that gave
# noodles and blots); the brown under it a stepped wash darker than elsewhere (HAIR_STEPS; drawn solid it was one blot)
HAIR_SIGMA, HAIR_DENS, HAIR_SMOOTH, HAIR_INK = 12.0, 0.25, 1.0, 36
# (darker, John, 2026-10-12: "the curls should be darker", "esp. around the leaves of the crown")
HAIR_STEPS = [(150, 0.3), (125, 0.5), (100, 0.66), (75, 0.8), (55, 0.88)]
# The left actor's hair and goatee, darker (John, 2026-10-12: "make the comic actor's hair darker", then "not ink,
# but just above ink color wise", "the goatee should be just above ink wash"): inside MASK_HAIR (the hair) and
# GOATEE (boxes, flat px) the paint darker than MASK_DARK (grey, blurred 1 px) is a wash at MASK_OP, not ink; the
# lines in them (the sprig's leaves) stay ink
MASK_HAIR, GOATEE, MASK_DARK, MASK_OP = (410, 420, 598, 640), (690, 505, 790, 585), 110, 0.85
# The grapes' dots, black ink (John, 2026-10-12: "those dots of the grapes should just be black ink"): small,
# compact dark marks (grey under DOT_L, blurred 1 px; DOT_MIN to DOT_MAX px^2, no longer than DOT_LEN px) on the
# clay above VINE_Y (flat y), off the hair, traced at their own size
DOT_L, DOT_MIN, DOT_MAX, DOT_LEN, VINE_Y = 130, 12, 700, 45, 780
# The added yellow (the wreath's berries): yellower than the clay (green over BERRY_G, blurred 2 px), a wash
BERRY_G, BERRY_OP = 195, 0.3
# The added white: a stepped grey wash following its whiteness, no outline where it meets the ground (as wasps.py)
TONE_STEPS, STEP_BLUR, STEP_MIN = [(0, 0.16), (45, 0.27), (70, 0.38)], 2.0, 40
# Paint that runs into the ground's black is taken for ground: inside these polygons (flat px) the dark is paint:
# the right actor's open mouth, open to the ground between his moustache and his beard
PAINT_POLYS = [[(2392, 801), (2450, 803), (2452, 832), (2390, 826)]]
# John's marks (2026-10-12, on pass 1 in PhotoCraft: 1 blue = ink to add, 2 green = ink to take out), on the file's
# grid: the flat cropped at MARKS_AT (its top-left, flat px). Laid in as he drew them, smoothed (Gaussian MARK_SIGMA,
# cut at half), and traced at their own size
MARKS_FILES, MARKS_AT, MARK_SIGMA = ["frogs_marks_1.png"], (0, 120), 0.8
# Smaller dark areas the figures close in that are ground (flat px, a point in each): the loop between the left
# grape bunch and its stalk
OPEN_PTS = [(416, 234)]
# The vine's loops close in the ground: every dark area above VINE_TOP (flat y; its top row) is ground, except in
# Dionysos's hair (HAIR_BOX, flat px)
VINE_TOP, HAIR_BOX = 330, (1150, 262, 2050, 760)
# Big dark areas the figures close in that are paint, not ground (flat px, a point in each)
PAINT_PTS = []
WEIGHT = 0.0015   # (pass 0: "own" gave 0.205%, the outline heavy)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as wasps.py)."""
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


def even_lines(contrast, dark, area, faces):
    """The painted lines: `dark`, and in `area` those found by local contrast (paler and shorter ones in `faces`),
    redrawn along their centres at the paint's own width (see LC_* and the constants after it; as wasps.py)."""
    from skimage.filters import apply_hysteresis_threshold
    found = np.where(faces, apply_hysteresis_threshold(contrast, *FACE_LC), apply_hysteresis_threshold(contrast, LC_LOW, LC_HIGH))
    firm = (found & area) | dark
    firm = morphology.remove_small_holes(firm, max_size=HOLE)
    near_max = ndi.maximum_filter(np.where(firm, contrast, 0), 2 * HALF_R + 1)
    own = (firm & (contrast >= 0.5 * near_max)) | dark
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray((firm * 255).astype(np.uint8)).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MASK_SIGMA}))
        mask = grey(Path(td) / "ms.png") >= 128
    c = centre_lines(mask, spur=SPUR, min_len=FACE_LEN)
    lab, _ = ndi.label(c, structure=np.ones((3, 3)))   # (outside the faces, only the longer pieces)
    short = np.bincount(lab.ravel()) <= LINE_LEN
    short[np.unique(lab[faces & c])] = False
    short[0] = False
    c &= ~short[lab]
    w = 2 * ndi.distance_transform_edt(own)
    num, den = (ndi.gaussian_filter(a, WIDTH_SIGMA) for a in (np.where(c, w, 0.0), c.astype(float)))
    half = np.where(c, np.maximum(num / np.maximum(den, 1e-6), LINE_MIN) / 2, 0.0)
    d, (iy, ix) = ndi.distance_transform_edt(~c, return_indices=True)
    return d <= half[iy, ix]


def measures(rgb):
    """The PhotoCraft measures of a flat image: {name: array}."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rgb).save(t / "c.png")
        rb = ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]})
        pc(t / "c.png", t / "rbs.png", rb, ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "g2.png", ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "g.png", t / "g1.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "g.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": STEP_BLUR}))
        pc(t / "g.png", t / "gc.png", ("filter.blur.gaussianBlur", {"radius": 1}),
           ("image.adjustments.levels", {"inWhite": LC_CAP}))
        pc(t / "gc.png", t / "gcc.png", ("filter.other.maximum", {"radius": LC_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": LC_R, "preserve": "squareness"}))
        pc(t / "c.png", t / "g2b.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [0, 100, 0, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "gc.png", t / "hmax.png", ("filter.other.maximum", {"radius": HM_R, "preserve": "roundness"}))
        pc(t / "gc.png", t / "hmin.png", ("filter.other.minimum", {"radius": HM_CORE, "preserve": "roundness"}))
        m = {n: grey(t / f"{n}.png") for n in ("rbs", "g", "g1", "g2", "gw", "gc", "gcc", "g2b", "hmax", "hmin")}
        m["core"] = grey(t / "core.png") < 128
    m["contrast"] = m["gcc"] - m["gc"]
    return m


# Side A's edges (John, 2026-10-12: "the whole of side A"; the edges as shown to him on the museum's preview). Top:
# under the rim's laurel band, whose lower clay strip holds row TOP_ROW; its lower edge per column, fitted by a
# cubic where nothing touches it. Floor: the top of the meander band's upper clay strip, found per column where no
# figure stands on it (the ground over it for FLOOR_CLEAR px) in rows FLOOR_ROWS, fitted by a cubic; the figures end
# a px above it. Sides: between LEFT and RIGHT (flat px, run through the black between the scene and the handles'
# ornaments); a clay piece is the scene's if most of it lies between them, so no ornament is cut through
TOP_ROW, FLOOR_ROWS, FLOOR_CLEAR = 112, (1772, 1812), 30
LEFT = [(90, 0), (90, 640), (175, 700), (195, 1000), (135, 1120), (125, 1360), (100, 1400), (40, 1650), (20, 2200)]
RIGHT = [(2985, 0), (2985, 540), (2965, 700), (2970, 940), (2895, 965), (2895, 1110), (2908, 1140), (2910, 1320),
         (2950, 2200)]


def band_lines(clay):
    """(top, floor): the rows of the scene's top and floor per column of the flat (see TOP_ROW)."""
    H, W = clay.shape
    xs, top, fl = np.arange(W), [], []
    for x in xs:
        col = clay[:, x]
        if col[TOP_ROW]:
            y = TOP_ROW
            while col[y + 1]:
                y += 1
            if y < TOP_ROW + 30:   # (the vine or the thyrsos touching it runs on: left out)
                top.append((x, y + 1))
        y0, y1 = FLOOR_ROWS
        k = np.nonzero(col[y0:y1])[0]
        if len(k) and not col[y0 + k[0] - FLOOR_CLEAR:y0 + k[0]].any():
            fl.append((x, y0 + k[0]))
    out = []
    for pts in (np.array(top, float), np.array(fl, float)):
        keep = np.ones(len(pts), bool)
        for _ in range(3):
            f = np.polyfit(pts[keep, 0], pts[keep, 1], 3)
            keep = np.abs(pts[:, 1] - np.polyval(f, pts[:, 0])) < 3
        out.append(np.polyval(f, xs))
    return out


def john_marks(shape):
    """(blue, green) of John's marks (MARKS_FILES, in order) on the flat."""
    blue, green = np.zeros(shape, bool), np.zeros(shape, bool)
    x0, y0 = MARKS_AT
    for f in MARKS_FILES:
        m = np.asarray(Image.open(Path(__file__).resolve().parent / f))
        h, w = m.shape
        b = np.zeros(shape, bool)
        b[y0:y0 + h, x0:x0 + w] = ndi.gaussian_filter((m == 1).astype(np.float32), MARK_SIGMA) > 0.5
        gr = np.zeros(shape, bool)
        gr[y0:y0 + h, x0:x0 + w] = m == 2
        blue = (blue & ~gr) | b
        green = (green & ~b) | gr
    return blue, green


def scene(rgb, paint_pts=()):
    """(ink, ink traced at its own size, figure, grey, brown steps, white steps) for the flat image `rgb`."""
    m = measures(rgb)
    g, g1, g2, rbs, core, contrast = m["g"], m["g1"], m["g2"], m["rbs"], m["core"], m["contrast"]
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    top, floor = band_lines(rbs > CLAY)
    rows = (yy >= top[xx]) & (yy < floor[xx] - 1)
    white = (g2 > WHITE_L) & (rbs < WHITE_RB) & rows
    clay = ((rbs > CLAY) | white) & rows
    side = lw.polygon_mask(g.shape, np.array(LEFT[::-1] + RIGHT, float))
    lab, _ = ndi.label(clay)
    inside = np.bincount(lab[side].ravel(), minlength=lab.max() + 1) > 0.5 * np.bincount(lab.ravel())
    inside[0] = False
    region = ndi.binary_fill_holes(inside[lab] | ~rows) & rows   # (the scene's clay with the dark it closes in)
    region = rows & ndi.binary_fill_holes(region | ~side)
    dark = ~clay & rows
    painted = np.any([lw.polygon_mask(g.shape, np.array(q, float)) for q in PAINT_POLYS], 0) & dark
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND
    for x, y in paint_pts:
        assert lab[y, x], f"paint point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = False
    for x, y in OPEN_PTS:
        assert lab[y, x], f"open point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = True
    hx0, hy0, hx1, hy1 = HAIR_BOX
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None or sl[0].start >= VINE_TOP:
            continue
        cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
        if not (hx0 <= cx < hx1 and hy0 <= cy < hy1):
            is_ground[k] = True
    for k in np.unique(lab[(lab > 0) & ~is_ground[lab]]):   # (check: the largest areas kept as paint)
        if size[k] > 3000:
            yk, xk = np.argwhere(lab == k)[0]
            print("dark kept as paint", size[k], (xk, yk))
    ground = (is_ground[lab] | ~rows) & ~painted
    fig = (ndi.binary_fill_holes(inside[ndi.label(clay)[0]] & ~ground) & ~ground) | painted
    fig = ndi.gaussian_filter(fig.astype(np.float32), SMOOTH) > 0.5
    fig &= rows
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) >= SPECK)[lab]
    paint = dark & fig & core
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE_IN)
    # (the white has no outline where it meets the ground: the tufts that stand out on the black; the clay body under
    # them keeps its outline)
    dt, (iy, ix) = ndi.distance_transform_edt(~fig, return_indices=True)
    outline = ~fig & rows & (dt <= EDGE_OUT) & ~white[iy, ix]
    outline |= fig & (yy >= floor[xx] - 1 - EDGE_OUT)
    inbox = lambda b: (xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3])
    faces = np.any([inbox(b) for b in FACES], 0)
    # (the faces' close lines are not hair)
    hair = ndi.binary_dilation(ndi.gaussian_filter(paint.astype(np.float32), HAIR_SIGMA) > HAIR_DENS, iterations=4) & fig & ~(faces & ~inbox(MASK_HAIR))
    hair_ink = (ndi.gaussian_filter(((g1 < HAIR_INK) & fig & ~edge).astype(np.float32), HAIR_SMOOTH) > 0.5) & hair & ~edge
    mask_wash = ((inbox(MASK_HAIR) & hair) | inbox(GOATEE)) & fig & ~edge & (g1 < MASK_DARK)
    mask_wash = ndi.gaussian_filter(mask_wash.astype(np.float32), HAIR_SMOOTH) > 0.5
    hair_ink &= ~mask_wash
    solid = ndi.binary_opening(paint & ~edge & ~hair, structure=morphology.disk(SOLID_R))
    solid = ndi.binary_dilation(solid, iterations=2) & paint
    area = fig & ~edge & ~white & ~hair & ~ndi.binary_dilation(solid, iterations=3)
    hm = (m["gc"] < m["hmin"] + HM_FR * (m["hmax"] - m["hmin"])) & (m["hmax"] - m["hmin"] > HM_DEPTH) & faces & area
    hm = (ndi.gaussian_filter(hm.astype(np.float32), HM_SMOOTH) > 0.5) & area
    hm = morphology.remove_small_objects(hm, max_size=HM_MIN)
    lab, n = ndi.label(hm)
    hm &= np.r_[False, ndi.minimum(g1, lab, np.arange(1, n + 1)) < HM_DARK][lab]
    lines = solid | (even_lines(contrast, core & area & ~faces, area & ~faces, faces) & ~faces) | hm
    lines &= fig & ~edge & ~white & ~hair
    marks = (g1 < DOT_L) & fig & ~edge & ~hair & (yy < VINE_Y)
    lab, _ = ndi.label(marks)
    sz = np.bincount(lab.ravel())
    ok = (sz >= DOT_MIN) & (sz <= DOT_MAX)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if ok[k] and max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) > DOT_LEN:
            ok[k] = False
    ok[0] = False
    dots = ok[lab]
    lines &= ~ndi.binary_dilation(dots, iterations=2)
    hair_ink |= dots
    lines &= ~(mask_wash & inbox(GOATEE))   # (the goatee's strokes are the wash, not lines)
    ink = lines | outline | hair_ink
    hair_ink = hair_ink | (lines & np.any([inbox(b) for b in FACES], 0))   # (faces traced at their own size, as wasps.py)
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    blue, green = john_marks(g.shape)
    # (the lines traced at the pinned weight stay as pass 1 drew them, less his green: his blue goes with the ink
    # traced at its own size, or the weighting's measured width moves and every line on the side changes)
    main = ink & ~hair_ink & ~green
    ink = (ink & ~green) | blue
    hair_ink = (hair_ink & ~green) | blue
    brown = fig & ~ink & ~white & ((rbs > BROWN_RB) | hair)
    bsteps, hsteps = [], []
    for steps, where, out in ((BROWN_STEPS, ~hair, bsteps), (HAIR_STEPS, hair, hsteps)):
        for level, opacity in steps:
            mm = brown & where & (g1 < level)
            lab, _ = ndi.label(mm)
            mm &= (np.bincount(lab.ravel()) >= BROWN_MIN)[lab]
            out.append((mm, opacity))
    whiteness = np.clip(m["gw"] - 120, 0, None) * np.clip((80 - rbs) / 60, 0, 1)
    wbase = fig & ~ink & (ndi.gaussian_filter((white & fig).astype(np.float32), 1.5) > 0.5)
    wsteps = []
    for level, opacity in TONE_STEPS:
        mm = wbase & (whiteness >= level)
        lab, _ = ndi.label(mm)
        mm &= (np.bincount(lab.ravel()) >= STEP_MIN)[lab]
        wsteps.append((mm, opacity))
    berry = fig & ~ink & (m["g2b"] > BERRY_G)
    lab, _ = ndi.label(berry)
    berry &= (np.bincount(lab.ravel()) >= BROWN_MIN)[lab]
    wsteps.append((berry, BERRY_OP))   # (drawn last; berries and white do not meet)
    return ink, main, hair_ink, fig, g, (bsteps, hsteps, [(mask_wash & ~ink, MASK_OP)]), wsteps


def add_tone(svg, steps, box):
    """The half tone added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of class
    "tone" in the line colour, between the body and the lines, one per step [(mask, total opacity)], each drawn
    over the last at the opacity that brings the total to its own (as wasps.py)."""
    x0, y0, x1, y1 = box
    paths, below = [], 0.0
    for mask, total in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(lw.resample_ink(mask[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
        a = 1 - (1 - total) / (1 - below)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
        below = total
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def main(src, qa=None, flat_png=None):
    rgb = np.asarray(Image.open(flat_png).convert("RGB")) if flat_png else flat_image(src)
    ink, main, own, fig, g, bsteps, wsteps = scene(rgb, PAINT_PTS)
    info = lw.trace_svg(main, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=own,
                        title="The bust of Dionysos between two comic actors, one reaching for grapes, one holding a cup",
                        desc="Line drawing after the Apulian red-figure bell-krater Cleveland Museum of Art 1989.73, side A; "
                             "traced from the museum's photograph (CC0), taken off the vase's curve.")
    for steps in bsteps:   # (the brown, the hair, the left actor's hair and goatee: each its own set of steps)
        add_tone(OUT, [(mm & ~ink, o) for mm, o in steps], info["box"])
    add_tone(OUT, [(mm & ~ink, o) for mm, o in wsteps], info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--refit" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--refit"]
        fit_model(dict(zip(["front", "alt1", "alt2"], args[:3])), float(args[3]) if len(args) > 3 else 30000.0)
    elif "--flat" in sys.argv:   # front.tif out.png [cam]
        args = [a for a in sys.argv[1:] if a != "--flat"]
        cam = args[2] if len(args) > 2 else "front"
        Image.fromarray(flat_image(args[0], cam)).save(args[1])
    elif "--from-flat" in sys.argv:   # flat.png [qa.png] (a flat saved with --flat: quicker)
        a = [x for x in sys.argv[1:] if x != "--from-flat"]
        main(None, a[1] if len(a) > 1 else None, flat_png=a[0])
    else:
        main(*sys.argv[1:3])
