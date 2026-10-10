"""Antigone: Antigone with her hands bound behind her, brought before Creon,
from the Apulian red-figure amphora of Panathenaic shape by the Darius
Painter, c. 350-320 BCE, found at Ceglie del Campo, Berlin, Antikensammlung
F 3240 (RVAp 18/23). Body A, upper frieze: a guard with a spear, Antigone
with bound hands, a boy, Heracles talking to Creon enthroned, two youths.
Photos: ArchaiOptix, CC BY-SA 4.0, so the drawing is CC BY-SA 4.0; _04 is the
drawing's source, _05 and _06 serve the vase's shape:
https://commons.wikimedia.org/wiki/File:Darius_Painter_-_RVAp_18-23_-_Antigone_-_judgement_of_Paris_-_Eros_with_youths_and_women_-_Berlin_AS_F_3240_-_04.jpg

Redrawn with PhotoCraft (John, 2026-10-09); the first tool of this name (2026-10-02/03, drawn from John's
traces of her hands and face) is in git history.

Photo -> flat (vase_unroll.py; geometry, so numpy and scipy, not PhotoCraft), as approved on 2026-10-02:
  - Her profile and the cameras of 04, 05 and 06 were fitted together (MODEL): to the upper border of
    the animal frieze under her feet (a painted circle) in all three, the vase's right-hand outline in
    06, and points of the painting matched between 04 and the other two. All three photos were taken on
    an EOS 6D, 04 and 05 at 50 mm, 06 at 40 mm (EXIF), so the focal lengths are fixed; 04 and 05 are
    uncropped. The vase is flattened without shear (vase_unroll.flatten) about her axis, and 04 laid
    onto it at 04's own scale at her waist. Unflattened, the photo shortens her feet and lower skirt by
    up to 13%.

Flat -> drawing: every image step runs in PhotoCraft (`photocraft-cli` 0.2.0): the crop, the
enlargement, the grey, the clay map (Channel Mixer, red less blue), the blurs, the Maximum and Minimum
filters and the thresholds. numpy only combines PhotoCraft's masks and measures. The SVG is written by
linework.trace_svg.

    python3 docs/redesign/drawings/tools/antigone.py 04.jpg 05.jpg 06.jpg [qa.png]
    python3 docs/redesign/drawings/tools/antigone.py 04.jpg 05.jpg 06.jpg --refit
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

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "antigone.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit
# again; it prints these numbers). World units are arbitrary (camera 04's D
# fixes them); y = 0 on the frieze's upper border, up the vase.
CAMERAS = {
    "04": dict(D=2100, H=691.744, b=0.298613, p=0.0263557, g=0.00720429, f=7600, cx=2736, cy=1824),
    "05": dict(D=2032.08, H=540.156, b=0.196177, p=0.120581, g=0.068141, f=7600, cx=1824, cy=2736),
    "06": dict(D=2373.41, H=776.763, b=0.318218, p=-0.0102281, g=-0.012863, f=6080, cx=2736, cy=1824),
}
PROFILE_Y = [-700, -500, -300, -100, 100, 300, 500, 700, 900, 1100, 1300]
PROFILE_R = [907.6, 929.3, 951.2, 958.2, 953.8, 925.6, 872.8, 808.8, 744.8, 680.9, 616.9]
TURNS = {"05": -3.682, "06": -33.217}  # degrees each photo is turned from 04
F50, F40 = 50.0 / (10.0 / 1520.0), 40.0 / (10.0 / 1520.0)  # px: focal length over the 6D's pixel pitch
# The data for fit_model: rough guides to the frieze's upper border where it
# shows (figures stand on it elsewhere), the rows of 06's right-hand outline,
# and the scales at which points are matched.
FIT_BAND = {"04": [[(30, 3412), (400, 3492), (800, 3560), (1040, 3600)],
                   [(3650, 3600), (4000, 3540), (4400, 3440), (4800, 3320), (5200, 3220), (5440, 3165)]],
            "05": [[(30, 4751), (1000, 4786), (2000, 4757), (3000, 4643), (3620, 4475)]],
            "06": [[(522, 2459), (1000, 2680), (1411, 2848), (2000, 2925), (2522, 2959), (3000, 2955), (3633, 2922),
                    (4200, 2800), (4744, 2644), (5226, 2404)]]}
FIT_ROWS_06 = (100, 3500)
FIT_MATCH = {"05": 0.4, "06": 0.6}


def vase():
    return {n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(PROFILE_Y, PROFILE_R)


def fit_model(photos: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit)."""
    from skimage.feature import SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in photos}
    views = {}
    for n in ("04", "05", "06"):
        band = np.vstack([vu.band_line(rgb[n], r) for r in FIT_BAND[n]])
        views[n] = dict(size=rgb[n].shape[1::-1], f=F40 if n == "06" else F50, band=band, sil=[])
    s6 = vu.silhouette(rgb["06"], *FIT_ROWS_06, step=8)
    views["06"]["sil"] = [(1, r[2], r[0]) for r in s6 if np.isfinite(r[2])]

    def feats(a, k):
        g = Image.fromarray(lum(a).clip(0, 255).astype(np.uint8))
        g = np.asarray(g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS), dtype=np.float32) / 255
        s = SIFT(upsampling=1, n_octaves=5, c_dog=0.006)
        s.detect_and_extract(g)
        return s.keypoints[:, ::-1] / k, s.descriptors

    k4, d4 = feats(rgb["04"], 0.4)
    matches = {}
    for n, k in FIT_MATCH.items():
        kn, dn = feats(rgb[n], k)
        m = match_descriptors(d4, dn, max_ratio=0.8, cross_check=True)
        _, inl = ransac((k4[m[:, 0]], kn[m[:, 1]]), ProjectiveTransform, min_samples=4, residual_threshold=80,
                        max_trials=5000, rng=0)
        matches[n] = np.hstack([k4[m[inl, 0]], kn[m[inl, 1]]])
    x0 = []
    for n in ("04", "05", "06"):
        x0 += [2100.0, 700.0, 0.25, 0.0, 0.0, views[n]["f"], 0.0, 0.0]
    x0 += [1000.0] * len(PROFILE_Y) + [0.0, 0.0] + [-0.06, -0.58]
    cams, R, _, turns, report, _ = vu.fit(views, np.array(PROFILE_Y, float), matches=matches, d0=2100.0,
                                          x_start=np.array(x0), nfev=400, outlier=30)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


# ---------------------------------------------------------------- the flat

# The vase flattened over FLAT_THETA x FLAT_Y (start, stop, step), its
# meridian CENTRE (her axis, between her head and her feet in 04) straight
# up; G px per world unit (04's own scale at her waist). The frame is the
# flat image of the photo-04 box BOX04 around her, MARGIN units wider.
FLAT_THETA, FLAT_Y, CENTRE, G = (-0.7, 0.7001, 0.008), (-200.0, 1150.1, 8.0), 0.0463, 6.117
BOX04, MARGIN = (2200, 150, 3450, 3550), 40.0


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def flat_image(p04):
    """Photo 04 laid onto the flat frame: (H x W x 3, and a function from
    frame px to photo-04 px)."""
    cams, R = vase()
    c = cams["04"]
    th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
    XY = vu.flatten(R, th, yy, centre=CENTRE)
    TH, Y = np.meshgrid(th, yy)
    inv = LinearNDInterpolator(XY.reshape(-1, 2), np.stack([TH.ravel(), Y.ravel()], -1))
    fwd = [RegularGridInterpolator((yy, th), XY[..., k]) for k in (0, 1)]
    x0, y0, x1, y1 = BOX04
    corners = vu.photo_to_surface(c, R, np.array([(x0, y0), (x1, y0), (x0, y1), (x1, y1)], float), (yy[0], yy[-1]))
    q = np.c_[corners[:, 1], corners[:, 0]]
    fx, fy = fwd[0](q), fwd[1](q)
    X0, X1, Y0, Y1 = fx.min() - MARGIN, fx.max() + MARGIN, fy.min() - MARGIN, fy.max() + MARGIN
    W, H = int((X1 - X0) * G), int((Y1 - Y0) * G)

    def to_photo(X, Y):
        ty = inv(np.stack([X0 + np.ravel(X) / G, Y1 - np.ravel(Y) / G], -1))
        return vu.project(c, vu.surface(R, ty[:, 1], ty[:, 0]))

    step = 4
    gx, gy = np.meshgrid(np.arange(0, W + step, step), np.arange(0, H + step, step))
    uv = to_photo(gx, gy).reshape(gx.shape + (2,))
    u = ndi.zoom(np.nan_to_num(uv[..., 0], nan=-1e4), step, order=1)[:H, :W]
    v = ndi.zoom(np.nan_to_num(uv[..., 1], nan=-1e4), step, order=1)[:H, :W]
    a = np.asarray(Image.open(p04).convert("RGB"), dtype=np.float32)
    out = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=1, cval=0) for k in range(3)], -1)
    return out, to_photo


# ---------------------------------------------------------------- her

BOX = (150, 230, 1420, 3720)   # frame px: her crop
UP = 2                          # work at 2x the frame's px, so curves stay smooth
SEED = (900, 2300)              # frame px, on her skirt: she is the clay joined to it
# Clay: red less blue (PhotoCraft's Channel Mixer, lightly blurred) above CLAY; the glaze, its white sheen
# and the painted lines read near 0, her clay about 200 (the plaster in the mends too)
CLAY = 90
# Both feet are paler than the clay (her front foot, and the back one under her hem): inside FEET anything
# lighter than FOOT_L (grey) is her (John, 2026-10-02: "Don't leave out the other foot")
FEET = [[(198, 3365), (335, 3365), (335, 3645), (198, 3645)],
        [(355, 3470), (1000, 3470), (1000, 3665), (355, 3665)]]
FOOT_L = 90
# Her fingers point left, tips against the glaze, some painted so thinly that the clay test misses them:
# inside HAND the clay test is looser (HAND_RB)
HAND = [(445, 1880), (600, 1840), (650, 1880), (650, 2000), (610, 2110), (445, 2110)]
HAND_RB = 55
# The band binding her wrists is black glaze, a crescent open to the black ground at its ends: inside
# WRIST_BAND the dark is paint, not ground
WRIST_BAND = [(595, 1804), (628, 1778), (652, 1770), (680, 1771), (712, 1781), (735, 1792), (754, 1804), (768, 1820),
              (772, 1840), (754, 1842), (742, 1826), (728, 1816), (708, 1806), (686, 1803), (665, 1804), (646, 1810),
              (628, 1824), (610, 1838)]
# Ground: the dark with the painted lines (up to 2 * OPEN frame px wide) opened away, in areas over
# AUTO_GROUND frame px^2 that reach the crop's edge
OPEN, AUTO_GROUND = 5, 20000
EDGE_R = 6                      # frame px: her edge where the clay map falls to half the clay's level nearby
FIG_SIGMA = 3.0                 # frame px: her area smoothed along its length
EDGE = 4.5                      # frame px: the outline, drawn inside her edge, as wide as her painted lines (median)
# Lines: the painted lines are black glaze on the clay, 3-8 frame px wide, many with a white highlight
# along them. In red less blue the highlight reads as glaze (it is grey, not red), so the lines are found
# there by local contrast (the blurred map's Maximum then Minimum over CLOSE_W frame px, less the blurred
# map) with hysteresis (LINE_LOW, LINE_HIGH), and drawn at their own width (where the contrast is at
# least half the strongest within HALF_R frame px), never thinner than LINE_MIN along their centre.
LINE_LOW, LINE_HIGH, HALF_R, LINE_MIN = 25, 55, 3, 2.5
CLOSE_W = 11
LINE_LEN = 25                   # frame px: shorter pieces are grain
# and pieces shorter than SHORT_LEN whose contrast never reaches SHORT_C are the brushy wash of dilute glaze
# the painter shaded the drapery with (by her elbows and fingers), not lines: the painted lines reach 200
# and more, the wash 70-110
SHORT_LEN, SHORT_C = 80, 130
HOLE = 12                       # frame px^2: holes this small in a line are filled
MASK_SIGMA = 1.5                # frame px
SPUR, WIDTH_SIGMA = 10, 8.0     # frame px
# Breaks in a painted line (where the glaze flaked, a crack crossed it, or a highlight cut it) are joined
# (John, 2026-10-09: "we want these ink strokes to be clean, not cracked or jagged"), as clouds.py joins
# them: line ends facing each other across at most JOIN_MAX frame px (their last JOIN_RUN px pointing at
# each other within JOIN_ANGLE degrees), where the contrast across the gap has a median of JOIN_C or more,
# and the join crosses no other line; ends pointing straight at each other (within 10 degrees) across up to
# ALIGN_MAX where its median is ALIGN_C or more
JOIN_MAX, JOIN_RUN, JOIN_ANGLE, JOIN_C, ALIGN_MAX, ALIGN_C = 20, 8, 20, 15, 40, 8
ALIGN_COS = np.cos(np.radians(10))
# Pale white streaks lie on the clay (arcs across her back by her elbows: worn white or a deposit, not
# painted lines); grey, not red, so red less blue reads them as glaze. Areas lighter than WHITE_L (grey)
# and wider than 2 * WHITE_W frame px count as clay for the lines (the highlights along painted lines are
# narrower), inside WHITE_ZONE only (elsewhere broad white is the highlight on her veil's glossy lines)
WHITE_L, WHITE_W, WHITE_ZONE = 150, 3, [(480, 1450), (980, 1450), (980, 1760), (480, 1760)]
# In her veil and hair (HEAD) the lines crowd and carry broad white highlights, and the contrast finder
# joined neighbours into ladders: there the lines are the paint itself (red less blue under HEAD_K times the
# clay nearby, the Maximum over EDGE_R), redrawn along its centres at its own width
HEAD = [(860, 280), (1340, 280), (1340, 860), (1100, 860), (900, 760), (860, 600)]
HEAD_PAINT, HEAD_K, HEAD_SIGMA = False, 0.5, 0.5   # (the mask smoothed less there: its lines lie 4-6 px apart)
# At the front of her veil four thick glossy lines lie 4-6 px apart, each with a broad white highlight, and
# the finder joined them with rungs. Inside BAND_ZONE they are drawn on hand-placed points (frame px, read off
# the photo at 4x on a 20 px grid, 2026-10-09), snapped to the paint as his strokes are, each at its own
# width (frame px); the found lines there go.
BAND_ZONE = [(1132, 412), (1325, 412), (1325, 522), (1132, 522)]
BAND_LINES = [(5, [(1126, 431), (1140, 428), (1160, 425), (1200, 424), (1240, 426), (1270, 429), (1290, 433), (1300, 438)]),
              (4, [(1122, 453), (1135, 450), (1160, 451), (1200, 450), (1240, 450), (1280, 449), (1298, 450)]),
              (7, [(1120, 486), (1140, 480), (1160, 475), (1180, 471), (1200, 471), (1220, 472), (1240, 475),
                   (1260, 480), (1280, 484), (1300, 487), (1315, 491)]),
              (6, [(1120, 506), (1140, 504), (1160, 501), (1180, 500), (1200, 500), (1220, 501), (1240, 504),
                   (1260, 501), (1280, 500)]),
              (4, [(1280, 515), (1292, 523), (1300, 530), (1305, 535)])]
# solid paint (the band at her wrists, the hem's dark edge over her back foot): red less blue under
# PAINT, wider than 2 * PAINT_WIDE frame px
PAINT, PAINT_WIDE = 40, 4
# Two mended breaks, each a band given by points along its two edges (upper, then lower, left to right),
# frame px. The plaster bleeds, so a band is erased MEND_PAD px wider. Each is erased whole and nothing is
# drawn along it; the folds it broke are joined across (John, 2026-10-02: "connect the lines broken up by
# that slash on the vase"): a line ending within MEND_NEAR px of one edge is carried on along its own line
# to the line it meets on the other side, within MEND_GAP px of the end and MEND_LAT px of its line.
MENDS = {
    "skirt": ([(444, 2810), (540, 2852), (620, 2896), (700, 2932), (780, 2976), (860, 3024), (940, 3084),
               (1020, 3144), (1036, 3166)],
              [(444, 2848), (540, 2888), (620, 2926), (700, 2968), (780, 3016), (860, 3064), (940, 3120),
               (1036, 3206)]),
    # the plaster ridge from x 575 to 800; left of it only a thin crack across her bare arm; right of it the
    # plaster spreads into a broad patch across her far shoulder to her back edge (x 850-1265, placed by eye
    # on the photo, 2026-10-09; the first tool's band stopped at x 820)
    "arm": ([(430, 1430), (500, 1408), (560, 1383), (575, 1368), (600, 1362), (650, 1350), (700, 1340), (760, 1328),
             (820, 1314), (850, 1290), (950, 1278), (1050, 1262), (1110, 1238), (1160, 1215), (1265, 1192)],
            [(430, 1446), (500, 1424), (560, 1400), (575, 1393), (600, 1389), (650, 1382), (700, 1372), (760, 1360),
             (820, 1346), (850, 1345), (950, 1335), (1050, 1318), (1110, 1302), (1160, 1296), (1265, 1290)]),
}
MEND_PAD, MEND_NEAR, MEND_GAP, MEND_LAT, MEND_MIN = 4, 24, 110, 6, 40
MEND_BEND = 0.0
# Across the broad patch on her far shoulder only the lines that plainly run on are joined, by hand (frame
# px, line ends on either side, checked on the photo): the long diagonal fold, and the fold at the shoulder's
# back that the patch cut (its two ends 110 px apart). The other folds end at the patch.
MEND_JOINS = [[(1126, 1227), (1083, 1314)], [(1230, 1188), (1217, 1298)]]
# John traced her hands, her face and the lines across the arm mend himself (2026-10-02, on crops of this
# frame; registered by SIFT within half a px): tools/antigone_traces.json, frame px, unchanged from the first
# antigone.py. His arm and fingers are the standard (John, 2026-10-09); the lines found in the photo did not
# meet it (lumpy fingers, the lips and chin doubled), so inside his traced zones his strokes are her lines
# and her edge, snapped to the paint within TRACE_SNAP frame px and drawn even, TRACE_W frame px wide (the
# found lines' median width), and her area follows his outlines: a space they enclose is her if the photo
# shows clay there (red less blue above TRACE_RB) or it was already inside her.
TR = json.load(open(Path(__file__).resolve().parent / "antigone_traces.json"))
TRACE_SNAP, TRACE_W, TRACE_RB = 2, 5.0, 45
# His corrections to pass 1 (John, 2026-10-10, four sittings, marked in PhotoCraft over the photo with pass 1 in red, on
# this tool's grid: UP px per frame px over BOX): tools/antigone_marks_1.png, blue = add, green = remove.
# Green takes out the lines and her area under it; blue is drawn as he drew it (its edge smoothed over
# MARK_SIGMA px), solid where he filled. Her area follows: a space his blue encloses, or the green leaves
# inside her, is her; green at her edge, outside his new line, is ground (the face's profile), and a new
# edge is drawn there only where he drew none
MARKS = np.asarray(Image.open(Path(__file__).resolve().parent / "antigone_marks_1.png"))
MARK_SIGMA, SLIVER, HOLE_MAX = 1.0, 5, 3000
# Across the arm mend his lines replace the found ones inside ARM_ZONE (his crop, less ARM_INSET px, so his
# lines overlap the found ones at its edges)
ARM_ZONE, ARM_INSET = (562, 1303, 843, 1430), 6
# The face: three traces, each closer than the last, each replacing the earlier ones inside its zone. Inside
# FACE_CORE his lines are drawn FACE_PEN frame px wide (lines 1.0-1.4% of the head's 350 px, as the faces
# John approved), easing to TRACE_W over 12 px. Where his outline encloses paint (a curl, the glaze dot on
# her temple, the dark of the lower lip: a cell under PAINT_CELL frame px^2 darker than PAINT_L grey) the
# paint is drawn as its filled shape. His solid marks (the lower lid's V, the corner of the mouth) are drawn
# solid. Her eye is the paint itself (EYE: red less blue under EYE_K times the clay nearby): its strokes lie
# too close for outlines. The
# reddish streak across her cheek, which he marked in pink, is a stain and not drawn (not_lines).
FACE_TRACES = [("face_trace", "face_trace_zone"), ("lower_face_trace", "lower_face_zone"), ("lips_trace", "lips_zone")]
FACE_CORE, FACE_PEN = [(1100, 530), (1310, 530), (1310, 790), (1100, 790)], 3.5
EYE, EYE_K = [(1145, 546), (1268, 546), (1268, 612), (1145, 612)], 0.4
PAINT_CELL, PAINT_L = 800, 70
# lines are drawn at this weight (the first pass's own, pinned so his strokes do not re-weight the rest)
WEIGHT = 0.00146


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def to_up(pts):
    """Frame px -> px of the crop at UP."""
    return (np.asarray(pts, float) - BOX[:2] + 0.5) * UP - 0.5


def poly(shape, pts):
    return lw.polygon_mask(shape, to_up(pts))


def centre_lines(m, spur, min_len):
    """Centre lines of a stroke mask, side spurs under `spur` px pruned (the line ends kept), pieces under
    `min_len` px dropped (as clouds.py)."""
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


def smooth_mask(m, sigma, t):
    """m blurred over sigma px in PhotoCraft and cut at half."""
    Image.fromarray((m * 255).astype(np.uint8)).save(t / "m.png")
    pc(t / "m.png", t / "ms.png", ("filter.blur.gaussianBlur", {"radius": sigma}))
    return grey(t / "ms.png") >= 128


def _walk(cl, x, y, n):
    """Up to n skeleton px from the end (x, y), following the line and stopping where it branches. Returns
    (x, y) points, the end first."""
    H, W = cl.shape
    path, seen = [(x, y)], {(x, y)}
    for _ in range(n - 1):
        nxt = [(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
               if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H and cl[y + dy, x + dx] and (x + dx, y + dy) not in seen]
        if len(nxt) != 1:
            if len(nxt) == 2 and abs(nxt[0][0] - nxt[1][0]) + abs(nxt[0][1] - nxt[1][1]) == 1:
                nxt = sorted(nxt, key=lambda q: abs(q[0] - x) + abs(q[1] - y))[:1]
            else:
                break
        x, y = nxt[0]
        seen.add((x, y))
        path.append((x, y))
    return np.array(path, float)


def mend_band(shape, name, pad):
    upper, lower = MENDS[name]
    m = poly(shape, list(upper) + list(lower)[::-1])
    return ndi.binary_dilation(m, iterations=round(pad * UP)) if pad else m


def _side(pts, name):
    """Signed distance of points (crop px) from a mend's centre line (positive above), and its unit normal
    there (pointing up)."""
    U, D = to_up(MENDS[name][0]), to_up(MENDS[name][1])
    x = np.arange(max(U[0, 0], D[0, 0]), min(U[-1, 0], D[-1, 0]) + 1, 10.0)
    C = np.stack([x, (np.interp(x, U[:, 0], U[:, 1]) + np.interp(x, D[:, 0], D[:, 1])) / 2], -1)
    best = np.full(len(pts), np.inf)
    sd, nrm = np.zeros(len(pts)), np.zeros((len(pts), 2))
    for a, b in zip(C[:-1], C[1:]):
        ab = b - a
        t = np.clip(((pts - a) @ ab) / (ab @ ab), 0, 1)
        foot = a + t[:, None] * ab
        d = np.hypot(*(pts - foot).T)
        n = np.array([ab[1], -ab[0]]) / np.hypot(*ab)
        if n[1] > 0:
            n = -n
        c = d < best
        best[c], sd[c], nrm[c] = d[c], ((pts - foot) @ n)[c], n
    return sd, nrm


def join_across(cl, name):
    """Join the centre lines (cl) a mend broke (as the first antigone.py): from each line end near the band
    a ray is cast along its line across the band and joined to the first line px it meets on the far side.
    Returns the joins (1-px lines) and how many."""
    from skimage.draw import line
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere((ndi.convolve(cl.astype(int), k, mode="constant") == 1) & cl)[:, ::-1].astype(float)
    joins = np.zeros_like(cl)
    if not len(ends):
        return joins, 0
    band = mend_band(cl.shape, name, MEND_PAD)
    gap = ndi.distance_transform_edt(~band)
    near = gap[ends[:, 1].astype(int), ends[:, 0].astype(int)] <= MEND_NEAR * UP
    ends = ends[near]
    sd, nrm = _side(ends, name)
    lab, _ = ndi.label(cl, structure=np.ones((3, 3)))
    long_ = (np.bincount(lab.ravel()) >= MEND_MIN * UP)[lab] & cl
    targets = np.argwhere(long_ & ~band & (gap <= (MEND_NEAR + 10) * UP))[:, ::-1].astype(float)
    tside, _ = _side(targets, name)
    n = 0
    for (x, y), side, nb in zip(ends, sd, nrm):
        path = _walk(cl, int(x), int(y), 35 * UP)
        if len(path) < MEND_MIN * UP // 2:
            continue
        back = path[10 * UP:]
        c = back.mean(0)
        u = np.linalg.svd(back - c)[2][0]
        u = u if (np.array([x, y]) - c) @ u > 0 else -u
        if abs(u @ nb) < 0.5:   # runs along the band, not across it
            continue
        far = targets[np.sign(tside) == -np.sign(side)]
        rel = far - [x, y]
        al = rel @ u
        off = np.abs(rel[:, 0] * u[1] - rel[:, 1] * u[0])
        ok = (al > 0) & (al <= MEND_GAP * UP) & (off <= MEND_LAT * UP + MEND_BEND * al)
        if not ok.any():
            continue
        hit = far[ok][np.argmin(al[ok] + 2 * off[ok])]
        rr, cc = line(int(y), int(x), int(hit[1]), int(hit[0]))
        joins[rr, cc] = True
        n += 1
    return joins, n


def trace_walls(shape, trace):
    """His strokes, rasterized as they are (not snapped), about 3 frame px wide."""
    from skimage.draw import line
    walls = np.zeros(shape, bool)
    for pts in trace:
        P = to_up(pts)
        for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
            rr, cc = line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
            walls[rr[ok], cc[ok]] = True
    return ndi.binary_dilation(walls, iterations=UP)


def traced_area(rb, fig, walls, zone_pts):
    """Her area inside a traced zone, from his outlines (walls). Returns the new area and the zone."""
    shape = fig.shape
    zone = poly(shape, zone_pts)
    walls = ndi.binary_closing(walls, structure=morphology.disk(3 * UP))   # where two strokes nearly meet
    cells, n = ndi.label(zone & ~walls)
    idx = np.arange(1, n + 1)
    her = np.zeros(n + 1, bool)
    her[1:] = (((ndi.median(rb, cells, idx) > TRACE_RB) | (ndi.mean(fig.astype(float), cells, idx) > 0.6))
               & (ndi.sum(np.ones(shape), cells, idx) >= 20 * UP * UP))
    area = her[cells]
    area |= walls & ndi.binary_dilation(area, iterations=3 * UP)   # her outline itself
    area = ndi.binary_closing(area, structure=morphology.disk(UP))
    area &= ndi.binary_erosion(area | ~zone, iterations=2 * UP)     # under the drawn lines, so no clay shows past them
    return (fig & ~zone) | (area & zone), zone


def strokes(gp, paths, w):
    """His strokes, each snapped to the darkest line within TRACE_SNAP frame px of its points (gp, the
    blurred grey), smoothed, and drawn as an even line w px wide (w at UP; w = 0: the centre lines)."""
    from skimage.draw import line
    centre = np.zeros(gp.shape, bool)
    H, W = gp.shape
    for pts in paths:
        P = to_up(pts).round().astype(int)
        x0, y0 = max(P[:, 0].min() - 20, 0), max(P[:, 1].min() - 20, 0)
        x1, y1 = min(P[:, 0].max() + 21, W), min(P[:, 1].max() + 21, H)
        sub = gp[y0:y1, x0:x1]
        Q = [(x - x0, y - y0) for x, y in P]
        rough = np.zeros(sub.shape, bool)
        for (xa, ya), (xb, yb) in zip(Q[:-1], Q[1:]):
            rr, cc = line(ya, xa, yb, xb)
            rough[rr, cc] = True
        near = ndi.distance_transform_edt(~rough) <= TRACE_SNAP * UP
        xy = lw.livewire(np.where(near, 1.0 + sub / 8.0, 1e4), Q) if len(Q) > 1 else np.array(Q, float)
        if len(xy) > 9:   # a running mean evens out the px steps; the ends stay put
            k = 7 * UP
            sm = np.vstack([np.convolve(np.pad(xy[:, i], k // 2, mode="edge"), np.ones(k) / k, mode="valid")[:len(xy)]
                            for i in (0, 1)]).T
            sm[0], sm[-1] = xy[0], xy[-1]
            xy = sm
        xy = xy + (x0, y0)
        for (xa, ya), (xb, yb) in zip(xy[:-1], xy[1:]):
            rr, cc = line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            centre[rr[ok], cc[ok]] = True
    return centre if w == 0 else ndi.distance_transform_edt(~centre) <= w / 2


def join_breaks(c, contrast, inner):
    """Joins (1-px lines) for the breaks in centre lines c that JOIN_* describe; `inner` is where they may run."""
    from scipy.spatial import cKDTree
    from skimage.draw import line
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere(c & (ndi.convolve(c.astype(int), k, mode="constant") == 1))
    out = np.zeros_like(c)
    if len(ends) < 2:
        return out
    runs = [_walk(c, int(x), int(y), JOIN_RUN * UP)[:, ::-1] for y, x in ends]   # (y, x), the end first
    lab = ndi.label(c, structure=np.ones((3, 3)))[0]
    used = set()
    cos = np.cos(np.radians(JOIN_ANGLE))
    for i, j in sorted(cKDTree(ends).query_pairs(ALIGN_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]]))):
        if i in used or j in used or len(runs[i]) < JOIN_RUN * UP / 2 or len(runs[j]) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        if lab[tuple(ends[i])] == lab[tuple(ends[j])]:
            continue
        u = (b - a) / np.hypot(*(b - a))
        da, db = runs[i][0] - runs[i][-1], runs[j][0] - runs[j][-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        aligned = da @ u >= ALIGN_COS * np.hypot(*da) and db @ -u >= ALIGN_COS * np.hypot(*db)
        if not aligned and np.hypot(*(b - a)) > JOIN_MAX * UP:
            continue
        q = a[None] + np.linspace(0.1, 0.9, max(int(np.hypot(*(b - a))), 3))[:, None] * (b - a)[None]
        qi = tuple(q.round().astype(int).T)
        if not inner[qi].all() or np.median(ndi.map_coordinates(contrast, q.T, order=1)) < (ALIGN_C if aligned else JOIN_C):
            continue
        if set(lab[qi]) - {0, lab[tuple(ends[i])], lab[tuple(ends[j])]}:   # it would cross another line
            continue
        rr, cc = line(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        out[rr, cc] = True
        used |= {i, j}
    return out


def drawing(p04, t):
    """Her lines (ink) and area (fig) at UP, and the grey crop."""
    rgb, _ = flat_image(p04)
    Image.fromarray(rgb.clip(0, 255).round().astype(np.uint8)).save(t / "flat.png")
    x0, y0, x1, y1 = BOX
    w, h = x1 - x0, y1 - y0
    pc(t / "flat.png", t / "up.png", ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
       ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
    pc(t / "up.png", t / "g.png", ("image.mode.grayscale", None))
    pc(t / "g.png", t / "gp.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
    pc(t / "up.png", t / "rb.png", ("image.adjustments.channelMixer", {"monochrome": True, "gray": [100, 0, -100, 0]}),
       ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
    pc(t / "rb.png", t / "rbmax.png", ("filter.other.maximum", {"radius": EDGE_R * UP, "preserve": "roundness"}))
    g, gp, rb, rbmax = grey(t / "g.png"), grey(t / "gp.png"), grey(t / "rb.png"), grey(t / "rbmax.png")
    shape = g.shape
    pc(t / "g.png", t / "white.png", ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}),
       ("image.adjustments.threshold", {"level": WHITE_L}))
    white = ndi.binary_dilation(ndi.binary_opening(grey(t / "white.png") >= 128, structure=morphology.disk(WHITE_W * UP)),
                                iterations=2 * UP) & poly(shape, WHITE_ZONE)

    clay = rb > CLAY
    feet = np.zeros(shape, bool)
    for f in FEET:
        feet |= poly(shape, f)
    clay |= feet & (gp > FOOT_L)
    clay |= poly(shape, HAND) & (rb > HAND_RB)
    wrist = poly(shape, WRIST_BAND)
    dark = ~clay & ~wrist
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    ground = ((size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim))[lab]
    lab, _ = ndi.label(~ground)
    sx, sy = to_up([SEED])[0].round().astype(int)
    fig = ndi.binary_fill_holes(lab == lab[sy, sx]) & ~ground
    fig &= ~((ndi.distance_transform_edt(fig) <= EDGE_R * UP) & (rb < 0.5 * rbmax) & ~wrist & ~feet)
    fig = ndi.binary_fill_holes(fig)
    fig = smooth_mask(fig, FIG_SIGMA * UP, t)
    lab, _ = ndi.label(fig)
    fig = lab == lab[sy, sx]
    # his traced zones: her area there follows his outlines
    fig, hand_zone = traced_area(rb, fig, trace_walls(shape, TR["hand_trace"]), TR["hand_trace_zone"])
    layers = []
    for k, (trace, _) in enumerate(FACE_TRACES):
        later = np.zeros(shape, bool)
        for _, z in FACE_TRACES[k + 1:]:
            later |= poly(shape, TR[z])
        layers.append((TR[trace], ~ndi.binary_erosion(later, iterations=3 * UP)))
    marks = np.zeros(shape, bool)
    for m in TR["lower_face_solid"]:
        marks |= poly(shape, m)
    marks &= layers[1][1]
    face_walls = marks.copy()
    for trace, keep in layers:
        face_walls |= trace_walls(shape, trace) & keep
    fig, face_zone = traced_area(rb, fig, face_walls, TR["face_trace_zone"])
    traced = hand_zone | face_zone
    ax0, ay0, ax1, ay1 = ARM_ZONE
    arm = poly(shape, [(ax0 + ARM_INSET, ay0 + ARM_INSET), (ax1 - ARM_INSET, ay0 + ARM_INSET),
                       (ax1 - ARM_INSET, ay1 - ARM_INSET), (ax0 + ARM_INSET, ay1 - ARM_INSET)])

    # lines by local contrast in red less blue, everything off her turned clay-bright, so the ground's
    # dark makes no contrast along her edge
    Image.fromarray(np.where(fig & ~white, rb, 255).astype(np.uint8)).save(t / "rw.png")
    pc(t / "rw.png", t / "rl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
    r = (CLOSE_W * UP) // 2
    pc(t / "rl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
       ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
    contrast = (grey(t / "closed.png") - grey(t / "rl.png")).clip(0, None)
    Image.fromarray(contrast.clip(0, 255).astype(np.uint8)).save(t / "c.png")
    pc(t / "c.png", t / "cmax.png", ("filter.other.maximum", {"radius": HALF_R * UP, "preserve": "roundness"}))
    cmax = grey(t / "cmax.png")
    from skimage.filters import apply_hysteresis_threshold
    to_edge = ndi.distance_transform_edt(fig) / UP
    firm = apply_hysteresis_threshold(contrast, LINE_LOW, LINE_HIGH) & fig & (to_edge > EDGE)
    lab, n = ndi.label(firm, structure=np.ones((3, 3)))
    length = np.bincount(lab[morphology.skeletonize(firm)], minlength=n + 1) / UP
    top = ndi.maximum(contrast, lab, np.arange(n + 1))
    firm &= ~((length < SHORT_LEN) & (top < SHORT_C))[lab]
    own = firm & (contrast >= 0.5 * cmax)
    head = poly(shape, HEAD) & ~face_zone
    hp = (rb < HEAD_K * rbmax) & fig & (to_edge > EDGE) & ~white
    if HEAD_PAINT:
        own = np.where(head, hp, own)
        firm = np.where(head, hp, firm)
    m = morphology.remove_small_holes(firm | own, max_size=HOLE * UP * UP)
    m = np.where(head, smooth_mask(m, HEAD_SIGMA * UP, t), smooth_mask(m, MASK_SIGMA * UP, t))
    c = centre_lines(m, SPUR * UP, LINE_LEN * UP)
    c |= join_breaks(c, contrast, fig & (to_edge > EDGE))
    # the mends: erased whole, nothing drawn along them; the folds they broke joined across
    for name in MENDS:
        band = mend_band(shape, name, MEND_PAD)
        c &= ~band
        c = morphology.remove_small_objects(c, max_size=MEND_MIN * UP // 2, connectivity=2) | (c & ~ndi.binary_dilation(band, iterations=MEND_NEAR * UP))
        joins, n = join_across(c, name)
        c |= joins
        print(f"  {name} mend: {n} lines joined across")
    for a, b in MEND_JOINS:
        from skimage.draw import line
        (xa, ya), (xb, yb) = to_up([a, b]).round().astype(int)
        rr, cc = line(ya, xa, yb, xb)
        c[rr, cc] = True
    bandz = poly(shape, BAND_ZONE)
    c &= ~traced & ~arm & ~bandz
    wd = 2 * ndi.distance_transform_edt(own)
    num, den = (ndi.gaussian_filter(a, WIDTH_SIGMA * UP) for a in (np.where(c, wd, 0.0), c.astype(float)))
    half = np.where(c, np.maximum(num / np.maximum(den, 1e-6), LINE_MIN * UP) / 2, 0.0)
    d, (iy, ix) = ndi.distance_transform_edt(~c, return_indices=True)
    lines = (d <= half[iy, ix]) & fig
    paint = (rb < PAINT) & fig & ~white
    paint &= ndi.binary_dilation(ndi.binary_opening(paint, structure=morphology.disk(PAINT_WIDE * UP)), iterations=UP)
    for name in MENDS:
        paint &= ~mend_band(shape, name, MEND_PAD)
    paint &= ~traced & ~bandz
    for w, pts in BAND_LINES:
        lines |= strokes(gp, [pts], w * UP)
    # his lines: across the arm mend and in the hands at TRACE_W, in the face at FACE_PEN
    lines |= strokes(gp, TR["arm_lines"], TRACE_W * UP) | strokes(gp, TR["hand_trace"], TRACE_W * UP)
    ease = np.clip(ndi.gaussian_filter(poly(shape, FACE_CORE).astype(float), 6 * UP) * 2, 0, 1)
    wmap = (TRACE_W - (TRACE_W - FACE_PEN) * ease) * UP
    centres = np.zeros(shape, bool)
    for trace, keep in layers:
        centres |= strokes(gp, trace, 0) & keep
    thin = np.zeros(shape, bool)
    for trace, keep in layers:
        thin |= trace_walls(shape, trace) & keep
    thin = morphology.skeletonize(thin) | marks
    cells, n = ndi.label(face_zone & ~thin)
    idx = np.arange(1, n + 1)
    pcell = np.zeros(n + 1, bool)
    pcell[1:] = ((ndi.sum(np.ones(shape), cells, idx) <= PAINT_CELL * UP * UP) & (ndi.median(gp, cells, idx) < PAINT_L)
                 & (ndi.mean(fig.astype(float), cells, idx) > 0.5))   # (paint on her, not the ground beside her profile)
    filled = ndi.binary_dilation(pcell[cells], iterations=UP)
    centres &= ndi.distance_transform_edt(~filled) > 3 * UP
    eye = poly(shape, EYE)
    centres &= ~eye
    lines |= ((ndi.distance_transform_edt(~centres) <= wmap / 2) | marks | filled) & ~eye
    lines |= smooth_mask((rb < EYE_K * rbmax) & eye, 0.5 * UP, t) & eye
    for m in TR["not_lines"]:
        lines &= ~poly(shape, m)
    # the band binding her wrists: solid where the photo is dark inside WRIST_BAND (its highlights filled)
    band = ((gp < 70) | (rb < PAINT)) & wrist
    band = ndi.binary_fill_holes(ndi.binary_closing(morphology.remove_small_objects(band, max_size=200 * UP * UP),
                                                    structure=morphology.disk(3 * UP)))
    fig |= band
    edge = fig & ~ndi.binary_erosion(fig, iterations=round(EDGE * UP))
    edge &= ~ndi.binary_erosion(traced, iterations=6 * UP)   # there his outline is her edge
    ink = lines | paint | edge | band
    # his corrections to pass 1
    blue = smooth_mask(MARKS == 1, MARK_SIGMA * UP, t)
    green = MARKS == 2
    kept = fig & ~green
    holes = ndi.binary_fill_holes(kept | blue) & ~(kept | blue)
    lab, n = ndi.label(holes)
    was = ndi.mean((fig | green).astype(float), lab, np.arange(n + 1)) > 0.5   # (not the ground seen through her)
    was[0] = False
    fig2 = kept | blue | was[lab]
    # (slivers of her left outside his new line where he marked green near it, under 2 * SLIVER frame px
    # wide (his green stopped short of the old outline), are ground; small holes in her,
    # under HOLE_MAX px^2 (the dark between brow and lid, specks by her back), are her)
    thin = fig2 & ~blue & ~ndi.binary_opening(fig2 & ~blue, structure=morphology.disk(SLIVER * UP))
    lab, n = ndi.label(thin)
    out = np.unique(lab[ndi.binary_dilation(~fig2) & thin])
    nearb = np.unique(lab[ndi.binary_dilation(blue, iterations=2) & thin])
    nearg = np.unique(lab[ndi.binary_dilation(green, iterations=5 * UP) & thin])
    fig2 &= ~np.isin(lab, np.intersect1d(np.intersect1d(out[out > 0], nearb), nearg))
    lab, n = ndi.label(ndi.binary_fill_holes(fig2) & ~fig2)
    fig2 |= (np.bincount(lab.ravel(), minlength=n + 1) < HOLE_MAX)[lab] & (lab > 0)
    changed = ndi.binary_dilation(fig ^ fig2, iterations=3 * UP)
    edge2 = fig2 & ~ndi.binary_erosion(fig2, iterations=round(EDGE * UP)) & changed
    edge2 &= ~ndi.binary_dilation(blue, iterations=4 * UP)
    ink = (ink & ~green & fig2) | blue | edge2
    fig = fig2
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]
    return ink, fig, g, dict(contrast=contrast, rb=rb, c=c)


def main(p04, p05, p06, qa=None, dump=None):
    if "--refit" in sys.argv:
        fit_model({"04": p04, "05": p05, "06": p06})
        return
    with tempfile.TemporaryDirectory() as td:
        ink, fig, g, extra = drawing(p04, Path(td))
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ink=ink, c=extra["c"],
                            contrast=extra["contrast"].clip(0, 255).astype(np.uint8), rb=extra["rb"].astype(np.uint8))
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT,
        title="Antigone, veiled, her hands bound behind her back, her head bowed",
        desc="Line drawing after the Apulian red-figure amphora by the Darius Painter, c. 350-320 BCE, Berlin, "
             "Antikensammlung F 3240; traced from a photograph by ArchaiOptix (CC BY-SA 4.0), taken off the "
             "vase's curve, changed. This drawing is CC BY-SA 4.0.")
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--refit"]
    main(*args[:5])
