"""Unroll a painting off a vase: fit the vase and the cameras of photos of it, then
map a photo onto the flat, where s = R(y) * theta runs around the vase and t is the
arc length up its profile.

A photo foreshortens a vase painting twice over: toward the sides, where the
surface turns away, and up and down wherever the profile slopes (the shoulder
curving in to the neck, the lower body in to the foot), the more so the closer
and higher the camera. On the drawings this shows as a squashed head, short
legs, a bent spear and a sagging ground line.

The model: the vase's axis is the world y axis (y up), with y = 0 at the lower
edge of a painted band (a circle: bands are painted on the wheel). Its profile
R(y) is a cubic spline through knots, kept smooth. Each camera is a pinhole at
(0, H, D), so that theta = 0 faces it; it looks down by `b`, with yaw `p` and
roll `g`, focal length `f` (px) and its principal point at the image centre.
Give `f` when the photos' EXIF records it (focal length over pixel pitch; a
crop keeps it): fitted, it trades against the camera's distance, and the
perspective comes out wrong.
The data: the silhouette's two edges in each row (rows clear of handles and
foot), the band's lower edge, and optionally a ring seen in any of the photos
(a circle of unknown height and radius on which the profile ends, such as the
base of the neck: it pins down the top of the shoulder, which the handles hide
in a photo facing the painting), and points of the painting matched between the
first photo and the others: each must land on the same spot of the vase, once
each photo's turn about the axis (phi) is fitted. The silhouettes alone leave
the shape under the painting loose; the matches hold it. The scale is fixed by
the first camera's D.

Dev-only tool for docs/redesign/drawings; needs numpy, scipy, pillow.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

# ---------------------------------------------------------------- measuring a photo


def silhouette(rgb: np.ndarray, v0: int, v1: int, step: int = 3) -> np.ndarray:
    """(v, u_left, u_right) for rows v0..v1: where the light, grey background
    touching the image's sides meets the vase, to a fraction of a pixel."""
    H, W = rgb.shape[:2]
    L = rgb.mean(2)
    bg = ndi.binary_opening((L > 140) & (rgb.max(2) - rgb.min(2) < 45), iterations=2)
    lab, _ = ndi.label(bg)
    bg = np.isin(lab, list(set(np.unique(np.r_[lab[:, 0], lab[:, -1]])) - {0}))
    Ls = ndi.gaussian_filter(L, 1.0)
    out = []
    for v in range(v0, v1, step):
        r = bg[v]
        if r.all():
            continue
        row = [float(v)]
        for side in (0, 1):
            x = int(np.argmax(~r)) if side == 0 else int(W - 1 - np.argmax(~r[::-1]))
            s = 1 if side == 0 else -1  # inward
            if x < 25 or x > W - 26:
                row.append(np.nan)
                continue
            line = Ls[v]
            mid = (np.median(line[x - 20 * s:x - 8 * s:s]) + np.median(line[x + 8 * s:x + 20 * s:s])) / 2
            xs = np.arange(x - 10, x + 11)
            k = np.nonzero(np.diff(np.sign(line[xs] - mid)))[0]
            row.append(float(xs[k[0]] + (mid - line[xs[k[0]]]) / (line[xs[k[0]] + 1] - line[xs[k[0]]]))
                       if len(k) else np.nan)
        out.append(row)
    return np.array(out)


def band_edge(rgb: np.ndarray, box: tuple, clay_rb: float = 90) -> np.ndarray:
    """(u, v) along the lower edge of the widest clay band inside box (u0, u1, v0, v1)."""
    u0, u1, v0, v1 = box
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.0)
    lab, n = ndi.label(RB[v0:v1, u0:u1] > clay_rb)
    spans = ndi.find_objects(lab)
    band = lab == 1 + max(range(n), key=lambda i: spans[i][1].stop - spans[i][1].start)
    pts = []
    for u in range(0, u1 - u0, 6):
        col = np.nonzero(band[:, u])[0]
        if len(col) < 10:
            continue
        vb = v0 + col.max()
        prof = RB[vb - 8:vb + 9, u0 + u]
        mid = (np.median(RB[vb - 14:vb - 6, u0 + u]) + np.median(RB[vb + 6:vb + 14, u0 + u])) / 2
        k = np.nonzero(np.diff(np.sign(prof - mid)))[0]
        if len(k):
            k = k[-1]
            pts.append((u0 + u, vb - 8 + k + (mid - prof[k]) / (prof[k + 1] - prof[k])))
    return np.array(pts)


def band_line(rgb: np.ndarray, rough, half: int = 50, step: int = 6, clay_rb: float = 120,
              widths: tuple = (20, 75)) -> np.ndarray:
    """(u, v) along the centre of a thin painted clay line (a frieze's border,
    painted on the wheel, so a circle on the vase): per column, the clay run
    `widths` px thick nearest the rough polyline (u, v points), kept where
    the points lie on one smooth curve. Give the rough line where the line
    shows; figures standing on it would be taken for it."""
    rough = np.asarray(rough, float)
    RB = ndi.gaussian_filter(rgb[..., 0] - rgb[..., 2], 1.0)
    out = []
    for u in range(int(rough[:, 0].min()), int(rough[:, 0].max()), step):
        vg = np.interp(u, rough[:, 0], rough[:, 1])
        v0 = max(int(vg) - half, 0)
        k = np.nonzero(RB[v0:v0 + 2 * half, u] > clay_rb)[0]
        runs = [r for r in np.split(k, np.nonzero(np.diff(k) > 1)[0] + 1) if widths[0] <= len(r) <= widths[1]] if len(k) else []
        if runs:
            r = min(runs, key=lambda r: abs(v0 + (r[0] + r[-1]) / 2 - vg))
            out.append((u, v0 + (r[0] + r[-1]) / 2))
    out = np.array(out)
    res = out[:, 1] - np.polyval(np.polyfit(out[:, 0], out[:, 1], 4), out[:, 0])
    return out[np.abs(res) < 3 * np.median(np.abs(res)) + 3]


def ring_edge(gray: np.ndarray, uc: float, half: float, v_side: float, sag: float) -> np.ndarray:
    """(u, v) along a ring's lower bright edge (the neck's base), searched within
    25 px of a rough ellipse (centre uc, half-width half, sides at v_side, front
    sag px lower), keeping points on one smooth curve."""
    L = ndi.gaussian_filter(gray.astype(np.float32), 1.5)
    pts = []
    for u in range(int(uc - half) + 8, int(uc + half) - 8, 6):
        c = (u - uc) / half
        v = int(v_side + sag * np.sqrt(1 - c * c))
        col = ndi.gaussian_filter1d(L[v - 25:v + 26, u], 1.0)
        peaks = [i for i in range(2, len(col) - 2) if col[i] == col[i - 2:i + 3].max() and col[i] > np.percentile(col, 70)]
        if peaks:
            pts.append((u, v - 25 + max(peaks)))
    pts = np.array(pts, float)
    r = pts[:, 1] - np.polyval(np.polyfit(pts[:, 0], pts[:, 1], 4), pts[:, 0])
    return pts[np.abs(r) < 3 * np.median(np.abs(r)) + 2]

# ---------------------------------------------------------------- the model


def axes(c: dict):
    """The camera's right, up and forward unit vectors in the world."""
    b, p, g = c["b"], c["p"], c["g"]
    fw = np.array([np.sin(p) * np.cos(b), -np.sin(b), -np.cos(p) * np.cos(b)])
    rt = np.array([np.cos(p), 0.0, np.sin(p)])
    up = np.cross(rt, fw)
    up = up if up[1] > 0 else -up
    return np.cos(g) * rt + np.sin(g) * up, -np.sin(g) * rt + np.cos(g) * up, fw


def project(c: dict, P: np.ndarray) -> np.ndarray:
    """World points (..., 3) -> image (u, v)."""
    rt, up, fw = axes(c)
    d = P - np.array([0.0, c["H"], c["D"]])
    X, Y, Z = d @ rt, d @ up, d @ fw
    return np.stack([c["cx"] + c["f"] * X / Z, c["cy"] - c["f"] * Y / Z], -1)


def surface(R, y, theta) -> np.ndarray:
    r = R(y)
    return np.stack([r * np.sin(theta), y * np.ones_like(theta), r * np.cos(theta)], -1)


def contour(c: dict, R, yg: np.ndarray):
    """The silhouette's left and right edges as image polylines: on each circle,
    the points whose surface normal is at right angles to the line of sight,
    cos(theta) = (R - R'(y - H)) / D."""
    r, dr = R(yg), R(yg, 1)
    ct = (r - dr * (yg - c["H"])) / c["D"]
    ok = np.abs(ct) < 0.999
    th = np.arccos(np.clip(ct, -0.999, 0.999))
    P = np.stack([r * np.sin(th), yg, r * np.cos(th)], -1)
    return project(c, P * np.array([-1, 1, 1]))[ok], project(c, P)[ok]


def _poly_dist(pts: np.ndarray, line: np.ndarray) -> np.ndarray:
    _, i = cKDTree(line).query(pts)
    best = np.full(len(pts), np.inf)
    for j in (i - 1, i):
        j = np.clip(j, 0, len(line) - 2)
        a, ab = line[j], line[j + 1] - line[j]
        t = np.clip(np.einsum("ij,ij->i", pts - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-9), 0, 1)
        best = np.minimum(best, np.hypot(*(pts - (a + t[:, None] * ab)).T))
    return best


def fit(views: dict, knots: np.ndarray, ring: dict | None = None, matches: dict | None = None,
        f_px: float | None = None, d0: float = 11000.0, smooth: float = 6.0, rounds: int = 2,
        outlier: float = 25.0, h0: float = 0.4, nfev: int = 300, x_start: np.ndarray | None = None):
    """Fit the profile and one camera per view. views: {name: dict(size=(W, H),
    sil=[(side, u, v), ...] (side 0 left, 1 right), band=[(u, v), ...])}; the
    first view's D is fixed at d0. A view's dict may also give its focal length
    `f` (px) and `crop: True` for a photo cropped from its frame, whose principal
    point is then fitted too. ring: {view name: [(u, v), ...]} or None; the
    profile is held to meet the ring (R at the ring's height = its radius).
    matches: {view name: array of (u, v) in the first view, (u, v) in that view}.
    Each round drops points more than `outlier` px from the model and refits.
    Returns (cams, R, (ring y, ring radius) or None, {view: phi}, report lines, x)."""
    names = list(views)
    NP = 8  # per camera: D, H, pitch, yaw, roll, f, principal point offset (x, y)
    yg = np.arange(knots[0], knots[-1] + 1, 2.0)
    th = np.linspace(-1.55, 1.55, 1200)
    obs = {n: dict(sil=np.asarray(v["sil"], float).reshape(-1, 3), band=np.asarray(v["band"], float).reshape(-1, 2))
           for n, v in views.items()}
    ringpts = None if ring is None else {n: np.asarray(v, float) for n, v in ring.items()}
    mt = {n: np.asarray(v, float) for n, v in (matches or {}).items()}
    ref = names[0]

    def unpack(x):
        cams = {}
        for i, n in enumerate(names):
            D, H, b, p, g, f, dcx, dcy = x[NP * i:NP * i + NP]
            W, Hh = views[n]["size"]
            crop = views[n].get("crop", False)
            cams[n] = dict(D=d0 if i == 0 else D, H=H, b=b, p=p, g=g, f=views[n].get("f") or f_px or f,
                           cx=W / 2 + (dcx if crop else 0.0), cy=Hh / 2 + (dcy if crop else 0.0))
        o = NP * len(names)
        phis = dict(zip(mt, x[o + len(knots) + 2:]))
        return cams, CubicSpline(knots, x[o:o + len(knots)]), x[o + len(knots):o + len(knots) + 2], phis

    def resid(x, detail=False):
        cams, R, (yn, rn), phis = unpack(x)
        out, parts = [], {}
        for n in names:
            c = cams[n]
            left, right = contour(c, R, yg)
            s = obs[n]["sil"]  # empty for a close view of the painting
            rs = np.full(len(s), 1e3)
            for side, line in ((0, left), (1, right)):
                m = s[:, 0] == side
                if m.any() and len(line) > 2:
                    rs[m] = _poly_dist(s[m, 1:3], line)
            rb = _poly_dist(obs[n]["band"], project(c, surface(R, 0.0, th))) if len(obs[n]["band"]) else np.zeros(0)
            out += [rs, 1.5 * rb]
            parts[n] = (rs, rb)
        if ringpts is not None:
            P = np.stack([rn * np.sin(th), np.full_like(th, yn), rn * np.cos(th)], -1)
            parts["ring"] = np.concatenate([_poly_dist(pts, project(cams[n], P)) for n, pts in ringpts.items()])
            out += [1.5 * parts["ring"], [3.0 * (float(R(yn)) - rn)]]
        for n, m in mt.items():  # matched points: from the first view onto the vase, then into view n
            ty = photo_to_surface(cams[ref], R, m[:, :2], (knots[0], knots[-1]), steps=60)
            d = project(cams[n], surface(R, ty[:, 1], ty[:, 0] + phis[n])) - m[:, 2:]
            parts["match " + n] = np.hypot(*d.T)
            out += [d[:, 0], d[:, 1]]
        o = NP * len(names)
        out.append(smooth * np.diff(x[o:o + len(knots)], 2))
        return (np.concatenate(out), parts) if detail else np.concatenate(out)

    # a start: every camera alike, the profile from the first view's silhouette
    if x_start is not None:
        x0 = np.array(x_start, float)
    else:
        x0 = []
        for n in names:
            x0 += [d0, h0 * d0, np.radians(16.0), 0.0, 0.0, f_px or d0, 0.0, 0.0]
        s = np.asarray(views[names[0]]["sil"], float)
        band_v = np.median(np.asarray(views[names[0]]["band"])[:, 1])
        half = {}
        for side, u, v in s:
            half.setdefault(round(v), []).append(u)
        rows = sorted(v for v, us in half.items() if len(us) == 2)
        hv = np.array([abs(half[v][1] - half[v][0]) / 2 for v in rows])
        k = d0 / (f_px + hv.max()) if f_px else 1.0  # world units per px at the vase, roughly
        yy, hv = k * (band_v - np.array(rows)) / 0.96, k * hv
        Rk = np.interp(knots, yy[::-1], hv[::-1])
        x0 = np.array(x0 + list(Rk) + ([knots[-1] - 100.0, 0.5 * Rk.max()] if ring else [0.0, 0.0]) + [0.0] * len(mt))
    lo, hi = np.full(len(x0), -np.inf), np.full(len(x0), np.inf)
    for i in range(len(names)):
        lo[NP * i], hi[NP * i], lo[NP * i + 5], hi[NP * i + 5] = 0.1 * d0, 6 * d0, 0.2 * d0, 8 * d0
        lo[NP * i + 6:NP * i + 8], hi[NP * i + 6:NP * i + 8] = -3000.0, 3000.0
    report = []
    for k in range(rounds):
        res = least_squares(resid, x0, bounds=(lo, hi), loss="soft_l1", f_scale=3.0, max_nfev=nfev, x_scale="jac")
        _, parts = resid(res.x, detail=True)
        cams, R, ringyr, phis = unpack(res.x)
        report.append(f"round {k}: cost {res.cost:.0f}, {res.nfev} evaluations, {res.message}")
        for n in names:
            c, (rs, rb) = cams[n], parts[n]
            if not len(rs) and not len(rb):
                report.append(f"  {n}: D {c['D']:.0f} H {c['H']:.0f} pitch {np.degrees(c['b']):.2f} f {c['f']:.0f} (matches only)")
                continue
            band = f"; band median {np.median(rb):.1f}, 90% {np.percentile(rb, 90):.1f}" if len(rb) else ""
            sil = f"silhouette median {np.median(rs):.1f} px, 90% {np.percentile(rs, 90):.1f}" if len(rs) else "no silhouette"
            report.append(f"  {n}: D {c['D']:.0f} H {c['H']:.0f} pitch {np.degrees(c['b']):.2f} yaw {np.degrees(c['p']):.2f} "
                          f"roll {np.degrees(c['g']):.2f} f {c['f']:.0f} | {sil}{band}")
            obs[n]["sil"], obs[n]["band"] = obs[n]["sil"][rs < outlier], obs[n]["band"][rb < outlier]
        if ringpts is not None:
            report.append(f"  ring at y {ringyr[0]:.0f}, radius {ringyr[1]:.0f}: median {np.median(parts['ring']):.1f} px")
        for n in mt:
            e = parts["match " + n]
            report.append(f"  matches {ref}->{n}: turn {np.degrees(phis[n]):.2f} deg, median {np.median(e):.1f} px, "
                          f"90% {np.percentile(e, 90):.1f} (n {len(e)})")
            mt[n] = mt[n][e < outlier]
        x0 = res.x
    return cams, R, (tuple(ringyr) if ring else None), phis, report, res.x

# ---------------------------------------------------------------- the flat


def arc_table(R, y0: float, y1: float, step: float = 0.5):
    """(y, t): t is the arc length up the profile from y = 0."""
    y = np.arange(y0, y1 + step, step)
    t = np.concatenate([[0.0], np.cumsum(np.sqrt(1 + R(y[:-1] + step / 2, 1) ** 2) * step)])
    return y, t - np.interp(0.0, y, t)


def flat_to_photo(c: dict, R, table, s: np.ndarray, t: np.ndarray, theta0: float = 0.0) -> np.ndarray:
    """Flat (s, t) -> image (u, v) of camera c; theta0 is the flat's centre
    line, as an angle in c's frame."""
    y = np.interp(t, table[1], table[0])
    r = R(y)
    th = theta0 + s / r
    return project(c, np.stack([r * np.sin(th), y, r * np.cos(th)], -1))


def photo_to_surface(c: dict, R, uv: np.ndarray, y_range: tuple, steps: int = 400) -> np.ndarray:
    """Image points -> (theta, y) where their lines of sight first meet the vase."""
    rt, up, fw = axes(c)
    C = np.array([0.0, c["H"], c["D"]])
    xn, yn = (uv[:, 0] - c["cx"]) / c["f"], -(uv[:, 1] - c["cy"]) / c["f"]
    d = xn[:, None] * rt + yn[:, None] * up + fw
    d /= np.linalg.norm(d, axis=1)[:, None]

    def g(lam):
        P = C + lam[:, None] * d
        y = np.clip(P[:, 1], *y_range)
        return np.hypot(P[:, 0], P[:, 2]) - R(y)

    lam = np.linspace(0.5 * c["D"], 1.2 * c["D"], steps)
    G = np.stack([g(np.full(len(uv), l)) for l in lam], 1)  # >0 outside the vase
    first = np.argmax(G < 0, axis=1)
    a, b = lam[np.maximum(first - 1, 0)], lam[first]
    for _ in range(30):
        m = (a + b) / 2
        out = g(m) > 0
        a, b = np.where(out, m, a), np.where(out, b, m)
    P = C + ((a + b) / 2)[:, None] * d
    return np.stack([np.arctan2(P[:, 0], P[:, 2]), P[:, 1]], -1)


def photo_to_flat(c: dict, R, table, uv: np.ndarray, theta0: float = 0.0) -> np.ndarray:
    """Image points -> flat (s, t)."""
    th_y = photo_to_surface(c, R, np.asarray(uv, float), (table[0][0], table[0][-1]))
    y = th_y[:, 1]
    return np.stack([R(y) * (th_y[:, 0] - theta0), np.interp(y, table[0], table[1])], -1)


# ---------------------------------------------------------------- flattening without shear


def flatten(R, theta: np.ndarray, y: np.ndarray, keep=None, iters: int = 40, centre: float = 0.0):
    """As-rigid-as-possible flattening (Liu et al. 2008) of the grid theta x y on
    the surface of revolution R. The plain unrolling (s = R theta, t = arc length
    up the profile) keeps lengths around and up the vase, but where the profile
    slopes it shears everything off the centre line, by R'(t) theta: on a shoulder
    curving in to the neck, a face a fifth of a radian off centre leans about 8
    degrees. This keeps every small triangle of the surface as near its true shape
    as the surface allows. keep(theta, y) -> bool limits the patch (cells kept
    where all four corners are kept). The result is turned so the meridian at
    `centre` runs straight up, with y = 0 on it at the origin. Returns XY, the
    flat (x, y) of every grid vertex (array ny x nx x 2, NaN where not kept), in
    world units."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import splu
    TH, Y = np.meshgrid(theta, y)
    ny, nx = TH.shape
    P = surface(R, Y, TH)
    ok = np.ones_like(TH, bool) if keep is None else keep(TH, Y)
    idx = np.arange(ny * nx).reshape(ny, nx)
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
    cell = ok[:-1, :-1] & ok[:-1, 1:] & ok[1:, :-1] & ok[1:, 1:]
    tri = np.concatenate([np.stack([a[cell], b[cell], d[cell]], -1), np.stack([a[cell], d[cell], c[cell]], -1)])
    used = np.unique(tri)
    remap = -np.ones(ny * nx, int)
    remap[used] = np.arange(len(used))
    T = remap[tri]
    V = P.reshape(-1, 3)[used]
    # each triangle's true shape, in its own plane
    e1, e2 = V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]
    l1 = np.linalg.norm(e1, axis=1)
    u = e1 / l1[:, None]
    px = np.einsum("ij,ij->i", e2, u)
    py = np.linalg.norm(e2 - px[:, None] * u, axis=1)
    X = np.zeros((len(T), 3, 2))
    X[:, 1, 0], X[:, 2, 0], X[:, 2, 1] = l1, px, py
    # cotangent weights, per edge opposite each corner
    def cot(p, q, r):  # cotangent of the angle at p
        v1, v2 = q - p, r - p
        return np.einsum("ij,ij->i", v1, v2) / np.abs(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0])
    W = np.stack([cot(X[:, 0], X[:, 1], X[:, 2]), cot(X[:, 1], X[:, 2], X[:, 0]), cot(X[:, 2], X[:, 0], X[:, 1])], -1) / 2
    W = np.clip(W, 1e-3, None)
    edges = [(1, 2, 0), (2, 0, 1), (0, 1, 2)]  # (i, j, opposite corner)
    n = len(used)
    rows, cols, vals = [], [], []
    for i, j, k in edges:
        w = W[:, k]
        rows += [T[:, i], T[:, j], T[:, i], T[:, j]]
        cols += [T[:, i], T[:, j], T[:, j], T[:, i]]
        vals += [w, w, -w, -w]
    L = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
    # start from the plain unrolling; pin one vertex (translation)
    yt, tt = arc_table(R, float(y.min()) - 5, float(y.max()) + 5)
    U = np.stack([R(V[:, 1]) * np.arctan2(V[:, 0], V[:, 2]), np.interp(V[:, 1], yt, tt)], -1)
    pin = int(np.argmin(np.hypot(np.arctan2(V[:, 0], V[:, 2]) - centre, V[:, 1] - np.median(y))))
    free = np.ones(n, bool)
    free[pin] = False
    lu = splu(L[free][:, free].tocsc())
    for _ in range(iters):
        # local: the best rotation for each triangle
        S = np.zeros((len(T), 2, 2))
        for i, j, k in edges:
            S += W[:, k, None, None] * np.einsum("ti,tj->tij", X[:, i] - X[:, j], U[T[:, i]] - U[T[:, j]])
        Us, _, Vt = np.linalg.svd(S)
        Rot = np.einsum("tji,tkj->tik", Vt, Us)  # V U^T
        neg = np.linalg.det(Rot) < 0
        if neg.any():
            Vt[neg, 1] *= -1
            Rot = np.einsum("tji,tkj->tik", Vt, Us)
        # global: the positions that best fit the rotated triangles
        B = np.zeros((n, 2))
        for i, j, k in edges:
            r = W[:, k, None] * np.einsum("tij,tj->ti", Rot, X[:, i] - X[:, j])
            np.add.at(B, T[:, i], r)
            np.add.at(B, T[:, j], -r)
        rhs = B[free] - L[free][:, [pin]].toarray() * U[pin]
        U[free] = np.stack([lu.solve(rhs[:, 0]), lu.solve(rhs[:, 1])], -1)
    # turn so the centre meridian runs straight up, y = 0 on it at the origin
    th_all = np.arctan2(V[:, 0], V[:, 2])
    on = np.abs(th_all - centre) < (theta[1] - theta[0]) / 2
    m = U[on][np.argsort(V[on, 1])]
    k = np.polyfit(m[:, 1], m[:, 0], 1)[0]  # dx/dy along the meridian
    ang = np.arctan(k)
    Rm = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    U = U @ Rm.T
    o = U[on][np.argmin(np.abs(V[on, 1]))]
    U -= o
    XY = np.full((ny * nx, 2), np.nan)
    XY[used] = U
    stretch = []  # report: how far each triangle's edges differ from the true lengths
    for i, j, k in edges:
        stretch.append(np.linalg.norm(U[T[:, i]] - U[T[:, j]], axis=1) / np.linalg.norm(X[:, i] - X[:, j], axis=1))
    stretch = np.concatenate(stretch)
    print(f"  flattened {len(used)} points, {len(T)} triangles: edge lengths within "
          f"{np.percentile(np.abs(stretch - 1), 50) * 100:.2f}% (median), {np.percentile(np.abs(stretch - 1), 99) * 100:.2f}% (99%)")
    return XY.reshape(ny, nx, 2)
