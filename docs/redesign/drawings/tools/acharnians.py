"""Acharnians: a seated warrior in a crested helmet, his round shield at his side and his right hand
raised, from a comic "departure of the warrior" played on a stage, on the Apulian red-figure
bell-krater Würzburg, Martin von Wagner Museum H 4689 (McDaniel Painter). He is the type of
Lamachus, the crested general of Acharnians; the link is the type, not an identification of this
vase with the play. Photos: ArchaiOptix, CC BY-SA 4.0; _07 is the drawing's source, _04, _05 and _06
serve the vase's shape:
https://commons.wikimedia.org/wiki/File:McDaniel_Painter_-_RVAp_4-245_-_departure_of_warrior_as_phlyax_play_-_draped_youths_-_W%C3%BCrzburg_MvWM_H_4689_-_07.jpg

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop,
the R-B channel (Channel Mixer), the grey, the blurs, the Maximum and Minimum filters and the
thresholds. numpy only combines the masks PhotoCraft made (labels, unions, hysteresis) and measures.
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
    waist. The shield, on the side turning away from the camera, comes out about a third wider.
    His head checked against 06 laid onto the same flat: they agree within 1-2 px.
  - Clay against glaze by red less blue (R-B), in which the glaze's white sheen reads as glaze.
    He is the clay joined to SEEDS: the old man's spear tip, at the left, is a separate shape and
    left out. The stage he sits on is cut away along its top edge (STAGE): the back foot stands on
    the stage's painted line, which is kept as its sole; the stool's right leg runs into the plank.
  - Lines: the painting's dark lines inside him, by grey (luminance; scratches in the clay are
    light, not dark): the paint at its own width, the outline, and the solid black (hair, beard).

    python3 docs/redesign/drawings/tools/acharnians.py H4689-07.jpg [qa.png]
    python3 docs/redesign/drawings/tools/acharnians.py H4689-07.jpg H4689-04.jpg H4689-05.jpg H4689-06.jpg --refit
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
from skimage.filters import apply_hysteresis_threshold

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
}
PROFILE_Y = [-300, -100, 100, 300, 500, 700, 900, 1100, 1300, 1500]
PROFILE_R = [410.7, 615.6, 714.8, 764.3, 789.0, 813.6, 858.0, 902.3, 946.7, 991.1]
TURNS = {"04": 17.668, "05": 4.449, "06": 1.373}  # degrees each photo is turned from 07
PITCH = 10.0 / 1520.0  # mm per px on the 6D's sensor (EXIF focal plane resolution)
FOCAL_MM = {"07": 50, "04": 40, "05": 28, "06": 28}
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


def flat_image(p07):
    """Photo 07 laid onto the flat frame (H x W x 3, uint8)."""
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
    step = 4
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    tq = inv(np.stack([X0 + gx.ravel() / G, Y1 - gy.ravel() / G], -1))
    uv = vu.project(c, vu.surface(R, tq[:, 1], tq[:, 0])).reshape(gx.shape + (2,))
    u = ndi.zoom(np.nan_to_num(uv[..., 0], nan=-1e4), step, order=1)[:H, :W]
    v = ndi.zoom(np.nan_to_num(uv[..., 1], nan=-1e4), step, order=1)[:H, :W]
    a = np.asarray(Image.open(p07).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


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


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def main(src, qa=None, dump=None):
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
        g = grey(t / "g.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    sy = np.convolve(np.pad(STAGE, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    outside = yy + Y0 > np.interp(xx + X0, STAGE_X0 + 25 * np.arange(len(sy)), sy)
    dark = ~clay & ~outside
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
    edge = fig & (ndi.distance_transform_edt(fig) <= EDGE)
    ink = ((core | paint) & fig) | edge
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ink=ink, clay=clay)
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight="own",
                        title='A seated warrior raising his hand, a comic "departure of the warrior"',
                        desc="Line drawing after the Apulian red-figure bell-krater Würzburg H 4689; traced from a "
                             "photograph by ArchaiOptix (CC BY-SA 4.0), taken off the vase's curve.")
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--refit" in sys.argv:
        fit_model(dict(zip(["07", "04", "05", "06"], sys.argv[1:5])))
    else:
        main(*sys.argv[1:4])
