"""Philoctetes: Philoctetes alone on Lemnos, seated on a rock under a tree, his
bandaged leg drawn up, his bow case at his feet, from the Attic red-figure
squat lekythos, c. 420 BCE, New York, Metropolitan Museum of Art 56.171.58
(Fletcher Fund, 1956). Photos: Marie-Lan Nguyen, 2011, CC BY 2.5 ("C", the
closest, the drawing's main source), and the Met's two Open Access photos,
CC0 ("A", DP165159, and "B", DP165160):
https://commons.wikimedia.org/wiki/File:Philoktetes_Lemnos_Met_56.171.58.jpg
https://images.metmuseum.org/CRDImages/gr/original/DP165159.jpg
https://images.metmuseum.org/CRDImages/gr/original/DP165160.jpg
The drawing traces only the ancient painting, which is public domain, so it
does not carry the photos' licences (John's ruling on Oedipus Tyrannus,
2026-10-02); the photographers are credited.

Photo -> drawing:
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
    which keeps every part within 3% of the vase's own lengths. C's camera
    was level with his head, which the flat changes by under 3%; it widens
    his right hand by about 20% and his raised leg and feet up to 1.8x.
  - C is the sharpest photo in the middle of the scene; A is sharper toward
    the sides (C is out of focus there and does not reach the rock's left
    end). Each part is taken from the sharper photo (SEAMS), and the two
    agree on the flat to about a pixel.
  - The scene is him, the rock he sits on and his bow case: one clay area.
    The tree is cut off where its trunk meets the rock (TREE_CUT, along the
    rock's own top line and the top of his hand). The black ground seen
    through the scene (WINDOWS: between his arms and his body, under his
    raised leg, under his raised foot) stays open in the dark theme too.
  - Painted lines are found by their narrowness (darker than the clay within
    a few px of them), which passes over the broad brown washes, and redrawn
    as even lines along their centres. The washes are not drawn ("the orange
    strokes don't translate to two tone"); on the rock, where the brush also
    left narrow strokes of wash, only black lines are drawn (ROCK). His hair
    and beard are drawn as the curls the brush laid (John, 2026-10-03: "For
    hair try the curls"). The top of his head is black glaze inside a
    reserved clay rim and is drawn solid, as are the bow case's black and the
    broad dark strokes outlining his feet (BLACK_AREAS, BLACK_BANDS).
  - Damage: a scratch and an abraded patch in the glaze by his right arm, and
    chips where the glaze meets the rock's left side, are left out of his
    outline (ABRASION, WORN).

    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg [qa.png]
    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg --refit
"""
import io
import sys
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

OUT = Path(__file__).resolve().parent.parent / "philoctetes.svg"

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
        img = rgb[n][:-2, :-2]  # B's last row and column are a dark border
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


# ---------------------------------------------------------------- the scene

# Colour classes, in A (C has glare on the glaze): clay is redder than CLAY_RB
# (red minus blue) and lighter than CLAY_L; glaze is less red than GLAZE_RB
# and darker than GLAZE_L; between them, the brown washes. Pale grey (less
# saturated than PALE_SAT, lighter than PALE_L; clay is far more saturated)
# is a scratch or a chip in the glaze, and counts as glaze.
CLAY_RB, CLAY_L, GLAZE_RB, GLAZE_L, PALE_SAT, PALE_L = 75, 120, 28, 70, 0.45, 60
SEED = (2000, 900)  # on his chiton (frame px): the scene is the clay joined to it
# The tree: its trunk runs into the rock where his right hand rests, with no
# line between them. It is cut off by TREE_CUT (frame px): from the black
# ground at the foot of the trunk, straight on to the tip of his index
# finger (nothing is painted there), then along the top of his hand (the
# painted line, followed by a least-cost path) to his wrist and into the
# black between the trunk and his arm.
TREE_CUT = [(975, 1318), lw.STRAIGHT, (1003, 1312), lw.STRAIGHT, (1050, 1301), lw.STRAIGHT, (1090, 1293),
            lw.STRAIGHT, (1128, 1286), (1145, 1258), (1170, 1242), (1210, 1230), (1255, 1223), lw.STRAIGHT,
            (1275, 1195)]
# The black ground seen through the scene (a point in each): between his
# right arm, his body and the rock; between his left arm and his body; under
# his raised thigh (two pieces, parted by a line of the bandage); between his
# hanging leg and the rock; under his raised foot; and a sliver where the
# rock's left end meets the ground line. These stay open; every other black
# area inside the scene is paint (the top of his head, the bow case's black).
WINDOWS = [(1635, 1256), (2213, 1024), (2550, 1431), (2699, 1675), (2490, 1804), (2857, 1902), (147, 2399)]
# The glaze is abraded in a patch against his right arm, where pale clay
# shows through in flecks; inside ABRASION (its right side along the arm's
# own edge, measured on A, 3 px out) it counts as ground. Left of LEFT_X, past
# the rock's left end, A sees the vase edge-on and blurred; that is ground too.
ABRASION = [(1380, 820), (1535, 820), (1523, 840), (1528, 860), (1529, 880), (1529, 900), (1522, 920), (1500, 940),
            (1475, 960), (1461, 980), (1447, 1000), (1430, 1020), (1424, 1040), (1380, 1040)]
LEFT_X = 98
EDGE_R = 4  # the scene's edges are smoothed by an opening and a closing this many px
# Where the glaze meets the rock's left side it is chipped, and the edge
# bites in and out by 10-20 px; inside WORN the edge is smoothed harder.
WORN, WORN_SIGMA = [(560, 1700), (830, 1700), (830, 2000), (560, 2120), (360, 2120), (360, 1960)], 12.0


def classes(rgb):
    L, RB = ndi.gaussian_filter(lum(rgb), 1.0), ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.0)
    mx = ndi.gaussian_filter(rgb.max(2), 1.0)
    sat = (mx - ndi.gaussian_filter(rgb.min(2), 1.0)) / np.maximum(mx, 1)
    glaze = ((RB < GLAZE_RB) & (L < GLAZE_L)) | (rgb.max(2) < 3)  # black off the flat counts as ground
    glaze |= (sat < PALE_SAT) & (L > PALE_L)
    clay = (RB > CLAY_RB) & (L > CLAY_L)
    return glaze, clay


def cut_path(L, pts, corridor=6):
    """A least-cost path through pts (STRAIGHT between two points joins them
    directly), held within `corridor` px of the polyline through them."""
    from skimage.draw import line
    plain = [p for p in pts if p != lw.STRAIGHT]
    rough = np.zeros(L.shape, bool)
    for (xa, ya), (xb, yb) in zip(plain[:-1], plain[1:]):
        rr, cc = line(int(ya), int(xa), int(yb), int(xb))
        rough[rr, cc] = True
    near = ndi.distance_transform_edt(~rough) <= corridor
    return lw.livewire(np.where(near, 1.0 + ndi.gaussian_filter(L, 1.2) / 8.0, 1e4), pts)


def ground_line(fr, W):
    """Per frame column, the frame row of the ground line: the upper edge of
    the dark line under the scene, y = 0 on the vase (MODEL fits it as a
    circle, to about a pixel). On A it is brownish, not as dark as the glaze,
    so the colours alone do not stop the scene there."""
    th = np.linspace(BOX_THETA[0] - 0.05, BOX_THETA[1] + 0.05, 2000)
    xy = fr["to_frame"](th, np.zeros_like(th))
    ok = np.isfinite(xy[:, 0])
    return np.interp(np.arange(W), xy[ok, 0], xy[ok, 1])


def scene(rgbA, L, ground_row):
    """The scene's area (him, the rock and the bow case), its windows (the
    black ground seen through it), and the painted black inside it."""
    glaze, _ = classes(rgbA)
    shape = glaze.shape
    glaze |= np.arange(shape[0])[:, None] >= ground_row[None, :]  # below the ground line
    glaze |= lw.polygon_mask(shape, np.array(ABRASION, float))
    glaze[:, :LEFT_X] = True
    cut = np.zeros(shape, bool)
    xy = cut_path(L, TREE_CUT).astype(int)
    cut[xy[:, 1], xy[:, 0]] = True
    cut = ndi.binary_dilation(cut, iterations=1)
    ground = ndi.binary_opening(glaze, structure=morphology.disk(2))
    lab, _ = ndi.label(~ground & ~cut)
    area = lab == lab[SEED[1], SEED[0]]
    area = ndi.binary_fill_holes(area | (cut & ndi.binary_dilation(area, iterations=2)))
    glab, _ = ndi.label(ground)
    windows = np.isin(glab, [glab[y, x] for x, y in WINDOWS]) & area
    area &= ~windows
    # smooth edges: flecks of clay in the glaze along an edge leave no notches
    area = ndi.binary_closing(ndi.binary_opening(area, structure=morphology.disk(EDGE_R)), structure=morphology.disk(EDGE_R))
    worn = lw.polygon_mask(shape, np.array(WORN, float))
    area = np.where(worn, ndi.gaussian_filter(area.astype(np.float32), WORN_SIGMA),
                    ndi.gaussian_filter(area.astype(np.float32), 2.0)) > 0.5
    lab, n = ndi.label(area)  # one piece: flecks of clay inside a window are not the scene
    area = lab == 1 + int(np.argmax(ndi.sum(np.ones(shape), lab, np.arange(1, n + 1))))
    windows = ndi.gaussian_filter(windows.astype(np.float32), 2.0) > 0.5
    painted = area & ground
    return area, windows, painted


# ---------------------------------------------------------------- the lines

# Each part from the sharper photo: C between the SEAMS (frame columns), A
# outside them, blended across each seam's span. (C is out of focus toward
# both sides and does not reach the rock's left end.)
SEAMS = ((950, 1100), (2300, 2450))
# Painted lines are found by their narrowness: a line is darker than the
# brightest pixel within LINE_SIZE px of it by a share of the clay round it
# (its depth), above LINE_HIGH to start a line and above LINE_LOW to carry it
# on, so faint stretches of a line survive and grain does not. The brown
# washes are broader than LINE_SIZE and have next to no depth. On the rock
# (ROCK: the rock he sits on, round the bow case, and the rock under his
# raised foot) some wash strokes are narrow too, and fainter than the
# painter's lines: there a line must reach ROCK_HIGH (carried on above
# ROCK_LOW). The lines are thinned to their centres and redrawn even. The
# black glaze inside the scene (the window between his hanging leg and the
# rock narrowing to a stroke along his heel; the bow case's black) is drawn
# solid where it is wide and as a line where it is not.
LINE_SIZE, LINE_LOW, LINE_HIGH, ROCK_LOW, ROCK_HIGH = 11, 0.12, 0.28, 0.2, 0.4
ROCK = [
    # the rock he sits on: from the ground left of it, under his right hand
    # and thumb, along the bottom of the black window under his arm, down the
    # left edge of his cloak where it hangs over the rock and along its hem,
    # and down the black between the rock and his hanging leg to the ground line
    [(0, 2420), (0, 1300), (950, 1300), (950, 1380), (1040, 1452), (1100, 1462), (1200, 1445), (1270, 1500),
     (1335, 1500), (1345, 1435), (1880, 1440), (1950, 1560), (2050, 1640), (2150, 1690), (2250, 1690),
     (2300, 1660), (2350, 1700), (2500, 1850), (2650, 2000), (2690, 2070), (2700, 2250), (2750, 2420)],
    # the rock under his raised foot, below its sole, right of his hanging foot
    [(2895, 1840), (3060, 1815), (3200, 1790), (3350, 1790), (3350, 2420), (3140, 2420), (3130, 2290),
     (3020, 2240), (2950, 2200), (2900, 2050)],
]
# On the rock only black lines are drawn (the bow case's lines and straps):
# a line there must have a tenth of its pixels darker than ROCK_DARK times
# the clay, and be ROCK_MIN px long. The rock's own thin strokes are brown
# dilute paint, like its washes, and are left out.
ROCK_DARK, ROCK_MIN = 0.35, 60
# Black paint the colours miss (A shows it brown-black, not as dark as the
# ground), drawn as its own filled shape: inside BLACK_AREAS (the bow case's
# black inside its outline and at its lower end), paint darker than BLACK_K
# times the clay; along BLACK_BANDS (the broad dark strokes that outline his
# feet against the rock: heel and sole of his hanging foot, its instep, and
# the sole of his raised foot; points along each, and a half-width in px),
# paint darker than BLACK_K joined by paint darker than BAND_LOW.
BLACK_K, BAND_LOW = 0.45, 0.62
BLACK_AREAS = [
    [(1860, 1790), (1960, 1790), (1990, 1900), (2030, 1990), (2030, 2100), (1930, 2100), (1900, 2000), (1860, 1960)],
    [(1950, 2190), (2130, 2190), (2130, 2310), (1950, 2310)],
]
BLACK_BANDS = [
    ([(2740, 2060), (2748, 2120), (2750, 2195), (2760, 2235), (2800, 2250), (2850, 2272), (2930, 2300), (3000, 2322),
      (3035, 2332)], 14),
    ([(2846, 1980), (2902, 2061), (2965, 2167), (3015, 2230), (3077, 2292), (3115, 2330)], 14),
    ([(2900, 1812), (2997, 1798), (3027, 1790)], 10),
]
# Paint at least 2 * THICK px wide and as dark as the glaze stays solid: the
# top of his head, the bow case's black, a thick stroke at his heel.
THICK = 6
# His hair and beard (HAIR): the curls the brush laid, drawn as their filled
# shapes (paint darker than CURL_K times the clay; specks under CURL_MIN px
# dropped). His eye (EYE): the paint itself, its strokes too close for lines.
HAIR = [(1800, 470), (1815, 380), (1850, 300), (1930, 240), (2000, 160), (2150, 140), (2330, 190), (2370, 330),
        (2360, 430), (2300, 445), (2250, 432), (2200, 428), (2150, 430), (2120, 450), (2110, 500), (2125, 545),
        (2165, 565), (2185, 600), (2165, 640), (2130, 668), (2070, 685), (2010, 680), (1960, 640), (1920, 590),
        (1870, 545), (1820, 515)]
EYE = (2140, 445, 2215, 505)
CURL_K, CURL_MIN = 0.8, 40


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


def seam_weight(rgbC):
    """C's weight in each pixel (A has the rest)."""
    x = np.arange(rgbC.shape[1], dtype=float)
    (a0, a1), (b0, b1) = SEAMS
    w = np.clip((x - a0) / (a1 - a0), 0, 1) * np.clip((b1 - x) / (b1 - b0), 0, 1)
    return w[None, :] * (ndi.binary_erosion(rgbC.max(2) > 3, iterations=8))


def darkness(rgb):
    """Each pixel's brightness over that of the clay round it, the glaze's pale
    highlights counted as dark (as antigone.paint)."""
    L = lum(rgb)
    mx, mn = rgb.max(2), rgb.min(2)
    hl = ((mx - mn) / np.maximum(mx, 1) < 0.5) & (mx > 70) & ndi.binary_dilation(ndi.gaussian_filter(L, 1.0) < 70,
                                                                                  iterations=3)
    L = np.where(ndi.binary_dilation(hl, iterations=1), np.minimum(L, 15), L)
    sm = ndi.gaussian_filter(L, 1.0)
    clay = ndi.gaussian_filter(ndi.grey_closing(sm, size=(25, 25)), 4)
    return sm / np.maximum(clay, 1.0)


def centre_lines(m, spur=6, min_len=14):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned and
    pieces under `min_len` px dropped (as in antigone.py)."""
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


def outline(area, w):
    """The scene's edge, w wide, straddling it (a quarter outside)."""
    return (area & (ndi.distance_transform_edt(area) <= 0.75 * w)) | (~area & (ndi.distance_transform_edt(~area) <= 0.25 * w))


def drawing(rgbC, rgbA, area, painted, w):
    """The ink: outline, painted lines, black paint, curls and eye."""
    from skimage.filters import apply_hysteresis_threshold
    shape = area.shape
    wC = seam_weight(rgbC)
    r = wC * darkness(rgbC) + (1 - wC) * darkness(rgbA)
    g = ndi.gaussian_filter(lum(wC[..., None] * rgbC + (1 - wC[..., None]) * rgbA), 1.0)
    depth = (ndi.grey_closing(g, size=(LINE_SIZE, LINE_SIZE)) - g) / np.maximum(
        ndi.gaussian_filter(ndi.grey_closing(g, size=(25, 25)), 4), 1.0)
    rock = np.zeros(shape, bool)
    for p in ROCK:
        rock |= poly(shape, p)
    inner = ndi.binary_erosion(area, structure=morphology.disk(4))
    hair, (x0, y0, x1, y1) = poly(shape, HAIR) & area, EYE
    eye = np.zeros(shape, bool)
    eye[y0:y1, x0:x1] = True
    black = np.zeros(shape, bool)
    for p in BLACK_AREAS:
        black |= poly(shape, p) & (r < BLACK_K)
    for pts, half in BLACK_BANDS:
        corridor = ndi.distance_transform_edt(~trace_line(shape, pts)) <= half
        lab, _ = ndi.label(corridor & (r < BAND_LOW))
        seeds = np.unique(lab[corridor & (r < BLACK_K)])
        black |= np.isin(lab, seeds[seeds > 0])
    black = ndi.binary_opening(black & area, structure=morphology.disk(1))
    black = morphology.remove_small_objects(ndi.gaussian_filter(black.astype(np.float32), 1.0) > 0.5, max_size=30)
    solid = ndi.binary_fill_holes(ndi.binary_opening(painted, structure=morphology.disk(THICK))) | black
    curls = hair & (r < CURL_K) & ~eye
    curls = ndi.gaussian_filter(ndi.binary_opening(curls, structure=morphology.disk(1)).astype(np.float32), 1.0) > 0.5
    curls = morphology.remove_small_objects(curls, max_size=CURL_MIN)
    found = np.where(rock, apply_hysteresis_threshold(depth, ROCK_LOW, ROCK_HIGH),
                     apply_hysteresis_threshold(depth, LINE_LOW, LINE_HIGH))
    lines = (found | painted) & inner & ~hair & ~eye & ~ndi.binary_dilation(solid, iterations=2)
    lines = morphology.remove_small_objects(ndi.binary_opening(lines, structure=morphology.disk(1)), max_size=40)
    cl = centre_lines(lines, min_len=25)
    # on the rock, only black lines (not the brown strokes of its washes)
    lab, n = ndi.label(cl & rock, structure=np.ones((3, 3)))
    idx = np.arange(1, n + 1)
    drop = np.zeros(n + 1, bool)
    if n:
        dark = np.array([np.percentile(r[lab == i], 10) for i in idx])
        drop[1:] = (ndi.sum(np.ones(shape), lab, idx) < ROCK_MIN) | (dark > ROCK_DARK)
    cl &= ~drop[lab]
    eye_paint = ndi.binary_opening((r < 0.62) & eye, structure=morphology.disk(1))
    ink = (ndi.distance_transform_edt(~cl) <= w / 2) | solid | curls | eye_paint | outline(area, w)
    return morphology.remove_small_objects(ink, max_size=60)


def main(pC: str, pA: str, pB: str) -> None:
    if "--refit" in sys.argv:
        fit_model({"C": pC, "A": pA, "B": pB})
        return
    _, R = vase()
    fr = frame(R)
    if "--flat" in sys.argv:  # diagnostic: the frame as each photo shows it
        stem = sys.argv[sys.argv.index("--flat") + 1]
        for name, p in (("C", pC), ("A", pA), ("B", pB)):
            Image.fromarray(flat_image(p, name, R, fr).clip(0, 255).astype(np.uint8)).save(f"{stem}_{name}.png")
        return
    rgbC, rgbA = flat_image(pC, "C", R, fr), flat_image(pA, "A", R, fr)
    if "--masks" in sys.argv:  # diagnostic: the scene over the frame
        area, windows, painted = scene(rgbA, lum(rgbC), ground_line(fr, rgbA.shape[1]))
        g = np.clip(lum(rgbA), 0, 255) * 0.55
        m = np.stack([g, g, g], -1)
        m[area] = m[area] * 0.55 + np.array([255, 60, 60]) * 0.45
        m[windows] = m[windows] * 0.5 + np.array([60, 60, 255]) * 0.5
        m[painted] = m[painted] * 0.4 + np.array([60, 255, 60]) * 0.6
        Image.fromarray(m.astype(np.uint8)).save(sys.argv[sys.argv.index("--masks") + 1])
        return
    area, windows, painted = scene(rgbA, lum(rgbC), ground_line(fr, rgbA.shape[1]))
    ys, xs = np.nonzero(area)
    w = lw.HOUSE_WEIGHT * max(np.ptp(ys), np.ptp(xs))  # the house weight, in frame px
    ink = drawing(rgbC, rgbA, area, painted, w)
    info = lw.trace_svg(
        ink, OUT, body=area, open_holes=windows,
        title="Philoctetes alone on Lemnos, seated on a rock, his bandaged leg drawn up, his bow case beside him",
        desc="Line drawing after the Attic red-figure squat lekythos, c. 420 BCE, New York, Metropolitan Museum of "
             "Art 56.171.58; traced from photographs by Marie-Lan Nguyen and the Metropolitan Museum of Art, changed.")
    print(OUT, info)
    qa = [a for a in sys.argv[4:] if not a.startswith("--")]
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        wC = seam_weight(rgbC)[..., None]
        src = lum(wC * rgbC + (1 - wC) * rgbA)
        lw.qa_overlay(src, OUT, info["box"], Path(qa[0]))
        lw.qa_dark(OUT, info["box"], Path(qa[0]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
