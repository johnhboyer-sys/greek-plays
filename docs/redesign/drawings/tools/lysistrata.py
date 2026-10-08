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


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


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
    frame = (px < np.where(py < LEFT[2], LEFT[0], LEFT[1])) | (py < TOP[0] * px + TOP[1] + TOP_CLEAR) | (px > RIGHT[0] * py + RIGHT[1] - 0.5)
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
    white = ndi.binary_opening(white, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
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
