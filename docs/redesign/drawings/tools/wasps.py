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


# ---------------------------------------------------------------- the scene

CLAY = 60                     # clay: red less blue above this (blurred 2 px); glaze under it
LINE_DARK = 85                # painted lines: grey darker than this (blurred 1.5 px)
# Ground: the glaze, its painted lines (up to OPEN*2 px wide) opened away; the large areas, inside the scene too.
# Smaller glaze areas inside the figures are paint.
OPEN, AUTO_GROUND = 14, 40000
# and smaller areas of ground that the figures close in (flat px, a point in each): between the slave's right arm
# and his side
OPEN_PTS = [(3174, 1817)]
# and pockets narrower than the opening, found at FINE_OPEN within OPEN_FINE_R px of a point: the ground between
# the slave's left hand and the chest's rim
OPEN_FINE, OPEN_FINE_R = [(3069, 1852)], 80
FINE, FINE_OPEN = [], 3       # boxes (flat px) where the ground between parts is narrower (fingers)
SMOOTH, FINE_SMOOTH = 3.0, 1.5
EDGE = 9                      # the outline, flat px wide
SPECK, FLECK = 150, 200
# the line weight, pinned at pass 1's own (the median width, 7.49 flat px, over the longer side, 4848 px), so that
# later changes to a few lines do not re-weight them all (as phoenician_women.py)
WEIGHT = 0.0015440
# Seeds (flat px): the door leaf, the column, the roof, the left-hand man, the patterned cloth he holds out, the
# slave, his chest, the right-hand man, the plank
SEEDS = [(845, 1306), (1450, 1500), (1100, 480), (1900, 1600), (2680, 1088), (3300, 1400), (3400, 2200),
         (4200, 1500), (2600, 2540)]
# The left handle's palmette touches the porch's left side across a dark seam narrower than the opening: all left
# of the porch's own edge (flat px: where red less blue falls under CLAY into 15 px of glaze, row by row, less 4) is out, the seam with it
PALM_L = [(0, 850), (654, 850), (654, 900), (647, 1000), (635, 1100), (623, 1200), (618, 1275), (624, 1350),
          (634, 1450), (637, 1525), (631, 1600), (610, 1700), (572, 1800), (528, 1900), (505, 2000), (481, 2100),
          (468, 2200), (0, 2200)]
# The stage's legs are cut off at the plank's lower edge: per column (every PLANK_STEP px), the end of the clay run
# that holds row PLANK_ROW, smoothed (a running median over 5)
PLANK_ROW, PLANK_STEP, PLANK_X = 2540, 25, (200, 5100)
# White paint (hair and beards): inside each head's box (flat px), lighter than its grey limit and less red than its
# red-less-blue limit (clay is redder). The old men's white is a cool white (red less blue about 45); the slave's
# hair and beard a warm cream (about 80, as red as worn clay), told from his clay by lightness alone (clay there
# 168 or darker, the cream 175 and up)
HEADS = [((1850, 330, 2420, 820), 150, 75), ((3980, 330, 4560, 1250), 150, 75), ((3300, 950, 3720, 1350), 175, 255)]
# The slave's curls are dots and hooks of brown glaze on the cream: darker than CURL_L (grey, blurred 1 px) inside
# his hair, drawn as ink at their own size
CURL_BOX, CURL_L = (3300, 950, 3720, 1350), 140
# The slave's head is a sheep mask (John, 2026-10-10: "that's a sheep mask"): the fleece cream with brown curl
# marks, and the sheep's face drawn in thinned glaze, a pale brown arc and ring that grey hardly shows. In the blue
# channel (the cream is high in it, the glaze low) they stand 35 or more under the cream round them: blue blurred
# SHEEP_BLUR px, its Maximum then Minimum over SHEEP_R px less it, above SHEEP_T, pieces of SHEEP_MIN px^2 or more,
# inside SHEEP_BOX (flat px)
SHEEP_BOX, SHEEP_BLUR, SHEEP_R, SHEEP_T, SHEEP_MIN = (3420, 1150, 3640, 1330), 2.5, 10, 35, 40
# Faces, the mouth and its teeth, and the mask are traced at their own size, not re-weighted with the rest (as
# helen.py's eyes): weighting rounded the notches between the teeth and thickened the eyes. Boxes, flat px
FACES = [(2150, 380, 2440, 830), (4050, 420, 4420, 1000), (3300, 950, 3720, 1350)]
HAIR_SPAN, CLAY_SPECK = 20, 10
# The left-hand man's open mouth shows a row of teeth hanging from the moustache, white like it (John, 2026-10-10:
# "there are teeth here along with the beard/mustache"; he drew the line between them). The line: the mouth's top
# edge (the black joined to MOUTH, flat px, grey under LINE_DARK), its highest points between the teeth joined (a
# running minimum over TOOTH_SPAN px, smoothed TOOTH_SMOOTH px) and raised TOOTH_ROOT px, run flat on to TEETH_X1.
# Below it, and with the mouth under it within TOOTH_H px, the white is teeth: no wash, so they stand white against the black of the mouth
MOUTH, TOOTH_SPAN, TOOTH_SMOOTH, TOOTH_ROOT, TEETH_X1, TOOTH_H = (2200, 767), 45, 10, 6, 2372, 40
WASH_HOLE = 2000
TONE_STEPS, STEP_BLUR, STEP_MIN = [(0, 0.16), (45, 0.27), (70, 0.38)], 4.0, 600


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def plank_bottom(clay_rb):
    """The plank's lower edge (row per column of the flat), from red less blue (blurred)."""
    xs, ys = [], []
    for x in range(PLANK_X[0], PLANK_X[1], PLANK_STEP):
        col = clay_rb[:, x] > CLAY
        if not col[PLANK_ROW]:
            continue
        y = PLANK_ROW
        while col[y + 1]:
            y += 1
        xs.append(x)
        ys.append(y + 0.5)
    ys = ndi.median_filter(np.array(ys), 5, mode="nearest")
    return np.array(xs), ys


def teeth(g):
    """The teeth's area (see MOUTH), on the flat."""
    x0, y0, x1, y1 = MOUTH[0] - 60, MOUTH[1] - 150, TEETH_X1 + 40, MOUTH[1] + 80
    sub = ndi.gaussian_filter(g[y0:y1, x0:x1], 1.5) < LINE_DARK
    lab, _ = ndi.label(sub)
    mouth = lab == lab[MOUTH[1] - y0, MOUTH[0] - x0]
    cols = np.nonzero(mouth.any(0))[0]
    top = np.array([np.nonzero(mouth[:, c])[0][0] for c in cols], float)
    line = ndi.gaussian_filter1d(ndi.minimum_filter1d(top, TOOTH_SPAN, mode="nearest"), TOOTH_SMOOTH) - TOOTH_ROOT
    xs = np.arange(x1 - x0)
    root = np.interp(xs, cols, line)
    below = np.zeros_like(mouth)   # the mouth within TOOTH_H px under a point (a column either side)
    m = ndi.maximum_filter(mouth, size=(1, 5))
    for d in range(1, TOOTH_H + 1):
        below[:-d] |= m[d:]
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    out = np.zeros(g.shape, bool)
    out[y0:y1, x0:x1] = (yy >= root[xx]) & below & (xx + x0 <= TEETH_X1) & ~mouth
    return out


def scene(src):
    """(ink, figure, grey, half-tone steps [(mask, total opacity)]) on the flat."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(flat_image(src)).save(t / "c.png")
        pc(t / "c.png", t / "rbw.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": STEP_BLUR}))
        pc(t / "c.png", t / "gw.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": STEP_BLUR}))
        pc(t / "c.png", t / "rbs.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "rbs.png", t / "rb.png", ("image.adjustments.threshold", {"level": CLAY}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "g2.png", ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "g.png", t / "g1.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "c.png", t / "blue.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [0, 0, 100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": SHEEP_BLUR}))
        pc(t / "blue.png", t / "bluec.png", ("filter.other.maximum", {"radius": SHEEP_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": SHEEP_R, "preserve": "squareness"}))
        sheep_c = grey(t / "bluec.png") - grey(t / "blue.png")
        rbw = grey(t / "rbw.png")
        whiteness = np.clip(grey(t / "gw.png") - 120, 0, None) * np.clip((80 - rbw) / 60, 0, 1)
        g = grey(t / "g.png")
        rbs = grey(t / "rbs.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        g2, g1 = grey(t / "g2.png"), grey(t / "g1.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3]) for b in bs], 0)
    heads = box([b for b, _, _ in HEADS])
    white = np.any([box([b]) & (g2 > wl) & (rbs < wrb) for b, wl, wrb in HEADS], 0)   # the white paint
    hair_zone = ndi.binary_fill_holes(ndi.binary_closing(white, structure=morphology.disk(HAIR_SPAN))) & heads
    # (the clay it closes in, inside an ear or on a cheek, is not hair: red areas wider than a speck; the slave's
    # cream is as red as clay, so the white itself is not counted)
    hair_zone &= ~ndi.binary_opening(clay & ~white, structure=morphology.disk(CLAY_SPECK))
    clay |= white | (hair_zone & ~core)
    px, py = plank_bottom(rbs)
    outside = yy > np.interp(xx, px, py)
    outside |= lw.polygon_mask(g.shape, np.array(PALM_L, float))
    dark = ~clay & ~outside
    fine = box(FINE) | hair_zone
    ground0 = np.where(fine, ndi.binary_opening(dark, structure=morphology.disk(FINE_OPEN)),
                       ndi.binary_opening(dark, structure=morphology.disk(OPEN)))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    # (the figures and the plank close in large areas of ground: behind the door, between the legs)
    is_ground = size > AUTO_GROUND
    for x, y in OPEN_PTS:
        assert lab[y, x], f"open point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = True
    ground = is_ground[lab]
    for x, y in OPEN_FINE:
        r = OPEN_FINE_R
        sub = ndi.binary_opening(dark[y - r:y + r, x - r:x + r], structure=morphology.disk(FINE_OPEN))
        sl, _ = ndi.label(sub)
        assert sl[r, r], f"open point {(x, y)} is not on glaze"
        ground[y - r:y + r, x - r:x + r] |= sl == sl[r, r]
    for k in np.unique(lab[(lab > 0) & ~ground]):   # (check: the largest areas kept as paint)
        if size[k] > 3000:
            yk, xk = np.argwhere(lab == k)[0]
            print("dark kept as paint", size[k], (xk, yk))
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[y, x] for x, y in SEEDS}
    assert 0 not in keep
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: clay left out)
        if k not in keep and sz[k] > 2000:
            print("unseeded", sz[k], (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground
    f = fig.astype(np.float32)
    fig = np.where(fine, ndi.gaussian_filter(f, FINE_SMOOTH), ndi.gaussian_filter(f, SMOOTH)) > 0.5
    fig &= ~outside
    paint = dark & fig & core
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE)
    lines = (core | paint) & fig & ~edge
    lab, _ = ndi.label(lines, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    touch = np.unique(lab[ndi.binary_dilation(edge, iterations=2)])
    lines &= ~((sz < SPECK) & ~np.isin(np.arange(len(sz)), touch))[lab]
    # the hair: the figure inside the hair's outline, so each curl and strand is its own shape, edged in the tone
    strokes = fig & hair_zone & ~paint
    soft_edge = edge & (ndi.distance_transform_edt(~strokes) <= EDGE + 3)
    lines &= ~strokes
    curls = strokes & box([CURL_BOX]) & (g1 < CURL_L)
    sheep = box([SHEEP_BOX]) & (sheep_c > SHEEP_T) & strokes
    lab, _ = ndi.label(sheep)
    sheep &= (np.bincount(lab.ravel()) >= SHEEP_MIN)[lab]
    ink = lines | (edge & ~soft_edge) | curls | sheep
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    base = ((ndi.gaussian_filter(strokes.astype(np.float32), 3.0) > 0.5) | soft_edge) & fig & ~ink
    base &= ~teeth(g)
    holes = ndi.binary_fill_holes(base) & ~base & ~ink   # (specks of bare clay in the worn white: washed over)
    lab, _ = ndi.label(holes)
    base |= (np.bincount(lab.ravel()) < WASH_HOLE)[lab] & holes
    steps = []
    for level, opacity in TONE_STEPS:
        m = base & (whiteness >= level)
        lab, _ = ndi.label(m)
        m &= (np.bincount(lab.ravel()) >= STEP_MIN)[lab]
        steps.append((m, opacity))
    faces = box(FACES) & ink
    return ink & ~faces, faces, fig, g, steps


def add_tone(svg, steps, box):
    """The half tone added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of class
    "tone" in the line colour, between the body and the lines, one per step [(mask, total opacity)], each drawn
    over the last at the opacity that brings the total to its own (as acharnians.py)."""
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


def main(src, qa=None, dump=None):
    ink, faces, fig, g, steps = scene(src)
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ink=ink, faces=faces)
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=faces,
                        title="Two old men in comic masks and a small slave behind a chest, by a door: a comic stage",
                        desc="Line drawing after the Apulian red-figure bell-krater J. Paul Getty Museum 96.AE.112; "
                             "traced from the museum's photograph (CC0), taken off the vase's curve.")
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in steps], info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--refit" in sys.argv:
        fit_model(dict(zip(["front", "lprofile", "rprofile"], sys.argv[1:4])))
    elif "--flat" in sys.argv:
        Image.fromarray(flat_image(sys.argv[1])).save(sys.argv[2])
    elif "--dump" in sys.argv:
        main(sys.argv[1], sys.argv[2], dump=sys.argv[3])
    else:
        main(*sys.argv[1:3])
