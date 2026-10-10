# Handoff: two plate drawings with PhotoCraft, Hecuba and Bacchae, 2026-10-10

One session, two drawings, one after the other: finish Hecuba (approved and recorded) before Bacchae, unless John
says otherwise. John picked both plates on Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD; record in
`.remember/sweep2-2026-10-04/rulings.md`: Hecuba 15-6Ea; Bacchae Furtwängler-Reichhold Taf. 44, "chosen earlier",
sweep 2). Every image step runs in PhotoCraft; John corrects in PhotoCraft or on a pixel grid. This file is all you
need.

| Drawing | Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|---|
| 1 | Hecuba (Euripides), key 15-6Ea | Gerhard, *Trinkschalen und Gefässe des Königlichen Museums zu Berlin* II (1850), Taf. XVI | `claude/redesign-plates-15`, `.claude/worktrees/redesign-plates-15` | `.remember/batch14/` |
| 2 | Bacchae (Euripides) | Furtwängler and Reichhold, *Griechische Vasenmalerei* I (1904), Taf. 44 | same branch | same folder |

Not Iphigenia at Aulis (plates-14) or Phoenician Women (plates-13): other sessions have them.

## 1: Hecuba
- Scan: Heidelberg `gerhard1850bd2`, page https://digi.ub.uni-heidelberg.de/diglit/gerhard1850bd2/0051 (2123 x 3063).
  Get the image's IIIF link from the volume's manifest (`https://digi.ub.uni-heidelberg.de/diglit/iiif/gerhard1850bd2/manifest.json`);
  Heracles' Taf. XXI in the same volume was `https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1850bd2%3AV_Tafel_21.jpg/full/full/0/default.jpg`.
  The preview crop in full-scan px (x0 y0 x1 y1): 907 1163 2049 2436.
- The scene: Neoptolemos, helmeted, with a spear, leads veiled Polyxena to the white tomb of Achilles; a snake and a
  small dog at the tomb, Achilles' winged shade above. Polyxena about 1,010 px, the pair about 1,130. A hoplite's
  shield overlaps Polyxena's mantle at the left, and Neoptolemos' spear crosses in front of her. Propose the crop to
  John in your first message (the pair with the tomb, dog, snake and shade is the obvious reading; the hoplite left out
  along the pair's own outlines).
- Style: black-figure with incised lines (black silhouettes on orange clay, added white). Read LESSONS' "Gerhard,
  black-figure plates": on Seven, Ajax and Lysistrata John chose the silhouette (black solid, incisions open in it, a
  clay rim in the dark theme) after a small test both ways. Show him the same small test first.
- The play: the herald tells of Polyxena's sacrifice at Achilles' tomb. Gerhard's text cites Euripides and reads the
  dog as Hecuba, whom Polymestor foretells will become a dog: read his text pages for the plate and check the vase's
  museum and number now (it is in the Berlin catalogue; Furtwängler 1885 numbers, as Heracles' credit did).

## 2: Bacchae
- Scan: already downloaded on 2026-10-04 with John's OK: `.remember/sweep2-2026-10-04/test-fr44/fr44.jpg` (2835 x 2372;
  from `https://digi.ub.uni-heidelberg.de/iiif/2/furtwaengler1904bd1%3A044.jpg/full/full/0/default.jpg`, Public Domain
  Mark). Copy it to your notes folder's `src/`; no new download.
- The figure: the maenad at the right of side A of the Kleophrades Painter's amphora, Munich 2344, with thyrsos, fawn
  skin and snake. A test drawing of her from that session is in the same folder (`maenad.py`, `maenad.svg`, crop
  1780 790 2540 1870 in plate px): read it for the crop, the band she stands on and her hair, then redo it properly
  with PhotoCraft. Propose the crop to John (the maenad alone, as tested; Dionysos is on the same plate).
- Style: Furtwängler-Reichhold, black pen lines on grey-brown, the ground a dark halftone. Read that LESSONS section;
  models `tools/andromache.py` and `tools/lysistrata.py`.
- The play: a maenad of Dionysos, the chorus and Agave's kind. Credit from the F-R text (I, p. 233 ff.) and the Munich
  museum's record.

## Sources and credits (both)
- Heidelberg, public domain. Your first message asks John to OK the one new download (Hecuba's scan; name and size)
  and shows a crop of what each drawing will hold. Read the licence in the IIIF manifest. Viewer pages sit behind a bot
  check; IIIF image links open in the browser pane.
- Save scans to `.remember/batch14/src/` (never commit them).
- Read the plate's own text for what the editors say the vase is and where it was; find where it is now and check the
  credit against the museum's record. On Trojan Women the publication had the museum wrong: check both.

## Method
- Read `docs/redesign/drawings/LESSONS.md` all of it: the two plate sections above, the PhotoCraft entries,
  "Checks that caught real faults" and "John's traces", and the newest entries (Helen, Ion, the Antigone corrections
  file, 2026-10-10).
- Models: `tools/heracles.py` (same Trinkschalen volume, PhotoCraft, approved 2026-10-09), `tools/seven.py`,
  `tools/ajax.py`, `tools/lysistrata.py` (black-figure silhouettes), `tools/andromache.py` (F-R), `tools/helen.py` and
  `tools/ion.py` (PhotoCraft, approved after John's marks).
- Every image step runs in PhotoCraft (`~/.local/bin/photocraft-cli`: `commands`, `run`, `convert`, `serve`; MCP via
  `photocraft-cli mcp`); geometry may stay in numpy/scipy; say so in the docstring. The SVG is written by
  `linework.trace_svg`.
- John wants clean, crisp, even strokes ("I don't want this rough. Nice and clean and crisp"). Faces and hands first
  (each finger at 20x; eyes never heavy). Check the dark theme for holes in a figure's area: the ground shows through.
- Corrections: a PhotoCraft file he marks, as for Antigone (2026-10-10): the source on your tool's grid, your lines in
  red on a layer at 70%, an empty layer "John corrections (blue = add, green = remove)". Build it with
  `photocraft-cli serve` (doc.open, paste in place, layer.setProps, layer.new.layer, doc.save; relative paths with
  `--automation-read-root`/`--automation-write-root`). Over 30 MB it will not send to his phone: put a copy on his
  Desktop. Read his layer alone (`layer.select` {"layer": id} + `layer.setProps` {"visible": false} on the others, save
  a PNG); keep it beside the tool as `tools/<name>_marks_1.png`; apply ink = (ink less green) plus blue; diff each new
  save he makes against the last.
- Nudity: draw as printed (John, 2026-10-09: "no censorship").

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/README.md` (SVG format) and the Drawings section of `docs/redesign/DESIGN.md` (John's
  file, untracked in the main checkout: never edit it).
- Branch off main in your own worktree (table above). Copy this file in as `docs/redesign/drawings/HANDOFF-plates-15.md`,
  commit first, commit as you go, push. Merging is John's call.
- Other sessions run at the same time (R1 Medea on `claude/redesign-redo-r1`, plates-13, plates-14, perhaps more): don't
  touch their branches, worktrees or notes folders. You all fill the same record files: before each records step,
  merge the latest main into your branch, keep every other entry, and rerun the contact sheet.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in `.remember/batch14/`. Python venv in your scratchpad
  (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are installed. Helper scripts
  (copy, don't edit): `.remember/batch5/scripts/`, `.remember/batch6/scripts/`, `.remember/redo-2026-10-09/r1/show.py`.

## Show John
Start every message with "Hecuba (PhotoCraft)" or "Bacchae (PhotoCraft)". Send with SendUserFile: source crop |
light | dark at 400 and 120 px; the whole drawing at full width in both themes; the full-res red overlay; close-ups of
every face and hand at 4-6x. Look at all of them yourself first, at full size. Ask his verdict with AskUserQuestion.

## Records, when he approves each
- `tools/hecuba.py` and `hecuba.svg`; `tools/bacchae.py` and `bacchae.svg`.
- Fill the play's entry in `docs/redesign/research/play-image-plan.json` (keep its format: `json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it; short house credit form, as the heracles and ion entries), add to
  `drawings.json` and the README table, rerun `tools/contact_sheet.py`, and add a dated LESSONS.md entry under the
  plate family's heading.
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly).
- No outside review unless John asks for one. Then stop and report: branch, commits, what John approved, the credit's
  sources.
