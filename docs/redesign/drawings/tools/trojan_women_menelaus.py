"""Trojan Women: Menelaus at Troy, his sword fallen at his feet, between Helen (right, her hand
raised) and a woman running from him (left), from the lower picture (fig. 4) of Gerhard,
Auserlesene griechische Vasenbilder III (1847), Taf. CLXIX, as scanned by Heidelberg University
Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_169.jpg/full/full/0/default.jpg
(2078 x 2869; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0216)

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the
crop, the enlargement, the grey, the blurs, the Maximum and Minimum filters and the thresholds.
numpy only combines the masks PhotoCraft made (labels, unions, the difference of two images,
hysteresis) and measures. The SVG is written by linework.trace_svg, as for every Gerhard plate.

Plate -> drawing, as for Hippolytus (tools/hippolytus.py): the plate prints the black ground
black, so the figures' outline comes free.
  - Ground: the dark of the plate, its thin lines opened away; the large areas, and the pockets
    of ground the figures close in (POCKETS). Smaller dark areas inside the figures are paint.
  - The scene is the clay area the ground leaves, from SEEDS. Below the panel's lower edge is
    paper (BOTTOM): the soles stand on a thin strip of black above it.
  - Lines: the plate's dark lines inside the figures (local contrast: the plate's Maximum then
    Minimum, less the plate), the outline, and the plate's solid paint.
  - Dark theme: the figures' area is the body; the ground pockets stay open, as on the vase.

    python3 docs/redesign/drawings/tools/trojan_women_menelaus.py gerhard1847bd3_169.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "trojan-women.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

X0, Y0, X1, Y1 = 153, 1392, 1858, 2512    # crop in plate px: the panel, inside its left, top and right edges
# the panel's lower edge: the last row of its black, y = a + b x (plate px; fitted to every column,
# within 2.4 px); paper below it
BOTTOM = (2507.09, -0.005377)
UP = 3                                    # work at 3x the plate's px, so curves stay smooth
DARK = 85                                 # ground and solid paint: darker than this (grey, lightly smoothed)
AUTO_GROUND = 10000                       # plate px: dark areas this large, reaching the panel's edge, are ground
# her dress (left), his chest, Helen's dress, the sword's blade, the shield's rim (a black band
# parts it from the shield's face), the end of Helen's mantle between the shield and her, and the
# strip of it outside her zigzag hem (plate px)
SEEDS = [(500, 1980), (1020, 1840), (1540, 2180), (720, 2140), (1350, 1789), (1357, 2136), (1395, 2060)]
# pockets of ground the figures close in (a point in each, plate px): between Helen's arm and her side
POCKETS = [(1686, 2019)]
# Black borders that run into the ground: the band inside the shield's rim (at both ends, where the
# rim thins out to a faint clay line), Helen's zigzag hem (at both ends, and where it turns between
# two clay tips), the hem of her overfold where it runs into the pocket at her side, and the left
# woman's zigzag hem (at its lower end, its tassel). WALLS (plate px) part them from the ground, WALL_W px wide: along the
# faint clay line, or across the border's end along the figure's edge.
WALLS = [[(1120, 1607), (1128, 1602), (1137, 1597)], [(1306, 2098), (1316, 2091), (1327, 2079)],
         [(1403, 2019), (1412, 2011)], [(1366, 2105), (1369, 2100), (1373, 2095)], [(1292, 2255), (1290, 2266)], [(1638, 2071), (1636, 2082)],
         [(395, 1899), (419, 1896)]]
WALL_W = 1.5


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def up(pts):
    return np.array([((x - X0) * UP, (y - Y0) * UP) for x, y in pts], float)


def polyline(pts):
    """Hand-placed points (plate px) joined by straight lines, a point per UP px, (x, y) at UP."""
    P = up(pts)
    return np.vstack([np.linspace(a, b, int(np.hypot(*(b - a))) + 2) for a, b in zip(P[:-1], P[1:])]) + 0.5


def along(shape, path, width):
    """A line `width` plate px wide along a path (x, y at UP)."""
    m = np.zeros(shape, bool)
    yx = (path[:, ::-1] - 0.5).astype(int)
    m[yx[:, 0], yx[:, 1]] = True
    return ndi.distance_transform_edt(~m) <= width * UP / 2


def ink_lines(g_blur, closed, low, high):
    """lw.ink_lines on PhotoCraft's images: the blurred plate's closing (Maximum then Minimum)
    less the blurred plate, with hysteresis."""
    return apply_hysteresis_threshold(closed - g_blur, low, high)


def main(src, qa=None, dump=None):
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gs.png", ("filter.blur.gaussianBlur", {"radius": 0.7 * UP}))
        pc(t / "gs.png", t / "dark.png", ("image.adjustments.threshold", {"level": DARK}))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        r = (9 * UP) // 2
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        dark0 = grey(t / "dark.png") < 128
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]

    # outside: the paper below the panel (the first light row under the black strip, column by column)
    a, b = BOTTOM
    outside = (yy + 0.5) / UP - 0.5 + Y0 > a + b * ((xx + 0.5) / UP - 0.5 + X0) + 0.5

    dark = ndi.binary_opening(dark0, structure=morphology.disk(2 * UP)) & ~outside
    for pts in WALLS:
        dark &= ~along(g.shape, polyline(pts), WALL_W)
    lab, _ = ndi.label(dark)
    size = np.bincount(lab.ravel())
    size[0] = 0
    rim = np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[ndi.binary_dilation(outside, iterations=2) | (yy >= H - 1)]])
    is_ground = (size > AUTO_GROUND * UP * UP) & np.isin(np.arange(len(size)), rim)
    for x, y in POCKETS:
        k = lab[(y - Y0) * UP, (x - X0) * UP]
        assert k, f'pocket point {(x, y)} is not on dark'
        is_ground[k] = True
    ground = is_ground[lab]
    paint = dark & ~ground

    lab, _ = ndi.label(~ground & ~outside)
    keep = {lab[(y - Y0) * UP, (x - X0) * UP] for x, y in SEEDS}
    assert 0 not in keep
    sz = np.bincount(lab.ravel())
    for k, sl in enumerate(ndi.find_objects(lab), 1):   # (check: clay left out)
        if k not in keep and sz[k] > 50 * UP * UP:
            print('unseeded clay', sz[k] // (UP * UP), X0 + sl[1].start // UP, Y0 + sl[0].start // UP,
                  X0 + sl[1].stop // UP, Y0 + sl[0].stop // UP)
    fig = np.isin(lab, list(keep))
    fig = ndi.binary_fill_holes(fig) & ~ground
    ridge = (g - ndi.grey_opening(g, size=(5 * UP, 5 * UP))) > 50
    fig = ndi.binary_opening(fig, structure=morphology.disk(UP)) | (fig & ridge)

    firm = ink_lines(gl, closed, 22, 34)
    lines = firm & fig
    lines |= (ndi.distance_transform_edt(~morphology.skeletonize(lines)) <= UP) & fig
    solid = paint & fig
    lab, _ = ndi.label(solid)
    solid &= (np.bincount(lab.ravel()) > 30 * UP * UP)[lab]
    edge = fig & ~ndi.binary_erosion(fig, iterations=int(2.5 * UP))
    ink = lines | solid | edge
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 12 * UP * UP)[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), fig=fig, ground=ground, ink=ink, paint=paint)

    held = ndi.binary_fill_holes(fig) & ground
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=held, weight="own",
        title='Menelaus dropping his sword at the sight of Helen',
        desc='Line drawing after the 1847 plate of a red-figure amphora (Gerhard, Auserlesene griechische '
             'Vasenbilder III, Taf. CLXIX, 4); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
