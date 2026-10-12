# Handoff: Frogs drawing with PhotoCraft (Cleveland 1989.73, side A: Dionysos and two comic actors), 2026-10-12

One session, one drawing. John picked it on 2026-10-09 12:25 (37-Sa, replacing 25-6Ha: "better because it has comic
actors"; record in `.remember/sweep2-2026-10-04/rulings.md`) and on 2026-10-12 12:07 asked again for "the whole of
side a". Other sessions are running (Persians on `claude/redesign-plates-20`, Prometheus Bound on
`claude/redesign-plates-21`): don't touch their branches, worktrees or notes.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Frogs (Aristophanes), key 37-Sa | Cleveland Museum of Art 1989.73, Apulian red-figure bell-krater attributed to the Choregos Painter, c. 390-380 BCE; museum photos (CC0) | `claude/redesign-plates-23`, `.claude/worktrees/redesign-plates-23` | `.remember/batch21/` |

## The source
- Record: https://www.clevelandart.org/art/1989.73; open-access API
  https://openaccess-api.clevelandart.org/api/artworks/1989.73 (`share_license_status` CC0, checked 2026-10-12).
- Images (from the API): main view `https://openaccess-cdn.clevelandart.org/1989.73/1989.73_full.tif` (4393 x 5685,
  75 MB) or `1989.73_print.jpg` (2627 x 3400, 5.1 MB); four other views `1989.73_alt0_print.jpg` to `alt2` (2627 x
  3400, about 4.5 MB each) and `alt3` (1536 x 1703, 1.7 MB). Look at the small `_web` versions first to learn which
  views show side A, then ask John for the ones you need by name and size. Never commit them; save to `src/` here.
- The scene, side A (the whole side, John): a colossal bust of Dionysos in a fillet and laurel wreath, his thyrsos
  with vines over his shoulder, between two comic actors in masks and padded costumes: the left one reaches for a
  bunch of grapes, the right one holds a large skyphos. Preview of the bust only:
  `.remember/sweep6-2026-10-08/page/imgs/37-Sa.jpg`. Whole figures only; propose to John where the side's edges fall
  (the handle palmettes and the bands left out, as on Wasps).
- Nudity: the actors' costumes may show phalluses. Draw as painted (John, 2026-10-09: "no censorship").
- The play: thematic. Dionysos is the hero of Frogs and the god of the theatre; the vase is no scene of the play and is
  some fifteen years after it (405 BC). Say so plainly in the record.

## Ask John first (one message, start it with "Frogs (PhotoCraft)")
1. The download OK: each file by name, source and size, with a crop of side A as the drawing will hold it.
2. Where side A's edges fall, and the style: as Wasps (`tools/wasps.py`): lines along their centres, washes for the
   thinned glaze, white or added colour as stepped washes. Show a small test of Dionysos's face and one actor's mask
   in both themes.

## Credit
- Check the Cleveland record (painter, date, fund, number) and BAPD 1002927 (the API's citation link). Short house form,
  as the Wasps and Clouds entries in `docs/redesign/research/play-image-plan.json`. CC0: the drawing carries no licence
  from the photo. Title as the museum reads it.

## Method
- A photo of a vase: flatten it first (`tools/vase_unroll.py`; John, 2026-10-02: trace from the photo taken off the
  curve). The Cleveland files may carry no focal length: fit the camera and profile to the vase's outline, the bands
  and points matched between views (SIFT), as `tools/wasps.py` did with the Getty's three views. Read LESSONS' "Photos
  of vases" section all through, the Wasps entries above all.
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); geometry may stay in numpy/scipy; say so in the
  docstring. `linework.trace_svg` writes the SVG. Faces, masks and hands first (each finger at 20x; eyes never heavy).
  Lines clean, crisp and even; cracks and wear leave no line (John, 2026-10-02 and 2026-10-10).
- Models: `tools/wasps.py` (Apulian comic vase, Getty photos, PhotoCraft, approved 2026-10-10), `tools/clouds.py` and
  `tools/acharnians.py` (comic vases from photos), `tools/philoctetes.py` (washes). Read
  `docs/redesign/drawings/LESSONS.md` whole: "Photos of vases", "Checks that caught real faults", "John's traces", and
  the 2026-10-10 to 10-12 entries (pin the line weight after pass 1; diff the whole plate after each round; `OPEN`,
  `DROP`; John's short lines meaning "this is paint").
- This vase's traps: the big bust's laurel leaves and the vine's tendrils and grapes (small marks at their painted
  width, through `dots`); the long thyrsos shaft (straight and whole); the masks' features; glare on the black glaze.
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe). Keep
  it under 30 MB so he can mark it on his phone (crop to the scene); else put a copy on his Desktop.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-23.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.

## Records, when he approves
- `tools/frogs.py` and `frogs.svg`; fill the play's entry in `play-image-plan.json` (`json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun `tools/contact_sheet.py`, and a dated
  LESSONS entry under "Photos of vases". Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add Frogs to `settled.json` (wid `frogs`; render `imgs/drawn-frogs.png` at 700 px high on #fbf9f4 with
  rsvg-convert; `imgs/orig-frogs.jpg` a crop of side A from the photo), take `frogs` out of the in-progress chip line
  in `build7.py` if it is there, run `build7.py`, read the artifact first (another session may have published since),
  and publish `index.html` with the two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch21/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Frogs (Cleveland 1989.73, the whole of side A: the bust of Dionysos between two comic actors), on a
> new branch `claude/redesign-plates-23`. Your first message to me asks me to OK the downloads, where the side's edges
> fall, and the style.
