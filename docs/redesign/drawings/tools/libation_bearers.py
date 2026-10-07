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

    python3 docs/redesign/drawings/tools/libation_bearers.py 06n_gerhard1843_T24.jpg [qa.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "libation-bearers.svg"

X0, Y0, X1, Y1 = 584, 440, 2945, 1730     # crop in plate px: the frieze, its band and strip cut below
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
FACE_DARK = 110                           # in FACES, the lines are the paint darker than this
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
# Clytemnestra, Orestes, Aegisthus, Electra (boxes, plate px)
FACES = [(1115, 530, 1205, 635), (1550, 545, 1640, 665), (1955, 725, 2075, 860), (2495, 515, 2585, 635)]


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


def drawn(shape, pts, width):
    """A line `width` plate px wide through hand-placed points (plate px), at UP."""
    m = np.zeros(shape, bool)
    P = up(pts)
    for a, b in zip(P[:-1], P[1:]):
        for t in np.linspace(0, 1, int(np.hypot(*(b - a))) + 2):
            q = a + t * (b - a)
            m[int(q[1]), int(q[0])] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


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
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = lw.ink_lines(g, size=9 * UP, low=22, high=34, sigma=0.8 * UP)
    loose = lw.ink_lines(g, size=9 * UP, low=14, high=34, sigma=0.8 * UP)
    faint = faint_stretches(firm, loose)
    lines = (firm | (loose & ndi.binary_dilation(faint, iterations=UP + 1))) & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    face = np.zeros_like(fig)
    for fx0, fy0, fx1, fy1 in FACES:
        (a, b), (c, d) = at(fx0, fy0), at(fx1, fy1)
        face[a:c, b:d] = True
    lines = np.where(face, (ndi.gaussian_filter(g, 0.5 * UP) < FACE_DARK) & fig, lines)
    solid = paint & fig
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
    lab, _ = ndi.label(ink)
    size = np.bincount(lab.ravel())
    ink &= np.where(face, (size > 3 * UP * UP)[lab], (size > 12 * UP * UP)[lab])

    # all the ground stays open on the dark theme (as in alcestis.py)
    held = ground & ~fig
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
