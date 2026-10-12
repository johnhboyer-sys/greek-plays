"""Prometheus Bound: Atlas holding up the sky and Prometheus bound to a column, the eagle at his breast, from the
tondo of a Laconian black-figure cup by the Arkesilas Painter, c. 560-550 BC: Vatican, Museo Gregoriano Etrusco
16592. From Daderot's photo on Wikimedia Commons (public domain; taken 2019-04-06):
https://commons.wikimedia.org/wiki/File:Prometheus_and_Atlas,_Laconian_black-figure_kylix,_by_the_Arkesilas_Painter,_560-550_BC,_inv._16592_-_Museo_Gregoriano_Etrusco_-_Vatican_Museums_-_DSC01069.jpg
(4468 x 3568).
John's pick (Plate Picks 4-6Va, 2026-10-08); what it holds (2026-10-10): everything painted inside the innermost
border ring (Atlas with the sky, the eagle, Prometheus and his column, the snake, the blood, and below the ground
line the capital between two lotus sprays); the rings left out.

The photo is taken at a slant: the tondo's outer edge (clay against the black band round it), found on 1440 rays
from the centre at the half-maximum between the clay and the black, fits an ellipse within 0.43 px (median, the
points off it by more than 2.5 medians dropped in five rounds: figures touching the edge). The ellipse is mapped to
a circle by the affine map that stretches its minor axis (TONDO: centre, axes, angle; ratio 0.976, about 12.5
degrees of slant). The tondo is shallow and the circle's residual is under half a px, so the cup's curve is left as
it is. This step runs in numpy and OpenCV (as vase_unroll.py), not PhotoCraft.

The crack: a ring of pale filler round a piece glued back in (the top of the sky, Atlas's head and raised arm, the
eagle's upper wing), traced by a least-cost path on the photo's grain through hand-placed points (CRACK). John,
2026-10-10: "Pay attention to crack and fill in what is missing due to it"; and 2026-10-02, cracks leave no line.
Inside it the photo is not read: the black, the ground and the red are carried across from both sides (a harmonic
fill of each mask's signed distance), and the incisions it broke are joined across it.

Made with PhotoCraft (John, 2026-10-07): every image step after the slant runs in `photocraft-cli` (0.2.0): the crop,
the enlargement, the grey, the channels (Channel Mixer), the blurs, Minimum and Maximum. numpy only combines the
masks PhotoCraft made and measures. The SVG is written in the house format directly, as hecuba.py.

Photo -> drawing, black-figure, drawn as a silhouette (John's choice, 2026-10-10, from a test on Prometheus's head
and the eagle, as Hecuba), the added red as a grey wash:
  - Ground: the clay (warm, red less blue over WARM_T, and lighter than CLAY_L), its large areas.
  - The figures: all else inside the ring. The glaze's glare photographs light and blue: it is black (red less
    blue reads 0 there).
  - Open in the black: the incisions, light thin marks (a white top-hat on the grey smoothed along its strokes)
    that are not blue (glare).
  - The added red: red well over green, darker than RED_L: a `tone` path at RED_OP.
  - Dark theme: the figures' area is clay, a RIM wider than the black.

    python3 docs/redesign/drawings/tools/prometheus.py vatican-16592-daderot.jpg [qa.png]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "prometheus.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# the tondo's outer edge in the photo: centre (x, y), axes (along ANGLE, across), ANGLE (degrees), photo px
TONDO = ((2198.73, 1767.92), (2813.74, 2882.57), 5.50)
N = 2960                                   # the round image: N x N, the tondo's centre at N/2, radius R0
# the border (John, 2026-10-10: "add a border to the circle. It looks bad without the band"): the three painted
# rings round the tondo, each fitted as a circle to the darkest px across it on 1440 rays (sub-px; the points off
# it by more than 2.5 medians dropped): centres within 2.5 px of each other, radii 1380, 1402.5 and 1423 (the
# painter's rings wobble by up to 4 px). Drawn as circles about RINGS_C, RING_W round px wide; inside the first
# ring's inner edge, the picture; outside it, out
RINGS_C, RINGS_R, RING_W = (1476.0, 1480.0), (1380.0, 1402.5, 1423.0), 5.0
R_IN = RINGS_R[0] - RING_W / 2
R_OUT = RINGS_R[-1] + RING_W / 2
X0 = Y0 = int(min(RINGS_C) - R_OUT) - 4
X1 = Y1 = int(max(RINGS_C) + R_OUT) + 5
UP = 2                                     # work at 2x the round image's px


def round_image(src):
    """The photo with the slant taken out: the tondo's ellipse mapped to a circle (numpy / OpenCV)."""
    (ex, ey), (w, h), ang = TONDO
    r0 = max(w, h) / 2
    t = np.deg2rad(ang)
    rot = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    m = rot.T @ np.diag([r0 / (w / 2), r0 / (h / 2)]) @ rot
    a = np.zeros((2, 3))
    a[:, :2] = m
    a[:, 2] = np.array([N / 2, N / 2]) - m @ np.array([ex, ey])
    im = cv2.imread(str(src), cv2.IMREAD_COLOR)
    return cv2.warpAffine(im, a, (N, N), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


# ---------------------------------------------------------------- the crack
# guide points (round px) for the least-cost path round the ring of filler, on the photo's grain (the filler is
# speckled: the grey's local deviation from its 2 px blur, over 7 px, reads 8-20 on it, 2-4 beside it); each point
# snapped to the grainiest px within CRACK_SNAP
CRACK = [(1200, 115), (1433, 107), (1667, 115), (1917, 165), (2050, 215), (2150, 290), (2192, 407), (2108, 490),
         (2000, 523), (1933, 673), (1883, 823), (1767, 940), (1533, 1057), (1367, 1082), (1200, 1073), (1000, 990),
         (833, 807), (717, 623), (733, 423), (850, 273), (1050, 157)]
CRACK_SNAP = 30
CRACK_W = 30                               # round px: the filler lies within this of the path...
CRACK_GRAIN = 0.5                          # ...where its grain is over this share of the grain on the path
CRACK_PAD = 4                              # round px: and this beside it (its pale edge passed for an incision)
# B: a patch of lost surface with fine cracks under Atlas's hand; C: a hairline crack across his forearm (round px)
PATCH_B = [(1085, 985), (1150, 950), (1250, 925), (1330, 915), (1400, 925), (1428, 960), (1428, 1065), (1085, 1065)]
CRACK_C = [(1290, 735), (1296, 770), (1301, 805), (1304, 840), (1306, 868)]
CRACK_C_W = 8


def crack_mask(L1):
    """The crack, B and C, at round px (L1: the round image's grey, from PhotoCraft)."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.fromarray(np.clip(L1, 0, 255).astype(np.uint8)).save(t / "g.png")
        pc(t / "g.png", t / "b.png", ("filter.blur.gaussianBlur", {"radius": 2}))
        hp = L1 - grey(t / "b.png")
    grain = ndi.gaussian_filter(np.sqrt(ndi.uniform_filter(hp * hp, 7)), 3)
    q = []
    for x, y in CRACK:
        w = grain[y - CRACK_SNAP:y + CRACK_SNAP + 1, x - CRACK_SNAP:x + CRACK_SNAP + 1]
        j = np.unravel_index(np.argmax(w), w.shape)
        q.append((x - CRACK_SNAP + j[1], y - CRACK_SNAP + j[0]))
    path = lw.livewire(1.0 / (0.02 + np.clip(grain / 12, 0, 1) ** 2), q, closed=True)
    on = np.zeros(L1.shape, bool)
    ij = path[:, ::-1].astype(int)
    on[ij[:, 0], ij[:, 1]] = True
    d = ndi.distance_transform_edt(~on)
    band = (d <= CRACK_W) & (grain > CRACK_GRAIN * np.median(grain[on]))
    band = ndi.binary_closing(band, structure=morphology.disk(4)) & (d <= CRACK_W)
    band = ndi.binary_propagation(on & band, mask=band)
    band = ndi.binary_dilation(band, structure=morphology.disk(CRACK_PAD)) & (d <= CRACK_W + CRACK_PAD)
    band |= lw.polygon_mask(L1.shape, np.array(PATCH_B, float))
    c = np.zeros(L1.shape, bool)
    P = np.array(CRACK_C, float)
    seg = np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])])
    c[seg[:, 1].astype(int), seg[:, 0].astype(int)] = True
    band |= ndi.distance_transform_edt(~c) <= CRACK_C_W / 2
    return band


def harmonic_fill(mask, hole, free):
    """mask carried across `hole`: its signed distance (to the other kind, over the known px), solved inside the
    hole as a harmonic function of the values round it (Laplace's equation, Dirichlet on the known px; px in `free` are not read, as if mirrored),
    then cut at 0. A boundary that crosses the hole comes out joined smoothly; one that ends at it runs on."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    # (the px along the hole's edge, and islands of known px inside it, join the hole: single px there read -1
    # beside a band of +20 and tipped the fill)
    hole = ndi.binary_dilation(hole, iterations=2) & ~free
    lab, n = ndi.label(~hole & ~free)
    hole |= (np.bincount(lab.ravel(), minlength=n + 1) < 200)[lab] & (lab > 0)
    # (each known px's distance to the nearest known px of the other kind, the hole not counted: measured to the
    # hole's edge instead, every px beside it read 1 and a stray speck across it tipped the fill)
    pos = ndi.distance_transform_edt(mask | hole | free)
    neg = ndi.distance_transform_edt(~mask | hole | free)
    sd = np.clip(np.where(mask, pos, -neg), -20, 20)
    unk = hole & ~free
    # (pieces of the hole that touch no known px, only the free px, have no values to carry: they stay as they are)
    lab, n = ndi.label(unk)
    known = ndi.binary_dilation(~hole & ~free) & unk
    unk &= (np.bincount(lab[known], minlength=n + 1) > 0)[lab] & (lab > 0)
    idx = -np.ones(mask.shape, int)
    ys, xs = np.nonzero(unk)
    idx[ys, xs] = np.arange(len(ys))
    rows, cols, vals = [], [], []
    rhs = np.zeros(len(ys))
    diag = np.zeros(len(ys))
    H, W = mask.shape
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ny, nx = ys + dy, xs + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        ny, nx, k = ny[ok], nx[ok], np.nonzero(ok)[0]
        use = ~free[ny, nx]
        ny, nx, k = ny[use], nx[use], k[use]
        diag[k] += 1
        j = idx[ny, nx]
        inner = j >= 0
        rows += list(k[inner]); cols += list(j[inner]); vals += [-1.0] * int(inner.sum())
        np.add.at(rhs, k[~inner], sd[ny[~inner], nx[~inner]])
    rows += list(range(len(ys))); cols += list(range(len(ys))); vals += list(diag)
    A = coo_matrix((vals, (rows, cols)), shape=(len(ys), len(ys))).tocsr()
    out = sd.copy()
    out[ys, xs] = spsolve(A, rhs)
    assert np.isfinite(out[ys, xs]).all()
    return np.where(unk, out > 0, mask)


# ---------------------------------------------------------------- the drawing
# clay: lighter than CLAY_K of the clay's own grey round it (the light falls off toward the rim: the clay reads grey
# 150 in the middle, 30-90 at the rim), not blue (red less blue over CLAY_W: the glare), and not red. The clay's
# grey round it: the mean grey over BG_R round px of the px that are surely clay (orange: red less blue over 40 and
# over 0.4 of the grey, green less blue over 12), the gaps filled from BG_R2
CLAY_K, CLAY_W, BG_R, BG_R2 = 0.66, 15, 40, 150
# the figures' edge: within EDGE_BAND round px of it, ground is lighter than halfway between the clay and the black
# round it (their mean grey over EDGE_R round px, each over its own side): the colour channels are at half the
# photo's px (JPEG), and an edge drawn from them came out ragged
EDGE_BAND, EDGE_R, EDGE_BLUE = 4, 6, 10
AUTO_GROUND = 400                          # round px^2: clay areas this large are ground
WIDE_CLAY = 2.5                            # round px: ground grows into clay this wide
FIG_MIN = 500                              # round px^2: smaller dark pieces are specks (but red pieces stay)
# below the ground line (y > FLOOR, round px) the glaze of the capital and the lotus photographs pale and warm in
# its glare, as light as the clay, and the lotus brown: there the clay must also be saturated (the photo's colour,
# blurred 2 px: clay 0.45-0.9, the glare 0.33-0.39, the lotus 0.5-0.6 against clay 0.75-0.9), over FLOOR_SAT and
# over FLOOR_K of the most saturated px within FLOOR_R round px (the clay beside it), smoothed over FLOOR_R
FLOOR, FLOOR_SAT, FLOOR_K, FLOOR_R = 2205, 0.42, 0.8, 25
# the added red: red less green over RED_RG, green less blue under RED_GBK of that (the red has no yellow: 0-0.3;
# the clay 0.6-0.75, in shadow too), darker than RED_L; pieces over RED_MIN
RED_RG, RED_GBK, RED_L, RED_MIN = 30, 0.45, 140, 80
# the dark red over the black (Atlas's beard, Prometheus's hair): red less green over DARK_RG (the black 2-6, the
# beard 17-18), darker than DARK_L, no yellow as above; opened by DARK_OPEN round px, pieces over DARK_MIN
DARK_RG, DARK_L, DARK_OPEN, DARK_MIN = 12, 90, 3, 300
# only in these boxes (round px: Atlas's beard): elsewhere it took patches of the column's
# glaze, worn brown in the glare
DARK_BOXES = [(1050, 680, 1240, 900)]
RED_OP = 0.45
# incisions: the white top-hat (radius MARK_R round px) on the grey smoothed along its strokes (Motion Blur
# ORIENT_D long at every ORIENT_STEP degrees, as hecuba.py), hysteresis MARK_T / 2 to MARK_T; not blue (blue less
# red under MARK_BR: the glare); not within EDGE_CLEAR of the figures' edge; pieces at least MARK_LEN long
MARK_R, MARK_T, MARK_BR = 2, 12, 40
ORIENT_D, ORIENT_STEP = 4, 15
GLARE_BR, GLARE_K, GLARE_LEN = 35, 2.2, 25
GLARE_GROW, GLARE_EDGE, GLARE_HAT, GLARE_L, GLARE_W, GLARE_WLEN = 6, 40, 10, 100, 20, 12
EDGE_CLEAR, FLOOR_CLEAR = 4, 9
MARK_MIN, MARK_LEN = 8, 7
LINE_W = 1.6                               # round px: the thinnest mark
CLAY = "#c4b294"                           # the body's fill in both themes (as clouds.svg)
RIM = 1.5                                  # round px: the clay round the black on the dark theme
SMOOTH = 0.6                               # round px: every edge smoothed (Gaussian Blur, Threshold at half)
# worn glaze that photographs as clay inside a figure (round px polygons): black (Atlas's palm on the sky)
WORN = [[(1590, 468), (1608, 452), (1640, 434), (1672, 419), (1690, 417), (1693, 432), (1670, 452), (1642, 472),
         (1616, 492), (1598, 501), (1587, 490)]]
# the sky's top, between these angles (degrees about RINGS_C, y down; its ends at the ring are at -134 and -53):
# black out to the first ring, over the last SKY_W round px
SKY_SPAN, SKY_W = (-128, -60), 30
SPECK = 200
FLOOR_CLOSE, RING_HUG = 3, 35
DROP = [(2242, 2587)]                      # round px: a stain on the clay right of the capital, below the lotus
SEEDS = [(1000, 1500), (1900, 1500), (1480, 2500)]


def pc_mask(m, *steps):
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "m.png", Path(td) / "o.png"
        Image.fromarray(m.astype(np.uint8) * 255).save(a)
        pc(a, b, *steps)
        return grey(b) >= 128


def smooth(m, r):
    return pc_mask(m, ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": r * UP}),
                   ("image.adjustments.threshold", {"level": 128}))


def along(t, src, out):
    """t/src smoothed along its own strokes: PhotoCraft's Motion Blur ORIENT_D long at every ORIENT_STEP degrees;
    numpy picks, per px, the blur at the strokes' direction (the structure tensor's, as hecuba.py)."""
    g = grey(t / src)
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(t / src, t / f"o{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    mb = np.stack([grey(t / f"o{a}.png") for a in angs])
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    Image.fromarray(np.clip(np.take_along_axis(mb, i[None], 0)[0], 0, 255).round().astype(np.uint8)).save(t / out)


def channels(src):
    """The round image, then PhotoCraft: the crop at UP and its channels."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        cv2.imwrite(str(t / "round.png"), round_image(src))
        pc(t / "round.png", t / "g1.png", ("image.mode.grayscale", None))
        L1 = grey(t / "g1.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "round.png", t / "up.png", ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        mix = lambda name, gray, r: pc(t / "up.png", t / name, ("image.adjustments.channelMixer",
                                                                 {"gray": gray, "monochrome": True}),
                                       ("filter.blur.gaussianBlur", {"radius": r * UP}))
        mix("W.png", [100, 0, -100, 0], 0.5)
        mix("RG.png", [100, -100, 0, 0], 0.8)
        mix("BR.png", [-100, 0, 100, 0], 1.0)
        mix("Wc.png", [100, 0, -100, 50], 0.5)          # red less blue, offset by half the range (no clipping)
        mix("GB.png", [0, 100, -100, 0], 0.8)
        pc(t / "up.png", t / "up_s.png", ("filter.blur.gaussianBlur", {"radius": 2 * UP}))
        rgb = np.asarray(Image.open(t / "up_s.png").convert("RGB")).astype(np.float32)
        sat = (rgb.max(-1) - rgb.min(-1)) / (rgb.max(-1) + 1)
        along(t, "L.png", "Lo.png")
        along(t, "Wc.png", "Wco.png")
        pc(t / "Lo.png", t / "Lopen.png", ("filter.other.minimum", {"radius": MARK_R * UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": MARK_R * UP, "preserve": "roundness"}))
        pc(t / "Wco.png", t / "Wopen.png", ("filter.other.minimum", {"radius": MARK_R * UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": MARK_R * UP, "preserve": "roundness"}))
        return dict(L1=L1, L=grey(t / "L.png"), what=grey(t / "Wco.png") - grey(t / "Wopen.png"), Wc=grey(t / "Wc.png") - 127.5, W=grey(t / "W.png"), RG=grey(t / "RG.png"), BR=grey(t / "BR.png"), GB=grey(t / "GB.png"), sat=sat,
                    hat=grey(t / "Lo.png") - grey(t / "Lopen.png"))


def clay_grey(L, sure, f=8):
    """The clay's grey round each px (CLAY_K): measured on a grid f work px apart, mean grey of the sure clay over
    BG_R round px, where that has too little clay, over BG_R2."""
    H, W = L.shape
    h, w = -(-H // f), -(-W // f)
    pad = lambda a: np.pad(a, ((0, h * f - H), (0, w * f - W)), mode='edge')
    s = pad(sure.astype(np.float32)).reshape(h, f, w, f).mean((1, 3))
    v = pad(np.where(sure, L, 0).astype(np.float32)).reshape(h, f, w, f).mean((1, 3))
    out = None
    for r in (BG_R, BG_R2):
        m = ndi.gaussian_filter(s, r * UP / f)
        g = ndi.gaussian_filter(v, r * UP / f) / np.maximum(m, 1e-6)
        out = g if out is None else np.where(m0 > 0.03, out, g)
        m0 = m if out is g else m0
    return ndi.zoom(out, f, order=1)[:H, :W]


def keep_big(m, n, keep=None):
    lab, _ = ndi.label(m)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    ok = sz > n
    if keep is not None:
        ok |= np.bincount(lab[keep], minlength=len(sz)) > 0
        ok[0] = False
    return ok[lab]


def write_svg(lines, body, tone, out, title, desc):
    """The house format (as hecuba.py): 1000 units tall, the body under a `tone` path (the red) under the lines."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    td, _ = lw.potrace_d(tone[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="{CLAY}" stroke="none" d="{bd}"/>'
                   f'<path class="tone" fill="currentColor" fill-opacity="{RED_OP}" stroke="none" d="{td}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


# incisions the crack broke, joined across it (round px, each a pair of line ends read off a map of the line ends
# beside the crack; the auto-pairing of facing ends joined the wrong locks of Atlas's hair): drawn JOIN_W wide
JOINS = [((768, 800), (810, 738)), ((797, 840), (853, 772)), ((835, 870), (870, 798))]   # Atlas's hair locks
JOIN_W = 2.6


# the eyes, drawn on points read off the photo's pixel grid at 7-8x (round px; John's rule, eyes never heavy): the
# found incisions came out broken there. Inside EYE_R round px of each ring's centre the light marks are these
# closed rings and strokes alone, EYE_W wide
EYES = {
    "Atlas": [[(1161.1, 664.8), (1167.2, 654.6), (1181.5, 648.5), (1196.8, 652.6), (1207, 662.8), (1212.1, 678.1),
               (1204.9, 688.3), (1191.7, 693.4), (1176.4, 694.4), (1164.1, 689.3), (1160, 675), (1161.1, 664.8)]],
    "Prometheus": [[(2306.5, 672), (2315.5, 664), (2325.5, 662), (2336.5, 666), (2346.5, 676), (2353.5, 690),
                    (2358.5, 700), (2352.5, 710), (2341.5, 716), (2326.5, 717), (2315.5, 712), (2307.5, 703),
                    (2304.5, 690), (2305.5, 678), (2306.5, 672)], [(2297.5, 709), (2308.5, 706)]],
    "eagle": [[(2083.1, 964.3), (2093.3, 956.1), (2108.6, 954.1), (2121.8, 960.2), (2129, 972.5), (2126.9, 984.7),
               (2115.7, 992.9), (2101.4, 992.9), (2089.2, 986.7), (2082, 976.5), (2083.1, 964.3)],
              [(2085.5, 967.5), (2073.5, 977.5), (2064.5, 984.5), (2079.5, 987.5), (2093.5, 989.5)]],
}
# (each ring placed first by eye on the grid, then moved and scaled to lie on the photo's pale ring: the shift and
# scale, within 7 round px and 12%, at which the photo's mean grey along the ring is highest)
EYE_R, EYE_W = 34, 2.4


# the incisions between the fingers of Prometheus's hanging hand, too faint in its glare to be found whole: placed on
# the warm top-hat's streaks (round px), drawn EYE_W wide
HAND = [[(2258, 1920), (2246, 1950), (2234, 1980), (2222, 2008), (2212, 2030)],
        [(2276, 1928), (2264, 1955), (2251, 1985), (2240, 2012), (2232, 2030)]]


# the two added-red bars across the capital's abacus: in its glare their left parts read only as darker than the
# glaze, with no hue of their own. Each a straight line fitted to the darkest row in every 25th column (round px;
# within 4.7 px), from end to end, drawn as wash at its measured width
RED_BARS = [([(1195, 2296.3), (1767, 2310.3)], 14), ([(1215, 2426.1), (1687, 2441.7)], 17)]


# the ropes binding Prometheus to the column (John, 2026-10-10: "Those are big thick rope lines"; "They have
# distinct separation"): his centreline for each strand (prometheus_ropes.json, round px). The rope is the red
# (red less green over ROPE_RG, darker than ROPE_L) within ROPE_MAX round px of his lines, its incisions closed
# (ROPE_CLOSE round px) and its holes filled; each px of it goes to the nearest line; between neighbouring strands
# a black line ROPE_SEP wide, where their areas meet (John, pass 2: drawn open, the separations were "too faint"). Bands of a fixed width along his lines left black between
# the strands where the photo has only the incisions; in the glare, where the red does not show, the strand is at
# least a band ROPE_W round px wide along his line
ROPES = json.loads((Path(__file__).parent / "prometheus_ropes.json").read_text())["strands"]
ROPE_RG, ROPE_L, ROPE_MAX, ROPE_CLOSE, ROPE_SEP, ROPE_W = 22, 135, 14, 4, 3.5, 22


def ropes(shape, L, RG, ground):
    """The rope strands (one label each, 0 elsewhere) and the open lines between them, at UP."""
    seeds = np.zeros(shape, np.int32)
    for k, pts in enumerate(ROPES, 1):
        seeds[strokes(shape, [pts], 1.0)] = k
    d, (iy, ix) = ndi.distance_transform_edt(seeds == 0, return_indices=True)
    near = seeds[iy, ix]
    zone = d <= ROPE_MAX * UP
    rope = (RG > ROPE_RG) & (L < ROPE_L) & zone & ~ground
    rope = ndi.binary_closing(rope, structure=morphology.disk(ROPE_CLOSE * UP)) & zone & ~ground
    rope = ndi.binary_opening(ndi.binary_fill_holes(rope), structure=morphology.disk(2 * UP))
    rope |= d <= ROPE_W / 2 * UP           # (in the glare the red does not show: a band along each line at least)
    rope = smooth(rope, 1.0) & zone & ~ground
    lab = np.where(rope, near, 0)
    edge = np.zeros(shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        e = (lab[:shape[0] - dy, :shape[1] - dx] != lab[dy:, dx:]) & (lab[:shape[0] - dy, :shape[1] - dx] > 0) \
            & (lab[dy:, dx:] > 0)
        edge[:shape[0] - dy, :shape[1] - dx] |= e
    sep = (ndi.distance_transform_edt(~edge) <= ROPE_SEP / 2 * UP) & (lab > 0)
    return lab, sep


# areas painted solid red edge to edge (John, pass 2: the eagle's wing "is a well defined area which is filled edge
# to edge with red"; "Whole beard shape is solid one color"). Each a polygon (round px) drawn a little outside the
# incisions that bound the area, read off the photo's grid: the eagle's red coverts, the brown-red band above them
# (the crack crosses between), the red stripe low on its wing (no incisions: the polygon is its edge), Atlas's
# beard. Inside each, the figure less the incisions longer than SOLID_SCRATCH round px is cut into pieces; the pieces
# at least SOLID_FRAC red are the area, its holes filled and its edge smoothed (SOLID_SMOOTH); the scratches in it go
SOLID_AREAS = [
    # (the band's left part, beyond John's outline: WING)
    [(1430, 985), (1500, 950), (1600, 905), (1640, 893), (1640, 985), (1600, 988), (1500, 1012), (1440, 1022)],
    [(1440, 1320), (1475, 1316), (1505, 1350), (1530, 1395), (1560, 1440), (1600, 1478), (1606, 1510), (1570, 1516),
     (1540, 1490), (1510, 1450), (1480, 1410), (1455, 1370), (1438, 1340)],
    # (the beard: along its ringing incision, read at 3x)
    [(1090, 642), (1100, 663), (1114, 690), (1135, 718), (1147, 739), (1149, 767), (1152, 798), (1157, 829), (1159, 861), (1152, 882), (1135, 888), (1111, 879), (1087, 864), (1062, 840), (1038, 809), (1017, 777), (1010, 749), (1020, 725), (1038, 700), (1055, 680), (1072, 659)],
]
SOLID_SCRATCH, SOLID_FRAC, SOLID_SMOOTH = 25, 0.3, 1.5
# John's outline of the eagle's red coverts and the brown-red band above them, one area across the crack between
# them (2026-10-11, "Wing area": prometheus_wing.json, round px), open at its left, where the band runs on: closed
# straight down there. Red whole inside it, edge to edge
WING = json.loads((Path(__file__).parent / "prometheus_wing.json").read_text())["outline"]


def solid_red(red, fig, marks, px, py):
    """red, made solid in SOLID_AREAS (at UP), and the scratches inside them dropped. Returns red and marks."""
    out = red.copy()
    lab, n = ndi.label(marks)
    ext = np.zeros(n + 1)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        ext[k] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
    long_marks = (ext >= SOLID_SCRATCH * UP)[lab] & marks
    for pts in SOLID_AREAS:
        poly = lw.polygon_mask(red.shape, np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float))
        room = poly & fig & ~ndi.binary_dilation(long_marks, iterations=UP)
        pl, m = ndi.label(room)
        frac = np.bincount(pl[red & room], minlength=m + 1) / np.maximum(np.bincount(pl.ravel(), minlength=m + 1), 1)
        area = (frac > SOLID_FRAC)[pl] & (pl > 0)
        area = smooth(ndi.binary_fill_holes(area), SOLID_SMOOTH) & fig & poly
        marks = marks & ~(area & ~long_marks)
        out = (out & ~poly) | (area & ~marks)
    poly = lw.polygon_mask(red.shape, np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in WING], float))
    area = smooth(poly, SOLID_SMOOTH) & fig
    marks = marks & ~area
    out = (out & ~poly) | area
    return out, marks


def strokes(shape, lines, w):
    """Polylines (round px) drawn w round px wide, at UP; those of four points or more as a smoothing spline through
    them (closed when the first point is the last)."""
    from scipy.interpolate import splev, splprep
    m = np.zeros(shape, bool)
    for pts in lines:
        P = np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)
        if len(P) >= 4:
            closed = bool(np.all(P[0] == P[-1]))
            tck, _ = splprep((P[:-1] if closed else P).T, s=len(P) * (0.6 * UP) ** 2, per=closed)
            P = np.array(splev(np.linspace(0, 1, 400), tck)).T
        for a, b in zip(P[:-1], P[1:]):
            t = np.linspace(0, 1, int(np.hypot(*(b - a))) * 2 + 2)[:, None]
            q = (a + t * (b - a)).astype(int)
            m[q[:, 1], q[:, 0]] = True
    return ndi.distance_transform_edt(~m) <= w / 2 * UP


def crack_joins(shape):
    """Strokes joining the incisions the crack broke (JOINS), at UP."""
    m = np.zeros(shape, bool)
    for (xa, ya), (xb, yb) in JOINS:
        a = np.array([(xa - X0) * UP, (ya - Y0) * UP], float)
        b = np.array([(xb - X0) * UP, (yb - Y0) * UP], float)
        t = np.linspace(0, 1, int(np.hypot(*(b - a))) + 2)[:, None]
        p = (a + t * (b - a)).astype(int)
        m[p[:, 1], p[:, 0]] = True
    return ndi.distance_transform_edt(~m) <= JOIN_W / 2 * UP


# The incisions redrawn as even lines (John, 2026-10-12: "the whole thing isn't precise enough"; found px by px in
# the photo they came out broken, beaded and wobbly): each found incision is thinned to its centre line, spurs
# shorter than INC_SPUR round px pruned, line ends that face each other across a gap of at most INC_GAP round px
# joined where the photo's top-hat holds over INC_HOLD of MARK_T all the way across, and the whole drawn INC_W round
# px wide (the incisions measure 2.5-3.0 at half maximum, median 2.75), its edges smoothed. Marks wider than
# INC_WIDE round px (dots, clay patches) stay as found
INC_W, INC_SPUR, INC_GAP, INC_HOLD, INC_ANGLE, INC_WIDE, INC_SHORT = 2.6, 4, 16, 0.15, 25, 4.5, 6
# John's marks on pass 4, in PhotoCraft over the full-res photo (prometheus_marks_1.png, his layer alone, on the
# tool's grid): green along incisions the drawing broke or missed (Atlas's hair locks, headband and brow, the edges
# of the eagle's wing, Prometheus's bracelets: "draw them whole"); each stroke, thinned to its centre and moved
# across to the photo's incision (the top-hat's peak within MARK_SNAP round px, where it is clear; the shifts
# smoothed along the stroke), is drawn INC_W wide and the found marks within MARK_NEAR of it go. Where under
# MARK_CLEAR of a stroke finds a peak (the bracelets, in the glare) it is drawn as he drew it, and every found mark in
# the area his strokes there cover (grown MARK_HULL round px, its convex hull) goes. Blue is ink
# His marks on pass 5 (2026-10-12, prometheus_marks_2.png; "Red trace is the lighter grey/blood. green=remove.
# blue = black ink"): green as on pass 4 (ink taken out along his line: the incisions of Prometheus's face, eye, ear
# and hair, the hip's ring, the column's capital); blue is black, as painted (the glare's patches on Prometheus's
# body, the bonds from his hand to the column, the block under the blood, the lines of the plant at the right, the
# column's top); red is the wash: each closed red line filled (the blood between the ribs), the dabs as painted (the
# drops)
# His marks on pass 6 (2026-10-12, prometheus_marks_3.png), read the same way: green along the incisions of Atlas's
# cap, curls, eye, beard, arms and side, the eagle's wing, legs and back, Prometheus's ribs and legs and toes; green
# painted broad (wider than MARK_BROAD round px: the lost surface under Atlas's hand) is clay there, not a line;
# blue the black over it; red the wash beside Prometheus's thigh
MARKS_FILES = [Path(__file__).parent / f"prometheus_marks_{i}.png" for i in (1, 2, 3)]
MARK_BROAD = 8
MARK_SNAP, MARK_NEAR, MARK_PEAK, MARK_CLEAR, MARK_HULL = 4, 3, 6, 0.5, 8


def order_path(sk):
    """The px of a thin open stroke, in order from one end (a walk to the nearest unvisited px)."""
    pts = np.argwhere(sk)
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode='constant') - 1
    ends = np.argwhere(sk & (nb == 1))
    start = ends[0] if len(ends) else pts[0]
    rem = {tuple(p) for p in pts}
    rem.discard(tuple(start))
    out, cur = [start], start
    while rem:
        cand = np.array(list(rem))
        d = np.hypot(*(cand - cur).T)
        i = int(np.argmin(d))
        if d[i] > 3:
            break
        cur = cand[i]
        out.append(cur)
        rem.discard(tuple(cur))
    return np.array(out, float)


def even_incisions(marks, hat, fig):
    """The found incisions as even lines along their centres, joined across short gaps (INC_*), at UP."""
    from lysistrata import centre_lines
    wide = ndi.binary_opening(marks, structure=morphology.disk(round(INC_WIDE / 2 * UP)))
    wide = ndi.binary_propagation(wide, mask=marks)
    thin = marks & ~wide
    sk = morphology.skeletonize(centre_lines(thin, 1, INC_SPUR * UP))
    n8 = np.ones((3, 3), int)
    nb = ndi.convolve(sk.astype(int), n8, mode='constant') - 1
    lab, _ = ndi.label(sk, structure=n8)
    ends = []
    for y, x in np.argwhere(sk & (nb == 1)):
        win = lab[max(y - 8, 0):y + 9, max(x - 8, 0):x + 9] == lab[y, x]
        yy, xx = np.nonzero(win)
        d = np.array([y - (yy.mean() + max(y - 8, 0)), x - (xx.mean() + max(x - 8, 0))])
        if np.hypot(*d) > 0.5:
            ends.append(((y, x), d / np.hypot(*d), lab[y, x]))
    cand = []
    for i, (p, d, la) in enumerate(ends):
        for j in range(i + 1, len(ends)):
            q, e, lb = ends[j]
            if la == lb:
                continue
            v = np.array(q, float) - p
            L = np.hypot(*v)
            if L < 1 or L > INC_GAP * UP:
                continue
            u = v / L
            c = np.cos(np.radians(INC_ANGLE))
            if np.dot(d, u) < c or np.dot(e, -u) < c:
                continue
            t = np.linspace(0, 1, int(L) + 2)
            ys, xs = (p[0] + t * v[0]).astype(int), (p[1] + t * v[1]).astype(int)
            if hat[ys, xs].min() < INC_HOLD * MARK_T or not fig[ys, xs].all():
                continue
            cand.append((L, i, j, ys, xs))
    used = set()
    for _, i, j, ys, xs in sorted(cand, key=lambda c: c[0]):
        if i in used or j in used:
            continue
        used |= {i, j}
        sk[ys, xs] = True
    print('incision joins', len(used) // 2)
    # (short pieces standing alone, under INC_SHORT round px long, are flecks of the glaze, not incisions)
    lab, n = ndi.label(sk, structure=n8)
    ext = np.zeros(n + 1)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        ext[k] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
    sk &= (ext >= INC_SHORT * UP)[lab]
    line = ndi.distance_transform_edt(~sk) <= INC_W / 2 * UP
    return (smooth(line, 0.5) | wide) & fig


# The eagle's feathers are straight incisions, broken in the photo by wear and glare into dashes. In STRAIGHT_ZONES
# (round px: the upper wing's flight feathers, the tail's fan) the light marks (the top-hat over half MARK_T) are cut
# into pieces along their centres; pieces that lie on one straight line (each piece's direction within ST_ANGLE
# degrees, its px within ST_OFF round px of the line at the median, the gaps between them at most ST_GAP) are one feather, drawn
# straight from end to end where the line fits all its pieces within ST_RMS round px and is at least ST_LEN long. The
# curved bands across the feathers do not fit a line and stay as found
STRAIGHT_ZONES = [
    [(1180, 1105), (1400, 1075), (1560, 1050), (1690, 1015), (1720, 1080), (1790, 1250), (1800, 1330),
     (1680, 1345), (1580, 1270), (1450, 1205), (1250, 1195), (1185, 1160)],
    [(1130, 1340), (1390, 1300), (1440, 1390), (1560, 1480), (1580, 1620), (1520, 1700), (1480, 1720),
     (1340, 1690), (1200, 1600), (1140, 1480)],
]
ST_ANGLE, ST_OFF, ST_GAP, ST_RMS, ST_LEN, ST_PIECE = 7, 1.6, 30, 1.2, 15, 4


def straight_feathers(hat, fig, shape):
    """The feathers in STRAIGHT_ZONES as straight lines (ST_*): their lines at UP, and the zone they cover."""
    zone = np.zeros(shape, bool)
    for pts in STRAIGHT_ZONES:
        zone |= lw.polygon_mask(shape, np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float))
    light = ndi.binary_propagation((hat > MARK_T) & zone & fig, mask=(hat > MARK_T / 2) & zone & fig)
    sk = morphology.skeletonize(light)
    n8 = np.ones((3, 3), int)
    nb = ndi.convolve(sk.astype(int), n8, mode='constant') - 1
    sk &= nb <= 2                                   # (cut at junctions: pieces are simple strokes)
    lab, n = ndi.label(sk, structure=n8)
    pieces = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        yy, xx = np.nonzero(lab[sl] == k)
        P = np.c_[xx + sl[1].start, yy + sl[0].start].astype(float)
        if len(P) < ST_PIECE * UP:
            continue
        c = P.mean(0)
        _, sv, vt = np.linalg.svd(P - c, full_matrices=False)
        if sv[1] / max(sv[0], 1e-6) > 0.25:
            continue
        pieces.append((len(P), P, c, vt[0]))
    pieces.sort(key=lambda q: -q[0])
    used = [False] * len(pieces)
    out = np.zeros(shape, bool)
    cover = np.zeros(shape, bool)
    nlines = 0
    for i, (_, P, c, d) in enumerate(pieces):
        if used[i]:
            continue
        members = [i]
        pts = P
        grew = True
        while grew:
            grew = False
            cc = pts.mean(0)
            _, _, vt = np.linalg.svd(pts - cc, full_matrices=False)
            dd = vt[0]
            nn = np.array([-dd[1], dd[0]])
            proj = (pts - cc) @ dd
            lo, hi = proj.min(), proj.max()
            for j, (_, Q, cq, dq) in enumerate(pieces):
                if used[j] or j in members:
                    continue
                if abs(np.dot(dq, dd)) < np.cos(np.radians(ST_ANGLE)):
                    continue
                if np.median(np.abs((Q - cc) @ nn)) > ST_OFF * UP:
                    continue
                pq = (Q - cc) @ dd
                gap = max(pq.min() - hi, lo - pq.max(), 0)
                if gap > ST_GAP * UP:
                    continue
                members.append(j)
                pts = np.vstack([pts, Q])
                grew = True
                break
        cc = pts.mean(0)
        _, _, vt = np.linalg.svd(pts - cc, full_matrices=False)
        dd = vt[0]
        nn = np.array([-dd[1], dd[0]])
        rms = np.sqrt(np.mean(((pts - cc) @ nn) ** 2))
        proj = (pts - cc) @ dd
        if len(members) < 2 or rms > ST_RMS * UP or proj.max() - proj.min() < ST_LEN * UP:
            continue
        for j in members:
            used[j] = True
        a, b = cc + proj.min() * dd, cc + proj.max() * dd
        t = np.linspace(0, 1, int(np.hypot(*(b - a)) * 2) + 2)[:, None]
        q = np.clip((a + t * (b - a)).round().astype(int), 0, np.array(shape)[::-1] - 1)
        line = np.zeros(shape, bool)
        line[q[:, 1], q[:, 0]] = True
        out |= line
        nlines += 1
    print('straight feathers', nlines)
    near = ndi.distance_transform_edt(~out) <= MARK_NEAR * UP
    return smooth(ndi.distance_transform_edt(~out) <= INC_W / 2 * UP, 0.5) & fig, near & zone


def john_lines(shape, hat, path):
    """John's green strokes snapped to the photo's incisions (MARK_*), as centre lines at UP; and his blue."""
    from scipy.interpolate import splev, splprep
    m = np.asarray(Image.open(path).convert('RGBA')).astype(int)
    assert m.shape[:2] == shape, (m.shape, shape)
    r, g, b, a = (m[..., i] for i in range(4))
    green = (a > 40) & (g > r + 40) & (g > b + 20)
    blue = (a > 40) & (b > r + 40) & (b > g + 20)
    broad = ndi.binary_opening(green, structure=morphology.disk(round(MARK_BROAD / 2 * UP)))
    broad = ndi.binary_propagation(broad, mask=green)
    green &= ~broad
    hs = ndi.gaussian_filter(hat, 0.8 * UP)
    out = np.zeros(shape, bool)
    weak = np.zeros(shape, bool)
    lab, n = ndi.label(ndi.binary_closing(green, iterations=2), structure=np.ones((3, 3)))
    for k in range(1, n + 1):
        sk = morphology.skeletonize(lab == k)
        if sk.sum() < 6:
            continue
        P = order_path(sk)
        if len(P) < 6:
            continue
        tck, _ = splprep(P.T, s=len(P) * 1.0, k=min(3, len(P) - 1))
        P = np.array(splev(np.linspace(0, 1, max(int(len(P) / 2), 4)), tck)).T
        T = np.gradient(P, axis=0)
        T /= np.maximum(np.hypot(*T.T), 1e-6)[:, None]
        Nn = np.c_[-T[:, 1], T[:, 0]]
        sh = np.arange(-MARK_SNAP * UP, MARK_SNAP * UP + 0.5, 0.5)
        off = np.full(len(P), np.nan)
        for i, (p, nn) in enumerate(zip(P, Nn)):
            q = p + sh[:, None] * nn
            v = ndi.map_coordinates(hs, [q[:, 0], q[:, 1]], order=1)
            j = int(np.argmax(v))
            if v[j] > MARK_PEAK and 0 < j < len(sh) - 1:
                off[i] = sh[j]
        ok = ~np.isnan(off)
        if ok.mean() < MARK_CLEAR:
            # (in the glare, on the bracelets, the photo shows no incision to snap to: his line as drawn, and
            # the marks found round it are glare)
            ok[:] = False
            weak[tuple(np.round(P).astype(int).T)] = True
        if ok.sum() >= 3:
            idx = np.arange(len(P))
            off = np.interp(idx, idx[ok], off[ok])
            off = ndi.gaussian_filter1d(off, 1.5)
        else:
            off = np.zeros(len(P))
        Q = P + off[:, None] * Nn
        line = np.zeros(shape, bool)
        for a_, b_ in zip(Q[:-1], Q[1:]):
            t = np.linspace(0, 1, int(np.hypot(*(b_ - a_)) * 2) + 2)[:, None]
            q = np.clip((a_ + t * (b_ - a_)).round().astype(int), 0, np.array(shape) - 1)
            line[q[:, 0], q[:, 1]] = True
        out |= line
    if weak.any():
        from skimage.morphology import convex_hull_object
        lab, _ = ndi.label(ndi.binary_dilation(weak, structure=morphology.disk(MARK_HULL * UP)))
        weak = convex_hull_object(lab > 0)
    return out, blue, weak, broad


def john_red(shape):
    """John's red (the marks files after the first): closed lines filled, dabs as painted, at UP."""
    red = np.zeros(shape, bool)
    for path in MARKS_FILES[1:]:
        m = np.asarray(Image.open(path).convert('RGBA')).astype(int)
        r, g, b, a = (m[..., i] for i in range(4))
        red |= (a > 40) & (r > g + 40) & (r > b + 40)
    sk = morphology.skeletonize(ndi.binary_closing(red, iterations=2))
    inside = ndi.binary_fill_holes(sk) & ~sk
    return smooth(red | inside, 0.5) | (inside & ~red)


def masks(ch, dump=None):
    L, W, RG, BR, GB, sat, hat, what, Wc = (ch[k] for k in ("L", "W", "RG", "BR", "GB", "sat", "hat", "what", "Wc"))
    # the glare: blue over GLARE_BR round it (4 px), or lighter than GLARE_L and less warm than GLARE_W over 8 px
    # (the glaze photographs grey-blue in it: Prometheus's hanging hand), grown by GLARE_GROW. There the grey and the blue both flicker;
    # red less blue does not (the black and its glare read under 20, the clay 60-90, an incision 20-30 over the
    # black beside it): the edge is where red less blue crosses GLARE_EDGE, the incisions its white top-hat
    f = 4
    Ls = ndi.zoom(ndi.gaussian_filter(L[::f, ::f], 8 * UP / f), f, order=1)[:L.shape[0], :L.shape[1]]
    Ws = ndi.zoom(ndi.gaussian_filter(Wc[::f, ::f], 8 * UP / f), f, order=1)[:L.shape[0], :L.shape[1]]
    glare0 = (ndi.gaussian_filter(BR, 4 * UP) > GLARE_BR) | ((Ls > GLARE_L) & (Ws < GLARE_W))
    glare0 = ndi.binary_dilation(glare0, structure=morphology.disk(GLARE_GROW * UP))
    H, Wd = L.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    rr = np.hypot(px - RINGS_C[0], py - RINGS_C[1])
    inside = rr < R_IN
    c1 = crack_mask(ch["L1"])[Y0:Y1, X0:X1]
    crack = np.repeat(np.repeat(c1, UP, 0), UP, 1)[:H, :Wd]

    # ground: the clay's large areas, grown into clay wider than an incision; its edge at the half-maximum
    sure = (W > 40) & (W > 0.4 * L) & (GB > 12) & inside & ~crack & ((py < FLOOR) | (sat > FLOOR_SAT))
    bg = clay_grey(L, sure)
    redc = (RG > RED_RG) & (GB < RED_GBK * RG) & (L < RED_L)
    f = 4
    smax = ndi.maximum_filter(sat[::f, ::f], size=2 * FLOOR_R * UP // f + 1)
    smax = ndi.zoom(ndi.gaussian_filter(smax, FLOOR_R * UP / f), f, order=1)[:H, :Wd]
    floor_clay = (sat > FLOOR_SAT) & (sat > FLOOR_K * smax)
    clay = (L > CLAY_K * bg) & ((py < FLOOR) | floor_clay) & (W > CLAY_W) & ~redc & inside & ~crack
    g0 = ndi.binary_opening(clay, structure=morphology.disk(4 * UP))
    ground = keep_big(g0, AUTO_GROUND * UP * UP)
    core = ndi.distance_transform_edt(clay) > WIDE_CLAY / 2 * UP
    ground = ndi.binary_propagation(ground, mask=clay & (ndi.distance_transform_edt(~core) <= WIDE_CLAY / 2 * UP))
    band = (ndi.distance_transform_edt(ground) <= EDGE_BAND * UP) & (ndi.distance_transform_edt(~ground) <= EDGE_BAND * UP)
    wg = ndi.gaussian_filter(ground.astype(np.float32), EDGE_R * UP)
    lg = ndi.gaussian_filter(np.where(ground, L, 0), EDGE_R * UP) / np.maximum(wg, 1e-3)
    lf = ndi.gaussian_filter(np.where(ground, 0, L), EDGE_R * UP) / np.maximum(1 - wg, 1e-3)
    # (the glare is blue and as light as the clay: blue over EDGE_BLUE is figure)
    ground = np.where(band & ~crack & inside, (L > (lg + lf) / 2) & (BR < EDGE_BLUE), ground)
    ground = np.where(band & ~crack & inside & glare0, ndi.gaussian_filter(Wc, UP) > GLARE_EDGE, ground)
    # the added red
    red = (RG > RED_RG) & (GB < RED_GBK * RG) & (L < RED_L) & inside & ~crack
    red = ndi.binary_opening(red, structure=morphology.disk(UP))
    red = keep_big(red, RED_MIN * UP * UP)
    in_box = np.zeros(L.shape, bool)
    for bx0, by0, bx1, by1 in DARK_BOXES:
        in_box |= (px >= bx0) & (px < bx1) & (py >= by0) & (py < by1)
    dark = (RG > DARK_RG) & (GB < RED_GBK * RG) & (L < DARK_L) & inside & ~crack & in_box
    dark = keep_big(ndi.binary_opening(dark, structure=morphology.disk(DARK_OPEN * UP)), DARK_MIN * UP * UP)
    red |= dark
    red = ndi.binary_closing(red, structure=morphology.disk(UP))
    red = morphology.remove_small_holes(red, max_size=80 * UP * UP)
    # the figures: all else inside the ring (the red pieces on the ground with them)
    fig = inside & ~ground & ~crack
    fig = keep_big(ndi.binary_opening(fig, structure=morphology.disk(UP)), FIG_MIN * UP * UP, keep=red)
    fig = ndi.binary_fill_holes(fig) & ~ground
    # (below the ground line the glaze's raised edge throws a thin shadow just outside it, with the glare's bright
    # rim inside: a sliver of ground between the two drew a second outline round the capital and the lotus. There
    # the figures are closed by FLOOR_CLOSE round px)
    fig = np.where(py > FLOOR, ndi.binary_closing(fig, structure=morphology.disk(FLOOR_CLOSE * UP)) & inside, fig)
    # (dark specks off the figures, under SPECK round px^2 and not red, go; pieces lying wholly within RING_HUG of the
    # first ring (the ring's shadow) go; and the pieces under DROP)
    lab, n = ndi.label(fig)
    sz = np.bincount(lab.ravel(), minlength=n + 1)
    has_red = np.bincount(lab[red], minlength=n + 1) > 0
    far = np.bincount(lab[rr < R_IN - RING_HUG], minlength=n + 1) > 0
    drop = ((sz < SPECK * UP * UP) & ~has_red) | ~far
    for x, y in DROP:
        drop[lab[round((y - Y0) * UP), round((x - X0) * UP)]] = True
    drop[0] = False
    fig &= ~drop[lab]
    for pts in WORN:
        fig |= lw.polygon_mask(fig.shape, np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)) & inside
    # across the crack: the figures and the red carried over from both sides
    free = ~inside
    fig = harmonic_fill(fig, crack, free) & inside
    red = harmonic_fill(red, crack, free) & inside
    # the sky meets the first ring: the filler runs along the ring there, and the fill left a strip of clay
    ang = np.degrees(np.arctan2(py - RINGS_C[1], px - RINGS_C[0]))
    fig |= inside & (rr > R_IN - SKY_W) & (ang > SKY_SPAN[0]) & (ang < SKY_SPAN[1])
    fig = smooth(fig, 0.8)
    red = smooth(red, 1.5) & fig
    for pts, w in RED_BARS:
        red |= strokes(red.shape, [pts], w) & fig
    rope_lab, rope_sep = ropes(red.shape, L, RG, ground)
    rp = np.array([p for pts in ROPES for p in pts])
    rbox = ((px > rp[:, 0].min() - 20) & (px < rp[:, 0].max() + 20) & (py > rp[:, 1].min() - 20)
            & (py < rp[:, 1].max() + 20))
    rope = rope_lab > 0
    fig |= rope
    red = np.where(rbox, rope & ~rope_sep, red)
    # the incisions
    from skimage.filters import apply_hysteresis_threshold
    # (below the ground line the glare's bright rim along the capital's edges drew a second outline: clear further)
    clear = ndi.distance_transform_edt(fig) > np.where(py > FLOOR, FLOOR_CLEAR, EDGE_CLEAR) * UP
    # (in the glare, blue over its 4 px round, and below the ground line, its speckle passed for incisions: there the
    # threshold is GLARE_K times as high, and the marks at least GLARE_LEN long)
    glare = glare0 | (py > FLOOR)
    t = np.where(glare, GLARE_K * MARK_T, MARK_T)
    marks = fig & clear & ~red & ~crack & (hat > t / 2) & (BR < MARK_BR)
    marks = ndi.binary_propagation(marks & (hat > t), mask=marks)
    wm = fig & clear & ~red & ~crack & glare0 & (what > GLARE_HAT / 2)
    wm = ndi.binary_propagation(wm & (what > GLARE_HAT), mask=wm)
    marks = np.where(glare0, wm, marks)
    # (below the ground line the glare's speckle passed for incisions: there they are also orange)
    marks &= (py < FLOOR) | (W > 0.4 * L)
    lab, _ = ndi.label(marks)
    sz = np.bincount(lab.ravel())
    ext = np.zeros(len(sz))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is not None:
            ext[k] = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
    in_glare = np.bincount(lab[glare & ~glare0], minlength=len(sz)) > 0.5 * sz
    in_g0 = np.bincount(lab[glare0], minlength=len(sz)) > 0.5 * sz
    marks &= ((sz >= MARK_MIN * UP * UP) & (ext >= np.where(in_g0, GLARE_WLEN, np.where(in_glare, GLARE_LEN, MARK_LEN)) * UP))[lab]
    marks = even_incisions(marks, hat, fig)
    feathers, fcover = straight_feathers(hat, fig, marks.shape)
    marks = (marks & ~fcover) | feathers
    jblue = np.zeros(marks.shape, bool)
    for path in MARKS_FILES:
        jl, jb, jweak, jbroad = john_lines(marks.shape, hat, path)
        marks &= ~(ndi.distance_transform_edt(~jl) <= MARK_NEAR * UP) & ~jweak
        marks |= jbroad & fig
        jblue &= ~jbroad
        marks |= smooth(ndi.distance_transform_edt(~jl) <= INC_W / 2 * UP, 0.5) & fig
        jblue = (jblue & ~(ndi.distance_transform_edt(~jl) <= INC_W / 2 * UP)) | jb
    jred = john_red(marks.shape)
    marks |= crack_joins(marks.shape) & fig
    marks |= strokes(marks.shape, HAND, EYE_W) & fig
    marks = marks & ~(rbox & rope)
    red, marks = solid_red(red, fig, marks, px, py)
    for lines in EYES.values():
        c = np.mean(lines[0], axis=0)
        zone = np.hypot(px - c[0], py - c[1]) < EYE_R
        marks = np.where(zone, strokes(marks.shape, lines, EYE_W) & fig, marks)
    if dump:
        np.savez_compressed(dump, fig=fig, red=red, marks=marks, crack=crack, ground=ground)
    rings = np.zeros(L.shape, bool)
    for r in RINGS_R:
        rings |= np.abs(rr - r) <= RING_W / 2
    return fig, red, marks, crack, rings, jblue, jred


def main(src, qa=None, dump=None, cache=None):
    if cache and Path(cache).exists():
        ch = dict(np.load(cache))
    else:
        ch = channels(src)
        if cache:
            np.savez(cache, **ch)
    fig, red, marks, crack, rings, jblue, jred = masks(ch, dump)
    lines = (smooth(fig & ~marks & ~red, SMOOTH) & ~jred) | rings | smooth(jblue, SMOOTH)
    tone = (smooth(red, SMOOTH) | jred) & ~lines
    # (John, 2026-10-11: "the white background just doesn't work here. Let's have clay for both light and dark":
    # the body is the whole tondo to the outer ring's edge, filled with clay in both themes, as clouds.svg)
    body = ndi.binary_fill_holes(fig | rings | (ndi.distance_transform_edt(~rings) <= RIM * UP))
    info = write_svg(
        lines, body, tone, OUT,
        title='Atlas holding up the sky, and Prometheus bound, with the eagle',
        desc='Line drawing after a photo of a Laconian black-figure cup in the Vatican (Museo Gregoriano Etrusco '
             '16592): Atlas holds up the sky; Prometheus is bound to a column and the eagle feeds on him; a snake '
             'behind Atlas; below, a capital between two lotus sprays; retraced.')
    print(OUT, info)
    if qa:
        lw.qa_overlay(ch["L"], OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3], dump=os.environ.get("PROMETHEUS_DUMP"), cache=os.environ.get("PROMETHEUS_CACHE"))
