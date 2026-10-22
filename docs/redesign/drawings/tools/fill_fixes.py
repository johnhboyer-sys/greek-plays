"""John's body-fill rulings (2026-10-22), laid onto a finished drawing.

B's design fills the body with clay on both themes, so a gap the body leaves out shows the page where clay belongs.
John flagged them on the drawings as the site shows them and ruled each one; this tool lays the rulings onto the
drawing its own tool wrote, and adds shapes only: the lines and the body as traced stay, byte for byte, and each fix
is a new potrace subpath appended to the body (clay) or the lines (ink). `close_min` starts the closing wider, for a
gap that leaks out through a hairline beside the one clicked.

Each fix names a point (the drawing's own units, as John clicked it) and an op:
  - clay: the gap round the point becomes clay. A gap that runs out into the ground is first closed across its
    narrowest mouth: the lines and body are closed (morphologically) over the smallest radius, up to `close` trace
    px, that seals the gap off; the clay then fills the sealed gap, up to the lines.
  - ink: the same, filled with the line colour (John on Euphorbos's sandals: "close up the back and then fill with
    black ink").
  - ground: the clay round the point, out to the lines that enclose it, cut from the body (traced, then appended
    reversed, so it winds the body's clay back to nothing there).
  - line: a line John drew (`pts`, drawing units), inked `w` trace px wide with round ends.
A fix may carry `seal`: a polyline (drawing units) John drew where the gap is to be closed, laid in as a line first,
so the gap closes there and not at the narrowest mouth. The gaps within NEAR trace px of the point go in with it (a
click lands beside a small gap as often as in it).

    python3 docs/redesign/drawings/tools/fill_fixes.py <drawing.svg> <fixes.json>

The fixes file: {"<drawing>.svg": [{"op": "clay"|"ink", "at": [x, y], "close": r, "why": "..."}]}.
"""
import json
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

WIN = 300          # trace px each side of the point searched for the gap
CLOSE_MAX = 12     # the widest mouth closed, trace px, unless a fix says otherwise
NEAR = 8           # trace px round the point within which every gap is taken
SEAL_W = 3         # trace px, the width of a drawn seal


def masks(svg: str, size: tuple[int, int], cls: list[str]) -> np.ndarray:
    """The paths of the given classes, filled, in trace px (the inner group's own units)."""
    w, h = size
    s = re.sub(r'<g transform="rotate\([^)]*\)">', "<g>", svg, count=1)       # levelling turns sit outside the trace
    scale = float(re.search(r'<g transform="scale\(([0-9.]+)\)">', s).group(1))
    s = re.sub(r'viewBox="[^"]+"', f'viewBox="0 0 {w * scale} {h * scale}" width="{w}" height="{h}"', s, count=1)
    css = ("<style>path{fill:none !important;stroke:none !important;fill-opacity:1 !important} "
           + " ".join(f"path.{c}{{fill:#000 !important}}" for c in cls) + "</style>")
    s = re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + css, s, count=1)
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "m.png"
        png.write_bytes(subprocess.run(["rsvg-convert", "-b", "white"], input=s.encode(), capture_output=True,
                                       check=True).stdout)
        return np.asarray(Image.open(png).convert("L"))[:h, :w] < 128


def gap(cov: np.ndarray, p: tuple[int, int], close_max: int, close_min: int = 0, win: int = WIN) -> tuple[np.ndarray, int]:
    """The gap round p (trace px), sealed across its narrowest mouth: (mask, closing radius). A gap larger than the
    window is looked for again in a window three times as wide."""
    x, y = p
    WIN = win
    y0, x0 = max(y - WIN, 0), max(x - WIN, 0)
    w = cov[y0:y + WIN, x0:x + WIN]
    py, px = y - y0, x - x0
    if w[py, px]:                             # a click that landed on a line: the nearest open pixel
        _, (iy, ix) = ndi.distance_transform_edt(w, return_indices=True)
        py, px = iy[py, px], ix[py, px]
    for r in range(close_min, close_max + 1):
        closed = w if r == 0 else ndi.binary_closing(np.pad(w, r + 1), morphology.disk(r))[r + 1:-r - 1, r + 1:-r - 1]
        inside = ndi.binary_fill_holes(closed) & ~w
        lab, _ = ndi.label(inside)
        if lab[py, px]:
            yy, xx = np.ogrid[:lab.shape[0], :lab.shape[1]]
            near = (yy - py) ** 2 + (xx - px) ** 2 <= NEAR ** 2
            ids = [i for i in np.unique(lab[near]) if i and (lab == i).sum() < (lab == lab[py, px]).sum() * 4 + 400]
            out = np.zeros_like(cov)
            out[y0:y + WIN, x0:x + WIN] = np.isin(lab, ids)
            return out, r
    if win < 3 * globals()["WIN"]:
        return gap(cov, p, close_max, close_min, 3 * win)
    raise SystemExit(f"no gap sealed at {p} within {close_max} px")


def reverse_d(d: str) -> str:
    """potrace's flat path (M/m, c, l, z) with every subpath run backwards, in absolute coordinates."""
    toks = re.findall(r"[MmclzZ]|-?\d+(?:\.\d+)?", d)
    subs, i, cur, start, op = [], 0, (0.0, 0.0), (0.0, 0.0), None
    while i < len(toks):
        if toks[i] in "MmclzZ":
            op = toks[i]
            i += 1
            if op in "zZ":
                cur = start
                continue
        if op in "Mm":
            x, y = float(toks[i]), float(toks[i + 1])
            i += 2
            cur = (x, y) if op == "M" or not subs else (cur[0] + x, cur[1] + y)
            start = cur
            subs.append([cur, []])
            op = "l"                          # pairs after a moveto are linetos
        elif op == "c":
            v = [float(t) for t in toks[i:i + 6]]
            i += 6
            p1, p2, p3 = [(cur[0] + v[k], cur[1] + v[k + 1]) for k in (0, 2, 4)]
            subs[-1][1].append(("C", p1, p2, p3, cur))
            cur = p3
        elif op == "l":
            v = (cur[0] + float(toks[i]), cur[1] + float(toks[i + 1]))
            i += 2
            subs[-1][1].append(("L", v, cur))
            cur = v
    out = []
    for s0, segs in subs:
        end = segs[-1][-2] if segs[-1][0] == "L" else segs[-1][3]
        parts = [f"M{end[0]:g} {end[1]:g}"]
        for seg in reversed(segs):
            if seg[0] == "C":
                _, p1, p2, p3, p0 = seg
                parts.append(f"C{p2[0]:g} {p2[1]:g} {p1[0]:g} {p1[1]:g} {p0[0]:g} {p0[1]:g}")
            else:
                parts.append(f"L{seg[2][0]:g} {seg[2][1]:g}")
        out.append(" ".join(parts) + "z")
    return " ".join(out)


def append(svg: str, cls: str, d: str) -> str:
    """Append subpaths to the first path of the class (same group, same trace px)."""
    m = re.search(rf'(<path class="{cls}"[^>]*? d=")([^"]*)(")', svg)
    return svg[:m.start(2)] + m.group(2) + " " + d + svg[m.end(2):]


def main(svg_path: str, fixes_path: str) -> None:
    path = Path(svg_path)
    svg = path.read_text()
    fixes = json.loads(Path(fixes_path).read_text()).get(path.name, [])
    if not fixes:
        return
    scale = float(re.search(r'<g transform="scale\(([0-9.]+)\)">', svg).group(1))
    h = int(float(re.search(r'translate\(0\.000000,([0-9.]+)\)', svg).group(1)))
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    rot = re.search(r'<g transform="rotate\(([-0-9.]+) ([0-9.]+) ([0-9.]+)\)">', svg)
    w = int(round((vb[0] + vb[2]) / scale)) + 2
    cov = masks(svg, (w, h), ["body", "lines"])
    add = {"clay": np.zeros_like(cov), "ink": np.zeros_like(cov), "ground": np.zeros_like(cov)}
    lines = masks(svg, (w, h), ["lines"])
    body = masks(svg, (w, h), ["body"])
    def unturn(x, y):
        """A point as clicked, back onto the unturned trace."""
        if not rot:
            return x, y
        a, cx, cy = map(float, rot.groups())
        t = np.radians(-a)
        return cx + (x - cx) * np.cos(t) - (y - cy) * np.sin(t), cy + (x - cx) * np.sin(t) + (y - cy) * np.cos(t)

    def polyline(pts, w):
        """A polyline in drawing units, inked w trace px wide."""
        m = np.zeros_like(cov)
        pts = [unturn(*q) for q in pts]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = int(max(abs(bx - ax), abs(by - ay)) / scale * 2) + 1
            for k in range(n + 1):
                m[int(round((ay + (by - ay) * k / n) / scale)), int(round((ax + (bx - ax) * k / n) / scale))] = True
        return ndi.binary_dilation(m, morphology.disk(max(w // 2, 1))) if w > 1 else m

    for f in fixes:
        if f["op"] == "line":
            add["ink"] |= polyline(f["pts"], f["w"])
            print(f'line {f["pts"][0]}..{f["pts"][-1]}, {f["w"]} trace px')
            continue
        x, y = unturn(*f["at"])
        here = cov
        seal = np.zeros_like(cov)
        if "seal" in f:                       # John's closing line, drawn in first
            pts = [unturn(*q) for q in f["seal"]]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                n = int(max(abs(bx - ax), abs(by - ay)) / scale) + 1
                for k in range(n + 1):
                    seal[int(round((ay + (by - ay) * k / n) / scale)), int(round((ax + (bx - ax) * k / n) / scale))] = True
            seal = ndi.binary_dilation(seal, morphology.disk(SEAL_W // 2 + 1)) & ~cov
            here = cov | seal
        if f["op"] == "ground":                # the clay between the lines round the point
            m, r = gap(lines | seal, (int(round(x / scale)), int(round(y / scale))), f.get("close", CLOSE_MAX),
                       f.get("close_min", 0))
            add["ground"] |= m & body
            print(f'ground at {f["at"]}: {int((m & body).sum())} trace px, mouth closed at {r} px')
            continue
        m, r = gap(here, (int(round(x / scale)), int(round(y / scale))), f.get("close", CLOSE_MAX), f.get("close_min", 0))
        if f["op"] == "ink":
            m |= seal
        # a pixel over the edge it meets, so no seam of page shows where the new shape meets the old
        add[f["op"]] |= ndi.binary_dilation(m) & (m | cov)
        print(f'{f["op"]} at {f["at"]}: {int(m.sum())} trace px, mouth closed at {r} px')
    if add["clay"].any():
        svg = append(svg, "body", lw.potrace_d(add["clay"], turdsize=0)[0])
    if add["ink"].any():
        svg = append(svg, "lines", lw.potrace_d(add["ink"], turdsize=0)[0])
    if add["ground"].any():
        svg = append(svg, "body", reverse_d(lw.potrace_d(add["ground"], turdsize=0)[0]))
    path.write_text(svg)


if __name__ == "__main__":
    main(*sys.argv[1:3])
