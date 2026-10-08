"""Clouds: a comic old man, the master, in a long chiton and a himation drawn up over his shoulder, a
bearded mask with curly hair, his right arm stretched out, from the phlyax scene on side A of a Sicilian
red-figure calyx-krater, Lentini-Manfria Group, c. 350-340 BC, Paris, Louvre CA 7249 (bought 1986).
The vase does not show Clouds: the master is the type of Strepsiades. His slave at the left (a short
tunic, the costume phallus), the stage under them, the door, the woman and the black ground are left out.

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


def frame(R):
    th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    with redirect_stdout(io.StringIO()):
        XY = vu.flatten(R, th, yy, centre=CENTRE)
    TH, Y = np.meshgrid(th, yy)
    X0, X1 = np.nanmin(XY[..., 0]), np.nanmax(XY[..., 0])
    Y0, Y1 = np.nanmin(XY[..., 1]), np.nanmax(XY[..., 1])
    inv = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))

    def to_vase(X, Y):
        return inv(np.stack([X0 + np.ravel(X) / G, Y1 - np.ravel(Y) / G], -1))
    return dict(W=int((X1 - X0) * G), H=int((Y1 - Y0) * G), to_vase=to_vase)


def flat_image(a, cam, R, fr, step=4):
    """A photo laid onto the frame through its camera (black off the flat or off the photo)."""
    W, H = fr["W"], fr["H"]
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    ty = fr["to_vase"](gx, gy)
    good = np.isfinite(ty[:, 0])
    uv = vu.project(cam, vu.surface(R, np.where(good, ty[:, 1], 0.0), np.where(good, ty[:, 0], 0.0)))
    u = ndi.zoom(np.where(good, uv[:, 0], -1e4).reshape(gx.shape), step, order=1)[:H, :W]
    v = ndi.zoom(np.where(good, uv[:, 1], -1e4).reshape(gx.shape), step, order=1)[:H, :W]
    return np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1).clip(0, 255)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def main(pJ, pL1, pL3, qa=None, dump=None):
    cams, R = vase()
    fr = frame(R)
    flat = flat_image(rgb(pJ), cams["J"], R, fr)
    if dump:
        Image.fromarray(flat.astype(np.uint8)).save(dump)


if __name__ == "__main__":
    if sys.argv[1] == "--refit":
        fit_model(*sys.argv[2:4])
    else:
        main(*sys.argv[1:])
