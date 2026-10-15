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
POCKETS = []
# the worn patch along the floor (polygon, plate px): the light areas inside it, closed off by the plate's long lines,
# with more than STIP_D of their px in small dark marks (each under STIP_DOT plate px^2) are ground
STIPPLE = [(150, 1625), (990, 1528), (1040, 1528), (1495, 1782), (150, 1718)]
STIP_DOT, STIP_D, STIP_LC = 60, 0.04, 30
PAINT_NEAR, PAINT_CORE = 7.6, 60
FACES = []
FACE_LO, FACE_HI, FACE_SPECK = 12, 22, 5.4
FACE_HM, FACE_MIN_R = 0.6, 3.8
DOT_LC, DOT_AREA, DOT_SIDE = 16, (7, 144), 15
LINE_R = 4.75
LINE_LO, LINE_HI = 22, 34
BLUR_S, BLUR_L, BLUR_F = 1.33, 1.52, 0.67  # plate px: Orestes' 0.7, 0.8, 0.35 at this scan's scale
WEIGHT = 0.0011                            # the line weight, of the longer side (F-R: John on Andromache)
MARKS_FILES = []


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
        pc(t / "up.png", t / "fine.png", ("filter.blur.gaussianBlur", {"radius": BLUR_F * UP}),
           ("image.adjustments.threshold", {"level": DARK}))
        g, gl, closed = grey(t / "up.png"), grey(t / "gl.png"), grey(t / "closed.png")
        gs = grey(t / "gs.png")
        gmin = grey(t / "gmin.png")
        dark0 = grey(t / "dark.png") < 128
        fine = grey(t / "fine.png") < 128
    H, W = g.shape
    outside = poly(g.shape, CUTS['left']) | poly(g.shape, CUTS['right']) | poly(g.shape, CUTS['top'])
    lc = closed - gl

    # the worn patch: light areas closed off by the long marks, thick with small ones
    stip = poly(g.shape, STIPPLE)
    marks = (lc > STIP_LC) | dark0
    lab, n = ndi.label(marks)
    size = np.bincount(lab.ravel()) / UP ** 2
    small = (size <= STIP_DOT)[lab] & marks
    long_ = marks & ~small
    lab, n = ndi.label(~long_ & stip)
    dens = ndi.mean(small, lab, range(1, n + 1)) if n else []
    worn = np.r_[False, np.asarray(dens) > STIP_D][lab] & stip
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
    blue = np.zeros_like(fig)
    for mf in MARKS_FILES:
        m = np.asarray(Image.open(mf).convert('RGBA')).astype(int)
        assert m.shape[:2] == fig.shape, (m.shape, fig.shape)
        r, gg, bb, al = (m[..., i] for i in range(4))
        blue |= (al > 40) & (bb > r + 40) & (bb > gg + 20)

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
        for i in big:
            yy, xx = np.nonzero(lab2 == i)
            k = len(yy) // 2
            px, py = xx[k] / UP + X0, yy[k] / UP + Y0
            d.text((xx[k], yy[k]), f'{round(px)},{round(py)}:{round(sz[i])}', fill=(255, 0, 0))
        im.save(qa)
        print('dark areas in the figure over 400 plate px:', len(big))
        return

    lab, n = ndi.label(dark & fig)
    solid = np.r_[False, np.array(ndi.minimum(gs, lab, range(1, n + 1))) < PAINT_CORE] if n else np.zeros(1, bool)
    solid = solid[lab]
    paint = fine & ndi.binary_dilation(solid, iterations=round(PAINT_NEAR * UP)) & fig

    ys, xs = np.nonzero(fig)
    tw = WEIGHT * max(np.ptp(ys), np.ptp(xs))   # the line width, work px
    if test:   # a test box: the weight the whole panel gives
        tw = WEIGHT * (X1_FULL - X0_FULL) * UP
    firm = apply_hysteresis_threshold(lc, LINE_LO, LINE_HI)
    black = firm & fig & ~ndi.binary_dilation(paint, iterations=round(UP))
    lines = centre_lines(black, tw, round(3 * 1.9 * UP), 2 * tw) | paint
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
        lines |= dot[lab] & ~ndi.binary_dilation(lines, iterations=round(UP))
    # the faces: the plate's own dark at its own width
    faces = box_mask(FACES)
    hm = gl < closed - FACE_HM * (closed - gmin)
    face_lines = morphology.remove_small_objects(apply_hysteresis_threshold(lc, FACE_LO, FACE_HI) & hm & fig & faces,
                                                 max_size=round(FACE_SPECK * UP * UP))
    lines = np.where(faces & ~paint, face_lines, lines)
    dt = ndi.distance_transform_edt(~fig)
    edge = ~fig & (dt <= tw) & ~outside
    ink = (lines & fig) | edge
    if blue.any():
        ink |= ndi.distance_transform_edt(~morphology.skeletonize(blue)) <= tw / 2
        ink |= ndi.binary_opening(blue, structure=morphology.disk(max(1, round(tw))))
    lab, _ = ndi.label(ink)
    ink &= (np.bincount(lab.ravel()) > 4 * 1.9 ** 2 * UP * UP)[lab]

    info = lw.trace_svg(
        ink, out, body=fig, open_holes=~fig, weight="drawn",
        title='Orestes kills Aegisthus',
        desc='Line drawing after Karl Reichhold\'s drawing of the Berlin Painter\'s pelike, Vienna, Kunsthistorisches '
             'Museum IV 3725 (Furtwängler and Reichhold, Griechische Vasenmalerei II, Taf. 72); cut out and retraced.')
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
