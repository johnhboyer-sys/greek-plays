"""Seven Against Thebes: Eriphyle and the chariot of Amphiaraos, from the main picture of an archaic
black-figure hydria in Gerhard, Auserlesene griechische Vasenbilder II (1843), Taf. XCI, "Eriphyle",
as scanned by Heidelberg University Library (Public Domain Mark):
https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_091.jpg/full/full/0/default.jpg
(1963 x 2767; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0218)
The vase, as Gerhard gives it (text pp. 29-30): "archaische Hydria, im römischen Kunsthandel
gezeichnet"; a four-horse chariot driven by two heroes, with a veiled woman walking ahead and looking
back: Eriphyle, and in the chariot her husband Amphiaraos. The picture on the shoulder (fights,
Gerhard: of a meaning he could not fix) is another picture, left out.

Plate -> drawing. Black-figure: the figures are black silhouettes on the orange clay, with incised
lines (the clay showing through the black), dots and added white (a woman's skin, a shield's device).
John chose the silhouette (2026-10-07, over an outline drawing), from a test on Eriphyle's head and the
lead horse's head, and asked for more detail in the eye and the faces.
  - The picture is a band of the vase's body, unrolled: its top edge an arc (TOP_ARC), its sides
    straight (LEFT, RIGHT), and the ground line under it (GROUND, the line's top edge, measured: the
    feet and hooves stand on it; the line is left out).
  - Ground: the orange clay, opened so thin incisions do not join it; its large areas, and the pockets
    of ground the figures close in (POCKETS).
  - The figure's area: all else in the band, with the thin dark lines on the ground (spears, reins, the
    outlines of her feet) by a ridge filter.
  - The black is drawn black. Open in it: the incisions, hatching and dots (light marks, found on the
    plate smoothed along each stroke, so close strokes stay apart; at least LINE_W wide), and the added
    white, with the thin brown lines drawn on it (her brow, eye, mouth, fingers). Where the white meets
    the ground, an outline LINE_W wide just outside it.
  - Dark theme: the figure's area is clay, a RIM wider than the black, so the black reads on the dark
    page; the incisions show clay, as on the vase.
  - Written as an SVG in the house format directly: linework's trace_svg takes off a clay rim no wider
    than a line outside the lines, which here is the rim the dark theme needs.

    python3 docs/redesign/drawings/tools/seven.py gerhard1843bd2_091.jpg [qa.png]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology
from skimage.feature import structure_tensor
from skimage.filters import apply_hysteresis_threshold, sato

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "seven.svg"

X0, Y0, X1, Y1 = 130, 720, 1780, 1840     # crop in plate px (the band, with a margin)
UP = 3                                    # work at 3x the plate's px
TOP_ARC = (913.4, 3642.9, 2914.0)         # centre x, y, radius (plate px): outside it, paper
# the ground line's top edge, measured column by column (every 20 px shown; the columns where a hoof or
# foot stands on it interpolated over), within 0.35 px of the measurements; the cut runs GROUND_CLEAR
# above it, so the line itself stays out (an arc fitted to it lay up to a px off, and a stretch of the
# line between her front foot and the hooves came into the drawing)
GROUND = [(215, 1801.0), (235, 1796.0), (255, 1790.8), (275, 1786.3), (295, 1782.0), (315, 1778.0), (335, 1774.0),
          (355, 1769.6), (375, 1765.7), (395, 1762.4), (415, 1759.4), (435, 1755.8), (455, 1752.5), (475, 1748.2),
          (495, 1745.5), (515, 1743.1), (535, 1740.5), (555, 1737.1), (575, 1734.6), (595, 1732.8), (615, 1730.7),
          (635, 1728.7), (655, 1726.8), (675, 1725.2), (695, 1723.7), (715, 1722.6), (735, 1721.6), (755, 1720.6),
          (775, 1719.4), (795, 1718.6), (815, 1718.4), (835, 1717.8), (855, 1717.3), (875, 1717.2), (895, 1716.6),
          (915, 1716.5), (935, 1716.8), (955, 1717.4), (975, 1718.1), (995, 1718.1), (1015, 1718.6), (1035, 1720.1),
          (1055, 1720.6), (1075, 1721.0), (1095, 1722.6), (1115, 1724.2), (1135, 1725.9), (1155, 1727.3),
          (1175, 1729.0), (1195, 1730.9), (1215, 1732.7), (1235, 1735.5), (1255, 1738.1), (1275, 1740.6),
          (1295, 1742.9), (1315, 1745.8), (1335, 1749.2), (1355, 1752.5), (1375, 1755.4), (1395, 1758.3),
          (1415, 1762.2), (1435, 1766.1), (1455, 1769.7), (1475, 1773.4), (1495, 1777.9), (1515, 1782.0),
          (1535, 1786.0), (1555, 1790.7), (1575, 1795.7), (1595, 1800.5), (1615, 1805.1), (1635, 1810.3),
          (1655, 1815.6), (1675, 1821.8), (1689, 1828.3)]
GROUND_CLEAR = 1.0                        # plate px
LEFT = (0.07554, 75.1)                    # the band's left edge, x = a y + b: left of it, paper
RIGHT = (-0.11154, 1866.0)                # its right edge
AUTO_GROUND = 2000                        # plate px: clay areas this large are ground
# pockets of ground the figures close in, smaller than AUTO_GROUND (a point in each, plate px): between
# the lead horse's raised forelegs and Eriphyle's mantle (two); between the horses' legs (eight, one of
# them at the ground line); under the crest of the nearer warrior's helmet; under the muzzle of the
# horse with the white blaze. Smaller clay areas in the figures are reserved clay: the shield's rim,
# the harness, the hatched manes and tails, the dots.
POCKETS = [(552, 1391), (620, 1341), (1126, 1575), (1239, 1458), (1267, 1549), (1273, 1633), (1019, 1513),
           (1053, 1697), (968, 1562), (1202, 1536), (1444, 893), (1004, 1071)]
# The white is printed out of register: about 8.5 plate px left of the shapes Gerhard's black outlines
# give (measured: the back leg's white 7.5 and 9.5 px left of its two outlines; the face's 9 px left of
# its profile line; the front leg's about 10). So the white is moved back by SHIFT; where it meets the
# black it keeps its printed edge (the black hid the rest of it); white printed beyond an outline, on
# the ground, is ground.
SHIFT = (8.5, 0.0)                        # plate px, x and y
LINE_W = 1.5                              # plate px: the outline and the thinnest mark
RIM = 1.5                                 # plate px: the clay round the black on the dark theme
# a light mark in the black smaller than GRAIN[0] plate px^2 that is nowhere lighter than grey GRAIN[1], and
# stands alone (no other mark within 2 plate px), is a speck of the print's grain (grey, where incisions and
# dots show the clay or white), not a mark
GRAIN = (8, 165)


def channels(src):
    """Lightness and yellowness (Lab), at UP, lightly smoothed; and the lightness less smoothed."""
    im = np.asarray(Image.open(src).convert('RGB').crop((X0, Y0, X1, Y1)))
    lab = cv2.cvtColor(im, cv2.COLOR_RGB2LAB).astype(np.float32)
    up = lambda a: np.asarray(Image.fromarray(a).resize((a.shape[1] * UP, a.shape[0] * UP), Image.BICUBIC),
                              np.float32)
    L, B = up(lab[..., 0]), up(lab[..., 2])
    return ndi.gaussian_filter(L, 0.5 * UP), ndi.gaussian_filter(B, 0.5 * UP), ndi.gaussian_filter(L, 0.3 * UP)


def oriented_smooth(L, sigma_d=1.0, sigma_i=6.0, half=6, sigma_s=3.0):
    """L smoothed along the local stroke direction (across the dominant gradient), not across it: close
    parallel strokes stay apart while each one evens out."""
    Arr, Arc, Acc = structure_tensor(L, sigma=sigma_d, order='rc')
    Arr, Arc, Acc = (ndi.gaussian_filter(a, sigma_i) for a in (Arr, Arc, Acc))
    theta = 0.5 * np.arctan2(2 * Arc, Arr - Acc)
    tr, tc = -np.sin(theta), np.cos(theta)
    yy, xx = np.mgrid[0:L.shape[0], 0:L.shape[1]].astype(np.float32)
    acc, wsum = np.zeros_like(L), 0.0
    for k in range(-half, half + 1):
        w = np.exp(-0.5 * (k / sigma_s) ** 2)
        acc += w * ndi.map_coordinates(L, [yy + k * tr, xx + k * tc], order=1, mode='nearest')
        wsum += w
    return acc / wsum


def thick(m, w):
    """m, every part at least w plate px wide (thin marks widened along their centres)."""
    return m | (ndi.distance_transform_edt(~morphology.skeletonize(m)) <= w * UP / 2)


def write_svg(lines, body, out, title, desc):
    """The house format (as linework.trace_svg writes it): 1000 units tall, the body path under the lines,
    traced at the work px."""
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


def main(src, qa=None):
    L, B, Lf = channels(src)
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx / UP + X0, yy / UP + Y0   # plate px

    # outside the band: above its top arc, left and right of its sides (the frame), and from the ground
    # line down
    gx, gy = np.array(GROUND).T
    below = py > np.interp(px, gx, gy) - GROUND_CLEAR
    side = (px < LEFT[0] * py + LEFT[1]) | (px > RIGHT[0] * py + RIGHT[1])
    side |= np.hypot(px - TOP_ARC[0], py - TOP_ARC[1]) > TOP_ARC[2]
    # and the paper the band's printed edge leaves inside those lines (its edge is ragged by up to 10 px)
    lab, _ = ndi.label((L > 175) & (B < 152) & ~side & ~below)
    edge_ids = np.unique(lab[ndi.binary_dilation(side, iterations=2) & (lab > 0)])
    frame = side | np.isin(lab, edge_ids[edge_ids > 0])
    outside = frame | below

    # the white, moved back into register (SHIFT); the dark lines drawn on it stay in it
    black_core = L < 100
    black_wide = ndi.binary_opening(black_core, structure=morphology.disk(2 * UP))
    printed = ndi.binary_opening((L > 175) & (B < 152) & ~outside, structure=morphology.disk(UP))
    moved = ndi.shift(printed.astype(np.float32), (SHIFT[1] * UP, SHIFT[0] * UP), order=1) > 0.5
    hidden = printed & (ndi.distance_transform_edt(~black_wide) <= (np.hypot(*SHIFT) + 1) * UP)
    white = (moved | hidden) & ~black_core & ~outside
    white = ndi.binary_opening(white, structure=morphology.disk(UP))
    lab, _ = ndi.label(white)
    white &= (np.bincount(lab.ravel()) > 60 * UP * UP)[lab]
    white = ndi.binary_fill_holes(ndi.binary_closing(white, structure=morphology.disk(2 * UP))) & ~black_wide & ~outside
    spill = printed & ~white                  # printed beyond the outlines

    # ground: the clay, and the white printed beyond the outlines, opened so thin incisions do not join
    # it; its large areas and the listed pockets
    # (the spill widened by a px: the soft edge between it and the clay is neither, and that seam cut it off)
    spill = ndi.binary_dilation(spill, iterations=UP)
    clay = ndi.binary_opening((((B > 155) & (L > 120)) | spill) & ~white & ~outside, structure=morphology.disk(2 * UP))
    lab, _ = ndi.label(clay)
    size = np.bincount(lab.ravel())
    size[0] = 0
    is_ground = size > AUTO_GROUND * UP * UP
    for x, y in POCKETS:
        k = lab[round((y - Y0) * UP), round((x - X0) * UP)]
        assert k, f'pocket point {(x, y)} is not on clay'
        is_ground[k] = True
    ground = is_ground[lab]

    # the figure's area: all else in the band, smoothed; and the thin dark lines on the ground
    dark_ridge = apply_hysteresis_threshold(sato(L, sigmas=[1.0, 1.5, 2.0], black_ridges=True), 8, 16) & (L < 190)
    fig = ndi.binary_opening(~ground & ~outside, structure=morphology.disk(UP)) | (dark_ridge & ~ground & ~outside)
    lab, _ = ndi.label(fig)
    fig &= (np.bincount(lab.ravel()) > 60 * UP * UP)[lab]   # specks of the print on the ground go
    fig = (ndi.binary_fill_holes(fig) & ~ground) | white
    white &= fig
    near_white = ndi.binary_dilation(white, iterations=2 * UP)

    # incisions, hatching and dots: light marks in the black, on the plate smoothed along each stroke
    Ls = oriented_smooth(Lf)
    tophat = Ls - ndi.grey_opening(Ls, size=(2 * UP, 2 * UP))
    marks = ((Ls > 160) | ((tophat > 30) & (Ls > 70))) & fig & ~near_white
    lab, n = ndi.label(marks)
    size = np.bincount(lab.ravel(), minlength=n + 1)
    peak = np.zeros(n + 1)
    peak[1:] = ndi.maximum(L, lab, np.arange(1, n + 1))
    grain = (size < GRAIN[0] * UP * UP) & (peak < GRAIN[1])
    # but a mark beside another (the arms of a cross, a broken stroke) is part of it
    near = ndi.grey_dilation(np.where(grain[lab], 0, lab), size=(4 * UP + 1, 4 * UP + 1))
    beside = np.zeros(n + 1, bool)
    beside[np.unique(lab[(lab > 0) & grain[lab] & (near > 0)])] = True
    grain &= ~beside
    marks &= ((size > 2 * UP * UP) & ~grain)[lab]
    marks_w = thick(marks, LINE_W) & fig

    # the lines on the white (brow, eye, mouth, fingers): darker than its own tone
    face_w = thick(((L < 150) | dark_ridge) & white, LINE_W) & white

    # the black: the figure but the white, the marks, and the soft light edge where the white fades into
    # the clay (drawn black, it joined the eye to the profile); the white and that edge outlined where they
    # meet the ground, by a band just outside the figure
    soft = fig & ~white & (L > 150) & (ndi.distance_transform_edt(~white) <= 3 * UP)
    a_black = fig & ~white & ~marks_w & ~soft
    # (under the white feet the outline runs along the ground line, as their soles do on the plate)
    lines = a_black | face_w | (~fig & ~frame & (ndi.distance_transform_edt(~(white | soft)) <= LINE_W * UP))
    body = (ndi.distance_transform_edt(~fig) <= RIM * UP) & ~frame

    info = write_svg(
        lines, body, OUT,
        title='Eriphyle before the chariot of Amphiaraos',
        desc='Line drawing after the 1843 plate of an archaic black-figure hydria (Gerhard, Auserlesene '
             'griechische Vasenbilder II, Taf. XCI, "Eriphyle"); cut out and retraced.')
    print(OUT, info)
    if qa:  # optional: the drawing over its source, and as the dark theme shows it
        lw.qa_overlay(L, OUT, info['box'], Path(qa))
        lw.qa_dark(OUT, info['box'], Path(qa).with_suffix('.dark.png'))


if __name__ == '__main__':
    main(*sys.argv[1:3])
