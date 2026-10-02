# Drawings: phase 1 test (2026-10-02)

Six test drawings for the redesign (DESIGN.md, Drawings). Records with credits
and licences: `../research/play-image-plan.json` (the `playwrights` list and
the Medea and Iphigenia at Aulis entries). Open `contact-sheet.html` to see
them on every ground, light and dark.

| File | Figure | Source |
|---|---|---|
| `aeschylus-pythia.svg` | the Pythia | Bötticher 1859 plate, Heidelberg scan (public domain) |
| `sophocles-oedipus.svg` | Oedipus | Berlin F 2355, photo by Gary Todd (CC0) |
| `euripides-iphigenia.svg` | Iphigenia | Archäologische Zeitung 1849 Taf. XII (public domain) |
| `aristophanes-mika.svg` | Mika | Würzburg H 5697, photo by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0) |
| `medea.svg` | Medea | Cleveland 1991.1, museum photo (CC0) |
| `rejected/iphigenia-at-aulis.svg` | failed test, not for use | Met 31.11.2, museum photo (CC0) |
| `alternates/sophocles-oedipus-sphinx-vatican.svg` | Oedipus and the Sphinx | 2009 public-domain vector redrawing of Vatican 16541 |

## The files

Each SVG is one filled path with `fill="currentColor"`, on a transparent
ground, 1000 units tall. Lines are filled outlines traced by potrace, not
strokes. Every drawing has the same line weight: 0.225% of its longer side,
so drawings fitted into the same box show the same line. At 400px the lines
hold; at 120px they go faint unless CSS adds `stroke: currentColor;
stroke-width: .5px` (the path has `vector-effect="non-scaling-stroke"`, so
the stroke stays .5px at any size). Where between the two to switch it on is
a layout decision.

## Rerunning

Sources are not committed. Download each source file named at the top of its
tool, then:

```
brew install potrace
python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-image pillow
.venv/bin/python tools/pythia.py bwpr1859_010a.jpg
.venv/bin/python tools/contact_sheet.py
```

The Oedipus alternate starts from the Commons SVG rendered to PNG
(`rsvg-convert -w 4000 -b '#000000'`).

`tools/linework.py` holds the shared steps: ink from a scan (`ink_from_scan`
for engravings, `ink_hairlines` for fine lithograph lines), a least-cost cut
through hand-placed points (`livewire`), the house line weight
(`set_line_width`), and potrace (`trace_svg`). Each figure's script holds its
own crop, cut points and hand fixes, with the reason for each.
