"""Sophocles: the shepherd Euphorbos carrying the infant Oedipus, from Karl Reichhold's drawing of the
neck-amphora in Paris in Furtwängler and Reichhold, Griechische Vasenmalerei III (Munich, F. Bruckmann,
1927 at the plate's foot), Taf. 167, 1 ("Amphora in Paris", "Euphorbos mit dem Ödipuskind"), as
photographed by the Williams College Visual Resources Center (JSTOR, Furtwängler Griechische
Vasenmalerei, https://www.jstor.org/stable/community.16364348): the whole plate (3440 x 2615) and a view
of Euphorbos at twice its scale (3440 x 2518), which cuts off the crown of his head.
The vase: Attic red-figure neck-amphora attributed to the Achilles Painter, from Vulci, Paris, Cabinet
des médailles 372 (ARV2 987.4; BAPD 213824). Their names are painted beside them: ΕΥΦΟΡΒΟΣ, ΟΙΔΙΠΟΔΑΣ.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop,
the enlargement, the grey, the blurs, Minimum and Maximum, and the thresholds. Two steps stay in numpy and
scipy: the crown, resampled from the whole plate into a strip above the view (a scale and shift fitted by
SIFT, 0.22 px rms), and the masks' arithmetic (labels, unions, distances, fills, centre lines). The SVG
is written by linework.trace_svg.

Plate -> drawing, Furtwängler-Reichhold, red figures on the black ground (as bacchae.py):
  - Ground: the plate's dark, thin lines opened away; the large areas reaching the crop's edge, and the
    pockets the figures close in (POCKETS). Smaller dark areas inside the figures are paint (the hair).
  - Lines: the plate's black lines (local contrast), redrawn along their centres at WEIGHT (the F-R
    weight, 0.11%); the outline on the ground just outside the clay, as wide.

    python3 docs/redesign/drawings/tools/euphorbos.py view.jpg plate.jpg [qa.png]
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
from skimage import morphology
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "sophocles-euphorbos.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# Coordinates are the view's px ("scan px"); y < 0 is the crown strip, taken from the whole plate.
VIEW_TO_PLATE = (0.500709, 1559.130, 771.911)   # plate = s * view + (dx, dy) (SIFT, 870 matches, 0.22 px rms)
CROWN = 80                                       # scan px of strip above the view (the hair's top is at -38)
# Levelling: the panel's ruled edges lean (x = 979 - 0.0098 y on the left, 2433 - 0.0127 y on the right) and the
# meander band's top edge slopes (0.0019, fitted on 37 columns where the ground lies over it): a shear each way, about (LEVEL_C) them, makes
# the edges upright and the band level (a plain turn would not do both)
LEVEL_X, LEVEL_Y, LEVEL_C = 0.0112, 0.0019, (1700, 1000)
X0, Y0, X1, Y1 = 800, -60, 3070, 2085            # the crop: the figure and the spear, its butt to its blade
# the black panel's ruled edges, after levelling (x = a + b y, fitted at 42 rows each, 0.4-0.5 px rms): the
# spear runs past both onto the paper, where its own outline closes it (John, 2026-10-12: as printed, "then we
# can cut down to b if need be")
PANEL_L, PANEL_R = (968.87, 0.00199), (2419.38, -0.00136)
PAPER_T = 150                                    # outside the panel: paper lighter than this, reaching the
                                                 # crop's edge, is ground
FLOOR = 2075                                     # below this, out: the meander band (its top edge at
                                                 # 2080.7-2083.7 after levelling) and the ground over it;
                                                 # the soles' clay ends at 2074-2075, and their outline
                                                 # is drawn below the cut
UP = 2                                           # work at 2x the scan's px
SEEDS = [(1500, 1500), (1900, 300)]
DARK = 85                                        # ground and paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 8000                               # scan px: dark areas this large reaching the crop's edge
# ground the figures close in (a point in each, scan px): between the chiton and the mantle, above and below
# the spear; between the hem and the spear behind his hand
POCKETS = [(1840, 1010), (1837, 1075), (1550, 1070)]
LINE_R = 3.0                                     # scan px: the closing for the lines' local contrast
LINE_LO, LINE_HI = 22, 34
PAINT_NEAR, PAINT_CORE, PAINT_MIN = 1, 45, 80                  # (paint: the dark areas wider than the opening, with a core
                                                 # darker than PAINT_CORE; at 6 scan px round them, as on
                                                 # Bacchae, the pen lines near them came out ragged;
                                                 # smaller than PAINT_MIN scan px, the blots where lines
                                                 # cross: lines)
LINE_W = 2.2                                     # scan px: the lines' width, the plate's pen (its lines'
                                                 # half-maximum width, 2-2.5 scan px)
# faces and hands (boxes, scan px): Euphorbos' eye, nose and lips; the child's face; the child's hand on the
# chiton. At LINE_W the child's eye and mouth ran into blots and the fingers merged. Inside each box the
# lines are the plate darker than FACE_T (blurred FACE_BLUR scan px: the lines' cores 45-70, the clay
# 170-190), at their printed width, traced at their own size; specks under FACE_SPECK scan px dropped
FACES = [(1868, 113, 1995, 215), (1826, 268, 1935, 352), (1738, 380, 1860, 468),
         (1712, 718, 1822, 772),                              # (and the belt's two rows of triangles,
         (2876, 939, 2934, 951, 150)]                         # and the five dots on the spear's socket,
                                                              # paler: darker than 150)
# the sandals' straps and lattices (boxes, scan px): broad brushstrokes; at FACE_BLUR their edges came out
# ragged and broken by the print's grain, so here the plate blurred SANDAL_BLUR scan px, darker than SANDAL_T,
# its pinholes filled and its specks (under SANDAL_SPECK scan px) dropped
SANDALS = [(1236, 1960, 1565, 2076), (1676, 1960, 2032, 2076)]
SANDAL_BLUR, SANDAL_T, SANDAL_SPECK = 1.2, 112, 8
# the petasos' thinned paint (a polygon round the crown and the cord, scan px): a wash whose opacity follows
# how much darker the plate is (blurred 1 scan px) than the hat's clay (HAT_CLAY, read at five points:
# 172-186), from HAT_A[0] at HAT_D[0] darker to HAT_A[1] at HAT_D[1]; the cord's broad brushstroke (darker
# than CORD_T, wider than 4 scan px) takes no lines
HAT = [(1415, 205), (1470, 188), (1560, 198), (1572, 260), (1545, 330), (1520, 385), (1470, 398), (1425, 392),
       (1398, 350), (1405, 290), (1435, 240)]
HAT_CLAY, HAT_D, HAT_A, CORD_T = 178, (22, 120), (0.15, 0.85), 115
HAT_SIGMA = 4                                    # scan px: the crown's grey smoothed (the cord's 1 px)
FACE_T, FACE_BLUR, FACE_SPECK = 100, 0.35, 3
# Euphorbos' hair (a polygon round it, scan px): the plate darker than HAIR_T (lightly smoothed; the hair
# 30-110, the clay line round it and the face 170 and over) joined to the paint's dark cores, its holes under
# HAIR_HOLE scan px filled. HAIR_STYLE "solid" (as Bacchae) or "wash": a tone whose opacity follows the
# plate, from HAIR_A[0] at grey HAIR_G[0] to HAIR_A[1] at HAIR_G[1]
HAIR = [(1620, -45), (2000, -45), (2000, 112), (1890, 112), (1875, 140), (1850, 150), (1815, 165), (1790, 240),
        (1620, 240)]
HAIR_T, HAIR_HOLE = 130, 6
HAIR_STYLE = "wash"                               # John, 2026-10-12: "Wash"
HAIR_A, HAIR_G = (0.45, 1.0), (130, 45)
# the child's curls, stippled in thinned paint: a wash whose opacity follows how much darker the plate is
# than the clay round it: the curls' mass (the plate darker than CHILD_T, blurred CHILD_SIGMA scan px: its
# edge where the curls end, not past it: John, "don't have hair bleed into face") at
# WASH_A[0]; no lines inside but long strokes (the chin
# beside it), longer than CHILD_LONG scan px
CHILD_HAIR = [(1800, 246), (1835, 244), (1858, 254), (1868, 238), (1876, 219), (1900, 216), (1922, 224),
              (1937, 240), (1950, 262), (1950, 292), (1925, 286), (1905, 283), (1890, 280), (1880, 276),
              (1862, 275), (1852, 290), (1830, 306), (1800, 306), (1796, 280)]
WASH_R, WASH_D, WASH_A = 10, 20, (0.3, 0.7)
CURL_T = 115   # the curls' darker strokes (grey, blurred 1 scan px): WASH_A[1], crisp, over the mass
CHILD_SIGMA, CHILD_T, CHILD_LONG = 1.5, 140, 25


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def composite(view, plate, out):
    """The view with the crown strip above it, resampled (cubic) from the whole plate; then levelled (cubic).
    Rows: CROWN px of strip, then the view."""
    v = np.asarray(Image.open(view).convert("RGB")).astype(np.float32)
    p = np.asarray(Image.open(plate).convert("RGB")).astype(np.float32)
    s, dx, dy = VIEW_TO_PLATE
    yy, xx = np.mgrid[-CROWN:0, 0:v.shape[1]].astype(np.float32)
    strip = np.stack([ndi.map_coordinates(p[..., c], [s * yy + dy, s * xx + dx], order=3, mode='nearest')
                      for c in range(3)], -1)
    c = np.r_[strip, v]
    cx, cy = LEVEL_C
    yy, xx = np.mgrid[0:c.shape[0], 0:c.shape[1]].astype(np.float32)   # levelled px (y with the strip)
    sx = xx - LEVEL_X * (yy - CROWN - cy)
    sy = yy + LEVEL_Y * (sx - cx)
    c = np.stack([ndi.map_coordinates(c[..., k], [sy, sx], order=3, mode='nearest') for k in range(3)], -1)
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(out)


def poly(px, py, pts):
    """Work-px mask of a polygon given in scan px."""
    x0, y0 = px[0, 0], py[0, 0]   # (the work grid's first px centre)
    P = np.array(pts, float)
    return lw.polygon_mask(px.shape, np.c_[(P[:, 0] - x0) * UP, (P[:, 1] - y0) * UP])


def add_tone(svg, alpha, box, step=0.05):
    """Paths of class "tone" in the line colour between the body and the lines, traced at the lines' own
    size: `alpha` (work px, 0 for none) in steps, each step's area drawn over the one below at the opacity
    that brings the total there to the step's, so no seam shows (as add_tone in andromache.py)."""
    x0, y0, x1, y1 = box
    a = alpha[y0:y1, x0:x1]
    lo = a[a > 0].min() if (a > 0).any() else 1
    paths, below = '', 0.0
    for v in np.arange(np.floor(lo / step) * step, a.max() + 1e-9, step):
        m = (a > 0) & (a >= v - step / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        op = 1.0 if v >= 1 - 1e-9 else 1 - (1 - v) / (1 - below)
        paths += f'<path class="tone" fill="currentColor" fill-opacity="{op:.3f}" stroke="none" d="{d}"/>'
        below = min(v, 0.999)
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def masks(src, box=None):
    """Everything up to the ink: returns a dict of work-px arrays for the crop (or `box`, scan px)."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    w, h = x1 - x0, y1 - y0
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        pc(src, t / "up.png",
           ("image.crop", {"x": x0, "y": y0 + CROWN, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = round(LINE_R * UP)
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
        r = WASH_R * UP
        pc(t / "gw.png", t / "wclosed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": FACE_BLUR * UP}))
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": 0.35 * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        g, gl, closed, gs, gw, wclosed = (grey(t / f"{n}.png") for n in ("up", "gl", "closed", "gs", "gw", "wclosed"))
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
        gf = grey(t / "gf.png")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP + x0 - 0.5, (yy + 0.5) / UP + y0 - 0.5
    return dict(gf=gf, g=g, gl=gl, closed=closed, gs=gs, gw=gw, wclosed=wclosed, dark0=dark0, fine=fine, px=px, py=py, box=(x0, y0, x1, y1))


def main(view, plate, qa=None, box=None, out=OUT, dump=None):
    with tempfile.TemporaryDirectory() as td:
        comp = Path(td) / "comp.png"
        composite(view, plate, comp)
        m = masks(comp, box)
    g, gl, closed, gs, dark0, fine, px, py = (m[k] for k in ("g", "gl", "closed", "gs", "dark0", "fine", "px", "py"))
    x0, y0, x1, y1 = m['box']
    outside = py > FLOOR
    panel = (px > PANEL_L[0] + PANEL_L[1] * py) & (px < PANEL_R[0] + PANEL_R[1] * py)

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP), border_value=1) & ~outside & panel
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside | ~panel, iterations=2)]])
    is_ground = (size > (AUTO_GROUND if box is None else 400) * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        if not (x0 <= x < x1 and y0 <= y < y1):
            continue
        r = 15 * UP
        cy, cx = round((y - y0) * UP), round((x - x0) * UP)
        win = lab[max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
        dist = np.hypot(*np.mgrid[0:win.shape[0], 0:win.shape[1]] - np.array([[[min(r, cy)]], [[min(r, cx)]]]))
        iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
        assert win[iy, ix], f'no dark area near {(x, y)}'
        is_ground[win[iy, ix]] = True
    ground = is_ground[lab]
    inground = ground.copy()                     # (the panel's ground, where the outline is drawn)
    lab, _ = ndi.label((gs > PAPER_T) & ~panel & ~outside)
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    ground |= np.isin(lab, rim[rim > 0])

    fig = ~ground & ~outside
    lab, _ = ndi.label(fig)
    sz = np.bincount(lab.ravel())
    sz[0] = 0
    fig = np.isin(lab, np.nonzero(sz > 2000 * UP * UP)[0])
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP))
    # (on the paper the spear's printed outline is its lines, not its clay: the clay is the paper inside them)
    paper_lines = fig & ~panel & ~(gs > PAPER_T)
    fig &= panel | (gs > PAPER_T)
    fig = morphology.remove_small_objects(fig, max_size=200 * UP * UP)   # (slivers of paper at the panel's edge)

    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    solid = morphology.remove_small_objects(solid, max_size=PAINT_MIN * UP * UP)
    paint = fine & ndi.binary_dilation(solid, iterations=PAINT_NEAR * UP) & fig
    head = poly(px, py, HAIR)
    lab, n = ndi.label((gs < HAIR_T) & fig & head)
    hair = np.bincount(lab[solid & head].ravel(), minlength=n + 1) > 0
    hair[0] = False
    hair = hair[lab]
    holes = ndi.binary_fill_holes(hair) & ~hair
    hair |= holes & ~morphology.remove_small_objects(holes, max_size=HAIR_HOLE * UP * UP)
    paint &= ~head
    tone = np.zeros(g.shape, np.float32)
    if HAIR_STYLE == "solid":
        paint |= hair
    else:
        a0, a1 = HAIR_A
        gh = ndi.gaussian_filter(gs, UP)
        tone = np.where(hair, a0 + (a1 - a0) * np.clip((HAIR_G[0] - gh) / (HAIR_G[0] - HAIR_G[1]), 0, 1), 0)
    # the child's curls: a wash
    ch = poly(px, py, CHILD_HAIR) & fig
    depth = m['wclosed'] - m['gw']
    cw = ch & (ndi.gaussian_filter(m['gw'], CHILD_SIGMA * UP) < CHILD_T)
    cw = morphology.remove_small_objects(cw, max_size=20 * UP * UP)
    curl = ch & ndi.binary_opening(m['gw'] < CURL_T, structure=morphology.disk(UP // 2 + 1))
    curl = morphology.remove_small_objects(curl, max_size=4 * UP * UP)
    tone = np.where(cw, WASH_A[0], tone)
    tone = np.where(curl, WASH_A[1], tone)
    hat = poly(px, py, HAT) & fig
    cord = ndi.binary_opening((m['gw'] < CORD_T) & hat, structure=morphology.disk(2 * UP))
    paint &= ~hat
    paint &= ~ch

    tw = LINE_W * UP - 1      # (a centre line grown by tw / 2 comes out tw + 1 px wide)
    firm = apply_hysteresis_threshold(closed - gl, LINE_LO, LINE_HI)
    black = firm & (fig | paper_lines) & ~ndi.binary_dilation(paint, iterations=UP) & ~(head & hair)
    lab, n = ndi.label(black & ch)
    sk = np.bincount(lab[morphology.skeletonize(black & ch)].ravel(), minlength=n + 1)
    black &= ~(ch & ~(sk > CHILD_LONG * UP)[lab])
    lines = centre_lines(black, tw, 3 * UP, 2 * tw) | paint
    faces = np.zeros_like(fig)
    face_t = np.full(fig.shape, FACE_T, np.float32)
    dotbox = np.zeros_like(fig)                  # (boxes with their own threshold add dots only, pieces
    for b in FACES:                              # under 20 scan px, to the lines, which they keep)
        inb = (px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3])
        faces |= inb
        if len(b) > 4:
            face_t[inb] = b[4]
            dotbox |= inb
    sandals = np.zeros_like(fig)
    for b in SANDALS:
        sandals |= (px >= b[0]) & (px < b[2]) & (py >= b[1]) & (py < b[3])
    faces |= sandals
    fl = (m["gf"] < face_t) & faces & ~sandals & (fig | paper_lines) & ~ch
    sd = (ndi.gaussian_filter(m['g'], SANDAL_BLUR * UP) < SANDAL_T) & sandals & fig
    sd |= ndi.binary_fill_holes(sd) & ~morphology.remove_small_objects(ndi.binary_fill_holes(sd) & ~sd, max_size=3 * UP * UP)
    fl |= morphology.remove_small_objects(sd, max_size=SANDAL_SPECK * UP * UP)
    holes = ndi.binary_fill_holes(fl) & ~fl
    fl |= holes & ~morphology.remove_small_objects(holes, max_size=UP * UP)
    fl = morphology.remove_small_objects(fl, max_size=FACE_SPECK * UP * UP)
    fl &= ~(dotbox & morphology.remove_small_objects(fl & dotbox, max_size=20 * UP * UP))
    lines = (lines & ~(faces & ~dotbox)) | fl
    lines &= ~ndi.binary_dilation(cord, iterations=UP)
    hd = HAT_CLAY - ndi.gaussian_filter(m['gw'], UP)
    hw = hat & (hd > HAT_D[0]) & ~ndi.binary_dilation(lines & ~cord, iterations=UP // 2)
    hw = morphology.remove_small_objects(ndi.binary_opening(hw, structure=morphology.disk(UP)), max_size=30 * UP * UP)
    # (the crown's grey smoothed over HAT_SIGMA within the wash only, so the clay round it does not pale its
    # edge; the cord, broader dark, kept sharp)
    sg = HAT_SIGMA * UP
    crown = hw & ~ndi.binary_dilation(cord, iterations=UP)
    hs = ndi.gaussian_filter(np.where(crown, hd, 0), sg) / np.maximum(ndi.gaussian_filter(crown.astype(np.float32), sg), 1e-6)
    hd = np.where(crown, hs, hd)
    tone = np.where(hw, HAT_A[0] + (HAT_A[1] - HAT_A[0]) * np.clip((hd - HAT_D[0]) / (HAT_D[1] - HAT_D[0]), 0, 1), tone)
    tone = np.round(tone / 0.05) * 0.05
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & (dt <= tw) & ndi.binary_dilation(inground | outside, iterations=UP) & panel
    ink = (lines & (fig | paper_lines)) | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * UP * UP)[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint, firm=firm & fig,
                            gs=gs.astype(np.uint8))
    info = lw.trace_svg(
        ink, Path(out), body=fig, open_holes=~fig, weight="drawn", dots=fl & ink,
        title='The shepherd Euphorbos carrying the infant Oedipus',
        desc='Line drawing after Karl Reichhold\'s drawing of the neck-amphora by the Achilles Painter, Paris, '
             'Cabinet des médailles 372 (Furtwängler and Reichhold, Griechische Vasenmalerei III, Taf. 167); '
             'cut out and retraced.')
    if tone.any():
        add_tone(Path(out), tone, info['box'])
    print(out, info)
    if qa:
        lw.qa_overlay(g, Path(out), info['box'], Path(qa))
        lw.qa_dark(Path(out), info['box'], Path(qa).with_suffix('.dark.png'))
    return info


if __name__ == '__main__':
    main(*sys.argv[1:4])
