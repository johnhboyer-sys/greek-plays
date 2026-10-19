"""Agamemnon: the murder of Agamemnon, the whole of side A of the Attic red-figure calyx-krater Boston, Museum of
Fine Arts 63.1246, attributed to the Dokimasia Painter, about 460 BC (the museum's record): Aegisthus, sword in
hand, grips the head of Agamemnon, who is caught in a net-like robe without openings; women round them, Clytemnestra
among them (the museum: "Behind Aegisthos, Klytaimnestra carries a double ax"), between the two Ionic columns under
the handles. Side B (Orestes kills Aegisthus) is not drawn. E. Vermeule, "The Boston Oresteia Krater", AJA 70 (1966)
1-22. The vase first appears in 1963, so no old plate exists: the drawing is traced from the museum's photos.

Photos (John, 2026-10-15: these three, "column to column"): the museum's side-A view as Google Arts & Culture serves
it (3853 px wide, the deepest level of its tile pyramid, put together from its viewer's tiles; the same photo the
museum's own site gives at 1350 px), and the museum's two black-and-white handle views (600896, the column at side
A's left edge in its middle; 600897, the column at its right edge). Credit: Museum of Fine Arts, Boston.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli`. Two steps are geometry, not
image filtering, and stay in numpy/scipy: taking the painting off the vase's curve (vase_unroll.py) and fitting
the vase (--refit). The SVG is written by linework.trace_svg.

Photo -> flat:
  - The photos carry no focal length. The vase's profile and the three cameras were fitted together (MODEL, as
    wasps.py): to the lower edge of the meander band under the picture (a painted circle) in all three, the vase's
    outline in all three (rows clear of the handles), and points of the painting matched between the front and each
    handle view (SIFT).

    python3 docs/redesign/drawings/tools/agamemnon.py front.png left.jpg right.jpg --refit
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

OUT = Path(os.environ.get("AGAMEMNON_OUT", Path(__file__).resolve().parent.parent / "agamemnon.svg"))
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
Image.MAX_IMAGE_PIXELS = None

# ---------------------------------------------------------------- the vase

NAMES = ["front", "left", "right"]   # GAC side A; MFA 600896 (side A's left column); MFA 600897 (its right column)
# MODEL: vase_unroll.fit on the data in fit_model() (run with --refit to fit again; it prints these numbers). World
# units are arbitrary (the front camera's D fixes them); y = 0 on the meander band's lower edge, up the vase.
# The focal lengths: each photo's half-width at the picture times DIST, the camera's distance in picture radii. Fitted
# on the outline and the meander band alone the fit kept improving out to 40 radii, but the checkers band then sagged
# too little (see RING_*); with that band's edge as a ring, and the matches found on the flat (FM_*), tried at 10, 12,
# 15, 20 and 27: cost 16200, 13625, 13322, 14603, 16408, so DIST is 15. (The fit: band median 3.7 px in the front, 3.5
# in both handle views; outlines 4.1, 6.5 and 4.5 px; the checkers ring 1.5 px; matches on the flat 1.2 px to the left
# view (n 294), 0.8 px to the right (n 318).)
DIST = 15.0
CAMERAS = {
    "front": dict(D=4000, H=1.58628, b=-0.0603714, p=-0.00210035, g=-0.0260547, f=18120, cx=1926.5, cy=2048),
    "left": dict(D=3992.8, H=418.12, b=0.0701005, p=0.000569393, g=-0.0011101, f=7305, cx=757, cy=800),
    "right": dict(D=4024.15, H=214.403, b=0.0166643, p=0.000376957, g=-0.0178407, f=7215, cx=752.5, cy=800),
}
PROFILE_PX = [-650, -400, -150, 100, 350, 600, 850, 1100, 1350, 1600, 1850, 2050]   # knots, in front px above the band
PROFILE_R = [113.2, 189.03, 237.21, 230.68, 232.79, 244.03, 254.35, 264.51, 276.06, 291.44, 310.28, 337.74]
TURNS = {"left": 95.412, "right": -99.227}   # degrees each handle view is turned from the front
D0 = 4000.0
# The data for fit_model: the rows (photo px) where each photo's outline is the vase's own (clear of the handles and
# the rim's lip), and rough guides to the band's lower edge (in the handle views, either side of the handle)
FIT_ROWS = {"front": [(1100, 2350), (3450, 3800)], "left": [(250, 1000), (1100, 1240)],
            "right": [(250, 1000), (1100, 1240)]}
FIT_BAND = {"front": [[(1000, 3172), (1500, 3171), (1900, 3159), (2500, 3135), (2950, 3130)]],
            "left": [[(300, 1072), (420, 1063), (520, 1066)], [(1000, 1080), (1100, 1080), (1200, 1073)]],
            "right": [[(300, 1076), (420, 1080), (520, 1070)], [(1000, 1085), (1100, 1074), (1200, 1076)]]}
# the axis and the vase's half-width at the picture's middle in each photo (px), roughly: the matches' turn filter
# and the focal lengths (each photo's f is its half-width times DIST, the camera's distance in vase radii)
AXIS = {"front": (1957.0, 1208.0), "left": (749.0, 487.0), "right": (756.0, 481.0)}
TURN0 = {"left": 90.0, "right": -90.0}
# The profile is loose above the outline's last rows: without more, the checkers band (a painted circle) bowed down
# about 100 flat px toward both ends of the flat, and a camera 40 radii away sags it too little (in the front photo it
# sags about 92 px from the middle to 65 degrees out; at 40 radii a model gives 28). So the fit also holds the profile
# to that band's lower edge (a vase_unroll "ring": a painted circle of fitted height and radius the profile passes
# through): per column (every RING_STEP px) within RING_BOX (photo px: x0, x1, the rows searched v0, v1), every row
# below RING_ABOVE px of clay (red less blue over 85 in the front, grey over 140 in the others) with no clay in the
# RING_BELOW px under it; of these the largest set within RING_TOL px of one parabola (RANSAC, seeded), then within
# RING_TOL of a quartic through it (heads, hands and the tops of the checks fall away)
RING_BOX = {"front": (500, 3400, 950, 1450), "left": (120, 1420, 150, 500), "right": (90, 1400, 150, 500)}
RING_STEP = {"front": 8, "left": 4, "right": 4}
RING_ABOVE = {"front": 8, "left": 6, "right": 6}
RING_BELOW = {"front": 60, "left": 30, "right": 30}
RING_TOL = {"front": 4.0, "left": 2.5, "right": 2.5}
# where SIFT looks (photo px, x0 y0 x1 y1): the picture zone only, under the checkers and over the meander band (the
# palmettes and the meander repeat and matched falsely), and in each handle view only side A's half; in the front
# only the half toward that handle view
MATCH_BOX = {"front": {"left": (0, 1150, 1957, 3100), "right": (1957, 1150, 3853, 3100)},
             "left": (749, 290, 1514, 1050), "right": (0, 290, 756, 1050)}


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def outline(L, rows, step=20):
    """(side, u, v): the vase's outline in rows `rows` [(v0, v1)] of the grey image L, where the light background
    (its own level in that row, read at the image's edge) meets the vase, to a fraction of a px at the half-way
    crossing."""
    L = ndi.gaussian_filter(L, 1.0)
    out = []
    for v0, v1 in rows:
        for v in range(v0, v1 + 1, step):
            row = L[v]
            for side in (0, 1):
                r = row if side == 0 else row[::-1]
                bgl = np.median(r[:40])
                x = int(np.argmax(r < bgl - 35))
                inner = np.median(r[x + 6:x + 30])
                mid = (bgl + inner) / 2
                seg = r[max(x - 12, 0):x + 13]
                k = np.nonzero((seg[:-1] >= mid) & (seg[1:] < mid))[0]
                if not len(k) or x < 30:
                    continue
                k = k[-1]
                u = max(x - 12, 0) + k + (seg[k] - mid) / (seg[k] - seg[k + 1])
                out.append((side, u if side == 0 else len(row) - 1 - u, v))
    return np.array(out)


def band_bottom(L, rough, half=40, step=8, above_min=100, below_max=60):
    """(u, v) along the meander band's lower edge in the grey (or red less blue) image L: per column near the rough
    guide, the step from the band's clay above (over above_min for 12 px) to the glaze below (under below_max for
    36 px), to a fraction of a px; kept where the points lie on one smooth curve (as mika.band_bottom)."""
    r = np.array(rough, float)
    f = np.polyfit(r[:, 0], r[:, 1], min(2, len(r) - 1))
    out = []
    for u in range(int(r[0, 0]), int(r[-1, 0]), step):
        vg, col, best = int(np.polyval(f, u)), L[:, u], None
        for v in range(vg - half, vg + half):
            above, below = col[v - 14:v - 2].mean(), col[v + 3:v + 39].mean()
            if below < below_max and above > above_min and (best is None or above - below > best[0]):
                best = (above - below, v, above, below)
        if best:
            _, v, above, below = best
            mid, seg = (above + below) / 2, col[v - 8:v + 9]
            k = np.nonzero((seg[:-1] > mid) & (seg[1:] <= mid))[0]
            if len(k):
                k = k[np.argmin(abs(k - 8))]
                out.append((u, v - 8 + k + (seg[k] - mid) / (seg[k] - seg[k + 1])))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 2), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 2]


def ring_edge(clay, n):
    """(u, v) along the checkers band's lower edge in photo `n` (see RING_*)."""
    x0, x1, v0, v1 = RING_BOX[n]
    a, b = RING_ABOVE[n], RING_BELOW[n]
    cand = []
    for u in range(x0, x1, RING_STEP[n]):
        col = clay[v0:v1, u]
        cand += [(u, v0 + y - 0.5) for y in range(a, v1 - v0 - b) if col[y - a:y].all() and not col[y:y + b].any()]
    cand = np.array(cand)
    rng, best = np.random.default_rng(0), None
    for _ in range(3000):
        s = cand[rng.choice(len(cand), 3, replace=False)]
        if len(set(s[:, 0])) < 3:
            continue
        inl = np.abs(np.polyval(np.polyfit(s[:, 0], s[:, 1], 2), cand[:, 0]) - cand[:, 1]) < RING_TOL[n]
        if best is None or inl.sum() > best.sum():
            best = inl
    pts = cand[best]
    return pts[np.abs(pts[:, 1] - np.polyval(np.polyfit(pts[:, 0], pts[:, 1], 4), pts[:, 0])) < RING_TOL[n]]


def measure(photos):
    """The fit's data from the photos: {name: (grey, outline, band)}, the checkers band's lower edge {name: (u, v)} and
    the matches front -> each handle view."""
    import cv2
    data, ring = {}, {}
    for n in NAMES:
        rgb = np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32)
        L = rgb.mean(2)
        if n == "front":
            bl = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5)
            band = np.vstack([band_bottom(bl, g, above_min=85, below_max=45) for g in FIT_BAND[n]])
        else:
            bl = ndi.gaussian_filter(L, 1.0)
            band = np.vstack([band_bottom(bl, g) for g in FIT_BAND[n]])
        data[n] = (L, outline(L, FIT_ROWS[n]), band)
        ring[n] = ring_edge(ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.5) > 85 if n == "front"
                            else ndi.gaussian_filter(L, 1.0) > 140, n)
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(n, k, box):
        g = cv2.resize(data[n][0].clip(0, 255).astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        m = np.zeros_like(g)
        m[int(box[1] * k):int(box[3] * k), int(box[0] * k):int(box[2] * k)] = 255
        kp, d = sift.detectAndCompute(g, m)
        return np.array([p.pt for p in kp]) / k, d

    matches = {}
    for n in ("left", "right"):
        kf, df = feats("front", 0.4, MATCH_BOX["front"][n])
        kn, dn = feats(n, 1.0, MATCH_BOX[n])
        good = [a for a, b in cv2.BFMatcher(cv2.NORM_L2).knnMatch(df, dn, k=2) if a.distance < 0.8 * b.distance]
        a, b = np.float32([kf[x.queryIdx] for x in good]), np.float32([kn[x.trainIdx] for x in good])
        (ua, ra), (ub, rb) = AXIS["front"], AXIS[n]
        d = np.degrees(np.arcsin(np.clip((b[:, 0] - ub) / rb, -1, 1)) - np.arcsin(np.clip((a[:, 0] - ua) / ra, -1, 1)))
        print(n, "matches", len(good), "turn histogram", np.histogram(d, bins=12, range=(-180, 180))[0])
        matches[n] = np.hstack([a, b])[np.abs(d - TURN0[n]) < 20]
    return data, ring, matches


def fit_once(data, matches, dist, x_start=None, ring=None):
    """vase_unroll.fit at camera distance `dist` (picture radii): (model, report, x); model = (cams, R, k, turns)."""
    r0 = D0 / dist   # the picture's radius in world units, at this distance
    k = r0 / AXIS["front"][1]   # world units per front px at the picture
    knots = np.array(PROFILE_PX, float) * k
    views, x0 = {}, []
    for n in NAMES:
        L, sil, band = data[n]
        views[n] = dict(size=L.shape[::-1], f=AXIS[n][1] * dist, sil=[tuple(r) for r in sil], band=band)
        x0 += [D0, 0.5 * r0, 0.0, 0.0, 0.0, D0, 0.0, 0.0]   # a start: the camera level with the picture (f given)
    s = data["front"][1]
    bv = np.median(data["front"][2][:, 1])
    left, right = s[s[:, 0] == 0], s[s[:, 0] == 1]
    hw = (np.interp(left[:, 2], right[:, 2], right[:, 1]) - left[:, 1]) / 2
    o = np.argsort(bv - left[:, 2])
    Rk = np.interp(knots, (bv - left[o, 2]) * k, hw[o] * k)
    x0 += list(Rk) + [2000.0 * k, float(Rk[-2])]   # (the ring: the checkers band, about 2000 front px above the band)
    x0 += [np.radians(TURN0["left"]), np.radians(TURN0["right"])]
    cams, R, _, turns, report, x = vu.fit(views, knots, ring=ring, matches=matches, d0=D0, rounds=3, outlier=30,
                                          nfev=1500, x_start=np.array(x0) if x_start is None else x_start)
    return (cams, R, k, {n: float(np.degrees(t)) for n, t in turns.items()}), report, x


# Matching again on the flat: the first fit's matches are few (SIFT across a turn of 90 degrees, the painting
# foreshortened near the front photo's edge), so the front and each handle view are laid onto the flat with the first
# fit, matched there (where they look alike: SIFT, ratio FM_RATIO, shifts under FM_SHIFT flat px, RANSAC on a
# similarity within FM_RANSAC px) inside the strip where both see the vase at least FM_SHARP sharp, and the matches
# taken back to photo px for the next fit
FM_RATIO, FM_SHIFT, FM_RANSAC, FM_SHARP = 0.8, 120.0, 6.0, 0.15
FM_ROUNDS = 2   # (each round lays the photos on with the last fit, so the second finds more)



def flat_matches(photos, model):
    """Matches front -> each handle view found on the flat (see FM_*): {view: (u, v) front, (u, v) view}."""
    import cv2
    out = {}
    maps = {}
    for n in NAMES:
        uv, sh = zip(*[view_maps(n, slice(r0, r0 + CHUNK), model) for r0 in range(0, frame(model)[-1], CHUNK)])
        maps[n] = (np.concatenate(uv), np.concatenate(sh))
    flats = {}
    for n in NAMES:
        rgb = np.asarray(Image.open(photos[n]).convert("RGB"), dtype=np.float32)
        uv = maps[n][0]
        L = rgb @ np.array([0.299, 0.587, 0.114], np.float32)   # (as PIL's grey, which the matches were found on)
        flats[n] = [ndi.map_coordinates(a, [uv[..., 1], uv[..., 0]], order=3, cval=0)
                    for a in ((L, rgb[..., 0] - rgb[..., 2]) if n == "front" else (L,))]
    for n in ("left", "right"):
        both = (maps[n][1] > FM_SHARP) & (maps["front"][1] > FM_SHARP)
        fl = {v: cv2.createCLAHE(2.0, (8, 8)).apply(flats[v][0].clip(0, 255).astype(np.uint8)) for v in ("front", n)}
        sift = cv2.SIFT_create(contrastThreshold=0.01)
        m8 = (both * 255).astype(np.uint8)
        ka, da = sift.detectAndCompute(fl["front"], m8)
        kb, db = sift.detectAndCompute(fl[n], m8)
        good = [x for x, y in cv2.BFMatcher(cv2.NORM_L2).knnMatch(da, db, k=2) if x.distance < FM_RATIO * y.distance]
        a = np.float32([ka[x.queryIdx].pt for x in good])
        b = np.float32([kb[x.trainIdx].pt for x in good])
        near = np.hypot(*(a - b).T) < FM_SHIFT
        a, b = a[near], b[near]
        _, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=FM_RANSAC)
        inl = inl.ravel().astype(bool)
        a, b = a[inl], b[inl]
        print(f"flat matches front->{n}: {len(good)} found, {near.sum()} near, {inl.sum()} kept; shift median "
              f"{np.median(np.hypot(*(a - b).T)):.1f} flat px")
        pa = np.stack([ndi.map_coordinates(maps["front"][0][..., i], [a[:, 1], a[:, 0]], order=1) for i in (0, 1)], -1)
        pb = np.stack([ndi.map_coordinates(maps[n][0][..., i], [b[:, 1], b[:, 0]], order=1) for i in (0, 1)], -1)
        out[n] = np.hstack([pa, pb])
    return out


def fit_model(photos, dists=(8.0, 12.0, 18.0, 27.0, 40.0)):
    """Refit MODEL from the three photos and print it, for each camera distance in `dists` (see vase_unroll.fit):
    first on the photos' own matches, then on matches found on the flat."""
    data, ring, matches = measure(photos)
    for n in NAMES:
        print(n, "outline", len(data[n][1]), "band", len(data[n][2]), "ring", len(ring[n]),
              "matches", len(matches.get(n, [])))
    for dist in dists:
        model, report, x = fit_once(data, matches, dist, ring=ring)
        print(f"DIST {dist}, first fit")
        print("\n".join(report))
        for r in range(FM_ROUNDS):
            fm = flat_matches(photos, model)
            model, report, x = fit_once(data, fm, dist, x_start=x, ring=ring)
            print(f"DIST {dist}, fit {r + 2} (matches on the flat)")
            print("\n".join(report))
        cams, R, k, turns = model
        print("CAMERAS = {")
        for n, c in cams.items():
            print(f'    "{n}": dict(' + ", ".join(f"{q}={c[q]:.6g}" for q in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
        print("}")
        print("PROFILE_R =", [round(float(R(y)), 2) for y in np.array(PROFILE_PX) * k])
        print("TURNS =", {n: round(t, 3) for n, t in turns.items()})


# ---------------------------------------------------------------- the flat

# As wasps.py (John's choice, 2026-10-10, of the flat with the rings straight over the shear-free one): x = R_C (theta
# - theta_C), y = the arc length up the profile, where R_C is the radius at CENTRE (a front-photo point at the scene's
# middle, Aegisthus' chest), theta in the front photo's terms. G px per world unit is the front photo's own scale at
# CENTRE. The frame runs over TH_SPAN (degrees, the front photo's terms: column to column, with a margin) and FLAT_PX
# (front px above the band, at the centre: from under the band's top to over the checkers).
CENTRE = (1900.0, 2000.0)
TH_SPAN = (-95.0, 112.0)
FLAT_PX = (-60.0, 2080.0)


def vase():
    """MODEL: (cams, R, world units per front px at the picture, turns)."""
    k = D0 / DIST / AXIS["front"][1]
    return ({n: dict(c) for n, c in CAMERAS.items()}, CubicSpline(np.array(PROFILE_PX) * k, PROFILE_R), k,
            dict(TURNS))


def frame(model=None):
    """(cams, R, theta_C, R_C, arc table (y, t), X0, Y1, G, W, H)."""
    cams, R, k, _ = model or vase()
    c = cams["front"]
    y_lo, y_hi = FLAT_PX[0] * k, FLAT_PX[1] * k
    t0 = vu.photo_to_surface(c, R, np.array([CENTRE]), (y_lo - 50 * k, y_hi + 50 * k))[0]
    P = vu.project(c, vu.surface(R, np.array([t0[1], t0[1] + 1.0]), np.array([t0[0], t0[0]])))
    G = float(np.hypot(*(P[1] - P[0])))
    rc = float(R(t0[1]))
    yt, tt = vu.arc_table(R, y_lo - 5 * k, y_hi + 5 * k)
    X0, X1 = rc * (np.radians(TH_SPAN[0]) - t0[0]), rc * (np.radians(TH_SPAN[1]) - t0[0])
    Y0, Y1 = np.interp(y_lo, yt, tt), np.interp(y_hi, yt, tt)
    return cams, R, float(t0[0]), rc, (yt, tt), X0, Y1, G, int((X1 - X0) * G), int((Y1 - Y0) * G)


def view_maps(name, rows=None, model=None):
    """For photo `name`: its (u, v) for each flat px, and its sharpness there (photo px per flat px in the map's
    worst direction, its smaller singular value: where the surface turns away the photo squeezes it one way only, and
    the root of the area scale let the front photo's smear win; 0 where the surface faces away from it). rows: a slice
    of the flat's rows."""
    cams, R, th0, rc, (yt, tt), X0, Y1, G, W, H = frame(model)
    gy, gx = np.mgrid[rows or slice(0, H), 0:W].astype(np.float64)
    c = cams[name]
    turn = np.radians((model or vase())[3].get(name, 0.0))

    def uv(gx, gy):
        th = th0 + (X0 + gx / G) / rc + turn
        y = np.interp(Y1 - gy / G, tt, yt)
        return vu.project(c, vu.surface(R, y.ravel(), th.ravel())).reshape(gx.shape + (2,)), th, y

    p, th, y = uv(gx, gy)
    px, _, _ = uv(gx + 1, gy)
    py, _, _ = uv(gx, gy + 1)
    a, b = px - p, py - p
    det = np.abs(a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0])
    T = (a ** 2).sum(-1) + (b ** 2).sum(-1)
    sharp = np.sqrt(np.maximum(T - np.sqrt(np.maximum(T * T - 4 * det * det, 0)), 0) / 2)
    # facing: the surface normal against the line of sight
    r, dr = R(y), R(y, 1)
    nrm = np.stack([np.sin(th), -dr, np.cos(th)], -1)
    P = vu.surface(R, y, th)
    cam = np.array([0.0, c["H"], c["D"]])
    face = np.einsum("...i,...i->...", nrm, cam - P) / (np.linalg.norm(nrm, axis=-1) * np.linalg.norm(cam - P, axis=-1))
    return p.astype(np.float32), np.where(face > 0.05, sharp, 0.0).astype(np.float32)


# Where the handle views take over: each flat px is taken from the photo that sees it sharpest (most photo px per flat
# px, in the worst direction; the front photo has 2.6 times the handle views' px, so it holds out to about 66 degrees
# from its own axis). The
# join is a seam through the ground: within SEAM_W flat px of where the two see alike, the path down the flat (a step
# of at most a px a row) through the least clay (its cost the grey squared, so it keeps to the ground where it can), both photos laid on and blurred SEAM_BLUR px. The handle views are
# black and white: their grey is matched to the front photo's grey (and to its red less blue, for the clay) by a
# straight line taking their glaze and clay (percentiles TONE_Q over that strip, blurred SEAM_BLUR px, where both see
# the vase at least FM_SHARP sharp) to the front photo's own in the middle of the picture (TONE_BOX, flat px, where it
# is TONE_SHARP sharp). (Fitted px to px over the strip the line came out at a slope of 0.08, and matched to the
# front's own levels in the strip, where it sees the vase edge on and darker, the clay came out at 129 against 169.)
SEAM_W, SEAM_BLUR, CHUNK = 260, 2.0, 256
TONE_Q, TONE_BOX, TONE_SHARP = [5, 90], (1500, 300, 3200, 2100), 0.8
SEAM_FLOOR = 0.3
# In each handle view the handle's loop stands in front of the picture's lowest strip by the column: the loop
# (polygon, photo px) counts as unseen, its opening too (the vase shows through it, but John, 2026-10-15: the edge
# figures end "at the handle line"; the opening's polygon is kept for the record)
HANDLES = {"left": ([(500, 1210), (510, 1080), (560, 1040), (580, 980), (585, 910), (615, 865), (670, 832), (740, 820), (810, 822), (870, 845), (905, 885), (920, 940), (930, 1010), (970, 1050), (1020, 1090), (1030, 1210)],
                    [(658, 1210), (655, 950), (665, 910), (695, 888), (750, 882), (810, 886), (845, 905), (858, 940), (860, 1210)]),
           "right": ([(480, 1210), (490, 1080), (530, 1030), (535, 930), (550, 865), (600, 825), (670, 810), (740, 812), (800, 830), (845, 870), (860, 940), (870, 1020), (920, 1060), (950, 1120), (950, 1210)],
                     [(600, 1210), (600, 950), (615, 900), (650, 875), (710, 872), (760, 890), (785, 930), (795, 970), (800, 1210)])}


def seam(cost):
    """The least-cost path down `cost` (H x w), a step of at most one column a row: its column in each row."""
    H, w = cost.shape
    acc = cost.astype(np.float64).copy()
    for i in range(1, H):
        prev = acc[i - 1]
        best = np.minimum(prev, np.minimum(np.r_[np.inf, prev[:-1]], np.r_[prev[1:], np.inf]))
        acc[i] += best
    path = np.zeros(H, int)
    path[-1] = int(np.argmin(acc[-1]))
    for i in range(H - 2, -1, -1):
        j = path[i + 1]
        lo, hi = max(j - 1, 0), min(j + 2, w)
        path[i] = lo + int(np.argmin(acc[i, lo:hi]))
    return path


def flat_image(photos):
    """The three photos laid onto the flat frame and joined: (grey, red less blue, source, sharpness), H x W uint8 each
    (source 0 front, 1 left, 2 right; sharpness of the photo used, times 100)."""
    *_, W, H = frame()
    rgb = np.asarray(Image.open(photos["front"]).convert("RGB"), dtype=np.float32)
    srcs = {"front": (rgb.mean(2), rgb[..., 0] - rgb[..., 2])}
    del rgb
    for n in ("left", "right"):
        srcs[n] = (grey(photos[n]),)
    g, sh = {}, {}
    rb = np.zeros((H, W), np.float32)
    for n in NAMES:
        g[n] = np.zeros((H, W), np.float32)
        sh[n] = np.zeros((H, W), np.float32)
        for r0 in range(0, H, CHUNK):
            rows = slice(r0, min(r0 + CHUNK, H))
            uv, sharp = view_maps(n, rows)
            ims = srcs[n]
            hh, ww = ims[0].shape
            inside = (uv[..., 0] > 2) & (uv[..., 0] < ww - 3) & (uv[..., 1] > 2) & (uv[..., 1] < hh - 3)
            if n in HANDLES:
                hw = ims[0].shape
                loop = lw.polygon_mask(hw, np.array(HANDLES[n][0], float))
                inside &= ~ndi.map_coordinates(loop, [uv[..., 1], uv[..., 0]], order=0, cval=0).astype(bool)
            sh[n][rows] = np.where(inside, sharp, 0)
            g[n][rows] = ndi.map_coordinates(ims[0], [uv[..., 1], uv[..., 0]], order=3, cval=0)
            if n == "front":
                rb[rows] = ndi.map_coordinates(ims[1], [uv[..., 1], uv[..., 0]], order=3, cval=0)
    src = np.zeros((H, W), np.uint8)
    out_g, out_rb = g["front"].copy(), rb.copy()
    mid = np.zeros((H, W), bool)
    mid[TONE_BOX[1]:TONE_BOX[3], TONE_BOX[0]:TONE_BOX[2]] = True
    mid &= sh["front"] > TONE_SHARP
    centre_g, centre_rb = np.percentile(g["front"][mid], TONE_Q), np.percentile(rb[mid], TONE_Q)
    tone = {}
    xx = np.arange(W)
    for k, n in ((1, "left"), (2, "right")):
        better = sh[n] > sh["front"]
        half = (xx < W // 2) if n == "left" else (xx >= W // 2)
        cols = np.where(better & half[None, :], xx[None, :], -1 if n == "left" else W)
        edge = cols.max(1) if n == "left" else cols.min(1)   # per row: the last (first) column the side view wins
        xb = int(np.median(edge))
        lo, hi = max(xb - SEAM_W, 0), min(xb + SEAM_W + 1, W)
        both = (sh[n][:, lo:hi] > FM_SHARP) & (sh["front"][:, lo:hi] > FM_SHARP)
        gf, gs = (ndi.gaussian_filter(a[:, lo:hi], SEAM_BLUR) for a in (g["front"], g[n]))
        rf = ndi.gaussian_filter(rb[:, lo:hi], SEAM_BLUR)
        qs = np.percentile(gs[both], TONE_Q)
        tone_g = lambda x, qs=qs: centre_g[0] + (x - qs[0]) * (centre_g[1] - centre_g[0]) / (qs[1] - qs[0])
        tone_rb = lambda x, qs=qs: centre_rb[0] + (x - qs[0]) * (centre_rb[1] - centre_rb[0]) / (qs[1] - qs[0])
        print(f"{n}: seam near flat x {xb}; its glaze and clay {qs.round()} -> grey {centre_g.round()}, "
              f"red less blue {centre_rb.round()} (over {both.sum()} px)")
        cost = ((gf + tone_g(gs)) / 2) ** 2
        cost = np.where(both, cost, 1e6)
        path = lo + seam(cost)
        side = xx[None, :] <= path[:, None] if n == "left" else xx[None, :] >= path[:, None]
        side &= sh[n] > 0
        tone[n] = (tone_g, tone_rb)
        out_g = np.where(side, tone_g(g[n]), out_g)
        out_rb = np.where(side, tone_rb(g[n]), out_rb)
        src[side] = k
    # (where the seam left the front photo seeing the vase at a slant, under SEAM_FLOOR sharp, and a handle view sees it
    # at SEAM_FLOOR or better, the handle view is used: the front's grazing smear drew folds that are not on the vase)
    for k, n in ((1, "left"), (2, "right")):
        half = (xx < W // 2) if n == "left" else (xx >= W // 2)
        swap = (src == 0) & (sh["front"] < SEAM_FLOOR) & (sh[n] >= SEAM_FLOOR) & half[None, :]
        out_g = np.where(swap, tone[n][0](g[n]), out_g)
        out_rb = np.where(swap, tone[n][1](g[n]), out_rb)
        src[swap] = k
    used = np.choose(src, [sh["front"], sh["left"], sh["right"]])
    return (out_g.clip(0, 255).round().astype(np.uint8), out_rb.clip(0, 255).round().astype(np.uint8), src,
            (used * 100).clip(0, 255).round().astype(np.uint8))


# ---------------------------------------------------------------- the scene

CLAY = 70                     # clay: red less blue above this (blurred 2 px); glaze under it
LINE_DARK = 85                # painted lines: grey darker than this (blurred 1.5 px)
# Ground: the glaze, its painted lines (up to OPEN*2 px wide) opened away; the areas over AUTO_GROUND px, inside the
# scene too (here the figures cut the ground into pockets of 3000 to 30000 px, as large as the hair and the beard).
# Smaller glaze areas inside the figures are paint.
OPEN, AUTO_GROUND = 14, 3000
# smaller areas of ground the figures close in (flat px, a point in each): between Clytemnestra's skirt and the left
# woman's (one under the right woman's arm went with the handle-line cut)
OPEN_PTS = [(795, 1165)]
# big dark areas that are paint, not ground (flat px, a point in each): the hair of the woman behind Agamemnon, of
# Aegisthus, of Clytemnestra (two), of the left woman, of the right woman; Aegisthus' beard; and a lock by Clytemnestra's
# neck
PAINT_PTS = [(3499, 334), (2153, 301), (1186, 311), (1160, 418), (609, 389), (4296, 577), (2191, 535), (1042, 494),
             (954, 1088), (934, 1198)]
WALLS = []                    # solid paint walled off where it meets the ground (flat px polylines, WALL_W wide)
WALL_W = 8
SMOOTH = 3.0
EDGE = 8                      # the outline, flat px wide (centred on the contour)
OUT_SMOOTH = 5.0
# Faces, hands and feet (John, 2026-10-16: "a lot more work to be done"; pass 3 lost the profiles of the women at the
# left and behind Agamemnon, and the fingers): the ground's opening (OPEN 14) counted every notch of ground under 28 px
# (between nose and lips, between fingers) as paint, and the smoothing closed the rest. Inside FINE (boxes, flat px) the
# ground is opened at FINE_OPEN, the figure smoothed at FINE_SMOOTH and outlined FINE_EDGE wide. Faces: the woman at the
# left column, Clytemnestra, Aegisthus, the woman behind Agamemnon, the woman at the right column; hands: Clytemnestra's
# raised and lowered, Aegisthus' raised and on Agamemnon's head and on the sword, the raised hands of the woman behind
# Agamemnon, the right woman's on her head; and the feet along the floor
HANDS = [(624, 248, 774, 388), (714, 1038, 814, 1148), (1754, 298, 1954, 448), (2864, 448, 2994, 568),
         (1394, 948, 1544, 1108), (2604, 288, 2804, 428), (3744, 278, 3854, 438), (4124, 398, 4304, 528)]
FINE = [(454, 348, 654, 578), (1164, 298, 1390, 528), (2054, 288, 2340, 678), (3294, 248, 3494, 558),
        (4144, 508, 4324, 748), (154, 1950, 4397, 2190)] + HANDS
FINE_OPEN, FINE_SMOOTH, FINE_EDGE = 3, 1.0, 5
FLECK_HOLE = 60   # flecks in the glaze filled before the fine opening, px^2
# The painter ran a stripe of thinned glaze round each hand, outside the clay (as clouds.py's STRIPES): read as clay it
# fattened the fingers and closed the gaps between them. In HANDS only the clay lighter than HAND_G (grey, blurred 1 px;
# the hands read 160-190, the stripe 90-130) counts as clay
HAND_D = 25
# and there the outline is drawn on the ground outside the clay (as ion.py's EDGE_OUT), FINE_EDGE wide, so a finger keeps
# its clay
# The heads (HEADS: the faces and hair of the five women and Aegisthus, flat px; Agamemnon's has its own rules, AGAM_*):
# the line finder's centre-line redraw ran the curls together and filled the eyes. There every line is the grey (blurred
# HAIR_BLUR px) at half maximum: darker than halfway between the clay round (its Maximum over HEAD_HI px) and the darkest
# within HEAD_LO px, where that span is over HEAD_SPAN; pieces under HEAD_SPECK px^2 dropped; the black hair solid (the
# grey under HEAD_SOLID, closed 2 px, under HEAD_SOLID_MAX), holes under HEAD_HOLE px^2 filled; at their own shape,
# traced at their own size
HEADS = [(420, 300, 680, 600), (1130, 260, 1360, 540), (2040, 250, 2370, 560), (3290, 230, 3510, 500),
         (4110, 460, 4340, 760)]
HEAD_HI, HEAD_LO, HEAD_SPAN, HEAD_SPECK, HEAD_SOLID, HEAD_SOLID_MAX, HEAD_HOLE = 8, 2, 40, 20, 70, 110, 30
# and the same rule for fine close lines elsewhere (John, 2026-10-19): the wavy double border of Aegisthus' cloak at his
# shoulder (the locks of the woman behind Agamemnon went solid black under it: they are thinned glaze, darker than
# HEAD_SOLID)
HEADS += [(1800, 480, 2070, 800)]
STRIPE_W, STRIPE_D = 8, 35
LEVEL_SIGMA = 30
# Lines the finder found along the figure's own edge (the edge's contrast, inside the outline) doubled it (the raised
# fingers): line pieces lying for EDGE_HUG of their length within EDGE_CLEAR px of the contour go
EDGE_CLEAR, EDGE_HUG = 7, 0.75
HAND_SPECK = 150
HAND_NEAR = 9
# Inside the face boxes (FACES) every line but the outline is traced at its own size (its pieces ran into the hair and
# the outline and so were too big for FACE_MAX, and the house weight then filled the eyes)
SPECK, FLECK = 150, 200
# Lines, as mika.py: the grey's local contrast (PhotoCraft: blurred 1 px, capped at the clay's level by Levels, input
# white LC_CAP; its Maximum then Minimum over LC_R px, less it), with hysteresis (LC_LOW, LC_HIGH), LINE_LEN px or
# longer along the centre, off the outline and the solid paint; each line redrawn along its centre at the paint's own
# width (half maximum), smoothed along the line over WIDTH_SIGMA px, at least LINE_MIN wide. The mask is smoothed first
# (Gaussian MASK_SIGMA in PhotoCraft, cut at half), pinholes under HOLE px^2 filled, side spurs under SPUR px pruned.
# Solid paint: the dark (LINE_DARK) opened over SOLID_R px, drawn at its own shape
LC_CAP, LC_R, LC_LOW, LC_HIGH = 175, 5, 30, 50
LINE_LEN, HALF_R, WIDTH_SIGMA, LINE_MIN = 25, 6, 6.0, 4.0
HOLE, MASK_SIGMA, SPUR, SOLID_R = 12, 1.5, 7, 10
WEIGHT = 0.00118              # the line weight: pinned at pass 2's ("own" set it to its median, 0.118% of the longer side)
NECK = 5                      # every line thickened to at least NECK flat px along its centre before tracing
# Seeds (flat px): the woman at the left column, Clytemnestra, Aegisthus, Agamemnon, the woman behind him, the woman at
# the right column
SEEDS = [(400, 1000), (1120, 720), (1920, 800), (2800, 1400), (3400, 1000), (4200, 900)]
# The floor: the meander band's upper clay strip, which the figures stand on, is cut away. Per column (every
# FLOOR_STEP px), from FLOOR_IN px above a guide near the strip's lower edge (FLOOR_LOW) up through the strip's clay to
# the first paint or glaze above it, at most FLOOR_UP px; smoothed (a running median over FLOOR_MED). Below it is band.
# The ceiling likewise: from CEIL_IN px below a guide near the upper edge of the clay strip under the checkers
# (CEIL_HIGH) down through it to the first paint or glaze, at most CEIL_DOWN px (a hand or head touching the strip).
FLOOR_STEP, FLOOR_MED, FLOOR_IN, FLOOR_UP = 10, 5, 4, 40
FLOOR_LOW = [(0, 2186), (4652, 2186)]
CEIL_IN, CEIL_DOWN = 4, 40
CEIL_HIGH = [(0, 224), (4652, 224)]
# Where no photo sees the vase well (the photo used is less than SEEN_MIN sharp: behind the handles, and the front
# photo's edge-on strips beside them) the figures end (John, 2026-10-15: "End them at the handle line"), along that
# area's edge smoothed (Gaussian SEEN_SMOOTH, cut at half). At 0.2 the front photo's grazing smear came in under the
# handles, folds bent round in arcs that are not on the vase (John, 2026-10-19: "the warp from unroll is bad on the
# bottom left and right"); 0.3 keeps the handle views' own sight (0.33-0.38) and ends the figures in a smooth line
SEEN_MIN, SEEN_SMOOTH = 0.3, 20.0
# (narrow tongues of it, under 2 SEEN_OPEN px across, where a handle view's handle and the front's slant meet at the
# seam, notched the skirts: opened away)
SEEN_OPEN = 40
# The columns under the handles are left out (John, 2026-10-15: "column to column"): everything beyond COLUMNS
# (polylines along each column's inner edge, flat px; left, right) goes
# (the columns lean as painted: the left one's inner edge 0.087 px left per px down, the right one's 0.09)
# (the left one's abacus reaches x 450 above row 312, its capital and its neck x 345 down to row 425)
COLUMNS = ([(450, 0), (450, 312), (345, 318), (345, 425), (262, 430), (108, 2200)], [(4415, 300), (4245, 2200)])
# Faces are traced at their own size (as mika.py): boxes, flat px; in them marks of FACE_SPECK px^2 or more stand
# (heads: the woman at the left column, Clytemnestra, Aegisthus with his beard, Agamemnon, the woman behind him, the
# woman at the right column)
FACES = [(400, 300, 640, 560), (1080, 260, 1320, 520), (2020, 240, 2340, 660), (2800, 500, 3160, 1060),
         (3280, 240, 3520, 520), (4120, 480, 4320, 720)]
FACE_SPECK = 12
FACE_DOT, FACE_DOT_MAX = 40, 400
FACE_LC = (14, 28)
PALE_OFF, PALE_MIN = 4, 30
JOIN_D, JOIN_COS, JOIN_G, JOIN_BACK = 30, 0.75, 120, 12
# Inside FAINT (polygons, flat px) lines are found at the faces' lower thresholds (FACE_LC); none now (the net's faint
# lines, first found so as broken dashes of ink, are drawn as a tone: see NET)
FAINT = []
# The net-robe (John, 2026-10-15: "a lot of faint lines for the net that should be rendered as partly opaque lines"):
# over Agamemnon (NET, a polygon round him, flat px, kept to the figure) dozens of faint wavy lines in thinned glaze,
# 8-20 grey under the clay. Found by local contrast at a finer scale (PhotoCraft: blurred NET_BLUR px, its Maximum then
# Minimum over NET_R px, less it) with hysteresis (NET_LOW, NET_HIGH), off the ink (NET_OFF px), their centre lines
# NET_LEN px or longer, drawn NET_W px wide and smoothed (Gaussian NET_SMOOTH, cut at half), as a tone at NET_OPACITY
NET = [(2840, 530), (3020, 490), (3120, 590), (3100, 850), (3200, 1010), (3020, 1110), (2940, 1350), (2900, 1750), (2980, 2070), (2700, 2160), (2100, 2160), (2020, 2090), (2300, 1870), (2500, 1630), (2560, 1290), (2560, 1010), (2740, 870), (2780, 650)]
NET_BLUR, NET_R, NET_LOW, NET_HIGH, NET_OFF, NET_LEN, NET_W, NET_SMOOTH, NET_OPACITY = 1.0, 4, 5, 9, 3, 40, 4.0, 1.0, 0.45
NET_ANGLES, NET_MB, NET_TENSOR = tuple(range(0, 180, 15)), 8, 4
# Inside NET only the truly dark lines stay ink (the body's contours through the robe, the robe's edges): line pieces
# with at least NET_CORE of their px darker than LINE_DARK; the rest of the net's lines go to the tone
NET_CORE = 0.5
# and of the lines the net's finder takes, runs of NET_INK_LEN px or more along the centre where the grey (blurred 0.7
# px, its Minimum over 1 px) is darker than NET_INK_G are the body's contours seen through the robe (legs, arms: the
# net's lines read 140-175 there, the contours 50-120): drawn as ink, NET_INK_W px wide
NET_INK_G, NET_INK_LEN, NET_INK_W = 125, 40, 5.0
# Agamemnon's head (John, 2026-10-15: "I redraw, you correct"): his curls are zigzag strokes of thinned glaze and his
# beard fine strands, mid-grey (90-130 against the clay's 170), too close for lines: the grey's line finder ran them
# into a lattice. Drawn as a tone at their own shape (the grey blurred HAIR_BLUR px, darker than CURL_G in AGAM_CURLS,
# than BEARD_G in AGAM_BEARD; specks under HAIR_SPECK px^2 dropped), at HAIR_OPACITY, darker than the net's. His face's
# lines (profile, brow, eye, nose, mouth) in AGAM_FACE: the grey blurred HAIR_BLUR px, at half maximum (darker than halfway between the clay round,
# the Maximum over FACE_HI px, and the darkest within FACE_LO px), where that span is over FACE_SPAN (the net's lines
# cross his face at 20-30, his own lines about 100), redrawn along their centres FACE_W px wide. Inside these no other
# ink
AGAM_CURLS = [(2840, 520), (3170, 520), (3170, 780), (3110, 800), (3020, 790), (2985, 750), (2972, 690), (2965, 640), (2895, 640),
              (2875, 600), (2840, 600)]
AGAM_BEARD = [(2930, 765), (2995, 765), (3015, 800), (3005, 925), (2910, 925), (2915, 790)]
AGAM_FACE = [(2880, 630), (2958, 630), (2958, 700), (2950, 725), (2965, 745), (2950, 775), (2915, 780), (2884, 740)]
HAIR_BLUR, CURL_G, BEARD_G, HAIR_SPECK, HAIR_OPACITY = 0.8, 120, 135, 15, 0.7
FACE_HI, FACE_LO, FACE_SPAN, FACE_W = 11, 5, 55, 3.0
# John's marks, round 1 (2026-10-16, on the PhotoCraft file of pass 2: the flat cropped to the trace box at 1x, origin
# MARKS_ORIGIN in flat px), kept beside the tool as 1-bit PNGs (MARKS_FILES: blue, purple). Blue is ink (the body's
# contours through the net, his arm and the net's upper edge, the robe's hem, folds in Aegisthus' tunic), purple the
# net's tone (its wavy lines, drawn long and whole). Both add to mine (John, 2026-10-16): each stroke drawn along its
# centre line (side spurs under SPUR px pruned, pieces MARK_LEN px or longer), the blue MARK_W flat px wide (the traced
# line width, WEIGHT of the trace box's longer side) and traced at its own size with the faces, the purple NET_W wide
# in the tone; where his line runs on mine it is drawn once (my ink within MARK_GAP px of his blue goes)
MARKS_ORIGIN = (154, 228)
# Round 2 (2026-10-16, on pass 3's file, same origin and colours, adding as round 1): Aegisthus' profile, his arm and
# the hand on Agamemnon's head, Agamemnon's back and arm under the net and the fingers of the woman behind him (blue);
# the net below his head and down his back (purple)
# Round 3 (2026-10-19, on pass 3's file again, on his layers and as line shapes; only what is new since round 2):
# blue ink (Aegisthus' cap, ear-locks, profile, necklace and shoulder line; the edges of the sword, the axe's shaft and
# head, Clytemnestra's hand), the axe head and Aegisthus' cap painted over whole (filled shapes: BLOB_*), yellow
# clay with no ink (the sword's blade, the axe's shaft, Clytemnestra's hand, Aegisthus' raised hand and profile, a
# foot), green ground (between the fingers, round the profile, the cap's knob, by the foot): as the fifth form in
# LESSONS (Iphigenia in Tauris). Yellow and green rule the figure before its outline is drawn; my lines inside yellow go.
# Round 4 (2026-10-19, on pass 5's file, the same colours): the woman behind Agamemnon, her profile, the locks under her
# chin and her dress's folds, her raised arm; Aegisthus' outstretched arm and the hand on Agamemnon's head
MARKS_FILES = [("agamemnon_marks_1_blue.png", "agamemnon_marks_1_purple.png", None, None),
               ("agamemnon_marks_2_blue.png", "agamemnon_marks_2_purple.png", None, None),
               ("agamemnon_marks_3_blue.png", None, "agamemnon_marks_3_yellow.png", "agamemnon_marks_3_green.png"),
               ("agamemnon_marks_4_blue.png", None, "agamemnon_marks_4_yellow.png", "agamemnon_marks_4_green.png")]
BLOB_R, BLOB_MIN = 5, 200
MARK_LEN, MARK_W, MARK_SMOOTH, MARK_GAP = 10, 5.0, 1.5, 2
# Small dots painted on the clothes (the net-robe's, the right-hand woman's): inside DOTS (polygons, flat px) small marks
# standing apart from the lines (DOT_OFF px), with local contrast DOT_LC or more, DOT_MIN to DOT_MAX px^2, drawn as dots
DOTS = [[(2560, 500), (3150, 500), (3150, 1300), (3100, 2150), (2350, 2150), (2480, 1300)],
        [(3880, 600), (4420, 600), (4420, 1600), (3880, 1600)]]
DOT_LC, DOT_OFF, DOT_MIN, DOT_MAX = 30, 3, 6, 120
FACE_MAX = 20000


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


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


def even_lines(contrast, dark, area, faces, faint):
    """The painted lines: `dark`, and in `area` those found by local contrast, redrawn along their centres at the
    paint's own width (see LC_* and the constants after it; as thesmophoriazusae.py)."""
    from skimage.filters import apply_hysteresis_threshold
    found = apply_hysteresis_threshold(contrast, LC_LOW, LC_HIGH)
    found = np.where(faces | faint, apply_hysteresis_threshold(contrast, *FACE_LC), found)
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


def strip_cut(clay, guide, step_in, reach, down):
    """The row where a band's clay strip ends toward the picture, per column (every FLOOR_STEP px) along `guide` (x, y
    points inside the strip, near its outer edge): from `step_in` px inside the guide, through the strip's clay toward
    the picture (up for the floor, down for the ceiling: `down`) to the first paint or glaze, at most `reach` px; where
    the clay runs on further (a foot or a hand touching the strip) the row is taken from the columns either side.
    Returns x, y (smoothed by a running median over FLOOR_MED)."""
    g = np.array(guide, float)
    s = 1 if down else -1
    xs, ys = [], []
    for x in range(int(g[0, 0]), int(g[-1, 0]), FLOOR_STEP):
        y0 = int(round(np.interp(x, g[:, 0], g[:, 1]))) + s * step_in
        col = clay[:, x]
        if not col[y0]:
            continue
        y = y0
        while col[y + s] and abs(y - y0) < reach:
            y += s
        xs.append(x)
        ys.append(y + s * 0.5 if abs(y - y0) < reach else np.nan)
    xs, ys = np.array(xs), np.array(ys)
    ok = ~np.isnan(ys)
    ys = np.interp(xs, xs[ok], ys[ok])
    return xs, ndi.median_filter(ys, FLOOR_MED, mode="nearest")


def net_contrast(gpath, shape, t):
    """The net's faint lines' local contrast (see NET_*), over NET's bounding box (0 elsewhere): the grey blurred
    NET_BLUR px, then blurred along the lines (as suppliants_eur.py: PhotoCraft's Motion Blur at NET_ANGLES, NET_MB px,
    each px from the angle nearest the lines' direction there, the structure tensor's, smoothed over NET_TENSOR px; so a
    line's dashes join), its Maximum then Minimum over NET_R px, less it."""
    P = np.array(NET, float)
    x0, y0 = (P.min(0) - 20).astype(int)
    x1, y1 = (P.max(0) + 20).astype(int)
    pc(gpath, t / "nb.png", ("image.crop", {"x": int(x0), "y": int(y0), "width": int(x1 - x0), "height": int(y1 - y0)}),
       ("filter.blur.gaussianBlur", {"radius": NET_BLUR}))
    gl = grey(t / "nb.png")
    gy, gx = np.gradient(ndi.gaussian_filter(gl, 1.0))
    jxx, jyy, jxy = (ndi.gaussian_filter(v, NET_TENSOR) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(-(0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2)) % 180
    pick = np.rint(line / (180 / len(NET_ANGLES))).astype(int) % len(NET_ANGLES)
    o = np.zeros_like(gl)
    for i, a in enumerate(NET_ANGLES):
        pc(t / "nb.png", t / "mb.png", ("filter.blur.motionBlur", {"angle": a, "distance": NET_MB}))
        o = np.where(pick == i, grey(t / "mb.png"), o)
    Image.fromarray(o.clip(0, 255).astype(np.uint8)).save(t / "along.png")
    pc(t / "along.png", t / "nc.png", ("filter.other.maximum", {"radius": NET_R, "preserve": "squareness"}),
       ("filter.other.minimum", {"radius": NET_R, "preserve": "squareness"}))
    out = np.zeros(shape, np.float32)
    out[y0:y1, x0:x1] = grey(t / "nc.png") - grey(t / "along.png")
    return out


def marks(shape):
    """John's marks on the flat (see MARKS_*): blue strokes, blue filled shapes, purple, yellow, green."""
    H, W = shape
    ox, oy = MARKS_ORIGIN
    blue, blobs, purple, yellow, green = (np.zeros((H, W), bool) for _ in range(5))
    for files in MARKS_FILES:
        for f, m in zip(files, (blue, purple, yellow, green)):
            if f is None:
                continue
            a = np.asarray(Image.open(Path(__file__).parent / f).convert("L")) > 127
            m[oy:oy + a.shape[0], ox:ox + a.shape[1]] |= a[:H - oy, :W - ox]
    # (his filled shapes: what an opening by a disk BLOB_R px across leaves, over BLOB_MIN px^2, grown back into the
    # paint; the axe head is joined to his shaft line, so a test of the whole stroke's length could not find it)
    thick = ndi.binary_opening(blue, structure=morphology.disk(BLOB_R))
    thick = morphology.remove_small_objects(thick, max_size=BLOB_MIN)
    blobs = ndi.binary_dilation(thick, iterations=2) & blue
    return blue & ~blobs, blobs, purple, yellow, green


def stroke(m, width):
    """A mark's strokes drawn along their centre lines, `width` px wide, edges smoothed (Gaussian MARK_SMOOTH in
    PhotoCraft, cut at half)."""
    cl = centre_lines(m, spur=SPUR, min_len=MARK_LEN)
    a = ((ndi.distance_transform_edt(~cl) <= width / 2) * 255).astype(np.uint8)
    with tempfile.TemporaryDirectory() as td:
        Image.fromarray(a).save(Path(td) / "m.png")
        pc(Path(td) / "m.png", Path(td) / "ms.png", ("filter.blur.gaussianBlur", {"radius": MARK_SMOOTH}))
        return grey(Path(td) / "ms.png") >= 128


def scene(g8, rb8, sharp8, dump=None):
    """(ink, ink traced at its own size, figure, grey, washes) for the flat's grey and red less blue (uint8)."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(rb8).save(t / "rb0.png")
        pc(t / "rb0.png", t / "rb.png", ("filter.blur.gaussianBlur", {"radius": 2}),
           ("image.adjustments.threshold", {"level": CLAY}))
        Image.fromarray(g8).save(t / "g.png")
        pc(t / "g.png", t / "core.png", ("filter.blur.gaussianBlur", {"radius": 1.5}),
           ("image.adjustments.threshold", {"level": LINE_DARK}))
        pc(t / "g.png", t / "g1.png", ("filter.blur.gaussianBlur", {"radius": 1}))
        pc(t / "g.png", t / "gc.png", ("filter.blur.gaussianBlur", {"radius": 1}),
           ("image.adjustments.levels", {"inWhite": LC_CAP}))
        pc(t / "gc.png", t / "gcc.png", ("filter.other.maximum", {"radius": LC_R, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": LC_R, "preserve": "squareness"}))
        contrast = grey(t / "gcc.png") - grey(t / "gc.png")
        net_c = net_contrast(t / "g.png", g8.shape, t)
        pc(t / "g.png", t / "gmin.png", ("filter.blur.gaussianBlur", {"radius": 0.7}),
           ("filter.other.minimum", {"radius": 1, "preserve": "squareness"}))
        gmin = grey(t / "gmin.png")
        pc(t / "g.png", t / "gh.png", ("filter.blur.gaussianBlur", {"radius": HAIR_BLUR}))
        gh = grey(t / "gh.png")   # (PhotoCraft 0.2.0 wrote a PNG PIL cannot read at radius 0.7; 0.8 reads)
        g = grey(t / "g.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        g1 = grey(t / "g1.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3]) for b in bs], 0) if bs else np.zeros((H, W), bool)
    # (both rules below are set against the clay's own level round each px, LEVEL_SIGMA px: the handle views' clay is
    # darker than the front's after the tone match, about 130 against 175, and fixed levels erased the left woman's
    # raised hand)
    cl = clay.astype(np.float32)
    level = ndi.gaussian_filter(g1 * cl, LEVEL_SIGMA) / np.maximum(ndi.gaussian_filter(cl, LEVEL_SIGMA), 1e-3)
    clay &= ~(box(HANDS) & (g1 <= level - HAND_D))
    # the painter's stripe of thinned glaze along the figures' edges (grey 90-140, between the clay and the glaze): read
    # half as clay it made the edges bumpy and drew blotches on the outline (John, 2026-10-19: "still rough"). Within
    # STRIPE_W px of the clay's edge, clay STRIPE_D darker than the clay round it is not clay
    near = clay & (ndi.distance_transform_edt(clay) <= STRIPE_W)
    clay &= ~(near & (g1 <= level - STRIPE_D) & ~box(FACES))
    fx, fy = strip_cut(clay, FLOOR_LOW, FLOOR_IN, FLOOR_UP, down=False)
    cx, cy = strip_cut(clay, CEIL_HIGH, CEIL_IN, CEIL_DOWN, down=True)
    outside = (yy > np.interp(xx, fx, fy)) | (yy < np.interp(xx, cx, cy))
    unseen = ndi.binary_opening(sharp8 < SEEN_MIN * 100, structure=morphology.disk(SEEN_OPEN))
    outside |= ndi.gaussian_filter(unseen.astype(np.float32), SEEN_SMOOTH) > 0.5
    for side, pts in zip((0, 1), COLUMNS):
        if len(pts):
            P = np.array(pts, float)
            xe = np.interp(yy, P[:, 1], P[:, 0])
            outside |= (xx < xe) if side == 0 else (xx > xe)
    dark = ~clay & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, pts, WALL_W)
    fine = box(FINE)
    # (the glaze's pale flecks break the ground up at the fine opening, and its pieces fell under AUTO_GROUND and turned
    # to paint: Clytemnestra's profile was lost in them. Fill the flecks first)
    darkf = morphology.remove_small_holes(dark, max_size=FLECK_HOLE) & ~outside
    ground0 = np.where(fine, ndi.binary_opening(darkf, structure=morphology.disk(FINE_OPEN)),
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
    fig = (np.where(fine, ndi.gaussian_filter(f, FINE_SMOOTH), ndi.gaussian_filter(f, SMOOTH)) > 0.5) & ~outside
    paint = dark & fig & core
    blue, blobs, purple, yellow, green = marks(g.shape)
    fig = (fig | yellow) & ~green
    hands = box(HANDS)
    out = ndi.binary_dilation(fig, structure=morphology.disk(FINE_EDGE)) & ~fig & hands & ~outside
    fig |= out
    # (the outline: an even band centred on the figure's contour, smoothed over OUT_SMOOTH px outside FINE, so it
    # neither swells where folds and paint meet it nor follows the photo's grain; John, 2026-10-19: "the outlines of
    # many of the figures are still too rough")
    fs = np.where(fine, fig, ndi.gaussian_filter(fig.astype(np.float32), OUT_SMOOTH) > 0.5) & ~outside
    w = np.where(fine, FINE_EDGE, EDGE) / 2.0
    edge = (fs & (ndi.distance_transform_edt(fs) <= w)) | (~fs & (ndi.distance_transform_edt(~fs) <= w) & ~outside)
    edge = (edge & ~(hands & ~out)) | out
    fig = fs | edge
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
    area = fig & ~edge & ~ndi.binary_dilation(solid, iterations=3)
    faint = np.any([lw.polygon_mask(g.shape, np.array(z, float)) for z in FAINT], 0) if FAINT else np.zeros_like(fig)
    found = even_lines(contrast, core & area, area, face_box, faint)
    pale = found & face_box & ~ndi.binary_dilation(old, iterations=PALE_OFF)
    pale = morphology.remove_small_objects(pale, max_size=PALE_MIN)
    pale = ndi.binary_dilation(pale, iterations=PALE_OFF + 1, mask=found)
    lines = solid | (found & ~face_box) | pale | old
    lines &= fig & ~edge
    lines = join_breaks(lines, g1, fig & ~solid) & fig
    hug = fs & (ndi.distance_transform_edt(fs) <= EDGE_CLEAR)
    lab, n = ndi.label(lines & ~edge, structure=np.ones((3, 3)))
    if n:
        frac = ndi.mean(hug.astype(float), lab, np.arange(1, n + 1))
        lines &= ~np.isin(lab, 1 + np.nonzero(frac >= EDGE_HUG)[0])
    # (in the hands every line px that close to the contour goes, and specks under HAND_SPECK px^2: the fingers are
    # 12-20 px wide and were drawn with a second outline inside the first)
    hb = box(HANDS)
    lines &= ~(hb & hug)
    lab, _ = ndi.label(lines & hb, structure=np.ones((3, 3)))
    lines &= ~((np.bincount(lab.ravel()) < HAND_SPECK)[lab] & (lab > 0))
    netz = lw.polygon_mask(g.shape, np.array(NET, float)) & fig & ~edge
    lab, _ = ndi.label(lines & netz & ~face_box, structure=np.ones((3, 3)))
    frac = ndi.mean(core.astype(float), lab, np.arange(1, lab.max() + 1)) if lab.max() else np.zeros(0)
    lines &= ~np.isin(lab, 1 + np.nonzero(frac < NET_CORE)[0])
    # small painted dots standing alone in DOTS (the net's, the dress's), at their own shape, traced at their own size
    dz = np.any([lw.polygon_mask(g.shape, np.array(z, float)) for z in DOTS], 0) if DOTS else np.zeros_like(fig)
    sp = dz & fig & ~edge & (contrast >= DOT_LC) & ~ndi.binary_dilation(lines, iterations=DOT_OFF)
    lab, _ = ndi.label(sp, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    spots = ((sz >= DOT_MIN) & (sz <= DOT_MAX))[lab] & sp
    old |= spots
    lines |= spots
    # the heads (see HEADS)
    heads = box(HEADS)
    hi, lo = ndi.maximum_filter(gh, 2 * HEAD_HI + 1), ndi.minimum_filter(gh, 2 * HEAD_LO + 1)
    hm = (gh < (hi + lo) / 2) & (hi - lo > HEAD_SPAN)
    hm = morphology.remove_small_objects(hm, max_size=HEAD_SPECK)
    hs = ndi.binary_closing(gh < HEAD_SOLID, iterations=2) & (gh < HEAD_SOLID_MAX)
    hm = morphology.remove_small_holes(hm | hs, max_size=HEAD_HOLE) & heads & fig & ~edge
    lines = (lines & ~heads) | hm
    old = (old & ~heads) | hm
    # Agamemnon's head (see AGAM_*)
    pm = lambda P: lw.polygon_mask(g.shape, np.array(P, float))
    head = (pm(AGAM_CURLS) | pm(AGAM_BEARD) | pm(AGAM_FACE)) & fig & ~edge
    lines &= ~head
    old &= ~head
    hi, lo = ndi.maximum_filter(gh, 2 * FACE_HI + 1), ndi.minimum_filter(gh, 2 * FACE_LO + 1)
    fl = (gh < (hi + lo) / 2) & (hi - lo > FACE_SPAN) & pm(AGAM_FACE) & fig & ~edge
    fl = ndi.distance_transform_edt(~centre_lines(fl, spur=5, min_len=6)) <= FACE_W / 2
    lines |= fl & fig
    old |= fl & fig
    hair = ((gh < CURL_G) & pm(AGAM_CURLS) | (gh < BEARD_G) & pm(AGAM_BEARD)) & head & ~ndi.binary_dilation(fl, iterations=1)
    hair = morphology.remove_small_objects(hair, max_size=HAIR_SPECK)
    ink = lines | edge
    holes = ndi.binary_fill_holes(ink) & ~ink & ~face_box   # (not in the heads: the eyes' whites, the clay between curls)
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    faces = np.isin(lab, np.unique(lab[(face_box | spots) & ink])) & (sz < FACE_MAX)[lab] & (lab > 0)
    faces |= ink & (face_box | heads) & ~edge
    # the net's faint lines, as a tone
    from skimage.filters import apply_hysteresis_threshold
    nl = apply_hysteresis_threshold(net_c, NET_LOW, NET_HIGH) & netz & ~ndi.binary_dilation(ink, iterations=NET_OFF)
    ncl = centre_lines(nl, spur=SPUR, min_len=NET_LEN)
    # (the body's contours seen through the robe are found with the net's lines but are darker: ink)
    dk = ncl & (gmin < NET_INK_G) & ~head   # (not in his head: the curls are dark too)
    lab, _ = ndi.label(dk, structure=np.ones((3, 3)))
    dk &= (np.bincount(lab.ravel()) >= NET_INK_LEN)[lab]
    thru = (ndi.distance_transform_edt(~dk) <= NET_INK_W / 2) & fig
    ink |= thru
    ncl &= ~ndi.binary_dilation(dk, iterations=2)
    net = (ndi.distance_transform_edt(~ncl) <= NET_W / 2).astype(np.float32)
    net = (ndi.gaussian_filter(net, NET_SMOOTH) > 0.5) & fig & ~ink & ~hair
    # John's marks (see MARKS_*)
    # (in the hands his round 2 strokes run 4-6 px inside my outline, which lies on the painted edge: the fingers came
    # out with two outlines. There his strokes within HAND_NEAR px of the outline go; the outline stays)
    blue = blue & ~(box(HANDS) & (ndi.distance_transform_edt(~edge) <= HAND_NEAR))
    johns = stroke(blue, MARK_W) | (ndi.gaussian_filter(blobs.astype(np.float32), MARK_SMOOTH) > 0.5)
    inner = yellow & ~edge
    ink &= ~inner
    faces &= ~inner
    ink &= ~ndi.binary_dilation(johns, iterations=MARK_GAP)
    faces &= ~ndi.binary_dilation(johns, iterations=MARK_GAP)
    faces |= johns
    net = (net | stroke(purple, NET_W)) & ~ink & ~faces & ~hair
    if dump:
        np.savez_compressed(dump, ink=ink, faces=faces, fig=fig, ground=ground, clay=clay, core=core, solid=solid,
                            net=net, hair=hair)
    return ink & ~faces, faces, fig, g, [[(hair & ~ink, HAIR_OPACITY)], [(net, NET_OPACITY)]]


def main(flat_prefix, qa=None, dump=None):
    """The drawing from a saved flat (--flat writes <prefix>-g.png, -rb.png, -src.png)."""
    g8 = np.asarray(Image.open(f"{flat_prefix}-g.png"))
    rb8 = np.asarray(Image.open(f"{flat_prefix}-rb.png"))
    sharp8 = np.asarray(Image.open(f"{flat_prefix}-sharp.png"))
    ink, faces, fig, g, wash = scene(g8, rb8, sharp8, dump)
    ink |= (ndi.distance_transform_edt(~morphology.skeletonize(ink)) <= NECK / 2) & fig
    info = lw.trace_svg(ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT if WEIGHT else "own", dots=faces,
                        extent=faces,
                        title="Aegisthus, sword in hand, seizes Agamemnon, caught in a robe like a net; Clytemnestra "
                              "behind him with an axe, women round them",
                        desc="Line drawing after the Attic red-figure calyx-krater Boston, Museum of Fine Arts "
                             "63.1246, side A; traced from the museum's photographs, taken off the vase's curve.")
    for steps in wash:
        add_tone(OUT, [(m & ~ink & ~faces, o) for m, o in steps], info["box"])
    print(OUT, info)
    if qa:
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    if "--flat" in sys.argv:   # front left right out-prefix --flat: the flat's grey, red less blue and source PNGs
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        for im, tag in zip(flat_image(dict(zip(NAMES, a[:3]))), ("g", "rb", "src", "sharp")):
            Image.fromarray(im).save(f"{a[3]}-{tag}.png")
    elif "--from-flat" in sys.argv:   # out-prefix [qa.png] --from-flat [--dump]
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        main(a[0], a[1] if len(a) > 1 else None, dump=os.environ.get("AGAMEMNON_DUMP") if "--dump" in sys.argv else None)
    elif "--refit" in sys.argv:
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        fit_model(dict(zip(NAMES, a[:3])), *([tuple(float(x) for x in a[3].split(","))] if len(a) > 3 else []))
