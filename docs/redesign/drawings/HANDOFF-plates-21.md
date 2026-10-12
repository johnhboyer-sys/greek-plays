# Handoff: Prometheus Bound drawing with PhotoCraft (Vatican 16592, Laconian cup), 2026-10-10

One session, one drawing. John picked it on Plate Picks on 2026-10-08 (4-6Va; record in
`.remember/sweep2-2026-10-04/rulings.md`). Other sessions are running (Electra on `claude/redesign-plates-19`, Persians on
`claude/redesign-plates-20`, perhaps Wasps on plates-17 and Bacchae on plates-15): don't touch their branches,
worktrees or notes folders.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Prometheus Bound (Aeschylus), key 4-6Va | Vatican, Museo Gregoriano Etrusco 16592, Laconian black-figure cup by the Arkesilas Painter, c. 560-550 BC; photo by Daderot (CC0) | `claude/redesign-plates-21`, `.claude/worktrees/redesign-plates-21` | `.remember/batch19/` |

## The source
- Already downloaded at John's OK (2026-10-08 10:31): `.remember/prometheus/src/vatican-16592-daderot.jpg`
  (4468 x 3568, gitignored; never commit it). Commons page:
  https://commons.wikimedia.org/wiki/File:Prometheus_and_Atlas,_Laconian_black-figure_kylix,_by_the_Arkesilas_Painter,_560-550_BC,_inv._16592_-_Museo_Gregoriano_Etrusco_-_Vatican_Museums_-_DSC01069.jpg
  Read the licence on that page yourself before you start. Earlier views: `.remember/prometheus/tondo-view.jpg`,
  `eagle-zoom.jpg`. No new download is needed, so no download question.
- The picture: the cup's tondo. Atlas holds up the sky; Prometheus is bound to a column; the eagle between them pecks
  at Prometheus; a column at the right. Black-figure: black silhouettes on the clay with incised lines and added
  colour. Figures about 1,700 px. Both men are nude (no genitals drawn clearly; a round mark at each hip): draw as
  painted (John, 2026-10-09: "no censorship").
- Defects: the photo is taken at a slant (the tondo is an ellipse, not a circle): take the slant out first so the
  tondo is round (fit the ellipse of the tondo's border and map it to a circle; say how in the docstring), then the
  cup's curve if it shows. A pale crack or repair line arcs across Atlas's head and the eagle: erase it whole, draw
  nothing along it, and join only the lines it broke (John, 2026-10-02, "cracks leave no line"); show John the crack's
  path over the photo before you draw across it.
- The play: direct. The play stages Prometheus bound; Hermes threatens him with the eagle at the end; Prometheus
  speaks of Atlas.

## Ask John first (one message, start it with "Prometheus Bound (PhotoCraft)")
1. What the drawing holds: the two men, the eagle and the column(s) inside the tondo, or the whole tondo with its
   border. Whole figures only.
2. The style: black-figure as a silhouette, as Hecuba (merged today, `tools/hecuba.py`) and Ajax: the black solid, the
   incisions as clay lines, any added red as a `tone` wash. Show a small test of Prometheus's head and the eagle in
   both themes.

## Credit
- The Vatican's own record if online (Museo Gregoriano Etrusco, inv. 16592), then the Beazley Archive or the
  literature on Laconian cups (Stibbe, *Lakonische Vasenmaler*; the Arkesilas Painter). Credit the photo to Daderot
  (CC0: no licence carried, but name him as the house form does). Title as the museum reads it.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (the slant and curve correction may stay in numpy/scipy, as `tools/vase_unroll.py`; say so in the
  docstring); `linework.trace_svg` writes the SVG; faces and hands first (each finger at 20x, eyes never heavy); John
  corrects in PhotoCraft or on a pixel grid; read his marks literally.
- Your models: `tools/hecuba.py` (black-figure silhouette, PhotoCraft, approved and merged 2026-10-10),
  `tools/ajax.py` (black-figure, John's hand marks), `tools/vase_unroll.py` and `tools/acharnians.py` / `tools/clouds.py`
  (drawing from a photo: flatten first). Read `docs/redesign/drawings/LESSONS.md` whole: the black-figure section,
  "Photos of vases", "Checks that caught real faults", "John's traces", and the 2026-10-10 entries (pin the line weight
  after pass 1; diff the whole plate after each round; `OPEN`, `DROP`).
- This source's traps: incised lines in a photo are thin and lighter than the black, with glare along them (trace the
  incisions, not the highlights); the eagle's feathers and the bonds on Prometheus are fine incision; the crack; the
  photo's lighting falls off toward the rim.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe (Phoenician Women).
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.
- John may be on Remote Control: send every image with SendUserFile and ask with AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-21.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.
- When John approves, update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Prometheus Bound to `settled.json` (wid `prometheus-bound`; render
  `imgs/drawn-prometheus-bound.png` at 700 px high on #fbf9f4 with rsvg-convert; `imgs/orig-prometheus-bound.jpg`
  from `imgs/4-6Va.jpg`), run `build7.py`, read the artifact first (another session may have published since), and
  publish `index.html` with the two new images to that URL.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch19/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Prometheus Bound (Vatican 16592, the Laconian cup: Prometheus bound, the eagle, and Atlas), on a new
> branch `claude/redesign-plates-21`. Your first message to me asks what the drawing holds and the style.
