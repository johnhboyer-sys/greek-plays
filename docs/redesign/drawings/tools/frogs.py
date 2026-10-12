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
EDGE = 8                      # the outline, flat px wide
SPECK, FLECK = 150, 200
# Lines, as wasps.py: the grey's local contrast (PhotoCraft: blurred 1 px, capped at the clay's level by Levels,
# input white LC_CAP; its Maximum then Minimum over LC_R px, less it), with hysteresis (LC_LOW, LC_HIGH), LINE_LEN px
# or longer along the centre, each line redrawn along its centre at the paint's own width (half maximum), smoothed
# along the line over WIDTH_SIGMA px, at least LINE_MIN wide; the mask smoothed first (Gaussian MASK_SIGMA, cut at
# half), pinholes under HOLE px^2 filled, side spurs under SPUR px pruned. Solid paint: the dark (LINE_DARK) opened
# over SOLID_R px, drawn at its own shape
LC_CAP, LC_R, LC_LOW, LC_HIGH = 175, 8, 30, 50
LINE_LEN, HALF_R, WIDTH_SIGMA, LINE_MIN = 25, 6, 6.0, 3.0
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
HAIR_STEPS = [(150, 0.18), (125, 0.32), (100, 0.46), (75, 0.6), (55, 0.72)]
# The added yellow (the wreath's berries): yellower than the clay (green over BERRY_G, blurred 2 px), a wash
BERRY_G, BERRY_OP = 195, 0.3
# The added white: a stepped grey wash following its whiteness, no outline where it meets the ground (as wasps.py)
TONE_STEPS, STEP_BLUR, STEP_MIN = [(0, 0.16), (45, 0.27), (70, 0.38)], 2.0, 40


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


def even_lines(contrast, dark, area):
    """The painted lines: `dark`, and in `area` those found by local contrast, redrawn along their centres at the
    paint's own width (see LC_* and the constants after it; as wasps.py)."""
    from skimage.filters import apply_hysteresis_threshold
    firm = (apply_hysteresis_threshold(contrast, LC_LOW, LC_HIGH) & area) | dark
    firm = morphology.remove_small_holes(firm, max_size=HOLE)
    near_max = ndi.maximum_filter(np.where(firm, contrast, 0), 2 * HALF_R + 1)
    own = (firm & (contrast >= 0.5 * near_max)) | dark
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray((firm * 255).astype(np.uint8)).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MASK_SIGMA}))
        mask = grey(Path(td) / "ms.png") >= 128
    c = centre_lines(mask, spur=SPUR, min_len=LINE_LEN)
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
        m = {n: grey(t / f"{n}.png") for n in ("rbs", "g", "g1", "g2", "gw", "gc", "gcc", "g2b")}
        m["core"] = grey(t / "core.png") < 128
    m["contrast"] = m["gcc"] - m["gc"]
    return m


def scene(rgb, region, paint_pts=()):
    """(ink, figure, grey, brown steps, white steps) for the flat image `rgb` inside `region` (bool mask)."""
    m = measures(rgb)
    g, g1, g2, rbs, core, contrast = m["g"], m["g1"], m["g2"], m["rbs"], m["core"], m["contrast"]
    white = (g2 > WHITE_L) & (rbs < WHITE_RB) & region
    clay = ((rbs > CLAY) | white) & region
    dark = ~clay & region
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND
    for x, y in paint_pts:
        is_ground[lab[y, x]] = False
    ground = is_ground[lab] | ~region
    fig = ndi.binary_fill_holes(~ground) & ~ground
    fig = ndi.gaussian_filter(fig.astype(np.float32), SMOOTH) > 0.5
    fig &= region
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) >= SPECK)[lab]
    paint = dark & fig & core
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE)
    # (the white has no outline where it meets the ground)
    soft_edge = edge & (ndi.distance_transform_edt(~(white & fig)) <= EDGE + 3)
    hair = ndi.binary_dilation(ndi.gaussian_filter(paint.astype(np.float32), HAIR_SIGMA) > HAIR_DENS, iterations=4) & fig
    hair_ink = (ndi.gaussian_filter(((g1 < HAIR_INK) & fig & ~edge).astype(np.float32), HAIR_SMOOTH) > 0.5) & hair & ~edge
    solid = ndi.binary_opening(paint & ~edge & ~hair, structure=morphology.disk(SOLID_R))
    solid = ndi.binary_dilation(solid, iterations=2) & paint
    area = fig & ~edge & ~white & ~hair & ~ndi.binary_dilation(solid, iterations=3)
    lines = solid | even_lines(contrast, core & area, area)
    lines &= fig & ~edge & ~white & ~hair
    ink = lines | (edge & ~soft_edge) | hair_ink
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    brown = fig & ~ink & ~white & ((rbs > BROWN_RB) | hair)
    bsteps = []
    for (level, _), (hlevel, hopacity) in zip(BROWN_STEPS + [(0, 0)] * 2, HAIR_STEPS):
        mm = brown & np.where(hair, g1 < hlevel, g1 < level)
        lab, _ = ndi.label(mm)
        mm &= (np.bincount(lab.ravel()) >= BROWN_MIN)[lab]
        bsteps.append((mm, hopacity))   # (the brown's opacities are the hair's first three)
    whiteness = np.clip(m["gw"] - 120, 0, None) * np.clip((80 - rbs) / 60, 0, 1)
    wbase = fig & ~ink & ((ndi.gaussian_filter((white & fig).astype(np.float32), 1.5) > 0.5) | soft_edge)
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
    return ink, hair_ink, fig, g, bsteps, wsteps


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


def test(flat_png, box, out, weight="own", paint_pts=()):
    """A small test of the style on box (x0, y0, x1, y1, flat px): the drawing (SVG) and its QA renders."""
    x0, y0, x1, y1 = box
    rgb = np.asarray(Image.open(flat_png).convert("RGB"))[y0:y1, x0:x1].copy()
    region = np.ones(rgb.shape[:2], bool)
    ink, own, fig, g, bsteps, wsteps = scene(rgb, region, [(x - x0, y - y0) for x, y in paint_pts])
    out = Path(out)
    info = lw.trace_svg(ink & ~own, out, body=fig, open_holes=~fig, weight=weight, extent=fig, dots=own,
                        title="test", desc="test")
    add_tone(out, [(mm & ~ink, o) for mm, o in bsteps], info["box"])
    add_tone(out, [(mm & ~ink, o) for mm, o in wsteps], info["box"])
    print(out, info)
    return info


if __name__ == "__main__":
    if "--refit" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--refit"]
        fit_model(dict(zip(["front", "alt1", "alt2"], args[:3])), float(args[3]) if len(args) > 3 else 30000.0)
    elif "--flat" in sys.argv:   # front.tif out.png [cam]
        args = [a for a in sys.argv[1:] if a != "--flat"]
        cam = args[2] if len(args) > 2 else "front"
        Image.fromarray(flat_image(args[0], cam)).save(args[1])
    elif "--test" in sys.argv:   # flat.png x0 y0 x1 y1 out.svg
        a = [x for x in sys.argv[1:] if x != "--test"]
        test(a[0], tuple(int(v) for v in a[1:5]), a[5])
