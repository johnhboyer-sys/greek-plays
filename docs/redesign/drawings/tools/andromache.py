"""Andromache: Neoptolemos killing old Priam, who sits on the altar with the
dead Astyanax across his lap, from Karl Reichhold's drawing of the Vivenzio
hydria in Furtwängler and Reichhold, Griechische Vasenmalerei I (1904),
Taf. 34 ("Hydria mit Iliupersis, Neapel"), as scanned by Heidelberg
University Library (its second copy):
https://digi.ub.uni-heidelberg.de/iiif/2/furtwaengler1904bd1%3A061_Tafel_34_1_Exemplar.jpg/full/full/0/default.jpg
(6734 x 5505; page https://digi.ub.uni-heidelberg.de/diglit/furtwaengler1904bd1/0059)

Plate -> drawing. The plate prints the vase's black ground as a dark
halftone (60-100 grey against 160-200 for the figures), so, as for
Hippolytus, the ground gives most of the outline. But every figure in the
frieze touches another, so the group is cut from its neighbours along the
plate's own lines where they touch:
  - The band round the vase's neck is a ring (RING: centre and radius fitted
    to the white disk's edge, 0.7 px rms; the band's outer edge lies 149 px
    out). Neoptolemos' crest overlaps it: the band goes, but for the crest,
    cut along its top line (CREST).
  - The sword's tip runs into the scene above (a hand on its left, a woman's
    head on its right): everything past the blade's edges there goes
    (SWORD_ZONE).
  - The palm behind Priam is left out: its crown is half hidden by another
    warrior's arm and spear, so it cannot be drawn whole without inventing
    fronds. Its trunk passes behind Priam's cloak and the altar's end, so the
    cut follows their outlines (PALM_ZONE); the warrior and the mourning woman
    beyond the palm go with it.
  - The dead Trojan lying on his shield under Neoptolemos' legs is left out:
    the legs are drawn over him, whole. Within FALLEN_ZONE only the parts of
    the legs are kept (LEGS: each the area its own outlines close, found by
    flood fill with the plate's lines as walls). The kneeling Greek at the
    right touches the group only through him and goes too.
  - The altar stands on a step drawn as a strip along the floor band; the cut
    follows the altar's own bottom line (FLOOR_ZONE).

    python3 docs/redesign/drawings/tools/andromache.py furtwaengler1904bd1_061_Tafel_34.jpg [qa.png]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import draw, morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
OUT = Path(__file__).resolve().parent.parent / "andromache.svg"
S = lw.STRAIGHT

X0, Y0, X1, Y1 = 2700, 1860, 4620, 4200   # crop in plate px: the group, with the sword's tip
UP = 2                                    # work at 2x the plate's px
GROUND_T = 130                            # the ground's halftone (60-100) against the figures (160-200)
AUTO_GROUND = 3000                        # plate px: dark areas this large are ground ...
# ... but for these, paint: the helmet's two black parts, Astyanax's hair, the blood on Priam's
# back and on the altar (the --diag run lists every dark area the group closes in)
PAINT = [(3720, 2725), (3853, 2755), (3636, 3578), (3317, 3190), (2902, 3865)]
# and smaller dark areas are paint but for these, ground: between the sword's hilt and his knuckles;
# under his jaw, between his chin and his arm; under his outstretched arm, between the folds of
# the cloak hanging from it, and between it and Priam's beard
GROUND = [(3918, 2430), (3742, 2904), (3538, 3096), (3458, 3116)]
# solid paint: dark on the plate lightly smoothed, and wider than a line (5 plate px): heavier
# smoothing ran close lines together (the altar's egg-and-dart, the hems) into blots
PAINT_T, PAINT_W = 130, 5
SEEDS = {'neoptolemos': (4050, 2600), 'priam': (3200, 3250), 'altar': (3000, 3800), 'sword': (4100, 2200)}
RING = (3363.0, 2101.8, 485.0 + 149)      # the band's outer edge: centre x, y, radius (plate px)
# the crest's top line, from where its front curl leaves the band to where its top does
CREST = [(3557, 2706), (3567, 2690), (3568, 2670), (3577, 2654), (3592, 2645), (3608, 2640), (3625, 2628),
         (3650, 2608), (3680, 2588), (3710, 2574), (3740, 2566), (3770, 2563), (3796, 2566)]
# zones: closed paths, plate px; the path follows the plate's lines between points, except
# across a STRAIGHT step (through the ground or through parts kept anyway)
SWORD_ZONE = [(4122, 2066), (4150, 2030), (4185, 1993), (4230, 1942), (4282, 1897), S, (4300, 1880), S,
              (4278, 1960), (4265, 2010), (4252, 2060), (4228, 2090), (4205, 2112), S, (4290, 2180), S,
              (4560, 2180), S, (4560, 1820), S, (4060, 1820), S, (4060, 2066), S]
PALM_ZONE = [(2650, 2450), S, (3260, 2450), S, (3260, 2880), S, (3180, 3000), S, (3120, 3150), S,
             (3076, 3172), (3072, 3210), (3077, 3250), S, (3040, 3300), S, (2990, 3400), S,
             (2950, 3423), (2900, 3421), (2850, 3432), (2818, 3470), (2811, 3520), (2818, 3575), (2823, 3620),
             (2826, 3680), S, (2790, 3720), S, (2758, 4000), S, (2745, 4052), S, (2650, 4300), S]
FLOOR_ZONE = [(2745, 4052), (2765, 4057), (2950, 4080), (3112, 4103), (3300, 4122), (3490, 4141), S,
              (3530, 4170), S, (3530, 4300), S, (2700, 4300), S]
FALLEN_ZONE = [(3745, 3545), S, (3748, 3700), S, (3750, 3880), S, (3746, 3923), (3748, 3950), (3752, 3972),
               (3764, 3986), (3760, 4007), (3742, 4012), S, (3736, 4078), (3660, 4085), (3580, 4082), (3500, 4080), S,
               (3480, 4300), S,
               (4300, 4300), S, (4700, 4000), S, (4700, 3480), S, (4560, 3410), S, (4300, 3435), S,
               (4110, 3455), S, (3960, 3480), S, (3850, 3500), S]
# a point in each part of the legs: front leg, its foot; back thigh, calf with foot, greave's front
LEGS = [(3900, 3800), (4060, 3995), (4200, 3520), (4397, 3671), (4262, 3650)]
LINE_T, LINE_GROW, LINE_MIN = 16, 2, 40   # the walls for the leg fill (1x px): top-hat, grown, min size


# the line weight: the plate's own (the median width of its lines as found, 0.155% of the drawing's
# height), not the house weight (0.225%): at that weight the close lines (eyelids, lips, curls) ran
# together. John, 2026-10-06, shown both: "Plate's own weight"
WEIGHT = 0.00155
# John's own traces (andromache_traces.json: his strokes as polylines along their centres, the
# marks he filled in as polygons; plate px), where the faces and hands did not come clean
# (apply_trace): Neoptolemos' face (2026-10-06, on a 3x crop of the plate)
TRACES_FILE = Path(__file__).parent / "andromache_traces.json"
TRACES = {k: v for k, v in json.loads(TRACES_FILE.read_text()).items() if k != 'note'} if TRACES_FILE.exists() else {}
TRACE_NEAR, TRACE_EDGE, TRACE_GAP = 6, 6, 1.5   # plate px
# A shape he closed off is filled where the plate's mean tone there (denoised) is under FILL_T:
# the long locks and the black band inside the visor (73-97), not the strap between the locks
# (134-154) or the face (179). The curls at the temple lie over a grey wash (91-167): every small
# shape he closed inside HAIR (x0, y0, x1, y1, plate px) is a curl and is filled ("obviously, the
# hair curls are filled in black"); the ear's inside, larger than HAIR_MAX plate px, is not
FILL_T, HAIR_MAX = 130, 200
HAIR = [(3700, 2791, 3758, 2845)]   # below the gap between the hair and the ear
FAINT = (3.0, 6.0)                        # ridge filter thresholds (hysteresis low, high)
FAINT_MIN = 60                            # plate px: shorter faint pieces are grain
DENOISE = 12                              # non-local means strength (grey levels)
INK_T = 120                               # the plate's black: darker than this, once denoised


def up(pts):
    return [S if p == S else ((p[0] - X0) * UP, (p[1] - Y0) * UP) for p in pts]


def even_lines(mask, t, min_len):
    """The thin parts of `mask` redrawn along their centres, t px wide (pieces of centre line
    shorter than min_len px are grain); the parts wider than t kept as they are."""
    core = ndi.binary_opening(mask, structure=morphology.disk(int(np.ceil(t / 2))))
    wide = mask & ndi.binary_dilation(core, iterations=2)
    sk = morphology.skeletonize(mask & ~wide)
    lab, _ = ndi.label(sk, structure=np.ones((3, 3)))
    sk &= (np.bincount(lab.ravel()) > min_len)[lab]
    return wide | (ndi.distance_transform_edt(~sk) <= t / 2)


def apply_trace(part, ink, edge, fig, tone, wide, t):
    """One of John's traces laid into the drawing. His strokes are drawn t px wide, as every line
    of the drawing, and his filled marks solid; where he left a gap between strokes narrower than
    that widening would close (between the curls at the temple, the lines of the strap), a channel
    TRACE_GAP plate px wide stays open along its middle. The shapes his marks close off inside the
    crop he traced are his: one the plate paints dark there (FILL_T, HAIR), inside the figure, is
    filled (the curls, the black inside the visor); in the others the plate's lines go. Within TRACE_NEAR plate px of his marks the
    plate's lines go too, but for its wide black that lies mostly outside all that (the helmet's
    bowl along his visor line), and where his stroke runs within TRACE_EDGE px of the outline it is
    the outline (he traced the face's outline on the plate's black line, a px or two outside the
    clay's edge, where the drawing's own outline runs). Returns the ink and his own ink (his
    strokes and the shapes filled)."""
    H, W = fig.shape
    strokes, solids = np.zeros_like(fig), np.zeros_like(fig)
    for line in part['lines']:
        P = up(line)
        for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
            rr, cc = draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            strokes[rr[ok], cc[ok]] = True
    for poly in part['solids']:
        solids |= lw.polygon_mask(fig.shape, np.array(up(poly), float))
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(part['box'], (X0, Y0, X0, Y0))]
    inbox = np.zeros_like(fig)
    inbox[by0:by1, bx0:bx1] = True
    to_stroke = ndi.distance_transform_edt(~strokes)
    pen = part['pen'] * UP
    # the shapes he closed off, as he drew them (at his own pen width)
    lab, n = ndi.label(inbox & ~((to_stroke <= pen / 2) | solids))
    rim = np.concatenate([lab[by0, bx0:bx1], lab[by1 - 1, bx0:bx1], lab[by0:by1, bx0], lab[by0:by1, bx1 - 1]])
    size = np.bincount(lab.ravel(), minlength=n + 1)
    is_closed = np.ones(n + 1, bool)
    is_closed[0] = False
    is_closed[np.unique(rim)] = False
    mean = np.bincount(lab.ravel(), weights=tone.ravel(), minlength=n + 1) / np.maximum(size, 1)
    cy, cx = [np.bincount(lab.ravel(), weights=c.ravel(), minlength=n + 1) / np.maximum(size, 1)
              for c in np.mgrid[0:H, 0:W]]
    curl = np.zeros(n + 1, bool)
    for hx0, hy0, hx1, hy1 in HAIR:
        curl |= (cx >= (hx0 - X0) * UP) & (cx < (hx1 - X0) * UP) & (cy >= (hy0 - Y0) * UP) & (cy < (hy1 - Y0) * UP)
    curl &= size < HAIR_MAX * UP * UP
    is_dark = ((mean < FILL_T) | curl) & (np.bincount(lab.ravel(), weights=fig.ravel(), minlength=n + 1) > 0.5 * size)
    closed, filled = is_closed[lab], (is_closed & is_dark)[lab]
    # a filled shape is the black he outlined, its edge where he drew it: the strokes round it stay
    # at his pen width. His other strokes are widened to t, but for a channel along the middle of
    # each gap the widening would close
    rims = strokes & (ndi.distance_transform_edt(~filled) <= pen / 2 + 1.5)
    free = ndi.distance_transform_edt(~(strokes & ~rims)) <= t / 2
    white = inbox & ~((to_stroke <= pen / 2) | solids | filled)
    axis = morphology.skeletonize(white) & (ndi.distance_transform_edt(white) <= (t - pen) / 2 + 1)
    his = (free & ~(ndi.distance_transform_edt(~axis) <= TRACE_GAP * UP / 2)) | \
        (ndi.distance_transform_edt(~rims) <= pen / 2) | solids
    zone = closed | (ndi.distance_transform_edt(~(strokes | solids)) <= TRACE_NEAR * UP)
    # the plate's wide black outside the zone grows back into it, through wide black and outside
    # the closed shapes, as far as TRACE_NEAR px: up to his line, not into what he drew
    cy0, cy1 = max(by0 - (TRACE_NEAR + 1) * UP, 0), min(by1 + (TRACE_NEAR + 1) * UP, H)
    cx0, cx1 = max(bx0 - (TRACE_NEAR + 1) * UP, 0), min(bx1 + (TRACE_NEAR + 1) * UP, W)
    room = (wide & ~closed)[cy0:cy1, cx0:cx1]
    grown = (wide & ~zone)[cy0:cy1, cx0:cx1]
    for _ in range(TRACE_NEAR * UP):
        grown = ndi.binary_dilation(grown) & room
    stays = np.zeros_like(fig)
    stays[cy0:cy1, cx0:cx1] = grown
    edge_kept = edge & ~(to_stroke <= TRACE_EDGE * UP)
    ink = (ink & ~zone) | ((edge_kept | stays) & zone) | his | filled
    return ink, his | filled


def faint_lines(g):
    """Faint dark lines 4-6 plate px wide, by a ridge filter on the plate smoothed past its grain
    (run at the plate's own scale: the lines are wide enough)."""
    from skimage.filters import apply_hysteresis_threshold, sato
    g1 = ndi.zoom(ndi.gaussian_filter(g, UP), 1 / UP, order=1)
    m = apply_hysteresis_threshold(sato(g1, sigmas=[2, 2.5, 3], black_ridges=True), *FAINT)
    m = ndi.zoom(m.astype(np.float32), UP, order=1) > 0.5
    out = np.zeros(g.shape, bool)
    out[:m.shape[0], :m.shape[1]] = m[:g.shape[0], :g.shape[1]]
    return out


def zone(cost, pts, shape):
    path = lw.livewire(cost, up(pts), closed=True)
    return lw.polygon_mask(shape, path), path


def leg_parts(src_l):
    """The legs' areas at 1x, inside FALLEN_ZONE's box: each the light area its own outlines close."""
    xs = [p[0] for p in FALLEN_ZONE if p != S]
    ys = [p[1] for p in FALLEN_ZONE if p != S]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    a = np.asarray(src_l.crop((bx0, by0, bx1, by1)), np.float32)
    dark = ndi.binary_opening(ndi.gaussian_filter(a, 2.0) < GROUND_T, structure=morphology.disk(3))
    g1 = ndi.gaussian_filter(a, 0.8)
    wall = (ndi.grey_closing(g1, size=(9, 9)) - g1) > LINE_T
    lab, _ = ndi.label(wall)
    wall &= (np.bincount(lab.ravel()) >= LINE_MIN)[lab]
    wall = ndi.binary_dilation(wall, iterations=LINE_GROW)
    lab, _ = ndi.label(~dark & ~wall)
    size = np.bincount(lab.ravel())
    size[0] = 0
    keep = np.zeros_like(dark)
    for x, y in LEGS:
        win = lab[y - by0 - 8:y - by0 + 9, x - bx0 - 8:x - bx0 + 9]
        k = max(np.unique(win[win > 0]), key=lambda i: size[i])
        keep |= lab == k
    keep = ndi.binary_dilation(keep, iterations=LINE_GROW + 2)   # the outline lines round each part,
    keep = ndi.binary_closing(keep, structure=morphology.disk(5))  # the lines between parts (the ankle)
    keep = ndi.binary_fill_holes(keep)                            # and the small areas inside the legs
    return keep, (bx0, by0, bx1, by1)


def main(src, qa=None, diag=None):
    src_l = Image.open(src).convert('L')
    plate = src_l.crop((X0, Y0, X1, Y1))
    plate = plate.resize((plate.width * UP, plate.height * UP), Image.BICUBIC)
    g = np.asarray(plate, np.float32)
    gs = ndi.gaussian_filter(g, 2.0 * UP)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    cost = 1 + 40 * np.clip((ndi.gaussian_filter(g, 0.8 * UP) - 60) / 140, 0, 1)   # cheap along dark lines

    # ground: dark, thin lines opened away; the large areas, but for the painted ones
    dark = ndi.binary_opening(gs < GROUND_T, structure=morphology.disk(4 * UP))
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for pts, val in ((PAINT, False), (GROUND, True)):
        for x, y in pts:   # the dark area at or nearest the point (within 15 plate px)
            win = lab[(y - Y0 - 15) * UP:(y - Y0 + 16) * UP, (x - X0 - 15) * UP:(x - X0 + 16) * UP]
            dist = np.hypot(*np.mgrid[-15 * UP:16 * UP, -15 * UP:16 * UP])
            iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
            assert win[iy, ix], f'no dark area near {(x, y)}'
            is_ground[win[iy, ix]] = val
    ground = is_ground[lab]
    paint = ndi.binary_opening(ndi.gaussian_filter(g, 0.8 * UP) < PAINT_T,
                               structure=morphology.disk(PAINT_W * UP // 2)) & ~ground

    # what is cut away: the band (but for the crest), the zones; in the fallen zone, all but the legs
    cx, cy, R = RING
    r = np.hypot(xx / UP + X0 - cx, yy / UP + Y0 - cy)
    crest = lw.livewire(cost, up(CREST))
    a0, a1 = [np.arctan2(y - cy, x - cx) for x, y in (CREST[-1], CREST[0])]
    arc = [((cx + (R + 100) * np.cos(t) - X0) * UP, (cy + (R + 100) * np.sin(t) - Y0) * UP)
           for t in np.linspace(a0, a1, 20)]
    under_crest = lw.polygon_mask(g.shape, np.vstack([crest, arc]))
    cut = (r < R) & ~under_crest
    paths = {}
    for name, pts in (('sword', SWORD_ZONE), ('palm', PALM_ZONE), ('floor', FLOOR_ZONE)):
        m, paths[name] = zone(cost, pts, g.shape)
        cut |= m
    fallen, paths['fallen'] = zone(cost, FALLEN_ZONE, g.shape)
    legs1, (bx0, by0, bx1, by1) = leg_parts(src_l)
    legs = np.zeros_like(fallen)
    sub = np.asarray(Image.fromarray(legs1.astype(np.uint8) * 255).resize(((bx1 - bx0) * UP, (by1 - by0) * UP),
                                                                        Image.NEAREST)) > 0
    oy, ox = (by0 - Y0) * UP, (bx0 - X0) * UP
    h, w = min(sub.shape[0], H - oy), min(sub.shape[1], W - ox)
    legs[oy:oy + h, ox:ox + w] = sub[:h, :w]
    cut |= fallen & ~legs

    # the group: the light area left, joined to the seeds
    lab, _ = ndi.label(~ground & ~cut)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS.values()}
    assert 0 not in keep, keep
    fig = np.isin(lab, list(keep))
    held = ndi.binary_fill_holes(fig) & ground & ~cut    # ground the group closes in stays open
    fig = ndi.binary_fill_holes(fig) & ~held & ~cut      # paint inside the group stays its own
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    if diag:
        diagnostic(g, ground, cut, fig, paths, Path(diag))
        # check: every dark area the group closes in, ground (left open) or paint (drawn solid)
        for name, m in (('pocket', held), ('paint', paint & fig)):
            hl, n = ndi.label(m)
            for i, sl in enumerate(ndi.find_objects(hl), 1):
                ys, xs = np.nonzero(hl[sl] == i)
                if len(ys) < 150 * UP * UP:
                    continue
                print(name, 'at', (round(X0 + (sl[1].start + xs.mean()) / UP), round(Y0 + (sl[0].start + ys.mean()) / UP)),
                      'size', len(ys) // UP ** 2, 'plate px')

    # lines: the plate's own black, its outline, and its faint brown lines. The print's grain is
    # cleared first by non-local means, which keeps edges: smoothing it away instead filled the
    # 3 px gaps between close lines (the crest's beads, the eyelids, the curls), and a
    # local-contrast finder took each line at its full fuzzy width; both ran close lines together.
    # Reichhold's pen lines are finer than WEIGHT, and thickening every edge to reach it ran them
    # together again, so each thin line is redrawn along its centre exactly WEIGHT wide, while
    # black wider than that (the crest's beads, the helmet, the hair, the blood) keeps its own
    # shape (even_lines). The brown lines of the anatomy (the greaves' and the muscles' lines)
    # print faint, little darker than the grain: a ridge filter at their width finds them
    # (FAINT), long pieces only, away from the black and from the outline
    ys, xs = np.nonzero(fig)
    t = WEIGHT * max(np.ptp(ys), np.ptp(xs))   # the line width, work px
    den = cv2.fastNlMeansDenoising(np.asarray(src_l.crop((X0, Y0, X1, Y1))), None, DENOISE, 7, 21)
    black = (np.asarray(Image.fromarray(den).resize((W, H), Image.BICUBIC), np.float32) < INK_T) & fig
    faint = faint_lines(g) & ndi.binary_erosion(fig, iterations=4 * UP) & \
        ~ndi.binary_dilation(black, iterations=3 * UP)
    lab, _ = ndi.label(faint)
    faint &= (np.bincount(lab.ravel()) > FAINT_MIN * UP * UP)[lab]
    if diag:
        np.save(Path(diag).with_suffix('.faint.npy'), faint)
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(round(t)))   # the outline, as wide as a line
    ink = even_lines(black, t, 3 * UP) | even_lines(faint, t, 3 * UP) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]   # specks of grain; a small curl stays
    body = fig
    if TRACES:
        tone = np.asarray(Image.fromarray(den).resize((W, H), Image.BICUBIC), np.float32)
        wide = black & ndi.binary_dilation(ndi.binary_opening(black, structure=morphology.disk(int(np.ceil(t / 2)))),
                                           iterations=2)
        for part in TRACES.values():
            ink, his = apply_trace(part, ink, edge, fig, tone, wide, t)
            body = body | (his & ndi.binary_dilation(fig, iterations=TRACE_EDGE * UP))   # clay under his outline
    info = lw.trace_svg(
        ink, OUT, body=body, open_holes=held, weight="own",   # drawn at WEIGHT already (even_lines)
        trace_h=lw.WORK_H,   # at TRACE_H a px is 1.1 plate px: the gaps between close lines closed
        title='Neoptolemos killing Priam, who sits on the altar with the dead Astyanax across his knees',
        desc='Line drawing after Karl Reichhold\'s drawing of the Vivenzio hydria by the Kleophrades Painter '
             '(Naples), in Furtwängler and Reichhold, Griechische Vasenmalerei I (1904), Taf. 34; '
             'cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


def diagnostic(g, ground, cut, fig, paths, out):
    from PIL import ImageDraw
    rgb = np.stack([g * 0.5 + 60] * 3, -1)
    rgb[ground] = (40, 40, 80)
    rgb[fig] = rgb[fig] * 0.45 + np.array([255, 170, 60]) * 0.55
    rgb[cut & ~ground] = rgb[cut & ~ground] * 0.5 + np.array([200, 0, 0]) * 0.5
    im = Image.fromarray(rgb.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for name, p in paths.items():
        d.line([tuple(q) for q in p], fill=(0, 255, 255), width=3)
    im.resize((im.width // 4, im.height // 4), Image.LANCZOS).save(out)
    im.save(out.with_suffix('.full.png'))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    diag = sys.argv[sys.argv.index('--diag') + 1] if '--diag' in sys.argv else None
    if diag:
        args = [a for a in args if a != diag]
    main(args[0], args[1] if len(args) > 1 else None, diag)
