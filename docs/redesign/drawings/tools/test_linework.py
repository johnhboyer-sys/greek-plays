"""Checks for trace_svg's body path, as the dark theme shows it: no clay past
the outline along a straight edge, and none lost inside it. A rod drawn with
lines twice the house weight (trace_svg thins them by half, as on the
Pythia's plate) and a ring small enough that the body's edge, pulled under
its line, would leave less than potrace's speck limit, rendered at 1400px.
And a dot under that limit, kept only when passed as `dots`.

    python3 docs/redesign/drawings/tools/test_linework.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import linework as lw  # noqa: E402

H, W = 1000, 300
ROD = (60, 940, 40, 80)       # y0, y1, x0, x1: the rod's outer edge
LINE = 4                      # px, raw: the house weight here is about 2
RING = (500, 200, 4, 2)       # centre y, x, outer radius, line width
DOT = (300, 150, 2)           # centre y, x, radius: under the speck limit at turdsize 100


def drawing():
    ink, body = np.zeros((H, W), bool), np.zeros((H, W), bool)
    y0, y1, x0, x1 = ROD
    body[y0:y1, x0:x1] = True
    ink[y0:y1, x0:x1] = True
    ink[y0 + LINE:y1 - LINE, x0 + LINE:x1 - LINE] = False
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(yy - RING[0], xx - RING[1])
    body |= r <= RING[2]
    ink |= (r <= RING[2]) & (r > RING[2] - RING[3])
    return ink, body


def render(svg: str, w: int) -> np.ndarray:
    with tempfile.TemporaryDirectory() as td:
        f, o = Path(td) / "a.svg", Path(td) / "a.png"
        f.write_text(svg)
        subprocess.run(["rsvg-convert", "-w", str(w), str(f), "-o", str(o)], check=True)
        return np.asarray(Image.open(o).convert("RGBA"), dtype=np.float32)[..., 3] / 255


def main() -> None:
    ink, body = drawing()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "t.svg"
        bx0, by0, bx1, _ = lw.trace_svg(ink, out, title="t", desc="t", body=body)["box"]
        s = out.read_text()
    lines = render(re.sub(r'<path class="body"[^>]*/>', "", s).replace("currentColor", "#000"), 1400)
    clay = render(re.sub(r'<path class="lines"[^>]*/>', "", s).replace('fill="none"', 'fill="#000"'), 1400)
    shown = clay * (1 - lines)  # clay left showing between and past the lines
    k = 1400 / (bx1 - bx0)  # render px per source px
    px = lambda x, y: (int((x - bx0) * k), int((y - by0) * k))  # noqa: E731
    y0, y1, x0, x1 = ROD
    # along the rod's straight sides (not its ends), clay left of its left line or right of its right one
    (a, top), (z, bot) = px(bx0, y0 + 20), px(x1 + 10, y1 - 20)
    on, cols = lines[top:bot, a:z] > 0.5, np.arange(z - a)
    first, last = on.argmax(1)[:, None], (z - a - 1 - on[:, ::-1].argmax(1))[:, None]
    past = (shown[top:bot, a:z] > 0.1) & ((cols < first) | (cols > last))
    (a, r), (z, _) = px(x0 + LINE, (y0 + y1) / 2), px(x1 - LINE, 0)
    inside = (shown[r, a:z] > 0.5).mean()
    (a, c), (z, e) = px(RING[1] - 1.5, RING[0] - 1.5), px(RING[1] + 1.5, RING[0] + 1.5)
    ring = shown[c:e, a:z]
    print(f"clay past the lines: {int(past.sum())} px; rod's inside showing clay: {inside:.0%}; "
          f"ring's inside showing clay: {(ring > 0.5).mean():.0%}")
    assert past.sum() == 0, "clay shows past the outline"
    assert inside > 0.9, "clay lost inside the rod"
    assert (ring > 0.5).mean() > 0.5, "clay lost inside the ring"
    dots_check()
    print("ok")


def dots_check() -> None:
    """A dot under potrace's speck limit: dropped from the ink, kept when passed as `dots`."""
    ink, _ = drawing()
    yy, xx = np.mgrid[0:H, 0:W]
    dot = np.hypot(yy - DOT[0], xx - DOT[1]) <= DOT[2]
    shown = []
    for kw in ({}, {"dots": dot}):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.svg"
            bx0, by0, bx1, _ = lw.trace_svg(ink | dot, out, title="t", desc="t", turdsize=100, **kw)["box"]
            lines = render(out.read_text().replace("currentColor", "#000"), 1400)
        k = 1400 / (bx1 - bx0)
        shown.append(lines[int((DOT[0] - by0) * k), int((DOT[1] - bx0) * k)])
    print(f"a dot under the speck limit: {shown[0]:.0%} drawn from the ink alone, {shown[1]:.0%} passed as dots")
    assert shown[0] < 0.5, "the dot was not under the speck limit: the check examined nothing"
    assert shown[1] > 0.5, "a dot passed as dots was dropped"


if __name__ == "__main__":
    main()
