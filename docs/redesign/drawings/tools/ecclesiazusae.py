"""Assemblywomen (Aristophanes): three comic actors, Philotimides, Charis and Xanthias, on a stage before a door.
From H. Heydemann, Die Phlyakendarstellungen auf bemalten Vasen (Neuntes Hallisches Winckelmannsprogramm, Halle 1884),
Taf. I; Heidelberg University Library's scan, hwpr1884 Tafel_01 (Tafel_01.jpg, 2449 x 2021, the largest it serves;
Public Domain Mark 1.0):
https://digi.ub.uni-heidelberg.de/iiif/2/hwpr1884%3A022_Tafel_01.jpg/full/full/0/default.jpg
The vase: the Caputi vase (Milan). The scene names no play: an old man, an old woman and a slave are stock types.

Made with PhotoCraft (John, 2026-10-07), as tools/persians.py: every image step runs in `photocraft-cli` (0.2.0).
Pillow only converts the JPEG to PNG and reads PhotoCraft's results; numpy and scipy only combine the masks
PhotoCraft made and measure. The SVG is written by linework.trace_svg.

Plate -> drawing. A contour plate in pen on cream paper (the same programme series and engraver's style as Persians).
John chose (2026-10-12): the three actors with the bench, the tray and the hanging flask, the stage and the door; the
painted names out; the hair as printed curls; Xanthias's beard as brushstrokes, a stepped wash (as Frogs' hair);
the style as Persians: pen lines at 0.8 plate px, the figures' area clay on the dark theme.

    python3 docs/redesign/drawings/tools/ecclesiazusae.py Tafel_01.jpg [qa.png] [dump.npz]
"""
import json
import os
import shutil
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

OUT = Path(__file__).resolve().parent.parent / "ecclesiazusae.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in plate px: the door, the flask, the three actors and the stage on its posts, above the vase's frame line
X0, Y0, X1, Y1 = 20, 195, 2420, 1830
UP = 3                                    # work at 3x the plate's px, as Persians (the curls are 1 px strokes)
BLUR = 0.5                                # plate px: the Gaussian before the line finder
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line
LOW, HIGH = 16, 34                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 120                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 1.5, 0.5                   # a line's core: the darkest px within CORE_R plate px; half maximum
SMOOTH = 0.6                              # plate px: the line mask's Gaussian, cut at half
SPECK = 2                                 # plate px^2: smaller pieces of ink are specks of the print
SEAL = 6                                  # plate px: passages narrower than this do not join ground to figure
# The heads (hair, curls, eyes, open mouths) are found by the main finder: a finer one inside boxes round the heads
# (less blur, a narrower core, as Eumenides' faces) took the grey shading between the curls for strokes and came
# out speckled (2026-10-12).
# Xanthias's beard is brushwork, not ink (John, 2026-10-12: "Make the beard into brushstrokes like with hair on other
# comedy plates"): inside BEARDS (polygons, plate px; the top edge between the lower lip's line, about y 644-647, and the beard's first strokes) the plate's lines go and its
# dark is a stepped wash in the line colour (BEARD_STEPS: grey under, the finder's 0.5 plate px blur; total opacity),
# as Frogs' hair and goatee; pieces under BEARD_MIN plate px^2 dropped
BEARDS = [[(2030, 650), (2045, 647), (2060, 646), (2085, 648), (2098, 649), (2112, 653), (2105, 668), (2095, 682), (2075, 695),
           (2058, 701), (2042, 698), (2033, 688), (2027, 672)]]
BEARD_STEPS = [(185, 0.25), (165, 0.45), (145, 0.62), (125, 0.76), (105, 0.86)]
BEARD_MIN = 1
# the painted names (boxes, plate px; John, 2026-10-12: out): ink pieces lying wholly inside are dropped
NAMES = [(800, 315, 1160, 365), (1488, 298, 1722, 348), (1978, 343, 2247, 414)]
# the vase's frame line, a double curve under the stage's posts (John chose the stage, not the frame): ink pieces
# lying wholly below FRAME_Y are dropped (the posts' lines run up into the platform)
FRAME_Y = 1700
# points on the ground (plate px): the paper areas they fall in are vase ground; every other area the lines close is
# clay; areas reaching the crop's edge are ground
GROUND = []
# specks of the print on the field: ink pieces under SPECK_MAX plate px^2 farther than NEAR plate px from the figures
SPECK_MAX, NEAR = 40, 6
# a development run on part of the plate: ECCL_BOX="x0,y0,x1,y1" (plate px); the drawing goes to ECCL_OUT
if os.environ.get("ECCL_BOX"):
    X0, Y0, X1, Y1 = map(int, os.environ["ECCL_BOX"].split(","))
    OUT = Path(os.environ["ECCL_OUT"])
WEIGHT = 0.8 / max(X1 - X0, Y1 - Y0)      # 0.8 plate px, as Persians (John, 2026-10-12)


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src, box=None, blur=BLUR, half=HALF, smooth=SMOOTH, core_r=CORE_R, speck=SPECK):
    """The plate's ink at UP (work px) in box (plate px; the crop by default), and the plate in grey."""
    x0, y0, x1, y1 = box or (X0, Y0, X1, Y1)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
        w, h = x1 - x0, y1 - y0
        pc(t / "src.png", t / "up.png",
           ("image.crop", {"x": x0, "y": y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        if blur:
            pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": blur * UP}))
        else:
            shutil.copy(t / "up.png", t / "gl.png")
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": core_r * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it, so each line keeps
        # its printed width
        hm = (closed - gl) >= half * (closed - core)
        ink = apply_hysteresis_threshold(np.where(hm, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": smooth * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > speck * UP * UP)[lab]
    return g, gl, ink


def sl(box):
    """A box (plate px) as a slice of the work arrays, clipped to the crop."""
    x0, y0, x1, y1 = box
    c = lambda v, lo, hi: min(max((v - lo) * UP, 0), (hi - lo) * UP)  # noqa: E731
    return np.s_[c(y0, Y0, Y1):c(y1, Y0, Y1), c(x0, X0, X1):c(x1, X0, X1)]


def drop_inside(ink, boxes):
    """ink less the pieces lying wholly inside one of boxes (plate px)."""
    lab, n = ndi.label(ink)
    inside = np.zeros(ink.shape, bool)
    for b in boxes:
        inside[sl(b)] = True
    out = np.bincount(lab[~inside], minlength=n + 1) == 0
    out[0] = False
    return ink & ~out[lab]


def areas(ink, seal=SEAL):
    """The paper the ink closes off, sealed at seal (plate px): watershed labels (0 on ink)."""
    from skimage.segmentation import watershed
    paper = ~ink
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(seal * UP)))
    return watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)


def at(ws, x, y):
    """The area at a point (plate px), the commonest label within 2 plate px if it lands on ink."""
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP]
    v, n = np.unique(win[win > 0], return_counts=True)
    assert len(v), f"no paper near {(x, y)}"
    return v[np.argmax(n)]


def figure(ink, ws):
    """The figures' area: every paper area but the ground (GROUND, and the areas reaching the crop's edge), and the
    ink touching them."""
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    pts = [at(ws, x, y) for x, y in GROUND if X0 <= x < X1 and Y0 <= y < Y1]
    ground = np.isin(ws, np.r_[out[out > 0], pts])
    # paper the seal leaves without a seed is clay, unless it reaches the crop's edge
    lab, _ = ndi.label((ws == 0) & ~ink)
    edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    clay = ((ws > 0) | ((lab > 0) & ~np.isin(lab, edge))) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~ground, ground


def add_tone(svg, steps, box):
    """The wash added to a drawing written by lw.trace_svg (box: the crop box it returned) as paths of class "tone"
    in the line colour, between the body and the lines, one per step [(mask, total opacity)], each drawn over the
    last at the opacity that brings the total to its own (as frogs.py)."""
    x0, y0, x1, y1 = box
    paths, below = [], 0.0
    for mask, total in steps:
        if not mask[y0:y1, x0:x1].any():
            continue
        d, _ = lw.potrace_d(lw.resample_ink(mask[y0:y1, x0:x1], lw.TRACE_H), turdsize=20, alphamax=1.0)
        a = 1 - (1 - total) / (1 - below)
        paths.append(f'<path class="tone" fill="currentColor" fill-opacity="{a:.3f}" stroke="none" d="{d}"/>')
        below = total
    s = svg.read_text().replace('<path class="lines"', "".join(paths) + '<path class="lines"', 1)
    svg.write_text(s)


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    ink = drop_inside(ink, NAMES)
    lab, n = ndi.label(ink)
    top = np.full(n + 1, 10 ** 9)
    np.minimum.at(top, lab.ravel(), np.repeat(np.arange(ink.shape[0]), ink.shape[1]))
    ink &= ~(top > (FRAME_Y - Y0) * UP)[lab]
    beard = np.zeros_like(ink)
    for pts in BEARDS:
        beard |= lw.polygon_mask(ink.shape, (np.array(pts, float) - (X0, Y0)) * UP)
    ink &= ~beard
    ws = areas(ink | beard)
    fig, ground = figure(ink | beard, ws)
    fig |= beard
    # specks on the field
    lab, n = ndi.label(ink)
    size = np.bincount(lab.ravel()) / UP / UP
    near = np.zeros(n + 1, bool)
    near[lab[ndi.distance_transform_edt(~fig) <= NEAR * UP]] = True
    drop = (size < SPECK_MAX) & ~near
    drop[0] = False
    ink &= ~drop[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight=WEIGHT,
        title="Three comic actors: Philotimides, Charis and Xanthias",
        desc="Line drawing after the 1884 plate of the Caputi vase (Heydemann, Hallisches Winckelmannsprogramm 9); "
             "retraced.")
    steps = []
    for level, opacity in BEARD_STEPS:
        m = beard & (gl < level)
        lab, _ = ndi.label(m)
        steps.append((m & (np.bincount(lab.ravel()) >= BEARD_MIN * UP * UP)[lab], opacity))
    add_tone(OUT, steps, info["box"])
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
