"""Electra (Euripides): Orestes drives his sword into Aegisthus, who falls back from his chair, his lyre gone; at the
left the woman the painter names Chrysothemis flees with a raised hand. From Karl Reichhold's drawing of side A of the
Berlin Painter's pelike in Vienna (Kunsthistorisches Museum IV 3725) in Furtwängler and Reichhold, Griechische
Vasenmalerei II (Munich, 1909), Taf. 72 ("Pelike in Wien", "Der Tod des Aigisthos"; text p. 75), as scanned by the
Visual Resources Center, Williams College (JSTOR community.16113283, FRSerieIIpt71_80_072.jpg; the scan CC BY-NC-SA
4.0, the plate public domain in the US). The source is the side-A panel at the scan's full size (6581 x 4989),
fetched from JSTOR's IIIF server, region 3080,2100,2500,2100: fr72_panel_full.jpg (2500 x 2100). JSTOR's Download
button gives the plate at half that (3445 x 2612).
John's pick (2026-10-15): this plate rather than Monumenti inediti VIII, tav. XV (the same side as an outline
engraving, Arachne's scan at most 2661 px). His edge calls (2026-10-15): the chair, the stool's leg and the floor band
in; the painted names, the palmette band and the meander borders out. The stippled patch along the floor is wear on
the vase: filled in as the black ground, the feet over it kept.

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli`, as in orestes.py, whose rules
this tool follows (the same book and family: red figures on the black ground). numpy only combines its masks and
measures; the cuts are geometry (electra_eur_cuts.json: least-cost paths through the plate's dark between the
figures and the bands, found once with scikit-image and kept as polygons).

Plate px here are this scan's, 1.9 times as fine as the Williams College scans the other F-R tools read (Orestes'
3440 px plate); lengths below are this scan's px.

Plate -> drawing:
  - Out: the polygons of CUTS (the borders and the palmette band).
  - The stipple (STIPPLE): inside its polygon, the light areas the plate's lines close off that are thick with small
    dark dots are the worn patch, and become ground.
  - Ground: the plate's dark, thin lines opened away; the large areas reaching the crop's edge or the cuts, and the
    pockets the figures close in (POCKETS).
  - The figures: the clay joined to SEEDS (each moved to the nearest clay within 30 plate px).
  - Lines, paint and hair: as orestes.py, the faces at the plate's own width (FACES), the small dots kept (DOT_*).

    python3 docs/redesign/drawings/tools/electra_eur.py fr72_panel_full.jpg [qa.png]
    python3 docs/redesign/drawings/tools/electra_eur.py fr72_panel_full.jpg qa.png --test x0,y0,x1,y1 out.svg
    python3 docs/redesign/drawings/tools/electra_eur.py fr72_panel_full.jpg diag.png --diag
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
from skimage import draw, morphology
from skimage.filters import apply_hysteresis_threshold

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402
from andromache import centre_lines  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "electra-eur.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))
CUTS = json.loads((Path(__file__).parent / "electra_eur_cuts.json").read_text())

X0, Y0, X1, Y1 = 0, 100, 2500, 1890       # crop in plate px: the panel, the black base under the floor band
UP = 1.5                                   # work at 1.5x the plate's px (about Orestes' work px)
SEEDS = [(800, 900), (1300, 700), (1700, 900), (2300, 1300), (1500, 1650), (1200, 1785)]
DARK = 85                                  # ground and paint: darker than this (grey, lightly smoothed; ground 30-40)
AUTO_GROUND = 15000                        # plate px: dark areas this large reaching the crop's edge are ground
# ground the figures close in (a point in each, plate px; the dark area at or nearest it): behind the woman's neck,
# under her ribbons; between Orestes' arm and his side; between his raised arm and Aegisthus' face; between the
# sword and Aegisthus' arm, and under the blade; the chair's back, behind Aegisthus' back, under the seat, between his
# hand and the volute, between the chair's leg and the border; between the woman and Orestes; between Orestes' legs;
# under Aegisthus; round the stool's leg and the worn patch; the black left under the feet
POCKETS = [(958, 474), (1169, 649), (1650, 569), (1592, 804), (1636, 907), (2198, 701), (2170, 893), (2164, 1072),
           (2395, 1073), (2421, 1390), (958, 942), (1268, 1362), (1918, 1556), (1310, 1612), (1158, 1571),
           (873, 1683), (948, 1691), (938, 1692), (621, 1715), (425, 1640), (2093, 1736), (1115, 1706),
           (299, 1659), (439, 1677), (420, 1670), (553, 1697)]
# the worn patch along the floor (polygon, plate px): inside it, where more than STIP_D of the plate (blurred over
# STIP_R plate px) is small dark marks (darker than STIP_T, lightly smoothed; each under STIP_DOT plate px^2: the dots
# read 3-25, the plate's lines run long), off the long marks, is ground. The dots: 0.10 of the patch; the clay: none.
# (Taken area by area, closed off by the lines, the foot whose outline breaks against the patch went with it)
STIPPLE = [(150, 1625), (980, 1515), (1050, 1505), (1545, 1800), (1100, 1790), (600, 1730), (300, 1690), (150, 1670)]
# (the dots thin out in places: the area where they lie closed over STIP_CLOSE plate px, its holes filled). A dot
# spans at most STIP_SIDE plate px: the veins of the feet, grey strokes as small, are longer
STIP_DOT, STIP_D, STIP_T, STIP_R, STIP_CLOSE, STIP_SIDE, STIP_LOW, STIP_EDGE = 60, 0.02, 135, 6, 8, 8, 0.004, 5
STIP_MIN = 1500
# the right foot over the patch (a polygon inside its outline, plate px): its veins break into dot-sized pieces. The
# patch's thin margins along the ground, where its dots thin out: the area grown by hysteresis down to STIP_LOW
STIP_KEEP = [(705, 1660), (800, 1632), (900, 1606), (960, 1592), (965, 1630), (900, 1680), (820, 1718), (745, 1730),
             (700, 1700)]
# the paint: dark areas whose core is darker than PAINT_CORE (the hair and beard read 33-41; the thinned paint's
# strands, Aegisthus' hair over his belly, 48-55, are wash)
PAINT_NEAR, PAINT_CORE = 7.6, 44
# the faces (boxes, plate px: the woman, Orestes, Aegisthus): at the line weight the woman's eye ran into a figure
# eight and Aegisthus' into a blot. Inside each box the lines are the plate's own at their own width, as orestes.py
FACES = [(740, 300, 860, 440), (1235, 330, 1345, 470), (1700, 560, 1830, 700)]
FACE_LO, FACE_HI, FACE_SPECK = 12, 22, 5.4
FACE_HM, FACE_MIN_R = 0.6, 3.8
DOT_LC, DOT_AREA, DOT_SIDE = 16, (7, 144), 15
# no dots in the floor band (below its top edge, read off the plate, less 4 px): its grain read as dots
NO_DOTS = [(150, 1651), (300, 1667), (600, 1708), (1100, 1770), (1400, 1776), (1700, 1765), (2000, 1714),
           (2300, 1643), (2476, 1606), (2476, 1890), (150, 1890)]
LINE_R = 4.75
LINE_LO, LINE_HI = 22, 34
# faint lines (the pale anatomy, the folds): local contrast over FAINT_LO/HI, kept where they run FAINT_LEN plate px
# or more along their centres and lie FAINT_CLEAR plate px off the lines already found
FAINT_LO, FAINT_HI, FAINT_LEN, FAINT_CLEAR = 9, 15, 30, 4
BLUR_S, BLUR_L, BLUR_F = 1.33, 1.52, 0.67  # plate px: Orestes' 0.7, 0.8, 0.35 at this scan's scale
WEIGHT = 0.0011                            # the line weight, of the longer side (F-R: John on Andromache)
# the wash: the thinned paint's strokes, darker by WASH_D than the clay round it (the plate blurred WASH_BLUR plate px,
# against its closing over WASH_R plate px), wider than WASH_W plate px; as bacchae.py, its lengths at this scan's scale
WASH_BLUR, WASH_R, WASH_D, WASH_W = 1.9, 30, 22, 5.7
WASH_MIN = 110                             # plate px^2: smaller pieces are specks of the print
WASH_A, WASH_D1, WASH_STEP, WASH_SIGMA = (0.15, 0.35), 60, 0.05, 3.8
# John's marks on pass 1, in PhotoCraft over the tool's grid (electra_eur_marks_1.png: his blue and yellow, read off
# every layer, 2026-10-15; "additive"): blue ink to add (his strokes
# as he painted them, at their own width); yellow is clay: the area round each yellow mark that the lines
# and his blue close off (within YELLOW_R plate px of it) joins the figure, its outline his blue where it runs there
# Round 2 on pass 2 (electra_eur_marks_2.png, all blue, on the red layer): the woman's profile, lips and fingers, Orestes'
# eyelids, sideburn and neck
MARKS_FILES = [Path(__file__).parent / "electra_eur_marks_1.png", Path(__file__).parent / "electra_eur_marks_2.png"]
YELLOW_R = 25
BLUE_CLEAR = 1.5


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def poly(shape, pts):
    """A polygon given in plate px, as a mask at UP."""
    p = np.asarray(pts, float)
    rr, cc = draw.polygon((p[:, 1] - Y0 + 0.5) * UP - 0.5, (p[:, 0] - X0 + 0.5) * UP - 0.5, shape)
    m = np.zeros(shape, bool)
    m[rr, cc] = True
    return m


def add_wash(svg, wash, depth, box):
    """The wash, as bacchae.add_wash."""
    x0, y0, x1, y1 = box
    b, dp, s = wash[y0:y1, x0:x1], depth[y0:y1, x0:x1], WASH_SIGMA * UP
    dpt = ndi.gaussian_filter(np.where(b, dp, 0), s) / np.maximum(ndi.gaussian_filter(b.astype(np.float32), s), 1e-6)
    (a0, a1) = WASH_A
    alpha = a0 + (a1 - a0) * np.clip((dpt - WASH_D) / (WASH_D1 - WASH_D), 0, 1)
    paths, below = '', 0.0
    for a in np.arange(a0, a1 + 1e-9, WASH_STEP):
        m = b & (alpha >= a - WASH_STEP / 2)
        if not m.any():
            break
        d, _ = lw.potrace_d(m, turdsize=20, alphamax=1.0)
        paths += (f'<path class="tone" fill="currentColor" fill-opacity="{1 - (1 - a) / (1 - below):.3f}" '
                  f'stroke="none" d="{d}"/>')
        below = a
    svg.write_text(svg.read_text().replace('<path class="lines"', paths + '<path class="lines"', 1))


def nearest(lab, x, y, r=30):
    """The label at or nearest plate (x, y), within r plate px (0 if none)."""
    r = round(r * UP)
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = lab[max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1]
    oy, ox = max(cy - r, 0) - (cy - r), max(cx - r, 0) - (cx - r)
    dist = np.hypot(*np.mgrid[-r + oy:-r + oy + win.shape[0], -r + ox:-r + ox + win.shape[1]])
    iy, ix = np.unravel_index(np.argmin(np.where(win > 0, dist, np.inf)), win.shape)
    return win[iy, ix]


def disk(v):
    return morphology.disk(max(1, round(v * UP)))


def main(src, qa=None, test=None, out=None, diag=False):
    global X0, Y0, X1, Y1
    out = Path(out) if out else OUT
    if test:
        X0, Y0, X1, Y1 = (int(v) for v in test.split(','))
    inbox = lambda x, y: X0 <= x < X1 and Y0 <= y < Y1
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": round(w * UP), "height": round(h * UP), "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": BLUR_S * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": BLUR_L * UP}))
        r = round(LINE_R * UP)
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        pc(t / "gl.png", t / "gmin.png", ("filter.other.minimum", {"radius": round(FACE_MIN_R * UP),
                                                                     "preserve": "roundness"}))
        pc(t / "up.png", t / "gf.png", ("filter.blur.gaussianBlur", {"radius": BLUR_F * UP}))
        pc(t / "gf.png", t / "fine.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "gf.png", t / "stip.png", ("image.adjustments.threshold", {"level": STIP_T}))
        pc(t / "up.png", t / "gw.png", ("filter.blur.gaussianBlur", {"radius": WASH_BLUR * UP}))
        r = round(WASH_R * UP)
        pc(t / "gw.png", t / "wclosed.png", ("filter.other.maximum", {"radius": r, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "roundness"}))
        gw, wclosed = grey(t / "gw.png"), grey(t / "wclosed.png")
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        gs = grey(t / "gs.png")
        gmin = grey(t / "gmin.png")
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
        marks = grey(t / "stip.png") < 128
    H, W = g.shape
    outside = poly(g.shape, CUTS['left']) | poly(g.shape, CUTS['right']) | poly(g.shape, CUTS['top'])
    lc = closed - gl

    # the worn patch: light areas closed off by the long marks, thick with small ones
    stip = poly(g.shape, STIPPLE)
    lab, n = ndi.label(marks)
    size = np.bincount(lab.ravel()) / UP ** 2
    side = np.array([0] + [max(q[0].stop - q[0].start, q[1].stop - q[1].start) / UP for q in ndi.find_objects(lab)])
    small = ((size <= STIP_DOT) & (side <= STIP_SIDE))[lab] & marks
    long_ = marks & ~small
    with tempfile.TemporaryDirectory() as td:   # (the share of the light round each px that is dots: near the ground
        t = Path(td)                             # and the lines, a plain blur of the dots fell off and left a margin)
        Image.fromarray((small * 255).astype(np.uint8)).save(t / "dots.png")
        Image.fromarray((~long_ * 255).astype(np.uint8)).save(t / "light.png")
        for nm in ("dots", "light"):
            pc(t / f"{nm}.png", t / f"{nm}_b.png", ("filter.blur.gaussianBlur", {"radius": STIP_R * UP}))
        dens = grey(t / "dots_b.png") / np.maximum(grey(t / "light_b.png"), 8)
    keep = poly(g.shape, STIP_KEEP)
    worn = ndi.binary_fill_holes(ndi.binary_closing(dens > STIP_D, structure=disk(STIP_CLOSE)) & stip & ~long_)
    worn = apply_hysteresis_threshold(np.where(worn, 1.0, dens), STIP_LOW, STIP_D) & stip & ~long_ & ~keep
    # (slivers of the patch left between it and the ground or a line, within STIP_EDGE plate px of it)
    worn |= ndi.binary_closing(worn | dark0 | long_, structure=disk(STIP_EDGE)) & ndi.binary_dilation(
        worn, structure=disk(STIP_EDGE)) & stip & ~long_ & ~keep
    worn = morphology.remove_small_objects(worn, max_size=round(STIP_MIN * UP * UP))   # (specks in the floor band)
    dark0 |= worn
    fine |= worn

    dark = ndi.binary_opening(dark0, structure=disk(2 * 1.9)) & ~outside
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        if inbox(x, y):
            i = nearest(lab, x, y)
            assert i, f'no dark area near {(x, y)}'
            is_ground[i] = True
    ground = is_ground[lab]
    dlab = lab

    lab, _ = ndi.label(~ground & ~outside)
    keep = {nearest(lab, x, y) for x, y in SEEDS if inbox(x, y)}
    assert 0 not in keep, keep
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground & ~outside
    fig = ndi.binary_opening(fig, structure=disk(1.9))
    # (the fill also took in the clay islands left in the pockets, the painted names: only what the seeds reach)
    lab, _ = ndi.label(fig)
    fig = np.isin(lab, list({nearest(lab, x, y) for x, y in SEEDS if inbox(x, y)}))
    blue, yellow = np.zeros_like(fig), np.zeros_like(fig)
    for mf in MARKS_FILES:
        m = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
        assert m.shape[:2] == fig.shape, (m.shape, fig.shape)
        r, gg, bb, al = (m[..., i] for i in range(4))
        blue |= (al > 40) & (bb > r + 40) & (bb > gg + 20)
        yellow |= (al > 40) & (r > 150) & (gg > 150) & (bb < 100)

    if diag:   # the figure tinted, the ground blue, the dark areas inside the figure numbered by size (plate px)
        rgb = np.dstack([g] * 3).astype(np.float32)
        rgb[fig] = rgb[fig] * 0.7 + np.array([255, 200, 120]) * 0.3
        rgb[ground] = rgb[ground] * 0.5 + np.array([40, 90, 255]) * 0.5
        rgb[outside] *= 0.4
        rgb[worn] = rgb[worn] * 0.4 + np.array([0, 255, 0]) * 0.6
        lab2, n2 = ndi.label(dark & fig)
        sz = np.bincount(lab2.ravel()) / UP ** 2
        big = [i for i in range(1, n2 + 1) if sz[i] > 400]
        im = Image.fromarray(rgb.clip(0, 255).astype(np.uint8))
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        from PIL import ImageFont
        font = ImageFont.load_default(size=40)
        for i in big:
            yy, xx = np.nonzero(lab2 == i)
            k = len(yy) // 2
            px, py = xx[k] / UP + X0, yy[k] / UP + Y0
            d.text((xx[k], yy[k]), str(i), fill=(255, 0, 0), font=font)
            print(i, round(px), round(py), round(sz[i]))
        im.save(qa)
        print('dark areas in the figure over 400 plate px:', len(big))
        return

    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    paint = fine & ndi.binary_dilation(solid, iterations=round(PAINT_NEAR * UP)) & fig

    ys, xs = np.nonzero(fig)
    tw = WEIGHT * max(np.ptp(ys), np.ptp(xs))   # the line width, work px (taken before his clay: pass 1's weight)
    if test:   # a test box: the weight the whole panel gives
        tw = WEIGHT * (X1_FULL - X0_FULL) * UP
    # his blue as he painted it, at its own width (John, 2026-10-15: "all ink is drawn by me to it's proper width";
    # drawn along its centres at the line weight, the hair curl he widened came out thin), pinholes filled
    blue_ink = blue | (ndi.binary_fill_holes(blue) & ~morphology.remove_small_objects(
        ndi.binary_fill_holes(blue) & ~blue, max_size=round(4 * UP * UP)))
    if yellow.any():   # his clay: what the figure's edge, the plate's lines and his blue close off round each mark
        barrier = blue_ink | (~fig & (ndi.distance_transform_edt(~fig) <= tw)) | outside | \
            (apply_hysteresis_threshold(lc, LINE_LO, LINE_HI) & ~fig)
        lab, _ = ndi.label(~barrier & ndi.binary_dilation(yellow, structure=disk(YELLOW_R)))
        clay = np.isin(lab, np.unique(lab[yellow & (lab > 0)])) | (yellow & ~blue_ink)
        clay = ndi.binary_closing(clay, structure=disk(1.9)) & ~blue_ink
        # (to his line's centre, so the body's trace stops there)
        clay |= ndi.binary_dilation(clay, structure=morphology.disk(round(tw / 2))) & blue_ink
        fig |= clay
        paint &= ~clay
    firm = apply_hysteresis_threshold(lc, LINE_LO, LINE_HI)
    black = firm & fig & ~ndi.binary_dilation(paint, iterations=round(UP))
    lines = centre_lines(black, tw, round(3 * 1.9 * UP), 2 * tw) | paint
    faint = apply_hysteresis_threshold(lc, FAINT_LO, FAINT_HI) & fig & \
        ~ndi.binary_dilation(black | paint, structure=disk(FAINT_CLEAR))
    lines |= centre_lines(faint, tw, round(FAINT_LEN * UP), 2 * tw)
    box_mask = lambda boxes: np.any([poly(g.shape, [(a, b), (c, b), (c, d), (a, d)]) for a, b, c, d in boxes],
                                    axis=0) if boxes else np.zeros_like(fig)
    # the dots: small dark marks of the fine threshold standing alone in the clay
    lab, n = ndi.label((lc > DOT_LC) & fig & ~paint)
    if n:
        area = np.bincount(lab.ravel()) / (UP * UP)
        sides = np.array([0] + [max(s[0].stop - s[0].start, s[1].stop - s[1].start) / UP
                                for s in ndi.find_objects(lab)])
        dot = (area >= DOT_AREA[0]) & (area <= DOT_AREA[1]) & (sides <= DOT_SIDE)
        dot[0] = False
        lines |= dot[lab] & ~ndi.binary_dilation(lines, iterations=round(UP)) & ~poly(g.shape, NO_DOTS)
    # the faces: the plate's own dark at its own width
    faces = box_mask(FACES)
    hm = gl < closed - FACE_HM * (closed - gmin)
    face_lines = morphology.remove_small_objects(apply_hysteresis_threshold(lc, FACE_LO, FACE_HI) & hm & fig & faces,
                                                 max_size=round(FACE_SPECK * UP * UP))
    lines = np.where(faces & ~paint, face_lines, lines)
    dt = ndi.distance_transform_edt(~fig)
    # (where his blue is the outline, the edge would run on half a line past it)
    edge = ~fig & (dt <= tw) & ~outside & ~ndi.binary_dilation(blue_ink, structure=morphology.disk(round(tw / 2)))
    # (his blue drawn as he drew it, my lines within BLUE_CLEAR line widths of its centre taken out, or a line he
    # traced over mine is drawn twice and runs into a blot: Mika, 2026-10-14)
    near_blue = ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= BLUE_CLEAR * tw if blue.any() else blue
    ink = (lines & fig & ~near_blue) | (edge & ~near_blue) | blue_ink
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * 1.9 ** 2 * UP * UP)[lab]

    # (the lines as drawn are taken out before the opening, which then leaves only broad strokes, as bacchae.py)
    w0 = fig & (wclosed - gw > WASH_D) & ~paint
    wash = ndi.binary_opening(w0 & ~ndi.binary_dilation(lines, iterations=round(UP / 2)),
                              structure=disk(WASH_W / 2))
    wash = ndi.binary_closing(wash, structure=disk(2 * 1.9)) & w0
    wash = morphology.remove_small_objects(wash, max_size=round(WASH_MIN * UP * UP))

    info = lw.trace_svg(
        ink, out, body=fig, open_holes=~fig, weight="drawn",
        title='Orestes kills Aegisthus',
        desc='Line drawing after Karl Reichhold\'s drawing of the Berlin Painter\'s pelike, Vienna, Kunsthistorisches '
             'Museum IV 3725 (Furtwängler and Reichhold, Griechische Vasenmalerei II, Taf. 72); cut out and retraced.')
    if wash.any():
        add_wash(out, wash, wclosed - gw, info['box'])
    print(out, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, out, info['box'], Path(qa))
        lw.qa_dark(out, info['box'], Path(qa).with_suffix('.dark.png'))


X0_FULL, X1_FULL = X0, X1

if __name__ == '__main__':
    a = sys.argv[1:]
    test = out = None
    diag = '--diag' in a
    if diag:
        a.remove('--diag')
    if '--test' in a:
        i = a.index('--test')
        test, out = a[i + 1], a[i + 2]
        del a[i:i + 3]
    main(*a[:2], test=test, out=out, diag=diag)
