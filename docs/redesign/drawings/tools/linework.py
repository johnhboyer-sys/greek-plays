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

def livewire(cost: np.ndarray, points: list[tuple[float, float]], closed: bool = False) -> np.ndarray:
    """Least-cost path through hand-placed (x, y) points, as in a magnetic lasso:
    between each pair of points the path follows low `cost` (e.g. ink or a
    shading edge). Returns an (x, y) polyline in pixel centres."""
    from skimage.graph import route_through_array
    pts = [(int(round(y)), int(round(x))) for x, y in points]
    if closed:
        pts.append(pts[0])
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        path, _ = route_through_array(cost, a, b, fully_connected=True, geometric=True)
        out.extend(path if not out else path[1:])
    return np.array([(x + 0.5, y + 0.5) for y, x in out], dtype=float)


def polygon_mask(shape, xy: np.ndarray) -> np.ndarray:
    from skimage.draw import polygon
    m = np.zeros(shape, bool)
    rr, cc = polygon(xy[:, 1], xy[:, 0], shape)
    m[rr, cc] = True
    return m


# ---------------------------------------------------------------- engraved plates

def ink_hairlines(gray: np.ndarray, size: int = 9, t: float = 16.0) -> np.ndarray:
    """Fine grey lithograph lines -> bool ink mask: a line is a pixel darker
    than its surroundings (black top-hat over a size x size window) by more
    than t grey levels. Catches hairlines a global threshold breaks up."""
    g = ndi.gaussian_filter(gray.astype(np.float32), 0.7)
    return (ndi.grey_closing(g, size=(size, size)) - g) > t


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


def trace_svg(ink: np.ndarray, out: Path, *, title: str, desc: str, pad: int = 4,
              turdsize: int = 10, alphamax: float = 1.0) -> dict:
    """Crop a figure's ink, rescale it to WORK_H px tall, set the house line
    weight, and potrace it into a theme-following SVG (fill currentColor)
    1000 units tall."""
    ys, xs = np.nonzero(ink)
    ink = ink[max(ys.min() - pad, 0):ys.max() + pad + 1, max(xs.min() - pad, 0):xs.max() + pad + 1]
    before = line_width(ink) / max(ink.shape)
    crop = resample_ink(ink, WORK_H)
    crop = set_line_width(crop, HOUSE_WEIGHT * max(crop.shape))
    weighted = crop
    crop = resample_ink(crop, TRACE_H)  # trace smaller: fewer, smoother curves
    h, w = crop.shape
    d, tr = potrace_d(crop, turdsize=turdsize, alphamax=alphamax)
    k = 1000.0 / h
    W = round(w * k, 1)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} 1000" role="img">\n'
           f'<title>{esc(title)}</title>\n<desc>{esc(desc)}</desc>\n'
           f'<g transform="scale({k:.6f})"><g transform="{tr}">'
           f'<path fill="currentColor" vector-effect="non-scaling-stroke" d="{d}"/></g></g>\n</svg>\n')
    out.write_text(svg)
    return {"bytes": out.stat().st_size, "viewBox": (W, 1000),
            "weight_before": round(before * 100, 3), "weight_after": round(line_width(weighted) / max(weighted.shape) * 100, 3)}


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
