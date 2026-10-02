"""Build docs/redesign/drawings/contact-sheet.html from the SVGs listed in
drawings.json: every drawing fitted into a 400px and a 120px square slot,
standing on the slot's ground line, light and dark, on the warm paper and on
each author tint. Each SVG is inlined once as a <symbol> and reused, so
currentColor takes the ink of the board it sits on.

    python3 docs/redesign/drawings/tools/contact_sheet.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # docs/redesign/drawings

# Light values are DESIGN.md's. Dark values are provisional: DESIGN.md says the
# dark tints are still to be made. Paper and ink follow the app's dark tokens.
# In dark mode the drawings keep dark lines and fill the figure with clay
# (--drawing-body), as on a red-figure vase, instead of turning the lines light.
LINE = "#1b1c1f"
CLAY = "#c4b294"
GROUNDS = [
    ("paper", "Warm paper", "#fbf9f4", "#1b1c1f", "#131414", "#e6e6e1"),
    ("aeschylus", "Aeschylus slate", "#e2e7ec", "#1b1c1f", "#182027", "#e6e6e1"),
    ("sophocles", "Sophocles sage", "#e3e8df", "#1b1c1f", "#1a2019", "#e6e6e1"),
    ("euripides", "Euripides clay", "#efe2dc", "#1b1c1f", "#261b17", "#e6e6e1"),
    ("aristophanes", "Aristophanes ochre", "#f0e7d2", "#1b1c1f", "#252013", "#e6e6e1"),
]


def symbol(slug: str, svg: str) -> str:
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    body = re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S)
    body = re.sub(r"</svg>\s*$", "", body)
    body = re.sub(r"<title>.*?</title>|<desc>.*?</desc>", "", body, flags=re.S)
    return f'<symbol id="d-{slug}" viewBox="{vb}">{body.strip()}</symbol>', vb


def main() -> None:
    items = json.loads((HERE / "drawings.json").read_text())["drawings"]
    syms, boxes = [], {}
    for it in items:
        if not it["file"]:
            continue
        s, vb = symbol(it["slug"], (HERE / it["file"]).read_text())
        syms.append(s)
        _, _, w, h = (float(v) for v in vb.split())
        boxes[it["slug"]] = (w, h)

    def fig(it, size):
        if it["slug"] not in boxes:
            return (f'<figure style="width:{size}px"><div class="missing" style="height:{size}px">not yet drawn</div>'
                    f'<figcaption>{html.escape(it["name"])}</figcaption></figure>')
        w, h = boxes[it["slug"]]
        k = min(size / w, size / h)  # fit the drawing into the square slot
        label = html.escape(it["alt"])
        return (f'<figure style="width:{size}px"><div class="slot" style="height:{size}px">'
                f'<svg class="dr" width="{round(w * k)}" height="{round(h * k)}" viewBox="0 0 {w:g} {h:g}" '
                f'role="img" aria-label="{label}"><use href="#d-{it["slug"]}"/></svg></div>'
                f'<figcaption>{html.escape(it["name"])}</figcaption></figure>')

    boards = []
    for theme in ("light", "dark"):
        for key, name, lbg, lfg, dbg, dfg in GROUNDS:
            bg, fg = (lbg, lfg) if theme == "light" else (dbg, dfg)
            big = "".join(fig(it, 400) for it in items)
            small = "".join(fig(it, 120) for it in items)
            body = "none" if theme == "light" else CLAY
            boards.append(
                f'<section class="board" id="{theme}-{key}" style="--bg:{bg};--fg:{fg};--body:{body}">'
                f'<h2>{"Light" if theme == "light" else "Dark"} · {name} <code>{bg}</code></h2>'
                f'<div class="row big">{big}</div><div class="row small">{small}</div></section>')

    nav = " ".join(f'<a href="#{t}-{k}">{t[0].upper()}{t[1:]}: {n}</a>'
                   for t in ("light", "dark") for k, n, *_ in GROUNDS)
    rows = "".join(
        f"<tr><td>{html.escape(it['name'])}</td><td>{html.escape(it['source'])}</td>"
        f"<td>{html.escape(it['method'])}</td><td>{html.escape(it['verdict'])}</td></tr>" for it in items if it["file"])
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Drawing Test Sheet</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Alegreya+Sans:wght@400;500&family=Cardo:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{{--page:#f4f3ef;--ink:#1b1c1f;--mid:#5c6064}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--page:#17191a;--ink:#e4e3de;--mid:#a4a8a6}}}}
:root[data-theme="dark"]{{--page:#17191a;--ink:#e4e3de;--mid:#a4a8a6}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--ink);font:16px/1.5 "Alegreya Sans",system-ui,sans-serif}}
header,.notes{{max-width:1320px;margin:0 auto;padding:28px 16px 8px}}
h1{{font:400 32px/1.2 Cardo,Georgia,serif;margin:0 0 8px}}
header p,.notes p{{margin:4px 0;max-width:80ch;color:var(--mid)}}
nav{{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:10px;font-size:15px}}
nav a{{color:var(--ink)}}
table{{border-collapse:collapse;margin:10px 0 0;font-size:14px;max-width:1320px}}
td{{padding:6px 12px 6px 0;vertical-align:top}}
.board{{background:var(--bg);color:var(--fg);padding:24px 16px 32px}}
.board h2{{max-width:1320px;margin:0 auto 18px;font:400 22px/1.2 Cardo,Georgia,serif}}
.board h2 code{{font:14px ui-monospace,monospace;opacity:.7;margin-left:6px}}
.row{{max-width:1320px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:flex-end;gap:36px 40px}}
.row.small{{margin-top:36px;gap:28px 32px}}
figure{{margin:0;max-width:100%}}
.slot{{display:flex;align-items:flex-end;justify-content:center;border-bottom:1px solid currentColor;max-width:100%}}
.dr{{display:block;color:{LINE};--drawing-body:var(--body);overflow:visible;max-width:100%;height:auto}}
figcaption{{font-size:13px;line-height:1.35;margin-top:6px;opacity:.8;height:2.7em;overflow:hidden}}
.small figcaption{{font-size:11px;height:4.05em}}
.small .dr{{stroke:currentColor;stroke-width:.5px}}
.missing{{display:flex;align-items:center;justify-content:center;font-size:13px;opacity:.6;outline:1px dashed currentColor}}
@media (max-width:440px){{.row.big .slot{{height:auto!important;aspect-ratio:1}}}}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">{"".join(syms)}</svg>
<header><h1>Drawing test: five drawings, revised</h1>
<p>Each drawing is fitted into a 400px and a 120px square slot, in light and dark, on the warm paper and on each author tint. The line under each slot is the ground line. The dark grounds are provisional: DESIGN.md says the dark tints are still to be made.</p>
<p>The drawings are filled shapes traced by potrace, with fill currentColor, and one line weight: 0.225% of the drawing's longer side, so drawings in the same slot show the same line. In the 120px slots the page adds a 0.5px stroke in currentColor so the lines stay visible; the 400px slots have none.</p>
<p>Dark mode: the lines stay dark and the figure is filled with clay ({CLAY}), as on a red-figure vase, rather than turning the lines light. Each SVG carries the figure's area as a second path, filled with var(--drawing-body, none): transparent unless the page sets it.</p>
<nav>{nav}</nav>
<table><tbody>{rows}</tbody></table></header>
{"".join(boards)}
</body></html>
"""
    (HERE / "contact-sheet.html").write_text(page)
    print("wrote", HERE / "contact-sheet.html", len(page), "bytes")


if __name__ == "__main__":
    main()
