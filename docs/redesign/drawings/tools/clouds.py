"""Clouds: a comic old man, the master, in a long chiton and a himation drawn up over his shoulder, a
bearded mask with curly hair, his right arm stretched out, and his slave (John, 2026-10-08: "yes, the
slave on the left too"), masked, his short tunic hitched up in his fist, from the phlyax scene on side A of
a Sicilian red-figure calyx-krater, Lentini-Manfria Group, c. 350-340 BC, Paris, Louvre CA 7249 (bought
1986). The vase does not show Clouds: the master is the type of Strepsiades. The slave's costume phallus is
drawn as painted (John, 2026-10-08: "you can include the genitals they aren't grotesque"). The stage under
them, the door and its column, the woman and the black ground are left out.

Photos:
  J  Jastrow, 2008-03-07, CC BY 3.0, the drawing's source (Nikon D200, 22 mm; a crop of the frame):
     https://upload.wikimedia.org/wikipedia/commons/4/41/Phlyax_scene_Louvre_CA7249.jpg
  L1 the Louvre's photo of side A, the whole vase (Hervé Lewandowski, 2005, (c) GrandPalaisRmn), for the
     vase's shape: https://collections.louvre.fr/media/cache/large/0000000021/0000263745/0000914097_OG.JPG
  L3 the Louvre's close view of the scene (the same), for the front foot's sole, which J cuts off:
     https://collections.louvre.fr/media/cache/original/0000000021/0000263745/0001015514_OG.JPG
The drawing traces only the ancient painting, which is public domain, so it does not carry the photos'
rights (John's rulings on Oedipus Tyrannus, 2026-10-02, and Philoctetes, 2026-10-03); Jastrow is credited.

Photo -> flat (vase_unroll.py; geometry, so numpy and scipy, not PhotoCraft):
  - J shows none of the vase's outline. The profile and L1's camera are fitted to L1's outline (row by
    row, from the middle out to the grey background, the gaps inside the handles included), the dark line
    under the checkers (y = 0, painted on the wheel, so a circle) and the lower edge of the clay strip
    under the ovolo (a ring); J's camera to points matched between L1 and J (SIFT, RANSAC). J's focal
    length is fixed from its EXIF (22 mm on a Nikon D200, 3872 px across 23.6 mm) and its centre fitted
    (MODEL). Left free, it comes out at 4020 px with the same error. A fit with L3 as a third camera
    moved the flat figure by 6 px (median), 37 at most, over its 2,200 px: not used, since L3's 684
    matches outweighed J's.
  - The camera stood about 20 cm from the vase, so the photo foreshortens his back by a third; the flat
    widens it again. The bowl here is nearly a cone, which flattens with lengths kept within 1%.

Flat -> drawing: every image step runs in PhotoCraft (`photocraft-cli` 0.2.0): the crop, the
enlargement, the grey, the clay map (Channel Mixer, red less blue), the blurs, the Maximum and Minimum
filters and the thresholds. numpy only combines PhotoCraft's masks and measures. The SVG is written by
linework.trace_svg.

    python3 docs/redesign/drawings/tools/clouds.py Phlyax_scene_Louvre_CA7249.jpg louvre1.jpg louvre3.jpg [qa.png]
    python3 docs/redesign/drawings/tools/clouds.py --refit Phlyax_scene_Louvre_CA7249.jpg louvre1.jpg
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline, LinearNDInterpolator
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "clouds.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (--refit prints these). World units: about L1's px
# at the vase (L1's D fixes them); y = 0 on the dark line under the checkers, up the vase; theta = 0
# faces J.
CAMERAS = {
    "L1": dict(D=6000, H=198.425, b=0.0129626, p=-0.000274157, g=0.00761186, f=6362.27, cx=590, cy=750),
    "J": dict(D=693.175, H=317.519, b=0.0123602, p=-0.0062072, g=0.00831529, f=3609.49, cx=1145.35, cy=1188.66),
}
PROFILE_Y = [-60, 40, 140, 240, 340, 440, 540, 600]
PROFILE_R = [227.6, 232.3, 237.1, 248.3, 265.7, 289.5, 313.4, 337.2]
FJ = 22.0 * 3872 / 23.6   # px: J's focal length over the D200's pixel pitch
# The data for fit_model: L1's outline rows and middle column; rough guides (L1 px) to the dark line
# under the checkers and to the lower edge of the clay strip under the ovolo; the box of L1 matched to
# J, and the scale J is matched at (the scene is about 7 times larger in J).
FIT_ROWS, FIT_MID = (385, 881), 590
FIT_BAND = [(360, 885), (500, 886.5), (600, 886), (700, 885.5), (825, 884)]
FIT_RING = [(440, 364.5), (520, 364), (600, 364), (700, 365), (780, 367), (840, 371), (905, 378)]
FIT_MATCH, FIT_K = (380, 360, 940, 760), 0.14


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def rgb(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def outline_rows(a, rows, mid, step=4, bg_min=54, run=5):
    """(v, u_left, u_right): from the vase's middle column out to the first run of the neutral grey
    background (the gap inside a handle counts), the edge where the level crosses halfway."""
    L = ndi.gaussian_filter(a.mean(2), 1.0)
    RB = ndi.gaussian_filter(a[..., 0] - a[..., 2], 1.0)
    bg = (L > bg_min) & (np.abs(RB) < 6)
    out = []
    for v in range(rows[0], rows[1], step):
        row = [float(v)]
        for s in (-1, 1):
            u = mid
            while 0 < u < L.shape[1] - run and not (bg[v, u:u + run].all() if s > 0 else bg[v, u - run + 1:u + 1].all()):
                u += s
            glaze, ground = np.median(L[v, u - s * 12:u - s * 4:s]), np.median(L[v, u + s * 2:u + s * 10:s])
            half = (glaze + ground) / 2
            xs = np.arange(u - 8, u + 9)
            line = L[v, xs]
            k = np.nonzero(np.diff(np.sign(line - half)))[0]
            if not len(k) or ground - glaze < 8:
                row.append(np.nan)
                continue
            k = k[np.argmin(np.abs(xs[k] - u))]
            row.append(float(xs[k] + (half - line[k]) / (line[k + 1] - line[k])))
        out.append(row)
    return np.array(out)


def _keep_smooth(out, tol=1):
    r = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 4), out[:, 0])
    return out[np.abs(r) < 3 * np.median(np.abs(r)) + tol]


def dark_line(a, guide, half=4, step=3, depth=15):
    """(u, v) along a thin dark painted line: per column, the darkest point within `half` px of the guide."""
    L = ndi.gaussian_filter(a.mean(2), 0.8)
    g = np.asarray(guide, float)
    out = []
    for u in range(int(g[0, 0]), int(g[-1, 0]), step):
        v0 = int(round(np.interp(u, g[:, 0], g[:, 1]))) - half
        col = L[v0:v0 + 2 * half + 1, u]
        i = int(np.argmin(col))
        if i in (0, len(col) - 1) or min(L[v0 + i - 4, u], L[v0 + i + 4, u]) - col[i] < depth:
            continue
        p, q, r = col[i - 1], col[i], col[i + 1]
        out.append((u, v0 + i + ((p - r) / (2 * (p - 2 * q + r)) if p - 2 * q + r else 0.0)))
    return _keep_smooth(np.array(out))


def clay_edge(a, guide, half=6, step=3):
    """(u, v) where clay above meets glaze below (red less blue crossing its middle), near the guide."""
    RB = ndi.gaussian_filter(a[..., 0] - a[..., 2], 1.0)
    g = np.asarray(guide, float)
    out = []
    for u in range(int(g[0, 0]), int(g[-1, 0]), step):
        vg = np.interp(u, g[:, 0], g[:, 1])
        v0 = int(round(vg)) - half - 4
        col = RB[v0:v0 + 2 * half + 9, u]
        hi, lo = np.percentile(col, 90), np.percentile(col, 10)
        s = np.sign(col - (hi + lo) / 2)
        ks = np.nonzero((s[:-1] > 0) & (s[1:] <= 0))[0]
        if not len(ks) or hi - lo < 30:
            continue
        c = ks[np.argmin(np.abs(v0 + ks - vg))]
        out.append((u, v0 + c + ((hi + lo) / 2 - col[c]) / (col[c + 1] - col[c])))
    return _keep_smooth(np.array(out))


def sift(a, box, k):
    from skimage.feature import SIFT
    g = Image.fromarray(lum(a).clip(0, 255).astype(np.uint8)).crop(box)
    g = np.asarray(g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS), dtype=np.float32) / 255
    s = SIFT(upsampling=2, n_octaves=5, c_dog=0.004)
    s.detect_and_extract(g)
    return s.keypoints[:, ::-1] / k + np.array(box[:2]), s.descriptors


def matched(a, box_a, k_a, b, box_b, k_b, tol):
    """Points matched between two photos (SIFT, kept by RANSAC on a projective map): (ua, va, ub, vb)."""
    from skimage.feature import match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    ka, da = sift(a, box_a, k_a)
    kb, db = sift(b, box_b, k_b)
    m = match_descriptors(da, db, max_ratio=0.85, cross_check=True)
    T, inl = ransac((ka[m[:, 0]], kb[m[:, 1]]), ProjectiveTransform, min_samples=4, residual_threshold=tol,
                    max_trials=5000, rng=0)
    return np.hstack([ka[m[inl, 0]], kb[m[inl, 1]]]), T


def fit_model(pJ, pL1):
    """Refit MODEL from the photos and print it (see vase_unroll.fit)."""
    J, L1 = rgb(pJ), rgb(pL1)
    s = outline_rows(L1, FIT_ROWS, FIT_MID)
    views = {"L1": dict(size=L1.shape[1::-1], band=dark_line(L1, FIT_BAND),
                        sil=[(side, r[1 + side], r[0]) for r in s for side in (0, 1) if np.isfinite(r[1 + side])]),
             "J": dict(size=J.shape[1::-1], f=FJ, crop=True, sil=[], band=[])}
    m, _ = matched(L1, FIT_MATCH, 1.0, J, (0, 0) + J.shape[1::-1], FIT_K, 25)
    x0 = [6000.0, 400.0, 0.0, 0.0, 0.0, 6000.0, 0, 0] + [900.0, 450.0, 0.25, 0.0, 0.0, FJ, 0, 0]
    x0 += [250, 255, 262, 270, 280, 292, 305, 315] + [520.0, 270.0] + [0.0]
    cams, R, ring, turns, report, _ = vu.fit(views, np.array(PROFILE_Y, float), ring={"L1": clay_edge(L1, FIT_RING)},
                                             matches={"J": m}, d0=6000.0, x_start=np.array(x0), nfev=800,
                                             outlier=8, rounds=3)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])

# ---------------------------------------------------------------- the flat

# The vase flattened without shear (vase_unroll.flatten) over FLAT_THETA x FLAT_Y (start, stop, step;
# theta in J's frame), the meridian CENTRE (his middle) straight up; G px per world unit (J's own scale
# at the front of the vase).
FLAT_THETA, FLAT_Y, CENTRE, G = (-0.22, 0.7801, 0.004), (125.0, 461.0, 3.0), 0.30, 8.3
# The slave (John, 2026-10-08: "yes, the slave on the left too") stands further round the vase. Flattened
# with the master, over the wider patch, the master moved by up to 16 flat px and every point measured on
# him would have gone off; so the slave's part is flattened on its own (FLAT_THETA_B, centred on him at
# CENTRE_B) and laid beside the master's by the rotation and shift that best fit the two flats where they
# overlap near the seam (within SEAM_FIT of it). Left of the meridian SEAM, which runs through the
# black ground between the slave's hand and the master's fingertips, the frame shows the slave's flat;
# right of it, the master's. Flat px are the master's flat's own (x may be negative: the image starts
# PAD px left of x = 0).
FLAT_THETA_B, CENTRE_B, SEAM, PAD, SEAM_FIT = (-0.74, -0.0499, 0.004), -0.45, -0.12, 1100, 0.03


def _flat(R, theta, centre):
    th, yy = np.arange(*theta), np.arange(*FLAT_Y)
    with redirect_stdout(io.StringIO()):
        XY = vu.flatten(R, th, yy, centre=centre)
    TH, Y = np.meshgrid(th, yy)
    X0, Y1 = np.nanmin(XY[..., 0]), np.nanmax(XY[..., 1])
    P = np.stack([(XY[..., 0] - X0) * G, (Y1 - XY[..., 1]) * G], -1)   # flat px
    inv = LinearNDInterpolator(P.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))
    return th, P, inv


def frame(R):
    """The master's flat (to_vase: flat px -> (theta, y)) and the slave's, laid onto it (to_vase_b)."""
    th, P, inv = _flat(R, FLAT_THETA, CENTRE)
    thb, Pb, invb = _flat(R, FLAT_THETA_B, CENTRE_B)
    # the rotation and shift that best fit the slave's flat to the master's along the seam (theta
    # within SEAM_FIT of it)
    ia = np.nonzero(np.abs(th - SEAM) <= SEAM_FIT)[0]
    ib = np.round((th[ia] - thb[0]) / FLAT_THETA_B[2]).astype(int)
    A, B = P[:, ia].reshape(-1, 2), Pb[:, ib].reshape(-1, 2)
    ok = np.isfinite(A).all(1) & np.isfinite(B).all(1)
    A, B = A[ok], B[ok]
    ma, mb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((B - mb).T @ (A - ma))
    rot = (U @ Vt).T
    fit = np.hypot(*((B - mb) @ rot.T + ma - A).T)

    # (the master's map interpolates in world units, as before the slave was added: the same flat px)
    tha, yya = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    with redirect_stdout(io.StringIO()):
        XY = vu.flatten(R, tha, yya, centre=CENTRE)
    TH, YY = np.meshgrid(tha, yya)
    X0, Y1 = np.nanmin(XY[..., 0]), np.nanmax(XY[..., 1])
    inv_w = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), YY.ravel()], -1))

    def to_vase(X, Y):
        return inv_w(np.stack([X0 + np.ravel(X) / G, Y1 - np.ravel(Y) / G], -1))

    def to_vase_b(X, Y):
        q = np.stack([np.ravel(X), np.ravel(Y)], -1).astype(float)
        return invb((q - ma) @ rot + mb)
    return dict(W=int(np.nanmax(P[..., 0])), H=int(np.nanmax(P[..., 1])), to_vase=to_vase, to_vase_b=to_vase_b,
                fit=(float(np.median(fit)), float(fit.max())))


def _lay(a, cam, R, to_vase, x_start, W, H, step=4):
    """A photo laid onto W x H flat px from x_start through its camera (black off the flat or the
    photo); also the theta of each px (NaN off the flat)."""
    gx, gy = np.meshgrid(np.arange(x_start, x_start + W + step, step), np.arange(0, H + step, step))
    ty = to_vase(gx, gy)
    good = np.isfinite(ty[:, 0])
    uv = vu.project(cam, vu.surface(R, np.where(good, ty[:, 1], 0.0), np.where(good, ty[:, 0], 0.0)))
    u = ndi.zoom(np.where(good, uv[:, 0], -1e4).reshape(gx.shape), step, order=1)[:H, :W]
    v = ndi.zoom(np.where(good, uv[:, 1], -1e4).reshape(gx.shape), step, order=1)[:H, :W]
    t = ndi.zoom(np.where(good, ty[:, 0], np.nan).reshape(gx.shape), step, order=0)[:H, :W]
    img = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1).clip(0, 255)
    return img, t


def flat_image(a, cam, R, fr):
    """The frame: the master's flat right of SEAM, the slave's left of it; column 0 is flat x = -PAD."""
    W, H = fr["W"], fr["H"]
    img_a, t_a = _lay(a, cam, R, fr["to_vase"], 0, W, H)
    img_b, t_b = _lay(a, cam, R, fr["to_vase_b"], -PAD, W + PAD, H)
    out = img_b.copy()   # (where the seam leaves a px to neither, the slave's flat fills it: ground)
    right = out[:, PAD:]
    right[:] = np.where((t_a >= SEAM)[..., None], img_a, right)
    return out


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


# ---------------------------------------------------------------- the drawing

BOX = (-720, 220, 1800, 2720)  # flat px: the slave and the master
UP = 2                         # work at 2x the flat's px, so curves stay smooth
CLAY = 22                      # red less blue, lightly blurred: his clay (and the pale, washed-out robe low
#                                on the right) is above it; the ground, black or mottled grey-green, below
# Ground: the black (darker than GROUND_L in grey, and not clay) or the grey-blue where the glaze is worn
# or the photo washed out (blue over red by more than GROUND_BR). By the clay map alone the painted lines
# where the photo is washed out (his feet, his hem: grey 110-220, red over blue by 10-25) joined the
# ground and cut his back foot off.
GROUND_L, GROUND_BR = 90, 8
AUTO_GROUND = 20000            # flat px: dark areas this large, reaching the box's edge, are ground
SEEDS = [(1200, 1400), (-200, 1440)]   # flat px: the master's robe, the slave's tunic
EDGE_R = 6                      # flat px
STRIPES, STRIPE_G = [(1030, 1500, 1140, 1980), (-290, 2000, -205, 2470)], 125
FIG_SIGMA = 2.0                 # flat px
EDGE_ZONE = 5.5                 # flat px
END_RUN = 6                     # flat px
STREAK_ANGLE, STREAK_C = 15, 36
FACE = (980, 230, 1450, 800)    # flat px: his head
# the stage's top edge (flat px, y = a + b x, fitted to its edge left of his feet): below it is the
# stage, left out, except his front foot, which stands over its edge (FOOT)
STAGE = (2565.0, -0.040)
# Under the slave the stage's edge lies lower in the flat than the master's line runs (his part is a flat of
# its own): STAGE_B (flat px, measured on the flat) runs along it from the column's foot, round the outer
# edge of his back sandal (heel, sole), up its toe to the black ground between his feet, across, and round
# his front sandal (heel, sole, toe) to the stage's edge beyond; below it is the stage. Right of
# STAGE_SPLIT the master's STAGE governs.
STAGE_B = [(-620, 2510), (-580, 2516), (-540, 2520), (-500, 2528), (-460, 2534), (-420, 2543), (-380, 2549),
           (-340, 2548), (-300, 2540), (-260, 2542), (-230, 2536), (-207, 2530), (-205, 2555), (-195, 2566),
           (-170, 2569), (-100, 2570), (-20, 2567), (4, 2562), (12, 2540), (12, 2499), (45, 2499), (46, 2520),
           (52, 2550), (62, 2575), (80, 2584), (100, 2574), (120, 2560), (140, 2550), (160, 2546), (180, 2547),
           (200, 2549), (220, 2554), (260, 2559), (300, 2563), (340, 2566), (352, 2560), (360, 2554),
           (400, 2552), (460, 2550), (550, 2548), (600, 2548)]
STAGE_SPLIT = 600
SLIVER = 5                     # flat px
# His front sandal and his right foot stand over the stage's edge, parted from it only by their painted
# lines; J's frame ends across the front sandal, about 40 flat px above its sole. FOOT closes the figure
# there along the outer edge of their lines (flat px; the outline is drawn on the lines): the front
# sandal's left side as J shows it (measured row by row), its sole from L3, and the right foot's back
# as J and L3 show it. L3 is laid on the flat by a projective map fitted to points matched with the flat
# around the feet (L3_BOX, L3_K), then moved by L3_SHIFT, the offset at which its lines best match J's
# where both show the sandal (correlation 0.71); the sole is its darkest line, measured column by
# column, and drawn along a smooth curve.
# centre points of the lines (flat px): the front sandal's left side (J), the sole (L3), the right foot's back
# (J above 2560, L3 below); each fitted with a smooth curve (x a quadratic in y; the sole y a quartic in
# x) and the figure closed along its outer edge, FOOT_HALF flat px out
FOOT_LEFT = [(1449, 2490), (1452, 2500), (1453, 2510), (1457, 2520), (1456, 2530), (1455, 2540), (1454, 2550),
             (1452, 2560), (1449, 2570), (1448, 2580), (1447, 2590), (1444, 2600), (1444, 2610), (1447, 2620)]
SOLE = [(1456, 2630), (1486, 2635), (1526, 2636), (1556, 2632), (1586, 2628), (1596, 2624), (1646, 2626),
        (1666, 2629), (1676, 2622), (1686, 2608)]
FOOT_RIGHT = [(1690, 2490), (1693, 2500), (1696, 2510), (1701, 2520), (1703, 2530), (1704, 2540), (1704, 2550),
              (1700, 2570), (1696, 2585), (1690, 2598)]
FOOT_TOP, FOOT_HALF = 2480, 1.75
L3_BOX, L3_K, L3_SHIFT = (700, 1200, 1900, 2650), 0.15, (-9, -1)
# ground seen through the figures: the black wedge between the master's front leg and his right foot; the
# black inside the slave's arm, akimbo on his hip
POCKETS = [(1590, 2470), (-460, 1110)]
# Lines: the painted lines are black on the clay, 3-8 flat px wide, but where the photo is washed out (his
# robe low on the right, his feet) only 10-20 grey levels under it. They are found by local contrast (the
# blurred photo's Maximum then Minimum over CLOSE_W flat px, less the blurred photo) with hysteresis
# (LINE_LOW, LINE_HIGH), and drawn at their own width (where the contrast is at least half the
# strongest within HALF_R flat px), never thinner than LINE_MIN flat px along their centre. The
# photo's faint horizontal streaks reach 10 at most.
LINE_LOW, LINE_HIGH, HALF_R, LINE_MIN = 12, 24, 3, 2.5
CLOSE_W = 9
# a piece of line shorter than LINE_LEN flat px (along its centre) is grain or a streak of the photo
LINE_LEN = 14
# and one shorter than SHORT_LEN whose contrast never reaches SHORT_C is grain
SHORT_LEN, SHORT_C = 40, 32
HOLE = 12                      # flat px^2: holes this small in a line are filled
MASK_SIGMA = 1.5               # flat px
SPUR, WIDTH_SIGMA = 7, 6.0     # flat px: side spurs pruned from the centre lines; width smoothing
# solid paint: the beard, the hair, the pupils. Darker than PAINT (grey, lightly blurred), in areas over
# PAINT_AREA flat px^2
PAINT, PAINT_AREA = 80, 150
PAINT_HOLE = 80                # flat px^2
PAINT_WIDE = 4                 # flat px: paint is wider than 2 x this (the lines are not)
# His hair is dark dabs over a thinner brown wash, with a rim of brown curls: drawn as a wash in the line
# colour (paths of class "tone" under the lines, as Andromache's blood) whose opacity follows the
# photo's darkness, from HAIR_A[0] where it is as light as HAIR_T[0] (grey, smoothed over HAIR_SIGMA
# flat px) to HAIR_A[1] where it is as dark as HAIR_T[1], in steps of HAIR_STEP, each step over the one
# below at the opacity that brings the total to its own (no seams). Solid black, the dabs ran into
# blots. The hair is the figure inside HAIRLINE (flat px: placed by hand along the edge of the dark mass,
# over the bald crown and forehead, round behind the ear, and out round the back of the head); no lines
# are drawn inside it. (By darkness alone it took in the forehead and its brows.)
HAIRLINE = [(1088, 200), (1092, 262), (1100, 282), (1112, 298), (1126, 314), (1136, 327), (1170, 328), (1212, 326), (1236, 332),
            (1256, 347), (1259, 365), (1250, 385), (1240, 410), (1230, 440), (1228, 470), (1232, 500), (1242, 518),
            (1265, 509), (1300, 503), (1325, 505), (1335, 522), (1343, 550), (1362, 548), (1400, 515), (1440, 496), (1490, 496), (1490, 200)]
HAIR_T, HAIR_A, HAIR_STEP, HAIR_SIGMA = (170, 45), (0.2, 0.8), 0.1, 1.5
# Breaks in the lines where the paint is worn or the photo fades (the long folds low on his robe), joined
# as trojan_women_menelaus.py joins them (join_breaks, copied with its rules): line ends facing each other
# across at most JOIN_MAX flat px (their last JOIN_RUN flat px pointing at each other within JOIN_ANGLE
# degrees), where the photo's local contrast across the gap has a median of JOIN_C or more and stays under
# JOIN_LOW for no more than JOIN_FADE flat px together, and the join crosses no other line (dots under
# JOIN_DOT flat px^2 aside); ends pointing straight at each other (within 10 degrees) across up to ALIGN_MAX,
# where the contrast's median is ALIGN_C or more, and not along the figure's edge (FAINT_EDGE)
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C, JOIN_LOW, JOIN_FADE, JOIN_DOT = 30, 6, 20, 7, 3, 5, 30
ALIGN_COS, ALIGN_C, ALIGN_MAX, FAINT_EDGE = np.cos(np.radians(10)), 4, 40, 6
EDGE = 3.5                     # flat px: the outline, drawn inside the figure's edge (the painted lines
#                                are 3-8 wide; at 2.5 it read as a halo round the figure)


def along(shape, path, width):
    """A line `width` flat px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (np.asarray(path)[:, ::-1] - 0.5).round().astype(int)
    ok = (yx[:, 0] >= 0) & (yx[:, 0] < shape[0]) & (yx[:, 1] >= 0) & (yx[:, 1] < shape[1])
    m[yx[ok, 0], yx[ok, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as oedipus_syracuse.py)."""
    from skimage import morphology
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    sk = morphology.skeletonize(m)
    s = sk.copy()
    for _ in range(spur):  # peel the ends...
        s &= ~((ndi.convolve(s.astype(int), k, mode="constant") == 1) & s)
    front = (ndi.convolve(s.astype(int), k, mode="constant") == 1) & s
    for _ in range(spur):  # ...and grow the surviving ends back
        front = ndi.binary_dilation(front, structure=np.ones((3, 3))) & sk & ~s
        s |= front
    return morphology.remove_small_objects(s, max_size=min_len, connectivity=2)


def even_lines(m, own):
    """The lines of mask m redrawn along their centres, each at the width `own` has there (the paint's
    own width), smoothed along the line over WIDTH_SIGMA flat px, at least LINE_MIN: the photo's grain
    and the brush's ragged edges made the lines lumpy."""
    from skimage import morphology
    m = morphology.remove_small_holes(m, max_size=HOLE * UP * UP)   # pinholes made rings of the centre lines
    # the mask smoothed first (blurred over MASK_SIGMA flat px in PhotoCraft, cut at half): its ragged
    # edges forked the centre lines at the ends of thick strokes, which drew drips hanging off them
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray((m * 255).astype(np.uint8)).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MASK_SIGMA * UP}))
        m = grey(Path(td) / "ms.png") >= 128
    c = centre_lines(m, spur=SPUR * UP, min_len=LINE_LEN * UP)
    w = 2 * ndi.distance_transform_edt(own)
    num, den = (ndi.gaussian_filter(a, WIDTH_SIGMA * UP) for a in (np.where(c, w, 0.0), c.astype(float)))
    half = np.where(c, np.maximum(num / np.maximum(den, 1e-6), LINE_MIN * UP) / 2, 0.0)
    d, (iy, ix) = ndi.distance_transform_edt(~c, return_indices=True)
    return d <= half[iy, ix], c, half


def find_lines(contrast, cmax, fig, origin):
    """The painted lines on the figure (LINE_* above), at their own width along their centres."""
    from skimage import morphology
    from skimage.filters import apply_hysteresis_threshold
    x0, y0 = origin
    to_edge = ndi.distance_transform_edt(fig) / UP
    # within EDGE_ZONE flat px of the edge the half-tone between clay and ground passes for a line: the
    # lines are found inside it, and those that run into it are carried on to the outline (to_outline)
    firm = apply_hysteresis_threshold(contrast, LINE_LOW, LINE_HIGH) & fig & (to_edge >= EDGE_ZONE)
    lab, n = ndi.label(firm, structure=np.ones((3, 3)))
    sk = morphology.skeletonize(firm)
    length = np.bincount(lab[sk], minlength=n + 1) / UP          # flat px of centre line per piece
    fxa, fya, fxb, fyb = FACE
    keep = np.zeros(n + 1, bool)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        p = np.argwhere(lab[sl] == k).astype(float)
        if length[k] < LINE_LEN or len(p) < 3:
            continue                                            # grain
        top = contrast[sl][lab[sl] == k].max()
        if length[k] < SHORT_LEN and top < SHORT_C:
            continue                                            # grain: short, curly and faint
        cy, cx = p.mean(0) / UP + (sl[0].start / UP + y0, sl[1].start / UP + x0)
        ax = np.linalg.eigh(np.cov(p.T))[1][:, 1]
        level = np.degrees(np.arctan2(abs(ax[0]), abs(ax[1]))) < STREAK_ANGLE
        in_face = fxa <= cx <= fxb and fya <= cy <= fyb
        keep[k] = not (level and top < STREAK_C and not in_face)
    firm &= keep[lab]
    own = firm & (contrast >= 0.5 * cmax)
    lines, c, half = even_lines(own | firm, own)
    lines = (lines | to_outline(c, half, to_edge)) & fig
    return lines | (join_breaks(lines, contrast, ndi.distance_transform_edt(fig)) & fig)


def to_outline(c, half, to_edge):
    """Each line ending within EDGE_ZONE + 2 flat px of the figure's edge, carried straight on (the
    direction of its last END_RUN flat px) until it meets the outline, at its own width."""
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere(c & (ndi.convolve(c.astype(int), k, mode="constant") == 1))
    H, W = c.shape
    out = np.zeros(c.shape, bool)
    for e in ends:
        if to_edge[tuple(e)] > EDGE_ZONE + 2:
            continue
        path, seen = [tuple(e)], {tuple(e)}
        for _ in range(END_RUN * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx)
                   and 0 <= y + dy < H and 0 <= x + dx < W and c[y + dy, x + dx] and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        if len(path) < END_RUN * UP / 2:
            continue
        d = np.array(path[0], float) - np.array(path[-1], float)
        d /= np.hypot(*d)
        q = np.array(e, float)
        for step in range(int(3 * EDGE_ZONE * UP)):
            q = q + d * 0.5
            i, j = int(round(q[0])), int(round(q[1]))
            if not (0 <= i < H and 0 <= j < W) or to_edge[i, j] <= EDGE:
                break
        else:
            continue
        seg = np.linspace(np.array(e, float), q, int(np.hypot(*(q - e))) * 2 + 2)
        m = np.zeros(c.shape, bool)
        m[seg[:, 0].round().astype(int).clip(0, H - 1), seg[:, 1].round().astype(int).clip(0, W - 1)] = True
        out |= ndi.distance_transform_edt(~m) <= half[tuple(e)]
    return out


def foot_polygon():
    """FOOT: the figure's closing below the stage's edge (flat px, a closed polygon)."""
    Lp, Sp, Rp = (np.array(v, float) for v in (FOOT_LEFT, SOLE, FOOT_RIGHT))
    kl, kr = np.polyfit(Lp[:, 1], Lp[:, 0], 2), np.polyfit(Rp[:, 1], Rp[:, 0], 2)
    ks = np.polyfit(Sp[:, 0], Sp[:, 1], 4)
    xs = np.linspace(np.polyval(kl, Sp[0, 1]), np.polyval(kr, Sp[-1, 1]), 120)
    ys_l = np.linspace(FOOT_TOP, np.polyval(ks, xs[0]), 60)
    ys_r = np.linspace(np.polyval(ks, xs[-1]), FOOT_TOP, 60)
    return np.vstack([np.c_[np.polyval(kl, ys_l) - FOOT_HALF, ys_l],
                      np.c_[xs, np.polyval(ks, xs) + FOOT_HALF],
                      np.c_[np.polyval(kr, ys_r) + FOOT_HALF, ys_r]])


def hair_mask(fig):
    x0, y0 = BOX[:2]
    return fig & lw.polygon_mask(fig.shape, (np.array(HAIRLINE, float) - (x0, y0) + 0.5) * UP - 0.5)


def add_hair(svg, hair, g, box):
    """The hair's wash (HAIR_*) added to the drawing trace_svg wrote (box: the crop box it returned)."""
    x0, y0, x1, y1 = box
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(np.where(hair, g, 0).astype(np.uint8)).save(t / "hg.png")
        Image.fromarray((hair * 255).astype(np.uint8)).save(t / "hm.png")
        for n in ("hg", "hm"):
            pc(t / f"{n}.png", t / f"{n}s.png", ("filter.blur.gaussianBlur", {"radius": HAIR_SIGMA * UP}))
        dark = grey(t / "hgs.png") / np.maximum(grey(t / "hms.png"), 1.0) * 255.0
    (t0, t1), (a0, a1) = HAIR_T, HAIR_A
    alpha = a0 + (a1 - a0) * np.clip((t0 - dark) / (t0 - t1), 0, 1)
    paths, below = "", 0.0
    for a in np.arange(a0, a1 + 1e-9, HAIR_STEP):
        m = hair & (alpha >= a - HAIR_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(lw.resample_ink(m[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


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


def main(pJ, pL1, pL3, qa=None, dump=None):
    from skimage import morphology
    from skimage.filters import apply_hysteresis_threshold
    cams, R = vase()
    fr = frame(R)
    flat = flat_image(rgb(pJ), cams["J"], R, fr)
    x0, y0, x1, y1 = BOX
    w, h = x1 - x0, y1 - y0
    td = tempfile.TemporaryDirectory()
    t = Path(td.name)
    Image.fromarray(flat.astype(np.uint8)).save(t / "flat.png")
    if dump:
        Image.fromarray(flat.astype(np.uint8)).save(str(dump) + ".flat.png")
    pc(t / "flat.png", t / "up.png",
       ("image.crop", {"x": x0 + PAD, "y": y0, "width": w, "height": h}),
       ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
    pc(t / "up.png", t / "g.png", ("image.mode.grayscale", None))
    pc(t / "up.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
       ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
    pc(t / "up.png", t / "br.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [-100, 0, 100, 0]}),
       ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
    pc(t / "g.png", t / "gp.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
    pc(t / "rb.png", t / "rbmax.png", ("filter.other.maximum", {"radius": EDGE_R * UP, "preserve": "roundness"}))
    g, rb, gp, rbmax = grey(t / "g.png"), grey(t / "rb.png"), grey(t / "gp.png"), grey(t / "rbmax.png")
    br = grey(t / "br.png")
    onphoto = grey(t / "up.png") > 0
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    fx, fy = x0 + (xx + 0.5) / UP - 0.5, y0 + (yy + 0.5) / UP - 0.5   # flat px
    a, b = STAGE
    below_b = lw.polygon_mask(g.shape, (np.array(STAGE_B + [(STAGE_SPLIT, y1 + 10), (x0 - 10, y1 + 10), (x0 - 10, STAGE_B[0][1])], float)
                                         - (x0, y0) + 0.5) * UP - 0.5)
    outside = np.where(fx < STAGE_SPLIT, below_b, fy > a + b * fx) | ~onphoto

    # ground: the dark (by the clay map) with thin lines opened away, in large areas reaching the box's
    # edge; the figure: what it leaves, from SEEDS
    dark = ((br > GROUND_BR) | ((rb <= CLAY) & (gp < GROUND_L))) & ~outside & onphoto
    dark = ndi.binary_opening(dark, structure=np.ones((4 * UP + 1, 4 * UP + 1)))
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[int((y - y0) * UP), int((x - x0) * UP)]
        assert k, f"pocket point {(x, y)} is not on dark"
        is_ground[k] = True
    ground = is_ground[lab]
    foot = lw.polygon_mask(g.shape, (foot_polygon() - (x0, y0) + 0.5) * UP - 0.5)
    outside &= ~foot
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[int((y - y0) * UP), int((x - x0) * UP)] for x, y in SEEDS}
    assert 0 not in keep
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground
    # its edge where the clay map falls to half the clay's level nearby (EDGE_R): CLAY alone put it out
    # in the blur between clay and ground, and the dark there drew a second line inside the outline
    fig &= ~((ndi.distance_transform_edt(fig) <= EDGE_R * UP) & (rb < 0.5 * rbmax) & onphoto)
    # along the master's robe's left edge and the back of the slave's calf the painter's brown stripe of
    # glaze (10-15 flat px, olive where it is worn) stays out: in STRIPES the figure is the clay
    # lighter than STRIPE_G (grey, lightly blurred)
    for sx0, sy0, sx1, sy1 in STRIPES:
        fig &= ~((fx >= sx0) & (fx < sx1) & (fy >= sy0) & (fy < sy1) & (gp < STRIPE_G))
    fig |= ndi.binary_fill_holes(fig) & ~ground        # (not the painted folds there: they are dark too)
    # slivers of the stage's clay left between the ground and the stage cut, beside the sandals, drew tails
    # off them: along the cut (within SLIVER flat px of it) only what an opening over SLIVER keeps is figure
    near_cut = ndi.distance_transform_edt(~outside) <= SLIVER * UP
    fig &= ~(near_cut & ~ndi.binary_opening(fig, structure=morphology.disk(SLIVER * UP)))
    # and smoothed along its length (the photo's grain made the outline wobble): the mask blurred over
    # FIG_SIGMA flat px in PhotoCraft and cut at half
    Image.fromarray((fig * 255).astype(np.uint8)).save(t / "fig.png")
    pc(t / "fig.png", t / "figs.png", ("filter.blur.gaussianBlur", {"radius": FIG_SIGMA * UP}))
    fig = (grey(t / "figs.png") >= 128) & ~outside
    lab, _ = ndi.label(fig)
    fig = np.isin(lab, list({lab[int((y - y0) * UP), int((x - x0) * UP)] for x, y in SEEDS}))

    # lines by local contrast, on the grey photo with everything off the figure turned white, so the
    # ground's dark makes no contrast along the figure's edge (it drew a second outline inside the first)
    # (and J's own edge: resampling darkens a rim of it, 1-3 flat px, which drew a line along it)
    inside = ndi.binary_erosion(onphoto, iterations=3 * UP)
    Image.fromarray(np.where(fig & inside, g, 255).astype(np.uint8)).save(t / "gw.png")
    pc(t / "gw.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
    r = (CLOSE_W * UP) // 2
    pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
       ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
    gl, closed = grey(t / "gl.png"), grey(t / "closed.png")
    contrast = (closed - gl).clip(0, None)
    Image.fromarray(contrast.clip(0, 255).astype(np.uint8)).save(t / "c.png")
    pc(t / "c.png", t / "cmax.png", ("filter.other.maximum", {"radius": HALF_R * UP, "preserve": "roundness"}))
    cmax = grey(t / "cmax.png")
    td.cleanup()

    lines = find_lines(contrast, cmax, fig, (x0, y0))
    paint = (gp < PAINT) & fig & onphoto
    wide = ndi.binary_opening(paint, structure=morphology.disk(PAINT_WIDE * UP))   # not the lines
    paint &= ndi.binary_dilation(wide, structure=morphology.disk(UP))
    lab, _ = ndi.label(paint)
    paint &= (np.bincount(lab.ravel()) > PAINT_AREA * UP * UP)[lab]
    paint = morphology.remove_small_holes(paint, max_size=PAINT_HOLE * UP * UP)   # specks of clay in the beard
    edge = fig & ~ndi.binary_erosion(fig, iterations=round(EDGE * UP))
    hair = hair_mask(fig)
    ink = ((lines | paint) & ~hair) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), rb=rb.astype(np.uint8), fig=fig, ground=ground,
                            outside=outside, contrast=contrast.clip(0, 255).astype(np.uint8), ink=ink)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight="own",
        title="A comic old man, the master",
        desc="Line drawing after a photo of a Sicilian red-figure calyx-krater (Louvre CA 7249), "
             "taken off the vase's curve, cut out and retraced.")
    add_hair(OUT, hair, g, info["box"])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))

if __name__ == "__main__":
    if sys.argv[1] == "--refit":
        fit_model(*sys.argv[2:4])
    else:
        main(*sys.argv[1:])
