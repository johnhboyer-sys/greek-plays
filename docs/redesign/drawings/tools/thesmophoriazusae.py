"""Women at the Thesmophoria: three masked comic actors on a stage. At the left a "stage-naked" actor (a padded
torso strapped over the costume) in a young man's mask with dark hair, holding a staff; in the middle an actor in a
young woman's dress, a cloth held up billowing over the head, wearing the white-haired mask of a wrinkled old woman;
at the right a tall actor in a crown and a white-bearded mask, holding a sceptre topped by a bird and reaching
toward the middle, read by the museum as Zeus. Apulian red-figure bell-krater, J. Paul Getty Museum 96.AE.113,
attributed to the Cotugno Painter, 370-360 BC (the museum's record). The vase names no play and is some forty years
later than Women at the Thesmophoria (411 BC): a man in a woman's dress is what the play's Kinsman is, so the link
is thematic only. Photos: the Getty's own (CC0, Open Content Program; IIIF manifest
https://media.getty.edu/iiif/manifest/3/41c5e7bf-5708-45f2-ab41-feae325e353b): "Main View, front" is the
drawing's source, "Left profile" and "Right profile" serve the vase's shape. The sister vase of Wasps
(96.AE.112, wasps.py): the same photos, the same method.

Since 2026-10-15 (John: "use the Würzburg scene for Women at the Thesmophoria, and let's use a comic actor from
apulian bell krator for home and the full apulian bell krator plate for the aristophanes page") the whole drawing is
the Aristophanes author page's figure and the crowned king, cut from it (KING_*), the home page's: the play's plate is
the Würzburg drawing (mika.py).

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli`. Two steps are geometry, not
image filtering, and stay in numpy/scipy: taking the painting off the vase's curve (vase_unroll.py) and fitting
the vase (--refit). The SVG is written by linework.trace_svg.

Photo -> flat:
  - The photos carry no focal length. The vase's profile and the three cameras were fitted together (MODEL), as
    wasps.py: to the upper edge of the meander band under the stage (where glaze lies above it), the vase's
    outline in all three (in the front view only the rows clear of the handles), and points of the painting
    matched between the front and each profile (SIFT). The focal length was tried at 20000, 30000, 40000 and
    55000 px (one for all three photos); the cost 45171, 44067, 49898, 53240, so FOCAL is 30000 (the profiles
    then turn 91 and 93 degrees from the front; matches 2.7 and 6.6 px median). The flat keeps the vase's rings
    straight and its meridians upright, as John chose for Wasps.

Flat -> drawing (approved by John on pass 5, 2026-10-12):
  - The scene is the clay joined to SEEDS (the three actors, the staff, the cloth, the sceptre and its bird, the
    plank), the handles' palmettes left out, cut at the plank's lower edge, found between the stage's posts (the
    posts left out). Pockets of ground the figures close in are opened (OPEN_PTS); the left actor's black hair and
    the king's open mouth are paint (PAINT_PTS, PAINT_POLYS).
  - Lines, as wasps.py: the grey's local contrast (a 5 px window, so the dress's close folds stay apart), each line
    redrawn along its centre at the paint's own width; in the faces the dark lines at their own shape and the
    paler, finer ones found too (FACE_LC, PALE_*; John: "dont miss those finer lines please"); lines run on
    through the white hair and beards (John: "Some lines incomplete or missing"); breaks where specks of wear
    cross a line closed (JOIN_*). On the plank only its boards' joins (PLANK_*). The sceptre's brown shaft a wash
    with its long upright lines (SCEPTRE_*); the added yellow (the bird, the dots) a wash with no outline.
  - The white hair and beards: brushstrokes of PhotoCraft's brush along the paint's grain, tapering (STROKE_*); the
    moustache round the mouth as John drew the area (BEARD); the king's two teeth white in his black mouth
    (TEETH). The bodies' thinned glaze repainted with PhotoCraft's brush along the contours, as wasps.py (BODY_*).

    python3 docs/redesign/drawings/tools/thesmophoriazusae.py front.jpg [qa.png]
    python3 docs/redesign/drawings/tools/thesmophoriazusae.py front.jpg flat.png --flat
    python3 docs/redesign/drawings/tools/thesmophoriazusae.py flat.png [qa.png] --from-flat
    python3 docs/redesign/drawings/tools/thesmophoriazusae.py front.jpg lprofile.jpg rprofile.jpg --refit 30000
"""
import json
import os
import re
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

OUT = Path(__file__).resolve().parent.parent / "thesmophoriazusae.svg"
# the drawing levelled by its ground line (John, 2026-10-22): turned by LEVEL degrees about LEVEL_C, its view box cut
# to LEVEL_VIEW so no corner of the turn shows
LEVEL, LEVEL_C, LEVEL_VIEW = -1.279, (942, 500), "11 -12 1879 1003"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit F to fit again at focal length F; it prints
# these numbers). World units are arbitrary (the front camera's D fixes them); y = 0 on the meander band's upper edge, up.
FOCAL = 30000.0
CAMERAS = {
    "front": dict(D=10000, H=1050.87, b=0.076979, p=0.000169992, g=0.0022375, f=30000, cx=3951, cy=4074),
    "lprofile": dict(D=9893.6, H=1152.33, b=0.0887205, p=-0.00147474, g=-0.0171376, f=30000, cx=3951, cy=4074),
    "rprofile": dict(D=9997.74, H=912.827, b=0.0627156, p=0.00229656, g=-0.0144241, f=30000, cx=3951, cy=4074),
}
PROFILE_PX = [-1100, -600, -100, 400, 900, 1400, 1900, 2400, 2900, 3150]   # knots, in front px above the band
PROFILE_R = [328.28, 535.96, 666.53, 729.49, 749.45, 759.96, 757.89, 769.03, 805.45, 842.09]
TURNS = {"lprofile": -90.687, "rprofile": 93.091}   # degrees each profile photo is turned from the front
D0 = 10000.0
# The data for fit_model: the rows (photo px) where each photo's outline is the vase's own (clear of the
# handles and the rim's lip), and rough guides to the meander band's upper edge (it is found only where glaze lies
# above it: between the stage's posts in the front, beside the palmettes in the profiles)
FIT_ROWS = {"front": [(1950, 2250), (4200, 6200)], "lprofile": [(1950, 6200)], "rprofile": [(1950, 6200)]}
FIT_BAND = {"front": [[(1900, 4960), (2800, 5060), (4000, 5112), (5200, 5070), (6000, 4980)]],
            "lprofile": [[(1900, 4988), (3000, 5060), (4000, 5112), (5000, 5088), (6000, 4992)]],
            "rprofile": [[(1900, 4980), (3000, 5088), (4000, 5128), (5000, 5100), (5800, 5020)]]}
BAND_V = 5110   # the band's row in the front photo, roughly (the profile's start)
BAND_CLAY = 60  # the band's clay strip: red less blue above this (this photo's clay is darker than Wasps')


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
            if above < 45 and below > BAND_CLAY and col[v - 60:v - 4].max() < 80 and (best is None or below - above > best[0]):
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


def fit_model(photos: dict, focal: float = FOCAL) -> None:
    """Refit MODEL from the three photos at focal length `focal` and print it (see vase_unroll.fit). Needs opencv for SIFT."""
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
    uc, rr = 3950.0, 2200.0   # the vase's axis and radius in the front photo, roughly
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
    k = D0 / focal
    knots = np.array(PROFILE_PX, float) * k
    s = outline(rgb["lprofile"], FIT_ROWS["lprofile"])
    left, right = s[s[:, 0] == 0], s[s[:, 0] == 1]
    hw = (np.interp(left[:, 2], right[:, 2], right[:, 1]) - left[:, 1]) / 2
    x0 = []
    for n in names:
        x0 += [D0, (BAND_V - 4074) * k, 0.0, 0.0, 0.0, focal, 0.0, 0.0]
    x0 += list(np.interp(PROFILE_PX, (BAND_V - left[::-1, 2]), hw[::-1]) * k) + [0.0, 0.0]
    x0 += [np.radians(-97.5), np.radians(97.5)]
    cams, R, _, turns, report, _ = vu.fit(views, knots, matches=matches, f_px=focal, d0=D0, rounds=3,
                                          outlier=30, nfev=1500, x_start=np.array(x0))
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{q}={c[q]:.6g}" for q in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 2) for y in knots])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})

# ---------------------------------------------------------------- the flat

# As wasps.py (John's choice there, 2026-10-10, of the flat with the rings straight over the shear-free one, which
# bowed the plank): x = R_C (theta - theta_C), y = the arc length up the profile, where R_C is the radius at CENTRE (a
# front-photo point at the scene's middle, the old woman's chest). No shear: the grid stays square, as on the vase.
# Lengths up the vase and round it at R_C are true; lower down, where the vase is narrower, round it is widened by
# R_C / R. G px per world unit is the front photo's own scale at CENTRE. The frame is the flat image of the
# front-photo box BOX, MARGIN units wider.
FLAT_Y = (-60.0, 1040.0)
CENTRE, BOX, MARGIN = (4000.0, 3500.0), (1950, 2200, 6050, 4900), 10.0


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
# and smaller areas of ground that the figures close in (flat px, a point in each): between the left actor's arm and
# his side, between the old woman's face and the cloth, under her raised arm, by her right hand
OPEN_PTS = [(1172, 1035), (2788, 644), (2639, 949), (3260, 1141)]
# Big dark areas that are paint, not ground (flat px, a point in each): the left actor's black hair, closed in by
# the clay band round his head
PAINT_PTS = [(1420, 470)]
# and dark inside these polygons (flat px) is paint: the king's open mouth, open to the ground under his teeth (John,
# 2026-10-12, the teeth white: they lie on the mouth's black), its left side inside the moustache's white curve
PAINT_POLYS = [[(4590, 604), (4720, 604), (4720, 690), (4600, 690), (4600, 668), (4593, 650), (4590, 632)]]
# Solid paint that runs into the ground's black is taken for ground: walled where it meets it (flat px, along the
# ground's edge; WALL_W px wide)
WALLS = []
WALL_W = 8
# and pockets narrower than the opening, found at FINE_OPEN within OPEN_FINE_R px of a point
OPEN_FINE, OPEN_FINE_R = [], 80
FINE, FINE_OPEN = [], 3       # boxes (flat px) where the ground between parts is narrower (fingers)
SMOOTH, FINE_SMOOTH = 3.0, 1.5
EDGE = 9                      # the outline, flat px wide
SPECK, FLECK = 150, 200
# Lines, as wasps.py: the grey's local contrast (PhotoCraft: blurred 1 px, capped at the clay's level by Levels,
# input white LC_CAP, so the white paint and pale scratches do not count; its Maximum then Minimum over LC_R px,
# less it), with hysteresis (LC_LOW, LC_HIGH), LINE_LEN px or longer along the centre, off the outline, the hair and
# the solid paint; each line redrawn along its centre at the paint's own width (where the contrast is at least half
# the line's top: half maximum), smoothed along the line over WIDTH_SIGMA px, at least LINE_MIN wide. The mask is
# smoothed first (Gaussian MASK_SIGMA in PhotoCraft, cut at half), pinholes under HOLE px^2 filled, side spurs
# under SPUR px pruned. Solid paint (the hair, the belts, the mouths): the dark (LINE_DARK) opened over SOLID_R px,
# drawn at its own shape
LC_CAP, LC_R, LC_LOW, LC_HIGH = 175, 5, 30, 50
# (LC_R 5: at 8 the window bridged the clay between the dress's close folds)
# Off the figures (outside LC_ZONES, boxes round them, flat px: on the plank) the contrast finder's hysteresis is
# stronger (CORE_LC), so the wood's grain stays out. Everywhere the dark core (LINE_DARK) is a line too
LC_ZONES = [(950, 300, 2400, 2450), (2450, 300, 3800, 2450), (3850, 150, 5600, 2450)]
CORE_LC = (45, 70)
LINE_LEN, HALF_R, WIDTH_SIGMA, LINE_MIN = 25, 6, 6.0, 4.0
HOLE, MASK_SIGMA, SPUR, SOLID_R = 12, 1.5, 7, 10
# Patterns on cloth as brushstrokes of thinned glaze (as wasps.py): inside PATTERNS (boxes, flat px) the brown
# wider than PAT_W px is a stepped wash at its own crisp edge, PAT_STEPS (grey under, total opacity)
PATTERNS = []
PAT_W, PAT_STEPS = 4, [(140, 0.35), (105, 0.6), (70, 0.9)]
# the line weight (as wasps.py's)
WEIGHT = 0.0015440
# every line thickened to at least NECK flat px along its centre before tracing (as acharnians.py)
NECK = 5
# Seeds (flat px): the left actor, his staff, the actor in the woman's dress, the cloth over her head, the king,
# his sceptre and its bird, the plank
SEEDS = [(1500, 1000), (2050, 2000), (3000, 1500), (3500, 700), (4800, 1300), (5100, 1500), (5150, 260),
         (3000, 2650)]
# The handles' palmettes are left out: all left of PALM_L and right of PALM_R (polygons, flat px)
PALM_L = [(0, 0), (640, 0), (640, 2980), (0, 2980)]
PALM_R = [(5620, 0), (6389, 0), (6389, 2980), (5620, 2980)]
# The stage's posts are cut off at the plank's lower edge (it slopes, 2680 to 2755 flat px, left to right): per
# column (every PLANK_STEP px) between the posts, the first clay above the black at PANEL_ROW, smoothed (a running
# median over PLANK_MED); the posts' columns skipped
PANEL_ROW, PLANK_STEP, PLANK_X, PLANK_MED = 2880, 25, (700, 4980), 5   # (past the last post the edge holds)
# On the plank (below PLANK_TOP, flat y: under the feet) only the boards' joins, level lines: the lines opened by a
# level bar PLANK_BAR px long (the wear's branches go), then pieces PLANK_LEN px long or more; its stains and wear
# left out
PLANK_TOP, PLANK_BAR, PLANK_LEN = 2505, 41, 150
PLANK_BARE = [(660, 2430, 870, 2560)]   # (and the plank's left end up to its top, where no foot stands: its wear)
# and the joins' breaks where the wear crosses them closed, up to PLANK_GAP px (wear leaves no line, and no gap)
PLANK_GAP = 201
# White paint (hair and beards): inside each head's box (flat px), lighter than its grey limit and less red than its
# red-less-blue limit (clay is redder): the old woman's mask, the king's
HEADS = [((2850, 420, 3200, 800), 150, 75), ((4520, 300, 5020, 1000), 150, 75)]
# The added yellow (the king's sceptre, its bird and the dots on it): yellower than the clay (green over YEL_G and
# red less blue over YEL_RB, both blurred 2 px) inside YELLOW (boxes, flat px); a stepped wash following its
# whiteness, no outline, as the white hair
YELLOW, YEL_G, YEL_RB = [(5040, 150, 5260, 2450)], 120, 110
# The king's sceptre is a shaft of thinned brown glaze with pale yellow knots, a thin black line along it: the line
# finder drew its brown and knots as a tangle of ink. Inside SCEPTRE (bands SCEPTRE_W px wide along its centre, flat
# px: above his hand and below it) only the long upright dark lines are ink (the dark core opened by an upright bar
# SCEPTRE_BAR px long, pieces SCEPTRE_LEN px or longer), and its brown a stepped wash (SCEPTRE_STEPS: grey under,
# blurred 1 px; total opacity), the knots left light
SCEPTRE = [[(5120, 330), (5118, 700), (5110, 900), (5100, 1120)],
           [(5058, 1350), (5060, 1800), (5058, 2100), (5050, 2420)]]
SCEPTRE_W, SCEPTRE_BAR, SCEPTRE_LEN = 56, 31, 80
SCEPTRE_STEPS = [(115, 0.3), (85, 0.5)]
# The bodies' brushwork (as wasps.py; John, 2026-10-10): the strokes of thinned brown glaze over the clay of the
# figures (LC_ZONES), repainted with PhotoCraft's brush along the contours, as a faint wash in the line colour
BODY_BLUR, BODY_R, BODY_RB, BODY_EDGE, BODY_OFF = 2.5, 12, 70, 18, 5
BODY_T, BODY_LEN, BODY_RATIO = 0.04, 40, 2.5
BODY_FLAT, BODY_FLOOR = 12, 2400
FLOW_SIGMA, FLOW_STEP = 10.0, 3.0
BRUSH_EXT, BRUSH_PAD, BRUSH_W, BRUSH_MIN, BRUSH_OP, BRUSH_K = 0.25, 6, 1.6, 12, 0.1, 1.2
WATER_STEPS = [(0.05, 0.05), (0.12, 0.09), (0.22, 0.13), (0.34, 0.17)]
# Faces and masks are traced at their own size, not re-weighted with the rest (as wasps.py). Boxes, flat px: the
# left actor's, the old woman's, the king's
FACES = [(1450, 430, 1730, 780), (2760, 420, 3030, 840), (4520, 330, 4820, 800)]
# In them the paler, finer lines too (FACE_LC hysteresis; as frogs.py; John, 2026-10-12, of the cloth's thin strokes
# over the old woman's brow: "dont miss those finer lines please")
FACE_LC = (14, 28)
PALE_OFF, PALE_MIN = 4, 30
# Breaks in the lines where specks of wear cross them (the dress's folds; John, 2026-10-12: "Some lines incomplete or
# missing"): closed where the paint runs on under them (see join_breaks)
JOIN_D, JOIN_COS, JOIN_G, JOIN_BACK = 30, 0.75, 120, 12
# The king's teeth in his open mouth, white like his beard but no wash, so they stand white against the black (John,
# 2026-10-12: "make the teeth white"; as wasps.py): polygons round them (flat px, read off the flat), the upper tooth
# the lower one (the white curve to the left of the mouth is the moustache: John, 2026-10-12, his line round the
# "Beard area")
TEETH = [[(4655, 617), (4706, 617), (4706, 633), (4655, 633)],
         [(4611, 631), (4669, 631), (4669, 648), (4611, 648)],
         [(4609, 648), (4641, 648), (4641, 663), (4609, 663)]]
# The king's moustache and beard round his mouth, as John drew it (2026-10-12, "Beard area": his lines round it, mapped
# to the flat by the photo beside them): the white wash and no outline inside, the mouth (and its two teeth) left
# out. Its cream curve to the left of the mouth is too warm for the white rule (HEADS): inside BEARD the paint is
# lighter than BEARD_L (grey blurred 2 px; the clay 140) and less red than BEARD_RB (red less blue; the clay 106)
BEARD = [(4580, 675), (4575, 615), (4597, 595), (4720, 591), (4724, 600), (4730, 665), (4736, 700), (4660, 705),
         (4680, 685), (4702, 665), (4711, 645), (4710, 635), (4700, 620), (4682, 607), (4660, 611), (4622, 622),
         (4596, 629), (4597, 640), (4615, 650), (4637, 656), (4642, 665), (4650, 665), (4615, 670)]
BEARD_L, BEARD_RB = 160, 95
# The white hair and beards as brushstrokes (John, 2026-10-12: "Zeus's beard should be brushstrokes", "All lighter
# hair should be brush strokes", of the moustache "the beard as wispy brushstrokes"). Inside HEADS' boxes and BEARD,
# the white paint's strokes (grey blurred 1 px lighter than ZEUS_L, in BEARD than BEARD_L, and RIDGE_D lighter than
# the grey blurred RIDGE_R px round it, so close strokes part; less red than BEARD_RB; pieces ZEUS_MIN px^2 or more)
# seed streamlines along the paint's grain (GRAIN_SIGMA), run up to STROKE_LEN px while on the paint (ROOM_D greys
# under the white's limit), kept at STROKE_MIN px or longer; each a stroke of PhotoCraft's brush STROKE_W times the
# paint's width there (at least STROKE_SIZE_MIN), hardness STROKE_HARD, opacity STROKE_OP, thinning to a point at both
# ends by pen pressure (sin^STROKE_TAPER), building up where they cross; drawn in STROKE_STEPS (paint level, total
# opacity). Lines centred on the skeleton's branches came out as specks
ZEUS_L, ZEUS_MIN, RIDGE_R, RIDGE_D = 185, 20, 4, 3
STROKE_MIN, STROKE_LEN, STROKE_W, STROKE_SIZE_MIN, STROKE_HARD, STROKE_OP = 14, 120, 1.0, 4, 0.8, 0.55
STROKE_TAPER, GRAIN_SIGMA, ROOM_D = 0.7, 4.0, 15
STROKE_STEPS = [(0.2, 0.24), (0.55, 0.38)]
FACE_MAX = 20000
HAIR_SPAN, CLAY_SPECK = 20, 10
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
    """The plank's lower edge (row per column of the flat), from red less blue (blurred): up from PANEL_ROW through
    the black between the posts to the clay."""
    xs, ys = [], []
    for x in range(PLANK_X[0], PLANK_X[1], PLANK_STEP):
        col = clay_rb[:, x] > CLAY
        if col[PANEL_ROW]:   # (a post)
            continue
        y = PANEL_ROW
        while not col[y - 1]:
            y -= 1
        xs.append(x)
        ys.append(y - 0.5)
    ys = ndi.median_filter(np.array(ys), PLANK_MED, mode="nearest")
    return np.array(xs), ys


def along(shape, pts, width):
    """A band `width` px wide along points (x, y) (as acharnians.py)."""
    P = np.array(pts, float)
    path = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])])
    m = np.zeros(shape, bool)
    m[path[:, 1].round().astype(int), path[:, 0].round().astype(int)] = True
    return ndi.distance_transform_edt(~m) <= width / 2


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as philoctetes.py)."""
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


def even_lines(contrast, dark, area, zones, faces):
    """The painted lines: `dark`, and in `area` those found by local contrast (CORE_LC outside `zones`), redrawn
    along their centres at the paint's own width (see LC_* and the constants after it)."""
    from skimage.filters import apply_hysteresis_threshold
    found = np.where(zones, apply_hysteresis_threshold(contrast, LC_LOW, LC_HIGH),
                     apply_hysteresis_threshold(contrast, *CORE_LC))
    found = np.where(faces, apply_hysteresis_threshold(contrast, *FACE_LC), found)
    firm = (found & area) | dark
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


def contour_flow(ink):
    """The direction of the contours at every px (unit vectors (dy, dx), sign arbitrary): along the level lines of
    the distance to the lines, smoothed by doubled angles over FLOW_SIGMA px."""
    gy, gx = np.gradient(ndi.distance_transform_edt(~ink))
    c2, s2 = gx * gx - gy * gy, 2 * gx * gy   # doubled angle of the gradient, weighted by its strength
    c2, s2 = ndi.gaussian_filter(c2, FLOW_SIGMA), ndi.gaussian_filter(s2, FLOW_SIGMA)
    a = np.arctan2(s2, c2) / 2 + np.pi / 2   # the gradient's angle, turned a right angle: along the contour
    return np.sin(a), np.cos(a)


def follow(start, length, flow, room):
    """A path from start (y, x) running both ways along flow for length px in all, inside room."""
    fy, fx = flow
    H, W = room.shape
    halves = []
    for sign in (1, -1):
        p, d, pts = np.array(start, float), None, []
        for _ in range(int(length / 2 / FLOW_STEP)):
            i, j = int(round(p[0])), int(round(p[1]))
            if not (0 <= i < H and 0 <= j < W and room[i, j]):
                break
            v = np.array([fy[i, j], fx[i, j]])
            if d is None:
                v = sign * v
            elif v @ d < 0:
                v = -v
            d = v
            p = p + FLOW_STEP * v
            pts.append(p.copy())
        halves.append(pts)
    return halves[1][::-1] + [np.array(start, float)] + halves[0]


def painted_strokes(m, contrast, ink, room):
    """The brushstrokes in m (see BODY_T and after it) repainted with PhotoCraft's brush along the contours; returns
    the paint (0-1)."""
    flow = contour_flow(ink)
    lab, _ = ndi.label(m, structure=np.ones((3, 3)))
    strokes = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        here = lab[sl] == k
        p = np.argwhere(here).astype(float) + (sl[0].start, sl[1].start)
        if len(p) < 20:
            continue
        ctr = p.mean(0)
        w, v = np.linalg.eigh(np.cov((p - ctr).T))
        long_, wide_ = 4 * np.sqrt(max(w[1], 0)), 4 * np.sqrt(max(w[0], 0))
        level = abs(np.degrees(np.arctan2(v[0, 1], v[1, 1])))   # (the long axis from the horizontal)
        level = min(level, 180 - level)
        if long_ < BODY_LEN or long_ < BODY_RATIO * max(wide_, 1) or level < BODY_FLAT:
            continue
        q = follow(ctr, long_ * (1 + 2 * BRUSH_EXT) + 2 * BRUSH_PAD, flow, room)
        if len(q) < 4:
            continue
        q = np.array(q)[::max(1, len(q) // 16)]
        dark = float(np.clip(np.percentile(contrast[sl][here], 80), 0, 0.2))
        strokes.append(([[round(x, 1), round(y, 1)] for y, x in q], round(max(BRUSH_W * wide_, BRUSH_MIN), 1),
                        round(min(BRUSH_OP + BRUSH_K * dark, 0.6), 3)))
    strokes.sort(key=lambda s: (s[0][0][1], s[0][0][0]))
    H, W = m.shape
    with tempfile.TemporaryDirectory() as td:
        args = [PC, "run", "--new", json.dumps({"width": W, "height": H, "background": "white"})]
        for pts, size, op in strokes:
            args += ["--cmd", "paint.stroke", "--params", json.dumps({"points": pts, "size": size, "hardness": 0.0,
                     "opacity": op, "flow": 1, "color": "#000000", "seed": 1})]
        subprocess.run(args + ["--out", str(Path(td) / "p.png")], check=True, capture_output=True, text=True)
        return 1 - grey(Path(td) / "p.png") / 255


def join_breaks(lines, g1, room):
    """The lines' breaks closed: skeleton ends facing each other (each end's direction, over its last JOIN_BACK px,
    within acos(JOIN_COS) of the other end) under JOIN_D px apart, where the paint runs on under the gap (the grey,
    blurred 1 px, darker than JOIN_G along it, median) and both ends lie in `room`: a stroke between them at the
    line's own width there."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(lines)
    k = np.ones((3, 3))
    k[1, 1] = 0
    ends = np.argwhere(sk & (ndi.convolve(sk.astype(int), k, mode="constant") == 1))
    width = 2 * ndi.distance_transform_edt(lines)

    def heading(p):
        seen, cur = {tuple(p)}, tuple(p)
        for _ in range(JOIN_BACK):
            nxt = [q for q in ((cur[0] + dy, cur[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
                   if q not in seen and 0 <= q[0] < sk.shape[0] and 0 <= q[1] < sk.shape[1] and sk[q]]
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
        v = np.asarray(p, float) - cur
        n = np.hypot(*v)
        return v / n if n else None

    out = lines.copy()
    tree = cKDTree(ends)
    hd = {}
    for i, j in sorted(tree.query_pairs(JOIN_D)):
        a, b = ends[i], ends[j]
        if not (room[tuple(a)] and room[tuple(b)]):
            continue
        for e in (i, j):
            if e not in hd:
                hd[e] = heading(ends[e])
        if hd[i] is None or hd[j] is None:
            continue
        v = (b - a).astype(float)
        d = np.hypot(*v)
        if d < 2 or hd[i] @ (v / d) < JOIN_COS or hd[j] @ (-v / d) < JOIN_COS:
            continue
        n = int(d) + 1
        ys, xs = np.linspace(a[0], b[0], n).round().astype(int), np.linspace(a[1], b[1], n).round().astype(int)
        if lines[ys, xs].all() or np.median(g1[ys, xs]) >= JOIN_G:
            continue
        w = max(min(np.median(width[tuple(a)]), np.median(width[tuple(b)])), LINE_MIN)
        out |= along(lines.shape, [(a[1], a[0]), (b[1], b[0])], w)
    return out


def white_strokes(m, light, room):
    """The white paint's strokes repainted with PhotoCraft's brush (see STROKE_*): streamlines along the paint's own
    grain (the direction of the grey's level lines, smoothed by doubled angles over GRAIN_SIGMA px), each seeded at
    the lightest paint of m no stroke covers yet, run both ways up to STROKE_LEN px while it stays in `room` (the
    paint), at the paint's own width there, thinning to a point at both ends (pen pressure); returns the paint (0-1)."""
    gy, gx = np.gradient(ndi.gaussian_filter(light, 1.5))
    c2, s2 = ndi.gaussian_filter(gx * gx - gy * gy, GRAIN_SIGMA), ndi.gaussian_filter(2 * gx * gy, GRAIN_SIGMA)
    ang = np.arctan2(s2, c2) / 2 + np.pi / 2
    flow = (np.sin(ang), np.cos(ang))
    width = 2 * ndi.distance_transform_edt(room)
    H, W = m.shape
    covered = np.zeros_like(m)
    order = np.argwhere(m)
    order = order[np.argsort(-light[m], kind="stable")]
    strokes = []
    for y, x in order:
        if covered[y, x]:
            continue
        path = follow((y, x), STROKE_LEN, flow, room)
        pts = np.array(path)
        seg = np.hypot(*np.diff(pts, axis=0).T).sum() if len(pts) > 1 else 0.0
        iy, ix = np.clip(pts[:, 0].round().astype(int), 0, H - 1), np.clip(pts[:, 1].round().astype(int), 0, W - 1)
        w = float(np.median(width[iy, ix]))
        cov = np.zeros_like(m)
        cov[iy, ix] = True
        covered |= ndi.binary_dilation(cov, iterations=max(int(w / 2), 1)) & m
        covered[y, x] = True
        if seg < STROKE_MIN:
            continue
        t = np.linspace(0, 1, len(pts))
        pr = np.maximum(np.sin(np.pi * t) ** STROKE_TAPER, 0.08)
        strokes.append(([[round(float(px), 1), round(float(py), 1), round(float(c), 3)] for (py, px), c in zip(pts, pr)],
                        round(max(STROKE_W * w, STROKE_SIZE_MIN), 1)))
    with tempfile.TemporaryDirectory() as td:
        args = [PC, "run", "--new", json.dumps({"width": W, "height": H, "background": "white"})]
        for pts, size in strokes:
            args += ["--cmd", "paint.stroke", "--params", json.dumps({"points": pts, "size": size, "hardness": STROKE_HARD,
                     "opacity": STROKE_OP, "flow": 1, "color": "#000000", "seed": 1})]
        subprocess.run(args + ["--out", str(Path(td) / "p.png")], check=True, capture_output=True, text=True)
        return 1 - grey(Path(td) / "p.png") / 255


def scene(rgb):
    """(ink, ink traced at its own size, figure, grey, white steps, pattern steps, body steps) for the flat image
    `rgb`."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rgb).save(t / "c.png")
        pc(t / "c.png", t / "rbw.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": STEP_BLUR}))
        pc(t / "c.png", t / "gw.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": STEP_BLUR}))
        pc(t / "c.png", t / "rbs.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "rbs.png", t / "rb.png", ("image.adjustments.threshold", {"level": CLAY}))
        pc(t / "c.png", t / "grn.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [0, 100, 0, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "g2.png", ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "g.png", t / "g1.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "g.png", t / "g4.png", ("filter.blur.gaussianBlur", {"radius": RIDGE_R}))
        g4 = grey(t / "g4.png")
        rbw = grey(t / "rbw.png")
        whiteness = np.clip(grey(t / "gw.png") - 120, 0, None) * np.clip((80 - rbw) / 60, 0, 1)
        g = grey(t / "g.png")
        rbs = grey(t / "rbs.png")
        green = grey(t / "grn.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        g2, g1 = grey(t / "g2.png"), grey(t / "g1.png")
        pc(t / "g.png", t / "gc.png", ("filter.blur.gaussianBlur", {"radius": 1}),
           ("image.adjustments.levels", {"inWhite": LC_CAP}))
        pc(t / "gc.png", t / "gcc.png", ("filter.other.maximum", {"radius": LC_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": LC_R, "preserve": "squareness"}))
        contrast = grey(t / "gcc.png") - grey(t / "gc.png")
        pc(t / "g.png", t / "gb.png", ("filter.blur.gaussianBlur", {"radius": BODY_BLUR}))
        pc(t / "gb.png", t / "gbc.png", ("filter.other.maximum", {"radius": BODY_R, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": BODY_R, "preserve": "roundness"}))
        pc(t / "c.png", t / "rbb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": BODY_BLUR}))
        gbc = grey(t / "gbc.png")
        body_c = (gbc - grey(t / "gb.png")) / np.maximum(gbc, 1)
        body_rb = grey(t / "rbb.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3]) for b in bs], 0) if bs else np.zeros((H, W), bool)
    heads = box([b for b, _, _ in HEADS])
    white = np.any([box([b]) & (g2 > wl) & (rbs < wrb) for b, wl, wrb in HEADS], 0)   # the white paint
    hair_zone = ndi.binary_fill_holes(ndi.binary_closing(white, structure=morphology.disk(HAIR_SPAN))) & heads
    # (the clay it closes in, inside an ear or on a cheek, is not hair: red areas wider than a speck)
    hair_zone &= ~ndi.binary_opening(clay & ~white, structure=morphology.disk(CLAY_SPECK))
    # the added yellow
    yellow = box(YELLOW) & (green > YEL_G) & (rbs > YEL_RB)
    yellow = ndi.binary_closing(yellow, structure=morphology.disk(3)) & box(YELLOW)
    clay |= white | (hair_zone & ~core) | yellow
    px, py = plank_bottom(rbs)
    outside = yy > np.interp(xx, px, py)
    outside |= lw.polygon_mask(g.shape, np.array(PALM_L, float)) | lw.polygon_mask(g.shape, np.array(PALM_R, float))
    dark = ~clay & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, pts, WALL_W)
    fine = box(FINE) | hair_zone
    ground0 = np.where(fine, ndi.binary_opening(dark, structure=morphology.disk(FINE_OPEN)),
                       ndi.binary_opening(dark, structure=morphology.disk(OPEN)))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    # (the figures and the plank close in large areas of ground: between the legs, inside the cloth's loop)
    is_ground = size > AUTO_GROUND
    for x, y in OPEN_PTS:
        assert lab[y, x], f"open point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = True
    for x, y in PAINT_PTS:
        assert lab[y, x], f"paint point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = False
    ground = is_ground[lab]
    for poly in PAINT_POLYS:
        ground &= ~lw.polygon_mask(g.shape, np.array(poly, float))
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
    assert 0 not in keep, [(x, y) for x, y in SEEDS if not lab[y, x]]
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
    # the faces' lines: the grey's dark core, traced at their own size
    face_box = box(FACES)
    old = (core | paint) & fig & ~edge & face_box
    lab, _ = ndi.label(old, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    touch = np.unique(lab[ndi.binary_dilation(edge, iterations=2)])
    old &= ~((sz < SPECK) & ~np.isin(np.arange(len(sz)), touch))[lab]
    # the brushstroke patterns
    pat = box(PATTERNS) & fig & ~edge
    brown = pat & (g1 < PAT_STEPS[0][0])
    wide = ndi.binary_opening(brown, structure=morphology.disk(PAT_W))
    wide = ndi.binary_dilation(wide, iterations=2) & brown
    # solid paint and the lines elsewhere
    solid = ndi.binary_opening(paint & ~edge, structure=morphology.disk(SOLID_R)) & ~pat
    solid = ndi.binary_dilation(solid, iterations=2) & paint
    shaft = np.any([along(g.shape, pts, SCEPTRE_W) for pts in SCEPTRE], 0) & fig
    # (the faces too: their finer, paler lines, John, 2026-10-12: "dont miss those finer lines please"; the dark core
    # alone, `old`, missed them)
    # (and the white hair and beards: the face's lines run under and through the white, John, 2026-10-12: "Some lines
    # incomplete or missing"; only the white paint itself is no line)
    area = fig & ~edge & ~white & ~yellow & ~wide & ~ndi.binary_dilation(solid, iterations=3)
    found = even_lines(contrast, core & area, area, box(LC_ZONES), face_box)
    # (in the faces the dark lines keep their own shape, `old`: redrawn they came out heavy; the finder adds only the
    # paler lines, its px more than PALE_OFF px from them, pieces of PALE_MIN px^2 or more)
    pale = found & face_box & ~ndi.binary_dilation(old, iterations=PALE_OFF)
    pale = morphology.remove_small_objects(pale, max_size=PALE_MIN)
    pale = ndi.binary_dilation(pale, iterations=PALE_OFF + 1, mask=found)   # (grown back to meet the dark lines)
    lines = solid | (found & ~face_box) | pale | old
    lines &= fig & ~edge
    # the sceptre: its long upright lines only
    rods = ndi.binary_opening(core & shaft & ~edge, structure=np.ones((SCEPTRE_BAR, 1), bool))
    lab, _ = ndi.label(rods, structure=np.ones((3, 3)))
    rods &= np.isin(lab, [k for k, sl in enumerate(ndi.find_objects(lab), 1) if sl[0].stop - sl[0].start >= SCEPTRE_LEN])
    lines = (lines & ~shaft) | rods
    lines = join_breaks(lines, g1, fig & ~shaft & ~yellow & ~(yy > PLANK_TOP) & ~solid) & fig
    # on the plank only the boards' joins: stains and wear left out
    on_plank = (yy > PLANK_TOP) | box(PLANK_BARE)
    joins = ndi.binary_opening(lines & on_plank, structure=np.ones((1, PLANK_BAR), bool))
    joins = ndi.binary_closing(joins, structure=np.ones((1, PLANK_GAP), bool)) & on_plank & fig & ~edge   # (the wear's breaks)
    lab, _ = ndi.label(joins, structure=np.ones((3, 3)))
    short = [k for k, sl in enumerate(ndi.find_objects(lab), 1) if sl[1].stop - sl[1].start < PLANK_LEN]
    lines = (lines & ~on_plank) | (joins & ~np.isin(lab, short))
    # the white hair and the yellow: the figure inside their outline, so each curl and strand is its own shape,
    # edged in the tone, no outline
    strokes = fig & ((hair_zone & ~paint) | yellow)
    soft_edge = edge & ((ndi.distance_transform_edt(~strokes) <= EDGE + 3) | lw.polygon_mask(g.shape, np.array(BEARD, float)))

    lines &= ~white & ~yellow
    ink = lines | (edge & ~soft_edge)
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    base = ((ndi.gaussian_filter(strokes.astype(np.float32), 3.0) > 0.5) | soft_edge) & fig & ~ink
    beard = lw.polygon_mask(g.shape, np.array(BEARD, float))   # (John's beard area: its cream paint)
    base |= ndi.binary_closing(beard & (g2 > BEARD_L) & (rbs < BEARD_RB), structure=morphology.disk(2)) & fig & ~ink
    base &= ~np.any([lw.polygon_mask(g.shape, np.array(t, float)) for t in TEETH], 0)   # (the teeth: white)
    pat_steps = []
    holes = ndi.binary_fill_holes(base) & ~base & ~ink   # (specks of bare clay in the worn white: washed over)
    lab, _ = ndi.label(holes)
    base |= (np.bincount(lab.ravel()) < WASH_HOLE)[lab] & holes
    for level, opacity in PAT_STEPS:
        m = wide & (g1 < level)
        lab, _ = ndi.label(m)
        m &= (np.bincount(lab.ravel()) >= 20)[lab]
        pat_steps.append((m, opacity))
    rod_steps = [(shaft & ~ink & ~yellow & (g1 < level), opacity) for level, opacity in SCEPTRE_STEPS]
    # the white hair and beards, as brushstrokes (John, 2026-10-12: "Zeus's beard should be brushstrokes", then "All
    # lighter hair should be brush strokes"): the white paint (lighter than ZEUS_L, grey blurred 1 px; inside the heads'
    # boxes and the king's beard area) repainted
    zeus = (heads | beard) & fig
    zw = zeus & (g1 > np.where(beard, BEARD_L, ZEUS_L)) & (g1 > g4 + RIDGE_D) & (rbs < BEARD_RB) & ~ink
    zw &= ~np.any([lw.polygon_mask(g.shape, np.array(t, float)) for t in TEETH], 0)
    zw = morphology.remove_small_objects(zw, max_size=ZEUS_MIN)
    room_z = zeus & (g1 > np.where(beard, BEARD_L, ZEUS_L) - ROOM_D) & (rbs < BEARD_RB) & ~ink
    paint_z = white_strokes(zw, g1, room_z) * (fig & ~ink)
    zeus_steps = [(paint_z > level, opacity) for level, opacity in STROKE_STEPS]
    base &= ~zeus
    steps = []
    for level, opacity in TONE_STEPS:
        m = base & (whiteness >= level)
        lab, _ = ndi.label(m)
        m &= ((np.bincount(lab.ravel()) >= STEP_MIN)[lab] | (m & yellow))   # (the sceptre's yellow dots are small)
        steps.append((m, opacity))
    on = (fig & box(LC_ZONES) & (to_edge > BODY_EDGE) & (body_rb > BODY_RB) & ~ndi.binary_dilation(ink, iterations=BODY_OFF)
          & ~base & ~hair_zone & ~yellow & ~ndi.binary_dilation(shaft, iterations=BODY_OFF)
          & ~ndi.binary_dilation(box(PATTERNS) & fig, iterations=BODY_OFF))
    on &= ~face_box & (yy < BODY_FLOOR)
    field = painted_strokes(on & (body_c > BODY_T), body_c, ink, fig & ~ndi.binary_dilation(ink, iterations=2)) * (fig & ~ink)
    body = [(field > level, opacity) for level, opacity in WATER_STEPS]
    # (whole pieces of ink: a box edge through the left actor's black hair left a seam; pieces larger than FACE_MAX,
    # the hair and the outline, stay with the rest)
    lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    faces = np.isin(lab, np.unique(lab[box(FACES) & ink])) & (sz < FACE_MAX)[lab] & (lab > 0)
    return ink & ~faces, faces, fig, g, steps, pat_steps + rod_steps, body, zeus_steps


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


# The crowned king alone, cut from this drawing for the Aristophanes home page (KING_OUT; John's pick, 2026-10-15): the
# figure inside KING_BOX (flat px: from his outstretched hand to his back foot, the palmette left out), cut along the
# plank's top edge (per column every KING_STEP px, up from KING_IN through the plank's clay to the first glaze or
# paint, at most KING_UP px; where it runs on further, under his feet, the row taken from the columns either side;
# smoothed over KING_MED columns), with an outline along the cut where he stands on the plank; his lines at the whole
# drawing's traced width
KING_OUT = Path(__file__).resolve().parent.parent / "aristophanes-king.svg"
KING_BOX = (3700, 0, 5600, 2700)
KING_STEP, KING_IN, KING_UP, KING_MED = 10, 2480, 120, 5


def king(ink, faces, fig, tones, rgb, info):
    """The king alone (see KING_*), written to KING_OUT; tones: the whole drawing's tone steps, in the order drawn."""
    with tempfile.TemporaryDirectory() as td:   # (the clay as scene() finds it: red less blue, blurred 2 px)
        Image.fromarray(rgb).save(Path(td) / "c.png")
        pc(Path(td) / "c.png", Path(td) / "rbs.png",
           ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        rbs = grey(Path(td) / "rbs.png")
    H, W = fig.shape
    yy, xx = np.mgrid[0:H, 0:W]
    x0, y0, x1, y1 = KING_BOX
    clay = rbs > CLAY
    xs, ys = [], []
    for x in range(x0, x1, KING_STEP):
        if not clay[KING_IN, x]:
            continue
        y = KING_IN
        while clay[y - 1, x] and KING_IN - y < KING_UP:
            y -= 1
        xs.append(x)
        ys.append(y - 0.5 if KING_IN - y < KING_UP else np.nan)
    xs, ys = np.array(xs), np.array(ys)
    ok = ~np.isnan(ys)
    ys = ndi.median_filter(np.interp(xs, xs[ok], ys[ok]), KING_MED, mode="nearest")
    inside = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < np.interp(xx, xs, ys))
    lab, _ = ndi.label(fig & inside)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    k = fig & inside & (lab == np.argmax(sz))   # (him: the largest piece; the cloth's tip and the palmette stay out)
    k = ndi.binary_fill_holes(k) & fig
    near = ndi.binary_dilation(k, iterations=2)
    sole = k & (ndi.distance_transform_edt(k) <= EDGE) & (yy > np.interp(xx, xs, ys) - 2 * EDGE)
    i, d = (ink & near) | sole, faces & near
    bx = info["box"]
    longer_all = max(bx[2] - bx[0], bx[3] - bx[1])
    ky, kx = np.nonzero(i | d)
    longer = max(ky.max() - ky.min(), kx.max() - kx.min()) + 9
    kinfo = lw.trace_svg(i, KING_OUT, body=k, open_holes=~k, weight=WEIGHT * longer_all / longer, dots=d,
                         title="A comic actor as a crowned king, white-bearded, a bird-topped sceptre in his hand, "
                               "reaching out",
                         desc="Line drawing after the Apulian red-figure bell-krater J. Paul Getty Museum 96.AE.113; "
                              "traced from the museum's photograph (CC0), taken off the vase's curve; the king cut out.")
    for steps in tones:
        add_tone(KING_OUT, [(m & k & ~i & ~d, o) for m, o in steps], kinfo["box"])
    print(KING_OUT, kinfo)
    return kinfo


def level_svg(svg):
    """The levelling turn (LEVEL) round the drawing, and its view box cut to LEVEL_VIEW."""
    s = svg.read_text()
    s = re.sub(r'viewBox="[^"]+"', f'viewBox="{LEVEL_VIEW}"', s, count=1)
    s = s.replace('<g transform="scale(', f'<g transform="rotate({LEVEL} {LEVEL_C[0]:g} {LEVEL_C[1]:g})"><g transform="scale(', 1)
    head, _, tail = s.rpartition("\n</svg>")
    svg.write_text(head + "\n</g></svg>" + tail)


def main(src, qa=None, flat_png=None):
    rgb = np.asarray(Image.open(flat_png).convert("RGB")) if flat_png else flat_image(src)
    ink, faces, fig, g, steps, washes, body, zeus_steps = scene(rgb)
    pat_steps, rod_steps = washes[:len(PAT_STEPS)], washes[len(PAT_STEPS):]
    ink |= (ndi.distance_transform_edt(~morphology.skeletonize(ink)) <= NECK / 2) & fig
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=faces,
                        title="Three comic actors on a stage: a padded young man with a staff, an actor in a woman's "
                              "dress and an old woman's mask, a crowned king with a sceptre",
                        desc="Line drawing after the Apulian red-figure bell-krater J. Paul Getty Museum 96.AE.113; "
                             "traced from the museum's photograph (CC0), taken off the vase's curve.")
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in body], info["box"])
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in pat_steps], info["box"])
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in rod_steps], info["box"])
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in steps], info["box"])
    add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in zeus_steps], info["box"])
    print(OUT, info)
    king(ink, faces, fig, [body, pat_steps, rod_steps, steps, zeus_steps], rgb, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))
    level_svg(OUT)                        # last: the check images are drawn on the unturned grid


if __name__ == "__main__":
    if "--refit" in sys.argv:
        fit_model(dict(zip(["front", "lprofile", "rprofile"], sys.argv[1:4])), float(sys.argv[sys.argv.index("--refit") + 1]))
    elif "--flat" in sys.argv:
        Image.fromarray(flat_image(sys.argv[1])).save(sys.argv[2])
    elif "--from-flat" in sys.argv:   # flat.png [qa.png] (a flat saved with --flat: quicker)
        a = [x for x in sys.argv[1:] if x != "--from-flat"]
        main(None, a[1] if len(a) > 1 else None, flat_png=a[0])
    else:
        main(*sys.argv[1:3])
