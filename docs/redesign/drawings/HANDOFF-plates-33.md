# Handoff: Knights, a line drawing with PhotoCraft from the Chiron vase plate (Élite II pl. XCIV), 2026-10-13

One session, one drawing. John picked it on 2026-10-13 12:13 ("use the Chiron vase for Knights"), and at 12:14 said
what it holds: "the three actors and the stage and steps. leave out the youth", "and no nymphs". Knights has no drawing
yet; its entry in `play-image-plan.json` is still the placeholder. Other sessions are running (the Euripides home
Iphigenia on `claude/redesign-plates-31`; a Suppliant Women source search in `.remember/batch33/`): don't touch their
branches, worktrees or notes.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Knights (Aristophanes) | C. Lenormant and J. de Witte, *Élite des monuments céramographiques* II (Paris, 1857), pl. XCIV (lith. Rey); Apulian red-figure bell-krater, British Museum F 151 | `claude/redesign-plates-33`, `.claude/worktrees/redesign-plates-33` | `.remember/batch34/` |

## The source
- Scan: Internet Archive `gri_33125009347440` (Getty Research Institute copy), leaf n756:
  https://archive.org/details/gri_33125009347440/page/n756/mode/1up. Printed sideways; IIIF with rotation 90 gives
  3000 x 2245. That file is already on disk (John OK'd it): `src/chiron-elite-II-XCIV.jpg`. Tallest figures about
  800 px.
- Heidelberg has *Élite* II (`lenormant1857bd2`; Ion and Iphigenia at Aulis were traced from it). Look for pl. XCIV
  there and compare its size and sharpness with the archive.org copy; if it is better, ask John to OK the download by
  name and size. Don't wait on this if it isn't.
- The plate: red figures on black, coloured. Comic actors in masks and padded costume on a stage of planks with a
  roofed structure at the left and steps up to it: one slave on the steps pulls an old man (named ΧΙΡΩΝ, Chiron) up by
  the head, the old man leans on a stick, a second slave pushes him from behind; a patterned bundle lies on the stage.
  Two Nymphs (ΝΥΜΦΑΙ) above at the right and a youth without a mask at the right.

## What the drawing holds (John, 12:14)
- The three actors, the stage, and the steps. Left out: the youth and the two Nymphs. Show John your reading of the
  edges in your first pass: whether the roofed structure at the left, the patterned bundle on the stage, the bundle's
  stick, and the painted names stay. Ask with AskUserQuestion if you can't tell.
- Nudity and the costumes' phalluses: draw as painted (John, 2026-10-09: "it's aristophanes. no censorship").
- The play: thematic only: an old master and two slaves, as at the opening of Knights (Demos and his two slaves). The
  vase names no play. Readings differ (Lenormant and de Witte: a parody of Apollo's arrival at Delphi with a blind
  Chiron; Heydemann, JdI 1, 1886, and Bieber: a sick Chiron's journey with his slaves, one named Xanthias). Say so
  plainly in the record; don't claim a link the sources don't make.

## Credit
- *Élite* II's text for pl. XCIV, the British Museum's record (painter, date), and Trendall's *Phlyax Vases* if it can
  be read. Short house form, as the Wealth (*Élite* III pl. LVIII) and Ion entries in
  `docs/redesign/research/play-image-plan.json`.

## Method
- An *Élite* coloured lithograph, red figures on black: read the Lenormant and de Witte section of
  `docs/redesign/drawings/LESSONS.md` and use `tools/wealth.py`, `tools/ion.py`, and `tools/iphigenia_aulis.py` as
  models. Read LESSONS whole, with the 2026-10-10 to 10-13 entries (pin the line weight after pass 1; diff the whole
  plate after each round; `OPEN`, `DROP`; John's short lines meaning "this is paint").
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); rotation and levelling may stay in numpy/scipy; say
  so in the docstring. `linework.trace_svg` writes the SVG. Masks, faces, and hands first (each finger at 20x; eyes
  never heavy). Lines clean, crisp, and even; foxing and paper grain leave no line.
- Traps: the masks' features (grotesque, but keep them crisp), the stick (straight and whole), the planks and the
  steps' rungs (straight, evenly spaced), the patterned bundle, the black ground between the figures (it gives the
  outline: the edge between figure and black is the line).
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe). Keep
  it under 30 MB so he can mark it on his phone.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-33.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- `tools/knights.py` and `knights.svg`; fill the play's entry in `play-image-plan.json` (`json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun `tools/contact_sheet.py`, and a dated
  LESSONS entry under Lenormant and de Witte. Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid `knights`; render `imgs/drawn-knights.png` at 700 px high on #fbf9f4 with
  rsvg-convert; `imgs/orig-knights.jpg` a crop of the plate), take it out of the in-progress chip line in `build7.py`
  if there, run `build7.py`, read the artifact first (another session may have published since), and publish
  `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch34/HANDOFF.md` and do it: one line drawing with PhotoCraft
> for Knights from the Chiron vase (Élite II pl. XCIV): the three actors, the stage, and the steps, without the youth
> or the Nymphs, on a new branch `claude/redesign-plates-33`.
