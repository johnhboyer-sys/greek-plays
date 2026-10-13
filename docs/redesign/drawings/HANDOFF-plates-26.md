# Handoff: Women at the Thesmophoria, a line drawing with PhotoCraft from a Getty photo, 2026-10-12

One session, one drawing. John picked it on Plate Picks on 2026-10-09 15:04 (36-8Ma, Getty 96.AE.113; record in
`.remember/sweep2-2026-10-04/rulings.md`) and on 2026-10-12 16:12 asked for the next play from the queue. It is the
sister vase of Wasps (Getty 96.AE.112, drawn and approved 2026-10-10): same collection, same kind of photo, same method.
Other sessions are running (Frogs on `claude/redesign-plates-23`, Euphorbos on `claude/redesign-plates-25`, Persians on
`claude/redesign-plates-20`, Medea in its own session): don't touch their branches, worktrees or notes.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Women at the Thesmophoria (Aristophanes), key 36-8Ma | J. Paul Getty Museum 96.AE.113, Apulian red-figure bell-krater attributed to the Cotugno Painter, 370-360 BC; museum photos (CC0, Getty Open Content) | `claude/redesign-plates-26`, `.claude/worktrees/redesign-plates-26` | `.remember/batch24/` |

## The source
- Object page: https://www.getty.edu/art/collection/object/10408F (renders with JavaScript: read it in the browser
  pane). Find the object's IIIF manifest (`https://media.getty.edu/iiif/manifest/...`; the Wasps tool's docstring
  shows the form) and from it the full images: the front view and any side views of side A (Wasps fitted three Getty
  cameras). Preview: `.remember/sweep6-2026-10-08/page/imgs/36-8Ma.jpg`. Your first message asks John to OK each
  download by name and size.
- The scene: three masked comic actors on a stage plank: at the left an old man in a padded costume leaning on a stick;
  in the middle an actor in a woman's dress kneeling, a veil over his head; at the right a king in a crown with a
  sceptre, pointing. Propose to John what the drawing holds (the whole stage scene, as Wasps; the bands, the handle
  palmettes and the black ground left out).
- Nudity: the actors may wear costume phalluses. Draw as painted (John, 2026-10-09: "it's aristophanes. no censorship").
- The play: thematic only: a man in woman's dress, as the Kinsman is in Women at the Thesmophoria. The vase names no
  play and is some forty years later than the play (411 BC). Say so plainly in the record. The Getty's own reading of the
  scene goes in `shows`.

## Credit
- The Getty's own record (painter, date, provenance, inventory, credit line) and the literature it cites. Short house
  form, as the Wasps entry in `docs/redesign/research/play-image-plan.json`. CC0: the drawing carries no licence from
  the photo.

## Method
- A photo of a vase: flatten it first (`tools/vase_unroll.py`; John, 2026-10-02: trace from the photo taken off the
  curve). Your model is `tools/wasps.py`: the Getty's cameras carry no focal length; fit them to the meander band, the
  outline and points matched between views (SIFT). Read LESSONS' "Photos of vases" section all through, the Wasps
  entries above all.
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); geometry may stay in numpy/scipy; say so in the
  docstring. `linework.trace_svg` writes the SVG. Faces, masks and hands first (each finger at 20x; eyes never heavy).
  Lines clean, crisp and even; cracks and wear leave no line (John, 2026-10-02 and 2026-10-10).
- Other models: `tools/clouds.py` and `tools/acharnians.py` (comic vases from photos), the Frogs tool if merged by then
  (`tools/frogs.py`, Apulian comic vase, Cleveland photos). Read `docs/redesign/drawings/LESSONS.md` whole, with the
  2026-10-10 to 10-12 entries (pin the line weight after pass 1; diff the whole plate after each round; `OPEN`,
  `DROP`; John's short lines meaning "this is paint").
- This vase's traps: the veil over the kneeling actor's head and hands; the masks' features; the patterned dress; the
  stick and sceptre (straight and whole); white or added colour (stepped washes, as Wasps' white hair); glare on the
  black glaze.
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe). Keep
  it under 30 MB so he can mark it on his phone (crop to the scene); else put a copy on his Desktop.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-26.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.

## Records, when he approves
- `tools/thesmophoriazusae.py` and `thesmophoriazusae.svg`; fill the play's entry in `play-image-plan.json`
  (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry under "Photos of vases". Rerun the tool: the SVG comes out byte
  for byte the same. `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless
  John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid `thesmophoriazusae`; render `imgs/drawn-thesmophoriazusae.png` at 700 px high on
  #fbf9f4 with rsvg-convert; `imgs/orig-thesmophoriazusae.jpg` from `imgs/36-8Ma.jpg`), take it out of the
  in-progress chip line in `build7.py`, run `build7.py`, read the artifact first (another session may have published
  since), and publish `index.html` with the two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch24/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Women at the Thesmophoria (Getty 96.AE.113: three comic actors, one in a woman's dress), on a new
> branch `claude/redesign-plates-26`. Your first message to me asks me to OK the downloads and what the drawing holds.
