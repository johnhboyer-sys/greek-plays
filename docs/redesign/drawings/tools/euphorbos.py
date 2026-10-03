"""Sophocles: the shepherd Euphorbos carrying the infant Oedipus, from the
Attic red-figure neck-amphora by the Achilles Painter, c. 450-445 BCE,
found at Vulci, Paris, Bibliotheque nationale de France, Cabinet des
Medailles 372 (ARV2 987.4; BAPD 213824). Their names are painted beside
them: ΕΥΦΟΡΒΟΣ, ΟΙΔΙΠΟΔΑΣ. Photos: ArchaiOptix, 2023, CC BY-SA 4.0, so the
drawing is CC BY-SA 4.0. Four views of the same side, files _01 to _04 of
https://commons.wikimedia.org/wiki/File:Achilles_Painter_-_ARV_987_4_-_Euphorbos_with_the_infant_Oidipous_-_man_-_Paris_BnF_CabMed_372_-_02.jpg

Four photos -> one drawing:
  - The painting is taken off the vase (vase_unroll.py). A photo foreshortens
    it: his head and shoulders lie on the shoulder, which curves up and in to
    the neck, and his legs on the lower body, which curves in to the foot.
    The vase's profile and the four cameras were fitted together (MODEL,
    below) to the silhouettes in 01, 02 and 04, the meander's lower edge
    (painted on the wheel, so a circle), the ring at the base of the neck,
    and points of the painting matched between 02 and the other three. All
    four photos were taken with an EF 40mm on an EOS 6D, so the focal length
    is fixed from the EXIF; 01, 02 and 04 are crops, whose centres are fitted.
  - The vase is then flattened as rigidly as it allows (vase_unroll.flatten):
    every small patch keeps its shape. A plain unrolling (around by arc
    length, up the profile) shears whatever lies off its centre line where
    the profile slopes; on the first version that tilted his face back and
    pushed his jaw forward, and swelled the hat on his back out of his neck
    (John, 2026-10-02: "smooshed like a Neanderthal", "an insane tumor").
  - Above his belt the drawing comes from 03, a close view that looks almost
    straight at the shoulder (2-12 degrees off the surface at his head), so
    its head is the truest; below, from 02, which faces him and is sharp to
    his feet. Each is laid onto the flat through its own camera.
  - His spear, trailed at the hip, is about 1.2x his height and wraps a
    third of the way round the vase, so 02 shows only the stretch near him.
    It is drawn at its full length (John, 2026-10-02), straight: one line
    fitted to the painted shaft on both sides of him, out to its own butt
    spike (from 01) and blade (from 04), placed where the model puts their
    tips.
  - The back of his neck is drawn in, where the vase has no line (NECK_BACK).
  - The points below (cuts, zones and hand-drawn lines) were measured on a
    first composite of 02 and 03 in 02's frame, with a margin of X02 px on its
    left; when the tool runs they are carried back to their photo (03 above
    SEAM, by the registration that made that composite; 02 below) and laid
    onto the flat with it.

    python3 docs/redesign/drawings/tools/euphorbos.py 01.jpg 02.jpg 03.jpg 04.jpg [qa.png]
    python3 docs/redesign/drawings/tools/euphorbos.py 01.jpg 02.jpg 03.jpg 04.jpg --refit
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline, RBFInterpolator
from scipy.spatial import cKDTree
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
import vase_unroll as vu  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sophocles-euphorbos.svg"
BOX02 = (1290, 1590, 2260, 3330)  # photo 02 crop around him (x0, y0, x1, y1)
BOX03 = (700, 1150, 2850, 4900)   # photo 03 crop around him
F = 2.4                           # the 02 frame is BOX02 scaled by F
X02 = 1050                        # the points below were measured with this many px of margin on its left
SEAM, FEATHER = 1180, 40          # 02-frame y where 03 hands over to 02, and the blend's half-width
PAD = 120                         # rows above the frame that the 03 warp also covers


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def band(x):
    """Lines and edges, for matching photos of different sharpness."""
    x = x.astype(np.float32)
    return ndi.gaussian_filter(x, 2) - ndi.gaussian_filter(x, 10)


def register(Lf, L03, rows):
    """Frame -> photo 03 coordinates (two arrays, rows x frame width).
    A projective warp from SIFT matches first; then four rounds of patch
    matching (normalised cross-correlation of `band` images over 80-96 px
    patches on the figure), each fitted with a smoothed thin-plate spline and
    composed with the warp so far."""
    from skimage.feature import SIFT, match_descriptors, match_template
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    src, dst = [], []
    small02 = Lf[::2, ::2] / 255  # frame at 1.2x photo 02
    for k03 in (0.5, 0.6):
        g03 = ndi.zoom(L03, k03, order=1) / 255
        s3, s2 = (SIFT(upsampling=1, n_octaves=5, c_dog=0.005) for _ in range(2))
        s3.detect_and_extract(g03)
        s2.detect_and_extract(small02)
        m = match_descriptors(s3.descriptors, s2.descriptors, max_ratio=0.85, cross_check=True)
        src.append(s3.keypoints[m[:, 0]][:, ::-1] / k03)
        dst.append(s2.keypoints[m[:, 1]][:, ::-1] * 2)
    src, dst = np.vstack(src), np.vstack(dst)
    P, inl = ransac((dst, src), ProjectiveTransform, min_samples=4, residual_threshold=12,
                    max_trials=10000, rng=0)
    H, W = rows, Lf.shape[1]
    # the maps run PAD rows above the frame, so that no correction pulls from off their top
    gy, gx = np.mgrid[-PAD:H, 0:W].astype(np.float32)
    m = P(np.c_[gx.ravel(), gy.ravel()])
    MX, MY = m[:, 0].reshape(gy.shape).astype(np.float32), m[:, 1].reshape(gy.shape).astype(np.float32)
    U = Lf[:H]
    bU = band(U)
    fig = ndi.binary_dilation(ndi.gaussian_filter(U, 3) > 100, iterations=90)  # the figure and its edges
    for T, R, step, smooth in ((48, 72, 36, 400.0), (40, 20, 30, 150.0), (40, 10, 30, 80.0), (36, 6, 30, 50.0)):
        bW = band(ndi.gaussian_filter(ndi.map_coordinates(L03, [MY[PAD:], MX[PAD:]], order=1, cval=0), 1.0))
        pts, dsp = [], []
        for y in range(T + R, H - T - R, step):
            for x in range(T + R, W - T - R, step):
                tpl = bW[y - T:y + T, x - T:x + T]
                if not fig[y, x] or tpl.std() < 1.5:
                    continue
                c = match_template(bU[y - T - R:y + T + R, x - T - R:x + T + R], tpl)
                iy, ix = np.unravel_index(np.argmax(c), c.shape)
                pk = c[iy, ix]
                if pk < 0.5 or iy in (0, c.shape[0] - 1) or ix in (0, c.shape[1] - 1):
                    continue
                dy = (c[iy - 1, ix] - c[iy + 1, ix]) / (2 * (c[iy - 1, ix] - 2 * pk + c[iy + 1, ix]) + 1e-9)
                dx = (c[iy, ix - 1] - c[iy, ix + 1]) / (2 * (c[iy, ix - 1] - 2 * pk + c[iy, ix + 1]) + 1e-9)
                pts.append((x, y))
                dsp.append((ix - R + dx, iy - R + dy))
        pts, dsp = np.array(pts, float), np.array(dsp)
        tree, ok = cKDTree(pts), np.ones(len(pts), bool)
        for i, p in enumerate(pts):  # a patch must agree with its neighbours
            med = np.median(dsp[tree.query_ball_point(p, 110)], axis=0)
            ok[i] = np.hypot(*(dsp[i] - med)) <= max(2.0, 0.15 * np.hypot(*med))
        pts, dsp = pts[ok], dsp[ok]
        f = RBFInterpolator(pts + dsp, dsp, kernel="thin_plate_spline", smoothing=smooth)
        cy, cx = np.mgrid[-PAD:H:16, 0:W:16].astype(np.float32)
        D = f(np.c_[cx.ravel(), cy.ravel()]).reshape(cy.shape + (2,))
        Dx = ndi.zoom(D[..., 0], (gy.shape[0] / D.shape[0], W / D.shape[1]), order=1)[:gy.shape[0], :W]
        Dy = ndi.zoom(D[..., 1], (gy.shape[0] / D.shape[0], W / D.shape[1]), order=1)[:gy.shape[0], :W]
        MX, MY = (ndi.map_coordinates(MX, [gy - Dy + PAD, gx - Dx], order=1, mode="nearest"),
                  ndi.map_coordinates(MY, [gy - Dy + PAD, gx - Dx], order=1, mode="nearest"))
        mag = np.hypot(*dsp.T)
        print(f"  registration, search {R} px: {len(pts)} patches, moved median {np.median(mag):.2f} px, "
              f"90% {np.percentile(mag, 90):.2f} px")
    return MX[PAD:], MY[PAD:]


def map_02_to_03(p02, p03):
    """Photo 03 coordinates of the 02 frame's pixels above SEAM (and 440 rows
    more): the registration that first joined the two views. The points above
    SEAM were measured on 03's pixels shown in the 02 frame; this carries them
    back to photo 03."""
    a02 = np.asarray(Image.open(p02).convert("RGB").crop(BOX02), dtype=np.float32)
    a03 = np.asarray(Image.open(p03).convert("RGB").crop(BOX03), dtype=np.float32)
    H, W = round(a02.shape[0] * F), round(a02.shape[1] * F)
    frame = np.stack([ndi.zoom(a02[..., c], F, order=3)[:H, :W] for c in range(3)], -1).clip(0, 255)
    MX, MY = register(lum(frame), lum(a03), SEAM + FEATHER + 400)
    return MX + BOX03[0], MY + BOX03[1]


# ---------------------------------------------------------------- the vase

# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit
# again; it prints these numbers). World units are arbitrary (camera 02's D
# fixes them); y = 0 at the meander's lower edge.
CAMERAS = {
    "02": dict(D=5500.0, H=2455.73, b=0.26492, p=0.00081, g=0.01297, f=6080.0, cx=1728.68, cy=2124.43),
    "01": dict(D=5418.98, H=2806.75, b=0.21429, p=0.1684, g=0.04342, f=6080.0, cx=2369.74, cy=1483.08),
    "04": dict(D=5440.76, H=3003.57, b=0.29651, p=0.09598, g=0.02437, f=6080.0, cx=2072.22, cy=1570.24),
    "03": dict(D=2212.98, H=2386.69, b=0.70237, p=-0.0556, g=-0.03919, f=6080.0, cx=1824.0, cy=2736.0),
}
PROFILE_Y = [-350, -150, 50, 250, 450, 650, 850, 1050, 1250, 1450, 1650, 1850]
PROFILE_R = [547.3, 671.5, 744.1, 806.7, 841.3, 874.2, 897.2, 896.2, 855.6, 746.7, 637.3, 527.9]
TURNS = {"01": 28.531, "04": -28.34, "03": -5.882}  # degrees each photo is turned from 02
# All four photos: an EF 40mm on an EOS 6D (EXIF), so the focal length is
# 6080 px (40 mm over the pixel pitch, 1520 px/cm). 01, 02 and 04 are crops,
# so their principal points are fitted; 03 is the whole frame. Fitted free,
# the focal length traded against the distance: it came out twice as long,
# with half the perspective, and the head stayed squashed.
F6D = 40.0 / (10.0 / 1520.0)
# The data for fit_model: silhouette rows clear of handles and foot (side,
# v from, v to), the box searched for the meander's lower edge, and the neck
# ring's rough ellipse (centre u, half-width, sides' v, sag).
FIT_ROWS = {"02": [(0, 1700, 3600), (1, 1700, 3600)], "01": [(0, 2100, 3700), (1, 1620, 3700)],
            "04": [(0, 1480, 3420), (1, 1900, 3420)]}
FIT_BAND = {"02": (900, 2700, 3000, 3450), "01": (700, 2400, 3150, 3600), "04": (500, 2400, 3050, 3550)}
FIT_RING = {"02": (1708.0, 425.0, 1475.0, 96.0), "01": (1325.0, 425.0, 1570.0, 98.0),
            "04": (1487.0, 402.0, 1385.0, 110.0)}
# boxes where points are matched between 02 and the others (02 box, other box, half size?)
FIT_MATCH = {"01": [((1250, 1550, 2300, 3350), (1350, 1600, 2400, 3550), True),
                    ((1450, 1580, 2150, 2150), (1500, 1620, 2250, 2250), False)],
             "04": [((1250, 1550, 2300, 3350), (650, 1550, 1700, 3350), True),
                    ((1450, 1580, 2150, 2150), (750, 1580, 1500, 2150), False)],
             "03": [((1300, 1600, 2100, 3320), (700, 1150, 2850, 4900), False)]}
# The flat: the vase flattened without shear (vase_unroll.flatten) over a
# grid of FLAT_THETA x FLAT_Y (start, stop, step); kept: the figure's sector
# FIG_THETA all the way up, and the band SPEAR_Y all round for the spear. The
# meridian CENTRE, through his body, runs straight up. G px per world unit.
FLAT_THETA, FLAT_Y = (-1.15, 1.4501, 0.01), (-80.0, 1820.1, 10.0)
FIG_THETA, SPEAR_Y, CENTRE, G = (-0.75, 0.95), (650.0, 1250.0), 0.07, 2.75


def vase():
    """The model: the cameras and the profile."""
    cams = {n: dict(c) for n, c in CAMERAS.items()}
    R = CubicSpline(PROFILE_Y, PROFILE_R)
    return cams, R


def fit_model(photos: dict) -> None:
    """Refit MODEL from the photos and print it (see vase_unroll.fit)."""
    from skimage.feature import SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    rgb = {n: np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32) for n in photos}
    views, rings = {}, {}
    for n in ("02", "01", "04"):
        sil = vu.silhouette(rgb[n], 1300, 3900)
        views[n] = dict(size=rgb[n].shape[1::-1], band=vu.band_edge(rgb[n], FIT_BAND[n]), f=F6D, crop=True,
                        sil=[(side, r[1 + side], r[0]) for r in sil for side, v0, v1 in FIT_ROWS[n]
                             if v0 <= r[0] <= v1 and np.isfinite(r[1 + side])])
        rings[n] = vu.ring_edge(rgb[n].mean(2), *FIT_RING[n])
    views["03"] = dict(size=rgb["03"].shape[1::-1], sil=[], band=[], f=F6D)

    def feats(a, box, half):
        g = Image.fromarray(lum(a).clip(0, 255).astype(np.uint8)).crop(box)
        k = 2 if half else 1
        g = np.asarray(g.resize((g.width // k, g.height // k), Image.LANCZOS), dtype=np.float32) / 255
        s = SIFT(upsampling=1, n_octaves=5, c_dog=0.006 if half else 0.004)
        s.detect_and_extract(g)
        return s.keypoints[:, ::-1] * k + np.array(box[:2]), s.descriptors

    matches = {}
    for n, boxes in FIT_MATCH.items():
        found = []
        for b02, bn, half in boxes:
            k2, d2 = feats(rgb["02"], b02, half)
            kn, dn = feats(rgb[n], bn, half)
            m = match_descriptors(d2, dn, max_ratio=0.8, cross_check=True)
            _, inl = ransac((k2[m[:, 0]], kn[m[:, 1]]), ProjectiveTransform, min_samples=4,
                            residual_threshold=40 if half else 25, max_trials=5000, rng=0)
            found.append(np.hstack([k2[m[inl, 0]], kn[m[inl, 1]]]))
        matches[n] = np.vstack(found)
    cams, R, ring, turns, report, x = vu.fit(views, np.array(PROFILE_Y, float), ring=rings, matches=matches, d0=5500.0)
    print("\n".join(report))
    print("CAMERAS = {")
    for n, c in cams.items():
        print(f'    "{n}": dict(' + ", ".join(f"{k}={c[k]:.6g}" for k in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
    print("}")
    print("PROFILE_R =", [round(float(R(y)), 1) for y in PROFILE_Y])
    print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


CLAY_RB = 100        # clay is redder than this (red minus blue); glaze and its blue highlights are not
SEED = (2050, 1500)  # on his chest: the figure is the clay joined to it
# The meander band he stands on is cut away along the thin dark line between
# his soles and the band's top stripe (a least-cost path within CORRIDOR px
# of these points), and straight across the glaze between his feet.
FLOOR_CUT = [(1050, 4035), (1250, 4060), (1450, 4085), (1650, 4112), (1850, 4142), (1930, 4160), lw.STRAIGHT,
             (2050, 4166), (2250, 4141), (2450, 4121), (2650, 4100), (2830, 4078), (2900, 4070), lw.STRAIGHT,
             (3377, 4000)]
CORRIDOR = 14
# The spear. Past his outline the painted shaft is kept for CUT px; beyond, it
# is erased and drawn straight: one line fitted to the painted shaft on both
# sides of him (SPEAR_SHAFT_X: 02-frame x ranges outside him, at the shaft's
# height), out to the ends, whose tips the model places from their photos.
# Each end is unrolled from its own photo (butt spike 01, blade 04) through
# the model, moved onto the line (by the shift and turn that carry its own
# axis, START to TIP, onto it), then found like the figure.
CUT = 30
SPEAR_OUTLINE = [(1435, 2330), (2783, 2158)]  # 02 frame: where the shaft leaves him (kilt, cloak)
SPEAR_SHAFT_X = [[(1170, 2336), (1350, 2332)], [(2810, 2153), (2990, 2116)]]
SPEAR_ENDS = {"butt": dict(photo="01", start=(1133, 2752), tip=(1095, 2756)),    # start: the collar's bands
              "blade": dict(photo="04", start=(2100, 2327), tip=(2190, 2301))}
# Glaze inside his outline that stays open: between the kilt, the cloak and the spear.
OPEN = [(2460, 2170)]
# His hair is glaze-dark like the ground, inside its own reserved outline:
# within HAIR, the dark is hair, drawn solid, and its locks keep their ends.
HAIR = [(1990, 250), (2015, 140), (2090, 70), (2200, 30), (2350, 30), (2500, 75), (2610, 150), (2680, 240),
        (2690, 290), (2630, 285), (2520, 285), (2430, 290), (2380, 345), (2340, 400), (2250, 445),
        (2150, 445), (2070, 420), (2010, 380), (1980, 320)]
OUTLINE_RB = 60  # the hair's reserved outline is thin and faint in places: found at this lower redness
# A brown smear across his right shin is a stain, not a painted line: its
# lines are erased, and the top edge of his leg wrapping, which it hides, is
# drawn on straight across it (WRAP_EDGE, joining the edge's two ends).
STAIN = [(2175, 3790), (2225, 3700), (2280, 3640), (2340, 3622), (2342, 3682), (2285, 3700), (2245, 3762),
         (2218, 3802)]
WRAP_EDGE = ((2200, 3745), (2282, 3737))
# Painted lines are redrawn as even lines along their centres, at the house
# weight (lw.HOUSE_WEIGHT of the drawing's longer side, its width with the
# spear: about 11 px here), so trace_svg hardly changes them. Above SEAM
# (photo 03) they are found as on the Syracuse Oedipus; below it (photo 02,
# enlarged F times) with a wider, smoother window, and pairs of lines closer
# than a hole of HOLE px are read as one line (no ladders). Strokes wider
# than 2 * THICK px and darker than DARK (the cord on his back) stay solid.
THICK, DARK, HOLE = 8, 75, 500
# The faces' lines are finer, FACE_PEN px: at the house weight they run
# together, since the full spear makes the drawing wide and his head small
# within it. 5 px gives his head (420 px) the same ratio to its lines as
# the approved Syracuse Oedipus head (540 px to 6.4 px).
FACE_PEN = 5
# His fist: the found lines tangle its fingers with the pleats behind them,
# so inside HAND its lines are drawn by hand, on the painted lines (snapped
# within SNAP px). From the Achilles Painter's own lines: the back of the
# hand from the wrist; three fingers curled under the shaft, each with its
# knuckle; the thumb across the shaft; the palm's crease.
SNAP = 5
HAND = [(1946, 2095), (1996, 2080), (2076, 2124), (2150, 2168), (2192, 2200), (2188, 2280), (2140, 2310),
        (2076, 2338), (1993, 2355), (1950, 2350), (1918, 2322), (1930, 2312), (1966, 2310), (1966, 2268),
        (1930, 2262), (1905, 2250), (1885, 2232), (1915, 2165), (1940, 2120)]
HAND_LINES = [
    [(1996, 2088), (2034, 2110), (2076, 2132), (2118, 2157), (2146, 2177), (2173, 2196), (2184, 2207)],  # back
    [(2184, 2207), (2180, 2227), (2178, 2254), (2176, 2271)],  # fist, right
    [(1946, 2102), (1979, 2118), (2007, 2129), (2034, 2136), (2051, 2139)],  # wrist, under
    [(1982, 2135), (1987, 2152), (1991, 2171)],  # wrist crease
    [(1923, 2166), (1934, 2185), (1943, 2210)],  # thumb's base
    [(1971, 2221), (1990, 2218), (2007, 2204), (2021, 2193)],  # palm crease
    [(1887, 2238), (1907, 2256), (1932, 2266), (1959, 2271)],  # hand, left
    [(2004, 2246), (2007, 2271), (2009, 2299), (2012, 2327)],  # first finger
    [(2009, 2293), (2021, 2304), (2025, 2302)],  # its knuckle
    [(2047, 2227), (2059, 2260), (2071, 2288), (2076, 2310)],  # second finger
    [(2071, 2282), (2082, 2293)],  # its knuckle
    [(2090, 2199), (2104, 2221), (2118, 2249), (2129, 2279), (2132, 2291)],  # thumb, left
    [(2096, 2213), (2112, 2221), (2134, 2229), (2137, 2235), (2134, 2254)],  # thumb, top
    [(1932, 2316), (1946, 2327), (1962, 2335), (1993, 2338), (2034, 2332), (2076, 2321),
     (2112, 2310), (2134, 2296), (2159, 2282), (2176, 2274)],  # fist, under
    [(1957, 2271), (1959, 2291), (1962, 2307)],  # fist, left
]
# His sandals: photo 02 is soft there, so found lines break up into grain.
# On the left foot the straps are thin lines, drawn by hand inside FEET[0]
# (FEET_LINES). On the right foot they are broad dark bands, and at the heel
# a net of them: inside FEET[1] they are drawn solid where the photo is
# darker than STRAP_K times the clay around it, and its toe lines by hand.
FEET = [[(1150, 3870), (1420, 3870), (1560, 4020), (1860, 4090), (1860, 4140), (1150, 4140)],
        [(2095, 3960), (2360, 3960), (2470, 4010), (2860, 4040), (2860, 4140), (2095, 4150)]]
STRAP_K = 0.6
# The two faces, Euphorbos's and the child's: their lines are the finest
# on the vase, and found lines break up there, so inside FACES every line is
# drawn by hand from the 03 view (FACE_LINES, snapped like the hand's), with
# the pupils and the child's curls as dots (FACE_DOTS: x, y, radius). The
# child's face is turned to the front, tilted under Euphorbos's chin: two
# eyes one above the other, the nose's side line running down from the
# lower eye's corner, an open mouth, and one long line from under that eye
# round the chin and up the far cheek. His hair is dilute glaze, a brown
# wash with no painted edge; it is drawn as its hairline (HAIRLINE, along
# the wash's edge, not snapped) with its curls as dots.
FACES = [[(2405, 266), (2540, 266), (2562, 300), (2562, 340), (2548, 396), (2500, 397), (2450, 401),
          (2425, 396), (2405, 340)],
         [(2333, 452), (2380, 455), (2407, 446), (2414, 425), (2440, 408), (2500, 420), (2565, 448),
          (2610, 480), (2565, 520), (2556, 572), (2554, 603), (2532, 618), (2513, 623), (2494, 619),
          (2481, 616), (2466, 611), (2448, 607), (2430, 601), (2412, 594), (2396, 587), (2368, 573),
          (2340, 561)]]
FACE_LINES = [
    # Euphorbos
    [(2415, 280), (2437, 284), (2459, 290), (2482, 295), (2497, 299), (2509, 303), (2521, 307.5),
     (2529, 311)],  # brow
    [(2428, 293.5), (2448, 298.5), (2470.5, 304), (2493, 310), (2508, 312.5)],  # upper lid
    [(2434.5, 303), (2448, 312), (2465, 320), (2482, 326.5), (2493, 332.5)],  # lower lid
    [(2473, 307.5), (2471.5, 314), (2475, 321), (2481, 324.5)],  # iris
    [(2481, 324.5), (2493, 317.5), (2502, 313)],  # lower lid, from the iris to the front corner
    [(2504, 314), (2515, 317.5), (2528, 320.5)],  # past the front corner
    [(2453, 375.5), (2454, 372), (2456, 369), (2465, 367.5), (2475, 368), (2485, 371), (2492, 373.5)],  # nose
    [(2457, 380), (2463, 382), (2470, 381.5), (2480, 383), (2490, 386), (2504, 390)],  # mouth
    # the child
    [(2335, 458), (2355, 460), (2380, 461), (2402, 457.5), (2412, 450), (2415, 436), (2420, 428),
     (2434, 422.5), (2442, 415)],  # where his head meets Euphorbos's chin
    [(2340, 556.5), (2358, 563.5), (2369, 568.5), (2381, 572.5), (2391, 576), (2397, 582), (2413, 589),
     (2431, 596.5), (2449, 602), (2467, 606.5), (2482, 611), (2494.5, 614.5), (2513, 618), (2531, 612.5),
     (2543.5, 600), (2547, 585.5), (2547, 573), (2546.5, 569)],  # under the lower eye, the chin, the far cheek
    [(2362.5, 564), (2368, 556.5), (2377, 551), (2385, 548.5), (2393, 548.5), (2399, 551)],  # lower eye
    [(2378.5, 561.5), (2381, 556), (2387.5, 552.5), (2396.5, 551.5)],
    [(2399, 552.5), (2402.5, 558.5), (2400, 566), (2395, 572.5)],
    [(2400, 552.5), (2410, 559), (2420, 567.5), (2429, 576.5), (2438, 585.5), (2445.5, 590), (2453, 591),
     (2460, 587.5), (2465.5, 582)],  # the nose's side
    [(2454.5, 570), (2458, 563.5), (2467, 561), (2474.5, 563.5), (2476, 569)],  # the nose's tip
    [(2494, 577), (2486, 584), (2483, 592), (2478, 596), (2473, 599.5), (2471, 603)],  # mouth
    [(2501.5, 581), (2502, 589), (2499, 596), (2493, 601), (2484, 604), (2475, 604)],
    [(2496, 573), (2503, 575), (2507, 578)],
    [(2411, 516), (2408, 524), (2406, 530), (2407, 535)],  # upper eye
    [(2414, 533.5), (2420, 521.5), (2426.5, 516.5), (2432.5, 513.5)],
    [(2444, 516.5), (2441.5, 525), (2436.5, 531.5), (2426.5, 539)],
    # ear: its outer rim and the short line inside; the rim's inner edge, 5 px
    # in, would merge with it at the house line weight
    [(2478, 469), (2485, 463), (2496, 461), (2506, 463), (2514, 469), (2518, 477), (2518, 484)],
    [(2498, 479.5), (2503, 479), (2508, 480), (2511, 482.5)],
]
# The back of his neck: the vase paints no line there, so his neck runs on into
# the hat hanging behind him, and in a drawing the two read as one swelling.
# Drawn in (John, 2026-10-02): from the lowest locks at the back of his head,
# bowing in at the nape, down to the beaded seam on top of his shoulder; the
# neck is then about half as deep as the head, throat to nape. Photo 03 px.
NECK_BACK = [(1708, 1752), (1712, 1785), (1706, 1812), (1694, 1838), (1676, 1860), (1652, 1878), (1630, 1890)]
FACE_DOTS = [(2477.5, 314, 4), (2424, 528, 4), (2385, 565, 2.5), (2468, 587, 2),  # pupils, nostril
             (2443, 459, 2.5), (2494, 496, 3), (2536, 480, 3), (2512, 491.5, 2)]  # curls
HAIRLINE = [(2345, 528), (2355, 512), (2365, 497), (2382, 488), (2405, 486), (2425, 489), (2445, 490),
            (2465, 491), (2482, 496), (2496, 502), (2512, 499), (2535, 492), (2556, 488)]
FEET_LINES = [
    [(1193, 3897), (1217, 3902), (1283, 3912), (1350, 3920), (1390, 3925), (1405, 3935), (1407, 3948),
     (1393, 3958), (1350, 3966), (1300, 3968), (1260, 3963)],  # left foot, loops
    [(1193, 3905), (1217, 3928), (1250, 3958), (1283, 3987), (1317, 4011), (1350, 4031), (1383, 4050),
     (1417, 4069), (1450, 4080), (1483, 4089), (1500, 4093)],  # left foot, the strap from heel to toes
    [(1300, 3987), (1350, 3988), (1400, 3990), (1440, 3993), (1457, 4000), (1452, 4012), (1433, 4017),
     (1383, 4018), (1337, 4013)],
    [(1500, 4037), (1510, 4043), (1512, 4052), (1502, 4060), (1483, 4065), (1450, 4067), (1417, 4063)],
    [(1163, 3958), (1190, 3959), (1217, 3957)],  # left heel
    [(1273, 4010), (1285, 4033), (1297, 4053)],
    [(1317, 4033), (1328, 4047), (1340, 4060)],
    [(1615, 4058), (1628, 4078), (1640, 4100)],  # left toes
    [(1663, 4073), (1678, 4092), (1690, 4105)],
    [(1745, 4090), (1760, 4104), (1773, 4113)],
    [(1792, 4098), (1803, 4110)],
    [(2510, 4060), (2530, 4075), (2548, 4093)],  # right toes
    [(2580, 4045), (2600, 4065), (2618, 4088)],
    [(2660, 4043), (2675, 4062), (2688, 4078)],
    [(2720, 4048), (2735, 4062), (2748, 4073)],
]


def poly(shape, pts):
    return lw.polygon_mask(shape, np.array(pts, float))


def centre_lines(m, spur=6, min_len=14):
    """Centre lines of a stroke mask, with side spurs under `spur` px pruned
    (the line ends are kept) and pieces under `min_len` px dropped. (As in
    oedipus_syracuse.py.)"""
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


def strokes(L, paths, w, snap=SNAP):
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


def segment(shape, ends, w):
    """A straight line w px wide between two points."""
    from skimage.draw import line
    (xa, ya), (xb, yb) = [(int(round(x)), int(round(y))) for x, y in ends]
    m = np.zeros(shape, bool)
    rr, cc = line(ya, xa, yb, xb)
    m[rr, cc] = True
    return ndi.distance_transform_edt(~m) <= w / 2


# ---------------------------------------------------------------- the flat


class Flat:
    """The flat, in px: x right, y down, G px per world unit. The drawing's frame
    holds the figure and the spear; the figure's frame is its part from x = dx,
    as wide as the figure's sector."""

    def __init__(self, p02, p03):
        from scipy.interpolate import LinearNDInterpolator, RegularGridInterpolator
        self.cams, self.R = vase()
        th, yy = np.arange(*FLAT_THETA), np.arange(*FLAT_Y)
        XY = vu.flatten(self.R, th, yy, centre=CENTRE,
                        keep=lambda T, Y: ((T >= FIG_THETA[0]) & (T <= FIG_THETA[1])) | ((Y >= SPEAR_Y[0]) & (Y <= SPEAR_Y[1])))
        TH, Y = np.meshgrid(th, yy)
        ok = np.isfinite(XY[..., 0])
        self._fwd = [RegularGridInterpolator((yy, th), XY[..., k], bounds_error=False) for k in (0, 1)]
        self._inv = LinearNDInterpolator(XY[ok], np.stack([TH[ok], Y[ok]], -1))
        self.m03 = map_02_to_03(p02, p03)
        # the frame: the figure's sector, widened to the spear's tips
        fig = ok & (TH >= FIG_THETA[0]) & (TH <= FIG_THETA[1])
        tips = np.array([self._unit(e["photo"], [e["tip"]])[0] for e in SPEAR_ENDS.values()])
        x0, x1 = min(XY[fig][:, 0].min(), tips[:, 0].min() - 25), max(XY[fig][:, 0].max(), tips[:, 0].max() + 25)
        self.ax0, self.ay1 = x0, XY[fig][:, 1].max()
        H = int((self.ay1 - XY[fig][:, 1].min()) * G)
        self.all_shape = (H, int((x1 - x0) * G))
        self.dx = int(round((XY[fig][:, 0].min() - x0) * G))
        self.fig_shape = (H, int((XY[fig][:, 0].max() - XY[fig][:, 0].min()) * G))
        self._crop(p02)

    def _crop(self, p02, step=8, margin=150):
        """Shrink both frames to the figure (the clay joined to SEED, found on a
        coarse unrolling of photo 02, less the thin spear; and his dark hair) and
        the spear's tips, with a margin."""
        a = np.asarray(Image.open(p02).convert("RGB"), dtype=np.float32)
        H, W = self.fig_shape
        ys, xs = np.arange(0, H, step), np.arange(0, W, step)
        X, Y = np.meshgrid(xs + self.dx, ys)
        uv = self.all_to_photo("02", X, Y)
        rb = ndi.map_coordinates(a[..., 0] - a[..., 2], [np.nan_to_num(uv[:, 1], nan=-1), np.nan_to_num(uv[:, 0], nan=-1)],
                                 order=1, cval=0).reshape(X.shape)
        fl = self.to_fig([q for q in FLOOR_CUT if q != lw.STRAIGHT]) / step  # the band he stands on: cut away
        o = np.argsort(fl[:, 0])
        rb[ys[:, None] / step > np.interp(xs[None, :] / step, fl[o, 0], fl[o, 1]) - 2] = 0
        lab, _ = ndi.label(ndi.binary_opening(ndi.binary_closing(rb > CLAY_RB, iterations=2), structure=morphology.disk(4)))
        sx, sy = self.to_fig([SEED])[0] / step
        k = lab[int(round(sy)), int(round(sx))]
        yy, xx = np.nonzero(lab == k)
        hair = self.to_fig(HAIR)
        fy0, fy1 = min(yy.min() * step, hair[:, 1].min()) - margin, (yy.max() + 1) * step + margin
        fx0, fx1 = xx.min() * step - margin + self.dx, (xx.max() + 1) * step + margin + self.dx
        tips = np.array([self.photo_to_all(e["photo"], [e["tip"]])[0] for e in SPEAR_ENDS.values()])
        ax0, ax1 = min(fx0, tips[:, 0].min() - 25 * G), max(fx1, tips[:, 0].max() + 25 * G)
        self.ax0 += ax0 / G
        self.ay1 -= fy0 / G
        self.all_shape = (int(fy1 - fy0), int(ax1 - ax0))
        self.dx = int(round(fx0 - ax0))
        self.fig_shape = (int(fy1 - fy0), int(fx1 - fx0))

    def _unit(self, name, uv):
        """Photo points -> flat world units."""
        ty = vu.photo_to_surface(self.cams[name], self.R, np.asarray(uv, float).reshape(-1, 2), (FLAT_Y[0], FLAT_Y[1] - 1))
        th = ty[:, 0] - (np.radians(TURNS[name]) if name != "02" else 0.0)
        q = np.c_[ty[:, 1], th]
        return np.stack([self._fwd[0](q), self._fwd[1](q)], -1)

    def photo_to_all(self, name, uv):
        """Points of photo `name` -> the drawing's frame (px)."""
        f = self._unit(name, uv)
        return np.stack([(f[:, 0] - self.ax0) * G, (self.ay1 - f[:, 1]) * G], -1)

    def all_to_photo(self, name, X, Y):
        """Drawing-frame px -> photo `name` (u, v); NaN outside the flattened patch."""
        ty = self._inv(np.stack([self.ax0 + np.ravel(X) / G, self.ay1 - np.ravel(Y) / G], -1))
        th = ty[:, 0] + (np.radians(TURNS[name]) if name != "02" else 0.0)
        return vu.project(self.cams[name], vu.surface(self.R, ty[:, 1], th))

    def unroll(self, name, path, step=4):
        """Photo `name` laid onto the figure's frame (H x W x 3) and where it was
        seen (inside the photo)."""
        a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
        H, W = self.fig_shape
        ys, xs = np.arange(0, H + step, step), np.arange(0, W + step, step)
        X, Y = np.meshgrid(xs + self.dx, ys)
        uv = self.all_to_photo(name, X, Y).reshape(len(ys), len(xs), 2)
        full = [ndi.zoom(np.nan_to_num(uv[..., k], nan=-1e4), step, order=1)[:H, :W] for k in (0, 1)]
        u, v = full
        seen = (u > 2) & (v > 2) & (u < a.shape[1] - 3) & (v < a.shape[0] - 3)
        out = np.stack([ndi.map_coordinates(a[..., k], [v, u], order=1, cval=0) for k in range(3)], -1)
        return out, seen

    def image(self, p02, p03):
        """The figure's frame as one photo: 03 above the belt, where it is sharp
        and looks straight at the shoulder; 02 below; blended across 2 x FEATHER
        px at the flat row of the 02 frame's SEAM, 03's colours matched to 02's.
        Also the mask of what came from 03."""
        a2, seen2 = self.unroll("02", p02)
        a3, seen3 = self.unroll("03", p03)
        ys = self.to_fig([(X02 + 1164, SEAM)])[0][1]  # the seam at his belt
        Y = np.arange(a2.shape[0], dtype=np.float32)[:, None]
        w = np.clip((ys + FEATHER - Y) / (2 * FEATHER), 0, 1) * seen3
        near = (np.abs(Y - ys) < 200) & seen2 & seen3
        L2, L3 = lum(a2), lum(a3)
        clay = near & ndi.binary_erosion((L2 > 110) & (L3 > 110), iterations=6)
        glaze = near & ndi.binary_erosion((L2 < 50) & (L3 < 50), iterations=6)
        for c in range(3):
            t0, t1 = np.median(a3[..., c][glaze]), np.median(a3[..., c][clay])
            f0, f1 = np.median(a2[..., c][glaze]), np.median(a2[..., c][clay])
            a3[..., c] = f0 + (a3[..., c] - t0) * (f1 - f0) / (t1 - t0)
        glaze_rgb = np.median(a2[seen2 & (L2 < 50)], axis=0)
        a2[~seen2] = glaze_rgb
        out = w[..., None] * a3 + (1 - w[..., None]) * a2
        return out.clip(0, 255), w > 0.5

    def to_fig(self, pts):
        """02-frame points (measured with the X02 margin) -> figure-frame px.
        Points above SEAM are carried back to photo 03 and laid down through its
        camera, the others through 02's."""
        P = np.asarray(pts, float).reshape(-1, 2)
        out = np.empty_like(P)
        up = P[:, 1] < SEAM
        if (~up).any():
            uv = np.stack([BOX02[0] + (P[~up, 0] - X02) / F, BOX02[1] + P[~up, 1] / F], -1)
            out[~up] = self.photo_to_all("02", uv)
        if up.any():
            q = [P[up, 1], P[up, 0] - X02]
            uv = np.stack([ndi.map_coordinates(m, q, order=1) for m in self.m03], -1)
            out[up] = self.photo_to_all("03", uv)
        out[:, 0] -= self.dx
        return out


def converted(fl: Flat):
    """The hand-placed points, carried from the 02 frame onto the figure's frame."""
    import types

    def pts(p):
        return [tuple(q) for q in fl.to_fig(p)]

    def path(p):  # keeps lw.STRAIGHT markers
        out, run = [], []
        for q in p:
            if q == lw.STRAIGHT:
                out += pts(run) + [lw.STRAIGHT] if run else [lw.STRAIGHT]
                run = []
            else:
                run.append(q)
        return out + (pts(run) if run else [])

    def dots(d):
        out = []
        for x, y, r in d:
            a, b = fl.to_fig([(x, y), (x + r, y)])
            out.append((a[0], a[1], float(np.hypot(*(b - a)))))
        return out

    floor = path(FLOOR_CUT)
    H, W = fl.fig_shape
    floor = [(0.0, floor[0][1])] + floor + [(W - 1.0, floor[-1][1])]  # out to the frame's sides...
    floor = [q if q == lw.STRAIGHT else (min(max(q[0], 0.0), W - 1.0), min(max(q[1], 0.0), H - 1.0)) for q in floor]  # ...and in it
    return types.SimpleNamespace(
        seed=pts([SEED])[0], floor=floor, open=pts(OPEN), hair=pts(HAIR), stain=pts(STAIN),
        wrap_edge=tuple(pts(WRAP_EDGE)), hand=pts(HAND), hand_lines=[pts(q) for q in HAND_LINES],
        feet=[pts(q) for q in FEET], feet_lines=[pts(q) for q in FEET_LINES], faces=[pts(q) for q in FACES],
        face_lines=[pts(q) for q in FACE_LINES], face_dots=dots(FACE_DOTS), hairline=pts(HAIRLINE),
        outline=[pts([q])[0] for q in SPEAR_OUTLINE], shaft_x=[pts(q) for q in SPEAR_SHAFT_X],
        neck_back=[tuple(q) for q in fl.photo_to_all("03", NECK_BACK) - [fl.dx, 0]])


def shaft_line(RB, xs_pairs):
    """The shaft's centre line y = a + b x and its width, fitted to the
    shaft-wide run of clay in the columns of each x range, near its row."""
    pts, widths = [], []
    for (xa, ya), (xb, yb) in xs_pairs:
        for x in np.arange(min(xa, xb), max(xa, xb), 3.0):
            yg = ya + (yb - ya) * (x - xa) / (xb - xa)
            y0 = int(yg) - 60
            col = np.nonzero(RB[max(y0, 0):y0 + 121, int(x)] > CLAY_RB)[0]
            runs = [r for r in np.split(col, np.nonzero(np.diff(col) > 1)[0] + 1) if 12 <= len(r) <= 70] if len(col) else []
            if len(runs) == 1:
                pts.append((x, y0 + (runs[0][0] + runs[0][-1]) / 2))
                widths.append(len(runs[0]))
    pts = np.array(pts)
    b, a = np.polyfit(pts[:, 0], pts[:, 1], 1)
    side = pts[:, 0] < np.mean([q[0][0] for q in xs_pairs[1:]] or [np.inf])
    w = (float(np.median(np.array(widths)[side])), float(np.median(np.array(widths)[~side])))
    r = pts[:, 1] - (a + b * pts[:, 0])
    print(f"  shaft: one line at {np.degrees(np.arctan(b)):.2f} deg through both sides, widths {w[0]:.0f} and {w[1]:.0f} px, "
          f"painted shaft within {np.abs(r).max():.1f} px of it (mean {r[side].mean():+.1f} left, {r[~side].mean():+.1f} right)")
    return a, b, w


def spear(fl: Flat, rgb, P, photos):
    """Erase the painted shaft beyond CUT on both sides (in the figure's
    frame, to glaze) and return the spear outside him for the drawing's
    frame: its body (shaft and ends) and its lines (shaft edges and the
    ends' outlines and painted lines)."""
    RB, L = rgb[..., 0] - rgb[..., 2], lum(rgb)
    a, b, widths = shaft_line(RB, P.shaft_x)
    e = np.array([1.0, b]) / np.hypot(1, b)
    n = np.array([-e[1], e[0]])
    H, W = rgb.shape[:2]
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    glaze = np.median(rgb[L < 50], axis=0)
    for (ox, _), side, w in zip(P.outline, (-1, 1), widths):
        O = np.array([ox, a + b * ox])
        u = side * ((gx - O[0]) * e[0] + (gy - O[1]) * e[1])
        v = (gx - O[0]) * n[0] + (gy - O[1]) * n[1]
        rgb[(u > CUT) & (np.abs(v) < 3 * w)] = glaze
    # the drawing's frame: the shaft as a band on the line, from CUT past each outline to its end
    Ha, Wa = fl.all_shape
    gy, gx = np.mgrid[0:Ha, 0:Wa].astype(np.float32)
    A = np.array([fl.dx, a])  # the line's point at the figure frame's x = 0, in the drawing's frame
    t_along = (gx - A[0]) * e[0] + (gy - A[1]) * e[1]
    v = (gx - A[0]) * n[0] + (gy - A[1]) * n[1]
    body = np.zeros((Ha, Wa), bool)
    lines = np.zeros((Ha, Wa), bool)
    wt = lw.HOUSE_WEIGHT * max(Ha, Wa)
    for name, (ox, _), side, w in zip(("butt", "blade"), P.outline, (-1, 1), widths):
        end = SPEAR_ENDS[name]
        q = fl.photo_to_all(end["photo"], [end["start"], end["tip"]])
        u_out = (fl.dx + ox - A[0]) * e[0] + (a + b * ox - A[1]) * e[1]  # the outline, along the line
        u_start, u_tip = ((q - A) @ e)
        seg = (side * (t_along - u_out) > CUT) & (side * (t_along - u_start) < 2)
        # the edges centred on the shaft's edges: drawn a quarter outside, as the
        # figure's outline is, the thin shaft's clay core would break up in tracing
        body |= seg & (np.abs(v) <= w / 2 + wt / 4)  # inside the lines' outer edge, or clay shows past them
        lines |= seg & (np.abs(np.abs(v) - w / 2) <= wt / 2)
        eb, el = spear_end(fl, photos[end["photo"]], end, q, A + u_start * e, A + u_tip * e, w)
        body |= eb
        lines |= el
        print(f"  {name}: {abs(u_tip - u_out):.0f} px past his outline; the model's tip lies "
              f"{abs((q[1] - A) @ n):.0f} px off the line")
    return body, lines


def spear_end(fl: Flat, photo, end, q, start, tip, w):
    """One end of the spear from its photo: unrolled through the model into the
    drawing's frame, moved so its own axis (q: START, TIP) lies on the line
    (start -> tip), found like the figure (clay = body, painted lines,
    outline). Returns (body, lines) in the drawing's frame."""
    a = np.asarray(Image.open(photo).convert("RGB"), dtype=np.float32)
    Ha, Wa = fl.all_shape
    # a box round the end on the line
    x0, x1 = int(min(start[0], tip[0]) - 80), int(max(start[0], tip[0]) + 80)
    y0, y1 = int(min(start[1], tip[1]) - 80), int(max(start[1], tip[1]) + 80)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, Wa), min(y1, Ha)
    Y, X = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    # the similarity carrying the target axis (start, tip) back onto the model's (q0, q1)
    d_t, d_q = tip - start, q[1] - q[0]
    k = np.hypot(*d_q) / np.hypot(*d_t)
    ang = np.arctan2(d_q[1], d_q[0]) - np.arctan2(d_t[1], d_t[0])
    c, s = np.cos(ang) * k, np.sin(ang) * k
    Xm = q[0][0] + c * (X - start[0]) - s * (Y - start[1])
    Ym = q[0][1] + s * (X - start[0]) + c * (Y - start[1])
    uv = fl.all_to_photo(end["photo"], Xm.ravel(), Ym.ravel()).reshape(X.shape + (2,))
    p = np.stack([ndi.map_coordinates(a[..., k_], [uv[..., 1], uv[..., 0]], order=1) for k_ in range(3)], -1)
    prb = p[..., 0] - p[..., 2]
    clay = ndi.binary_closing(prb > CLAY_RB, structure=morphology.disk(3))
    lab, _ = ndi.label(clay)
    # the end: the clay joined to its axis
    along = np.linspace(0.15, 0.95, 9)
    keys = [lab[int(round(start[1] + f * d_t[1])) - y0, int(round(start[0] + f * d_t[0])) - x0] for f in along]
    part = np.isin(lab, [k_ for k_ in keys if k_])
    # cut off the shaft stub behind the start (the drawn shaft takes over there)
    e = d_t / np.hypot(*d_t)
    part &= ((X - start[0]) * e[0] + (Y - start[1]) * e[1]) > -2
    part = ndi.gaussian_filter(part.astype(np.float32), 1.0) > 0.5
    wt = lw.HOUSE_WEIGHT * max(Ha, Wa)
    inner = lw.ink_lines(lum(p), size=15, low=14, high=30, sigma=1.0) & ndi.binary_erosion(part, iterations=3)
    edge = (part & (ndi.distance_transform_edt(part) <= 0.75 * wt)) | (~part & (ndi.distance_transform_edt(~part) <= 0.25 * wt))
    # the edge across the joint with the shaft is not an outline
    edge &= ((X - start[0]) * e[0] + (Y - start[1]) * e[1]) > 0.75 * wt
    body = np.zeros((Ha, Wa), bool)
    lines = np.zeros((Ha, Wa), bool)
    body[y0:y1, x0:x1] = part
    lines[y0:y1, x0:x1] = edge | morphology.remove_small_objects(inner, max_size=30)
    return body, lines


def floor_mask(L, cut):
    """Everything below the floor cut, snapped to the darkest line near it."""
    from skimage.draw import line
    H, W = L.shape
    rough = np.zeros(L.shape, bool)
    pts = [(int(round(x)), int(round(y))) for x, y in (q for q in cut if q != lw.STRAIGHT)]
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        rr, cc = line(ya, xa, yb, xb)
        rough[rr.clip(0, H - 1), cc.clip(0, W - 1)] = True
    near = ndi.distance_transform_edt(~rough) <= CORRIDOR
    cost = np.where(near, 1.0 + ndi.gaussian_filter(L, 1.5) / 8.0, 1e4)
    path = lw.livewire(cost, cut)
    outline = np.vstack([path, [(W - 0.5, H - 0.5), (0.5, H - 0.5)]])
    return lw.polygon_mask(L.shape, outline)


def masks(rgb, P):
    """The figure's area (sil), his hair (solid), and the zones, from the frame."""
    L, RB = lum(rgb), rgb[..., 0] - rgb[..., 2]
    shape = L.shape
    clay = ndi.binary_opening(RB > CLAY_RB, structure=morphology.disk(2))
    out = floor_mask(L, P.floor)
    lab, _ = ndi.label(ndi.binary_closing(clay & ~out, structure=morphology.disk(4)) & ~out)
    fig = lab == lab[int(round(P.seed[1])), int(round(P.seed[0]))]
    # his hair's thin outline, closed where it is faint, walls in his hair
    hair_zone = poly(shape, P.hair)
    fig = ndi.binary_closing(fig | (hair_zone & (RB > OUTLINE_RB)), structure=morphology.disk(3))
    # painted lines and his hair are holes in the clay: fill them, but not the open glaze
    holes, _ = ndi.label(ndi.binary_fill_holes(fig) & ~fig)
    keep_open = [holes[int(round(y)), int(round(x))] for x, y in P.open if holes[int(round(y)), int(round(x))]]
    inside = fig | ((holes > 0) & ~np.isin(holes, keep_open))
    hair = hair_zone & inside & ~clay
    hair = ndi.binary_closing(hair, structure=morphology.disk(3)) & hair_zone & inside
    hair = morphology.remove_small_objects(ndi.gaussian_filter(hair.astype(float), 1.5) > 0.5, max_size=300)
    # the sandals' straps are wide and dark and cut notches into the clay: close them up
    feet = np.zeros(shape, bool)
    for f in P.feet:
        feet |= poly(shape, f)
    inside |= ndi.binary_fill_holes(ndi.binary_closing(inside & feet, structure=morphology.disk(12))) & feet & ~out
    sil = ndi.gaussian_filter(inside.astype(float), 1.5) > 0.5
    return sil, hair, hair_zone, out, L


def drawing(rgb, P, above, w):
    """The lines (ink) and the figure's area (sil) from the figure's frame, and
    its luminance; `above`: where the frame shows photo 03; w: the house weight
    of the whole drawing, in px."""
    sil, hair, hair_zone, out, L = masks(rgb, P)
    shape = L.shape
    # painted lines by local contrast, at each photo's own scale
    found = np.where(above, lw.ink_lines(L, size=15, low=16, high=38, sigma=1.0),
                     lw.ink_lines(L, size=31, low=10, high=26, sigma=2.5))
    faces = np.zeros(shape, bool)
    for f in P.faces:
        faces |= poly(shape, f)
    feet = [poly(shape, f) for f in P.feet]
    by_hand = poly(shape, P.hand) | feet[0] | feet[1]
    inner = ndi.binary_erosion(sil, structure=morphology.disk(4)) & ~poly(shape, P.stain) & ~hair & ~by_hand
    found &= inner & ~faces
    # wide dark strokes (the cord on his back) stay solid
    wide = lw.ink_lines(L, size=45, low=40, high=70, sigma=1.5) & inner & ~faces
    solid = ndi.binary_opening((wide | found) & (ndi.gaussian_filter(L, 1.5) < DARK), structure=morphology.disk(THICK))
    thin = found & ~ndi.binary_dilation(solid, iterations=2)
    # the rest as even lines: grain smoothed off, close pairs read as one line
    thin = ndi.gaussian_filter(ndi.binary_closing(thin, structure=morphology.disk(2)).astype(np.float32), 1.5) > 0.5
    thin = morphology.remove_small_holes(thin, max_size=HOLE)
    centres = np.where(above, centre_lines(thin), centre_lines(thin, spur=18, min_len=40))
    lines = (ndi.distance_transform_edt(~centres) <= w / 2) | solid | hair
    # the faces, by hand
    Y, X = np.mgrid[0:shape[0], 0:shape[1]]
    for x, y, r in P.face_dots:
        lines |= (X - x) ** 2 + (Y - y) ** 2 <= r * r
    lines |= strokes(L, P.face_lines, FACE_PEN) | strokes(L, [P.hairline], FACE_PEN, snap=0)
    lines |= segment(shape, P.wrap_edge, w) | strokes(L, P.hand_lines, w) | strokes(L, P.feet_lines, w, snap=8)
    lines |= strokes(L, [P.neck_back], w, snap=0)
    # the right sandal's straps, solid
    sm = ndi.gaussian_filter(L, 2.0)
    clay = ndi.gaussian_filter(ndi.grey_closing(sm, size=(41, 41)), 8)
    straps = (sm < STRAP_K * clay) & feet[1] & ndi.binary_erosion(sil, structure=morphology.disk(3))
    straps = ndi.gaussian_filter(ndi.binary_opening(straps, structure=morphology.disk(2)).astype(np.float32), 2.5) > 0.5
    lines |= morphology.remove_small_objects(straps, max_size=150)
    lines = morphology.remove_small_objects(lines, max_size=120)  # specks of wear
    # the outline, w wide, straddling the figure's edge (a quarter outside)
    edge = (sil & (ndi.distance_transform_edt(sil) <= 0.75 * w)) | (~sil & (ndi.distance_transform_edt(~sil) <= 0.25 * w))
    return edge | lines, sil, L


def main(p01: str, p02: str, p03: str, p04: str) -> None:
    photos = {"01": p01, "02": p02, "03": p03, "04": p04}
    if "--refit" in sys.argv:
        fit_model(photos)
        return
    fl = Flat(p02, p03)
    P = converted(fl)
    rgb, above = fl.image(p02, p03)
    if "--composite" in sys.argv:  # diagnostic: the figure's frame as one photo, before the spear
        Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(sys.argv[sys.argv.index("--composite") + 1])
        return
    sbody, slines = spear(fl, rgb, P, photos)
    Ha, Wa = fl.all_shape
    w = lw.HOUSE_WEIGHT * max(Ha, Wa)  # the house weight of the whole drawing, in px
    ink, sil, L = drawing(rgb, P, above, w)
    H, W = ink.shape
    ink_all, sil_all = slines.copy(), sbody.copy()
    ink_all[:H, fl.dx:fl.dx + W] |= ink
    sil_all[:H, fl.dx:fl.dx + W] |= sil
    info = lw.trace_svg(
        ink_all, OUT, body=sil_all,
        title="The shepherd Euphorbos carrying the infant Oedipus on his shoulder, a long spear in his hand",
        desc="Line drawing after the Attic red-figure neck-amphora by the Achilles Painter, c. 450-445 BCE, "
             "Paris, Bibliothèque nationale de France, Cabinet des médailles 372; traced from photographs by "
             "ArchaiOptix (CC BY-SA 4.0), changed. This drawing is CC BY-SA 4.0.")
    print(OUT, info)
    qa = [a for a in sys.argv[5:] if not a.startswith("--")]
    if qa:  # optional: the drawing over its source (the figure's frame), and as the dark theme shows it
        Lall = np.full((Ha, Wa), 200.0, np.float32)
        Lall[:H, fl.dx:fl.dx + W] = L
        lw.qa_overlay(Lall, OUT, info["box"], Path(qa[0]))
        lw.qa_dark(OUT, info["box"], Path(qa[0]).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:5])
