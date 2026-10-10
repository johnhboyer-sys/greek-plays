"""Rhesus (Euripides): two young warriors creep to the right on a night raid, Hoernes's Diomedes and Odysseus.
From M. Hoernes, "Orest in Delphi. Diomedes und Odysseus. Zwei Vasenbilder des k. k. Antiken-Cabinets zu Wien",
Archäologische Zeitung 35 (1877), pp. 17-21, Taf. 5 ("Vasenbild in Wien", Lichtdruck v. A. Frisch, Berlin), as
photographed for the Internet Archive from the Getty Research Institute's copy (archaologischez35deut, leaf 229 of
the original captures, page n228 in the viewer; NOT_IN_COPYRIGHT):
https://archive.org/download/archaologischez35deut/archaologischez35deut_orig_jp2.tar/archaologischez35deut_orig_jp2%2Farchaologischez35deut_orig_0229.jp2
(4368 x 2912, the open book photographed upside down). A second scan of the plate (in.gov.ignca.25813, leaf n325,
5120 x 6400) is blocky with JPEG artefacts at full size; registered to this photo by SIFT it agrees within about 2 px
(median 1.8) under a similarity, so the photo is taken as flat: turned upright, nothing else.
Hoernes (p. 21): the only picture on the front of a red-figure krater of fine style from the Lamberg collection
(Wien V 57, height and diameter 12 3/4 inches), two lightly armed young warriors stepping warily to the right; the
older in front (Odysseus) with the star shield, the spear lowered, a helmet with a spike ending in a star; behind him
on his toes Diomedes, nude but for a belt and two cross-bands set with small plates, a disc where they cross, a
pileus rimmed with plates, one spear in the right hand and two over the left shoulder. Diomedes and Odysseus on their
night raid into the Trojan camp (Iliad 10), which "cannot be strictly proved". Sacken and Kenner, Die Sammlungen des
k. k. Münz- und Antiken-Cabinetes (Vienna, 1866), Kasten V, 2, no. 57: the same krater, the figures "ephebes".
Present location not found. Titled as Hoernes reads it (John, 2026-10-10).

Made with PhotoCraft (John, 2026-10-07), as tools/phoenician_women.py: every image step runs in `photocraft-cli`
(0.2.0). Pillow only converts the JPEG 2000 to PNG, which PhotoCraft cannot read; numpy only combines the masks
PhotoCraft made and measures. The SVG is written by linework.trace_svg.

Plate -> drawing. The plate is a contour drawing in black on cream paper, with no black ground (as Hoernes printed
it; the vase's ground is black). John chose (2026-10-10): the pen lines traced, and on the dark theme the figures'
area filled as clay, as on Andromache.
  - Lines: the plate's dark lines by local contrast (PhotoCraft's Maximum then Minimum, less the plate), with the
    solid black (the shield's star, the crescent) by a plain threshold; the mask smoothed (Gaussian Blur, cut at
    half) so the lines come out even.
  - The figures' area: every paper area the plate's lines close, but for the one round the group and the pockets
    of vase ground the figures close in (POCKETS: between an arm and the body, a spear and a leg).

    python3 docs/redesign/drawings/tools/rhesus.py archaologischez35deut_orig_0229.jp2 [qa.png]
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

OUT = Path(__file__).resolve().parent.parent / "rhesus.svg"
PC = os.environ.get("PHOTOCRAFT", str(Path.home() / ".local/bin/photocraft-cli"))

# crop in upright px: the group, with the spears' tips and the feet
X0, Y0, X1, Y1 = 1000, 400, 4080, 2340
UP = 2                                    # work at 2x the plate's px
CLOSE_R = 5                               # plate px: Maximum then Minimum, wider than a line (2-5 px)
LOW, HIGH = 22, 40                        # local contrast (grey levels): a line starts at HIGH, runs on down to LOW
SOLID = 120                               # solid black: darker than this, lightly blurred
CORE_R, HALF = 3, 0.5                     # a line's core: the darkest px within CORE_R plate px
SMOOTH = 0.6                              # plate px: the line mask's Gaussian, cut at half
SPECK = 6                                 # plate px^2: smaller pieces of ink are specks of the print
# The pen outline is broken in many places (at the joints, where a line stops short of the next), so the
# ground reaches the figures only through passages wider than SEAL plate px: the paper is opened by a disk
# that wide, each piece left is an area, and the watershed of the paper's distance to the ink gives every
# paper px to the nearest area (slivers of ground beside a figure go with the ground round it)
SEAL = 6
# pockets of vase ground the figures close in (a point in each, upright px): between the left youth's
# raised arm and the spears on his shoulder; between the two youths, down to where their feet meet; and
# between the left youth's lowered arm, his back, the lowered spear and his calf
POCKETS = [(2060, 915), (2320, 1510), (1630, 1530)]
# Shafts too narrow for the seal (12-22 plate px between their edge lines): each given by rough ends of its
# centre line (upright px); the centre and width are fitted to its two edge lines (`shaft`). The two spears
# over the left youth's shoulder, behind his neck, before and past his fist and in front of his face; the
# right youth's spear; his helmet's spike
SHAFTS = [((1880, 815), (2215, 849)), ((1880, 830), (2215, 862)),
          ((2320, 865), (2440, 876)), ((2340, 881), (2450, 887)),
          ((1440, 789), (1660, 798)), ((1440, 802), (1660, 807)),
          ((2470, 1102), (3950, 1372)), ((3203, 578), (3226, 492))]
# small closed parts (boxes, upright px): there the paper the ink closes after a closing by CLOSE plate px is
# clay (the spike's star, the right spear's head, the blade under the spearheads behind the left youth)
CLOSED = [(3200, 440, 3260, 500), (3930, 1330, 4040, 1400), (1240, 800, 1440, 835)]
CLOSE = 2
# breaks in the outline wider than the seal, walled for the figures' area only (not drawn): each found by the
# path the ground takes into a figure, cut where it crosses the plate's lines (upright px): behind the right
# youth's rear knee
WALLS = [[(2696, 1818), (2705, 1811)]]
WALL_W = 2.0


def pc(src, out, *steps):
    """Run PhotoCraft on src: steps are (command, params) pairs; the result saved to out."""
    args = [PC, "run", str(src)]
    for cmd, params in steps:
        args += ["--cmd", cmd] + (["--params", json.dumps(params)] if params is not None else [])
    args += ["--out", str(out)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def grey(p):
    return np.asarray(Image.open(p).convert("L")).astype(np.float32)


def masks(src):
    """The plate's ink and the figures' area at UP (work px), and the plate in grey."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        Image.open(src).convert("RGB").save(t / "src.png")
        w, h = X1 - X0, Y1 - Y0
        pc(t / "src.png", t / "up.png",
           ("image.imageRotation.180", None),
           ("image.crop", {"x": X0, "y": Y0, "width": w, "height": h}),
           ("image.imageSize", {"width": w * UP, "height": h * UP, "resample": "bicubic"}),
           ("image.mode.grayscale", None))
        pc(t / "up.png", t / "gl.png", ("filter.blur.gaussianBlur", {"radius": 0.5 * UP}))
        r = CLOSE_R * UP
        pc(t / "gl.png", t / "closed.png", ("filter.other.maximum", {"radius": r, "preserve": "squareness"}),
           ("filter.other.minimum", {"radius": r, "preserve": "squareness"}))
        pc(t / "gl.png", t / "solid.png", ("image.adjustments.threshold", {"level": SOLID}))
        pc(t / "gl.png", t / "core.png", ("filter.other.minimum", {"radius": CORE_R * UP, "preserve": "roundness"}))
        g, gl, closed, core = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png"), grey(t / "core.png")
        # half maximum: darker than halfway between the paper and the line's darkest px near it, so each
        # line keeps its printed width (local contrast alone took in its soft edge, and the hair's strokes
        # ran together)
        half = (closed - gl) >= HALF * (closed - core)
        ink = apply_hysteresis_threshold(np.where(half, closed - gl, 0), LOW, HIGH) | (grey(t / "solid.png") < 128)
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).save(t / "ink.png")
        pc(t / "ink.png", t / "smooth.png", ("filter.blur.gaussianBlur", {"radius": SMOOTH * UP}),
           ("image.adjustments.threshold", {"level": 128}))
        ink = grey(t / "smooth.png") < 128
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > SPECK * UP * UP)[lab]
    return g, gl, ink


def shaft(gl, a, b):
    """A shaft's band (bool, work px): the paper between its two edge lines, along the centre line fitted
    to the midpoints between them (read across the shaft every 4 plate px, the darkest px on each side of
    the rough centre within 14 plate px), out to the edge lines' centres. Returns the band, its half-width
    and the fit's rms (plate px)."""
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a))
    n = np.array([-u[1], u[0]])
    mids, gaps = [], []
    for s in np.arange(0, np.hypot(*(b - a)), 4):
        p = a + s * u
        o = np.arange(-14, 14.01, 0.5)
        q = (p[None] + o[:, None] * n[None] - (X0, Y0)) * UP
        v = ndi.map_coordinates(gl, [q[:, 1], q[:, 0]], order=1)
        lo, hi = o < 0, o > 0
        i, j = np.argmin(np.where(lo, v, 1e9)), np.argmin(np.where(hi, v, 1e9))
        if v[i] < 150 and v[j] < 150 and 4 < o[j] - o[i] < 26:
            mids.append(p + (o[i] + o[j]) / 2 * n)
            gaps.append(o[j] - o[i])
    mids = np.array(mids)
    t = (mids - a) @ u
    f = np.polyfit(t, (mids - a) @ n, 1)
    res = (mids - a) @ n - np.polyval(f, t)
    hw = np.median(gaps) / 2
    band = np.zeros(gl.shape, bool)
    (cx0, cy0), (cx1, cy1) = [(np.floor((np.minimum(a, b) - 20 - (X0, Y0)) * UP)).astype(int).clip(0),
                              (np.ceil((np.maximum(a, b) + 20 - (X0, Y0)) * UP)).astype(int)]
    yy, xx = np.mgrid[cy0:cy1, cx0:cx1]
    px, py = (xx + 0.5) / UP + X0 - a[0], (yy + 0.5) / UP + Y0 - a[1]
    along_, across = px * u[0] + py * u[1], px * n[0] + py * n[1]
    band[cy0:cy1, cx0:cx1] = ((along_ >= 0) & (along_ <= np.hypot(*(b - a))) &
                              (np.abs(across - np.polyval(f, along_)) <= hw))
    return band, hw, float(np.sqrt(np.mean(res ** 2)))


def walls(shape):
    """WALLS as a mask (work px), WALL_W plate px wide."""
    m = np.zeros(shape, bool)
    for pts in WALLS:
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            k = int(np.hypot(xb - xa, yb - ya) * UP * 2) + 2
            xs, ys = np.linspace(xa, xb, k), np.linspace(ya, yb, k)
            m[np.round((ys - Y0) * UP).astype(int), np.round((xs - X0) * UP).astype(int)] = True
    return ndi.distance_transform_edt(~m) <= WALL_W * UP / 2 if m.any() else m


def figure(ink, gl):
    """The figures' area: the paper the ink closes off from the ground round the group by passages narrower
    than SEAL (the watershed areas but for those reaching the crop's edge and the POCKETS), the shafts, the
    small closed parts, and the ink touching them."""
    from skimage.segmentation import watershed
    paper = ~(ink | walls(ink.shape))
    mk, _ = ndi.label(ndi.binary_opening(paper, structure=morphology.disk(SEAL * UP)))
    ws = watershed(-ndi.distance_transform_edt(paper), mk, mask=paper)
    out = np.unique(np.r_[ws[0], ws[-1], ws[:, 0], ws[:, -1]])
    out = out[out > 0]
    ground = np.isin(ws, out)
    for x, y in POCKETS:
        k = ws[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k and k not in out, f'pocket point {(x, y)} is not on paper the group closes'
        ground |= ws == k
    clay = paper & ~ground
    for a, b in SHAFTS:
        band, hw, rms = shaft(gl, a, b)
        print('shaft', a, b, 'half-width', round(hw, 2), 'rms', round(rms, 2))
        clay |= band & paper
    for bx0, by0, bx1, by1 in CLOSED:
        sl = np.s_[(by0 - Y0) * UP:(by1 - Y0) * UP, (bx0 - X0) * UP:(bx1 - X0) * UP]
        c = ndi.binary_closing(ink[sl], structure=morphology.disk(CLOSE * UP))
        clay[sl] |= ndi.binary_fill_holes(c) & ~c & paper[sl]
    # (the ink they close in too: the shield's star, wider than the reach)
    fig = ndi.binary_fill_holes(clay | (ink & ndi.binary_dilation(clay, iterations=2 * UP)))
    return fig & ~(ground & paper)


def main(src, qa=None, dump=None):
    g, gl, ink = masks(src)
    fig = figure(ink, gl)
    lab, n = ndi.label(ink)   # specks on the paper round the group: ink that touches no figure
    on = np.zeros(n + 1, bool)
    on[lab[fig]] = True
    on[0] = False
    ink &= on[lab]
    if dump:
        np.savez_compressed(dump, g=g.astype(np.uint8), gl=gl.astype(np.uint8), ink=ink, fig=fig)
    info = lw.trace_svg(
        ink, OUT, body=fig, open_holes=~fig, weight="drawn",
        title='Diomedes and Odysseus on the night raid',
        desc='Line drawing after the 1877 plate of a red-figure krater in Vienna (Hoernes, Archäologische '
             'Zeitung 35, Taf. 5); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(g, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
