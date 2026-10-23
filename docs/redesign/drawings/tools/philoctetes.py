"""Philoctetes: Philoctetes alone on Lemnos, seated on a rock under a tree, his
bandaged leg drawn up, his bow case at his feet, from the Attic red-figure
squat lekythos in the manner of the Eretria Painter (Bothmer; BAPD 10931),
c. 420 BCE, New York, Metropolitan Museum of Art 56.171.58 (Fletcher Fund,
1956). Photos: Marie-Lan Nguyen, 2011, CC BY 2.5 ("C", the
closest, the drawing's main source), and the Met's two Open Access photos,
CC0 ("A", DP165159, and "B", DP165160):
https://commons.wikimedia.org/wiki/File:Philoktetes_Lemnos_Met_56.171.58.jpg
https://images.metmuseum.org/CRDImages/gr/original/DP165159.jpg
https://images.metmuseum.org/CRDImages/gr/original/DP165160.jpg
The drawing traces only the ancient painting, which is public domain, so it
does not carry the photos' licences (John's ruling on Oedipus Tyrannus,
2026-10-02; on this drawing: "Don't care about license"); the photographers
are credited.

Redrawn with PhotoCraft (2026-10-09; John: "The photocraft method is so good,
that these earlier ones are looking not good"). The first drawing's tool
(2026-10-03, in git history) set the geometry, which is kept as John approved
it: the vase model and the flat, the cut-out (the tree cut, the windows, the
damage in the glaze), the rock's black lines only. Its lines are found anew.

Photo -> flat (vase_unroll.py; geometry, so numpy and scipy, not PhotoCraft):
  - The vase is taken off its curve (vase_unroll.py, as for Euphorbos and
    Antigone). Its profile and the cameras of C, A and B were fitted together
    (MODEL): to the outline of the vase in A and B, the upper edge of the
    dark line under the scene (painted on the wheel, so a circle) in all
    three, and points of the painting matched between C and the other two.
    C's focal length is fixed from its EXIF (50 mm on a Nikon D300S, 4288 px
    across 23.6 mm) and its centre fitted (the file is a crop). A and B have
    no EXIF; their focal length is fitted (about 14,500 px), and fixed
    anywhere from 9,000 to 34,000 px it moves the flat figure by 2-3 px.
  - The scene wraps 150 degrees round the vase, and the photos all face the
    same side: his raised leg and feet lie 40-70 degrees round from C, the
    rock's left end about 80. The flat (flat_keep) covers the scene alone,
    which keeps every part within 3% of the vase's own lengths.
  - C is the sharpest photo in the middle of the scene; A is sharper toward
    the sides (C is out of focus there and does not reach the rock's left
    end). Each part is taken from the sharper photo (SEAMS), the two laid
    together with numpy before PhotoCraft sees them. On the flat the two
    agree to 1-2 px in the middle; toward the rock's left end C drifts off
    A, 3-5 px across the seam and 6-7 px past it.

Flat -> drawing: every image step runs in PhotoCraft (`photocraft-cli` 0.2.0):
the grey, the clay map (Channel Mixer, red less blue), the blurs, the Maximum
and Minimum filters (local contrast, and the clay level round each pixel).
numpy only combines PhotoCraft's maps and measures. The SVG is written by
linework.trace_svg.
  - The scene is him, the rock he sits on and his bow case: one clay area.
    The tree is cut off where its trunk meets the rock (TREE_CUT). The black
    ground seen through the scene (WINDOWS) stays open in the dark theme;
    the two between his legs are drawn black on the light page too.
  - Painted lines by local contrast (the grey's Maximum then Minimum, less
    the grey), which passes over the broad brown washes, drawn along their
    centres at their own width, smoothed along the line (as clouds.py). On
    the rock only black lines (ROCK); on the bow, the case and the straps
    all of them (GEAR).
  - His hair and beard are brown wash over the clay, with darker strokes for
    the curls: drawn as a wash in the line colour whose opacity follows the
    photo's darkness, in steps, so the brushstrokes show (John, 2026-10-09:
    "do the brown curly hair and beard as brushstrokes, similar to how we did
    hair in other plates"; as Clouds' hair).
  - John's traces of the head, feet and hands for the first drawing
    (philoctetes_traces.json, frame px) are the check for the new lines
    there: `--traces out.png` draws them over the new drawing.

    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg [qa.png]
    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg --refit
    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg --traces out.png
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline, LinearNDInterpolator, RegularGridInterpolator
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

OUT = Path(__file__).resolve().parent.parent / "philoctetes.svg"
# the drawing levelled by its ground line (John, 2026-10-22): turned by LEVEL degrees about LEVEL_C, its view box cut
# to LEVEL_VIEW so no corner of the turn shows
LEVEL, LEVEL_C, LEVEL_VIEW = 0.801, (641, 500), "-5 6 1281 985"


# (from the photo Euphorbos tool, retired 2026-10-12, which this tool imported it from)
def strokes(L, paths, w, snap):
    """Hand-placed strokes, each snapped to the darkest line within `snap` px
    of its points, smoothed, and drawn as an even line w px wide."""
    from skimage.draw import line
    xs = [x for p in paths for x, _ in p]
    ys = [y for p in paths for _, y in p]
    x0, y0 = int(max(min(xs) - 30, 0)), int(max(min(ys) - 30, 0))
    x1, y1 = int(min(max(xs) + 30, L.shape[1])), int(min(max(ys) + 30, L.shape[0]))
    sub = ndi.gaussian_filter(L[y0:y1, x0:x1], 1.5)
    centre = np.zeros(sub.shape, bool)
    for pts in paths:
        pts = [(round(x - x0), round(y - y0)) for x, y in pts]
        rough = np.zeros(sub.shape, bool)
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            rr, cc = line(ya, xa, yb, xb)
            rough[rr, cc] = True
        near = ndi.distance_transform_edt(~rough) <= snap
        xy = lw.livewire(np.where(near, 1.0 + sub / 8.0, 1e4), pts)
        if len(xy) > 9:  # a running mean evens out the pixel steps; the ends stay put
            k = 7
            sm = np.vstack([np.convolve(np.pad(xy[:, i], k // 2, mode="edge"), np.ones(k) / k, mode="valid")
                            for i in (0, 1)]).T
            sm[0], sm[-1] = xy[0], xy[-1]
            xy = sm
        for (xa, ya), (xb, yb) in zip(xy[:-1], xy[1:]):
            rr, cc = line(int(ya), int(xa), int(yb), int(xb))
            ok = (rr >= 0) & (rr < sub.shape[0]) & (cc >= 0) & (cc < sub.shape[1])
            centre[rr[ok], cc[ok]] = True
    out = np.zeros(L.shape, bool)
    out[y0:y1, x0:x1] = ndi.distance_transform_edt(~centre) <= w / 2
    return out


# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit
# again; it prints these numbers). World units are arbitrary (C's D fixes
# them; about A's pixels); y = 0 on the upper edge of the dark line under the
# scene, up the vase; theta = 0 faces C.
CAMERAS = {
    "C": dict(D=6300, H=1117.49, b=-0.0115667, p=0.00362706, g=-0.0153902, f=9084.75, cx=1069.26, cy=462.778),
    "A": dict(D=14268.1, H=3804.57, b=0.198857, p=-1.68011e-05, g=0.00291606, f=14218.5, cx=2000, cy=2000),
    "B": dict(D=14400.3, H=3896.62, b=0.203658, p=-0.000326597, g=0.00446153, f=13610, cx=1895.5, cy=1896),
}
PROFILE_Y = [-150, 40, 230, 420, 610, 800, 990, 1180, 1340, 1500]
PROFILE_R = [690.0, 734.2, 754.0, 761.5, 756.1, 746.8, 724.9, 688.5, 628.6, 568.6]
TURNS = {"A": 3.362, "B": -7.298}  # degrees each photo is turned from C
FC = 50.0 * 4288 / 23.6  # px: C's focal length over the D300S's pixel pitch
# The data for fit_model: the rows of A's and B's outline (clear of the
# shoulder's steepest part and of the foot), rough guides to the dark line
# under the scene (three points on it, joined by a parabola, searched 40 px
# either side) and the columns searched, and the boxes where points are
# matched (C whole, at 0.6 of its size, to A and B at their own).
FIT_ROWS = {"A": (1590, 3160), "B": (1590, 3000)}
FIT_BAND = {"A": [(1500, 3012.5), (2000, 3070.5), (2500, 3017.5)],
            "B": [(1500, 2867.5), (1950, 2905.5), (2400, 2838.5)],
            "C": [(300, 2346.5), (1075, 2394.5), (1800, 2352.5)]}
FIT_SPAN = {"A": (1330, 2680), "B": (1250, 2620), "C": (30, 2100)}
FIT_MATCH = {"A": (1250, 1550, 2750, 3150), "B": (1150, 1500, 2650, 3050)}


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def band_top(rgb, guide, span, half=40, step=6):
    """(u, v) along the upper edge of the dark line under the scene (clay above,
    glaze below): per column, the crossing nearest the guide, kept where the
    points lie on one smooth curve."""
    g = np.asarray(guide, float)
    k = np.polyfit(g[:, 0], g[:, 1], 2)
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.0)
    out = []
    for u in range(span[0], span[1], step):
        vg = np.polyval(k, u)
        v0, v1 = max(int(vg) - half, 0), min(int(vg) + half, rgb.shape[0] - 1)
        col = RB[v0:v1, u]
        mid = 0.5 * (np.percentile(col, 90) + np.percentile(col, 10))
        s = np.sign(col - mid)
        ks = np.nonzero((s[:-1] > 0) & (s[1:] <= 0))[0]  # clay -> glaze, going down
        if not len(ks):
            continue
        c = ks[np.argmin(np.abs(v0 + ks - vg))]
        if c < 6 or c + 7 > len(col) or not (col[c - 6:c - 1] > mid).all() or not (col[c + 2:c + 7] < mid).all():
            continue
        out.append((u, v0 + c + (mid - col[c]) / (col[c + 1] - col[c])))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 4), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 2]


def fit_model(photos: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit)."""
    from skimage.feature import SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in "CAB"}
    views = {"C": dict(size=rgb["C"].shape[1::-1], f=FC, crop=True, sil=[],
                       band=band_top(rgb["C"], FIT_BAND["C"], FIT_SPAN["C"]))}
    for n in "AB":
        img = rgb[n][:-2, :-2]  # the photos' last rows and columns are a border (B's dark, A's light)
        s = vu.silhouette(img, *FIT_ROWS[n], step=8)
        views[n] = dict(size=rgb[n].shape[1::-1], band=band_top(rgb[n], FIT_BAND[n], FIT_SPAN[n]),
                        sil=[(side, r[1 + side], r[0]) for r in s for side in (0, 1) if np.isfinite(r[1 + side])])

    def feats(a, box, k):
        g = Image.fromarray(lum(a).clip(0, 255).astype(np.uint8)).crop(box)
        g = np.asarray(g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS), dtype=np.float32) / 255
        s = SIFT(upsampling=1, n_octaves=5, c_dog=0.006)
        s.detect_and_extract(g)
        return s.keypoints[:, ::-1] / k + np.array(box[:2]), s.descriptors

    kc, dc = feats(rgb["C"], (0, 0) + rgb["C"].shape[1::-1], 0.6)
    matches = {}
    for n, box in FIT_MATCH.items():
        kn, dn = feats(rgb[n], box, 1.0)
        m = match_descriptors(dc, dn, max_ratio=0.8, cross_check=True)
        _, inl = ransac((kc[m[:, 0]], kn[m[:, 1]]), ProjectiveTransform, min_samples=4, residual_threshold=40,
                        max_trials=5000, rng=0)
        matches[n] = np.hstack([kc[m[inl, 0]], kn[m[inl, 1]]])
    x0 = [6300.0, 600.0, 0.0, 0.0, 0.0, FC, 0.0, 0.0]
    for _ in "AB":
        x0 += [15450.0, 3900.0, 0.18, 0.0, 0.0, 15000.0, 0.0, 0.0]
    x0 += [575.0, 665.0, 711.0, 731.0, 739.0, 735.0, 726.0, 703.0, 668.0, 600.0] + [0.0, 0.0] + [0.0, 0.0]
    cams, R, _, turns, report, _ = vu.fit(views, np.array(PROFILE_Y, float), matches=matches, d0=6300.0,
                                          x_start=np.array(x0), nfev=600, outlier=25, rounds=3)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


# ---------------------------------------------------------------- the flat

# The vase flattened without shear (vase_unroll.flatten) over FLAT_THETA x
# FLAT_Y (start, stop, step), only where flat_keep holds: everything up to his
# knee, and above it the band that holds his arms and head (the tree above is
# not drawn). Flattening the whole rectangle would leave his head 5% wider at
# the top than the vase has it; this keeps every part within 3%. The meridian
# CENTRE (facing C) runs straight up; G px per world unit (C's own scale at
# the vase's front). The frame is the flat image of BOX_THETA x BOX_Y.
FLAT_THETA, FLAT_Y = (-1.56, 1.4501, 0.008), (-150.0, 1470.1, 8.0)
BOX_THETA, BOX_Y, CENTRE, G = (-1.50, 1.27), (-70.0, 1440.0), 0.0, 1.637


def flat_keep(t, y):
    return (y <= 950) | ((t >= -0.45) & (t <= 0.85) & (y <= 1390))


def frame(R):
    """The frame: its size, and maps between frame px and the vase (theta, y)."""
    th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    with redirect_stdout(io.StringIO()):
        XY = vu.flatten(R, th, yy, keep=flat_keep, centre=CENTRE)
    TH, Y = np.meshgrid(th, yy)
    ok = np.isfinite(XY[..., 0])
    inv = LinearNDInterpolator(XY[ok], np.stack([TH[ok], Y[ok]], -1))
    fwd = [RegularGridInterpolator((yy, th), XY[..., k], bounds_error=False) for k in (0, 1)]
    # the box's edges, where the flat holds them (top: just inside flat_keep's band)
    tb, yb = np.linspace(*BOX_THETA, 300), np.linspace(*BOX_Y, 300)
    edge = np.vstack([np.c_[np.full(300, BOX_Y[0]), tb], np.c_[np.full(300, 940.0), tb],
                      np.c_[np.full(300, 1380.0), np.linspace(-0.44, 0.84, 300)],
                      np.c_[yb, np.full(300, BOX_THETA[0])], np.c_[yb, np.full(300, BOX_THETA[1])]])
    fx, fy = fwd[0](edge), fwd[1](edge)
    X0, X1, Y0, Y1 = np.nanmin(fx), np.nanmax(fx), np.nanmin(fy), np.nanmax(fy)

    def to_vase(X, Y):
        return inv(np.stack([X0 + np.ravel(X) / G, Y1 - np.ravel(Y) / G], -1))  # (theta, y); NaN off the flat

    def to_frame(theta, y):
        q = np.c_[np.ravel(y), np.ravel(theta)]
        return np.c_[(fwd[0](q) - X0) * G, (Y1 - fwd[1](q)) * G]
    return dict(W=int((X1 - X0) * G), H=int((Y1 - Y0) * G), to_vase=to_vase, to_frame=to_frame)


def flat_image(photo, name, R, fr, step=4):
    """A photo laid onto the frame through its own camera (black off the flat,
    off the photo, or on the vase's far side)."""
    cams, _ = vase()
    cam, phi = cams[name], np.radians(TURNS.get(name, 0.0))
    W, H = fr["W"], fr["H"]
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    ty = fr["to_vase"](gx, gy)
    good = np.isfinite(ty[:, 0])
    t, y = np.where(good, ty[:, 0], 0.0), np.where(good, ty[:, 1], 0.0)
    P = vu.surface(R, y, t + phi)
    uv = vu.project(cam, P)
    nrm = np.stack([np.sin(t + phi), -R(y, 1), np.cos(t + phi)], -1)
    facing = np.einsum("ij,ij->i", nrm, np.array([0.0, cam["H"], cam["D"]]) - P) > 0
    ok = (good & facing).reshape(gx.shape)
    u = ndi.zoom(np.where(ok, uv[:, 0].reshape(gx.shape), -1e4), step, order=1)[:H, :W]
    v = ndi.zoom(np.where(ok, uv[:, 1].reshape(gx.shape), -1e4), step, order=1)[:H, :W]
    a = np.asarray(Image.open(photo).convert("RGB"), dtype=np.float32)
    return np.stack([ndi.map_coordinates(a[..., k], [v, u], order=1, cval=0) for k in range(3)], -1)


# ---------------------------------------------------------------- PhotoCraft

def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


# Each part from the sharper photo: C between the SEAMS (frame columns), A
# outside them, blended across each seam's span. (C is out of focus toward
# both sides and does not reach the rock's left end.)
SEAMS = ((950, 1100), (2300, 2450))
# The local contrast of a line: the grey (blurred 1 px) closed by PhotoCraft's
# Maximum then Minimum over CLOSE_R px, less the grey. The clay level round a
# pixel: the grey closed over CLAY_R px and blurred CLAY_BLUR px (darkness
# ratios are the grey over it); the wide one (A's grey, WIDE_R, WIDE_BLUR) for
# black paint wider than the narrow window.
CLOSE_R, CLAY_R, CLAY_BLUR, WIDE_R, WIDE_BLUR = 6, 12, 4, 40, 10


def seam_weight(rgbC):
    """C's weight in each pixel (A has the rest)."""
    x = np.arange(rgbC.shape[1], dtype=float)
    (a0, a1), (b0, b1) = SEAMS
    w = np.clip((x - a0) / (a1 - a0), 0, 1) * np.clip((b1 - x) / (b1 - b0), 0, 1)
    return w[None, :] * (ndi.binary_erosion(rgbC.max(2) > 3, iterations=8))


def maps(rgbC, rgbA):
    """PhotoCraft's maps of the frame. From A (no glare on the glaze, so the
    colours): LA, its grey blurred 1 px; RBA, red less blue blurred 1 px; rA,
    LA over the wide clay level. From the blend of C and A (the sharper photo
    in each part): g, its grey; gf, blurred 1 px; contrast, gf closed over
    CLOSE_R less gf; r, gf over the clay level; rW, gf over the wide one; RB,
    red less blue blurred 1 px."""
    wC = seam_weight(rgbC)[..., None]
    blend = (wC * rgbC + (1 - wC) * rgbA).clip(0, 255).round().astype(np.uint8)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rgbA.clip(0, 255).round().astype(np.uint8)).save(t / "A.png")
        Image.fromarray(blend).save(t / "F.png")
        pc(t / "A.png", t / "LA.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "A.png", t / "RBA.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "LA.png", t / "clayA.png", ("filter.other.maximum", {"radius": WIDE_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": WIDE_R, "preserve": "squareness"}),
           ("filter.blur.gaussianBlur", {"radius": WIDE_BLUR}))
        pc(t / "F.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "F.png", t / "RB.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "g.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "gf.png", t / "clayW.png", ("filter.other.maximum", {"radius": WIDE_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": WIDE_R, "preserve": "squareness"}),
           ("filter.blur.gaussianBlur", {"radius": WIDE_BLUR}))
        pc(t / "gf.png", t / "cl.png", ("filter.other.maximum", {"radius": CLOSE_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": CLOSE_R, "preserve": "squareness"}))
        pc(t / "gf.png", t / "clay.png", ("filter.other.maximum", {"radius": CLAY_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": CLAY_R, "preserve": "squareness"}),
           ("filter.blur.gaussianBlur", {"radius": CLAY_BLUR}))
        m = {k: grey(t / f"{k}.png") for k in ("LA", "RBA", "clayA", "g", "gf", "cl", "clay", "clayW", "RB")}
    m["contrast"] = m["cl"] - m["gf"]
    m["r"] = m["gf"] / np.maximum(m["clay"], 1.0)
    m["rA"] = m["LA"] / np.maximum(m["clayA"], 1.0)
    m["rW"] = m["gf"] / np.maximum(m["clayW"], 1.0)
    m["LAn"] = m["LA"] / 100.0   # A's grey on the ratios' scale (for the black top of his head)
    return m


# ---------------------------------------------------------------- the scene

# Colour classes, in A: clay is redder than CLAY_RB (red minus blue) and
# lighter than CLAY_L; glaze is less red than GLAZE_RB and darker than GLAZE_L;
# between them, the brown washes. Pale grey (less red than PALE_RB, lighter
# than PALE_L) is a scratch or a chip in the glaze, and counts as glaze.
CLAY_RB, CLAY_L, GLAZE_RB, GLAZE_L, PALE_RB, PALE_L = 75, 120, 28, 70, 30, 60
SEED = (2000, 900)  # on his chiton (frame px): the scene is the clay joined to it
# The tree: its trunk widens into the rock where his right hand rests. A
# thin painted line marks the rock's top under it: the washes that model the
# rock start below that line, and the clay above it is the trunk. The tree is
# cut off by TREE_CUT (frame px): from the black ground (straight, a little
# above where the rock's top line meets the trunk's edge, so the two lines
# do not run together into a blot) along the rock's top line (a least-cost
# path held near the points) to his fingertips, straight
# across the open tips of his middle and index fingers (nothing is painted
# there), then along the top of his hand (the painted line) to his wrist and
# into the black between the trunk and his arm.
TREE_CUT = [(790, 1584), lw.STRAIGHT, (828, 1575), (845, 1545), (852, 1520), (875, 1490), (900, 1460), (933, 1428),
            (975, 1396), (1025, 1374), (1062, 1368), lw.STRAIGHT, (1083, 1343), lw.STRAIGHT, (1127, 1283),
            (1147, 1260), (1170, 1240), (1193, 1232), (1220, 1223), (1253, 1220), lw.STRAIGHT, (1275, 1195)]
TREE_CORRIDOR = 8
# The black ground seen through the scene (a point in each): between his
# right arm, his body and the rock; between his left arm and his body;
# between his hanging leg and the rock; under his raised foot; and a sliver
# where the rock's left end meets the ground line. These stay open; every
# other black area inside the scene is paint (the top of his head, the bow
# case's black, the broad stroke down the back of his raised calf, which is
# browner than the ground and shows the brush; John, 2026-10-03, marked it
# black).
WINDOWS = [(1635, 1256), (2213, 1024), (2490, 1804), (2857, 1902), (147, 2399)]
# The two between his legs (between his hanging leg and the rock, under his
# raised foot) are drawn black, on the light page too (John, 2026-10-03:
# "Fill those in with black. They look weird not black in day mode."); the
# two by his arms stay open there (he chose that over drawing them black).
BLACK_WINDOWS = [(2490, 1804), (2857, 1902)]
# Along the figure's edge the glaze is a little browner and lighter than the
# rest (the painter's contour stripe, 3-15 px wide), and the colour test
# leaves it to the figure, whose edge then follows the stripe's ragged outer
# side instead of the clay's crisp one. The ground takes in paint darker than
# STRIPE_L within STRIPE_REACH px of it (an opening of STRIPE_OPEN px keeps
# out painted lines that touch it), except in his head (HEAD), where the
# curls of his hair and beard reach the edge, and along the black strokes
# that outline his feet (BLACK_BANDS), which are paint, not stripe.
# Where a window narrows to less than 2 * WINDOW_OPEN px (down along his heel),
# it is drawn as black paint, not as two outlines with a sliver between.
STRIPE_L, STRIPE_REACH, STRIPE_OPEN, WINDOW_OPEN = 55, 40, 4, 6
# Where the stripe is too narrow for that opening, or the photo soft (A sees
# the right end of the rock at 60 degrees), the edge is drawn in to the
# midpoint between clay and glaze: paint darker than SOFT_L within SOFT_REACH
# px of the ground (not along the ground line, where his toes stand on it).
SOFT_L, SOFT_REACH = 75, 10
HEAD = [(1800, 470), (1815, 380), (1850, 300), (1930, 240), (2000, 160), (2150, 140), (2330, 190), (2400, 330),
        (2380, 450), (2300, 520), (2280, 640), (2200, 700), (2070, 700), (2010, 690), (1960, 645), (1920, 595),
        (1870, 550), (1820, 520)]
# Damage in the glaze, counted as ground (GLAZE_DAMAGE): a patch abraded
# against his right arm, where pale clay shows through in flecks (its right
# side along the arm's own edge, measured on A, 3 px out); and a scratch in
# the black between his arm and his body, whose brownish halo in A would
# join the arm. Left of LEFT_X, past the rock's left end, A sees the vase
# edge-on and blurred; that is ground too.
GLAZE_DAMAGE = [
    [(1380, 820), (1535, 820), (1523, 840), (1528, 860), (1529, 880), (1529, 900), (1522, 920), (1500, 940),
     (1475, 960), (1461, 980), (1447, 1000), (1430, 1020), (1424, 1040), (1380, 1040)],
    [(1632, 1070), (1650, 1062), (1675, 1075), (1700, 1092), (1722, 1112), (1722, 1145), (1690, 1150), (1660, 1130),
     (1638, 1110), (1632, 1095)],
]
LEFT_X = 98
# The scene's edges: specks under EDGE_R px are opened and closed away, and
# each outline (the scene's and each window's) is smoothed along its own
# length (EDGE_SIGMA px of arc). Where the glaze meets the rock's left side it
# is chipped and the edge bites in and out by 10-20 px: inside WORN it is
# smoothed over WORN_SIGMA px. His head (HEAD) keeps its edge as found (the
# curls, the profile of his face).
EDGE_R, EDGE_SIGMA = 4, 9.0
WORN, WORN_SIGMA = [(560, 1700), (830, 1700), (830, 2000), (560, 2120), (360, 2120), (360, 1960)], 15.0


def classes(m):
    """Glaze and clay, from A's PhotoCraft maps."""
    L, RB = m["LA"], m["RBA"]
    glaze = ((RB < GLAZE_RB) & (L < GLAZE_L)) | (L < 2)  # black off the flat counts as ground
    glaze |= (RB < PALE_RB) & (L > PALE_L)
    clay = (RB > CLAY_RB) & (L > CLAY_L)
    return glaze, clay


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(pts, float))


def trace_line(shape, pts):
    """A polyline through pts, 1 px wide."""
    from skimage.draw import line
    m = np.zeros(shape, bool)
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        rr, cc = line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
        ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
        m[rr[ok], cc[ok]] = True
    return m


def cut_path(gf, pts, corridor=6):
    """A least-cost path through pts (STRAIGHT between two points joins them
    directly), held within `corridor` px of the polyline through them."""
    plain = [p for p in pts if p != lw.STRAIGHT]
    near = ndi.distance_transform_edt(~trace_line(gf.shape, plain)) <= corridor
    return lw.livewire(np.where(near, 1.0 + gf / 8.0, 1e4), pts)


def ground_line(fr, W):
    """Per frame column, the frame row of the ground line: the upper edge of
    the dark line under the scene, y = 0 on the vase."""
    th = np.linspace(BOX_THETA[0] - 0.05, BOX_THETA[1] + 0.05, 2000)
    xy = fr["to_frame"](th, np.zeros_like(th))
    ok = np.isfinite(xy[:, 0])
    return np.interp(np.arange(W), xy[ok, 0], xy[ok, 1])


def smooth_outline(mask, keep, worn):
    """The mask with every outline (outer and holes) smoothed along its own
    length: EDGE_SIGMA px of arc, WORN_SIGMA inside worn, none inside keep
    (blended over the same length), and filled again (even-odd)."""
    from PIL import ImageDraw
    from skimage import measure
    out = np.zeros(mask.shape, bool)
    H, W = mask.shape
    for c in measure.find_contours(np.pad(mask, 1).astype(np.float32), 0.5):
        c = c[:-1] - 1.0  # closed: the last point repeats the first
        if len(c) < 8:
            continue
        iy, ix = np.clip(np.round(c[:, 0]).astype(int), 0, H - 1), np.clip(np.round(c[:, 1]).astype(int), 0, W - 1)
        s1 = ndi.gaussian_filter1d(c, EDGE_SIGMA, axis=0, mode="wrap")
        s2 = ndi.gaussian_filter1d(c, WORN_SIGMA, axis=0, mode="wrap")
        ww = ndi.gaussian_filter1d(worn[iy, ix].astype(float), EDGE_SIGMA, mode="wrap")[:, None]
        wk = ndi.gaussian_filter1d(keep[iy, ix].astype(float), EDGE_SIGMA, mode="wrap")[:, None]
        sm = (1 - wk) * ((1 - ww) * s1 + ww * s2) + wk * c
        im = Image.new("1", (W, H), 0)
        ImageDraw.Draw(im).polygon([(float(x), float(y)) for y, x in sm], fill=1)
        out ^= np.asarray(im, dtype=bool)  # even-odd: holes inside the outer outline open again
    return out


def biggest(mask):
    lab, n = ndi.label(mask)
    return lab == 1 + int(np.argmax(ndi.sum(np.ones(mask.shape), lab, np.arange(1, n + 1))))


def scene(m, ground_row):
    """The scene's area (him, the rock and the bow case), its windows (the
    black ground seen through it), and the painted black inside it."""
    glaze, _ = classes(m)
    shape = glaze.shape
    glaze |= np.arange(shape[0])[:, None] >= ground_row[None, :]  # below the ground line
    for p in GLAZE_DAMAGE:
        glaze |= poly(shape, p)
    glaze[:, :LEFT_X] = True
    cut = np.zeros(shape, bool)
    xy = cut_path(m["gf"], TREE_CUT, TREE_CORRIDOR).astype(int)
    cut[xy[:, 1], xy[:, 0]] = True
    cut = ndi.binary_dilation(cut, iterations=1)
    ground = ndi.binary_opening(glaze, structure=morphology.disk(2))
    # the ground takes in the contour stripe along its edge
    keep_paint = poly(shape, HEAD)
    for pts, half in BLACK_BANDS:
        keep_paint |= ndi.distance_transform_edt(~trace_line(shape, pts)) <= half
    stripe = (m["LA"] < STRIPE_L) & ~ground & ~keep_paint
    stripe &= ndi.distance_transform_edt(~ground) <= STRIPE_REACH
    stripe = ndi.binary_opening(stripe, structure=morphology.disk(STRIPE_OPEN))
    # (only the ground round him and the windows: not the specks of glaze in a
    # wash stroke, which the stripe would swell into black blots)
    def outer_of(gr):
        glab, _ = ndi.label(gr)
        o = np.unique(np.r_[glab[0], glab[-1], glab[:, 0], glab[:, -1], [glab[y, x] for x, y in WINDOWS]])
        return glab, o[o > 0]
    glab, outer = outer_of(ground)
    lab, _ = ndi.label(ground | stripe)
    ground |= stripe & np.isin(lab, np.unique(lab[np.isin(glab, outer)]))
    glab, outer = outer_of(ground)
    outer_ground = np.isin(glab, outer)
    near_ground = np.arange(shape[0])[:, None] >= ground_row[None, :] - 2 * SOFT_REACH
    soft = (m["LA"] < SOFT_L) & ~ground & ~keep_paint & ~near_ground
    soft &= ndi.distance_transform_edt(~outer_ground) <= SOFT_REACH
    lab, _ = ndi.label(outer_ground | soft)
    ground |= soft & np.isin(lab, np.unique(lab[outer_ground]))
    lab, _ = ndi.label(~ground & ~cut)
    area = lab == lab[SEED[1], SEED[0]]
    area = ndi.binary_fill_holes(area | (cut & ndi.binary_dilation(area, iterations=2)))
    glab, _ = ndi.label(ground)
    windows = np.isin(glab, [glab[y, x] for x, y in WINDOWS]) & area
    # a window's narrow parts are black paint, not ground
    lab, _ = ndi.label(ndi.binary_opening(windows, structure=morphology.disk(WINDOW_OPEN)))
    windows = np.isin(lab, [k for k in (lab[y, x] for x, y in WINDOWS) if k > 0])
    area &= ~windows
    # smooth edges: flecks of clay in the glaze along an edge leave no notches
    area = ndi.binary_closing(ndi.binary_opening(area, structure=morphology.disk(EDGE_R)), structure=morphology.disk(EDGE_R))
    area = smooth_outline(biggest(area), poly(shape, HEAD), poly(shape, WORN))
    area = biggest(area)  # one piece: flecks of clay inside a window are not the scene
    # the windows are exactly the holes left in the smoothed area; holes that
    # are not windows are filled
    holes = ndi.binary_fill_holes(area) & ~area
    lab, _ = ndi.label(holes)
    windows = np.isin(lab, np.unique(lab[windows & holes])) & (lab > 0)
    area |= holes & ~windows
    painted = area & ground
    return area, windows, painted


# ---------------------------------------------------------------- the lines

# Painted lines: local contrast (maps) with hysteresis, LINE_LOW to carry a
# line on and LINE_HIGH to start one; drawn at their own width (where the
# contrast is at least half the strongest within HALF_R px), along their
# centres, never thinner than LINE_MIN px. A piece shorter than LINE_LEN px
# (along its centre) is grain; one shorter than SHORT_LEN whose contrast never
# reaches SHORT_C is grain too. The brown washes are broader than the closing
# and give next to no contrast inside.
LINE_LOW, LINE_HIGH, HALF_R, LINE_MIN = 14, 30, 3, 3.5
LINE_LEN, SHORT_LEN, SHORT_C = 14, 40, 45
HOLE, MASK_SIGMA, SPUR, WIDTH_SIGMA = 12, 1.5, 7, 6.0
# The outline, drawn EDGE px wide inside the figure's edge; lines ending within
# EDGE_ZONE px of the edge are carried straight on to it (the last END_RUN px
# give their direction), and none are found nearer the edge than that (the
# half-tone between clay and ground passes for a line there).
EDGE, EDGE_ZONE, END_RUN = 5.0, 7.0, 8
# On the rock (ROCK: the rock he sits on, and the rock under his raised foot)
# only black lines are drawn: a line there must have a tenth of its pixels
# darker than ROCK_DARK times the clay round it (r), and be ROCK_MIN px long.
# The rock's own thin strokes are brown dilute paint, like its washes, and are
# left out. His gear (GEAR: the bow, the bow case and its straps) lies on the
# rock with almost no wash under it; there the lines are found as on him,
# faint ones included, and pieces shorter than GEAR_MIN are wash or a crack.
ROCK = [
    [(0, 2420), (0, 1300), (950, 1300), (950, 1380), (1050, 1440), (1095, 1442), (1222, 1372), (1290, 1378),
     (1302, 1460), (1335, 1500), (1345, 1435), (1880, 1440), (1975, 1480), (2030, 1530), (2075, 1570), (2105, 1610),
     (2112, 1650), (2105, 1705), (2130, 1715), (2200, 1718), (2260, 1695), (2300, 1665), (2350, 1700),
     (2500, 1850), (2650, 2000), (2690, 2070), (2700, 2250), (2750, 2420)],
    [(2895, 1840), (3060, 1815), (3200, 1790), (3350, 1790), (3350, 2420), (3140, 2420), (3130, 2290),
     (3020, 2240), (2950, 2200), (2900, 2050)],
]
ROCK_DARK, ROCK_MIN = 0.35, 60
GEAR = [(1630, 1395), (1795, 1395), (1800, 1560), (1850, 1640), (1950, 1690), (1990, 1765), (2250, 1765),
        (2335, 1795), (2365, 1860), (2365, 1990), (2250, 2005), (2150, 2005), (2120, 2100), (2250, 2120),
        (2355, 2160), (2360, 2335), (1950, 2335), (1840, 2210), (1665, 2070), (1550, 2070), (1462, 1735),
        (1622, 1580)]
GEAR_MIN = 40
# Black paint the colours miss (A shows it brown-black, not as dark as the
# ground), drawn solid. On the bow case (QUIVER, ARROWHEAD): paint darker
# than QUIVER_SEED times the wide clay level (rA), joined by paint darker than
# QUIVER_GROW; pieces at least 2 * QUIVER_THICK px wide somewhere are filled
# whole. Along BLACK_BANDS (the broad dark strokes that outline his feet
# against the rock, and the stroke down the back of his raised calf: points
# along each, and a half-width in px), paint darker than BLACK_K joined by
# paint darker than BAND_LOW. Glaze inside the scene at least 2 * THICK px
# wide stays solid (the top of his head, a thick stroke at his heel).
QUIVER = [(1685, 1773), (1752, 1665), (1900, 1660), (1945, 1700), (1950, 1790), (2027, 1915), (2077, 1990),
          (2093, 2107), (2043, 2157), (2127, 2190), (2143, 2307), (1977, 2323), (1918, 2223), (1835, 2107),
          (1752, 1995), (1650, 1985), (1645, 1915), (1685, 1857)]
ARROWHEAD = [(1570, 2005), (1640, 2005), (1640, 2068), (1570, 2068)]
QUIVER_SEED, QUIVER_GROW, QUIVER_THICK = 0.3, 0.35, 4.5
BLACK_K, BAND_LOW = 0.3, 0.45
BLACK_BANDS = [
    ([(2700, 2040), (2745, 2075), (2765, 2105), (2750, 2140), (2735, 2180), (2727, 2212), (2735, 2235), (2770, 2248),
      (2820, 2258), (2870, 2275), (2930, 2300), (3000, 2322), (3035, 2332)], 16),
    ([(2846, 1980), (2902, 2061), (2965, 2167), (3015, 2230), (3077, 2292), (3115, 2330)], 14),
    ([(2900, 1812), (2960, 1804), (2995, 1798), (3040, 1803), (3080, 1808), (3100, 1810), (3115, 1811)], 10),
    ([(2512, 1270), (2500, 1320), (2505, 1370), (2540, 1420), (2585, 1465)], 32),
    ([(2585, 1465), (2620, 1505), (2648, 1550), (2668, 1590), (2690, 1640), (2705, 1680), (2718, 1712)], 22),
]
THICK = 6
# The dark strokes round his hanging foot (BLACK_BANDS 0 and 1: heel and sole,
# and down the front of his shin to the toes) are dark brown paint, darkest in
# the core (rA 0.14-0.3) with a browner fringe: drawn as their brushstroke, a
# wash in SHADOW_STEPS (as the hair's) over the paint darker than SHADOW_K
# within SHADOW_PAD px of the band's corridor, near black in the core (John,
# 2026-10-09: "the shadow around his foot needs some correcting").
SHADOW, SHADOW_PAD, SHADOW_K, SHADOW_SIGMA, SHADOW_MIN = (0, 1), 8, 0.75, 1.5, 40
SHADOW_STEPS = [("rA", 0.75, 0.35), ("rA", 0.55, 0.6), ("rA", 0.42, 0.85), ("rA", 0.3, 1.0)]
# The bow's inner line and the outer line round the end of the strap's loop
# are fainter than any test passes: placed by hand, snapped to the paint
# within BOW_SNAP px (John, 2026-10-03: "part of the top outside curve of the
# bow isn't drawn"; "you also missed part of the strap").
BOW_LINE = [(1655, 1402), (1664, 1420), (1684, 1444), (1700, 1465), (1708, 1480), (1713, 1500), (1716, 1540),
            (1715, 1560), (1713, 1580), (1710, 1600), (1705, 1620), (1699, 1640), (1692, 1660), (1685, 1680),
            (1677, 1700), (1668, 1720)]
STRAP_LINE = [(2345, 1822), (2357, 1833), (2366, 1847), (2372, 1862), (2376, 1880), (2376, 1895), (2374, 1910),
              (2368, 1924)]
BOW_SNAP = 4
# Breaks where the paint is worn or the photo fades (as clouds.py): line ends
# facing each other across at most JOIN_MAX px (their last JOIN_RUN px
# pointing at each other within JOIN_ANGLE degrees), where the contrast across
# the gap has a median of JOIN_C or more and stays under JOIN_LOW for no more
# than JOIN_FADE px together, and the join crosses no other line; ends pointing
# straight at each other (within 10 degrees) across up to ALIGN_MAX, where the
# contrast's median is ALIGN_C or more, and not along the edge (FAINT_EDGE).
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C, JOIN_LOW, JOIN_FADE, JOIN_DOT = 35, 8, 20, 8, 4, 6, 40
ALIGN_COS, ALIGN_C, ALIGN_MAX, FAINT_EDGE = np.cos(np.radians(10)), 5, 60, 8
# His hair and beard: brown wash over the clay, darker strokes for the curls,
# inside HEAD. The hair is the paint there darker than HAIR_K times the clay
# over the wide window (rW: the narrow one finds only brown inside the hair)
# and redder than HAIR_RB (red less blue: C's glare on the black glaze is
# light but grey, and the glaze itself under 40; the brown 45-150), closed over HAIR_CLOSE px, in pieces of HAIR_MIN px or more, less the
# black top of the head and his face (FACE: the profile, brow and eye, drawn as
# lines); the clay between the strokes stays clay. Its wash in the line colour follows the photo's
# darkness (smoothed over HAIR_SIGMA px) in HAIR_STEPS (map, level, total
# opacity; pieces of HAIR_STEP_MIN px or more): only the brown paint, the
# clay between the strokes left clear (John, 2026-10-09, of four treatments:
# "D, but note the different dark and light intensities"), from the light
# wash through the curl strokes (r: darker than the wash round them) to the
# darkest curls, whose glaze touches the black top of his head and is all but
# black, so the hair grades into it ("he's not wearing a hat"); rH (below)
# darkens it toward the top. As acharnians.py. No lines are drawn inside the hair.
CAP_OPEN = 10
# where the curls meet the ground: the back of his head, and the curls over
# his forehead (elsewhere the brown stripe along his outline is not hair)
HEAD_OPEN = [(1760, 600), (1760, 90), (2460, 90), (2460, 470), (2345, 470), (2300, 440), (1990, 560), (1960, 600)]
# the black top's brushstrokes: A's grey (no glare there; LAn = grey / 100),
# the whole top at the first step's opacity and the darker strokes layered on
CAP_STEPS = [("LAn", 9.0, 0.86)] + [("LAn", float(lv), float(op)) for lv, op in
                                    zip(np.linspace(0.34, 0.17, 6), np.linspace(0.89, 0.99, 6))]
CAP_SIGMA, CAP_MIN = 3.0, 60
HAIR_EDGE = [[(1780, 250), (1960, 250), (1960, 600), (1780, 600)], [(2290, 370), (2370, 370), (2370, 470), (2290, 470)]]
HAIR_K, HAIR_RB, HAIR_CLOSE, HAIR_MIN, HAIR_SIGMA = 0.78, 40, 2, 100, 6.0
# Layered as the vase has it (John, 2026-10-09: "More blending of tones", then
# "keep iterating on the hair"; of three layerings he chose the one with the
# most curls): the hair's mass as a soft tone (HAIR_STEPS, smoothed over
# HAIR_SIGMA px), and on it the curl strokes, the paint darker than CURL_R
# times the wash round it (r), sharp (CURL_STEPS, smoothed over CURL_SIGMA px,
# in pieces of CURL_MIN px or more).
HAIR_STEPS = [("rH", float(lv), float(op)) for lv, op in zip(np.linspace(0.8, 0.4, 6), np.linspace(0.22, 0.5, 6))]
CURL_R, CURL_SIGMA, CURL_MIN = 0.8, 1.2, 25
CURL_STEPS = [("rH", 9.0, 0.5), ("rH", 0.45, 0.68), ("rH", 0.36, 0.82), ("rH", 0.28, 0.92)]
# rH: rW darkened toward the black top of his head, by CAP_DARK at its edge,
# fading to nothing CAP_NEAR px away (John, 2026-10-09: "make the other hair
# (especially those closest to the dark part on the top) darker so there's
# less contrast between top of head and the rest")
CAP_DARK, CAP_NEAR = 0.45, 120
# and in his goatee (BEARD, frame px), by BEARD_DARK, feathered over
# BEARD_FEATHER px (John, 2026-10-09: "And make the goatee area darker")
BEARD = [(1980, 500), (2100, 470), (2180, 520), (2190, 600), (2160, 690), (2080, 710), (2000, 680), (1970, 600)]
BEARD_DARK, BEARD_FEATHER = 0.35, 12
HAIR_STEP_MIN, HAIR_HOLE = 60, 200
# his face's painted marks (brow, eye, pupil), at their own shape: r under
# FACE_K, or A's rA under FACE_KA (C's glare lightens the glossy brow)
FACE_K, FACE_KA = 0.62, 0.5
FACE = [(2130, 445), (2170, 425), (2200, 430), (2240, 450), (2290, 465), (2340, 470), (2350, 520), (2300, 600),
        (2180, 600), (2150, 555), (2140, 510), (2125, 470)]


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the
    line ends kept), pieces under `min_len` px dropped."""
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


def even_lines(mask, own):
    """The lines of `mask` redrawn along their centres, each at the width `own`
    has there (the paint's own width), smoothed along the line over
    WIDTH_SIGMA px, at least LINE_MIN (as clouds.py). The mask is smoothed
    first in PhotoCraft (Gaussian, cut at half)."""
    mask = morphology.remove_small_holes(mask, max_size=HOLE)
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray((mask * 255).astype(np.uint8)).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MASK_SIGMA}))
        mask = grey(Path(td) / "ms.png") >= 128
    c = centre_lines(mask, spur=SPUR, min_len=LINE_LEN)
    w = 2 * ndi.distance_transform_edt(own)
    num, den = (ndi.gaussian_filter(a, WIDTH_SIGMA) for a in (np.where(c, w, 0.0), c.astype(float)))
    half = np.where(c, np.maximum(num / np.maximum(den, 1e-6), LINE_MIN) / 2, 0.0)
    d, (iy, ix) = ndi.distance_transform_edt(~c, return_indices=True)
    return d <= half[iy, ix], c, half


def along(shape, pts, width):
    """A line `width` px wide along points (x, y)."""
    P = np.array(pts, float)
    path = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) * 2 + 2) for a, b in zip(P[:-1], P[1:])])
    m = np.zeros(shape, bool)
    iy, ix = path[:, 1].round().astype(int), path[:, 0].round().astype(int)
    ok = (iy >= 0) & (iy < shape[0]) & (ix >= 0) & (ix < shape[1])
    m[iy[ok], ix[ok]] = True
    return ndi.distance_transform_edt(~m) <= width / 2


def to_outline(c, half, to_edge):
    """Each line ending within EDGE_ZONE + 2 px of the figure's edge, carried
    straight on until it meets the outline, at its own width."""
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere(c & (ndi.convolve(c.astype(int), k, mode="constant") == 1))
    H, W = c.shape
    out = np.zeros(c.shape, bool)
    for e in ends:
        if to_edge[tuple(e)] > EDGE_ZONE + 2:
            continue
        path, seen = [tuple(e)], {tuple(e)}
        for _ in range(END_RUN):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx)
                   and 0 <= y + dy < H and 0 <= x + dx < W and c[y + dy, x + dx] and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        if len(path) < END_RUN / 2:
            continue
        d = np.array(path[0], float) - np.array(path[-1], float)
        d /= np.hypot(*d)
        q = np.array(e, float)
        for _ in range(int(6 * EDGE_ZONE)):
            q = q + d * 0.5
            i, j = int(round(q[0])), int(round(q[1]))
            if not (0 <= i < H and 0 <= j < W) or to_edge[i, j] <= EDGE:
                break
        else:
            continue
        out |= along(c.shape, [e[::-1], q[::-1]], 2 * half[tuple(e)])
    return out


def join_breaks(lines, contrast, to_edge):
    """The breaks in `lines` that JOIN_* describe, joined (as clouds.py)."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    ends = np.argwhere(sk & (nb == 1))
    dt = ndi.distance_transform_edt(lines)
    H, W = sk.shape

    def run_back(p):
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
    size = np.bincount(lab.ravel())
    out = np.zeros_like(lines)
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    pairs = sorted(cKDTree(ends).query_pairs(ALIGN_MAX), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used or len(runs[i]) < JOIN_RUN / 2 or len(runs[j]) < JOIN_RUN / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
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
        if not aligned and np.hypot(*(b - a)) > JOIN_MAX:
            continue
        if aligned:
            if np.median(c) < ALIGN_C or np.median(ndi.map_coordinates(to_edge, q.T, order=1)) < FAINT_EDGE:
                continue
        elif np.median(c) < JOIN_C or (len(starts) and (stops - starts).max() > JOIN_FADE):
            continue
        mid = (np.hypot(*(q - a).T) > 2) & (np.hypot(*(q - b).T) > 2)
        hit = set(lab[tuple(q[mid].round().astype(int).T)]) - {0, lab[tuple(a.astype(int))], lab[tuple(b.astype(int))]}
        if any(size[k] >= JOIN_DOT for k in hit):
            continue
        w = np.median([dt[tuple(r.astype(int))] for r in np.vstack([runs[i], runs[j]])]) * 2
        out |= along(lines.shape, [(a - 1.5 * u)[::-1], (b + 1.5 * u)[::-1]], max(w, LINE_MIN))
        used |= {i, j}
    return out


def black_paint(m, area, painted):
    """The solid black: the bow case's black, the bands along his feet, and
    glaze inside the scene wider than 2 * THICK px."""
    shape = area.shape
    rA = m["rA"]
    quiver = (poly(shape, QUIVER) | poly(shape, ARROWHEAD)) & area
    lab, _ = ndi.label(quiver & (rA < QUIVER_GROW))
    seeds = np.unique(lab[quiver & (rA < QUIVER_SEED)])
    black = ndi.gaussian_filter(np.isin(lab, seeds[seeds > 0]).astype(np.float32), 1.0) > 0.5
    lab, n = ndi.label(black)
    thick = np.zeros(n + 1, bool)
    thick[1:] = ndi.maximum(ndi.distance_transform_edt(black), lab, np.arange(1, n + 1)) >= QUIVER_THICK
    black = thick[lab]
    for k, (pts, half) in enumerate(BLACK_BANDS):
        if k in SHADOW:
            continue
        corridor = ndi.distance_transform_edt(~trace_line(shape, pts)) <= half
        lab, _ = ndi.label(corridor & (rA < BAND_LOW))
        seeds = np.unique(lab[corridor & (rA < BLACK_K)])
        black |= np.isin(lab, seeds[seeds > 0])
    black = ndi.binary_opening(black & area, structure=morphology.disk(1))
    black = morphology.remove_small_objects(ndi.gaussian_filter(black.astype(np.float32), 1.0) > 0.5, max_size=30)
    return ndi.binary_fill_holes(ndi.binary_opening(painted, structure=morphology.disk(THICK))) | black


def shadow_zone(m, area):
    """The paint of the shadow bands round his hanging foot (SHADOW_*)."""
    shape = area.shape
    corridor = np.zeros(shape, bool)
    for k in SHADOW:
        pts, half = BLACK_BANDS[k]
        corridor |= ndi.distance_transform_edt(~trace_line(shape, pts)) <= half + SHADOW_PAD
    z = corridor & area & (m["rA"] < SHADOW_K)
    return morphology.remove_small_objects(ndi.binary_opening(z, structure=morphology.disk(1)), max_size=SHADOW_MIN)


def hair_zone(m, area, cap, painted):
    """His hair and beard (HAIR_*): the brown paint inside HEAD, and the glaze
    of the darkest curls (painted), less the top of his head (cap) and his
    face (FACE)."""
    head = poly(area.shape, HEAD) & area & ~cap & ~poly(area.shape, FACE)
    paint = ((m["rW"] < HAIR_K) & (m["RB"] > HAIR_RB)) | painted
    brown = ndi.binary_closing(head & paint, structure=morphology.disk(HAIR_CLOSE)) & head
    # specks of clay between the strokes, under HAIR_HOLE px, take the wash
    # (white specks in the dark hair read as noise)
    brown = morphology.remove_small_holes(brown, max_size=HAIR_HOLE) & head
    return morphology.remove_small_objects(brown, max_size=HAIR_MIN)


def drawing(m, area, painted, w):
    """(ink, hair, solid): the lines, the hair's area, the solid black."""
    from skimage.filters import apply_hysteresis_threshold
    shape = area.shape
    contrast, r = m["contrast"], m["r"]
    solid = black_paint(m, area, painted)
    # the black top of his head (opened over CAP_OPEN px: the dark curls
    # touching its lower edge come off) is not solid but very dark layered
    # brushstrokes (CAP_STEPS), so all the hair is the same (John, 2026-10-09:
    # "the black part of the hair might work best as VERY dark layered
    # brushstrokes so all the hair is same"); the dark curls are the hair's
    # darkest wash
    head = poly(shape, HEAD)
    cap = biggest(ndi.binary_opening(biggest(solid & head), structure=morphology.disk(CAP_OPEN)))
    solid &= ~head
    hair = hair_zone(m, area, cap, painted)
    shadow = shadow_zone(m, area) & ~solid
    to_edge = ndi.distance_transform_edt(area)
    keep_out = hair | ndi.binary_dilation(solid, iterations=2) | ndi.binary_dilation(shadow, iterations=3)
    firm = apply_hysteresis_threshold(contrast, LINE_LOW, LINE_HIGH) & area & (to_edge >= EDGE_ZONE) & ~keep_out
    rock = np.zeros(shape, bool)
    for p in ROCK:
        rock |= poly(shape, p)
    gear = poly(shape, GEAR)
    rock &= ~gear
    lab, n = ndi.label(firm, structure=np.ones((3, 3)))
    sk = morphology.skeletonize(firm)
    idx = np.arange(1, n + 1)
    length = np.bincount(lab[sk], minlength=n + 1)
    top = np.zeros(n + 1)
    top[1:] = ndi.maximum(contrast, lab, idx)
    dark = np.ones(n + 1)
    on_rock = np.zeros(n + 1)
    on_gear = np.zeros(n + 1)
    if n:
        dark[1:] = ndi.minimum(ndi.minimum_filter(r, 3), lab, idx)
        on_rock[1:] = ndi.mean(rock.astype(float), lab, idx)
        on_gear[1:] = ndi.mean(gear.astype(float), lab, idx)
    keep = (length >= LINE_LEN) & ~((length < SHORT_LEN) & (top < SHORT_C))
    keep &= ~((on_rock > 0.5) & ((dark > ROCK_DARK) | (length < ROCK_MIN)))
    keep &= ~((on_gear > 0.5) & (length < GEAR_MIN))
    keep[0] = False
    firm &= keep[lab]
    near_max = ndi.maximum_filter(np.where(firm, contrast, 0), 2 * HALF_R + 1)
    own = firm & (contrast >= 0.5 * near_max)
    lines, c, half = even_lines(own | firm, own)
    lines = (lines | to_outline(c, half, to_edge)) & area
    # his face: the brow, the eye and its pupil at the paint's own shape
    # (smoothed in PhotoCraft), not as centre lines
    face = poly(shape, FACE) & area & (to_edge >= EDGE)
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray(((face & ((r < FACE_K) | (m["rA"] < FACE_KA))) * 255).astype(np.uint8)).save(Path(td) / "f.png")
        pc(Path(td) / "f.png", Path(td) / "fs.png", ("filter.blur.gaussianBlur", {"radius": 1.0}))
        fpaint = morphology.remove_small_objects(grey(Path(td) / "fs.png") >= 128, max_size=20)
    lines = (lines & ~face) | fpaint
    lines |= join_breaks(lines, contrast, to_edge) & area
    lines |= strokes(m["gf"], [BOW_LINE, STRAP_LINE], 2 * np.median(half[c]), snap=BOW_SNAP)
    edge = area & (to_edge <= EDGE)
    # where the curls meet the ground (HAIR_EDGE) there is no outline on the
    # vase: the edge there is the hair's wash; round the top and back of his
    # head (HEAD_OPEN, not his face) no outline is drawn either: the clay band
    # round the black top is left to the page (John, 2026-10-09: "in day mode,
    # the white buffer with black line outlining the head doesn't work")
    soft = edge & (ndi.distance_transform_edt(~hair) <= 2) & ~cap
    soft &= np.any([poly(shape, p) for p in HAIR_EDGE], axis=0)
    open_head = edge & poly(shape, HEAD_OPEN) & ~poly(shape, FACE)
    hair = (hair & ~edge) | soft
    ink = lines | (edge & ~soft & ~open_head) | solid
    return ink, hair, shadow, cap


def add_wash(svg, washes, m, box):
    """Washes added to the drawing trace_svg wrote (box: the crop box it
    returned), between the body and the lines: for each (mask, steps, sigma,
    min_px), the maps named in its steps smoothed within the mask over sigma px
    (a masked blur in PhotoCraft), and a path per step (map, level, total
    opacity: where the map is under the level, inside the step below, in
    pieces of min_px or more), each over the one below at the opacity that
    brings the total to its own."""
    x0, y0, x1, y1 = box
    paths = ""
    for mask, steps, sigma, min_px in washes:
        dark = {}
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            Image.fromarray((mask * 255).astype(np.uint8)).save(t / "hm.png")
            pc(t / "hm.png", t / "hms.png", ("filter.blur.gaussianBlur", {"radius": sigma}))
            for key in sorted({k for k, _, _ in steps}):
                Image.fromarray((np.where(mask, m[key], 0) * 200).clip(0, 255).astype(np.uint8)).save(t / "hr.png")
                pc(t / "hr.png", t / "hrs.png", ("filter.blur.gaussianBlur", {"radius": sigma}))
                dark[key] = grey(t / "hrs.png") / 200 / np.maximum(grey(t / "hms.png") / 255, 1e-3)
        below, prev = 0.0, mask
        for key, level, total in steps:
            mk = prev & (dark[key] < level)
            lab, _ = ndi.label(mk)
            mk &= (np.bincount(lab.ravel()) >= min_px)[lab]
            prev = mk
            if not mk[y0:y1, x0:x1].any():
                continue
            d, _ = lw.potrace_d(lw.resample_ink(mk[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
            paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - total) / (1 - below):.3f}" '
                      f'stroke="none" d="{d}"/>')
            below = total
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


# The rock's brown washes, drawn as its brushstrokes (John, 2026-10-09: "can
# you also duplicate the texture brush strokes on the rock?"; the first drawing
# left them out): on the rock (ROCK, less the bow case), the paint darker than
# ROCK_K times the wide clay level and redder than HAIR_RB, in ROCK_STEPS (as
# the hair's; the first step is the strokes darker than the wash round them
# (r), so the strokes stand on clay, not one pale wash), smoothed
# over ROCK_SIGMA px, in pieces of ROCK_STEP_MIN px or more.
ROCK_K, ROCK_SIGMA, ROCK_STEP_MIN = 0.93, 3.0, 300
ROCK_STEPS = [("r", 0.92, 0.16), ("rW", 0.7, 0.34), ("rW", 0.58, 0.5), ("rW", 0.46, 0.65)]


def rock_wash(m, area, ink):
    shape = area.shape
    rock = np.any([poly(shape, p) for p in ROCK], axis=0) & area & ~poly(shape, QUIVER)
    rock &= ~ndi.binary_dilation(ink, iterations=1)
    brown = rock & (m["rW"] < ROCK_K) & (m["RB"] > HAIR_RB)
    brown = ndi.binary_opening(brown, structure=morphology.disk(2))
    return morphology.remove_small_objects(brown, max_size=ROCK_STEP_MIN)


def build(m, ground_row):
    """Everything up to the SVG: (ink, area, windows, washes); washes as
    add_wash takes them."""
    area, windows, painted = scene(m, ground_row)
    ys, xs = np.nonzero(area)
    w = lw.HOUSE_WEIGHT * max(np.ptp(ys), np.ptp(xs))
    ink, hair, shadow, cap = drawing(m, area, painted, w)
    lab, _ = ndi.label(windows)
    ink |= np.isin(lab, [k for k in (lab[y, x] for x, y in BLACK_WINDOWS) if k > 0])
    ink &= ~hair & ~shadow & ~cap
    m["rH"] = m["rW"] * (1 - CAP_DARK * np.clip(1 - ndi.distance_transform_edt(~cap) / CAP_NEAR, 0, 1))
    m["rH"] *= 1 - BEARD_DARK * ndi.gaussian_filter(poly(area.shape, BEARD).astype(np.float32), BEARD_FEATHER)
    washes = [(rock_wash(m, area, ink) & ~shadow, ROCK_STEPS, ROCK_SIGMA, ROCK_STEP_MIN),
              (shadow, SHADOW_STEPS, SHADOW_SIGMA, SHADOW_MIN), (cap, CAP_STEPS, CAP_SIGMA, CAP_MIN),
              (hair, HAIR_STEPS, HAIR_SIGMA, HAIR_STEP_MIN),
              (hair & (m["r"] < CURL_R), CURL_STEPS, CURL_SIGMA, CURL_MIN)]
    return ink, area, windows, washes


# the line weight, pinned (as acharnians.py): the paint's own median width is
# 0.14% of the longer side, which read faint beside the other drawings at 400 px
WEIGHT = 0.0021


def write(ink, area, washes, m, qa=None):
    ys, xs = np.nonzero(ink | area)   # the crop trace_svg takes (pad 4)
    weight = WEIGHT_PX / max(np.ptp(ys) + 9, np.ptp(xs) + 9)
    info = lw.trace_svg(
        ink, OUT, body=area, open_holes=~area, extent=area, weight=weight,
        title="Philoctetes alone on Lemnos, seated on a rock under a tree, his bandaged leg drawn up, his bow case beside him",
        desc="Line drawing after the Attic red-figure squat lekythos in the manner of the Eretria Painter, c. 420 BCE, "
             "New York, Metropolitan Museum of Art 56.171.58; traced from photographs by Marie-Lan Nguyen (CC BY 2.5) "
             "and the Metropolitan Museum of Art (CC0), changed.")
    add_wash(OUT, washes, m, info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(m["g"], OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))
    level_svg(OUT)                        # last: the check images are drawn on the unturned grid
    return info


def level_svg(svg):
    """The levelling turn (LEVEL) round the drawing, and its view box cut to LEVEL_VIEW."""
    s = svg.read_text()
    s = re.sub(r'viewBox="[^"]+"', f'viewBox="{LEVEL_VIEW}"', s, count=1)
    s = s.replace('<g transform="scale(', f'<g transform="rotate({LEVEL} {LEVEL_C[0]:g} {LEVEL_C[1]:g})"><g transform="scale(', 1)
    head, _, tail = s.rpartition("\n</svg>")
    svg.write_text(head + "\n</g></svg>" + tail)

# ---------------------------------------------------------------- the tree

# The tree, added back (John, 2026-10-09: "Can we also add the tree? I think it
# completes the framing nicely"; the first drawing cut it off). Its boughs run
# up onto the vase's shoulder, outside the flat (flat_keep keeps his head true).
# So the tree has a flat of its own, the whole rectangle up to TREE_TOP, and
# that flat is laid onto the frame by the similarity (with the flip of the y
# axis) that best fits the frame along the seam where the trunk meets the rock
# (TREE_CUT, sampled every 2 px and TREE_SEAM_OFFS px either side): 0.65 px
# median, 3.3 at most; away from the seam the boughs are free. The canvas is the
# frame widened by PAD_T px at the top. Photo A (it sees the whole tree).
TREE_TOP, PAD_T = 1560.1, 300
TREE_SEAM_OFFS = (-30, -15, 0, 15, 30)
# The tree's area: clay (as classes) joined to TREE_SEED (frame px, on the
# trunk), walled off from the scene along TREE_CUT (TREE_WALL px), its outline
# smoothed as the scene's; the narrow gap the wall leaves at the seam closed
# over SEAM_CLOSE px. It is drawn as its outline, EDGE px wide, except along the
# seam (the scene draws the rock's top line there).
TREE_SEED, TREE_WALL, SEAM_CLOSE = (1220, 620), 4, 6
# the line weight in frame px, pinned at the weight of the drawing without the
# tree (WEIGHT of its 3228-px crop), as the wider canvas would thin it
WEIGHT_PX = WEIGHT * 3228


def tree_frame(R, fr):
    """The tree's flat (inverse map to the vase) and the seam fit: tree flat
    world (x, y) -> frame px is z -> c[0] * conj(z) + c[1]."""
    th, yy = np.arange(*FLAT_THETA), np.arange(FLAT_Y[0], TREE_TOP, FLAT_Y[2])
    with redirect_stdout(io.StringIO()):
        XY = vu.flatten(R, th, yy, centre=CENTRE)
    TH, Y = np.meshgrid(th, yy)
    inv = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))
    fwd = [RegularGridInterpolator((yy, th), XY[..., k], bounds_error=False) for k in (0, 1)]
    P = np.array([p for p in TREE_CUT if p != lw.STRAIGHT], float)
    seg = np.vstack([np.linspace(a, b, max(int(np.hypot(*(b - a)) / 2), 2)) for a, b in zip(P[:-1], P[1:])])
    S = np.vstack([seg + (dx, dy) for dx in TREE_SEAM_OFFS for dy in TREE_SEAM_OFFS])
    tv = fr["to_vase"](S[:, 0], S[:, 1])
    ok = np.isfinite(tv).all(1)
    S, tv = S[ok], tv[ok]
    q = np.c_[tv[:, 1], tv[:, 0]]
    b = np.c_[fwd[0](q), fwd[1](q)]
    ok = np.isfinite(b).all(1)
    A = np.c_[np.conj(b[ok, 0] + 1j * b[ok, 1]), np.ones(ok.sum())]
    c, *_ = np.linalg.lstsq(A, S[ok, 0] + 1j * S[ok, 1], rcond=None)
    return inv, c


def tree_image(photo, R, fr, step=4):
    """Photo A laid onto the canvas (the frame widened by PAD_T at the top)
    through the tree's flat."""
    inv, c = tree_frame(R, fr)
    Hc, Wc = fr["H"] + PAD_T, fr["W"]
    gx, gy = np.meshgrid(np.arange(0, Wc + step, step), np.arange(0, Hc + step, step))
    zb = np.conj(((gx + 1j * (gy - PAD_T)).ravel() - c[1]) / c[0])
    tq = inv(np.c_[zb.real, zb.imag])
    good = np.isfinite(tq[:, 0])
    t, y = np.where(good, tq[:, 0], 0.0), np.where(good, tq[:, 1], 0.0)
    cams, _ = vase()
    cam, phi = cams["A"], np.radians(TURNS["A"])
    P = vu.surface(R, y, t + phi)
    uv = vu.project(cam, P)
    nrm = np.stack([np.sin(t + phi), -R(y, 1), np.cos(t + phi)], -1)
    facing = np.einsum("ij,ij->i", nrm, np.array([0.0, cam["H"], cam["D"]]) - P) > 0
    ok = (good & facing).reshape(gx.shape)
    u = ndi.zoom(np.where(ok, uv[:, 0].reshape(gx.shape), -1e4), step, order=1)[:Hc, :Wc]
    v = ndi.zoom(np.where(ok, uv[:, 1].reshape(gx.shape), -1e4), step, order=1)[:Hc, :Wc]
    a = np.asarray(Image.open(photo).convert("RGB"), dtype=np.float32)
    return np.stack([ndi.map_coordinates(a[..., k], [v, u], order=1, cval=0) for k in range(3)], -1)


def pad(a, value=0):
    return np.pad(a, ((PAD_T, 0), (0, 0)) + ((0, 0),) * (a.ndim - 2), constant_values=value)


def with_tree(rgbT, ink, area, washes, m):
    """The drawing on the canvas, with the tree: (ink, area, washes, maps)."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rgbT.clip(0, 255).round().astype(np.uint8)).save(t / "T.png")
        pc(t / "T.png", t / "LT.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "T.png", t / "RBT.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 1}))
        _, clay = classes({"LA": grey(t / "LT.png"), "RBA": grey(t / "RBT.png")})
        gT = grey(t / "LT.png")
    shape = clay.shape
    main = pad(area)
    cut = np.zeros(shape, bool)
    for (xa, ya), (xb, yb) in zip(*[[p for p in TREE_CUT if p != lw.STRAIGHT][k:] for k in (0, 1)]):
        cut |= trace_line(shape, [(xa, ya + PAD_T), (xb, yb + PAD_T)])
    wall = ndi.binary_dilation(cut, iterations=TREE_WALL)
    cand = ndi.binary_opening(clay, structure=morphology.disk(2)) & ~wall & ~main
    lab, _ = ndi.label(cand)
    k = lab[TREE_SEED[1] + PAD_T, TREE_SEED[0]]
    assert k, "TREE_SEED is not on the tree's clay"
    tree = ndi.binary_fill_holes(lab == k)
    tree = ndi.binary_closing(ndi.binary_opening(tree, structure=morphology.disk(EDGE_R)), structure=morphology.disk(EDGE_R))
    tree = smooth_outline(biggest(tree), np.zeros(shape, bool), np.zeros(shape, bool)) & ~main
    both = main | tree
    gap = ndi.binary_closing(both, structure=morphology.disk(SEAM_CLOSE)) & ~both & ndi.binary_dilation(wall, iterations=2)
    area2 = both | gap
    edge = area2 & (ndi.distance_transform_edt(area2) <= EDGE)
    ink2 = pad(ink) | (edge & ~ndi.binary_dilation(main | gap, iterations=int(EDGE) + 3))
    m2 = {k: pad(v) for k, v in m.items() if isinstance(v, np.ndarray) and v.ndim == 2}
    m2["g"] = np.where(np.arange(shape[0])[:, None] < PAD_T, gT, m2["g"])
    return ink2, area2, [(pad(mk), *rest) for mk, *rest in washes], m2


# John's traces for the first drawing (frame px): the check for the new lines
TRACES = {k: v for k, v in json.loads((Path(__file__).parent / "philoctetes_traces.json").read_text()).items()
          if k != "note"}
TRACE_K = 3   # the check image's enlargement


def traces_check(ink, hair, g, out):
    """John's traces (blue) over the new drawing (red ink, the hair's area
    pale red) and the photo's grey, one panel per traced part."""
    panels = []
    for name, t in TRACES.items():
        pts = np.vstack([np.array(p, float) for p in t["lines"] + t["solids"]])
        x0, y0 = (pts.min(0) - 20).astype(int)
        x1, y1 = (pts.max(0) + 20).astype(int)
        sl = (slice(y0, y1), slice(x0, x1))
        im = np.repeat(g[sl][..., None], 3, -1) * 0.5 + 127
        im[hair[sl]] = im[hair[sl]] * 0.7 + np.array([255, 120, 120]) * 0.3
        im[ink[sl]] = [220, 30, 30]
        big = Image.fromarray(im.clip(0, 255).astype(np.uint8)).resize(((x1 - x0) * TRACE_K, (y1 - y0) * TRACE_K),
                                                                       Image.NEAREST)
        from PIL import ImageDraw
        d = ImageDraw.Draw(big)
        for p in t["lines"]:
            d.line([((x - x0) * TRACE_K, (y - y0) * TRACE_K) for x, y in p], fill=(0, 90, 255), width=2)
        for p in t["solids"]:
            d.polygon([((x - x0) * TRACE_K, (y - y0) * TRACE_K) for x, y in p], outline=(0, 90, 255))
        d.text((6, 6), name, fill=(0, 0, 0))
        panels.append(big)
    W = max(p.width for p in panels)
    sheet = Image.new("RGB", (W, sum(p.height + 10 for p in panels)), "white")
    y = 0
    for p in panels:
        sheet.paste(p, (0, y))
        y += p.height + 10
    sheet.save(out)


def main(pC: str, pA: str, pB: str) -> None:
    if "--refit" in sys.argv:
        fit_model({"C": pC, "A": pA, "B": pB})
        return
    _, R = vase()
    fr = frame(R)
    rgbC, rgbA = flat_image(pC, "C", R, fr), flat_image(pA, "A", R, fr)
    m = maps(rgbC, rgbA)
    ink, area, windows, washes = build(m, ground_line(fr, rgbA.shape[1]))
    if "--traces" in sys.argv:   # the check against John's traces, not the drawing
        traces_check(ink, washes[3][0], m["g"], sys.argv[sys.argv.index("--traces") + 1])
        return
    ink, area, washes, m = with_tree(tree_image(pA, R, fr), ink, area, washes, m)
    rest = [a for a in sys.argv[4:] if not a.startswith("--")]
    write(ink, area, washes, m, rest[0] if rest else None)


if __name__ == "__main__":
    main(*sys.argv[1:4])
