"""Libation Bearers: Orestes killing Aegisthus, from Gerhard, Etruskische und kampanische Vasenbilder
des Königlichen Museums zu Berlin (Berlin, 1843), Taf. XXIV, "Aegisthos", as scanned by Heidelberg
University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843%3AT_24.jpg/full/full/0/default.jpg
(3510 x 2590; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843/0071)
The vase, as Gerhard gives it (text p. 35, note 1): a stamnos from Vulci, bought by Bunsen in Rome
in 1832 (his Berlins antike Bildwerke I, no. 1007). It is Berlin F 2184, attributed by Beazley to
the Copenhagen Painter (ARV2 257.6), now in Moscow, Pushkin Museum (Beazley Archive 202912). The
figures are named on the vase: Clytemnestra with the axe, Orestes, Aegisthus on his throne, and
Electra.

Plate -> drawing, as for Suppliant Women (tools/suppliants_aesch.py): the plate prints the black
ground black, so the figures' outline comes free. The frieze is one linked group (Orestes' rear
foot lies over Clytemnestra's hem, Aegisthus' toes on Orestes' shin, Orestes' arms lock with
Aegisthus'), drawn whole, with the throne and the footstool.
  - The frame's edges bow by 6 px at most over 2,300 (top rule 442-452, the strip under the feet
    1714-1723): the scan is not levelled.
  - Out: the tongue band along the top, cut just below its tongues' tips (TOP), but for the axe
    head, which rises into it (AXE: the axe is kept whole, inside its own outline); the strip and
    the meander along the bottom, cut just above the strip's top edge (BOTTOM); the names painted
    on the ground, which touch no figure and drop out with it.
  - Lines: the plate's dark lines inside the figures (local contrast), the outline, and the plate's
    solid paint; the faces (FACES) from the plate's dark paint at its own width, so eyes stay fine
    (John, 2026-10-07: "Be sure not to use too heavy of a line on fine details like eyes").
  - The plate's own line weight: the frieze is wider than tall, so the house weight (a share of
    the longer side) would run its close lines together.
  - Dark theme: the figures' area is the body; all the ground stays open, as in tools/alcestis.py.

    python3 docs/redesign/drawings/tools/libation_bearers_plate_a.py 06n_gerhard1843_T24.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "libation-bearers-plate-a.svg"

X0, Y0, X1, Y1 = 584, 440, 2945, 1730     # crop in plate px: the frieze, its band and strip cut below
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
# Ground and paint. The plate paints wide black bands that run into the ground: Electra's borders,
# Aegisthus' hair, beard and the border of his mantle. Dark areas that join the ground are not all
# ground, then. The ground's core is the dark that a disk CORE_R plate px across fits in (the bands
# are narrower), in areas of AUTO_GROUND plate px or more. The rest of the dark is ground where it
# borders that core along much of its edge (the ground's corners and narrow gaps), and paint where it
# is large (BAND_MIN plate px) and touches the core only at its ends (less than BAND_TOUCH plate px
# per px of its area). Pockets of ground the figures close in, or that touch the core only at a
# narrow neck, are listed (POCKETS: a point in each, plate px): behind Clytemnestra's face, under
# her raised arm; under Electra's raised arm, behind her head; between Aegisthus' arm and his chest,
# above Orestes' sword and below it. Dark that touches the cuts is ground as well (the gaps between
# the hems and the strip they stand on).
CORE_R = 5
AUTO_GROUND = 10000
BAND_MIN, BAND_TOUCH = 150, 0.08
# Clytemnestra's skirt, Orestes' cuirass, Aegisthus' lap, the throne's leg, the footstool, Electra's
# dress (plate px)
SEEDS = [(950, 1300), (1350, 1150), (1950, 1150), (2245, 1400), (1800, 1690), (2700, 1300)]
POCKETS = [(1220, 610), (2680, 600), (1930, 975), (1960, 1050)]
# the tongues' tips, 1 px below (measured every 100 px; plate px)
TOP = [(580, 497), (686, 495), (786, 495), (986, 495), (1186, 495), (1286, 494), (1486, 493),
       (1686, 494), (1886, 494), (1986, 495), (2086, 496), (2486, 496), (2586, 495), (2686, 495),
       (2786, 497), (2950, 497)]
# the axe head above TOP, along the outer edge of its outline (plate px)
AXE = [(837, 471.5), (856, 468.5), (875, 467.5), (894, 468.5), (910, 471.5), (899, 488), (891, 500),
       (852, 500), (843, 488)]
# the strip's top edge, 1 px above it (measured every 20 px, given every 120; plate px)
BOTTOM = [(580, 1713.2), (704, 1715.2), (824, 1716.5), (944, 1717), (1064, 1717.3), (1184, 1718.8),
          (1304, 1719.7), (1424, 1720), (1544, 1720.9), (1664, 1722.5), (1784, 1721.3), (1904, 1721.2),
          (2024, 1721.4), (2144, 1720.7), (2264, 1720.8), (2384, 1721), (2504, 1720.3), (2624, 1720.2),
          (2744, 1719.3), (2864, 1718.5), (2950, 1718.5)]
# The blood on Aegisthus' chest: the plate prints it in a darker red than the clay, in streaks from
# the wound down. Drawn as LESSONS.md says (Blood; tools/andromache.py): a wash in the line colour,
# no outline, the black lines through it. The blood is the plate's red inside BLOOD (polygon round the
# streaks, plate px; the black edge of his mantle runs just right of it, his nipple just left): its dark cores (green under
# BLOOD_G, red over BLOOD_R, lightly smoothed), grown into the paler red they touch (red over green by
# BLOOD_RG, green under BLOOD_G2: the streaks' tapering tips, which the cores miss and the line finder
# draws as black lines), never within BLOOD_NEAR plate px of the black lines' paint (red under
# BLOOD_BLACK: their fringes are as red), in pieces of BLOOD_MIN plate px or more. The wash's opacity
# follows the plate's grey under it, smoothed over BLEND_SIGMA plate px, from BLEND_A[0] where it is
# BLEND_T[0] to BLEND_A[1] where it is BLEND_T[1], in steps of BLEND_STEP (Andromache's values, John,
# 2026-10-06).
BLOOD = [(2024, 922), (2080, 920), (2082, 960), (2072, 1010), (2062, 1110), (2035, 1160), (2012, 1160),
         (2020, 1080), (2030, 1000), (2032, 962), (2030, 945)]
BLOOD_G, BLOOD_R, BLOOD_RG, BLOOD_G2 = 100, 120, 85, 120
BLOOD_BLACK, BLOOD_NEAR, BLOOD_MIN, BLOOD_RING = 115, 2, 30, 2
BLEND_T, BLEND_A, BLEND_STEP, BLEND_SIGMA = (140, 85), (0.25, 0.55), 0.05, 2
# The thin line across his chest runs on through the streaks on the plate, but prints dark red there,
# and the blood takes it in: drawn through them along its darkest points (plate px), JOIN_W plate px
# wide, over the wash ("you should be able to see black lines through the blood", John, 2026-10-06)
THROUGH = [[(2038, 977), (2047, 977.5), (2059, 978), (2068, 977), (2077, 975)]]
JOIN_W = 2.3
# The faces, and Aegisthus' wreath: in each box (plate px), in turn, the ink is the plate's paint
# darker than its grey (lightly smoothed), at the paint's own width, in place of the lines and the
# solid paint. The eyes are drawn in a thin brown paler than the black: at 110 (Alcestis') their
# lower lids and pupils broke up, at 130 they close as printed; the boxes leave out Clytemnestra's
# curls and Electra's ringlets, whose clay fills in at 130. The wreath is added purple on the black
# hair: at 80 its leaves and stem come out whole, open in the black, as the plate prints them.
FACES = [((1160, 578, 1205, 640), 130),                   # Clytemnestra
         ((1550, 545, 1640, 665), 130),                   # Orestes
         ((1940, 690, 2160, 762), 80),                    # Aegisthus' wreath and hair
         ((1975, 745, 2075, 860), 120),                   # Aegisthus (at 110 his lower lid broke)
         ((2495, 540, 2556, 640), 130)]                   # Electra
# The faintest brown lines (muscles of the arms and legs, ankle bones, knees) slip past the line
# finder: a ridge filter on the plate (at its own scale, lightly smoothed; sato, sigmas FAINT_SIGMA,
# hysteresis FAINT) finds them, inside the figures (FAINT_IN plate px from the outline) and clear of
# the lines already drawn (FAINT_CLEAR plate px) and of the blood; pieces whose centre line runs
# FAINT_MIN plate px or more are drawn along it, FAINT_W plate px wide: at the filter's own width
# Andromache's faint lines came out beaded and heavier than the black (LESSONS.md).
FAINT_SIGMA, FAINT = (1, 1.5), (4, 8)
FAINT_IN, FAINT_CLEAR, FAINT_MIN, FAINT_W = 4, 3, 20, 1.5
# Breaks: where the print fades, a line breaks into pieces whose ends face each other across a short
# gap. Ends of the drawn lines (centre-line ends, the direction read over GAP_RUN plate px back) that
# face each other within GAP_MAX plate px, each pointing at the other within GAP_ANGLE degrees, are
# joined, GAP_W plate px wide, where the plate between them is darker than the clay either side of
# the gap by GAP_DARK grey (lightly smoothed): the faded stretch of the line. True ends (pleats'
# tips, folds that stop) have clay between them, and stay apart.
GAP_MAX, GAP_RUN, GAP_ANGLE, GAP_W, GAP_DARK = 12, 6, 25, 2.0, 10
# Orestes' and Electra's lower eyelids, and Clytemnestra's upper lid (from its corner to her pupil),
# are fainter still, and break up at any threshold that leaves the rest of the face fine: each is traced along its darkest ridge through hand-placed points
# (plate px, from corner to corner), LID_W plate px wide, as hippolytus.py traces a faint line.
LIDS = [[(1595.5, 605.5), (1600, 608.5), (1605, 610), (1610, 610), (1614, 608), (1616.5, 605.5)],
        [(2526, 574.5), (2531.5, 578.3), (2536.5, 579.6), (2541, 579.2), (2545, 577.6)],
        [(1171, 583.5), (1176, 582), (1181, 581.5), (1184, 581)]]
LID_W = 1.2


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


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


def traced(g, pts, width):
    """The plate's own dark line between hand-placed points (plate px), followed by a least-cost
    path along its darkest ridge, `width` plate px wide, at UP (as in hippolytus.py)."""
    P = up(pts)
    pad = 10 * UP
    x0, y0 = int(P[:, 0].min()) - pad, int(P[:, 1].min()) - pad
    x1, y1 = int(P[:, 0].max()) + pad, int(P[:, 1].max()) + pad
    w = ndi.gaussian_filter(g[y0:y1, x0:x1], 0.7 * UP)
    cost = 1 + 40 * np.exp(-np.clip(ndi.grey_closing(w, size=(5 * UP, 5 * UP)) - w, 0, None) / 12)
    path = lw.livewire(cost, [(x - x0, y - y0) for x, y in P])
    m = np.zeros(g.shape, bool)
    m[(path[:, 1] - 0.5).astype(int) + y0, (path[:, 0] - 0.5).astype(int) + x0] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def drawn(shape, pts, width):
    """A line `width` plate px wide through hand-placed points (plate px), at UP."""
    m = np.zeros(shape, bool)
    P = up(pts)
    for a, b in zip(P[:-1], P[1:]):
        for t in np.linspace(0, 1, int(np.hypot(*(b - a))) + 2):
            q = a + t * (b - a)
            m[int(q[1]), int(q[0])] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def faint_lines(g1, fig, ink, blood):
    """The faintest lines (see FAINT), at UP; g1 is the plate's grey at its own scale."""
    from skimage.filters import apply_hysteresis_threshold, sato
    h, w = g1.shape
    small = lambda m: m[::UP, ::UP][:h, :w]  # noqa: E731
    r = sato(ndi.gaussian_filter(g1, 0.6), sigmas=FAINT_SIGMA, black_ridges=True)
    m = apply_hysteresis_threshold(r, *FAINT)
    m &= ndi.binary_erosion(small(fig), iterations=FAINT_IN)
    m &= ~ndi.binary_dilation(small(ink | blood), iterations=FAINT_CLEAR)
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    sk = morphology.skeletonize(m)
    sk &= (np.bincount(lab[sk], minlength=n + 1) >= FAINT_MIN)[lab]
    c = np.zeros(fig.shape, bool)
    yx = np.argwhere(sk) * UP + UP // 2
    c[yx[:, 0], yx[:, 1]] = True
    c = ndi.binary_dilation(c, structure=np.ones((3, 3)), iterations=UP // 2 + 1)  # join the steps
    c = morphology.skeletonize(c)
    return (ndi.distance_transform_edt(~c) <= FAINT_W * UP / 2) & fig


def join_breaks(ink, g, fig):
    """Joins across the breaks in the plate's printing (see GAP_*), at UP."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(ink)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    run = GAP_RUN * UP
    pts = np.argwhere(sk)
    tree = cKDTree(pts)
    lab = ndi.label(sk, structure=np.ones((3, 3)))[0]
    heads = []
    for e in ends:   # the way each end points: from the mean of its line's points within `run`
        near = pts[tree.query_ball_point(e, run)]
        near = near[lab[near[:, 0], near[:, 1]] == lab[tuple(e)]]
        v = e - near.mean(0)
        n = np.hypot(*v)
        heads.append(v / n if n > 0.5 * UP else np.zeros(2))
    gs = ndi.gaussian_filter(g, 0.5 * UP)
    out = np.zeros_like(ink)
    used = set()
    pairs = cKDTree(ends).query_pairs(GAP_MAX * UP)
    for i, j in sorted(pairs, key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]]))):
        if i in used or j in used:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        d = np.hypot(*(b - a))
        if d < 1:
            continue
        u = (b - a) / d
        c = np.cos(np.radians(GAP_ANGLE))
        if heads[i] @ u < c or heads[j] @ -u < c:
            continue
        t = np.linspace(0, 1, int(d) + 2)[1:-1]
        seg = a + t[:, None] * (b - a)
        if not len(seg):
            continue
        inner = gs[seg[:, 0].astype(int), seg[:, 1].astype(int)]
        side = np.array([-u[1], u[0]]) * 3 * UP
        mid = (a + b) / 2
        clay = [gs[int(q[0]), int(q[1])] for q in (mid + side, mid - side)
                if 0 <= q[0] < g.shape[0] and 0 <= q[1] < g.shape[1] and fig[int(q[0]), int(q[1])] and not ink[int(q[0]), int(q[1])]]
        if not clay or np.median(clay) - inner.mean() < GAP_DARK:
            continue
        used |= {i, j}
        m = np.zeros_like(ink)
        q = np.vstack([a, seg, b]).astype(int)
        m[q[:, 0], q[:, 1]] = True
        out |= ndi.distance_transform_edt(~m) <= GAP_W * UP / 2
    return out & fig


def opened(mask, r):
    """mask opened by a disk of radius r px (by distance transforms: a disk this large is slow)."""
    return ndi.distance_transform_edt(~(ndi.distance_transform_edt(mask) > r)) <= r


def ground_and_paint(gs, outside, at):
    """The ground, and the solid paint inside the figures (see CORE_R)."""
    d0 = (gs < DARK) & ~outside
    dark = ndi.binary_opening(d0, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(opened(d0, CORE_R * UP))
    size = np.bincount(lab.ravel())
    size[0] = 0
    core = (size > AUTO_GROUND * UP * UP)[lab]
    lab, n = ndi.label(dark & ~core)
    size = np.bincount(lab.ravel(), minlength=n + 1)
    touch = np.bincount(lab[ndi.binary_dilation(core) & (lab > 0)], minlength=n + 1)
    cut = np.bincount(lab[ndi.binary_dilation(outside, iterations=2 * UP) & (lab > 0)], minlength=n + 1)
    # a band of paint: large, and touching the ground for less than BAND_TOUCH px per px of its area
    # (plate px); what touches the ground more is ground narrower than the core's disk
    is_ground = (touch > 0) & ~((size > BAND_MIN * UP * UP) & (touch * UP < BAND_TOUCH * size))
    is_ground |= cut > 0
    is_ground[0] = False
    for x, y in POCKETS:
        k = lab[at(x, y)]
        assert k or core[at(x, y)], f'pocket point {(x, y)} is not on dark'
        is_ground[k] = bool(k)
    ground = core | is_ground[lab]
    return ground, dark & ~ground


def blood_mask(rgb):
    """The blood (see BLOOD), at UP."""
    c = ndi.gaussian_filter(rgb, (0.7 * UP, 0.7 * UP, 0))
    r, gr = c[..., 0], c[..., 1]
    ok = lw.polygon_mask(r.shape, up(BLOOD)) & ~(ndi.distance_transform_edt(~(r < BLOOD_BLACK)) <= BLOOD_NEAR * UP)
    core = (gr < BLOOD_G) & (r > BLOOD_R) & ok
    m = ndi.binary_propagation(core, mask=core | ((r - gr > BLOOD_RG) & (gr < BLOOD_G2) & ok))
    lab, _ = ndi.label(m)
    return m & (np.bincount(lab.ravel()) >= BLOOD_MIN * UP * UP)[lab]


def add_blood(svg, blood, grey, box):
    """Add the blood to the drawing written by lw.trace_svg (box: the crop box it returned): a wash
    in the line colour whose opacity follows the plate's grey under it (BLEND_*), in steps, each
    step's area drawn over the one below at the opacity that brings the total there to the step's
    (as andromache.py's add_tone). The blood and the grey are resampled as trace_svg resamples the
    ink (to lw.WORK_H, then lw.TRACE_H), so the wash is traced at the lines' own size and their
    transform holds for it."""
    x0, y0, x1, y1 = box
    b = lw.resample_ink(lw.resample_ink(blood[y0:y1, x0:x1], lw.WORK_H), lw.TRACE_H)
    t = grey[y0:y1, x0:x1]
    for h in (lw.WORK_H, lw.TRACE_H):
        t = ndi.zoom(t, h / t.shape[0], order=1)
    assert t.shape == b.shape
    s = BLEND_SIGMA * UP * lw.TRACE_H / (y1 - y0)
    dark = ndi.gaussian_filter(np.where(b, t, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (t0, t1), (a0, a1) = BLEND_T, BLEND_A
    alpha = a0 + (a1 - a0) * np.clip((t0 - dark) / (t0 - t1), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, BLEND_STEP):
        m = b & (alpha >= a - BLEND_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=2, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def main(src, qa=None):
    rgb = Image.open(src).convert('RGB').crop((X0, Y0, X1, Y1))
    rgb = np.asarray(rgb.resize((rgb.width * UP, rgb.height * UP), Image.BICUBIC), np.float32)
    plate = Image.open(src).convert('L').crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 0.7 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    def at(x, y):
        return int(round((y - Y0) * UP)), int(round((x - X0) * UP))

    # outside: the band above TOP (but the axe head), the strip on and below BOTTOM
    top, bottom = up(TOP), up(BOTTOM)
    outside = (yy < np.interp(xx, top[:, 0], top[:, 1])) & ~lw.polygon_mask(g.shape, up(AXE))
    outside |= yy >= np.interp(xx, bottom[:, 0], bottom[:, 1])

    ground, paint = ground_and_paint(gs, outside, at)

    # the scene: the clay area the ground leaves, joined to the seeds
    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[at(x, y)] for x, y in SEEDS}
    assert 0 not in keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground
    # filling the holes keeps whatever lies in the ground the figures close in: a small clay ring on
    # the ground between Orestes and Aegisthus (1667, 1074) came back. Only what joins the seeds stays
    lab, _ = ndi.label(fig)
    fig = np.isin(lab, [lab[at(x, y)] for x, y in SEEDS])
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    face = np.zeros(fig.shape, np.float32)
    for (fx0, fy0, fx1, fy1), t in FACES:
        (a, b), (c, d) = at(fx0, fy0), at(fx1, fy1)
        face[a:c, b:d] = t
    painted = (ndi.gaussian_filter(g, 0.5 * UP) < face) & fig
    face = face > 0
    lines = np.where(face, painted, lines)
    for pts in LIDS:
        lines |= traced(g, pts, LID_W) & fig
    solid = paint & fig & ~face
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    # the outline: 2.5 plate px in from the clay's edge, but no more than 0.6 of the figure's
    # half-width there, so thin parts keep clay inside their outline (as in alcestis.py)
    dt = ndi.distance_transform_edt(fig)
    _, (iy, ix) = ndi.distance_transform_edt(~morphology.skeletonize(fig), return_indices=True)
    edge = fig & (dt <= np.minimum(2.5 * UP, 0.6 * dt[iy, ix]))
    blood = blood_mask(rgb) & fig
    ink = (lines | solid | edge) & ~blood
    # no black outline on the blood: the line finder takes each streak for a line a little wider than
    # the blood, and leaves a fringe along it. Within BLOOD_RING plate px of the blood, ink goes where
    # the nearest line centre lies in the blood (the streak's own fringe); lines whose centres run
    # outside it (the line across the chest, the sword) stay
    P = up(BLOOD)
    (ya, xa), (yb, xb) = (P.min(0) - 3 * BLOOD_RING * UP).astype(int)[::-1], (P.max(0) + 3 * BLOOD_RING * UP).astype(int)[::-1]
    sl = (slice(ya, yb), slice(xa, xb))
    _, (iy, ix) = ndi.distance_transform_edt(~morphology.skeletonize(lines[sl] | solid[sl] | edge[sl]), return_indices=True)
    b = blood[sl]
    ring = (ndi.distance_transform_edt(~b) <= BLOOD_RING * UP) & ~b
    ink[sl] &= ~(ring & b[iy, ix])
    for pts in THROUGH:
        ink |= drawn(ink.shape, pts, JOIN_W) & fig
    g1 = np.asarray(Image.open(src).convert('L').crop((X0, Y0, X1, Y1)), np.float32)
    ink |= faint_lines(g1, fig, ink, blood) & ~blood
    ink |= join_breaks(ink, g, fig) & ~blood
    lab, _ = ndi.label(ink)
    size = np.bincount(lab.ravel())
    ink &= np.where(face, (size > 3 * UP * UP)[lab], (size > 12 * UP * UP)[lab])

    # all the ground stays open on the dark theme (as in alcestis.py)
    # (everything outside the figures, not only the ground: trace_svg fills the pockets the figures
    # close in, and the clay ring left out of them came back as a clay dot)
    held = ~fig
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight="own",
        title='Orestes killing Aegisthus, between Clytemnestra and Electra',
        desc='Line drawing after the 1843 plate of a red-figure stamnos from Vulci by the Copenhagen '
             'Painter, formerly Berlin F 2184, now Moscow, Pushkin Museum (Gerhard, Etruskische und '
             'kampanische Vasenbilder, Taf. XXIV); cut out and retraced.')
    add_blood(OUT, blood, g, info['box'])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
