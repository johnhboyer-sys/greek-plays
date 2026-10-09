"""Lysistrata: five women carrying water jars at a fountain, from the lower picture (fig. 2) of
Gerhard, Auserlesene griechische Vasenbilder IV (Berlin, 1858), Taf. CCCVIII, as scanned by Heidelberg
University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1858bd4%3ATafel_308.jpg/full/full/0/default.jpg
(1995 x 2680; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1858bd4/0200)
The vase: a black-figure hydria; its picture of women fetching water at a fountain house, each named
by an inscription. John's pick (2026-10-08: "do water carriers, and include them all. It's a CHORUS"):
the five women, without the fountain house ("Out").

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop,
the enlargement, the grey, the warm channel (Channel Mixer), the blurs and the thresholds. numpy only
combines the masks PhotoCraft made (labels, unions, distances, fills) and measures; the cuts are
geometry. The SVG is written in the house format directly, as for Seven (tools/seven.py): linework's
trace_svg takes off the clay rim outside the lines that the dark theme needs here.

Plate -> drawing, black-figure, drawn as silhouettes as on Seven (John's choice there, 2026-10-07):
  - Ground: the orange clay (warm: red less blue over WARM_T), opened so thin marks do not join it; its
    large areas, and the pockets the figures close in (POCKETS).
  - The women: all else, joined to SEEDS (one point in each). The inscriptions and the fountain house
    touch none of them, but for the first woman's heel, which stands against the fountain's basin: cut
    straight along it (LEFT). The frame is left out (TOP, RIGHT), and the ground line under the feet
    (FLOOR, its top edge).
  - The black is drawn black. Open in it: the incisions, the dots and crosses, the hatched fillets and
    bands (light marks: lighter than BLACK_T, at least LINE_W wide), and the added white of the women's
    skin, with the dark lines drawn on it (eyes, mouths, fingers). Where the white meets the ground, an
    outline LINE_W wide just outside it.
  - Dark theme: the women's area is clay, a RIM wider than the black, so the black reads on the dark
    page; the marks and the skin show clay.

    python3 docs/redesign/drawings/tools/lysistrata.py gerhard1858bd4_308.jpg [qa.png]
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

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "lysistrata.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 560, 1120, 1970, 2180    # crop in plate px: the picture, inside its frame
UP = 3                                    # work at 3x the plate's px
# the ground line's top edge: y = quadratic in (x - 1270) (plate px, grey 100; fitted to 392 columns of
# clay above it, within 1.4 px): below it, out
FLOOR = (2.14e-06, 0.00718517, 2160.6140504)
FLOOR_CLEAR = 1.0                         # plate px: the cut runs this far above it
# the fountain house: left of LEFT[0] plate px above y = LEFT[2], left of LEFT[1] below it. The column's
# edge is at 577-579 and the first woman's fingertips 4 px from it; her heel meets the basin at 573.5
LEFT = (579.5, 573.5, 2140)
# the frame's top border, its lower edge y = a x + b, and its right border, its inner edge x = a y + b
# (plate px, grey 90; within 1.5 px): beyond them, out. Two jars come within 10 px of the top, the last
# woman's fingers within 5 px of the right, and the paper beyond the border reads as white
TOP = (0.00698, 1131.65)
TOP_CLEAR = 1.5
RIGHT = (-0.0478, 2018.5)
WARM_T = 40                               # clay: red less blue over this (clay 70-75, black and white 0-5)
BLACK_T = 100                             # the black: darker than this (grey, lightly smoothed)
WHITE_T = 175                             # the added white: lighter than this, and not warm
AUTO_GROUND = 2000                        # plate px: clay areas this large are ground
POCKETS = []                              # pockets of ground the women close in (a point in each, plate px)
# a point in each woman (plate px), left to right: on her dress
SEEDS = [(700, 1900), (900, 1900), (1110, 1900), (1360, 1900), (1700, 1900)]
LINE_W = 1.5                              # plate px: the outline and the thinnest mark
RIM = 1.5                                 # plate px: the clay round the black on the dark theme
GRAIN = 6                                 # plate px^2: light specks in the black smaller than this are grain
# The finest incisions (the meander on the third woman's mantle, 1-1.5 px, grey 70-120 in the black) broke
# into dashes at BLACK_T. They are found on the plate smoothed along its own strokes (PhotoCraft's Motion
# Blur, ORIENT_D plate px long, at every ORIENT_STEP degrees, each pixel taking the blur at its strokes'
# direction: the structure tensor's, measured in numpy), as its white top-hat (less its Minimum then
# Maximum over 1 plate px) over MARK_T
ORIENT_D, ORIENT_STEP = 4, 15
MARK_T = 22
# The dark lines drawn on the skin (brows, eyes, mouths, the necks' and fingers' lines) print fine and
# grey: on the skin and within LINE_NEAR plate px of it, the plate's black top-hat (its Maximum then
# Minimum over 2 plate px, less it) over SKIN_T, at least LINE_W wide
SKIN_T, LINE_NEAR = 30, 2
# The clay between the fingers (gaps 2-4 px wide) is too small for the ground's opening and stayed in
# the women; the skin-line finder then took it for dark lines and drew black wedges between the fingers.
# Clay (warm) within NOTCH_NEAR plate px of the skin that opens onto the ground is ground; the skin-line
# finder takes no clay
NOTCH_NEAR = 3
# The skin's soft edge (grey between the white and its printed contour) is the skin's: left open, it drew
# a second outline beside the contour (the thumbs). Neither black nor clay, within SOFT plate px of it
SOFT = 2
# The hands, arms and feet (John, 2026-10-08, on pass 1: "hands. and some lines could be smoother"): the
# plate's contours round the skin and between the fingers print uneven, broken and specked, 1-3 px; drawn
# as printed, or along their centres or their midline, they came out lumpy or broken. Here the outline is
# drawn from the skin's shape (its light, the thin fingertips too): the skin closed over the thin dark lines inside it (SIL_CLOSE plate px,
# never over clay), its holes filled, smoothed (PhotoCraft: Gaussian Blur SIL_SMOOTH plate px, Threshold);
# the outline is an even band LINE_W wide just outside it, and the rest of the printed band is the figure's
# (clay on the dark theme). The lines inside the shape (between the fingers, the thumb's crease) are the
# dark it closes in, along their centres, LINE_W wide, pieces under INNER_MIN plate px long going as specks.
# All this within CONTOUR_NEAR plate px of the skin, apart from the wide black (the dresses, hair and jars:
# what survives an opening of WIDE plate px). The faces keep the plate's own lines, which came out clean,
# with the skin's outline: the skin of each head, found from a point on each cheek (FACE_PTS)
SIL_CLOSE, SIL_SMOOTH, INNER_MIN = 0, 1.0, 4
# the lines inside: darker than INNER_T, or the black top-hat over SKIN_T; pieces of the skin's shape smaller
# than SIL_MIN plate px^2 (the print's specks of white at the fingertips) go with their outline
INNER_T, SIL_MIN = 160, 40
CONTOUR_NEAR, WIDE = 6, 2
FACE_PTS = [(700, 1400), (960, 1440), (1150, 1360), (1480, 1400), (1760, 1380)]
# John's traces (2026-10-09, after pass 2: "i'll need to trace some in photocraft myself"): the lowered hands,
# drawn in red in PhotoCraft on a layer over the picture at 3x (this tool's own grid: no registration);
# lysistrata_traces.json holds his strokes as polylines along their centres, plate px. His strokes are drawn
# LINE_W wide; within TRACE_NEAR plate px of them, and inside the shapes they close (his fingers), my lines
# go, but for the wide black (the mantle the third woman's hand lies on), and but round the open ends of his
# strokes (TRACE_NEAR + 1 plate px), where my outline runs on to meet them (cleared there, it left gaps); what
# his lines close is skin
TRACES_FILE = Path(__file__).parent / "lysistrata_traces.json"
TRACE_NEAR = 2.5
# Every line's edge is smoothed before tracing (PhotoCraft: Gaussian Blur SMOOTH plate px, then Threshold
# at half): the print's grain left the edges ragged (John: "some lines could be smoother")
SMOOTH = 0.5


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def pc_mask(m, *steps):
    """A mask run through PhotoCraft (steps as for pc), back as a mask (grey 128 and over)."""
    with tempfile.TemporaryDirectory() as td:
        a, b = Path(td) / "m.png", Path(td) / "o.png"
        Image.fromarray(m.astype(np.uint8) * 255).save(a)
        pc(a, b, *steps)
        return grey(b) >= 128


def smooth(m, r):
    """m with its edges smoothed: PhotoCraft's Gaussian Blur r plate px, then Threshold at half."""
    return pc_mask(m, ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": r * UP}),
                   ("image.adjustments.threshold", {"level": 128}))


def centre_lines(mask, t, spur):
    """mask redrawn along its centre line, t px wide, less spurs shorter than spur px (as andromache.py)."""
    n8 = np.ones((3, 3), int)
    sk = morphology.skeletonize(mask)
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
    return ndi.distance_transform_edt(~sk) <= t / 2


def polyline(pts):
    """Points (plate px) joined by straight lines, a point per work px, (x, y) at UP."""
    P = np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = np.clip((path[:, ::-1] - 0.5).astype(int), 0, np.array(shape) - 1)
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def thick(m, w):
    """m, every part at least w plate px wide (thin marks widened along their centres)."""
    return m | (ndi.distance_transform_edt(~morphology.skeletonize(m)) <= w * UP / 2)


def oriented(t, src_png, name):
    """src_png smoothed along its own strokes (ORIENT_*): PhotoCraft's Motion Blur at each angle; numpy picks,
    per pixel, the blur at the strokes' direction (as the Falerii pass did)."""
    g = grey(src_png)
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(src_png, t / f"{name}{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    mb = np.stack([grey(t / f"{name}{a}.png") for a in angs])
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    out = np.take_along_axis(mb, i[None], 0)[0]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(t / f"{name}.png")
    return t / f"{name}.png"


def write_svg(lines, body, out, title, desc):
    """The house format (as linework.trace_svg writes it): 1000 units tall, the body path under the lines,
    traced at the work px (as seven.py)."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "up.png", t / "warm.png", ("image.adjustments.channelMixer", {"gray": [100, 0, -100, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "L.png", t / "black.png", ("image.adjustments.threshold", {"level": BLACK_T}))
        pc(t / "L.png", t / "light.png", ("image.adjustments.threshold", {"level": WHITE_T}))
        pc(t / "warm.png", t / "clay.png", ("image.adjustments.threshold", {"level": WARM_T}))
        Lo = oriented(t, t / "L.png", "Lo")
        pc(Lo, t / "Lo_open.png", ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}))
        pc(t / "L.png", t / "L_close.png", ("filter.other.maximum", {"radius": 2 * UP, "preserve": "roundness"}),
           ("filter.other.minimum", {"radius": 2 * UP, "preserve": "roundness"}))
        L = grey(t / "L.png")
        light_hat = grey(Lo) - grey(t / "Lo_open.png")
        dark_hat = grey(t / "L_close.png") - L
        black = grey(t / "black.png") < 128
        light = grey(t / "light.png") >= 128
        clay = grey(t / "clay.png") >= 128
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    below = py > np.polyval(FLOOR, px - 1270) - FLOOR_CLEAR
    frame = (px < np.where(py < LEFT[2], LEFT[0], LEFT[1])) | (py < TOP[0] * px + TOP[1] + TOP_CLEAR) | (px > RIGHT[0] * py + RIGHT[1] - 2.0)
    outside = below | frame

    # ground: the clay, opened so thin marks do not join it; its large areas and the pockets
    ground0 = ndi.binary_opening(clay & ~outside, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]

    # the women: all else, joined to the seeds
    lab, _ = ndi.label(ndi.binary_opening(~ground & ~outside, structure=morphology.disk(UP)))
    keep = {lab[round((y - Y0) * UP), round((x - X0) * UP)] for x, y in SEEDS}
    assert 0 not in keep, 'a seed is off the figures'
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: what is left out)
        if k not in keep and sz[k] > 200 * UP * UP:
            print('left out', sz[k] // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP,
                  X0 + sl[1].stop // UP, Y0 + sl[0].stop // UP)
    fig = ndi.binary_fill_holes(np.isin(lab, list(keep))) & ~ground & ~outside
    hl, _ = ndi.label(ndi.binary_fill_holes(fig) & ~fig & ~outside)
    for k, sl in enumerate(ndi.find_objects(hl), 1):     # (check: ground the women close in)
        n = (hl[sl] == k).sum()
        if n > 30 * UP * UP:
            print('closed in', n // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP)

    # the added white (skin): light, not warm, inside the women
    white = light & ~clay & fig
    white_raw = white.copy()   # (before the opening: the fingertips are 2-3 px wide)
    white = ndi.binary_opening(white, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    white0 = white.copy()   # (before its soft edge: the grey lines between the fingers are not skin)
    white |= fig & ~black & ~clay & (ndi.distance_transform_edt(~white) <= SOFT * UP)
    notch = fig & clay & (ndi.distance_transform_edt(~white) <= NOTCH_NEAR * UP)
    lab, n = ndi.label(notch)
    opens = np.zeros(n + 1, bool)
    opens[np.unique(lab[ndi.binary_dilation(ground, iterations=2) & notch])] = True
    opens[0] = False
    notch = opens[lab]
    fig &= ~notch
    ground |= notch
    # the black: the dark of the women; light specks in it smaller than GRAIN are grain
    a_black = black & fig
    holes = fig & ~a_black & ~white
    lab, _ = ndi.label(holes)
    a_black |= (np.bincount(lab.ravel()) < GRAIN * UP * UP)[lab] & holes
    # the marks in the black (all of the women that is neither black nor white) at least LINE_W wide
    marks = (fig & ~a_black & ~white) | (fig & ~white & (light_hat > MARK_T))
    lab, _ = ndi.label(marks)
    marks &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    marks = thick(marks, LINE_W) & fig & ~white
    a_black &= ~marks
    # the dark lines on the skin; the skin outlined where it meets the ground, just outside it (under the
    # feet, along the ground line)
    near = ndi.distance_transform_edt(~white) <= LINE_NEAR * UP
    skin_lines = thick((dark_hat > SKIN_T) & near & ~outside & ~clay, LINE_W) & near & ~frame & ~notch
    outline = ~fig & ~frame & (ndi.distance_transform_edt(~white) <= LINE_W * UP)
    lines = a_black | outline | skin_lines
    # the outline of the hands, arms and feet, from the skin's smoothed shape
    lab, _ = ndi.label(white)
    heads = {lab[round((y - Y0) * UP), round((x - X0) * UP)] for x, y in FACE_PTS}
    assert 0 not in heads, 'a face point is off the skin'
    faces = ndi.distance_transform_edt(~np.isin(lab, list(heads))) <= (CONTOUR_NEAR + 1) * UP
    wide = ndi.binary_dilation(ndi.binary_opening(a_black, structure=morphology.disk(WIDE * UP)), iterations=UP)
    zone = (ndi.distance_transform_edt(~white) <= CONTOUR_NEAR * UP) & ~wide & ~faces & ~outside
    # (its soft edge left out: on the last woman's hand the grey between the fingers, 1-2 px, would fill in)
    skin = white0 | (white_raw & (ndi.distance_transform_edt(~white0) <= 4 * UP))
    sil = ndi.binary_closing(skin, structure=morphology.disk(SIL_CLOSE * UP)) if SIL_CLOSE else skin
    sil = smooth(ndi.binary_fill_holes((sil & ~clay) | skin), SIL_SMOOTH)
    lab, _ = ndi.label(sil)
    sil &= (np.bincount(lab.ravel()) >= SIL_MIN * UP * UP)[lab]
    ring = ~sil & (ndi.distance_transform_edt(~sil) <= LINE_W * UP)
    inner = centre_lines(sil & ~white0 & ~clay & ((L < INNER_T) | (dark_hat > SKIN_T)), LINE_W * UP, 3 * UP) & sil
    inner &= ~(ndi.distance_transform_edt(sil) <= LINE_W * UP)   # (not along the outline itself)
    lab, _ = ndi.label(inner)
    inner &= (np.bincount(lab.ravel()) >= INNER_MIN * LINE_W * UP * UP)[lab]
    fig |= zone & ~clay
    contour = (ring | inner) & ~frame
    lines = np.where(zone, contour, lines)
    fig |= contour & zone
    # John's traces (TRACES_FILE)
    his, ends = np.zeros(fig.shape, bool), np.zeros(fig.shape, bool)
    for part in json.loads(TRACES_FILE.read_text()).values():
        if isinstance(part, dict):
            for pts in part['lines']:
                his |= along(fig.shape, polyline(pts), LINE_W)
                if np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 2:   # an open stroke
                    for x, y in (pts[0], pts[-1]):
                        ends[min(max(round((y - Y0) * UP), 0), fig.shape[0] - 1),
                             min(max(round((x - X0) * UP), 0), fig.shape[1] - 1)] = True
    closed = ndi.binary_fill_holes(his) & ~his
    near_end = ndi.distance_transform_edt(~ends) <= (TRACE_NEAR + 1) * UP
    region = (((ndi.distance_transform_edt(~his) <= TRACE_NEAR * UP) & ~near_end) | closed)
    lines = np.where(region, his | (lines & wide), lines)
    fig |= his | closed
    lines = smooth(lines, SMOOTH) & ~frame
    body = (ndi.distance_transform_edt(~fig) <= RIM * UP) & ~frame
    if dump:
        np.savez_compressed(dump, L=L.astype(np.uint8), fig=fig, white=white, lines=lines, ground=ground, marks=marks)

    info = write_svg(
        lines, body, OUT,
        title='Women carrying water jars',
        desc='Line drawing after the 1858 plate of a black-figure hydria (Gerhard, Auserlesene griechische '
             'Vasenbilder IV, Taf. CCCVIII, 2): five women at a fountain; cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
