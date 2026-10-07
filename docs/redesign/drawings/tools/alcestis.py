"""Alcestis: two drawings from Lenormant and de Witte, Élite des monuments céramographiques II
(Paris, 1857), pl. LIV, a plate printed across two facing pages, as scanned by Heidelberg University
Library in one image (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1857bd2%3A455a_Planche_054.jpg/full/full/0/default.jpg
(3420 x 2850; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1857bd2/0577)
The vase, as the Élite gives it (text p. 160): a red-figure Nola amphora in the Blacas collection,
the painting running round both sides. Apollo Nomios keeps King Admetus' herds: Apollo, a bull and
a palm; Admetus on horseback.
  - alcestis-apollo.svg: Apollo, with the palm and the bull.
  - alcestis-admetus.svg: Admetus on his horse.
Both are drawn in one frame, at the plate's own line weight, and nothing joins the two groups, so
laid side by side at their place on the plate they give the whole scene (John, 2026-10-07: "If you
do two can they be rejoined later?").

The Getty copy on the Internet Archive (gri_33125009347440, leaves 637 and 638) loses the bull's
head in its binding; Heidelberg's shows it, but its pages curve into the fold, which runs through
the bull's head. So the scan is levelled first (level):
  - the panel's top and bottom edges, printed straight, are measured at every column; each column
    is moved and scaled so they come out straight and level, 1450 px apart;
  - each page's tilt (left 1.5 degrees, right 0.65, measured on its flat part) is taken out, the
    two blending across the fold, so the figures stand upright;
  - near the fold the panel is up to 2.4% shorter: perspective shrinks the width as much as the
    height, so each column there is widened by the same factor;
  - and there the page slopes away from the camera, which narrows it sideways further: each column
    is widened by an estimate of that too (WIDEN_Z0), set so the dots on the bull's forehead come
    out round, as on the vase. It adds about 90 px across the bull's head and 35 px to the
    horse's side.
  More than 450 px from the fold (NEAR_FOLD) the levelled scan matches the Getty copy (which lies
  flat but for its gutter) to 1-2 px. Near the fold neither copy can check it: Getty's is
  squeezed or missing there.
  - The fold's crease, a thin light line down the panel and through the bull's ear, is painted out
    (CREASE) before the lines are found: it gets no line, and the lines it crosses join.

Plate -> drawing, as for Suppliant Women (tools/suppliants_aesch.py): the plate prints the black
ground black, so the figures' outline comes free. The lines inside are the plate's own (local
contrast); the faces (FACES) are the plate's dark paint at its own width, so eyes and mouths stay
fine (John, 2026-10-07: "not too heavy of a line on fine details like eyes").

    python3 docs/redesign/drawings/tools/alcestis.py 11n_elite2_pl54_heidelberg.jpg [qa_stem]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

HERE = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- levelling (scan px)
FOLD = 1702                     # the crease in the scan, where the two pages meet
BLEND = 60                      # px either side of the fold over which the two tilts blend
FLAT_L = (200, 1250)            # columns where each page lies flat: its tilt is fitted there
FLAT_R = (1950, 3250)
PANEL_X = (167, 3276)           # the panel's left and right ends
T0, HP = 600.0, 1450.0          # the levelled panel's top edge and height
NEAR_FOLD = 450                 # columns this near the fold get the perspective widening
# The page also slopes away from the camera as it curves into the fold, and that narrows the plate
# sideways by cos(slope), which the frame's edges cannot show. An estimate (John, 2026-10-07:
# "Estimate and widen"): the height lost at each column gives the paper's depth below the flat
# page (depth = Z0 * (HP / height - 1), Z0 the camera's distance in scan px), its slope gives the
# narrowing, and each column is widened by 1 / cos(slope) as well. Z0 is not known. John chose
# 8300 px (the camera at about 1 m, at the scan's 207 dpi): there the dots on the bull's forehead,
# round on the vase once its curve is allowed for, come out round (median width over height 1.0,
# against 0.73 unwidened). He had seen the camera at 50 and 65 cm (the bull's head 26 and 41 px
# wider) and found them "still too smooshed". The heights are smoothed (WIDEN_SMOOTH px) first, or
# the slope follows the edges' pixel noise. None: no widening.
WIDEN_Z0 = 8300
WIDEN_SMOOTH = 15
# the crease in the levelled scan: a straight line through these points, painted out CREASE_W px
# either side by interpolating across it, row by row
CREASE = [(1714, 630), (1703, 1970)]
CREASE_W = 4

# ---------------------------------------------------------------- drawing (levelled px)
UP = 3                          # work at 3x, so curves stay smooth
DARK = 85                       # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000             # plate px: dark areas this large are ground (but those listed as paint)
FACE_DARK = 110                 # in FACES, the lines are the paint darker than this, at its own width
# A thin clay line too faint to part two dark areas once smoothed (Apollo's hair from the ground at
# its front, where only a 1 px reserved line runs from the wreath's tip to the forehead): WALLS
# (levelled px) part them, WALL_W px wide, along that line.
WALL_W = 1.5
GROUPS = {
    'apollo': dict(
        out='alcestis-apollo.svg', box=(200, 600, 1850, 2050),
        seeds=[(455, 1413), (1261, 1413)],                      # Apollo's chest; the bull's flank
        pockets=[(370, 1960)],                                  # between his feet, under his mantle
        walls=[[(548, 925), (556, 932), (564, 942), (570, 950)]],
        paint=[(440, 950)],                                     # his hair, larger than AUTO_GROUND
        faces=[(520, 970, 600, 1075)],
        title='Apollo with a palm and a bull',
        desc='Line drawing after the 1857 plate of a Nola amphora in the Blacas collection (Lenormant '
             'and de Witte, Élite des monuments céramographiques II, pl. LIV); cut out and retraced.'),
    'admetus': dict(
        out='alcestis-admetus.svg', box=(1740, 600, 3250, 2050),
        seeds=[(2650, 1497), (2733, 1052)],                     # the horse's body; Admetus' mantle
        pockets=[(2409, 1197), (2411, 1170), (2072, 1002)],     # below the reins, between them; under the jaw
        walls=[],
        paint=[],
        faces=[(2680, 755, 2740, 860)],
        title='Admetus on horseback',
        desc='Line drawing after the 1857 plate of a Nola amphora in the Blacas collection (Lenormant '
             'and de Witte, Élite des monuments céramographiques II, pl. LIV); cut out and retraced.'),
}


def edges(g, run=5):
    """The panel's top and bottom edge at every column (scan px): the first and the last run of
    `run` px darker than 80 in rows 400-2300; lightly smoothed (the fold bends them in a sharp V);
    nan off the panel."""
    gs = ndi.gaussian_filter(g, 1.0)
    W = g.shape[1]
    top = np.full(W, np.nan)
    bot = np.full(W, np.nan)
    dark = ndi.minimum_filter1d((gs[400:2300] < 80).astype(np.uint8), run, axis=0, origin=-(run // 2)) > 0
    for x in range(PANEL_X[0], PANEL_X[1] + 1):
        d = np.where(dark[:, x])[0]
        if len(d):
            top[x], bot[x] = 400 + d.min(), 400 + d.max() + run - 1
    ok = ~np.isnan(top)
    for e in (top, bot):
        e[ok] = ndi.gaussian_filter1d(ndi.median_filter(e[ok], 7), 1.5)
    return top, bot


def level(img, margin=150):
    """The scan levelled (see the docstring); rows 0 to T0 + HP + margin, columns as the scan's but
    widened near the fold. Also returns xmap, which takes an x in the levelled frame without the
    WIDEN_Z0 estimate (where every point in this file is placed) to the frame returned."""
    g = np.asarray(Image.fromarray(img).convert('L'), np.float32)
    top, bot = edges(g)
    W = g.shape[1]
    xs = np.arange(W, dtype=float)
    ok = ~np.isnan(top)
    slope = {}
    for name, (a, b) in (('L', FLAT_L), ('R', FLAT_R)):
        sel = (xs >= a) & (xs <= b)
        slope[name] = (np.polyfit(xs[sel], top[sel], 1)[0] + np.polyfit(xs[sel], bot[sel], 1)[0]) / 2
    t = np.clip((xs - (FOLD - BLEND)) / (2 * BLEND), 0, 1)
    t = t * t * (3 - 2 * t)
    lean = slope['L'] * (1 - t) + slope['R'] * t      # dy/dx of the page at each column
    k = np.ones(W)
    k[ok] = HP / (bot[ok] - top[ok])
    k[np.abs(xs - FOLD) >= NEAR_FOLD] = 1.0
    ucol0 = np.cumsum(k) - k[0]                       # output column of each scan column
    xmap = lambda x: x                                # noqa: E731
    if WIDEN_Z0:
        r = ndi.gaussian_filter1d(1 / k, WIDEN_SMOOTH)            # the height lost, smoothed
        dip = np.gradient(WIDEN_Z0 * (1 / r - 1)) * r            # depth per px of the flat page
        k *= np.where(np.abs(xs - FOLD) < NEAR_FOLD, np.sqrt(1 + dip ** 2), 1.0)
        xmap = lambda x: np.interp(np.interp(x, ucol0, xs), xs, np.cumsum(k) - k[0])  # noqa: E731
    ucol = np.cumsum(k) - k[0]
    v = np.arange(0, T0 + HP + margin, dtype=float)
    U, V = np.meshgrid(np.interp(np.arange(0, ucol[-1] + 1), ucol, xs), v)
    # a vertical line in the plate runs at dx/dy = -lean on the page; the edges are read at the
    # source column, which the lean moves: solve for it in turn
    sU = np.interp(U, xs, lean)
    X = U.copy()
    for _ in range(4):
        tt = np.interp(X, xs[ok], top[ok])
        bb = np.interp(X, xs[ok], bot[ok])
        Y = tt + (V - T0) * (bb - tt) / HP
        X = U - sU * (Y - (tt + bb) / 2)
    out = np.stack([ndi.map_coordinates(img[..., c].astype(np.float32), [Y, X], order=3, mode='nearest')
                    for c in range(3)], -1)
    return np.clip(out, 0, 255).astype(np.uint8), xmap


def paint_out_crease(g, xmap):
    """The crease interpolated away, row by row, CREASE_W px either side of its line."""
    (xa, ya), (xb, yb) = CREASE
    xa, xb = xmap(xa), xmap(xb)
    g = g.copy()
    for y in range(g.shape[0]):
        c = xa + (y - ya) * (xb - xa) / (yb - ya)
        l, r = int(np.floor(c)) - CREASE_W, int(np.ceil(c)) + CREASE_W
        g[y, l:r + 1] = np.linspace(g[y, l - 1], g[y, r + 1], r - l + 3)[1:-1]
    return g


def faint_stretches(firm, loose):
    """The faint stretches of the plate's thin lines (as in hippolytus.py and suppliants_aesch.py):
    a stretch standing alone must be line-shaped; a short one, or a piece of the looser lines'
    centre line between firm lines, must bridge two firm lines and run along at least one."""
    def axis(p):
        if len(p) < 3:
            return np.zeros(2), 0.0
        w, vv = np.linalg.eigh(np.cov(p.T.astype(float)))
        return vv[:, 1], float(np.sqrt(max(w[1], 1e-9) / max(w[0], 0.25)))

    firm_lab = ndi.label(firm)[0]
    box = np.ones((2 * UP + 3, 2 * UP + 3), bool)

    def bridges(lab, small):
        keep = np.zeros(lab.max() + 1, bool)
        for k, sl in enumerate(ndi.find_objects(lab), 1):
            pad = 8 * UP
            ys = slice(max(sl[0].start - pad, 0), sl[0].stop + pad)
            xs = slice(max(sl[1].start - pad, 0), sl[1].stop + pad)
            mine = lab[ys, xs] == k
            if mine.sum() > small:
                continue
            fl = firm_lab[ys, xs]
            reach = ndi.binary_dilation(mine, structure=box)
            touched = [f for f in np.unique(fl[reach]) if f]
            near = ndi.distance_transform_edt(~mine) <= 6 * UP
            meets = [np.argwhere(reach & (fl == f)).mean(0) for f in touched]
            runs = [axis(np.argwhere(near & (fl == f)))[0] for f in touched]
            for i in range(len(touched)):
                for j in range(i + 1, len(touched)):
                    d = meets[j] - meets[i]
                    if np.hypot(*d) >= 1:
                        d /= np.hypot(*d)
                        keep[k] |= max(abs(d @ runs[i]), abs(d @ runs[j])) > np.cos(np.radians(30))
        return keep[lab]

    flab, n = ndi.label(loose & ~ndi.binary_dilation(firm, iterations=UP))
    alone = np.zeros(n + 1, bool)
    for k, sl in enumerate(ndi.find_objects(flab), 1):
        mine = flab[sl] == k
        alone[k] = mine.sum() > 12 * UP * UP and axis(np.argwhere(mine))[1] >= 3
    centre = ndi.label(morphology.skeletonize(loose) & ~firm, structure=np.ones((3, 3)))[0]
    return alone[flab] | bridges(flab, 12 * UP * UP) | bridges(centre, np.inf)


def draw(lev, grp, xmap, qa=None):
    grp = dict(grp)
    for key in ('seeds', 'pockets', 'paint'):
        grp[key] = [(xmap(x), y) for x, y in grp[key]]
    grp['walls'] = [[(xmap(x), y) for x, y in pts] for pts in grp['walls']]
    grp['faces'] = [(xmap(a), b, xmap(c), d) for a, b, c, d in grp['faces']]
    X0, Y0, X1, Y1 = grp['box']
    X0, X1 = int(np.floor(xmap(X0))), int(np.ceil(xmap(X1)))

    def at(x, y):
        return int(round((y - Y0) * UP)), int(round((x - X0) * UP))

    plate = Image.fromarray(lev).crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)

    # ground: dark, thin lines opened away; the large areas and the listed pockets
    dark = ndi.binary_opening(gs < DARK, structure=morphology.disk(2 * UP))
    for pts in grp['walls']:
        wall = np.zeros_like(dark)
        P = np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)
        for a, b in zip(P[:-1], P[1:]):
            for t in np.linspace(0, 1, int(np.hypot(*(b - a))) + 2):
                q = a + t * (b - a)
                wall[int(round(q[1])), int(round(q[0]))] = True
        dark &= ~(ndi.distance_transform_edt(~wall) <= WALL_W * UP / 2)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in grp['pockets']:
        k = lab[at(x, y)]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    for x, y in grp['paint']:
        k = lab[at(x, y)]
        assert k, f'paint point {(x, y)} is not on dark'
        is_ground[k] = False
    ground = is_ground[lab]
    paint = dark & ~ground

    # the figures: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground)
    keep = {lab[at(x, y)] for x, y in grp['seeds']}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    face = np.zeros_like(fig)
    for fx0, fy0, fx1, fy1 in grp['faces']:
        (a, b), (c, d) = at(fx0, fy0), at(fx1, fy1)
        face[a:c, b:d] = True
    lines = np.where(face, (ndi.gaussian_filter(g, 0.5 * UP) < FACE_DARK) & fig, lines)
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the outline: 2.5 plate px in from the clay's edge, but no more than 0.6 of the figure's
    # half-width there, so thin parts (a tail's tuft, a leaf's tip, an ear, a toe) keep clay
    # inside their outline and show it on the dark theme, as on the vase
    dt = ndi.distance_transform_edt(fig)
    _, (iy, ix) = ndi.distance_transform_edt(~morphology.skeletonize(fig), return_indices=True)
    edge = fig & (dt <= np.minimum(2.5 * UP, 0.6 * dt[iy, ix]))
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    size = np.bincount(lab.ravel())
    ink &= np.where(face, (size > 3 * UP * UP)[lab], (size > 12 * UP * UP)[lab])

    # all the ground stays open on the dark theme, outside the figures as well as in the pockets
    # they close in: else trace_svg's clay rim for thin lines strays onto it (a notch of clay at
    # the horse's mouth, crumbs along the outline)
    held = ground & ~fig
    out = HERE / grp['out']
    info = lw.trace_svg(ink, out, body=fig, open_holes=held, weight="own", title=grp['title'], desc=grp['desc'])
    print(out, info)
    if qa:
        lw.qa_overlay(g, out, info['box'], Path(f'{qa}_{out.stem}.png'))
        lw.qa_dark(out, info['box'], Path(f'{qa}_{out.stem}.dark.png'))
    return info


def main(src, qa=None):
    lev, xmap = level(np.asarray(Image.open(src).convert('RGB')))
    g = paint_out_crease(np.asarray(Image.fromarray(lev).convert('L'), np.float32), xmap)
    lev = np.clip(g, 0, 255).astype(np.uint8)
    if qa:
        Image.fromarray(lev).save(f'{qa}_levelled.png')
    for grp in GROUPS.values():
        draw(lev, grp, xmap, qa)


if __name__ == '__main__':
    main(*sys.argv[1:3])
