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
PROFILE_PX = [-650, -400, -150, 100, 350, 600, 850, 1100, 1350, 1600, 1850, 2050]   # knots, in front px above the band
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


def measure(photos):
    """The fit's data from the photos: {name: (grey, outline, band)} and the matches front -> each handle view."""
    import cv2
    data = {}
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
    sift = cv2.SIFT_create(contrastThreshold=0.02)

    def feats(n, k):
        g = cv2.resize(data[n][0].clip(0, 255).astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        m = np.zeros_like(g)
        b0 = int(np.median(data[n][2][:, 1]) * k)
        m[int(0.1 * g.shape[0]):b0, :] = 255   # the picture zone, above the band
        kp, d = sift.detectAndCompute(g, m)
        return np.array([p.pt for p in kp]) / k, d

    kf, df = feats("front", 0.4)
    matches = {}
    for n in ("left", "right"):
        kn, dn = feats(n, 1.0)
        good = [a for a, b in cv2.BFMatcher(cv2.NORM_L2).knnMatch(df, dn, k=2) if a.distance < 0.8 * b.distance]
        a, b = np.float32([kf[x.queryIdx] for x in good]), np.float32([kn[x.trainIdx] for x in good])
        (ua, ra), (ub, rb) = AXIS["front"], AXIS[n]
        d = np.degrees(np.arcsin(np.clip((b[:, 0] - ub) / rb, -1, 1)) - np.arcsin(np.clip((a[:, 0] - ua) / ra, -1, 1)))
        print(n, "matches", len(good), "turn histogram", np.histogram(d, bins=12, range=(-180, 180))[0])
        matches[n] = np.hstack([a, b])[np.abs(d - TURN0[n]) < 20]
    return data, matches


def fit_model(photos, dists=(8.0, 12.0, 18.0, 27.0, 40.0)):
    """Refit MODEL from the three photos and print it, for each camera distance in `dists` (see vase_unroll.fit)."""
    data, matches = measure(photos)
    for n in NAMES:
        print(n, "outline", len(data[n][1]), "band", len(data[n][2]), "matches", len(matches.get(n, [])))
    for dist in dists:
        r0 = D0 / dist   # the picture's radius in world units, at this distance
        knots = np.array(PROFILE_PX, float) * r0 / AXIS["front"][1]
        views, x0 = {}, []
        for n in NAMES:
            L, sil, band = data[n]
            f = AXIS[n][1] * dist
            views[n] = dict(size=L.shape[::-1], f=f, sil=[tuple(r) for r in sil], band=band)
            x0 += [D0, 0.5 * r0, 0.0, 0.0, 0.0, f, 0.0, 0.0]   # a start: the camera level with the picture
        s = data["front"][1]
        k = r0 / AXIS["front"][1]   # world units per front px at the picture
        bv = np.median(data["front"][2][:, 1])
        left, right = s[s[:, 0] == 0], s[s[:, 0] == 1]
        hw = (np.interp(left[:, 2], right[:, 2], right[:, 1]) - left[:, 1]) / 2
        o = np.argsort(bv - left[:, 2])
        x0 += list(np.interp(knots, (bv - left[o, 2][::1]) * k, hw[o] * k)) + [0.0, 0.0]
        x0 += [np.radians(TURN0["left"]), np.radians(TURN0["right"])]
        cams, R, _, turns, report, _ = vu.fit(views, knots, matches=matches, d0=D0, rounds=3, outlier=30,
                                              nfev=1500, x_start=np.array(x0))
        print(f"DIST {dist}")
        print("\n".join(report))
        print("CAMERAS = {")
        for n, c in cams.items():
            print(f'    "{n}": dict(' + ", ".join(f"{q}={c[q]:.6g}" for q in ("D", "H", "b", "p", "g", "f", "cx", "cy")) + "),")
        print("}")
        print("PROFILE_R =", [round(float(R(y)), 2) for y in knots])
        print("TURNS =", {n: round(float(np.degrees(t)), 3) for n, t in turns.items()})


if __name__ == "__main__":
    if "--refit" in sys.argv:
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        fit_model(dict(zip(NAMES, a[:3])), *([tuple(float(x) for x in a[3].split(","))] if len(a) > 3 else []))
