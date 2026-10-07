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
    flood fill with the plate's lines as walls), and Priam's feet (what John's
    trace of them closes). The kneeling Greek at the right touches the group
    only through him and goes too.
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


# the line weight: finer than the house weight (0.225%), at which the close lines (eyelids, lips,
# curls) ran together; John, 2026-10-06, shown both: "Plate's own weight" (0.155%, the median width
# of its lines as found). Then 0.11%: at 0.155% the pleats on Priam's chest, 5 plate px apart, ran
# together too; shown 0.155, 0.11 and 0.088%: "Yeah the thinner weight is needed"
WEIGHT = 0.0011
# John's own traces (andromache_traces.json: his strokes as polylines along their centres, the
# marks he filled in as polygons, his dots as points, the areas he marked to be filled; plate px),
# where the faces and hands did not come clean (apply_trace), each on a crop of the plate,
# 2026-10-06: Neoptolemos' face; Priam's head with both hands on it, and his beard and mouth below
# the arm (the blood on his scalp marked on a screenshot of the drawing); Astyanax; Neoptolemos'
# sword hand; Astyanax's hanging hand
TRACES_FILE = Path(__file__).parent / "andromache_traces.json"
TRACES = {k: v for k, v in json.loads(TRACES_FILE.read_text()).items() if k.startswith('trace_')} if TRACES_FILE.exists() else {}
TRACE_NEAR, TRACE_EDGE, TRACE_GAP = 6, 6, 1.5   # plate px
# A shape he closed off is filled where the plate's mean tone there (denoised) is under FILL_T:
# the long locks and the black band inside the visor (73-97), not the strap between the locks
# (134-154) or the face (179). The curls at the temple lie over a grey wash (91-167): every small
# shape he closed inside HAIR (x0, y0, x1, y1, plate px) is a curl and is filled ("obviously, the
# hair curls are filled in black"); the ear's inside, larger than HAIR_MAX plate px, is not
FILL_T, HAIR_MAX = 130, 200
HAIR = [(3700, 2791, 3758, 2845)]   # below the gap between the hair and the ear
# The streaks on Priam's scalp and on Astyanax's body are blood, which the plate prints lighter
# than its black. John marked them to be filled: Priam's on a screenshot of the drawing ('fill':
# "they and the black outlines are blood. same color for the blue and the black shapes they fill
# in"), Astyanax's in two greens on his crop ('fill_dark', 'fill_light': "dark green: darker blood;
# light green, lighter, more transparent blood"). On Priam he painted over his own outlines: a
# shape they close, or a gap between his strokes, that his marks mostly cover is filled, and his
# outlines give the edges and are of the blood too ("the outlines of the blood should be the blood
# color/gradient, wash too"; but his dots, and his lines that only touch it, the hands' outlines),
# as are the small bits of them his marks just miss (under BIT plate px^2: where strokes meet,
# a streak's tail). On Astyanax he painted the plate's streaks, outlined by nothing (PAINTED):
# there the blood is the plate's own streak under his paint, darker than BLOOD_T (his brush is
# broader than the streaks: drawn as painted, the wounds came out "absurdly big"), and its lines
# there. The blood is thinned paint in lighter brushstrokes (John) with his lines black across it
# ("you should be able to see black lines through the blood"): a wash in the line colour whose
# opacity follows the plate's darkness under it, smoothed over BLEND_SIGMA plate px, from
# BLEND_A[0] where the plate is BLEND_T[0] to BLEND_A[1] where it is BLEND_T[1], in steps of
# BLEND_STEP (John, shown flat tones and a blend: "the fourth blend ... was better ... make it more
# subtle"). Paths of class "tone", between the body and the lines, as philoctetes.py draws the
# brown wash of his hair and beard
BLOOD = ('fill', 'fill_dark', 'fill_light')
PAINTED = ('fill_dark', 'fill_light')
BLOOD_T = 132
BIT = 100
# The plate rims some wounds with a darker edge just outside his paint, which the line finder took
# for lines ("The black circular outlines for the wounds aren't in the original"): a piece of the
# plate's ink there that hugs his paint (half of it within RIM plate px) goes
RIM = 6
BLEND_T, BLEND_A, BLEND_STEP, BLEND_SIGMA = (140, 85), (0.25, 0.55), 0.05, 2
# His line from Astyanax's groin down across the thigh runs under the blood he painted over it
# (his light green hides it but for a fleck): joined across, from his groin line through the
# fleck to where it comes out, to be seen through the blood
JOINS = {'trace_3_astyanax_face_and_hip_hand': [[(3358.61, 3579.16), (3359.19, 3584.36), (3365.0, 3591.0)]]}
# His trace of the kilt (the scabbard's edges, the chape, the tassels, the flaps and hems) leaves out
# lines he did not mean to change: the chape's meander, the straps crossed over the scabbard, the
# corslet's flaps above it. There (PARTIAL) the plate's lines near his go only where they run along
# his, within DUP_ANGLE degrees (the same line, drawn twice); those that cross his stay. And the
# shape he closed round the meander keeps the plate's lines (KEEP: a point inside it, plate px)
PARTIAL = {'trace_13_kilt'}
DUP_ANGLE = 35
KEEP = {'trace_13_kilt': [(3778, 3232)]}
# The dark smear across the pleats on Priam's chest is blood too, not black (John, ringing it: "The
# area here you have black is actually blood"): inside his ring (CHEST), the plate's dark wider
# than CHEST_W plate px, darker than BLOOD_T as on Astyanax ("make sure the blood on here has the
# same effect as on the corpse"), is blood, in the same wash. The pleats run on under it: John
# traced them through it ('chest_pleats' in andromache_traces.json, his strokes over the plate),
# drawn as lines under the blood and as far as REACH plate px past its edge, where they meet the
# plate's own (clean there: his strokes, drawn in pieces, would break them); there the plate's
# lines within DUP plate px of his are the same pleats, and go. Inside his ring the plate's lines
# are all redrawn along their centres (centre_lines): its black there is pleats, and the blood's
# soft edge, wider, had stayed as blobs beside the wash. Where a pleat prints faint the finder
# broke it into dashes: gaps up to PLEAT_GAP plate px along the pleats (near upright) are closed
CHEST = [(3326, 3290), (3266, 3281), (3252, 3270), (3245, 3253), (3244, 3184), (3250, 3152), (3263, 3133),
         (3287, 3123), (3344, 3122), (3358, 3126), (3374, 3146), (3394, 3188), (3392, 3220), (3356, 3280),
         (3350, 3284), (3328, 3284)]
CHEST_W, CHEST_MIN, DUP, REACH, PLEAT_GAP = 6, 40, 3, 3, 8
# The three dark streaks on the altar's front and the floor below Astyanax are blood drips, drawn
# the same way (a ring round each, plate px); no lines run under them, so all their dark is blood,
# however thin (on the chest, only what is wider than the pleats, CHEST_W)
ALTAR = [[(2865, 3770), (2945, 3770), (2945, 3945), (2865, 3945)],
         [(3125, 3860), (3212, 3860), (3212, 4030), (3125, 4030)],
         [(3380, 3850), (3430, 3850), (3430, 3956), (3380, 3956)]]   # below the hanging hand
CHEST_PLEATS = json.loads(TRACES_FILE.read_text()).get('chest_pleats', {}).get('lines', []) if TRACES_FILE.exists() else []
# The lines the drawing still missed (the pleats' tops under Priam's arm and round the blood, his
# fingers on his chest, his robe's left edge, the base of Neoptolemos' neck, his armpit): John drew
# them in black over the overlay ('missed_lines'), at 0.84 px per plate px. Each is drawn a line
# wide along the plate's own line under it: every SNAP_STEP plate px his point moves to the darkest
# point within SNAP_R plate px, if that is SNAP_D grey levels darker
MISSED = json.loads(TRACES_FILE.read_text()).get('missed_lines', {}).get('lines', []) if TRACES_FILE.exists() else []
SNAP_STEP, SNAP_R, SNAP_D = 3, 2, 6
# Areas John marked to be black ink ('black_fills': the gap in Neoptolemos' lock where it crosses
# the strap behind his neck): solid
BLACK = json.loads(TRACES_FILE.read_text()).get('black_fills', {}).get('solids', []) if TRACES_FILE.exists() else []
# Two slivers of figure that the cut left on the sword hand, all outline, with a rim of clay round
# them in the dark theme (the crossguard's tip; a wedge at the fist's lower left): John ringed them
# to go: each is the plate's dark ground, which the cut left in the figure. Inside each ring (grown
# by 2 plate px) the figure loses what is as dark as the ground (GROUND_T), and the ink left
# farther than a line's width from it goes
ERASE = [[(3932, 2397), (3925, 2396), (3920, 2390), (3920, 2386), (3922, 2381), (3928, 2378),
          (3936, 2377), (3940, 2383), (3934, 2391), (3936, 2395), (3932, 2397)],
         [(3874, 2488), (3869, 2484), (3868, 2472), (3877, 2459), (3881, 2457), (3881, 2459),
          (3886, 2464), (3889, 2470), (3879, 2477), (3874, 2488)]]
# A gap between his strokes longer than THICK_LEN plate px whose mean tone is under THICK_T is
# black too: he traced a thick line along both edges (the line under Priam's arm, 70-90; the dark
# gaps at the corners of his strokes on Neoptolemos' face are 8 px or shorter)
THICK_LEN, THICK_T = 20, 100
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


def centre_lines(mask, t, min_len, spur):
    """All of `mask` redrawn along its centre line, t px wide: the skeleton, less the spurs that
    bulges in the mask put out (branches shorter than spur px between a junction and a free end)
    and pieces shorter than min_len px (grain)."""
    n8 = np.ones((3, 3), int)
    sk = morphology.skeletonize(mask)
    for _ in range(2):   # a spur off a spur
        nb = ndi.convolve(sk.astype(int), n8, mode='constant') - 1
        near_j = ndi.binary_dilation(sk & (nb >= 3), structure=n8)
        lab, n = ndi.label(sk & ~near_j, structure=n8)
        size = np.bincount(lab.ravel(), minlength=n + 1)
        at_j, at_end = np.zeros(n + 1, bool), np.zeros(n + 1, bool)
        at_j[lab[ndi.binary_dilation(near_j, structure=n8) & ~near_j & sk]] = True
        at_end[lab[sk & (nb == 1) & ~near_j]] = True
        cut = at_j & at_end & (size < spur)
        cut[0] = False
        sk = morphology.skeletonize(sk & ~cut[lab])
    lab, _ = ndi.label(sk, structure=n8)
    sk &= (np.bincount(lab.ravel()) > min_len)[lab]
    return ndi.distance_transform_edt(~sk) <= t / 2


def trace_strokes(part, shape):
    """John's strokes in one of his traces, 1 px wide, work px."""
    strokes = np.zeros(shape, bool)
    for line in part['lines']:
        P = up(line)
        for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
            rr, cc = draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
            strokes[rr[ok], cc[ok]] = True
    return strokes


def below_trace(part, shape):
    """Inside the crop John traced, what lies below his lowest stroke in each column (work px)."""
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(part['box'], (X0, Y0, X0, Y0))]
    sub = trace_strokes(part, shape)[by0:by1, bx0:bx1]
    low = np.where(sub.any(0), sub.shape[0] - 1 - np.argmax(sub[::-1], 0), sub.shape[0])
    out = np.zeros(shape, bool)
    out[by0:by1, bx0:bx1] = np.arange(sub.shape[0])[:, None] > low[None, :] + max(part['pen'] * UP, 2.0)
    return out


def traced_area(part, shape):
    """What one of John's traces covers: his strokes and the shapes they close inside the crop he
    traced (those not reaching its edge), work px. The cut spares it."""
    band = within(trace_strokes(part, shape), max(part['pen'] * UP, 2.0) / 2)
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(part['box'], (X0, Y0, X0, Y0))]
    inbox = np.zeros(shape, bool)
    inbox[by0:by1, bx0:bx1] = True
    lab, _ = ndi.label(inbox & ~band)
    rim = np.unique(np.concatenate([lab[by0, bx0:bx1], lab[by1 - 1, bx0:bx1], lab[by0:by1, bx0], lab[by0:by1, bx1 - 1]]))
    return (band | ((lab > 0) & ~np.isin(lab, rim))) & inbox


def along(ink, strokes, angle, t):
    """Where the ink runs along the nearest stroke (within DUP_ANGLE degrees), or lies within a
    line's width of it; not where it crosses."""
    d, (iy, ix) = ndi.distance_transform_edt(~strokes, return_indices=True)
    f = ndi.gaussian_filter(ink.astype(np.float32), UP / 2)
    gy, gx = np.gradient(f)
    jxx, jxy, jyy = [ndi.gaussian_filter(a, 1.5 * UP) for a in (gx * gx, gx * gy, gy * gy)]
    ink_angle = (0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2) % np.pi   # the ink line's direction
    diff = np.abs(ink_angle - angle[iy, ix])
    diff = np.minimum(diff, np.pi - diff)
    return (d <= t) | (diff < np.radians(DUP_ANGLE))


def within(mask, r):
    """Within r px of mask; nowhere if the mask is empty (scipy measures an empty mask's distances
    from just outside its corner, and drew a speck there)."""
    return ndi.distance_transform_edt(~mask) <= r if mask.any() else np.zeros_like(mask)


def apply_trace(part, ink, edge, fig, tone, wide, t, partial=False, keep=()):
    """One of John's traces laid into the drawing. His strokes are drawn t px wide, as every line
    of the drawing, his filled marks solid, and his dots t px across; where he left a gap between
    strokes narrower than that widening would close (between the curls at the temple, the lines of
    the strap), a channel TRACE_GAP plate px wide stays open along its middle, unless the plate
    paints the gap black (THICK: he traced a thick line along both edges) or he marked it to be
    filled, when it is filled. The shapes his marks close off inside the crop he traced are his: one
    the plate paints dark there (FILL_T, HAIR) or he marked to be filled (the blood), inside the
    figure, is filled (the curls, the black inside the visor); in the others the plate's lines go.
    Within TRACE_NEAR plate px of his marks the plate's lines go too, but for its wide black that
    lies mostly outside all that (the helmet's bowl along his visor line), and where his stroke runs
    within TRACE_EDGE px of the outline it is the outline (he traced the face's outline on the
    plate's black line, a px or two outside the clay's edge, where the drawing's own outline runs).
    Returns the ink (less the blood, but for his lines across what he painted), his own ink (his
    strokes and the shapes filled), his dots, and the blood: the shapes he marked to be filled, with
    his strokes round them and the marks he filled in there, or the plate's streaks under what he
    painted."""
    H, W = fig.shape
    strokes, solids = np.zeros_like(fig), np.zeros_like(fig)
    angle = np.zeros(fig.shape, np.float32)   # each stroke px's direction (radians, mod pi)
    for line in part['lines']:
        P = up(line)
        for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
            rr, cc = draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))
            ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            strokes[rr[ok], cc[ok]] = True
            angle[rr[ok], cc[ok]] = np.arctan2(yb - ya, xb - xa) % np.pi
    for poly in part['solids']:
        solids |= lw.polygon_mask(fig.shape, np.array(up(poly), float))
    dots = np.zeros_like(fig)
    for x, y in up(part.get('dots', [])):
        if fig[int(round(y)), int(round(x))]:   # off the figure, a dot is a slip of his pen
            dots[draw.disk((y, x), t / 2, shape=fig.shape)] = True
    marked = {k: np.zeros_like(fig) for k in BLOOD}   # the areas he marked to be filled, by kind
    for k in BLOOD:
        for poly in part.get(k, []):
            marked[k] |= lw.polygon_mask(fig.shape, np.array(up(poly), float))
    marks = np.logical_or.reduce([marked[k] for k in BLOOD if k not in PAINTED])   # over his outlines
    painted = np.logical_or.reduce([marked[k] for k in PAINTED])
    bx0, by0, bx1, by1 = [(v - o) * UP for v, o in zip(part['box'], (X0, Y0, X0, Y0))]
    inbox = np.zeros_like(fig)
    inbox[by0:by1, bx0:bx1] = True
    to_stroke = ndi.distance_transform_edt(~strokes)
    # his pen, but at least 2 work px: a band narrower than that is a diagonal line's single px, and
    # the white on its two sides touched through it, so the gaps' skeleton ran along his stroke and
    # the channels cut it away (his finest pen, 0.89 plate px on the corpse's other hand)
    pen = max(part['pen'] * UP, 2.0)
    # the shapes he closed off, as he drew them (at his own pen width)
    lab, n = ndi.label(inbox & ~((to_stroke <= pen / 2) | solids))
    rim = np.concatenate([lab[by0, bx0:bx1], lab[by1 - 1, bx0:bx1], lab[by0:by1, bx0], lab[by0:by1, bx1 - 1]])
    size = np.bincount(lab.ravel(), minlength=n + 1)
    is_closed = np.ones(n + 1, bool)
    is_closed[0] = False
    is_closed[np.unique(rim)] = False
    for x, y in up(keep):   # a shape he closed whose plate lines stay
        is_closed[lab[int(round(y)), int(round(x))]] = False
    mean = np.bincount(lab.ravel(), weights=tone.ravel(), minlength=n + 1) / np.maximum(size, 1)
    cy, cx = [np.bincount(lab.ravel(), weights=c.ravel(), minlength=n + 1) / np.maximum(size, 1)
              for c in np.mgrid[0:H, 0:W]]
    curl = np.zeros(n + 1, bool)
    for hx0, hy0, hx1, hy1 in HAIR:
        curl |= (cx >= (hx0 - X0) * UP) & (cx < (hx1 - X0) * UP) & (cy >= (hy0 - Y0) * UP) & (cy < (hy1 - Y0) * UP)
    curl &= size < HAIR_MAX * UP * UP
    fill = np.bincount(lab.ravel(), weights=marks.ravel(), minlength=n + 1) > 0.5 * size
    is_dark = ((mean < FILL_T) | curl | fill) & \
        (np.bincount(lab.ravel(), weights=fig.ravel(), minlength=n + 1) > 0.5 * size)
    closed, filled = is_closed[lab], (is_closed & is_dark)[lab]
    # the gaps between his strokes that widening them to t would close: a channel stays open along
    # the middle of each, but for a long one the plate paints black, which is the inside of a thick
    # line he traced along both its edges, and one he marked: filled, as a shape he outlined
    white = inbox & ~((to_stroke <= pen / 2) | solids | filled)
    sk, half = morphology.skeletonize(white), ndi.distance_transform_edt(white)
    axis = sk & (half <= (t - pen) / 2 + 1)
    al, an = ndi.label(sk & (half <= t / 2 + 1), structure=np.ones((3, 3)))   # his edges a line apart
    length = np.bincount(al.ravel(), minlength=an + 1)
    thick = ((length > THICK_LEN * UP) &
             (np.bincount(al.ravel(), weights=tone.ravel(), minlength=an + 1) < THICK_T * length)) | \
        (np.bincount(al.ravel(), weights=marks.ravel(), minlength=an + 1) > 0.5 * length)
    thick[0] = False
    if thick.any():
        filled |= white & (ndi.distance_transform_edt(~thick[al]) <= t / 2 + 1)
        axis &= ~filled
    # a filled shape is the black he outlined, its edge where he drew it: the strokes round it stay
    # at his pen width. His other strokes are widened to t, but for the channels
    rims = strokes & within(filled, pen / 2 + 1.5)
    free = ndi.distance_transform_edt(~(strokes & ~rims)) <= t / 2
    lines = (free & ~within(axis, TRACE_GAP * UP / 2)) | within(rims, pen / 2)
    his = lines | solids | dots
    zone = closed | (ndi.distance_transform_edt(~(strokes | solids | dots)) <= TRACE_NEAR * UP)
    if partial:   # near his strokes, only the plate's lines that run along them go
        near = to_stroke <= TRACE_NEAR * UP
        zone = closed | within(solids | dots, TRACE_NEAR * UP) | (near & along(ink, strokes, angle, t))
        # and what is left there must run on beyond them, as a line that crosses his does: a crumb
        # lying all within that distance goes
        left, n = ndi.label(ink & ~zone, structure=np.ones((3, 3)))
        out = np.bincount(left.ravel(), weights=(~near).ravel(), minlength=n + 1) > 0
        out[0] = True
        zone |= ~out[left]
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
    blood = np.zeros_like(fig)
    if painted.any():   # painted with no outline: the plate's streak under his paint, and its lines
        # there, in place of the plate's ink
        reach = ndi.binary_dilation(painted, iterations=4 * UP)   # its dark edge too: no black outline
        streak = reach & fig & (ndi.gaussian_filter(tone, 0.75 * UP) < BLOOD_T)
        blood |= ndi.binary_fill_holes(morphology.remove_small_objects(streak, max_size=4 * UP * UP))
        blood |= ink & painted & ~(his | filled)
        ink &= ~(reach & ~(his | filled))
        to_paint = ndi.distance_transform_edt(~painted)
        pl, _ = ndi.label(ink & ~(his | filled))
        ids = np.unique(pl[(to_paint <= RIM * UP) & (pl > 0)])
        if len(ids):
            hug = ids[np.asarray(ndi.median(to_paint, labels=pl, index=ids)) <= RIM * UP]
            ink &= ~np.isin(pl, hug)
    if marks.any():   # the shapes and gaps filled for his marks, his strokes round them, each mark
        # he filled in that reaches them, and the bits of their outline his marks just miss
        to_mark = ndi.distance_transform_edt(~marks)
        fl, _ = ndi.label(filled)
        b = np.isin(fl, np.unique(fl[filled & marks])) | (his & ~dots & (to_mark <= pen + 2))
        sl, _ = ndi.label(solids)
        b |= np.isin(sl, np.unique(sl[(to_mark <= TRACE_NEAR * UP) & solids]))
        bits, _ = ndi.label((his | filled) & ~dots & ~b)
        size = np.bincount(bits.ravel())
        near = np.unique(bits[ndi.binary_dilation(b, iterations=2) & (bits > 0)])
        b |= np.isin(bits, near[size[near] < BIT * UP * UP])
        blood |= b
        ink &= ~b
    return ink, his | filled, dots, blood


def add_tone(svg, blood, tone, box):
    """Add the blood to the drawing written by lw.trace_svg (box: the crop box it returned): a wash
    in the line colour whose opacity follows the plate's darkness under it (BLEND_*), in steps, each
    step's area drawn over the one below at the opacity that brings the total there to the step's
    (so no seam shows between steps): paths of class "tone", between the body and the lines,
    traced at the ink's own size, as the lines are (weight "drawn"): traced at another size, the
    wash fell out of register with the lines."""
    x0, y0, x1, y1 = box
    b, g, s = blood[y0:y1, x0:x1], tone[y0:y1, x0:x1], BLEND_SIGMA * UP
    dark = ndi.gaussian_filter(np.where(b, g, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (t0, t1), (a0, a1) = BLEND_T, BLEND_A
    alpha = a0 + (a1 - a0) * np.clip((t0 - dark) / (t0 - t1), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, BLEND_STEP):
        m = b & (alpha >= a - BLEND_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


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
    if 'trace_11_priam_feet' in TRACES:   # Priam's feet, under the fallen zone: John traced them;
        feet = TRACES['trace_11_priam_feet']   # what hangs below his outline is the fallen man's hair
        cut = (cut & ~traced_area(feet, g.shape)) | below_trace(feet, g.shape)

    # the group: the light area left, joined to the seeds
    lab, _ = ndi.label(~ground & ~cut)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS.values()}
    assert 0 not in keep, keep
    fig = np.isin(lab, list(keep))
    held = ndi.binary_fill_holes(fig) & ground & ~cut    # ground the group closes in stays open
    fig = ndi.binary_fill_holes(fig) & ~held & ~cut      # paint inside the group stays its own
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    erase = np.zeros_like(fig)
    for poly in ERASE:   # John's rings: the slivers of figure on the sword hand
        ring = within(lw.polygon_mask(g.shape, np.array(up(poly), float)), 2 * UP)
        fig &= ~(ring & (gs < GROUND_T))
        erase |= ring
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
    # (FAINT), long pieces only, away from the black and from the outline, and each is redrawn
    # along its centre, WEIGHT wide (centre_lines): they are never painted areas, and at the
    # filter's own width (4-6 px, uneven) they came out heavier than the black lines, and beaded
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
    ink = even_lines(black, t, 3 * UP) | centre_lines(faint, t, 3 * UP, 2 * t) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]   # specks of grain; a small curl stays
    body, dots, blood = fig, np.zeros_like(fig), np.zeros_like(fig)
    if TRACES:
        tone = np.asarray(Image.fromarray(den).resize((W, H), Image.BICUBIC), np.float32)
        wide = black & ndi.binary_dilation(ndi.binary_opening(black, structure=morphology.disk(int(np.ceil(t / 2)))),
                                           iterations=2)
        his_all = np.zeros_like(fig)
        for name, part in TRACES.items():
            part = dict(part, lines=part['lines'] + JOINS.get(name, []))
            ink, his, his_dots, his_blood = apply_trace(part, ink, edge, fig, tone, wide, t,
                                                        partial=name in PARTIAL, keep=KEEP.get(name, ()))
            body = body | (his & ndi.binary_dilation(fig, iterations=TRACE_EDGE * UP))   # clay under his outline
            dots |= his_dots
            blood |= his_blood
            his_all |= his
        # Priam's chest and the altar: the smear is blood; the pleats John traced through it are lines
        pleats = np.zeros_like(fig)
        for line in CHEST_PLEATS:
            P = up(line)
            for (xa, ya), (xb, yb) in zip(P[:-1], P[1:]):
                pleats[draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))] = True
        to_pleat = ndi.distance_transform_edt(~pleats)
        near_his = ndi.distance_transform_edt(~his_all) <= TRACE_NEAR * UP   # his traces keep their ground
        for ring in [CHEST] + ALTAR:
            chest = lw.polygon_mask(fig.shape, np.array(up(ring), float)) & fig
            smear = chest & (ndi.gaussian_filter(tone, 0.75 * UP) < BLOOD_T)
            if ring is CHEST:
                smear = ndi.binary_opening(smear, structure=morphology.disk(int(round(CHEST_W / 2 * UP))))
            smear = morphology.remove_small_objects(smear, max_size=CHEST_MIN * UP * UP)
            under = ndi.distance_transform_edt(~smear) <= REACH * UP
            plate = ndi.binary_closing((black | faint) & chest, structure=np.ones((PLEAT_GAP * UP, 1), bool))
            plate = centre_lines(plate & chest & ~ndi.binary_dilation(smear, iterations=UP), t, 3 * UP, 2 * t)
            plate = (plate | edge) & ~((to_pleat <= DUP * UP) & under) & ~near_his
            ink = (ink & ~(chest & ~his_all)) | (plate & chest) | ((to_pleat <= t / 2) & under & chest)
            blood |= smear
        # the lines the drawing missed, snapped to the plate's own
        gsm = ndi.gaussian_filter(g, UP)
        r = SNAP_R * UP
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        disk = xx ** 2 + yy ** 2 <= r * r
        missed = np.zeros_like(fig)
        for line in MISSED:
            P = np.array(up(line), float)
            s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
            Q = np.column_stack([np.interp(np.linspace(0, s[-1], max(int(s[-1] / (SNAP_STEP * UP)), 1) + 1), s, P[:, k])
                                 for k in (0, 1)])
            for q in Q:
                x, y = int(round(q[0])), int(round(q[1]))
                win = np.where(disk, gsm[y - r:y + r + 1, x - r:x + r + 1], np.inf)
                iy, ix = np.unravel_index(np.argmin(win), win.shape)
                if gsm[y, x] - win[iy, ix] > SNAP_D:
                    q[:] = (x + ix - r, y + iy - r)
            if len(Q) > 2:   # smooth the snapped points (ends stay)
                Q[1:-1] = (Q[:-2] + 2 * Q[1:-1] + Q[2:]) / 4
            for (xa, ya), (xb, yb) in zip(Q[:-1], Q[1:]):
                missed[draw.line(int(round(ya)), int(round(xa)), int(round(yb)), int(round(xb)))] = True
        ink |= within(missed, t / 2)
        for poly in BLACK:
            ink |= lw.polygon_mask(fig.shape, np.array(up(poly), float))
    if erase.any():   # in John's rings, the ink left stranded off the figure, and its clay
        ink &= ~(erase & ~within(fig, t))
        body &= ~(erase & ~fig)
    info = lw.trace_svg(
        ink, OUT, body=body, open_holes=held,
        weight="drawn",   # drawn at WEIGHT already, a px apart in places: traced as it is, at its own size
        # (resampled and re-weighted, the blur closed the px between close lines: the kilt's hems ran together)
        dots=dots,        # his dots, a line wide: under potrace's speck limit at this weight
        title='Neoptolemos killing Priam, who sits on the altar with the dead Astyanax across his knees',
        desc='Line drawing after Karl Reichhold\'s drawing of the Vivenzio hydria by the Kleophrades Painter '
             '(Naples), in Furtwängler and Reichhold, Griechische Vasenmalerei I (1904), Taf. 34; '
             'cut out and retraced.')
    if blood.any():
        add_tone(OUT, blood, tone, info['box'])
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
