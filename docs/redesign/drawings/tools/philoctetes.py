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
    end). Each part is taken from the sharper photo (SEAMS). On the flat the
    two agree to 1-2 px in the middle; toward the rock's left end C drifts
    off A, 3-5 px across the seam and 6-7 px past it.
  - The scene is him, the rock he sits on and his bow case: one clay area.
    The tree is cut off where its trunk meets the rock (TREE_CUT, along the
    rock's own top line and the top of his hand). The black ground seen
    through the scene (WINDOWS: between his arms and his body, under his
    raised leg, under his raised foot) stays open in the dark theme too.
  - Painted lines are found by their narrowness (darker than the clay within
    a few px of them), which passes over the broad brown washes, and redrawn
    as even lines along their centres. The washes are not drawn ("the orange
    strokes don't translate to two tone"); on the rock, where the brush also
    left narrow strokes of wash, only black lines are drawn (ROCK). The bow
    case's black and the broad dark strokes outlining his feet are drawn solid
    (QUIVER, BLACK_BANDS).
  - His head is drawn from John's own trace (2026-10-03; TRACES): his strokes
    as lines, his filled marks (eye, brow, the marks at his neck) solid, the
    black top of his head solid with the fillet he outlined left light, and
    the area's edge following his outline. His hair and beard carry a half
    tone where the vase has its brown wash (TONE: "can you do a half-dark
    tone for the beard to mimic the tone of the original on the beard?",
    "same for hair"), a third path under the lines.
  - The outline follows the clay's own edge, not the browner stripe of glaze
    the painter laid along it (STRIPE_L, SOFT_L), and is smoothed along its
    length (EDGE_SIGMA): the photo's grain and the brush's ragged outer edge
    made it wobble. His head keeps its edge as found, and then John's.
  - Faint lines that the line test breaks up (worn stretches, a dry brush)
    are joined across their gaps (join_gaps); the bow's outer top curve,
    fainter than any test passes, is placed by hand and snapped to the paint
    (BOW_LINE), as is the outer line round the end of the strap's loop
    (STRAP_LINE). (John, 2026-10-03, on the first pass: "Not all the dark ink
    on the quiver and arrow are captured"; "part of the top outside curve of
    the bow isn't drawn".)
  - Damage: a scratch and an abraded patch in the glaze by his right arm, and
    chips where the glaze meets the rock's left side, are left out of his
    outline (GLAZE_DAMAGE, WORN).

    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg [qa.png]
    python3 docs/redesign/drawings/tools/philoctetes.py C.jpg A.jpg B.jpg --refit
"""
import io
import json
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
from euphorbos import strokes  # noqa: E402

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


# ---------------------------------------------------------------- the scene

# Colour classes, in A (C has glare on the glaze): clay is redder than CLAY_RB
# (red minus blue) and lighter than CLAY_L; glaze is less red than GLAZE_RB
# and darker than GLAZE_L; between them, the brown washes. Pale grey (less
# saturated than PALE_SAT, lighter than PALE_L; clay is far more saturated)
# is a scratch or a chip in the glaze, and counts as glaze.
CLAY_RB, CLAY_L, GLAZE_RB, GLAZE_L, PALE_SAT, PALE_L = 75, 120, 28, 70, 0.45, 60
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
# right arm, his body and the rock; between his left arm and his body; under
# his raised thigh (two pieces, parted by a line of the bandage); between his
# hanging leg and the rock; under his raised foot; and a sliver where the
# rock's left end meets the ground line. These stay open; every other black
# area inside the scene is paint (the top of his head, the bow case's black).
WINDOWS = [(1635, 1256), (2213, 1024), (2550, 1431), (2699, 1675), (2490, 1804), (2857, 1902), (147, 2399)]
# Along the figure's edge the glaze is a little browner and lighter than the
# rest (the painter's contour stripe, 3-15 px wide; A shows it at L 25-50, red
# minus blue 25-55), and the colour test leaves it to the figure, whose edge
# then follows the stripe's ragged outer side instead of the clay's crisp one.
# The ground takes in paint darker than STRIPE_L within STRIPE_REACH px of it
# (an opening of STRIPE_OPEN px keeps out painted lines that touch it), except
# in his head (HEAD), where the curls of his hair and beard reach the edge,
# and along the black strokes that outline his feet (BLACK_BANDS), which are
# paint, not stripe.
# Where a window narrows to less than 2 * WINDOW_OPEN px (down along his heel),
# it is drawn as black paint, a line or a solid shape, not as two outlines
# with a sliver between.
STRIPE_L, STRIPE_REACH, STRIPE_OPEN, WINDOW_OPEN = 55, 40, 4, 6
# Where the stripe is too narrow for that opening, or the photo soft (A sees
# the right end of the rock at 60 degrees), the edge is drawn in to the
# midpoint between clay and glaze: paint darker than SOFT_L within SOFT_REACH
# px of the ground (painted lines that end at the edge lose that much; not
# along the ground line, where his toes stand on it).
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
# length (EDGE_SIGMA px of arc), which evens out the ragged brushwork and the
# photo's grain without thinning narrow parts, as a blur of the whole area
# would. Where the glaze meets the rock's left side it is chipped and the
# edge bites in and out by 10-20 px: inside WORN it is smoothed over
# WORN_SIGMA px. His head (HEAD) keeps its edge as found (the curls, the
# profile of his face).
EDGE_R, EDGE_SIGMA = 4, 9.0
WORN, WORN_SIGMA = [(560, 1700), (830, 1700), (830, 2000), (560, 2120), (360, 2120), (360, 1960)], 15.0


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


def scene(rgbA, L, ground_row):
    """The scene's area (him, the rock and the bow case), its windows (the
    black ground seen through it), and the painted black inside it. The tree
    cut follows L, the luminance the lines are found on."""
    glaze, _ = classes(rgbA)
    shape = glaze.shape
    glaze |= np.arange(shape[0])[:, None] >= ground_row[None, :]  # below the ground line
    for p in GLAZE_DAMAGE:
        glaze |= lw.polygon_mask(shape, np.array(p, float))
    glaze[:, :LEFT_X] = True
    cut = np.zeros(shape, bool)
    xy = cut_path(L, TREE_CUT, TREE_CORRIDOR).astype(int)
    cut[xy[:, 1], xy[:, 0]] = True
    cut = ndi.binary_dilation(cut, iterations=1)
    ground = ndi.binary_opening(glaze, structure=morphology.disk(2))
    # the ground takes in the contour stripe along its edge
    keep_paint = lw.polygon_mask(shape, np.array(HEAD, float))
    for pts, half in BLACK_BANDS:
        keep_paint |= ndi.distance_transform_edt(~trace_line(shape, pts)) <= half
    stripe = (ndi.gaussian_filter(lum(rgbA), 1.0) < STRIPE_L) & ~ground & ~keep_paint
    stripe &= ndi.distance_transform_edt(~ground) <= STRIPE_REACH
    stripe = ndi.binary_opening(stripe, structure=morphology.disk(STRIPE_OPEN))
    # (only the ground round him and the windows: not the specks of glaze in a
    # wash stroke, which the stripe would swell into black blots)
    glab, _ = ndi.label(ground)
    outer = np.unique(np.r_[glab[0], glab[-1], glab[:, 0], glab[:, -1], [glab[y, x] for x, y in WINDOWS]])
    lab, _ = ndi.label(ground | stripe)
    ground |= stripe & np.isin(lab, np.unique(lab[np.isin(glab, outer[outer > 0])]))
    glab, _ = ndi.label(ground)
    outer = np.unique(np.r_[glab[0], glab[-1], glab[:, 0], glab[:, -1], [glab[y, x] for x, y in WINDOWS]])
    outer_ground = np.isin(glab, outer[outer > 0])
    near_ground = np.arange(shape[0])[:, None] >= ground_row[None, :] - 2 * SOFT_REACH
    soft = (ndi.gaussian_filter(lum(rgbA), 1.0) < SOFT_L) & ~ground & ~keep_paint & ~near_ground
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
    keep = [lab[y, x] for x, y in WINDOWS]
    windows = np.isin(lab, [k for k in keep if k > 0])
    area &= ~windows
    # smooth edges: flecks of clay in the glaze along an edge leave no notches
    area = ndi.binary_closing(ndi.binary_opening(area, structure=morphology.disk(EDGE_R)), structure=morphology.disk(EDGE_R))
    lab, n = ndi.label(area)
    area = lab == 1 + int(np.argmax(ndi.sum(np.ones(shape), lab, np.arange(1, n + 1))))
    area = smooth_outline(area, lw.polygon_mask(shape, np.array(HEAD, float)), lw.polygon_mask(shape, np.array(WORN, float)))
    lab, n = ndi.label(area)  # one piece: flecks of clay inside a window are not the scene
    area = lab == 1 + int(np.argmax(ndi.sum(np.ones(shape), lab, np.arange(1, n + 1))))
    # the windows are exactly the holes left in the smoothed area (no sliver
    # of neither between them, which the body path would fill with clay);
    # holes that are not windows are filled
    holes = ndi.binary_fill_holes(area) & ~area
    lab, _ = ndi.label(holes)
    windows = np.isin(lab, np.unique(lab[windows & holes])) & (lab > 0)
    area |= holes & ~windows
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
    [(0, 2420), (0, 1300), (950, 1300), (950, 1380), (1050, 1440), (1095, 1442), (1222, 1372), (1290, 1378),
     (1302, 1460), (1335, 1500), (1345, 1435), (1880, 1440), (1975, 1480), (2030, 1530), (2075, 1570), (2105, 1610),
     (2112, 1650), (2105, 1705), (2130, 1715), (2200, 1718), (2260, 1695), (2300, 1665), (2350, 1700),
     (2500, 1850), (2650, 2000), (2690, 2070), (2700, 2250), (2750, 2420)],
    # the rock under his raised foot, below its sole, right of his hanging foot
    [(2895, 1840), (3060, 1815), (3200, 1790), (3350, 1790), (3350, 2420), (3140, 2420), (3130, 2290),
     (3020, 2240), (2950, 2200), (2900, 2050)],
]
# On the rock only black lines are drawn: a line there must have a tenth of
# its pixels darker than ROCK_DARK times the clay, and be ROCK_MIN px long.
# The rock's own thin strokes are brown dilute paint, like its washes, and
# are left out. His gear (GEAR: the bow, the bow case and its straps) lies on
# the rock with almost no wash under it; there the lines are found as on him,
# faint ones included (the bow's inner curve, the outer curve of the case's
# lid, the straps' edges). The space between the two straps, where the rock's
# washes show, is left out of it.
ROCK_DARK, ROCK_MIN = 0.35, 60
GEAR = [(1630, 1395), (1795, 1395), (1800, 1560), (1850, 1640), (1950, 1690), (1990, 1765), (2250, 1765),
        (2335, 1795), (2365, 1860), (2365, 1990), (2250, 2005), (2150, 2005), (2120, 2100), (2250, 2120),
        (2355, 2160), (2360, 2335), (1950, 2335), (1840, 2210), (1665, 2070), (1550, 2070), (1462, 1735),
        (1622, 1580)]
GEAR_MIN = 40  # the gear's lines are long: pieces shorter than this there are wash or a crack
# Black paint the colours miss (A shows it brown-black, not as dark as the
# ground), drawn as its own filled shape. On the bow case (QUIVER: the case
# with its band of dots, the black shapes painted on it, the arrowhead, and
# the black at its foot): paint in A darker than QUIVER_SEED times the clay,
# joined by paint darker than QUIVER_GROW; each piece of it that is at least
# 2 * QUIVER_THICK px wide somewhere is filled whole, thin parts and all,
# and the thin pieces are lines. (A, not the blend: in C the glaze's sheen
# lightens the black, and the fill came out patchy. The clay it is measured
# against is the lightest within QUIVER_CLAY px: inside black wider than the
# usual 25 px window, that window finds only black.)
# Along BLACK_BANDS (the broad dark strokes that outline his feet against the
# rock: heel and sole of his hanging foot, its instep, and the sole of his
# raised foot; points along each, and a half-width in px), paint darker than
# BLACK_K joined by paint darker than BAND_LOW.
QUIVER = [(1685, 1773), (1752, 1665), (1900, 1660), (1945, 1700), (1950, 1790), (2027, 1915), (2077, 1990),
          (2093, 2107), (2043, 2157), (2127, 2190), (2143, 2307), (1977, 2323), (1918, 2223), (1835, 2107),
          (1752, 1995), (1650, 1985), (1645, 1915), (1685, 1857)]
ARROWHEAD = [(1570, 2005), (1640, 2005), (1640, 2068), (1570, 2068)]
QUIVER_SEED, QUIVER_GROW, QUIVER_THICK, QUIVER_CLAY = 0.3, 0.35, 4.5, 81
BLACK_K, BAND_LOW = 0.3, 0.45
# The bow's inner line, a fine line fainter than the rock test passes, from
# the hem of his cloak down to where the found line takes over (BOW_LINE,
# placed by hand and snapped to the paint within BOW_SNAP px).
BOW_LINE = [(1655, 1402), (1664, 1420), (1684, 1444), (1700, 1465), (1708, 1480), (1713, 1500), (1716, 1540),
            (1715, 1560), (1713, 1580), (1710, 1600), (1705, 1620), (1699, 1640), (1692, 1660), (1685, 1680),
            (1677, 1700), (1668, 1720)]
# The outer line round the right end of the strap's loop thins out there,
# just past GEAR, and the rock test drops it (John, 2026-10-03: "you also
# missed part of the strap ... for the quiver"): placed by hand the same way
# (STRAP_LINE), between the ends of the found line.
STRAP_LINE = [(2345, 1822), (2357, 1833), (2366, 1847), (2372, 1862), (2376, 1880), (2376, 1895), (2374, 1910),
              (2368, 1924)]
BOW_SNAP = 4
BLACK_BANDS = [
    ([(2700, 2040), (2745, 2075), (2765, 2105), (2750, 2140), (2735, 2180), (2727, 2212), (2735, 2235), (2770, 2248),
      (2820, 2258), (2870, 2275), (2930, 2300), (3000, 2322), (3035, 2332)], 16),
    ([(2846, 1980), (2902, 2061), (2965, 2167), (3015, 2230), (3077, 2292), (3115, 2330)], 14),
    ([(2900, 1812), (2960, 1804), (2995, 1798), (3040, 1803), (3080, 1808), (3100, 1810)], 10),
]
# Paint at least 2 * THICK px wide and as dark as the glaze stays solid: the
# top of his head, a thick stroke at his heel.
THICK = 6
# The toes of his raised foot (FINE) lie closer together than the line test
# can hold apart; there the lines are the paint itself, darker than PAINT_K
# times the clay round it, thinned to their centres.
FINE = [[(2975, 1735), (3095, 1735), (3095, 1798), (2975, 1798)]]
PAINT_K = 0.62
# Lines broken by wear or by a faint stretch of the brush are joined across
# their gaps (join_gaps): two line ends at most JOIN_GAP px apart, each
# pointing at the other within JOIN_TURN degrees, the two lines running the
# same way within JOIN_BEND degrees; the joining curve crosses no other line
# and stays inside him.
JOIN_GAP, JOIN_TURN, JOIN_BEND = 35, 30.0, 45.0
# Then a second pass for faint straight lines that the line test breaks into
# dashes (the upper strap's top edge, the case's right side): ends up to
# DASH_GAP px apart, pointing at each other within DASH_TURN degrees.
DASH_GAP, DASH_TURN, DASH_BEND = 80, 12.0, 18.0
# John's own traces (philoctetes_traces.json: his strokes as polylines along
# their centres, and the marks he filled in, registered onto this frame by
# SIFT). The head (2026-10-03): inside the region his outline encloses, and
# within a few px of his marks (the zone), his trace replaces the found
# drawing. His strokes are drawn at TRACE_PEN px, the width of his own (6-9
# px on the crop he traced, at twice this scale), his filled marks solid.
# Black glaze inside his outline (the top of the head; the brushy brown
# patches of thinner glaze inside it, holes up to TRACE_HOLE_MAX px, filled)
# is drawn solid where it spreads over TRACE_BLACK_MIN px; his strokes lying
# inside it are drawn light (the fillet he outlined round the head). The
# figure's area follows his outline: inside it is the head; within
# TRACE_NEAR px outside it only clean clay stays (the reserved rim round the
# top of the head); and where his line runs within TRACE_EDGE px of the
# area's edge, his line stands for the outline.
TRACES = {k: v for k, v in json.loads((Path(__file__).parent / "philoctetes_traces.json").read_text()).items()
          if k != "note"}
TRACE_PEN, TRACE_NEAR, TRACE_EDGE, TRACE_BLACK_MIN, TRACE_HOLE_MAX = 4.0, 20, 6, 3000, 4000
# His hair and beard get a half tone where the vase has its brown wash (John,
# 2026-10-03: "can you do a half-dark tone for the beard to mimic the tone of
# the original on the beard?", "same for hair"): paint darker than TONE_K
# times the clay within TONE_CLAY px, inside his outline of the head, drawn
# as a third path in the line colour at TONE opacity, under the lines. On a
# light page it shows grey, on the dark theme's clay a darker clay, as the
# thinned glaze does on the vase. (0.45 at first; John: "the original wasn't
# just a different tone but also somewhat less opaque".)
TONE_PARTS, TONE, TONE_K, TONE_CLAY = ("head",), 0.3, 0.72, 81


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


def join_gaps(cl, keep_in, max_gap=JOIN_GAP, max_turn=JOIN_TURN, max_bend=JOIN_BEND, look=12):
    """Curves joining the line ends of the centre lines cl across their gaps
    (as oedipus_syracuse.join_gaps, on centre lines): each end's direction is
    taken from its last `look` px; the curve may touch cl only at its two
    ends and must stay inside keep_in. Returns the curves, 1 px wide."""
    from scipy.spatial import cKDTree
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    lab, _ = ndi.label(cl, structure=np.ones((3, 3)))
    ends = np.argwhere(cl & (ndi.convolve(cl.astype(int), k, mode="constant") == 1))
    out = np.zeros_like(cl)
    if len(ends) < 2:
        return out
    heads = []
    for y, x in ends:
        path, seen, cur = [(y, x)], {(y, x)}, (y, x)
        for _ in range(look):
            nxt = [(cur[0] + dy, cur[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= cur[0] + dy < cl.shape[0] and 0 <= cur[1] + dx < cl.shape[1]
                   and cl[cur[0] + dy, cur[1] + dx] and (cur[0] + dy, cur[1] + dx) not in seen]
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
            path.append(cur)
        P = np.array(path, float)
        d = P[0] - P[len(P) // 2:].mean(0) if len(P) >= 6 else np.zeros(2)
        n = np.hypot(*d)
        heads.append(d / n if n else d)
    heads = np.array(heads)
    cos_max, cos_bend = np.cos(np.radians(max_turn)), np.cos(np.radians(max_bend))
    pairs = []
    for i, j in cKDTree(ends).query_pairs(max_gap):
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
        v = (ends[j] - ends[i]).astype(float)
        g = np.hypot(*v)
        if g < 2:
            continue
        v /= g
        a, b = heads[i] @ v, heads[j] @ -v
        if a >= cos_max and b >= cos_max and heads[i] @ -heads[j] >= cos_bend:
            pairs.append((g * (3 - a - b), i, j, g))
    used = set()
    for _, i, j, g in sorted(pairs):
        if i in used or j in used:
            continue
        p0, p3 = ends[i].astype(float), ends[j].astype(float)
        p1, p2 = p0 + heads[i] * g / 3, p3 + heads[j] * g / 3
        tt = np.linspace(0, 1, int(g * 2) + 2)[:, None]
        curve = (1 - tt) ** 3 * p0 + 3 * (1 - tt) ** 2 * tt * p1 + 3 * (1 - tt) * tt ** 2 * p2 + tt ** 3 * p3
        cy = np.clip(np.round(curve[:, 0]).astype(int), 0, cl.shape[0] - 1)
        cx = np.clip(np.round(curve[:, 1]).astype(int), 0, cl.shape[1] - 1)
        off = (np.hypot(*(curve - p0).T) > 3) & (np.hypot(*(curve - p3).T) > 3)
        if ndi.binary_dilation(cl, iterations=1)[cy[off], cx[off]].any() or not keep_in[cy, cx].all():
            continue
        used |= {i, j}
        out[cy, cx] = True
    return out


def traced(shape):
    """John's traces on the frame, per part: his strokes' centre lines, the
    marks he filled, the walls they make, the region his outline encloses,
    and the zone where his trace replaces the found drawing."""
    parts = {}
    for name, t in TRACES.items():
        centre = np.zeros(shape, bool)
        for pts in t["lines"]:
            centre |= trace_line(shape, pts)
        solids = np.zeros(shape, bool)
        for pts in t["solids"]:
            solids |= poly(shape, pts)
        walls = ndi.binary_dilation(centre, iterations=1) | solids
        inside = ndi.binary_fill_holes(ndi.binary_closing(walls, structure=morphology.disk(2)))
        parts[name] = dict(centre=centre, solids=solids, walls=walls, inside=inside,
                           zone=inside | ndi.binary_dilation(walls, iterations=6))
    return parts


def traced_area(area, windows, rgbA, parts):
    """The scene's area with each traced part's own outline: inside it is the
    figure; within TRACE_NEAR px outside it only clean clay stays."""
    _, clay = classes(rgbA)
    clay = ndi.binary_opening(clay, structure=morphology.disk(2))
    for t in parts.values():
        near = ndi.binary_dilation(t["walls"], iterations=TRACE_NEAR)
        area = (area & ~(near & ~t["inside"] & ~clay)) | t["inside"]
    lab, n = ndi.label(area)
    area = lab == 1 + int(np.argmax(ndi.sum(np.ones(area.shape), lab, np.arange(1, n + 1))))
    return ndi.binary_fill_holes(area | windows) & ~windows


def traced_ink(parts, rgbA, g):
    """The traced parts' ink (his strokes, his filled marks, the black glaze
    inside his outline, his strokes inside it light) and the half tone (g:
    the frame's luminance)."""
    glaze, _ = classes(rgbA)
    glaze = ndi.binary_closing(ndi.binary_opening(glaze, structure=morphology.disk(2)), structure=morphology.disk(3))
    rw = g / np.maximum(ndi.gaussian_filter(ndi.grey_closing(g, size=(TONE_CLAY, TONE_CLAY)), 10), 1.0)
    ink = np.zeros(g.shape, bool)
    tone = np.zeros(g.shape, bool)
    for name, t in parts.items():
        walls, inside, centre = t["walls"], t["inside"], t["centre"]
        black = glaze & inside & ~walls
        black = ndi.binary_closing(black | (walls & ndi.binary_dilation(black, iterations=3)),
                                   structure=morphology.disk(4)) & inside
        lab, n = ndi.label(ndi.binary_fill_holes(black) & ~black)
        small = np.zeros(n + 1, bool)
        small[1:] = ndi.sum(np.ones(g.shape), lab, np.arange(1, n + 1)) < TRACE_HOLE_MAX
        black = morphology.remove_small_objects(black | small[lab], max_size=TRACE_BLACK_MIN)
        lab, n = ndi.label(centre, structure=np.ones((3, 3)))
        light_piece = np.zeros(n + 1, bool)
        light_piece[1:] = ndi.mean(ndi.binary_erosion(black, iterations=2).astype(float), lab, np.arange(1, n + 1)) > 0.8
        light = ndi.binary_fill_holes(ndi.distance_transform_edt(~(centre & light_piece[lab])) <= TRACE_PEN / 2)
        black &= ~light
        ink |= ((ndi.distance_transform_edt(~centre) <= TRACE_PEN / 2) & ~light) | t["solids"] | black
        if name in TONE_PARTS:
            paint = ndi.binary_opening((rw < TONE_K) & inside, structure=morphology.disk(1))
            paint = ndi.gaussian_filter(paint.astype(np.float32), 2.0) > 0.5
            paint = morphology.remove_small_holes(morphology.remove_small_objects(paint, max_size=80), max_size=80)
            tone |= paint & ~walls & ~black
    return ink, tone


def add_tone(svg, tone, box):
    """Add the half tone to a drawing written by lw.trace_svg (box: the crop
    box it returned) as a third path, class "tone", in the line colour at TONE
    opacity, between the body and the lines."""
    x0, y0, x1, y1 = box
    d, _ = lw.potrace_d(lw.resample_ink(tone[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
    s = svg.read_text().replace('<path class="lines"', f'<path class="tone" fill="currentColor" fill-opacity="{TONE}" '
                                f'stroke="none" d="{d}"/><path class="lines"', 1)
    svg.write_text(s)


def outline(area, w):
    """The scene's edge, w wide, straddling it (a quarter outside)."""
    return (area & (ndi.distance_transform_edt(area) <= 0.75 * w)) | (~area & (ndi.distance_transform_edt(~area) <= 0.25 * w))


def drawing(rgbC, rgbA, area, painted, w, parts):
    """The ink (outline, painted lines, black paint, John's traces) and the
    half tone."""
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
    zone = np.zeros(shape, bool)
    for t in parts.values():
        zone |= t["zone"]
    LA = ndi.gaussian_filter(lum(rgbA), 1.0)
    rA = LA / np.maximum(ndi.gaussian_filter(ndi.grey_closing(LA, size=(QUIVER_CLAY, QUIVER_CLAY)), 10), 1.0)
    quiver = (poly(shape, QUIVER) | poly(shape, ARROWHEAD)) & area
    lab, _ = ndi.label(quiver & (rA < QUIVER_GROW))
    seeds = np.unique(lab[quiver & (rA < QUIVER_SEED)])
    black = ndi.gaussian_filter(np.isin(lab, seeds[seeds > 0]).astype(np.float32), 1.0) > 0.5
    lab, n = ndi.label(black)
    thick = np.zeros(n + 1, bool)
    thick[1:] = ndi.maximum(ndi.distance_transform_edt(black), lab, np.arange(1, n + 1)) >= QUIVER_THICK
    black = thick[lab]
    for pts, half in BLACK_BANDS:
        corridor = ndi.distance_transform_edt(~trace_line(shape, pts)) <= half
        lab, _ = ndi.label(corridor & (rA < BAND_LOW))
        seeds = np.unique(lab[corridor & (rA < BLACK_K)])
        black |= np.isin(lab, seeds[seeds > 0])
    black = ndi.binary_opening(black & area, structure=morphology.disk(1))
    black = morphology.remove_small_objects(ndi.gaussian_filter(black.astype(np.float32), 1.0) > 0.5, max_size=30)
    solid = ndi.binary_fill_holes(ndi.binary_opening(painted, structure=morphology.disk(THICK))) | black
    rock &= ~poly(shape, GEAR)
    found = np.where(rock, apply_hysteresis_threshold(depth, ROCK_LOW, ROCK_HIGH),
                     apply_hysteresis_threshold(depth, LINE_LOW, LINE_HIGH))
    fine = np.zeros(shape, bool)
    for p in FINE:
        fine |= poly(shape, p)
    found = np.where(fine, r < PAINT_K, found)
    lines = (found | painted) & inner & ~zone & ~ndi.binary_dilation(solid, iterations=2)
    lines = morphology.remove_small_objects(ndi.binary_opening(lines, structure=morphology.disk(1)), max_size=40)
    lines = morphology.remove_small_holes(lines, max_size=40)  # pinholes in a line thin to loops
    cl = centre_lines(lines)
    # on the rock, only black lines (not the brown strokes of its washes)
    lab, n = ndi.label(cl & rock, structure=np.ones((3, 3)))
    idx = np.arange(1, n + 1)
    drop = np.zeros(n + 1, bool)
    if n:
        dark = np.array([np.percentile(r[lab == i], 10) for i in idx])
        drop[1:] = (ndi.sum(np.ones(shape), lab, idx) < ROCK_MIN) | (dark > ROCK_DARK)
    cl &= ~drop[lab]
    cl |= join_gaps(cl, inner & ~zone & ~solid)
    cl |= join_gaps(cl, inner & ~zone & ~solid, DASH_GAP, DASH_TURN, DASH_BEND)
    gear = poly(shape, GEAR)
    lab, n = ndi.label(cl, structure=np.ones((3, 3)))
    short = np.zeros(n + 1, bool)
    short[1:] = ndi.sum(np.ones(shape), lab, np.arange(1, n + 1)) < GEAR_MIN
    cl &= ~(short[lab] & gear)
    bow = strokes(g, [BOW_LINE, STRAP_LINE], w, snap=BOW_SNAP)
    lines = (ndi.distance_transform_edt(~cl) <= w / 2) | solid | bow
    t_ink, tone = traced_ink(parts, rgbA, g)
    centre = np.zeros(shape, bool)
    for t in parts.values():
        centre |= t["centre"]
    edge = outline(area, w) & ~(ndi.distance_transform_edt(~centre) <= TRACE_EDGE)  # there his line is the edge
    ink = (lines & ~zone) | t_ink | edge
    return morphology.remove_small_objects(ink, max_size=60), tone


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
    wC = seam_weight(rgbC)[..., None]
    L = lum(wC * rgbC + (1 - wC) * rgbA)  # each part from its sharper photo, as the lines are found
    if "--masks" in sys.argv:  # diagnostic: the scene over the frame
        area, windows, painted = scene(rgbA, L, ground_line(fr, rgbA.shape[1]))
        g = np.clip(lum(rgbA), 0, 255) * 0.55
        m = np.stack([g, g, g], -1)
        m[area] = m[area] * 0.55 + np.array([255, 60, 60]) * 0.45
        m[windows] = m[windows] * 0.5 + np.array([60, 60, 255]) * 0.5
        m[painted] = m[painted] * 0.4 + np.array([60, 255, 60]) * 0.6
        Image.fromarray(m.astype(np.uint8)).save(sys.argv[sys.argv.index("--masks") + 1])
        return
    area, windows, painted = scene(rgbA, L, ground_line(fr, rgbA.shape[1]))
    parts = traced(area.shape)
    area = traced_area(area, windows, rgbA, parts)
    ys, xs = np.nonzero(area)
    w = lw.HOUSE_WEIGHT * max(np.ptp(ys), np.ptp(xs))  # the house weight, in frame px
    ink, tone = drawing(rgbC, rgbA, area, painted, w, parts)
    info = lw.trace_svg(
        ink, OUT, body=area, open_holes=windows,
        title="Philoctetes alone on Lemnos, seated on a rock, his bandaged leg drawn up, his bow case beside him",
        desc="Line drawing after the Attic red-figure squat lekythos in the manner of the Eretria Painter, c. 420 BCE, "
             "New York, Metropolitan Museum of Art 56.171.58; traced from photographs by Marie-Lan Nguyen (CC BY 2.5) "
             "and the Metropolitan Museum of Art (CC0), changed.")
    add_tone(OUT, tone, info["box"])
    print(OUT, info)
    qa = [a for a in sys.argv[4:] if not a.startswith("--")]
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(qa[0]))
        lw.qa_dark(OUT, info["box"], Path(qa[0]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
