# Drawings: phase 1 test (2026-10-02, revised the same day)

Test drawings for the redesign (DESIGN.md, Drawings). Records with credits
and licences: `../research/play-image-plan.json` (the `playwrights` list and
the Medea and Iphigenia at Aulis entries). Open `contact-sheet.html` to see
them on every ground, light and dark.

| File | Figure | Source |
|---|---|---|
| `aeschylus-pythia.svg` | the Pythia | Bötticher 1859 plate, Heidelberg scan (public domain) |
| `sophocles-euphorbos.svg` | Euphorbos carrying the infant Oedipus (Sophocles' home-page figure) | Cabinet des médailles 372, four photos by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0); unrolled off the vase with `tools/vase_unroll.py` |
| `sophocles-oedipus.svg` | Oedipus (superseded by the Euphorbos drawing) | Berlin F 2355, photo by Gary Todd (CC0) |
| `euripides-iphigenia.svg` | Iphigenia | Archäologische Zeitung 1849 Taf. XII (public domain) |
| `aristophanes-mika.svg` | Mika | Würzburg H 5697, photo by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0) |
| `medea.svg` | Medea | Cleveland 1991.1, museum photo (CC0) |
| `oedipus-tyrannus.svg` | Oedipus (Oedipus Tyrannus) | Syracuse 66557, photo by Dan Diffendale (CC BY-NC-SA 2.0); the drawing traces only the painting, so it does not carry that licence (John, 2026-10-02) |
| `antigone.svg` | Antigone, bound, before Creon (Antigone) | Berlin F 3240, photo by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0); flattened off the vase with `tools/vase_unroll.py` |
| `rejected/iphigenia-at-aulis.svg` | failed test, not for use | Met 31.11.2, museum photo (CC0) |
| `alternates/sophocles-oedipus-sphinx-vatican.svg` | Oedipus and the Sphinx | 2009 public-domain vector redrawing of Vatican 16541 |

## The files

Each SVG is 1000 units tall, on a transparent ground, with two paths:

- `lines`: the drawing, `fill="currentColor"`. Lines are filled outlines
  traced by potrace, not strokes. Every drawing has the same line weight:
  0.225% of its longer side, so drawings fitted into the same box show the
  same line.
- `body`: the figure's whole area, under the lines, `class="body"
  fill="none"`, so it is transparent unless a page fills it with CSS
  (`.body { fill: <clay> }` in the dark theme). It has no holes, and lines
  too thin to hold clay on either side (a goad, a spear) get a narrow clay
  rim. The contact sheet's dark boards set it to a clay colour and keep
  the lines dark, so a drawing reads as a red-figure vase instead of a photo
  negative. At 400px the lines
hold; at 120px they go faint unless CSS adds `stroke: currentColor;
stroke-width: .5px` (the path has `vector-effect="non-scaling-stroke"`, so
the stroke stays .5px at any size). Where between the two to switch it on is
a layout decision.

## Rerunning

Sources are not committed. Download each source file named at the top of its
tool, then, from this folder (`docs/redesign/drawings`):

```
brew install potrace librsvg
python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-image pillow
.venv/bin/python tools/pythia.py bwpr1859_010a.jpg qa.png   # qa.png optional
.venv/bin/python tools/contact_sheet.py
```

The optional second argument writes two check images, `qa.png` and
`qa.dark.png`; they need `rsvg-convert` (librsvg).

The Oedipus alternate starts from the Commons SVG rendered to PNG
(`rsvg-convert -w 4000 -b '#000000'`).

`tools/linework.py` holds the shared steps: ink from a scan (`ink_from_scan`
for engravings; `ink_lines`, local contrast with hysteresis, for fine
lithograph lines and the relief lines of red-figure photos), a least-cost
cut through hand-placed points (`livewire`, with `STRAIGHT` for crossings over
blank paper), the figure's area for the body path (`body_from_cut`), the
house line weight (`set_line_width`), potrace (`trace_svg`), and a check
image of the drawing over its source (`qa_overlay`: any grey line left
showing is a line the drawing missed), and the drawing as the dark theme
shows it, at the same size (`qa_dark`). Each figure's script holds its own
crop, cut points and hand fixes, with the reason for each.

`tools/vase_unroll.py` takes a painting off the curve of its vase. A photo
of a vase foreshortens the painting toward the sides and wherever the
profile slopes (a figure on the shoulder comes out squashed, a long spear
bent, a ground band sagging). The tool fits the vase as a surface of
revolution, and a pinhole camera for each photo, to the silhouettes, a
painted band (level, being painted on the wheel), the ring at the base of
the neck and points matched between photos, then lays a photo onto the
flat. `flatten` flattens the vase as rigidly as it allows (every small patch
keeps its shape); plain unrolling, around by arc length and up the profile,
shears whatever lies off its centre line where the profile slopes. Give it every photo's
focal length from its EXIF, and mark cropped photos (`crop: True`) so their
centres are fitted; fitted free, focal length trades against distance and
the perspective comes out wrong. `tools/euphorbos.py` uses it;
its docstring says what was fitted and how well.
