"""Wasps: two old men in comic masks, white-haired and bearded, and a small bearded slave behind a patterned
chest between them; the right-hand old man leads the slave by the hand and holds a stick; a porch with its
door and a column at the left; all on a stage. Apulian red-figure bell-krater, J. Paul Getty Museum 96.AE.112,
attributed to the Rainone Painter, about 370 BC (the museum's record). The vase names no play and is some fifty
years later than Wasps (422 BC): two old men and a slave are stock types the play uses (Philocleon and
Bdelycleon, Xanthias), so the link is thematic only. Photos: the Getty's own (CC0, Open Content Program; IIIF
manifest https://media.getty.edu/iiif/manifest/3/b7620435-880f-4556-9695-23b32cf00339): "Main View, front" is
the drawing's source, "Left profile" and "Right profile" serve the vase's shape.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0). Two steps are
geometry, not image filtering, and stay in numpy/scipy: taking the painting off the vase's curve
(vase_unroll.py) and fitting the vase (--refit). The SVG is written by linework.trace_svg.

Photo -> flat:
  - The photos carry no focal length. The vase's profile and the three cameras were fitted together
    (MODEL): to the upper edge of the meander band under the stage (a painted circle) in all three, the
    vase's outline in all three (in the front view only the rows clear of the handles), and points of the
    painting matched between the front and each profile (SIFT). The focal length was tried at 20000,
    30000, 40000, 55000 and 80000 px (one for all three photos: they agree in distance and height, as from
    one camera stand); the fit improves up to 40000 and is flat beyond it (the cost 57279, 50412, 49387,
    49340, 49536), so FOCAL is 40000 (the profiles then turn 92 and 91 degrees from the front). The flat
    keeps the vase's rings straight and its meridians upright (see "the flat"), and the front photo is laid
    onto it at its own scale at the scene's centre.

    python3 docs/redesign/drawings/tools/wasps.py front.jpg [qa.png]
    python3 docs/redesign/drawings/tools/wasps.py front.jpg lprofile.jpg rprofile.jpg --refit
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

OUT = Path(__file__).resolve().parent.parent / "wasps.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit again; it prints these numbers).
# World units are arbitrary (the front camera's D fixes them); y = 0 on the meander band's upper edge, up.
FOCAL = 40000.0
CAMERAS = {
    "front": dict(D=10000.0, H=892.91512, b=0.06834, p=0.00122, g=0.00178, f=FOCAL, cx=3935.0, cy=4123.5),
    "lprofile": dict(D=10033.00864, H=761.59532, b=0.05429, p=0.00018, g=0.00484, f=FOCAL, cx=3935.0, cy=4123.5),
    "rprofile": dict(D=10002.68576, H=631.36487, b=0.04182, p=-0.0002, g=-0.0045, f=FOCAL, cx=3935.0, cy=4123.5),
}
PROFILE_PX = [-1100, -600, -100, 400, 900, 1400, 1900, 2400, 2900, 3100]   # knots, in front px above the band
PROFILE_R = [211.14, 389.34, 487.43, 528.18, 540.48, 540.71, 543.73, 559.11, 707.49, 863.38]
TURNS = {"lprofile": -92.19, "rprofile": 91.197}   # degrees each profile photo is turned from the front
D0 = 10000.0
# The data for fit_model: the rows (photo px) where each photo's outline is the vase's own (clear of the
# handles and the rim's lip), and rough guides to the meander band's upper edge (left and right of the handle
# in the profiles)
FIT_ROWS = {"front": [(2150, 2650), (4300, 6250)], "lprofile": [(2100, 6250)], "rprofile": [(2100, 6250)]}
FIT_BAND = {"front": [[(2350, 5090), (3000, 5135), (4000, 5135), (4800, 5140), (5450, 5100)]],
            "lprofile": [[(2150, 5050), (2500, 5075), (2850, 5090)], [(5050, 5110), (5500, 5080), (5850, 5040)]],
            "rprofile": [[(2350, 5070), (2800, 5095)], [(5050, 5100), (5500, 5060), (5850, 5020)]]}
BAND_V = 5100   # the band's row in the front photo, roughly (the profile's start)


def vase():
    k = D0 / FOCAL
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(np.array(PROFILE_PX) * k, PROFILE_R)


def outline(rgb, rows, step=25):
    """(side, u, v): the vase's outline in rows `rows` [(v0, v1)], where the grey background (no colour) meets
    the vase (dark, or coloured clay), to a fraction of a px at the half-way crossing."""
    L = ndi.gaussian_filter(rgb.mean(2), 1.0)
    vase_px = (L < 95) | (rgb.max(2) - rgb.min(2) > 30)
    out = []
    for v0, v1 in rows:
        for v in range(v0, v1 + 1, step):
            idx = np.nonzero(vase_px[v])[0]
            for side in (0, 1):
                x, s = (idx[0], 1) if side == 0 else (idx[-1], -1)
                mid = (np.median(L[v, x - 40 * s:x - 10 * s:s]) + np.median(L[v, x + 10 * s:x + 40 * s:s])) / 2
                xs = np.arange(x - 12, x + 13)
                seg = L[v, xs]
                k = np.nonzero(np.diff(np.sign(seg - mid)))[0]
                if len(k):
                    k = k[np.argmin(abs(k - 12))]
                    out.append((side, xs[k] + (mid - seg[k]) / (seg[k + 1] - seg[k]), v))
    return np.array(out)


def band_edge(rgb, rough, half=60, step=8):
    """(u, v) along the meander band's upper edge: per column near the rough guide, the step from the black
    above (R-B under 45 for 60 px) to the clay strip below, to a fraction of a px; kept where the points lie on
    one smooth curve (as acharnians.py)."""
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5)
    r = np.array(rough, float)
    f = np.polyfit(r[:, 0], r[:, 1], min(2, len(r) - 1))
    out = []
    for u in range(int(r[0, 0]), int(r[-1, 0]), step):
        vg, col, best = int(np.polyval(f, u)), RB[:, u], None
        for v in range(vg - half, vg + half):
            above, below = col[v - 60:v - 4].mean(), col[v + 3:v + 17].mean()
            if above < 45 and below > 85 and col[v - 60:v - 4].max() < 80 and (best is None or below - above > best[0]):
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


def fit_model(photos: dict) -> None:
    """Refit MODEL from the three photos at FOCAL and print it (see vase_unroll.fit). Needs opencv for SIFT."""
    import cv2
    names = ["front", "lprofile", "rprofile"]
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

    kf, df = feats("front", 0.35, (1700, 2300, 6200, 5500))
    matches = {}
    uc, rr = 3930.0, 2160.0   # the vase's axis and radius in the front photo, roughly
    for n, turn in (("lprofile", -97.5), ("rprofile", 97.5)):
        kn, dn = feats(n, 0.35, (1500, 2300, 6400, 5500))
        good = [a for a, b in cv2.BFMatcher(cv2.NORM_L2).knnMatch(df, dn, k=2) if a.distance < 0.8 * b.distance]
        a, b = np.float32([kf[x.queryIdx] for x in good]), np.float32([kn[x.trainIdx] for x in good])
        # keep the matches a turn of about `turn` explains (on a cylinder); the epipolar test passes any
        # match at the same height, as this turntable's lines are level
        d = np.degrees(np.arcsin(np.clip((b[:, 0] - uc) / rr, -1, 1)) - np.arcsin(np.clip((a[:, 0] - uc) / rr, -1, 1)))
        matches[n] = np.hstack([a, b])[np.abs(d - turn) < 12]
    views = {}
    for n in names:
        band = np.vstack([band_edge(rgb[n], g) for g in FIT_BAND[n]])
        views[n] = dict(size=rgb[n].shape[1::-1], sil=[tuple(r) for r in outline(rgb[n], FIT_ROWS[n])], band=band)
    k = D0 / FOCAL
    knots = np.array(PROFILE_PX, float) * k
    s = outline(rgb["lprofile"], FIT_ROWS["lprofile"])
    left, right = s[s[:, 0] == 0], s[s[:, 0] == 1]
    hw = (np.interp(left[:, 2], right[:, 2], right[:, 1]) - left[:, 1]) / 2
    x0 = []
    for n in names:
        x0 += [D0, (BAND_V - 4124) * k, 0.0, 0.0, 0.0, FOCAL, 0.0, 0.0]
    x0 += list(np.interp(PROFILE_PX, (BAND_V - left[::-1, 2]), hw[::-1]) * k) + [0.0, 0.0]
    x0 += [np.radians(-97.5), np.radians(97.5)]
    cams, R, _, turns, report, _ = vu.fit(views, knots, matches=matches, f_px=FOCAL, d0=D0, rounds=3,
                                          outlier=30, nfev=1500, x_start=np.array(x0))
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{q}={c[q]:.6g}" for q in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 2) for y in knots])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})

# ---------------------------------------------------------------- the flat

# The scene wraps about 130 degrees round the vase, and the body tapers just above the stage. The shear-free
# flat (vase_unroll.flatten) cannot lay a tapering band out straight: it bowed the plank into an arc and fanned
# the door and the right-hand man outward. So the flat keeps the vase's rings straight and its meridians upright
# (John's choice, 2026-10-10, shown both): x = R_C (theta - theta_C), y = the arc length up the profile, where
# R_C is the radius at CENTRE (a front-photo point at the scene's middle, the slave's chest). No shear: the grid
# stays square, as on the vase. Lengths up the vase and round it at R_C are true; lower down, where the vase is
# narrower, round it is widened by R_C / R (up to about 5% at the feet). G px per world unit is the front
# photo's own scale at CENTRE. The frame is the flat image of the front-photo box BOX, MARGIN units wider.
FLAT_Y = (-60.0, 760.0)
CENTRE, BOX, MARGIN = (4300.0, 3700.0), (1960, 2340, 5890, 4850), 10.0


def frame():
    """(cams, R, theta_C, R_C, arc table (y, t), X0, Y1, G, W, H)."""
    cams, R = vase()
    c = cams["front"]
    t0 = vu.photo_to_surface(c, R, np.array([CENTRE]), FLAT_Y)[0]
    P = vu.project(c, vu.surface(R, np.array([t0[1], t0[1] + 1.0]), np.array([t0[0], t0[0]])))
    G = float(np.hypot(*(P[1] - P[0])))
    rc = float(R(t0[1]))
    yt, tt = vu.arc_table(R, *FLAT_Y)
    x0, y0, x1, y1 = BOX
    s = np.linspace(0, 1, 40)
    edge = np.vstack([np.c_[x0 + s * (x1 - x0), np.full(40, y0)], np.c_[x0 + s * (x1 - x0), np.full(40, y1)],
                      np.c_[np.full(40, x0), y0 + s * (y1 - y0)], np.c_[np.full(40, x1), y0 + s * (y1 - y0)]])
    cr = vu.photo_to_surface(c, R, edge, FLAT_Y)
    fx, fy = rc * (cr[:, 0] - t0[0]), np.interp(cr[:, 1], yt, tt)
    X0, X1, Y0, Y1 = fx.min() - MARGIN, fx.max() + MARGIN, fy.min() - MARGIN, fy.max() + MARGIN
    return cams, R, float(t0[0]), rc, (yt, tt), X0, Y1, G, int((X1 - X0) * G), int((Y1 - Y0) * G)


def flat_image(src):
    """The front photo laid onto the flat frame (H x W x 3, uint8)."""
    cams, R, th0, rc, (yt, tt), X0, Y1, G, W, H = frame()
    gx, gy = np.meshgrid(np.arange(W), np.arange(H))
    th = th0 + (X0 + gx / G) / rc
    y = np.interp(Y1 - gy / G, tt, yt)
    uv = vu.project(cams["front"], vu.surface(R, y.ravel(), th.ravel())).reshape(gx.shape + (2,))
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [uv[..., 1], uv[..., 0]], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


if __name__ == "__main__":
    if "--refit" in sys.argv:
        fit_model(dict(zip(["front", "lprofile", "rprofile"], sys.argv[1:4])))
    elif "--flat" in sys.argv:
        Image.fromarray(flat_image(sys.argv[1])).save(sys.argv[2])
