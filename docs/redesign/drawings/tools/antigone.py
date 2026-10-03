"""Antigone: Antigone with her hands bound behind her, brought before Creon,
from the Apulian red-figure amphora of Panathenaic shape by the Darius
Painter, c. 350-320 BCE, found at Ceglie del Campo, Berlin, Antikensammlung
F 3240 (RVAp 18/23). Body A, upper frieze: a guard with a spear, Antigone
with bound hands, a boy, Heracles talking to Creon enthroned, two youths.
Photos: ArchaiOptix, CC BY-SA 4.0, so the drawing is CC BY-SA 4.0; _04 is the
drawing's source, _05 and _06 serve the vase's shape:
https://commons.wikimedia.org/wiki/File:Darius_Painter_-_RVAp_18-23_-_Antigone_-_judgement_of_Paris_-_Eros_with_youths_and_women_-_Berlin_AS_F_3240_-_04.jpg

Photo -> drawing:
  - The vase is taken off its curve (vase_unroll.py, as for Euphorbos; John
    approved the method on that drawing, 2026-10-02). Its profile and the
    cameras of 04, 05 and 06 were fitted together (MODEL): to the upper
    border of the animal frieze under her feet (a painted circle) in all
    three, the vase's right-hand outline in 06, and points of the painting
    matched between 04 and the other two. All three photos were taken on an
    EOS 6D, 04 and 05 at 50 mm, 06 at 40 mm (EXIF), so the focal lengths are
    fixed; 04 and 05 are uncropped. The vase is then flattened without shear
    (vase_unroll.flatten) about her axis, and 04 laid onto it at 04's own
    scale at her waist. Unflattened, the photo shortens her skirt and feet,
    which lie where the vase curves in toward its foot.
  - She is the clay joined to SEED; the guard and the boy are separate
    figures on the glaze. Her front foot is paler than the rest of her, so
    the clay test misses it; it is added inside FOOT.
  - The guard's cord, in added white, survives in his hand and wound round
    her forearms; between them it has flaked off the glaze. On her it is
    drawn as two bands along the surviving white (CORD).
  - Two mended breaks cross her: one over her upper arm and back, one
    diagonally across her skirt, where the painted folds stop at its edges.
    Each is erased whole and nothing is drawn along it (John's rule for
    cracks); the folds that cross it are joined across (MENDS).
  - Painted lines are found by local contrast and redrawn as even lines
    along their centres at the house weight. Her hands are drawn by hand:
    each finger a closed outline (HAND_LINES), the lines that divide the
    fingers carried out to the notches between their tips.

    python3 docs/redesign/drawings/tools/antigone.py 04.jpg 05.jpg 06.jpg [qa.png]
    python3 docs/redesign/drawings/tools/antigone.py 04.jpg 05.jpg 06.jpg --refit
"""
import sys
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

OUT = Path(__file__).resolve().parent.parent / "antigone.svg"

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

CLAY_RB = 100        # clay is redder than this (red minus blue)
SEED = (900, 2300)   # on her skirt (frame px): she is the clay joined to it
# Both feet are paler than the clay (her front foot, and the back one under
# her hem): inside FEET, anything lighter than the glaze (FOOT_L) is her.
FEET = [[(198, 3365), (335, 3365), (335, 3645), (198, 3645)],
        [(355, 3470), (1000, 3470), (1000, 3665), (355, 3665)]]
FOOT_L = 90
# The back foot, under her hem, is cut off from her by the hem's dark line,
# and a thick painted stroke (the hem falling over it) crosses it to the
# sole: light areas in FEET within FOOT_GAP px of her join her, and the gaps
# close up (FOOT_CLOSE).
FOOT_GAP, FOOT_CLOSE = 20, 20
# Two mended breaks, each a band given by points along its two edges (upper,
# then lower, left to right). The plaster bleeds, so a band is erased
# MEND_PAD px wider. Folds that cross a band are joined across it: a line
# ending within MEND_NEAR px of one edge is carried on along its own line to
# the line it meets on the other side (see join_across).
MENDS = {
    "skirt": ([(444, 2810), (540, 2852), (620, 2896), (700, 2932), (780, 2976), (860, 3024), (940, 3084),
               (1020, 3144), (1036, 3166)],
              [(444, 2848), (540, 2888), (620, 2926), (700, 2968), (780, 3016), (860, 3064), (940, 3120),
               (1036, 3206)]),
    # the plaster ridge from x 575 to 800; left of it only a thin crack across her bare arm
    "arm": ([(430, 1430), (500, 1408), (560, 1383), (575, 1368), (600, 1362), (650, 1350), (700, 1340), (760, 1328),
             (820, 1314)],
            [(430, 1446), (500, 1424), (560, 1400), (575, 1393), (600, 1389), (650, 1382), (700, 1372), (760, 1360),
             (820, 1346)]),
}
MEND_PAD, MEND_NEAR, MEND_GAP, MEND_LAT, MEND_MIN = 4, 24, 110, 6, 40
# Across the arm mend John traced the lines himself (2026-10-02), on a crop of
# photo 04: each fold straight through the mend, the drapery's hook on the
# right. His trace was registered onto this frame by SIFT (183 matches, 0.3
# px) and its strokes turned into polylines (ARM_LINES, frame px). Inside
# ARM_ZONE (his crop, less ARM_INSET px, so his lines overlap the found ones
# at its edges) they replace the found lines, drawn even and snapped to the
# paint within ARM_SNAP px.
ARM_ZONE, ARM_INSET, ARM_SNAP = (562, 1303, 843, 1430), 6, 3
ARM_LINES = [
    [(658.3, 1412.6), (656.8, 1416.6), (656.8, 1420.6), (656.8, 1424.6), (656.3, 1425.1)],
    [(778.8, 1377.4), (782.8, 1379.4), (786.8, 1380.4), (788.8, 1379.9)],
    [(650.7, 1391.5), (646.7, 1392), (642.7, 1393.5), (639.2, 1397), (638.2, 1401), (637.7, 1405), (637.7, 1409.1), (637.7, 1413.1), (637.7, 1417.1), (637.7, 1419.6)],
    [(695.9, 1418.6), (695.9, 1414.6), (695.4, 1410.6), (695.9, 1406.5), (695.9, 1402.5), (696.4, 1398.5), (696.4, 1394.5), (696.4, 1390.5), (696.9, 1386.4), (696.9, 1382.4), (696.9, 1378.4), (697.4, 1374.4), (697.9, 1370.4), (698.4, 1366.4), (698.4, 1362.3), (698.9, 1358.3), (699.4, 1354.3), (700.4, 1350.3), (700.4, 1346.3), (700.4, 1342.3), (699.9, 1338.2)],
    [(836, 1353.8), (835, 1357.8), (833.5, 1361.8), (831.5, 1365.8), (829, 1369.9), (827.5, 1373.9), (826.5, 1377.9), (825, 1381.9), (822.5, 1385.9), (819.4, 1389.9), (817.4, 1394), (813.9, 1398), (811.9, 1402), (809.4, 1406), (807.4, 1410), (805.9, 1414), (803.9, 1418.1), (802.4, 1422.1), (800.9, 1426.1), (796.9, 1428.6), (795.9, 1428.6)],
    [(612.1, 1374.9), (612.6, 1378.9), (613.1, 1383), (613.6, 1387), (614.1, 1391), (614.1, 1395), (614.1, 1399), (614.1, 1403), (614.1, 1407.1), (614.1, 1411.1), (614.1, 1415.1), (614.1, 1419.1), (614.1, 1423.1), (613.6, 1426.6)],
    [(736.1, 1314.1), (735.6, 1310.1), (736.6, 1306.1), (739.1, 1305.1)],
    [(651.2, 1391), (650.2, 1387), (649.2, 1382.9), (646.7, 1378.9), (644.2, 1374.9), (642.2, 1370.9), (639.7, 1366.9), (637.7, 1362.9), (635.2, 1358.8), (632.7, 1354.8), (630.6, 1350.8), (629.1, 1346.8), (627.6, 1342.8), (626.6, 1338.8), (625.6, 1334.7), (624.6, 1330.7), (624.1, 1326.7), (624.1, 1322.7), (623.1, 1318.7), (622.6, 1314.7), (621.6, 1310.6), (619.6, 1308.6)],
    [(658.8, 1412.1), (658.8, 1408), (658.8, 1404), (658.3, 1400), (658.3, 1397.5)],
    [(662.3, 1327.7), (662.3, 1331.7), (662.3, 1335.7)],
    [(634.2, 1428.6), (636.7, 1425.1), (637.2, 1421.1), (637.7, 1420.1)],
    [(584.5, 1375.9), (580.9, 1379.9), (579.9, 1382.5)],
    [(576.4, 1400.5), (574.9, 1396.5), (574.4, 1392.5), (575.4, 1388.5), (577.9, 1384.5), (579.9, 1382.5)],
    [(593.5, 1429.2), (589.5, 1427.1), (586.5, 1423.1), (584.5, 1419.1), (581.4, 1415.1), (579.9, 1411.1)],
    [(585, 1375.4), (587.5, 1371.4), (589.5, 1367.4), (591.5, 1363.4), (593.5, 1359.4), (594, 1357.3)],
    [(707, 1305.1), (704.4, 1308.6), (704.4, 1312.6), (703.9, 1316.7), (702.9, 1320.7), (702.4, 1324.7), (701.9, 1328.7), (701.4, 1332.7), (700.9, 1336.7), (700.4, 1337.7)],
    [(768.7, 1328.7), (766.7, 1332.7), (766.7, 1336.7), (766.7, 1340.7), (766.7, 1344.8), (767.2, 1348.8), (767.2, 1352.8), (767.7, 1356.8), (767.7, 1360.8), (768.7, 1364.8), (770.7, 1368.9), (773.7, 1372.9), (777.8, 1375.9), (778.3, 1376.9)],
    [(598, 1344.8), (599, 1340.8), (600, 1336.8), (601.5, 1332.7), (603.5, 1328.7), (606, 1324.7), (609, 1320.7), (610, 1320.2)],
    [(757.7, 1305.6), (757.7, 1309.6), (758.7, 1313.6), (758.2, 1317.6), (758.7, 1320.2)],
    [(751.2, 1402), (750.2, 1406), (750.2, 1410), (750.2, 1414.1), (750.2, 1418.1), (750.7, 1422.1), (754.2, 1425.6), (758.2, 1426.6), (762.2, 1426.6), (766.2, 1426.6), (770.2, 1424.6), (772.3, 1423.1)],
    [(835.5, 1353.3), (831.5, 1354.3), (827.5, 1355.3), (823.5, 1358.3), (819.4, 1361.3), (815.4, 1364.3), (811.4, 1366.3), (807.4, 1368.3), (803.4, 1370.9), (799.4, 1373.4), (795.3, 1375.9), (791.3, 1377.4), (789.3, 1379.4)],
    [(618.6, 1308.6), (614.6, 1311.1), (612.1, 1315.2), (610.6, 1319.2), (610.6, 1319.7)],
    [(597.5, 1345.8), (596, 1349.8), (594.5, 1353.8), (594.5, 1356.3)],
    [(836, 1352.8), (837.5, 1348.8), (839, 1344.7), (840.5, 1340.7), (842, 1336.7), (842, 1336.2)],
    [(769.7, 1317.6), (769.2, 1321.7), (769.2, 1325.7), (769.2, 1328.2)],
    [(636.7, 1304.1), (640.2, 1307.1), (641.7, 1311.1), (644.2, 1315.2), (646.7, 1319.2), (649.2, 1323.2), (649.2, 1327.2), (649.2, 1331.2)],
    [(695.9, 1419.1), (696.4, 1423.1), (695.4, 1427.1), (691.9, 1427.1)],
    [(774.2, 1304.1), (770.2, 1308.1), (769.7, 1312.1), (770.2, 1316.1), (770.2, 1316.6)],
    [(658.8, 1412.6), (662.8, 1416.6), (664.3, 1419.1)],
    [(611.6, 1351.3), (611.6, 1355.3), (612.1, 1359.4), (612.1, 1363.4), (612.1, 1367.4), (612.1, 1371.4), (612.1, 1374.4)],
    [(729.1, 1425.6), (729.1, 1421.6), (729.1, 1417.6), (729.1, 1413.6), (729.1, 1409.5), (729.1, 1405.5), (729.1, 1401.5), (729.1, 1397.5), (729.1, 1393.5), (729.1, 1389.5), (729.1, 1385.4), (729.1, 1381.4), (729.6, 1377.4), (730.1, 1373.4), (730.1, 1369.4), (730.6, 1365.4), (731.1, 1361.3), (731.6, 1357.3), (731.6, 1353.3), (732.1, 1349.3), (732.6, 1345.3), (733.1, 1341.3), (733.1, 1337.2), (733.6, 1333.2), (734.1, 1329.2), (734.1, 1327.2)],
    [(658.3, 1397), (662.3, 1394), (663.3, 1390), (662.3, 1386), (662.3, 1381.9), (662.3, 1377.9), (662.3, 1373.9), (662.3, 1369.9), (662.3, 1365.9), (662.3, 1361.9), (662.3, 1357.8), (662.3, 1353.8), (662.3, 1349.8), (662.3, 1345.8), (662.3, 1341.8), (662.3, 1337.8), (662.3, 1336.7)],
    [(840.5, 1304.1), (836.5, 1306.6), (832.5, 1310.1), (828.5, 1314.1), (825.5, 1318.1), (821.4, 1322.2), (817.4, 1325.7), (813.4, 1328.7), (809.4, 1332.2), (805.4, 1334.2), (801.4, 1335.7), (797.3, 1335.7), (793.3, 1335.7), (789.3, 1334.7), (785.3, 1332.2), (782.8, 1328.2), (780.3, 1324.2), (777.8, 1320.7), (773.7, 1318.6), (770.7, 1317.1)],
    [(668.3, 1304.1), (664.8, 1307.6), (664.3, 1311.6), (663.8, 1315.7), (663.3, 1318.7)],
    [(651.2, 1392), (655.3, 1395), (657.8, 1397)],
    [(611.6, 1350.8), (610.6, 1346.8), (610.6, 1342.8), (610.1, 1340.8)],
]

# Painted lines are redrawn as even lines along their centres at the house
# weight; paint wider than 2 * THICK px and darker than DARK (the band at
# her wrists, the hem's dark edge over her back foot) stays solid.
THICK, DARK = 7, 60


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(pts, float))


def clean_band_edges(cl, band):
    """Drop skeleton pieces shorter than MEND_MIN px that lie within MEND_NEAR
    px of a band: the plaster's rough edges, not painted lines."""
    near = ndi.distance_transform_edt(~band) <= MEND_NEAR
    lab, n = ndi.label(cl, structure=np.ones((3, 3)))
    size = np.bincount(lab.ravel())
    inside = np.bincount(lab.ravel(), weights=near.ravel())
    drop = (size < MEND_MIN) & (inside > 0.5 * size)
    drop[0] = False
    return cl & ~drop[lab]


def mend_bands(shape, pad=MEND_PAD):
    """Each mend's band as a mask, `pad` px wider than its edges."""
    out = {}
    for name, (upper, lower) in MENDS.items():
        m = poly(shape, list(upper) + list(lower)[::-1])
        out[name] = ndi.binary_dilation(m, iterations=pad) if pad else m
    return out


def silhouette(rgb):
    """Her area: the clay joined to SEED, with her feet, her painted lines,
    the black band at her wrists and the mends' plaster filled in."""
    RB, L = rgb[..., 0] - rgb[..., 2], lum(rgb)
    clay = ndi.binary_opening(RB > CLAY_RB, structure=morphology.disk(2))
    feet = np.zeros(L.shape, bool)
    for f in FEET:
        feet |= poly(L.shape, f)
    clay |= feet & ndi.binary_opening(L > FOOT_L, structure=morphology.disk(2))
    lab, _ = ndi.label(ndi.binary_closing(clay, structure=morphology.disk(3)))
    fig = lab == lab[SEED[1], SEED[0]]
    # the back foot: light parts of the feet's zones close to her join her...
    near = ndi.binary_dilation(fig, iterations=FOOT_GAP)
    keep = np.unique(lab[near & feet & clay])
    fig |= np.isin(lab, keep[keep > 0]) & feet
    # ...and the hem line between them closes up
    fig |= ndi.binary_closing(fig, structure=morphology.disk(FOOT_CLOSE)) & feet
    # the mends' plaster is her where it lies within her outline
    bands = np.zeros(L.shape, bool)
    for m in mend_bands(L.shape).values():
        bands |= m
    fig |= ndi.binary_closing(fig, structure=morphology.disk(12)) & bands
    fig = ndi.binary_fill_holes(fig)
    return ndi.gaussian_filter(fig.astype(float), 1.5) > 0.5


def _centre(upper, lower, step=10.0):
    """A mend band's centre line and half-width, both edges resampled on one
    x grid (the bands run left to right)."""
    U, D = np.asarray(upper, float), np.asarray(lower, float)
    x = np.arange(max(U[0, 0], D[0, 0]), min(U[-1, 0], D[-1, 0]) + 1, step)
    yu, yd = np.interp(x, U[:, 0], U[:, 1]), np.interp(x, D[:, 0], D[:, 1])
    return np.stack([x, (yu + yd) / 2], -1), np.mean(yd - yu) / 2


def _side(pts, upper, lower):
    """Signed distance of points from a mend band's centre line (positive on
    the upper side), and the band's unit normal there (pointing up)."""
    C, _ = _centre(upper, lower)
    best_d = np.full(len(pts), np.inf)
    sd = np.zeros(len(pts))
    nrm = np.zeros((len(pts), 2))
    for a, b in zip(C[:-1], C[1:]):
        ab = b - a
        t = np.clip(((pts - a) @ ab) / (ab @ ab), 0, 1)
        foot = a + t[:, None] * ab
        d = np.hypot(*(pts - foot).T)
        n = np.array([ab[1], -ab[0]]) / np.hypot(*ab)  # left of the direction of travel: up for a band run left to right
        if n[1] > 0:
            n = -n
        closer = d < best_d
        best_d[closer] = d[closer]
        sd[closer] = ((pts - foot) @ n)[closer]
        nrm[closer] = n
    return sd, nrm


def _walk(cl, x, y, n):
    """Up to n skeleton pixels from the end (x, y), following the line and
    stopping where it branches. Returns (x, y) points, the end first."""
    H, W = cl.shape
    path, seen = [(x, y)], {(x, y)}
    for _ in range(n - 1):
        nxt = [(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
               if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H and cl[y + dy, x + dx] and (x + dx, y + dy) not in seen]
        if len(nxt) != 1:
            # two steps on from a diagonal and a straight neighbour can be the same line: keep the straight one
            if len(nxt) == 2 and abs(nxt[0][0] - nxt[1][0]) + abs(nxt[0][1] - nxt[1][1]) == 1:
                nxt = sorted(nxt, key=lambda q: abs(q[0] - x) + abs(q[1] - y))[:1]
            else:
                break
        x, y = nxt[0]
        seen.add((x, y))
        path.append((x, y))
    return np.array(path, float)


def join_across(cl, name):
    """Join the centre lines (cl, a skeleton) that a mend broke. From each line
    end near the band, a ray is cast along its line (its direction taken 10-35
    px back along it; the last few px hook along the plaster's edge) across
    the band; it is joined to the first line pixel it meets on the far side
    within MEND_LAT px of the ray and MEND_GAP px of the end. Rays that run
    along the band (from lines that follow its edge) never reach the far side
    and make no join. Returns the joins (1-px lines) and how many were made."""
    from skimage.draw import line
    upper, lower = MENDS[name]
    k = np.ones((3, 3), int)
    k[1, 1] = 0
    ends = np.argwhere((ndi.convolve(cl.astype(int), k, mode="constant") == 1) & cl)[:, ::-1].astype(float)
    if not len(ends):
        return np.zeros_like(cl), 0
    sd, nrm = _side(ends, upper, lower)
    band = mend_bands(cl.shape)[name]
    gap = ndi.distance_transform_edt(~band)
    near = gap[ends[:, 1].astype(int), ends[:, 0].astype(int)] <= MEND_NEAR
    ends, sd, nrm = ends[near], sd[near], nrm[near]
    # targets: pixels of lines at least MEND_MIN px long, on the far side near the band
    lab, _ = ndi.label(cl, structure=np.ones((3, 3)))
    size = np.bincount(lab.ravel())
    long_ = (size >= MEND_MIN)[lab] & cl
    targets = np.argwhere(long_ & ~band & (gap <= MEND_NEAR + 10))[:, ::-1].astype(float)
    tside, _ = _side(targets, upper, lower)
    joins = np.zeros_like(cl)
    n = 0
    for (x, y), side, nb in zip(ends, sd, nrm):
        path = _walk(cl, int(x), int(y), 35)
        if len(path) < MEND_MIN // 2:  # a fragment, not a fold
            continue
        back = path[10:]
        c = back.mean(0)
        u = np.linalg.svd(back - c)[2][0]
        u = u if (np.array([x, y]) - c) @ u > 0 else -u
        if abs(u @ nb) < 0.5:  # runs along the band, not across it
            continue
        far = targets[np.sign(tside) == -np.sign(side)]  # line pixels on the other side
        rel = far - [x, y]
        along = rel @ u
        off = np.abs(rel[:, 0] * u[1] - rel[:, 1] * u[0])
        ok = (along > 0) & (along <= MEND_GAP) & (off <= MEND_LAT)
        if not ok.any():
            continue
        hit = far[ok][np.argmin(along[ok] + 2 * off[ok])]
        rr, cc = line(int(y), int(x), int(hit[1]), int(hit[0]))
        joins[rr, cc] = True
        n += 1
    return joins, n


def centre_lines(m, spur=6, min_len=14):
    """Centre lines of a stroke mask, with side spurs under `spur` px pruned
    (the line ends are kept) and pieces under `min_len` px dropped. (As in
    oedipus_syracuse.py and euphorbos.py.)"""
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


def drawing(rgb, w):
    """Her lines (ink) and area (sil) from the flat frame, and its luminance;
    w is the house weight in px."""
    sil = silhouette(rgb)
    L = lum(rgb)
    inner = ndi.binary_erosion(sil, structure=morphology.disk(4))
    found = lw.ink_lines(L, size=21, low=16, high=38, sigma=1.0) & inner
    # wide dark paint stays solid: the line finder sees only the edges of a band wider than its window
    solid = ndi.binary_opening((ndi.gaussian_filter(L, 1.5) < DARK) & inner, structure=morphology.disk(THICK))
    thin = found & ~ndi.binary_dilation(solid, iterations=2)
    thin = ndi.gaussian_filter(ndi.binary_closing(thin, structure=morphology.disk(1)).astype(np.float32), 1.0) > 0.5
    cl = centre_lines(thin)
    # the mends: erased whole, nothing drawn along them; the folds they broke joined across
    for name, band in mend_bands(L.shape).items():
        cl &= ~band
        solid &= ~band
        cl = clean_band_edges(morphology.remove_small_objects(cl, max_size=6, connectivity=2), band)
        joins, n = join_across(cl, name)
        cl |= joins
        print(f"  {name} mend: {n} lines joined across")
    # John's lines across the arm mend
    x0, y0, x1, y1 = ARM_ZONE
    zone = np.zeros(L.shape, bool)
    zone[y0 + ARM_INSET:y1 - ARM_INSET, x0 + ARM_INSET:x1 - ARM_INSET] = True
    cl &= ~zone
    solid &= ~zone
    lines = (ndi.distance_transform_edt(~cl) <= w / 2) | solid | strokes(L, ARM_LINES, w, snap=ARM_SNAP)
    lines = morphology.remove_small_objects(lines, max_size=60)  # specks of wear
    # the outline, w wide, straddling her edge (a quarter outside)
    edge = (sil & (ndi.distance_transform_edt(sil) <= 0.75 * w)) | (~sil & (ndi.distance_transform_edt(~sil) <= 0.25 * w))
    return edge | lines, sil, L


def main(p04: str, p05: str, p06: str) -> None:
    if "--refit" in sys.argv:
        fit_model({"04": p04, "05": p05, "06": p06})
        return
    rgb, _ = flat_image(p04)
    if "--flat" in sys.argv:  # diagnostic: the flat frame as one photo
        Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(sys.argv[sys.argv.index("--flat") + 1])
        return
    sil = silhouette(rgb)
    if "--masks" in sys.argv:  # diagnostic: her area over the frame
        g = np.clip(lum(rgb), 0, 255) * 0.55
        m = np.stack([g, g, g], -1)
        m[sil] = m[sil] * 0.55 + np.array([255, 60, 60]) * 0.45
        Image.fromarray(m.astype(np.uint8)).save(sys.argv[sys.argv.index("--masks") + 1])
        return
    w = lw.HOUSE_WEIGHT * max(rgb.shape[:2])  # the house weight, in frame px
    ink, sil, L = drawing(rgb, w)
    info = lw.trace_svg(
        ink, OUT, body=sil,
        title="Antigone, veiled, her hands bound behind her back",
        desc="Line drawing after the Apulian red-figure amphora by the Darius Painter, c. 350-320 BCE, Berlin, "
             "Antikensammlung F 3240; traced from a photograph by ArchaiOptix (CC BY-SA 4.0), changed: taken off "
             "the vase's curve, mended breaks erased, hand and cord lines redrawn. This drawing is CC BY-SA 4.0.")
    print(OUT, info)
    qa = [a for a in sys.argv[4:] if not a.startswith("--")]
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info["box"], Path(qa[0]))
        lw.qa_dark(OUT, info["box"], Path(qa[0]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
