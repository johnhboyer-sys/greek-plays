# Handoff: Electra (Euripides), drawn with PhotoCraft from Monumenti inediti VIII (1864-68), tav. XV, 2026-10-15

One session, one drawing. John, 2026-10-15: "let's turn to getting the last remaining plates done." His pick
(2026-10-13, Plate Picks 10-7Bb): Monumenti inediti dell'Instituto VIII, tav. XV, the right panel of a pelike drawn
flat: Orestes, inscribed OPESTES, drives his sword into the seated, bearded Aegisthus; Chrysothemis at the left with a
raised hand. The only scan we have is Arachne's, 1000 x 784: https://arachne.dainst.org/data/image/2467050 (preview
`.remember/sweep6-2026-10-08/page/imgs/10-7Bb.jpg`). John rejected a plate that was too small to look good (Panofka,
2026-10-13: "We want something that looks GOOD").

| Subject | Vase | Branch / worktree | Notes folder |
|---|---|---|---|
| Orestes kills Aegisthus (Eur. El. 774-858, told by a messenger) | the pelike of Mon. Ined. VIII tav. XV (find its museum and number) | `claude/redesign-plates-40`, `.claude/worktrees/redesign-plates-40` | `.remember/batch43/` |

## Step 1: find a bigger scan of this plate, and other printed drawings of the vase (before anything else)
- Identify the vase. If it is the Vienna pelike (Kunsthistorisches Museum), Reichhold drew it in Furtwängler-Reichhold
  Taf. 72 (Heidelberg furtwaengler1904bd1 or bd2): check whether that plate shows this side, and how the site used it
  before (`docs/redesign/research/play-image-plan.json`, `.remember/batch36/electra-eur-search.md`). Then find the best
  scan of Mon. Ined. VIII tav. XV (Heidelberg, archive.org, Gallica, Google Books, HathiTrust, Arachne's full size) and
  other old drawings of the vase, German first (Wiener Vorlegeblätter; Archäologische Zeitung; Overbeck). Pre-1931
  is public domain.
- Open each and see it. Never report that a plate shows the vase unless you saw it. Report in your first message:
  each plate's citation, link, scan size (and the figures' height in px), and a small crop (SendUserFile). Ask John
  to pick and to OK each download by name and size. If nothing better than Arachne's 1000 px exists, say so and ask.
- Libation Bearers' plate (Gerhard, Etruskische und kampanische Vasenbilder, Taf. XXIV) shows the same killing on a
  different vase; this one must look different on the page, so say if the plates you find are the same vase.

## Credit
- The plate's own text (if a plate), the museum's record, and the standard catalogue. Short house form, as the Knights
  and Assemblywomen entries in `play-image-plan.json`. A drawing carries no licence from a CC BY-SA photo (John,
  2026-10-08).

## Method
- A plate: models in the plate families in LESSONS (Monumenti inediti and Furtwängler-Reichhold sections; `tools/iphigenia_tauris.py`, `tools/orestes.py`, `tools/medea.py`). Traps: the sword where it enters, the inscription (letters drawn as printed), the throne's legs, faces and hands, and the panel's curve if the plate was drawn from the round.
- Read LESSONS whole, with the 2026-10-10 to 10-15 entries (pin the line weight after pass 1; diff the whole plate
  after each round; `OPEN`, `DROP`; John's short lines meaning "this is paint"; pupils as dots, both or neither).
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); geometry may stay in numpy/scipy; say so in the
  docstring. `linework.trace_svg` writes the SVG. Faces and hands first (each finger at 20x; eyes never heavy).
  Lines clean, crisp and even; cracks and wear leave no line, and nothing is drawn along a crack.
- Nudity drawn as painted (John: "no censorship").
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe). Keep
  it under 30 MB so he can mark it on his phone. He paints on any layer and re-saves under new layer ids: list the ids
  and read blue/green by colour from every layer each round; ask whether blue replaces or adds.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed. Run Python that reads downloaded files with `-I`.
- Three other drawing sessions run at the same time (Agamemnon, Peace, Children of Heracles, Electra of Euripides,
  branches `claude/redesign-plates-37` to `-40`): touch only your own branch, worktree and notes folder. Runs are
  slow when memory is short; never wait with `pgrep` loops (they match themselves).

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-40.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Confirm with John before each download (name and size), previews included.
- Before the records step, merge the latest main (the other sessions fill the same record files: keep every other
  entry, rerun the contact sheet).

## Records, when he approves
- `tools/electra_eur.py` and `electra-eur.svg`; fill the play's entry (`work_id` `electra-eur`) in `play-image-plan.json`
  (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry. Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid `electra-eur`; render `imgs/drawn-electra-eur.png` at 700 px high on #fbf9f4 with
  rsvg-convert; `imgs/orig-electra-eur.jpg` a crop of the source you traced), run `build7.py`, read the artifact first (the
  other sessions publish to it too), diff the live page against your build card by card, and publish `index.html`
  with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch43/HANDOFF.md` and do it: draw the Electra (Euripides) plate with
> PhotoCraft on a new branch `claude/redesign-plates-40`. Start by finding a bigger scan of the Monumenti plate, and other old drawings of the vase, and report them to me.
