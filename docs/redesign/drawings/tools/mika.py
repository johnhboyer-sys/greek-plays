"""Aristophanes: the parody of Euripides' Telephus in Women at the Thesmophoria (689 ff.), the whole of side A of the
Apulian red-figure bell-krater Würzburg, Martin von Wagner Museum H 5697: at the left a woman in a veil and an
ankle-length dress, in an old woman's comic mask, holds out a large skyphos (Mika, the play's First Woman, called
Mikka at 760, asks for a bowl to catch the "baby's" blood at 754-755); at the right the Kinsman (Mnesilochus),
in a stubble-bearded mask, long trousers, a knee-length sleeved tunic and a headband, kneels on a blood-stained
altar, a knife in his right hand, in his raised left the "baby", a wineskin in little shoes; a hand mirror hangs
above them. From Rome, acquired 1977; Schiller Painter, about 370 BC. CVA Würzburg 4 (Deutschland 71, ed. G.
Güntner, 1999), pp. 13-14, Tafel 4, 1-4, Beilage 2, 1 (the entry describes side A as above; the vase is complete and
unbroken but for a chip under the lip); A. Kossatz-Deissmann, "Telephus travestitus", in Tainia (Festschrift R.
Hampe, 1980) 281 ff., pl. 60-61, its first publication; RVAp I 65 no. 4a; E. Csapo, Phoenix 40 (1986) 379 ff.
No old plate of the vase exists (it came to light in the 1970s), so the drawing is traced from photos (John,
2026-10-14). Photos: ArchaiOptix, CC BY-SA 4.0: _04 is the drawing's source, _03 serves the vase's shape. The
drawing traces only the ancient painting and carries no licence (John, 2026-10-08); the photographer is credited.
https://commons.wikimedia.org/wiki/File:Schiller_Painter_-_RVAp_4-4a_-_Thesmophoriazousai_as_phlyax_play_-_youths_-_W%C3%BCrzburg_MvWM_H_5697_-_04.jpg

It replaces the 2026-10-02 drawing of Mika alone (John, 2026-10-14: "i want the whole image, not just mika"). The
edges (John, 2026-10-14): both figures, the altar with its base, the mirror, the knife and the skyphos; the egg
bands above and below the picture left out.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli`. Two steps are geometry, not
image filtering, and stay in numpy/scipy: taking the painting off the vase's curve (vase_unroll.py) and fitting
the vase (--refit). The SVG is written by linework.trace_svg.

Photo -> flat:
  - The vase's profile and the cameras of 04 and 03 were fitted together (MODEL, as acharnians.py): to the lower
    edge of the egg band under the picture (a painted circle) in both, the vase's outline in 03 (rows clear of the
    handles), and points of the painting matched between 04 and 03 (SIFT). Both were taken on an EOS 6D with a
    50 mm lens (EXIF), so the focal length is fixed; 04 is cropped from its frame (its centre fitted). The flat
    keeps the vase's rings straight and its meridians upright, as John chose for Wasps (as thesmophoriazusae.py).

    python3 docs/redesign/drawings/tools/mika.py H5697-04.jpg [qa.png]
    python3 docs/redesign/drawings/tools/mika.py H5697-04.jpg flat.png --flat
    python3 docs/redesign/drawings/tools/mika.py flat.png [qa.png] --from-flat
    python3 docs/redesign/drawings/tools/mika.py H5697-04.jpg H5697-03.jpg --refit
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

OUT = Path(os.environ.get("MIKA_OUT", Path(__file__).resolve().parent.parent / "aristophanes-mika.svg"))
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit again; it prints these numbers). World
# units are arbitrary (camera 04's D fixes them); y = 0 on the egg band's lower edge, up the vase.
# (the fit: band median 2.7 px in 04, 2.2 in 03; 03's outline 2.9 px; matches 04->03 1.3 px, n 2728)
CAMERAS = {
    "04": dict(D=2100, H=238.262, b=-0.0537315, p=-0.014086, g=0.00638075, f=7600, cx=1772.2, cy=2439.5),
    "03": dict(D=2103.08, H=307.925, b=-0.0247162, p=-0.0171885, g=0.00892269, f=7600, cx=2736, cy=1824),
}
PROFILE_Y = [-150, 0, 150, 300, 450, 600, 750, 900]
PROFILE_R = [306.04, 393.88, 476.87, 489.53, 499.63, 503.12, 596.56, 690.06]
TURNS = {"03": -0.136}   # degrees 03 is turned from 04
D0 = 2100.0
PITCH = 10.0 / 1520.0   # mm per px on the 6D's sensor (EXIF focal plane resolution)
FOCAL_MM = {"04": 50, "03": 50}
CROPPED = {"04": True, "03": False}
# The data for fit_model: rough guides (photo px) to the egg band's lower edge under the picture, clear all along
# (band_bottom); rough guides to the vase's left (0) and right (1) outline in 03 where it
# stands clear of the handles (photo px; the strongest light-to-dark step within 70 px of them, as acharnians.py)
FIT_BAND = {"04": [(450, 3790), (1100, 3890), (1800, 3921), (2500, 3900), (3150, 3815)],
            "03": [(1550, 3290), (2200, 3330), (2900, 3345), (3600, 3335), (4200, 3290)]}
FIT_OUTLINE = {"03": {0: [(1000, 1800), (1005, 2000), (1020, 2200), (1057, 2400), (1115, 2600), (1180, 2800),
                          (1270, 3000), (1397, 3200), (1518, 3400)],
                      1: [(4682, 2000), (4690, 2200), (4667, 2400), (4636, 2600), (4576, 2800), (4500, 3000),
                          (4394, 3200), (4242, 3400)]}}
FIT_OUTLINE_UP = {"03": {0: [(1000, 450), (1000, 1050)], 1: [(4803, 600), (4757, 800), (4740, 1000)]}}
MATCH_04, MATCH_03 = 0.35, 0.35   # the scale each photo is matched at (SIFT)


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def outline(rgb, rough, half=70, step=8):
    """(side, u, v): the vase's outline row by row near the rough guides, where the light background meets the dark
    vase (the strongest step), to a fraction of a px (as acharnians.py)."""
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


def band_bottom(rgb, rough, half=70, step=8):
    """(u, v) along the egg band's lower edge: per column near the rough guide, the step from the clay strip above
    (R-B over 85 for 14 px) to the black below (R-B under 45 for 60 px), to a fraction of a px; kept where the points
    lie on one smooth curve (acharnians.band_edge turned over)."""
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5)
    r = np.array(rough, float)
    f = np.polyfit(r[:, 0], r[:, 1], min(2, len(r) - 1))
    out = []
    for u in range(int(r[0, 0]), int(r[-1, 0]), step):
        vg, col, best = int(np.polyval(f, u)), RB[:, u], None
        for v in range(vg - half, vg + half):
            above, below = col[v - 17:v - 3].mean(), col[v + 4:v + 60].mean()
            if below < 45 and above > 85 and col[v + 4:v + 60].max() < 80 and (best is None or above - below > best[0]):
                best = (above - below, v, above, below)
        if best:
            _, v, above, below = best
            mid, seg = (above + below) / 2, col[v - 8:v + 9]
            k = np.nonzero((seg[:-1] > mid) & (seg[1:] <= mid))[0]
            if len(k):
                k = k[np.argmin(abs(k - 8))]
                out.append((u, v - 8 + k + (seg[k] - mid) / (seg[k] - seg[k + 1])))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 3), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 2]


def fit_model(photos: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit). Needs opencv for SIFT."""
    import cv2
    names = ["04", "03"]
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in names}
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(n, k):
        g = cv2.resize(cv2.cvtColor(rgb[n].astype(np.uint8), cv2.COLOR_RGB2GRAY), None, fx=k, fy=k,
                       interpolation=cv2.INTER_AREA)
        kp, d = sift.detectAndCompute(g, None)
        return np.array([p.pt for p in kp]) / k, d

    ka, da = feats("04", MATCH_04)
    kb, db = feats("03", MATCH_03)
    m = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(da, db)
    a, b = np.float32([ka[x.queryIdx] for x in m]), np.float32([kb[x.trainIdx] for x in m])
    _, inl = cv2.findHomography(a, b, cv2.RANSAC, 25.0, maxIters=5000)
    inl = inl.ravel().astype(bool)
    matches = {"03": np.hstack([a[inl], b[inl]])}
    views = {}
    for n in names:
        sil = np.vstack([outline(rgb[n], r) for r in (FIT_OUTLINE.get(n), FIT_OUTLINE_UP.get(n)) if r]) \
            if n in FIT_OUTLINE else np.zeros((0, 3))
        views[n] = dict(size=rgb[n].shape[1::-1], f=FOCAL_MM[n] / PITCH, crop=CROPPED[n],
                        band=band_bottom(rgb[n], FIT_BAND[n]), sil=[tuple(r) for r in sil])
        print(n, "outline", len(sil), "band", len(views[n]["band"]), "matches", len(matches.get(n, [])))
    x0 = []
    for n, h in (("04", 370.0), ("03", 420.0)):
        x0 += [D0, h, 0.0, 0.0, 0.0, FOCAL_MM[n] / PITCH, 0.0, 0.0]
    x0 += [330.0, 380.0, 450.0, 500.0, 515.0, 520.0, 528.0, 540.0] + [0.0, 0.0] + [0.0]
    # (a loose first fit, then the outliers dropped from its result: from the start alone every band point of 03
    # lay over 30 px off and all were dropped)
    _, _, _, _, report, x1 = vu.fit(views, np.array(PROFILE_Y, float), matches=matches, d0=D0,
                                    x_start=np.array(x0), nfev=800, outlier=1e4, rounds=2)
    print("\n".join(report))
    cams, R, _, turns, report, _ = vu.fit(views, np.array(PROFILE_Y, float), matches=matches, d0=D0,
                                          x_start=x1, nfev=800, outlier=30, rounds=3)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 2) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})

# ---------------------------------------------------------------- the flat

# As thesmophoriazusae.py (John's choice for Wasps, 2026-10-10, of the flat with the rings straight over the
# shear-free one): x = R_C (theta - theta_C), y = the arc length up the profile, where R_C is the radius at CENTRE (a
# photo-04 point at the scene's middle, between the knife and his knee). G px per world unit is 04's own scale at
# CENTRE. The frame is the flat image of the photo-04 box BOX, MARGIN units wider.
FLAT_Y = (-60.0, 1000.0)
CENTRE, BOX, MARGIN = (1750.0, 2300.0), (230, 780, 3480, 3700), 10.0


def frame():
    """(cams, R, theta_C, R_C, arc table (y, t), X0, Y1, G, W, H)."""
    cams, R = vase()
    c = cams["04"]
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


def flat_image(src, name="04"):
    """Photo `name` laid onto the flat frame (H x W x 3, uint8)."""
    cams, R, th0, rc, (yt, tt), X0, Y1, G, W, H = frame()
    gx, gy = np.meshgrid(np.arange(W), np.arange(H))
    th = th0 + (X0 + gx / G) / rc + np.radians(TURNS.get(name, 0.0))
    y = np.interp(Y1 - gy / G, tt, yt)
    uv = vu.project(cams[name], vu.surface(R, y.ravel(), th.ravel())).reshape(gx.shape + (2,))
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [uv[..., 1], uv[..., 0]], order=3, cval=0) for k in range(3)], -1)
    return out.clip(0, 255).round().astype(np.uint8)


# ---------------------------------------------------------------- the scene

CLAY = 70                     # clay: red less blue above this (blurred 2 px); glaze under it
LINE_DARK = 85                # painted lines: grey darker than this (blurred 1.5 px)
# Ground: the glaze, its painted lines (up to OPEN*2 px wide) opened away; the large areas, inside the scene too.
# Smaller glaze areas inside the figures are paint.
OPEN, AUTO_GROUND = 14, 40000
# and smaller areas of ground that the figures close in (flat px, a point in each): under his thigh between his
# shin and the altar, between her feet and her hem, inside the mirror's side handle
OPEN_PTS = [(2971, 2390), (1087, 3017), (2448, 578)]
# Big dark areas that are paint, not ground (flat px, a point in each): his black hair, closed in by its clay rim
PAINT_PTS = [(3350, 790)]
# Solid paint that runs into the ground's black is taken for ground: walled where it meets it (flat px, along the
# ground's edge; WALL_W px wide)
WALLS = []
WALL_W = 8
FINE, FINE_OPEN = [], 3       # boxes (flat px) where the ground between parts is narrower (fingers)
SMOOTH, FINE_SMOOTH = 3.0, 1.5
EDGE = 9                      # the outline, flat px wide
SPECK, FLECK = 150, 200
# Lines, as thesmophoriazusae.py: the grey's local contrast (PhotoCraft: blurred 1 px, capped at the clay's level by
# Levels, input white LC_CAP; its Maximum then Minimum over LC_R px, less it), with hysteresis (LC_LOW, LC_HIGH),
# LINE_LEN px or longer along the centre, off the outline and the solid paint; each line redrawn along its centre at
# the paint's own width (half maximum), smoothed along the line over WIDTH_SIGMA px, at least LINE_MIN wide. The mask
# is smoothed first (Gaussian MASK_SIGMA in PhotoCraft, cut at half), pinholes under HOLE px^2 filled, side spurs under
# SPUR px pruned. Solid paint (his hair, the altar's zigzag): the dark (LINE_DARK) opened over SOLID_R px, drawn at its
# own shape
LC_CAP, LC_R, LC_LOW, LC_HIGH = 175, 5, 30, 50
LINE_LEN, HALF_R, WIDTH_SIGMA, LINE_MIN = 25, 6, 6.0, 4.0
HOLE, MASK_SIGMA, SPUR, SOLID_R = 12, 1.5, 7, 10
# the line weight (as thesmophoriazusae.py's)
WEIGHT = 0.0015440
# every line thickened to at least NECK flat px along its centre before tracing (as acharnians.py)
NECK = 5
# Seeds (flat px): the woman, the skyphos and its foot, the knife's blade, him and the altar, the altar's base, the
# wineskin, the mirror, its handle and the handle's end
SEEDS = [(1200, 2200), (2000, 1800), (2050, 2080), (2550, 1500), (3200, 1800), (3500, 2700), (3500, 3000),
         (4200, 1800), (2500, 600), (2500, 870), (2500, 1000)]
# The floor: the egg band's clay strip, which the woman's feet and the altar's base stand on, is cut away (John,
# 2026-10-14: the bands left out). Per column (every FLOOR_STEP px) over FLOOR_X, from the strip's lower edge (where
# its clay meets the black line under it, near FLOOR_LOW) up through the strip's clay to the first paint or glaze
# above it: her soles' painted line, the base's double line, or the ground; smoothed (a running median over
# FLOOR_MED). Below it is band
FLOOR_X, FLOOR_STEP, FLOOR_MED, FLOOR_IN, FLOOR_UP = (300, 5000), 10, 5, 12, 50
FLOOR_LOW = [(700, 3175), (1700, 3175), (2500, 3168), (3500, 3165), (4300, 3160)]
# Faces and masks are traced at their own size, not re-weighted with the rest (as thesmophoriazusae.py). Boxes,
# flat px: hers, his, and her back foot's toes (printed soft: the foot lies at the vase's edge, out of focus in both
# photos). In them marks of FACE_SPECK px^2 or more stand (his stubble's dots, 30-80 px^2)
FACES = [(1500, 750, 1950, 1350), (3000, 700, 3600, 1300), (820, 3020, 1180, 3160)]
FACE_SPECK = 12
# and there small marks the dark core misses (the stubble's dots, blurred above LINE_DARK): local contrast over
# FACE_DOT, pieces of FACE_SPECK to FACE_DOT_MAX px^2, at their own shape
FACE_DOT, FACE_DOT_MAX = 40, 400
# The altar's top: a row of triangles over a ruled line, and loops down its right side, in thinned glaze, soft edged,
# with black dots. Inside ZIGZAG (polygon, flat px) only the dark core (LINE_DARK: the ruled line, the dots) is drawn,
# at its own shape; the triangles are John's zigzag line (round 3; first drawn as a wash)
ZIGZAG = [(2985, 2290), (3880, 2270), (4130, 2440), (4130, 2580), (4040, 2540), (3870, 2400), (2985, 2420)]
# The blood (John's rulings, andromache.py): on the altar's front a splash with drips, a red mark beside it, and a
# loop with a drip on its side (CVA: "blutbefleckter Altar"), in thinned glaze. Inside BLOOD (polygons, flat px) no
# lines; a wash in the line colour following the paint: BLOOD_STEPS (grey blurred 2 px under, total opacity)
BLOOD = [[(3280, 2430), (3495, 2430), (3505, 2850), (3465, 2915), (3290, 2915), (3265, 2700)],
         [(3225, 2505), (3295, 2505), (3295, 2690), (3225, 2690)],
         [(3905, 2510), (4085, 2560), (4085, 2800), (3905, 2800)]]
BLOOD_STEPS = [(150, 0.2), (140, 0.25), (125, 0.32), (110, 0.4), (95, 0.48), (85, 0.55)]
FACE_LC = (14, 28)
PALE_OFF, PALE_MIN = 4, 30
# Her back foot's toes (John, 2026-10-14: "the feet (toes specifically) need to be traced clearly"). The foot lies at
# the vase's edge, out of focus in both photos; its four toe lines print as soft bands. Their centres, the grey's
# minima row by row on the two flats averaged (they agree within 1 px) and blurred 3 px, are drawn as strokes TOE_W
# px wide, smoothed along their length, run to the sole (flat px)
TOES = [[(934, 3110), (940, 3120), (944, 3130), (946, 3140), (952, 3150), (952, 3170)],
        [(970, 3110), (978, 3120), (982, 3130), (986, 3140), (986, 3150), (984, 3170)],
        [(1008, 3120), (1015, 3130), (1022, 3140), (1025, 3150), (1024, 3170)],
        [(1056, 3110), (1062, 3120), (1072, 3130), (1080, 3140), (1089, 3150), (1094, 3170)]]
TOE_W = 7
# John's marks, round 1 (2026-10-14, on the PhotoCraft file of pass 1: the flat cropped to the trace box at 1x,
# origin MARKS_ORIGIN in flat px), kept beside the tool as 1-bit PNGs (MARKS_FILES: blue, green). He set the photo's
# levels to bring out the fine lines (John: "i'll see about adjusting levels of original in pcraft to help") and drew
# them in blue: ink to add (the dress's finer folds, her eye and cheeks, her hem and feet, the skyphos' rim, the
# knife's edges and his fist, his cheek, the wineskin's shoes, the altar's ruled lines). Each blue stroke is drawn as
# he drew it: its centre line (side spurs under SPUR px pruned, pieces MARK_LEN px or longer), MARK_W flat px wide
# (the main lines' traced width: WEIGHT of the trace box's longer side), its edges smoothed (Gaussian MARK_SMOOTH,
# cut at half), traced at that size so the pinned weight of the rest does not move. My ink under his blue goes, so
# his line replaces mine and none is drawn twice (snapped to the photo's lines instead, the strokes came out ragged
# along the knife, the grain and the clay's edge taken for line). Where his line runs just outside the clay (the
# knife), the figure takes in the strip between. His green: my ink under it goes (the knife's and his fist's
# outlines, redrawn in blue; her soles at the floor cut). Where his blue lines close an area with the figure inside
# FEET_BOX (flat px: her soles, which he drew lower, at the strip's lower edge, so her feet take in the strip under
# them), that area is hers
# Round 2 (2026-10-15, on pass 2's file, some on the red layer: read by colour from both): blue only, the fainter
# lines I missed (his tunic's folds, his brows and cheeks, the wineskin's folds and the hand on it) and joins across
# lines I broke (John). These add to my lines; my ink under them stays (John, 2026-10-15: "those over red lines are
# additive"). Round 3 (2026-10-15, on pass 3's file): her pupil and a dark spot at the top of her veil, painted as
# filled shapes, drawn filled: marks short for their width (skeleton under BLOB_ELONG times their greatest width);
# and a zigzag along the altar's top and down its side, which replaces my wash triangles there (John, 2026-10-15:
# "Replace, keep dots": the ruled line and the dots stay). The third item of each round: whether my ink under its
# blue goes; the fourth: whether its short wide marks are filled shapes
MARKS_ORIGIN = (685, 309)
MARKS_FILES = [("mika_marks1_blue.png", "mika_marks1_green.png", True, False),
               ("mika_marks2_blue.png", "mika_marks2_green.png", False, False),
               ("mika_marks3_blue.png", "mika_marks3_green.png", False, True)]
BLOB_ELONG = 4
FEET_BOX = (760, 2940, 1760, 3200)
MARK_LEN, MARK_W, MARK_SMOOTH, MARK_GAP = 10, 6.0, 1.5, 4
# Breaks in the lines where specks of wear cross them: closed where the paint runs on under them (see join_breaks)
JOIN_D, JOIN_COS, JOIN_G, JOIN_BACK = 30, 0.75, 120, 12
FACE_MAX = 20000


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def floor(clay):
    """The row of the floor cut per column of the flat (see FLOOR_*): x, y. From FLOOR_IN px above the guide (inside
    the strip's clay) up while the clay runs on, at most FLOOR_UP px; where it runs on further (a foot's clay
    touching the strip with no painted line between) the row is taken from the columns either side."""
    lo = np.array(FLOOR_LOW, float)
    xs, ys = [], []
    for x in range(FLOOR_X[0], FLOOR_X[1], FLOOR_STEP):
        y0 = int(round(np.interp(x, lo[:, 0], lo[:, 1]))) - FLOOR_IN
        col = clay[:, x]
        if not col[y0]:   # (off the band's end)
            continue
        y = y0
        while col[y - 1] and y0 - y < FLOOR_UP:
            y -= 1
        xs.append(x)
        ys.append(y - 0.5 if y0 - y < FLOOR_UP else np.nan)
    xs, ys = np.array(xs), np.array(ys)
    ok = ~np.isnan(ys)
    ys = np.interp(xs, xs[ok], ys[ok])
    return xs, ndi.median_filter(ys, FLOOR_MED, mode="nearest")


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


def even_lines(contrast, dark, area, faces):
    """The painted lines: `dark`, and in `area` those found by local contrast, redrawn along their centres at the
    paint's own width (see LC_* and the constants after it; as thesmophoriazusae.py)."""
    from skimage.filters import apply_hysteresis_threshold
    found = apply_hysteresis_threshold(contrast, LC_LOW, LC_HIGH)
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


def join_breaks(lines, g1, room):
    """The lines' breaks closed (as thesmophoriazusae.py): skeleton ends facing each other (each end's direction, over
    its last JOIN_BACK px, within acos(JOIN_COS) of the other end) under JOIN_D px apart, where the paint runs on under
    the gap (the grey, blurred 1 px, darker than JOIN_G along it, median) and both ends lie in `room`: a stroke between
    them at the line's own width there."""
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


def marks(shape):
    """John's blue and green marks on the flat (see MARKS_*), the blue of the rounds that replace my ink, and his
    filled shapes."""
    H, W = shape
    ox, oy = MARKS_ORIGIN
    blue, green, replace, blobs = (np.zeros((H, W), bool) for _ in range(4))
    for fb, fg, rep, fill in MARKS_FILES:
        for f, m in ((fb, blue), (fg, green)) + (((fb, replace),) if rep else ()):
            a = np.asarray(Image.open(Path(__file__).parent / f).convert("L")) > 127
            m[oy:oy + a.shape[0], ox:ox + a.shape[1]] |= a[:H - oy, :W - ox]
        if fill:
            a = np.asarray(Image.open(Path(__file__).parent / fb).convert("L")) > 127
            lab, _ = ndi.label(a, structure=np.ones((3, 3)))
            sk, dt = morphology.skeletonize(a), ndi.distance_transform_edt(a)
            short = [k for k, sl in enumerate(ndi.find_objects(lab), 1)
                     if sk[sl][lab[sl] == k].sum() < BLOB_ELONG * 2 * dt[sl][lab[sl] == k].max()]
            blobs[oy:oy + a.shape[0], ox:ox + a.shape[1]] |= np.isin(lab, short)[:H - oy, :W - ox]
    return blue & ~blobs, green, replace, blobs


def johns_lines(blue):
    """John's blue strokes as he drew them, at an even width (see MARKS_* and the constants after it); and their
    centre lines."""
    cl = centre_lines(blue, spur=SPUR, min_len=MARK_LEN)
    m = (ndi.distance_transform_edt(~cl) <= MARK_W / 2).astype(np.float32)
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray((m * 255).astype(np.uint8)).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MARK_SMOOTH}))
        return grey(Path(td) / "ms.png") >= 128, cl


def scene(rgb, dump=None):
    """(ink, ink traced at its own size, figure, grey) for the flat image `rgb`."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rgb).save(t / "c.png")
        pc(t / "c.png", t / "rbs.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
           ("filter.blur.gaussianBlur", {"radius": 2}))
        pc(t / "rbs.png", t / "rb.png", ("image.adjustments.threshold", {"level": CLAY}))
        pc(t / "c.png", t / "g.png", ("image.mode.grayscale", None))
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "g1.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "g.png", t / "gc.png", ("filter.blur.gaussianBlur", {"radius": 1}),
           ("image.adjustments.levels", {"inWhite": LC_CAP}))
        pc(t / "gc.png", t / "gcc.png", ("filter.other.maximum", {"radius": LC_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": LC_R, "preserve": "squareness"}))
        contrast = grey(t / "gcc.png") - grey(t / "gc.png")
        g = grey(t / "g.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        g1 = grey(t / "g1.png")
        pc(t / "g.png", t / "g2.png", ("filter.blur.gaussianBlur", {"radius": 2}))
        g2 = grey(t / "g2.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3]) for b in bs], 0) if bs else np.zeros((H, W), bool)
    fx, fy = floor(clay)
    outside = yy > np.interp(xx, fx, fy)
    dark = ~clay & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, pts, WALL_W)
    fine = box(FINE)
    ground0 = np.where(fine, ndi.binary_opening(dark, structure=morphology.disk(FINE_OPEN)),
                       ndi.binary_opening(dark, structure=morphology.disk(OPEN)))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND
    for x, y in OPEN_PTS:
        assert lab[y, x], f"open point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = True
    for x, y in PAINT_PTS:
        assert lab[y, x], f"paint point {(x, y)} is not on glaze"
        is_ground[lab[y, x]] = False
    ground = is_ground[lab]
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
    blue, green, replace, blobs = marks(g.shape)
    feet = box([FEET_BOX])
    johns, jcl = johns_lines(blue)
    # (her feet down to his soles' centre lines; the band's glaze the strip then takes in is no paint)
    added = ndi.binary_fill_holes(ndi.binary_closing(fig | ndi.binary_dilation(jcl & feet),
                                                     structure=morphology.disk(2 * MARK_GAP))) & feet & ~fig
    fig |= added
    # (to his line's centre, not its outer edge: there the body's trace overshot the line and left a sliver of clay
    # on the dark theme)
    near = ndi.binary_dilation(jcl, iterations=MARK_GAP + 2)
    fig |= ndi.binary_fill_holes(fig | jcl) & near
    fig |= ndi.binary_closing(fig | jcl, structure=morphology.disk(MARK_GAP)) & near
    paint = dark & fig & core & ~added
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE) & ~ndi.binary_dilation(jcl, iterations=EDGE + 2)   # (his line is the edge there)
    # the faces' lines: the grey's dark core, traced at their own size
    face_box = box(FACES)
    old = (core | paint) & fig & ~edge & face_box
    lab, _ = ndi.label(old, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    touch = np.unique(lab[ndi.binary_dilation(edge, iterations=2)])
    old &= ~((sz < FACE_SPECK) & ~np.isin(np.arange(len(sz)), touch))[lab]
    dots = face_box & fig & ~edge & (contrast >= FACE_DOT) & ~ndi.binary_dilation(old, iterations=2)
    lab, _ = ndi.label(dots, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    old |= ((sz >= FACE_SPECK) & (sz <= FACE_DOT_MAX))[lab] & dots
    solid = ndi.binary_opening(paint & ~edge, structure=morphology.disk(SOLID_R))
    solid = ndi.binary_dilation(solid, iterations=2) & paint
    area = fig & ~edge & ~ndi.binary_dilation(solid, iterations=3) & ~added
    found = even_lines(contrast, core & area, area, face_box)
    pale = found & face_box & ~ndi.binary_dilation(old, iterations=PALE_OFF)
    pale = morphology.remove_small_objects(pale, max_size=PALE_MIN)
    pale = ndi.binary_dilation(pale, iterations=PALE_OFF + 1, mask=found)
    lines = solid | (found & ~face_box) | pale | old
    lines &= fig & ~edge
    lines = join_breaks(lines, g1, fig & ~solid) & fig
    # the altar's zigzag at its own shape; no lines in the blood
    zig = lw.polygon_mask(g.shape, np.array(ZIGZAG, float)) & fig
    zpaint = zig & core & ~edge
    blood = np.any([lw.polygon_mask(g.shape, np.array(b, float)) for b in BLOOD], 0) & fig
    lines = (lines & ~zig & ~blood) | zpaint
    for pts in TOES:
        P = np.array(pts, float)
        t = np.linspace(0, 1, len(P))
        tt = np.linspace(0, 1, 60)
        c = [np.polyval(np.polyfit(t, P[:, k], 2), tt) for k in (0, 1)]
        lines |= along(g.shape, list(zip(*c)), TOE_W) & fig
    old |= zpaint
    ink = lines | edge
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    faces = np.isin(lab, np.unique(lab[(face_box | zig) & ink])) & (sz < FACE_MAX)[lab] & (lab > 0)
    # John's lines, traced at their own size with the faces' (the main ink stays as the pass he marked)
    gone = ndi.binary_dilation(green, iterations=2) | ndi.binary_dilation(replace, iterations=2)
    ink &= ~gone
    faces &= ~gone
    faces |= johns | (ndi.gaussian_filter(blobs.astype(np.float32), MARK_SMOOTH) > 0.5)
    wash = [[(blood & ~ink & (g2 < level), op) for level, op in BLOOD_STEPS]]   # (the zigzag's wash: John's line now)
    if dump:
        np.savez_compressed(dump, ink=ink, faces=faces, fig=fig, ground=ground, clay=clay, core=core, solid=solid)
    return ink & ~faces, faces, fig, g, wash


def add_tone(svg, steps, box):
    """The half tone added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of class
    "tone" in the line colour, between the body and the lines, one per step [(mask, total opacity)], each drawn
    over the last at the opacity that brings the total to its own (as thesmophoriazusae.py)."""
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


def main(src, qa=None, flat_png=None, dump=None):
    rgb = np.asarray(Image.open(flat_png).convert("RGB")) if flat_png else flat_image(src)
    ink, faces, fig, g, wash = scene(rgb, dump)
    ink |= (ndi.distance_transform_edt(~morphology.skeletonize(ink)) <= NECK / 2) & fig
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT, dots=faces, extent=faces,
                        title="The Kinsman on the altar threatens the wineskin 'baby' with a knife; Mika holds out a "
                              "bowl for its blood",
                        desc="Line drawing after the Apulian red-figure bell-krater Würzburg, Martin von Wagner "
                             "Museum H 5697, side A; traced from photographs by ArchaiOptix, taken off the vase's curve.")
    for steps in wash:
        add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in steps], info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--flat" in sys.argv:   # photo flat.png [name] --flat
        a = [x for x in sys.argv[1:] if x != "--flat"]
        Image.fromarray(flat_image(a[0], *a[2:3])).save(a[1])
    elif "--refit" in sys.argv:
        fit_model(dict(zip(["04", "03"], sys.argv[1:3])))
    elif "--from-flat" in sys.argv:   # flat.png [qa.png] (a flat saved with --flat: quicker)
        a = [x for x in sys.argv[1:] if x not in ("--from-flat", "--dump")]
        main(None, a[1] if len(a) > 1 else None, flat_png=a[0],
             dump=os.environ.get("MIKA_DUMP") if "--dump" in sys.argv else None)
    else:
        main(*sys.argv[1:3])
