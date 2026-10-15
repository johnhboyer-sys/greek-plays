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
# The focal lengths: each photo's half-width at the picture times DIST, the camera's distance in picture radii, tried
# at 8, 12, 18, 27, 40 and 60: the fit improves up to 40 and little beyond (cost 12619, 11451, 10349, 9738, 9577,
# 9505; the matches on the flat best at 40: 1.6 px to the left view, 2.9 to the right), so DIST is 40. (the fit: band
# median 2.8 px in the front, 1.8 and 4.1 in the handle views; outlines 4.6, 2.8 and 4.5 px; matches 95 and 110)
DIST = 40.0
CAMERAS = {
    "front": dict(D=4000, H=60.4769, b=-0.0074265, p=-0.000816661, g=-0.0281714, f=48320, cx=1926.5, cy=2048),
    "left": dict(D=3943.25, H=351.148, b=0.0755643, p=0.000100378, g=-0.0114748, f=19480, cx=757, cy=800),
    "right": dict(D=3991.99, H=-9.92795, b=-0.0170506, p=3.56495e-05, g=-0.00947308, f=19240, cx=752.5, cy=800),
}
PROFILE_PX = [-650, -400, -150, 100, 350, 600, 850, 1100, 1350, 1600, 1850, 2050]   # knots, in front px above the band
PROFILE_R = [43.36, 71.27, 87.5, 84.82, 85.85, 90.75, 95.47, 99.24, 103.58, 109.39, 116.67, 127.65]
TURNS = {"left": 97.737, "right": -102.122}   # degrees each handle view is turned from the front
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
# black and white: their grey is matched to the front photo's grey (and to its red less blue, for the clay) by
# percentiles (1 to 99) over that strip, blurred SEAM_BLUR px, where both see the vase at least FM_SHARP sharp (a
# straight line fitted there came out at a slope of 0.08: the strip's px do not pair up closely enough).
SEAM_W, SEAM_BLUR, CHUNK = 260, 2.0, 256
# In each handle view the handle's loop stands in front of the picture's lowest strip by the column: the loop
# (polygon, photo px) less its opening (through which the vase shows) counts as unseen, so the front photo is used
# there where it sees the vase
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
    """The three photos laid onto the flat frame and joined: (grey, red less blue, source), H x W uint8 each (source
    0 front, 1 left, 2 right)."""
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
                loop = lw.polygon_mask(hw, np.array(HANDLES[n][0], float)) & ~lw.polygon_mask(hw, np.array(HANDLES[n][1], float))
                inside &= ~ndi.map_coordinates(loop, [uv[..., 1], uv[..., 0]], order=0, cval=0).astype(bool)
            sh[n][rows] = np.where(inside, sharp, 0)
            g[n][rows] = ndi.map_coordinates(ims[0], [uv[..., 1], uv[..., 0]], order=3, cval=0)
            if n == "front":
                rb[rows] = ndi.map_coordinates(ims[1], [uv[..., 1], uv[..., 0]], order=3, cval=0)
    src = np.zeros((H, W), np.uint8)
    out_g, out_rb = g["front"].copy(), rb.copy()
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
        q = np.arange(1, 100)
        qs = np.percentile(gs[both], q)
        tone_g, tone_rb = (lambda x, a=np.percentile(gf[both], q): np.interp(x, qs, a),
                           lambda x, a=np.percentile(rf[both], q): np.interp(x, qs, a))
        print(f"{n}: seam near flat x {xb}; its grey {qs[[4, 49, 94]].round()} -> front grey "
              f"{tone_g(qs[[4, 49, 94]]).round()}, red less blue {tone_rb(qs[[4, 49, 94]]).round()} (over {both.sum()} px)")
        cost = ((gf + tone_g(gs)) / 2) ** 2
        cost = np.where(both, cost, 1e6)
        path = lo + seam(cost)
        side = xx[None, :] <= path[:, None] if n == "left" else xx[None, :] >= path[:, None]
        side &= sh[n] > 0
        out_g = np.where(side, tone_g(g[n]), out_g)
        out_rb = np.where(side, tone_rb(g[n]), out_rb)
        src[side] = k
    return out_g.clip(0, 255).round().astype(np.uint8), out_rb.clip(0, 255).round().astype(np.uint8), src


# ---------------------------------------------------------------- the scene

CLAY = 70                     # clay: red less blue above this (blurred 2 px); glaze under it
LINE_DARK = 85                # painted lines: grey darker than this (blurred 1.5 px)
# Ground: the glaze, its painted lines (up to OPEN*2 px wide) opened away; the large areas, inside the scene too.
# Smaller glaze areas inside the figures are paint.
OPEN, AUTO_GROUND = 14, 40000
OPEN_PTS = []                 # smaller areas of ground the figures close in (flat px, a point in each)
PAINT_PTS = []                # big dark areas that are paint, not ground (flat px, a point in each)
WALLS = []                    # solid paint walled off where it meets the ground (flat px polylines, WALL_W wide)
WALL_W = 8
SMOOTH = 3.0
EDGE = 9                      # the outline, flat px wide
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
WEIGHT = None                 # the line weight: pinned after pass 1
NECK = 5                      # every line thickened to at least NECK flat px along its centre before tracing
SEEDS = []                    # flat px, a point on each figure's clay
# The floor: the meander band's upper clay strip, which the figures stand on, is cut away. Per column (every
# FLOOR_STEP px), from FLOOR_IN px above a guide near the strip's lower edge (FLOOR_LOW) up through the strip's clay to
# the first paint or glaze above it, at most FLOOR_UP px; smoothed (a running median over FLOOR_MED). Below it is band.
# The ceiling likewise: from CEIL_IN px below a guide near the upper edge of the clay strip under the checkers
# (CEIL_HIGH) down through it to the first paint or glaze, at most CEIL_DOWN px (a hand or head touching the strip).
FLOOR_STEP, FLOOR_MED, FLOOR_IN, FLOOR_UP = 10, 5, 6, 40
FLOOR_LOW = []
CEIL_IN, CEIL_DOWN = 6, 40
CEIL_HIGH = []
# The columns under the handles are left out (John, 2026-10-15: "column to column"): everything beyond COLUMNS
# (polylines along each column's inner edge, flat px; left, right) goes
COLUMNS = ([], [])
# Faces are traced at their own size (as mika.py): boxes, flat px; in them marks of FACE_SPECK px^2 or more stand
FACES = []
FACE_SPECK = 12
FACE_DOT, FACE_DOT_MAX = 40, 400
FACE_LC = (14, 28)
PALE_OFF, PALE_MIN = 4, 30
JOIN_D, JOIN_COS, JOIN_G, JOIN_BACK = 30, 0.75, 120, 12
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


def scene(g8, rb8, dump=None):
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
        g = grey(t / "g.png")
        clay = grey(t / "rb.png") >= 128
        core = grey(t / "core.png") < 128
        g1 = grey(t / "g1.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    box = lambda bs: np.any([(xx >= b[0]) & (yy >= b[1]) & (xx < b[2]) & (yy < b[3]) for b in bs], 0) if bs else np.zeros((H, W), bool)
    fx, fy = strip_cut(clay, FLOOR_LOW, FLOOR_IN, FLOOR_UP, down=False)
    cx, cy = strip_cut(clay, CEIL_HIGH, CEIL_IN, CEIL_DOWN, down=True)
    outside = (yy > np.interp(xx, fx, fy)) | (yy < np.interp(xx, cx, cy))
    for side, pts in zip((0, 1), COLUMNS):
        if len(pts):
            P = np.array(pts, float)
            xe = np.interp(yy, P[:, 1], P[:, 0])
            outside |= (xx < xe) if side == 0 else (xx > xe)
    dark = ~clay & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, pts, WALL_W)
    ground0 = ndi.binary_opening(dark, structure=morphology.disk(OPEN))
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
    fig = (ndi.gaussian_filter(fig.astype(np.float32), SMOOTH) > 0.5) & ~outside
    paint = dark & fig & core
    to_edge = ndi.distance_transform_edt(fig)
    edge = fig & (to_edge <= EDGE)
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
    found = even_lines(contrast, core & area, area, face_box)
    pale = found & face_box & ~ndi.binary_dilation(old, iterations=PALE_OFF)
    pale = morphology.remove_small_objects(pale, max_size=PALE_MIN)
    pale = ndi.binary_dilation(pale, iterations=PALE_OFF + 1, mask=found)
    lines = solid | (found & ~face_box) | pale | old
    lines &= fig & ~edge
    lines = join_breaks(lines, g1, fig & ~solid) & fig
    ink = lines | edge
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, _ = ndi.label(holes)
    ink |= (np.bincount(lab.ravel()) < FLECK)[lab] & holes
    lab, _ = ndi.label(ink, structure=np.ones((3, 3)))
    sz = np.bincount(lab.ravel())
    faces = np.isin(lab, np.unique(lab[face_box & ink])) & (sz < FACE_MAX)[lab] & (lab > 0)
    if dump:
        np.savez_compressed(dump, ink=ink, faces=faces, fig=fig, ground=ground, clay=clay, core=core, solid=solid)
    return ink & ~faces, faces, fig, g, []


def main(flat_prefix, qa=None, dump=None):
    """The drawing from a saved flat (--flat writes <prefix>-g.png, -rb.png, -src.png)."""
    g8 = np.asarray(Image.open(f"{flat_prefix}-g.png"))
    rb8 = np.asarray(Image.open(f"{flat_prefix}-rb.png"))
    ink, faces, fig, g, wash = scene(g8, rb8, dump)
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
        for im, tag in zip(flat_image(dict(zip(NAMES, a[:3]))), ("g", "rb", "src")):
            Image.fromarray(im).save(f"{a[3]}-{tag}.png")
    elif "--from-flat" in sys.argv:   # out-prefix [qa.png] --from-flat [--dump]
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        main(a[0], a[1] if len(a) > 1 else None, dump=os.environ.get("AGAMEMNON_DUMP") if "--dump" in sys.argv else None)
    elif "--refit" in sys.argv:
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        fit_model(dict(zip(NAMES, a[:3])), *([tuple(float(x) for x in a[3].split(","))] if len(a) > 3 else []))
