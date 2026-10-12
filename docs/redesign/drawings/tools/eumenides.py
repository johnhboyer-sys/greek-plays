"""Eumenides: Orestes at Delphi, the whole of fig. 1 of Carl Bötticher's plate, Der Omphalos des Zeus zu Delphi
(Neunzehntes Programm zum Winckelmannsfest der Archäologischen Gesellschaft zu Berlin, Berlin, 1859), as scanned by
Heidelberg University Library (Public Domain Mark 1.0):
https://digi.ub.uni-heidelberg.de/iiif/2/bwpr1859%3A010a.jpg/full/full/0/default.jpg (1775 x 2341). The Munich copy
(MDZ bsb10221820, 2458 x 3192) is larger but softer; Heidelberg's is the sharper (John, 2026-10-12).
Bötticher (p. 15, note 66) copied the drawing from O. Jahn, Vasenbilder (Hamburg, 1839), Taf. I. The vase: the Black
Fury Painter's volute-krater, Naples, Museo Archeologico Nazionale 82270 (H 3249).

Made with PhotoCraft (John, 2026-10-07), as tools/rhesus.py: every image step runs in `photocraft-cli` (0.2.0) but the
levelling, a rotation by ANGLE in scipy (PhotoCraft has no free rotation). numpy only combines the masks PhotoCraft
made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing. A pen contour drawing on paper, no black ground (the vase's ground is black). John chose
(2026-10-12): the whole of fig. 1 (the two outer columns, the rules, the hanging objects, the ground line); the pen
lines traced at the plate's own weight (1.2 scan px); on the dark theme the figures' area filled as clay; the black
areas (the Fury, the hair, the stripes) solid, with a clay rim round them on the dark theme.

    python3 docs/redesign/drawings/tools/eumenides.py boetticher-1859-010a.jpg [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "eumenides.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# the scan leans: the top rule falls 8.5 px over 1470, the ground line 11 over 1200, the column flutes lean with
# them; turned back by their mean about the scan's centre (degrees, counter-clockwise)
ANGLE = 0.43
# crop in levelled scan px: the whole of fig. 1
X0, Y0, X1, Y1 = 236, 178, 1754, 892
UP = 4                                    # work at 4x the scan's px (the faces are 30-40 px tall)
BLUR = 0.4                                # scan px: the Gaussian before the line finder
CLOSE_R = 4                               # scan px: Maximum then Minimum, wider than a line (1-3 px)
LOW, HIGH = 22, 40                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 100                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 3, 0.5                     # a line's core: the darkest px within CORE_R scan px; half maximum
SMOOTH = 0.4                              # scan px: the line mask's Gaussian, cut at half
SPECK = 3                                 # scan px^2: smaller pieces of ink are specks of the print
SEAL = 4                                  # scan px: passages narrower than this do not join ground to figure
WEIGHT = 1.2 / (X1 - X0)                  # the plate's own line, 1.2 scan px (John, 2026-10-12)
RIM = 1.5                                 # scan px: the clay round the solid black on the dark theme
SOLID_OPEN = 2                            # scan px: solid black is the ink an opening this wide leaves
# points on the ground (levelled scan px): the paper areas they fall in are vase ground; every other area the
# lines close is clay
GROUND = []


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def level(src, out):
    """The scan turned by ANGLE about its centre (scipy, bicubic), saved as PNG."""
    a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    r = np.stack([ndi.rotate(a[..., k], -ANGLE, reshape=False, order=3, mode="nearest") for k in range(3)], -1)
    Image.fromarray(np.clip(r, 0, 255).round().astype(np.uint8)).save(out)


def masks(src):
    """The plate's ink at UP (work px), and the plate in grey."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        level(src, t / "src.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "src.png", t / "up.png",
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": BLUR * UP}))
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it
        half = (closed - gl) >= HALF * (closed - core)
        ink = apply_hysteresis_threshold(np.where(half, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": SMOOTH * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    return g, gl, ink


def areas(ink):
    """The paper the ink closes off, sealed at SEAL: watershed labels (0 on ink)."""
    from skimage.segmentation import watershed
    paper = ~ink
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(SEAL * UP)))
    return watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)


def at(ws, x, y):
    """The area at a point (levelled scan px), the commonest label within 2 scan px if it lands on ink."""
    cy, cx = round((y - Y0) * UP), round((x - X0) * UP)
    win = ws[max(cy - 2 * UP, 0):cy + 2 * UP, max(cx - 2 * UP, 0):cx + 2 * UP]
    v, n = np.unique(win[win > 0], return_counts=True)
    assert len(v), f"no paper near {(x, y)}"
    return v[np.argmax(n)]


def figure(ink, ws):
    """The figures' area: every paper area but the ground (GROUND, and the areas reaching the crop's edge), and the
    ink touching it."""
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    ground = np.isin(ws, np.r_[out[out > 0], [at(ws, x, y) for x, y in GROUND]])
    clay = (ws > 0) & ~ground
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~ground, ground


def add_rim(rim, info):
    """The clay rim round the solid black, added to the body path after tracing: trace_svg takes clay off
    where it lies outside a line and no wider than one, which is what this rim is. Traced on the body's grid."""
    x0, y0, x1, y1 = info["box"]
    d, _ = lw.potrace_d(lw.resample_ink(rim[y0:y1, x0:x1], lw.TRACE_H), turdsize=0, alphamax=1.2)
    s = OUT.read_text()
    key = '<path class="body" fill="none" stroke="none" d="'
    assert key in s
    OUT.write_text(s.replace(key, key + d + " ", 1))


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    ws = areas(ink)
    fig, ground = figure(ink, ws)
    solid = ndi.binary_opening(ink, structure=morphology.disk(SOLID_OPEN * UP))
    rim = (ndi.distance_transform_edt(~solid) <= RIM * UP) & ~ink
    body = fig | solid
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), ink=ink, ws=ws.astype(np.int32), fig=fig, body=body)
    info = lw.trace_svg(
        ink, OUT, body=body, open_holes=~body, weight=WEIGHT,
        title="Orestes at Delphi",
        desc="Line drawing after Carl Bötticher's 1859 drawing of an Apulian red-figure volute-krater (Naples): "
             "the Pythia fleeing, the Fury, Apollo, Orestes at the omphalos, Artemis with her hounds; retraced.")
    add_rim(rim, info)
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info["box"], Path(qa))
        lw.qa_dark(OUT, info["box"], Path(qa).with_suffix(".dark.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
