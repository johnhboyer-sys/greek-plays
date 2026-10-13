# Handoff: Oedipus Tyrannus, a line drawing with PhotoCraft from the Sbani vase plate, 2026-10-13

One session, one drawing. John, 2026-10-13 09:23: "use the Sbani vase"; 09:24: "whole lower row, but we want a higher
res scan". It replaces `oedipus-tyrannus.svg` (`tools/oedipus_syracuse.py`, from the Syracuse krater, which John
rejected on 2026-10-09 as "too damaged" and "too crude"). Other sessions are running (Assemblywomen on
`claude/redesign-plates-29`, Suppliant Women on `claude/redesign-plates-30`, the Euripides home Iphigenia on
`claude/redesign-plates-31`): don't touch their branches, worktrees or notes.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Oedipus Tyrannus (Sophocles) | the Sbani vase (Naples, once Sbani collection), as drawn in O. Benndorf, *Wiener Vorlegeblätter für archaeologische Übungen*, Serie 1889 (Vienna 1890), Taf. IX, fig. 6, after Raoul-Rochette, *Monuments inédits d'antiquité figurée*, pl. 78 | `claude/redesign-plates-32`, `.claude/worktrees/redesign-plates-32` | `.remember/batch32/` |

## Step 1: a higher-resolution scan (before anything else)
- What we have: Heidelberg `benndorf1890bd2`, Taf. IX (https://digi.ub.uni-heidelberg.de/diglit/benndorf1890bd2/0020;
  IIIF `https://digi.ub.uni-heidelberg.de/iiif/2/benndorf1890bd2%3ATafel_09.jpg/info.json`, 3409 x 2796, the largest
  size served). Fig. 6 is the top right group; at full size it is about 945 x 670 px and each figure about 300 px tall.
  A copy of that crop is in `src/benndorf-IX-6-sbani.jpg` (region 2420,70,945,670 of the full plate).
- Look for a larger copy of this drawing:
  - Raoul-Rochette, *Monuments inédits d'antiquité figurée* (Paris 1833), pl. 78, the plate Benndorf copied. It may
    print the scene larger. Try Heidelberg, Gallica, archive.org, Google Books, BSB/MDZ, and HathiTrust (don't get round a
    bot check; report it).
  - Other scans of Wiener Vorlegeblätter 1889, and any other print of the vase.
- Open each one and see it. Report to John in your first message: each copy's link, its pixel size, the lower row's
  size in it, and a crop of Oedipus' face and hands beside the same crop from Benndorf (crops from pages you viewed,
  sent with SendUserFile). Ask him to pick one and to OK each download by name and size. If nothing is larger, say so.
- Also find, from the literature (Raoul-Rochette's text, Benndorf's text, LIMC "Oidipous", Trendall), where the vase
  is now and whether its authenticity has been questioned. Say what you find plainly, with sources; don't guess.

## What the drawing holds (John, 09:24)
- The whole lower row: the woman with the mirror at the left (with the basin on its stand behind her), Oedipus enthroned
  with his sceptre (the chair and footstool, the wall pattern behind him), the old man in the rich robe with his staff,
  and the child with the branch. Left out: the upper row of goddesses, the beaded line between the rows, and the plant
  between the woman and Oedipus unless John wants it. Ask John if anything at the edges is unclear.
- Who the figures are: report the identifications in Raoul-Rochette's and Benndorf's texts (Teiresias led by a boy,
  Jocasta?). Don't assert names the sources don't give.
- Nudity: draw as painted.

## Credit
- Benndorf's and Raoul-Rochette's plates, and the vase's present place if found. Short house form, as the Bacchae and
  Eumenides entries in `docs/redesign/research/play-image-plan.json`.

## Method
- An engraved or lithographed outline drawing with interior lines, no black ground: read the "Contour plates with no
  black ground" (Hoernes, Archäologische Zeitung 1877) section of `docs/redesign/drawings/LESSONS.md`, and use
  `tools/eumenides.py` (Bötticher plate) and `tools/iphigenia_aulis.py` (Élite) as models. Read LESSONS whole, with
  the 2026-10-10 to 10-13 entries (pin the line weight after pass 1; diff the whole plate after each round; `OPEN`,
  `DROP`; John's short lines meaning "this is paint").
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); rotation and levelling may stay in numpy/scipy; say
  so in the docstring. `linework.trace_svg` writes the SVG. Faces and hands first (each finger at 20x; eyes never
  heavy). Lines clean, crisp and even; paper grain and foxing leave no line.
- Traps: the small scale (fine pleats must not merge; trace at an upscale), the sceptre and staff (straight and
  whole), the old man's patterned robe, the chair's legs and the footstool, the child's branch.
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe).
  Keep it under 30 MB so he can mark it on his phone.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-32.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- Replace `oedipus-tyrannus.svg` in place (same name); write `tools/oedipus_tyrannus.py` and leave
  `tools/oedipus_syracuse.py` as the record of the old one. Update the play's entry in `play-image-plan.json`
  (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry under the contour-plate section. Rerun the tool: the SVG comes out
  byte for byte the same. `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless
  John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  update the `oedipus-tyrannus` entry in `settled.json` (source, link, alt), re-render `imgs/drawn-oedipus-tyrannus.png`
  (700 px high on #fbf9f4 with rsvg-convert), replace `imgs/orig-oedipus-tyrannus.jpg` with a crop of the plate,
  clear `oedipus-tyrannus` in `redo.json`, and change the Oedipus Tyrannus "Open" status in `build7.py` (the
  `oedipus-and-sophocles` article) to settled. Run `build7.py`, read the artifact first (another session may have
  published since), and publish `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch32/HANDOFF.md` and do it: one line drawing with PhotoCraft
> for Oedipus Tyrannus from the Sbani vase (Wiener Vorlegeblätter 1889 Taf. IX.6, after Raoul-Rochette pl. 78), the
> whole lower row, on a new branch `claude/redesign-plates-32`. Start by looking for a higher-resolution scan.
