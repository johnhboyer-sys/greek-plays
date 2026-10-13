"""Birds: a piper and two dancers dressed as birds, from C. Smith, "Actors with Bird-Masks on Vases", Journal of
Hellenic Studies 2 (1881), 309-314, pl. XIV, fig. B.1 (published 1881, public domain), the copy in JSTOR's Early
Journal Content on Zenodo (record 1960286, CC0): article.pdf, page 2, its one image (3222 x 4394, 300 ppi; taken
out with `pdfimages -j`).
Smith's text: an oinochoe with black figures on a red panel, British Museum, once in the Burgon collection, found in
Italy in 1835, c. 500-450 BC. The piper plays the double pipes; two bearded dancers move to the right with purple
crests, their bodies stippled (left) or set with incised circles (right), feather bunches at the knees, wings
strapped to their arms; ivy or vine branches strewn in the field.
John's pick (Plate Picks 34-Q2a, 2026-10-12: "get full plate though"); the drawing: fig. B.1 whole, the piper, both
dancers and the branches (John, 2026-10-12).

Made with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (0.2.0): the crop, the
enlargement, the grey, the channel mixes, the blurs, Minimum and Maximum. numpy only combines the masks PhotoCraft
made (labels, unions, distances, fills) and measures. The SVG is written in the house format directly, as
cyclops.py.

Plate -> drawing, black-figure, drawn as a silhouette (John, 2026-10-12: "as Cyclops"):
  - Ground: the tan clay (red less 0.18 green over WARM_T, not red), its large areas.
  - Red: the added red (red less 1.6 green over RED_T): a path of class `red` in the plate's own red (John,
    2026-10-12: "match the bright red with red"), with no outline, cut out of the black.
  - The figures: all else that is not ground (the black prints olive on this plate).
  - The black is drawn black. Open in it: the incisions (light marks, at least LINE_W wide).
  - Dark theme: the figures' area is clay, a RIM wider than the black, so the black reads on the dark page.

    python3 docs/redesign/drawings/tools/birds.py p2-000.png [qa.png]
"""
import json
import os
import re
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

OUT = Path(__file__).resolve().parent.parent / "birds.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# plate px: the page image as it comes out of the PDF; the crop: fig. B.1 with its frame (John, 2026-10-12: "as
# painted"), the bands above and below it whole, on the white page
X0, Y0, X1, Y1 = 180, 2300, 3060, 3820
if os.environ.get("BIRDS_BOX"):            # (a sub-crop, for working on one part: the same steps on a box)
    X0, Y0, X1, Y1 = (int(v) for v in os.environ["BIRDS_BOX"].split(","))
UP = 3                                     # work at 3x the plate's px (the incisions print 1-2 px wide; 4x
                                           # gave the same lines on the test and does not fit in memory whole)
# colours, as the plate prints them (medians): clay 193,151,107; the black 160,141,101; red 171,88,84; incisions
# 219,197,158 at their lightest. The clay against the black: red less 0.18 green (the two parted best by a linear
# discriminant over k-means classes of the panel, smoothed 1 plate px: clay 160-166, the black 133, each +-5).
# Red less 1.6 green: red 30, clay -49, the black -66.
WARM_T = 146                               # clay: red less 0.18 green over this,
CLAY_L = 172                               # the clay's grey is under this (155-160; the incisions, 190-200, pass WARM_T)
RED_T = 0                                  # red: red less 1.6 green over this (PhotoCraft's constant 50 adds 127.5)
PAPER_B = 200                              # the white page: blue over this (the page 245; incisions 158, clay 105)
RED_FILL = "#ab5854"                       # the plate's red (median of the crests and beards)
BLACK_T = 158                              # light marks in the black: lighter than this (grey; the black 141 +-5)
MARK_T = 10                                # or by the white top-hat over this
ORIENT_D, ORIENT_STEP = 4, 15              # plate px, degrees: the plate smoothed along its own strokes (hecuba.py)
JOIN_MAX, JOIN_RUN, JOIN_ANGLE = 7, 4, 30   # plate px, plate px, degrees: see join_marks (cyclops.py)
AUTO_GROUND = 60                           # plate px^2: clay areas this large are ground,
GROUND_W = 3.0                             # plate px: if some px of them under CLAY_L lies this deep in them (the broad
                                           # incisions, 3-4 px wide and light, pass the opening)
INCISED_L = 182                            # grey: lighter than this is an incision, never ground (where an incision runs
                                           # out to the figure's edge, the beard's hatching)
DOT_MIN = 30                               # plate px^2: dark marks on the ground smaller than this are grain (the branches dots 60-100)
RED_MIN = 20                               # plate px^2: red areas smaller than this are grain
LINE_W = 2.0                               # plate px: the outline and the thinnest mark
RIM = 2.0                                  # plate px: the clay round the black on the dark theme
GRAIN = 3                                  # plate px^2: light specks in the black smaller than this are grain
EDGE_CLEAR = 1.0                           # plate px: no light marks this near the figures' edge
# the right dancer's lines in black pigment (Smith: his arms' outline "faintly indicated with a black pigment",
# through the wings): darker than the black (grey under DARK_T; the black 141 +-5), not near the red (whose blurred edge
# is as dark), inside DANCER2; drawn as thin clay lines (John, 2026-10-12), their centre lines LINE_W wide
DARK_T = 112
DARK_MIN = 8                               # plate px^2: smaller dark specks are the print's
RED_CLEAR = 3                              # plate px
DANCER2 = (1780, 2480, 2800, 3700)         # plate px: the right dancer
SMOOTH = 0.4                               # plate px: every edge smoothed (Gaussian Blur, Threshold at half)


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


def join_marks(marks):
    """Breaks in the incisions joined (the print's dark specks cut the thinnest into dashes): skeleton ends facing
    each other (each end's last JOIN_RUN plate px of centre line points within JOIN_ANGLE degrees of the other end)
    across at most JOIN_MAX plate px, joined by a stroke LINE_W wide that crosses no other mark."""
    from scipy.spatial import cKDTree
    sk = morphology.skeletonize(marks)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    ends = np.argwhere(sk & (nb == 1))
    out = np.zeros_like(marks)
    if len(ends) < 2:
        return out
    H, W = sk.shape

    def run_back(p):
        path, seen = [tuple(p)], {tuple(p)}
        for _ in range(JOIN_RUN * UP):
            y, x = path[-1]
            nxt = [(y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                   if (dy or dx) and 0 <= y + dy < H and 0 <= x + dx < W and sk[y + dy, x + dx]
                   and (y + dy, x + dx) not in seen]
            if not nxt:
                break
            path.append(nxt[0])
            seen.add(nxt[0])
        return np.array(path, float)

    lab = ndi.label(marks, structure=np.ones((3, 3)))[0]
    cos = np.cos(np.radians(JOIN_ANGLE))
    used = set()
    pairs = sorted(cKDTree(ends).query_pairs(JOIN_MAX * UP), key=lambda ij: np.hypot(*(ends[ij[0]] - ends[ij[1]])))
    for i, j in pairs:
        if i in used or j in used:
            continue
        ri, rj = run_back(ends[i]), run_back(ends[j])
        if len(ri) < JOIN_RUN * UP / 2 or len(rj) < JOIN_RUN * UP / 2:
            continue
        a, b = ends[i].astype(float), ends[j].astype(float)
        u = (b - a) / np.hypot(*(b - a))
        da, db = ri[0] - ri[-1], rj[0] - rj[-1]
        if da @ u < cos * np.hypot(*da) or db @ -u < cos * np.hypot(*db):
            continue
        q = np.linspace(a, b, int(np.hypot(*(b - a))) + 2)
        hit = set(lab[tuple(q.round().astype(int).T)]) - {0, lab[tuple(ends[i])], lab[tuple(ends[j])]}
        if hit:
            continue
        m = np.zeros_like(marks)
        m[tuple(q.round().astype(int).T)] = True
        out |= ndi.distance_transform_edt(~m) <= LINE_W * UP / 2
        used |= {i, j}
    return out


def oriented(t, src_png, name):
    """src_png smoothed along its own strokes (ORIENT_*): PhotoCraft's Motion Blur at each angle; numpy picks,
    per pixel, the blur at the strokes' direction (as hecuba.py)."""
    g = grey(src_png)
    angs = list(range(0, 180, ORIENT_STEP))
    for a in angs:
        pc(src_png, t / f"{name}{a}.png", ("filter.blur.motionBlur", {"angle": a, "distance": ORIENT_D * UP}))
    gy, gx = np.gradient(g)
    jxx, jyy, jxy = (ndi.gaussian_filter(v, 1.5 * UP) for v in (gx * gx, gy * gy, gx * gy))
    del gx, gy
    line = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90       # the strokes' direction, y down
    del jxx, jyy, jxy
    i = np.round(((-line) % 180) / ORIENT_STEP).astype(int) % len(angs)   # PhotoCraft's angle is y up
    out = g.copy()
    for k, a in enumerate(angs):        # (one blur at a time: the whole plate at UP is large)
        out[i == k] = grey(t / f"{name}{a}.png")[i == k]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(t / f"{name}.png")
    return t / f"{name}.png"


def write_svg(lines, body, red, out, title, desc):
    """The house format (as cyclops.py): 1000 units tall, the body path under the red under the lines."""
    ys, xs = np.nonzero(lines | body)
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lines.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lines.shape[1])
    d, tr = lw.potrace_d(lines[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    bd, _ = lw.potrace_d(body[y0:y1, x0:x1], turdsize=2, alphamax=1.2)
    rd, _ = lw.potrace_d(red[y0:y1, x0:x1], turdsize=2, alphamax=1.0)
    h, w = y1 - y0, x1 - x0
    k = 1000.0 / h
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {round(w * k, 1):g} 1000" role="img">\n'
                   f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
                   f'<g transform="scale({k:.6f})"><g transform="{tr}">'
                   f'<path class="body" fill="none" stroke="none" d="{bd}"/>'
                   f'<path class="red" fill="{RED_FILL}" stroke="none" d="{rd}"/>'
                   f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/>'
                   f'</g></g>\n</svg>\n')
    return {"bytes": out.stat().st_size, "box": (int(x0), int(y0), int(x1), int(y1))}


def qa(L, out, box, qa_png):
    """The lines in red over the plate in grey (lw.qa_overlay, the red path left out), and the dark theme."""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "l.svg"
        f.write_text(re.sub(r'<path class="red"[^>]*/>', "", out.read_text()))
        lw.qa_overlay(L, f, box, Path(qa_png))
    lw.qa_dark(out, box, Path(qa_png).with_suffix(".dark.png"))


def main(src, qa_png=None, dump=None):
    out = Path(os.environ.get("BIRDS_OUT", OUT))
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        w, h = X1 - X0, Y1 - Y0
        pc(src, t / "up.png", ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}))
        pc(t / "up.png", t / "L.png", ("image.mode.grayscale", None), ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        pc(t / "up.png", t / "blue.png", ("image.adjustments.channelMixer", {"gray": [0, 0, 100, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
        pc(t / "up.png", t / "warm.png", ("image.adjustments.channelMixer", {"gray": [100, -18, 0, 0], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 1.0 * UP}))
        pc(t / "up.png", t / "red.png", ("image.adjustments.channelMixer", {"gray": [100, -160, 0, 50], "monochrome": True}),
           ("filter.blur.gaussianBlur", {"radius": 0.8 * UP}))
        Lo = oriented(t, t / "L.png", "Lo")
        pc(Lo, t / "L_open.png", ("filter.other.minimum", {"radius": UP, "preserve": "roundness"}),
           ("filter.other.maximum", {"radius": UP, "preserve": "roundness"}))
        L, W, R = grey(t / "L.png"), grey(t / "warm.png"), grey(t / "red.png") - 127.5
        paper = grey(t / "blue.png") > PAPER_B
        light_hat = grey(Lo) - grey(t / "L_open.png")

    # the red
    red = ndi.binary_opening(R > RED_T, structure=morphology.disk(UP))
    lab, _ = ndi.label(red)
    red &= (np.bincount(lab.ravel()) >= RED_MIN * UP * UP)[lab]
    red = morphology.remove_small_holes(red, max_size=GRAIN * UP * UP) & ~paper

    # ground: the clay, opened so thin marks do not join it; its large areas
    clay = (W > WARM_T) & ~red & ~paper
    ground0 = ndi.binary_opening(clay, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(ground0)
    size = np.bincount(lab.ravel())
    size[0] = 0
    deep = ndi.maximum(ndi.distance_transform_edt(ground0) * (L < CLAY_L), lab, index=np.arange(len(size)))
    ground = ((size > AUTO_GROUND * UP * UP) & (deep >= GROUND_W * UP))[lab] & (L < INCISED_L)
    ground |= paper

    # the figures: all else, but specks of the print on the ground
    fig = ~ground & ~red
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) >= DOT_MIN * UP * UP)[lab]
    fig = ndi.binary_fill_holes(fig | red) & ~ground & ~red

    # the light marks in the black (incisions), at least LINE_W wide; not along the figures' edge
    clear = ndi.distance_transform_edt(fig) > EDGE_CLEAR * UP
    marks = fig & clear & ((L > BLACK_T) | (light_hat > MARK_T))
    lab, _ = ndi.label(marks)
    marks &= (np.bincount(lab.ravel()) >= GRAIN * UP * UP)[lab]
    marks = (marks | (ndi.distance_transform_edt(~morphology.skeletonize(marks)) <= LINE_W * UP / 2)) & fig & clear
    marks |= join_marks(marks) & fig
    H, Wd = L.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    px, py = (xx + 0.5) / UP - 0.5 + X0, (yy + 0.5) / UP - 0.5 + Y0
    box2 = (px >= DANCER2[0]) & (px < DANCER2[2]) & (py >= DANCER2[1]) & (py < DANCER2[3])
    del yy, xx, px, py
    dark = (L < DARK_T) & fig & box2 & (ndi.distance_transform_edt(~red) > RED_CLEAR * UP)
    lab, _ = ndi.label(dark)
    dark &= (np.bincount(lab.ravel()) >= DARK_MIN * UP * UP)[lab]
    dark = (ndi.distance_transform_edt(~morphology.skeletonize(dark)) <= LINE_W * UP / 2) & fig
    marks |= dark

    lines = smooth(fig & ~marks, SMOOTH)
    red = smooth(red, SMOOTH) & ~lines
    body = ndi.distance_transform_edt(~(fig | red)) <= RIM * UP
    if dump:
        np.savez_compressed(dump, L=L.astype(np.uint8), fig=fig, lines=lines, ground=ground, marks=marks, red=red,
                            dark=dark)
    info = write_svg(
        lines, body, red, out,
        title='A piper and two dancers dressed as birds',
        desc='Line drawing after the 1881 plate of a black-figure oinochoe in the British Museum (Journal of '
             'Hellenic Studies 2, pl. XIV, fig. B.1): a piper playing the double pipes for two dancers in bird '
             'masks with crests and strapped-on wings, branches of ivy in the field; cut out and retraced.')
    print(out, info)
    if qa_png:
        qa(L, out, info['box'], qa_png)


if __name__ == '__main__':
    main(*sys.argv[1:4])
