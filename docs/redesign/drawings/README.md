# Drawings: phase 1 test (2026-10-02, revised the same day)

Test drawings for the redesign (DESIGN.md, Drawings). Records with credits
and licences: `../research/play-image-plan.json` (the `playwrights` list, and
the `plays` entry of each play drawn). Open `contact-sheet.html` to see
them on every ground, light and dark.

Before you draw from a printed plate, read `LESSONS.md`: what went wrong on
the earlier plates, how John traces, how blood is drawn. Add to it when you
finish.

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
| `andromache.svg` | Neoptolemos killing Priam on the altar, the dead Astyanax across his knees (Andromache) | Furtwängler and Reichhold, *Griechische Vasenmalerei* I (1904), Taf. 34, Heidelberg scan (public domain) |
| `trachiniae.svg` | Herakles and Deianeira with their infant son Hyllos, between Athena and Oineus (Women of Trachis) | Gerhard, *Auserlesene griechische Vasenbilder* II (1843), Taf. CXVI, Heidelberg scan (public domain) |
| `seven.svg` | Eriphyle walking ahead of the four-horse chariot of Amphiaraos (Seven Against Thebes) | Gerhard, *Auserlesene griechische Vasenbilder* II (1843), Taf. XCI, Heidelberg scan (public domain) |
| `suppliants-aesch.svg` | Amymone running, and her father Danaus (Suppliant Women) | Lenormant and de Witte, *Élite des monuments céramographiques* III (1858), pl. XX, Heidelberg scan (public domain) |
| `alcestis-apollo.svg`, `alcestis-admetus.svg` | Apollo with a palm and a bull; Admetus on horseback (Alcestis): two drawings from one plate, which laid side by side at their places give the whole scene | Lenormant and de Witte, *Élite des monuments céramographiques* II (1857), pl. LIV, Heidelberg scan (public domain); the scan levelled first (`tools/alcestis.py`) |
| `libation-bearers.svg` | Orestes killing Aegisthus, with Clytemnestra and Electra (Libation Bearers): the whole frieze | Gerhard, *Etruskische und kampanische Vasenbilder* (1843), Taf. XXIV, Heidelberg scan (public domain); the scan levelled first; John's corrections on pass 1 in `tools/libation_bearers_marks.json` (`tools/libation_bearers.py`) |
| `trojan-women.svg` | Menelaus dropping his sword at the sight of Helen, with a woman running at the left (Trojan Women) | Gerhard, *Auserlesene griechische Vasenbilder* III (1847), Taf. CLXIX, 4, Heidelberg scan (public domain); made with PhotoCraft (`tools/trojan_women_menelaus.py`); the left woman's profile on John's line |
| `acharnians.svg` | a seated warrior in a crested helmet with his shield, the comic soldier of the type of Lamachus (Acharnians) | Würzburg H 4689, photos by ArchaiOptix (CC BY-SA 4.0); the drawing traces only the painting, so it carries no licence (John, 2026-10-08); flattened off the vase with `tools/vase_unroll.py`; made with PhotoCraft (`tools/acharnians.py`) |
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
weight is 0.11%, finer than the house weight: at the house weight, and at
the plate's own 0.155%, its close lines ran together (John, 2026-10-06).
`trachiniae.svg` too keeps its plate's own weight, 0.104%, traced as drawn
(John, 2026-10-07: the first pass was "too blotchy").

`seven.svg` is black-figure, drawn as silhouettes (John's choice,
2026-10-07): its `lines` path is the black figures themselves, solid, with
the incisions open in them; its `body` path runs 1.5 px past them, so on the
dark theme they stand on a clay rim, as on the vase, and the incisions show
clay. `tools/seven.py` writes it in this format itself, as `trace_svg` would
take that rim away. Eriphyle's feet are drawn on lines in `tools/seven_feet.json`,
her face and hands on John's traces in `tools/seven_traces.json` (plate px).

## Blood

`andromache.svg` carries `tone` paths for the blood: a wash in the line
colour whose opacity follows the plate, with the lines black through it.
How it is drawn, and John's rulings on it, are in `LESSONS.md` (Blood);
`tools/andromache.py` holds the code, and `tools/andromache_traces.json`
John's marks (`fill`, `fill_dark`, `fill_light`, `chest_pleats`,
`missed_lines`, `black_fills`), in plate px.

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
the perspective comes out wrong. `tools/euphorbos.py`, `tools/antigone.py`,
`tools/philoctetes.py` and `tools/acharnians.py` use it; their docstrings say what was fitted.
