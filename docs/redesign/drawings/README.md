# Drawings: phase 1 test (2026-10-02, revised the same day)

Test drawings for the redesign (DESIGN.md, Drawings). Records with credits
and licences: `../research/play-image-plan.json` (the `playwrights` list, and
the `plays` entry of each play drawn). Open `contact-sheet.html` to see
them on every ground, light and dark.

| File | Figure | Source |
|---|---|---|
| `aeschylus-pythia.svg` | the Pythia | Bötticher 1859 plate, Heidelberg scan (public domain) |
| `sophocles-euphorbos.svg` | Euphorbos carrying the infant Oedipus (Sophocles' home-page figure) | Cabinet des médailles 372, four photos by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0); flattened off the vase with `tools/vase_unroll.py` |
| `sophocles-oedipus.svg` | Oedipus (superseded by the Euphorbos drawing) | Berlin F 2355, photo by Gary Todd (CC0) |
| `euripides-iphigenia.svg` | Iphigenia | Archäologische Zeitung 1849 Taf. XII (public domain) |
| `aristophanes-mika.svg` | Mika | Würzburg H 5697, photo by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0) |
| `medea.svg` | Medea | Cleveland 1991.1, museum photo (CC0) |
| `oedipus-tyrannus.svg` | Oedipus (Oedipus Tyrannus) | Syracuse 66557, photo by Dan Diffendale (CC BY-NC-SA 2.0); the drawing traces only the painting, so it does not carry that licence (John, 2026-10-02) |
| `antigone.svg` | Antigone, bound, before Creon (Antigone) | Berlin F 3240, photo by ArchaiOptix (CC BY-SA 4.0, so the drawing is CC BY-SA 4.0); flattened off the vase with `tools/vase_unroll.py` |
| `philoctetes.svg` | Philoctetes alone on Lemnos, with the rock he sits on and his bow case (Philoctetes) | Met 56.171.58, photos by Marie-Lan Nguyen (CC BY 2.5) and the Met (CC0); the drawing traces only the painting, so it carries no licence (John, 2026-10-03); flattened off the vase with `tools/vase_unroll.py` |
| `oedipus-coloneus.svg` | Oedipus with Ismene and Antigone (Oedipus at Colonus) | Geddes A 5:8, the photos in Green 2003 (pp. 4, 26 and 29, HathiTrust), placed on their reprint in Taplin, *Pots & Plays* no. 27, with Ismene's lines and borders, and those outside p. 26, from a photo found online (source unknown), checked against Digital LIMC photo 8569X101; the drawing traces only the painting, so it does not carry the photos' rights (John, 2026-10-02) |
| `hippolytus.svg` | an Amazon fighting a hoplite, Gerhard's "Theseus und Antiope" (Hippolytus) | Gerhard, *Auserlesene griechische Vasenbilder* III (1847), Taf. CLXV, 4, Heidelberg scan (public domain) |
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
  (`.body { fill: <clay> }` in the dark theme). It has no holes, except where a
  scene shows the black ground through it or leaves ground open
  (`open_holes`, where no clay rim goes either, except along `rim_lines`:
  thin clay things that cross open ground, like Hippolytus' bowstring), and lines
  too thin to hold clay on either side (a goad, a spear) get a narrow clay
  rim. The contact sheet's dark boards set it to a clay colour and keep
  the lines dark, so a drawing reads as a red-figure vase instead of a photo
  negative. At 400px the lines
hold; at 120px they go faint unless CSS adds `stroke: currentColor;
stroke-width: .5px` (the path has `vector-effect="non-scaling-stroke"`, so
the stroke stays .5px at any size). Where between the two to switch it on is
a layout decision.

A drawing may carry a third path between the two: `tone` (only
`philoctetes.svg` so far), `fill="currentColor"` at partial opacity
(`fill-opacity`) and `stroke="none"`, for the brown wash of hair and beard,
which on the vase is thinned glaze over the clay. On a light page it shows
grey; on the dark theme's clay, a darker clay. It needs no CSS (John,
2026-10-03: "can you do a half-dark tone for the beard to mimic the tone of
the original on the beard?", "same for hair").

`andromache.svg` carries several `tone` paths, for the blood. Its line
weight is the plate's own, 0.155%, not the house weight (John, 2026-10-06).

## Blood

On the vase, blood is thinned paint laid on in lighter brushstrokes. The
drawing shows it as a wash in the line colour, not as lines. These rules
come from John's rulings on Andromache (2026-10-06); `tools/andromache.py`
holds them (`BLOOD`, `PAINTED`, `BLOOD_T`, `BLEND_*`, `RIM`, `BIT`).

- No black outlines on the blood. Where John traced a streak's outline
  (Priam's scalp), the outline is part of the wash. Lines that cross the
  blood (Astyanax's body) stay black and show through it ("you should be able
  to see black lines through the blood"). The dots of Priam's stubble stay
  black.
- The wash follows the plate. Its opacity runs from 0.25 where the plate is
  light (grey 140, after denoising) to 0.55 where it is darkest (85),
  smoothed over 2 plate px, in steps of 0.05. Each step is a path drawn over
  the larger step below it, at the opacity that brings the total to the
  step's value, so no seam shows between steps. John saw flat tones (they
  read as grey patches, and two tones side by side looked patchy) and a
  blend, and chose the blend: "make it more subtle".
- Where its edges come from: on Priam, from the shapes John's outlines
  close where he marked them. On Astyanax, from the plate's own streak under
  his paint (darker than grey 132): his brush is broader than the streaks,
  and drawn as painted the wounds came out "absurdly big". The plate's
  darker rim just outside a wound goes too ("The black circular outlines for
  the wounds aren't in the original").

How John marks it, on a tracing crop of the plate (or on a screenshot of
the drawing's close-up, placed by its ruler): blue is black ink, his lines;
blue paint over his own outlines marks the shapes they close as blood;
green marks blood painted with no outline (he used dark and light green for
darker and lighter blood, but the wash takes its darkness from the plate).
A line he painted over is joined across the paint (`JOINS`). The marks are
kept in `tools/andromache_traces.json` (`fill`, `fill_dark`, `fill_light`),
plate px. The scripts that read his marks (`map_trace.py`: blue strokes,
filled marks and dots; `map_fill.py`: blue paint on a screenshot;
`map_blood.py`: green on a crop; `crisp.py`: sharp close-ups) are kept with
the batch's sources in `.remember/batch1-2026-10-06/scripts/`.

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

`tools/oedipus_colonus.py` starts from the plate on page 112 of the Getty
PDF of *Pots & Plays* (`pdfimages -j -f 112 -l 112`), which sets the frame,
and three page images of Green 2003 from HathiTrust (mdp.39015060089391,
seq 6, 28 and 31, as TIFF), which it registers to the plate and draws from,
and a photo of the scene John found online (`found.png`, 547x560, source
unknown), which gives the painted lines and borders outside p. 26: Ismene, the
altar's left end, and the strip along the bottom.
It also needs `opencv-python-headless`: non-local means clears the plate's
JPEG noise before the 4x enlargement, and SIFT matches the pages. The LIMC
photo it was checked against is Digital LIMC 8569X101
(`https://iiif.dasch.swiss/080E/39p0GV9AZiB-7HG3RtcJ3N4.jpx/full/max/0/default.png`);
the tool does not read it.

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
the perspective comes out wrong. `tools/euphorbos.py`, `tools/antigone.py` and
`tools/philoctetes.py` use it; their docstrings say what was fitted.
