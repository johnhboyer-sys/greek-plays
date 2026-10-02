"""Shared steps for the redesign drawings: ink from a scan, a guided cut
along a figure's own lines, one house line weight, and potrace to an SVG
whose fill is currentColor.

Dev-only tool for docs/redesign/drawings; needs numpy, scipy, scikit-image,
pillow and the potrace CLI (brew install potrace). See ../README.md.
"""
from __future__ import annotations

import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology

# House line weight: median line width as a fraction of the drawing's longer
# side, so drawings fitted into the same box show the same line. 0.0022 gives
# about 1px lines in a 450px box.
HOUSE_WEIGHT = 0.0022

# ---------------------------------------------------------------- guided tracing

STRAIGHT = "-"  # put between two points in an outline: join them with a straight line


def livewire(cost: np.ndarray, points: list, closed: bool = False, flags: bool = False):
    """Least-cost path through hand-placed (x, y) points, as in a magnetic lasso:
    between each pair of points the path follows low `cost` (e.g. ink or a
    shading edge). Where the outline must cross blank paper (a gap between a
    hand and a head), the path would rather detour along any nearby line, so
    STRAIGHT between two points joins them directly instead. Returns an
    (x, y) polyline in pixel centres; with flags=True, also a bool per point,
    True where the point lies on a STRAIGHT crossing."""
    from skimage.draw import line
    from skimage.graph import route_through_array
    pts, straight = [], set()
    for p in points:
        if p == STRAIGHT:
            straight.add(len(pts) - 1)
        else:
            pts.append((int(round(p[1])), int(round(p[0]))))
    if closed:
        pts.append(pts[0])
    out, on_straight = [], []
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        if i in straight:
            rr, cc = line(a[0], a[1], b[0], b[1])
            path = list(zip(rr.tolist(), cc.tolist()))
        else:
            path, _ = route_through_array(cost, a, b, fully_connected=True, geometric=True)
        seg = path if not out else path[1:]
        out.extend(seg)
        on_straight.extend([i in straight] * len(seg))
    xy = np.array([(x + 0.5, y + 0.5) for y, x in out], dtype=float)
    return (xy, np.array(on_straight)) if flags else xy


def cut_masks(shape, path: np.ndarray, on_straight: np.ndarray, rim: int = 2):
    """From a closed cut path: `keep`, the area inside it plus a rim `rim` px
    wide (the lines the path runs on); `inner`, the area inside it alone; and
    `wall`, the path itself except its STRAIGHT crossings (for body_from_cut)."""
    yx = (path[:, ::-1] - 0.5).astype(int)
    ring = np.zeros(shape, bool)
    ring[yx[:, 0], yx[:, 1]] = True
    wall = np.zeros(shape, bool)
    wall[yx[~on_straight, 0], yx[~on_straight, 1]] = True
    inner = polygon_mask(shape, path)
    keep = inner | ndi.binary_dilation(ring, iterations=rim)
    return keep, inner, wall


def body_from_cut(ink: np.ndarray, inner: np.ndarray, wall: np.ndarray, close: int = 3,
                  inset: int = 4) -> np.ndarray:
    """The figure's area, for the body layer of a figure cut out with livewire:
    every region its lines and the cut path wall in, kept `inset` px inside the
    path so no sliver shows outside the outline (trace_svg adds the lines
    back under the body). Paper inside the cut that opens onto a STRAIGHT
    crossing (the gap between a hand and a head) is background and stays empty."""
    walled = ndi.binary_closing(ink, structure=morphology.disk(close)) | wall
    return ndi.binary_fill_holes(walled) & ndi.binary_erosion(inner, iterations=inset)


def polygon_mask(shape, xy: np.ndarray) -> np.ndarray:
    from skimage.draw import polygon
    m = np.zeros(shape, bool)
    rr, cc = polygon(xy[:, 1], xy[:, 0], shape)
    m[rr, cc] = True
    return m


# ---------------------------------------------------------------- engraved plates

def ink_lines(gray: np.ndarray, size: int = 9, low: float = 16.0, high: float = 16.0,
              sigma: float = 0.7) -> np.ndarray:
    """Dark lines on a lighter ground -> bool mask, by local contrast: a line
    pixel is darker than its surroundings (black top-hat over a size x size
    window). Pixels `high` grey levels darker start a line; connected pixels
    down to `low` continue it, so faint stretches of a line survive and
    isolated specks of grain do not. Catches the fine grey lines that one
    global threshold breaks up; wide solid areas need ink_from_scan too."""
    from skimage.filters import apply_hysteresis_threshold
    g = ndi.gaussian_filter(gray.astype(np.float32), sigma)
    tophat = ndi.grey_closing(g, size=(size, size)) - g
    return apply_hysteresis_threshold(tophat, low, high)


def ink_from_scan(gray: np.ndarray, bg_sigma: float = 25.0, k: float = 0.80) -> np.ndarray:
    """Black ink on paper -> bool ink mask. The paper tone (foxing, uneven
    light) is divided out first, so one threshold works across the plate."""
    g = gray.astype(np.float32)
    bg = ndi.grey_closing(g, size=(15, 15))
    bg = ndi.gaussian_filter(bg, bg_sigma)
    norm = np.clip(g / np.maximum(bg, 1.0), 0, 1)
    return norm < k


# ---------------------------------------------------------------- line weight

def line_width(ink: np.ndarray) -> float:
    """Median line width in px: twice the distance to paper, read on the
    skeleton. Solid masses barely move the median."""
    sk = morphology.skeletonize(ink)
    dt = ndi.distance_transform_edt(ink)
    w = 2 * dt[sk] - 1
    return float(np.median(w)) if w.size else 0.0


def _shift_edges(ink: np.ndarray, r: float, s: float) -> np.ndarray:
    """Move every edge outward by r px (inward if r < 0), sub-pixel, by
    blurring with sigma s and thresholding at Phi(-r/s). Also rounds off
    pixel steps, so potrace draws curves rather than staircases."""
    t = 0.5 * (1 + math.erf(-r / s / math.sqrt(2)))
    return ndi.gaussian_filter(ink.astype(np.float32), s) > t


def set_line_width(ink: np.ndarray, target: float) -> np.ndarray:
    """Thicken or thin every line by the same amount so the median width is
    `target` px. Thin lines are never erased: thinning keeps a band of
    0.6 x target along each line's centre."""
    out = ink
    band = ndi.distance_transform_edt(~morphology.skeletonize(ink)) <= 0.3 * target
    for _ in range(3):  # the blur model is approximate on thin lines: correct twice
        r = (target - line_width(out)) / 2
        if abs(r) < 0.2:
            break
        s = max(1.5, target / 5, abs(r))
        out = _shift_edges(out, r, s)
        if r < 0:
            out |= band & ink
    return _shift_edges(out, 0.0, max(1.0, target / 6))


def resample_ink(ink: np.ndarray, height: int) -> np.ndarray:
    """Rescale a bool ink map so its height is `height` px, with smooth edges."""
    k = height / ink.shape[0]
    f = ndi.zoom(ink.astype(np.float32), k, order=1)
    if k > 1:
        f = ndi.gaussian_filter(f, k / 3)
    return f > 0.5


WORK_H = 4000   # every drawing is weighted at this height (fine steps)...
TRACE_H = 2000  # ...and traced at this one (smaller files)


def trace_svg(ink: np.ndarray, out: Path, *, title: str, desc: str, body: np.ndarray | None = None,
              pad: int = 4, turdsize: int = 10, alphamax: float = 1.0) -> dict:
    """Crop a figure's ink, rescale it to WORK_H px tall, set the house line
    weight, and potrace it into a theme-following SVG 1000 units tall: the
    lines are filled with currentColor. `body`, a mask of the figure's area
    (same shape as ink), becomes a second path under the lines, filled with
    var(--drawing-body, none): transparent unless a page colours it, as the
    dark theme does. The body has no holes, and lines too thin to hold clay
    get a narrow clay rim. Returns the crop box in ink's pixels, for
    qa_overlay."""
    ys, xs = np.nonzero(ink)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, ink.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, ink.shape[1])
    ink = ink[y0:y1, x0:x1]
    before = line_width(ink) / max(ink.shape)
    crop = resample_ink(ink, WORK_H)
    crop = set_line_width(crop, HOUSE_WEIGHT * max(crop.shape))
    weighted = crop
    crop = resample_ink(crop, TRACE_H)  # trace smaller: fewer, smoother curves
    h, w = crop.shape
    d, tr = potrace_d(crop, turdsize=turdsize, alphamax=alphamax)
    body_path = ""
    if body is not None:
        b = resample_ink(body[y0:y1, x0:x1] | ink, TRACE_H)
        hh, ww = min(b.shape[0], h), min(b.shape[1], w)
        b, lines = b[:hh, :ww], crop[:hh, :ww]
        # no holes inside the figure: the dark theme then shows the same drawing
        # as the light one, on clay instead of paper (gaps open to the outside,
        # like those between fingers, stay open)
        b = ndi.binary_fill_holes(b)
        b = ndi.binary_opening(b, structure=morphology.disk(2))
        # a line with no clay on either side of it (a goad, a chain link) would
        # vanish on a dark page: give it a narrow clay rim
        lw_px = HOUSE_WEIGHT * max(lines.shape)
        clay = b & ~lines
        orphan = lines & ~(ndi.distance_transform_edt(~clay) <= 1.5 * lw_px)
        if orphan.any():
            b |= ndi.distance_transform_edt(~orphan) <= 0.8 * lw_px
        bd, _ = potrace_d(b, turdsize=200, alphamax=1.2)
        body_path = f'<path class="body" stroke="none" style="fill:var(--drawing-body,none)" d="{bd}"/>'
    k = 1000.0 / h
    W = round(w * k, 1)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} 1000" role="img">\n'
           f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
           f'<g transform="scale({k:.6f})"><g transform="{tr}">{body_path}'
           f'<path class="lines" fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/></g></g>\n</svg>\n')
    out.write_text(svg)
    return {"bytes": out.stat().st_size, "viewBox": (W, 1000), "box": (int(x0), int(y0), int(x1), int(y1)),
            "weight_before": round(before * 100, 3), "weight_after": round(line_width(weighted) / max(weighted.shape) * 100, 3)}


def qa_dark(svg: Path, box: tuple, out: Path, clay: str = "#c4b294", line: str = "#1b1c1f",
            ground: str = "#131414") -> None:
    """The drawing as the dark theme shows it (lines dark on a clay-filled
    figure, on a dark ground), rendered at the size of the crop box so it
    lines up pixel for pixel with qa_overlay."""
    x0, y0, x1, y1 = box
    s = svg.read_text().replace('style="fill:var(--drawing-body,none)"', f'fill="{clay}"')
    s = s.replace('fill="currentColor"', f'fill="{line}"')
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "d.svg"
        f.write_text(s)
        subprocess.run(["rsvg-convert", "-w", str(x1 - x0), "-h", str(y1 - y0), "-b", ground, str(f),
                        "-o", str(out)], check=True)


def qa_overlay(gray: np.ndarray, svg: Path, box: tuple, out: Path) -> None:
    """The finished drawing in red over its source in grey (same pixels as
    the ink given to trace_svg; `box` is the crop box it returned). Any grey
    line left showing is a line the drawing missed."""
    x0, y0, x1, y1 = box
    with tempfile.TemporaryDirectory() as td:
        png, lines = Path(td) / "d.png", Path(td) / "lines.svg"
        # lines only: rsvg reads var(--drawing-body,none) as black, not as its fallback
        lines.write_text(re.sub(r'<path class="body"[^>]*/>', "", svg.read_text()))
        subprocess.run(["rsvg-convert", "-w", str(x1 - x0), "-h", str(y1 - y0), str(lines), "-o", str(png)], check=True)
        a = np.asarray(Image.open(png).convert("RGBA"), dtype=np.float32)[..., 3] / 255
    g = gray[y0:y1, x0:x1].astype(np.float32)
    g = 255 - (255 - g) * 0.6  # lighten the source so red reads on top
    rgb = np.stack([g, g, g], -1)
    a = a[:rgb.shape[0], :rgb.shape[1], None]
    rgb = rgb * (1 - a) + np.array([215, 0, 0], np.float32) * a
    Image.fromarray(rgb.astype(np.uint8)).save(out)


# ---------------------------------------------------------------- masses (potrace)

def potrace_d(mass: np.ndarray, turdsize: int = 10, alphamax: float = 1.0) -> tuple[str, str]:
    """Trace a filled mask with potrace. Returns (path d, transform)."""
    with tempfile.TemporaryDirectory() as td:
        pbm = Path(td) / "m.pbm"
        svg = Path(td) / "m.svg"
        Image.fromarray((~mass.astype(bool)).astype(np.uint8) * 255).convert("1").save(pbm)
        subprocess.run(["potrace", str(pbm), "-b", "svg", "--flat", "-t", str(turdsize),
                        "-a", str(alphamax), "-O", "1.0", "-u", "1", "-o", str(svg)], check=True)
        s = svg.read_text()
    tr = re.search(r'<g transform="([^"]+)"', s).group(1)
    d = " ".join(re.findall(r'<path d="([^"]+)"', s))
    return re.sub(r"\s+", " ", d), tr


# ---------------------------------------------------------------- SVG writer
