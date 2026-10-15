# Handoff: Children of Heracles, drawn with PhotoCraft from Gerhard, Auserlesene Vasenbilder II (1843), Taf. XCVII, fig. 1, 2026-10-15

One session, one drawing. John, 2026-10-15: "let's turn to getting the last remaining plates done." His pick
(2026-10-13): Gerhard AV II Taf. XCVII, fig. 1, the top panel: Heracles brings the Erymanthian boar to Eurystheus, who
hides in a storage jar; a nymph and Iolaos at the left, Athena and Hermes at the right. Iolaos and Eurystheus are both
characters of the play. Black-figure: black figures with incised lines on orange clay, a colour chromolithograph.

| Subject | Vase | Branch / worktree | Notes folder |
|---|---|---|---|
| Heracles, the boar and Eurystheus in the jar, with Iolaos | Attic black-figure amphora from Vulci (Candelori collection; Gerhard: "now in Munich"; find the number) | `claude/redesign-plates-39`, `.claude/worktrees/redesign-plates-39` | `.remember/batch42/` |

## Step 1: the source (before anything else)
- Page: https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0223 (Public Domain Mark). IIIF:
  https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_097.jpg/info.json (1963 x 2767; the main
  figures about 950-1000 px tall). Heidelberg IIIF works with curl. Search report and preview:
  `.remember/batch35/heraclidae-search.md`, `.remember/batch35/previews/1-gerhard-AV-II-XCVII-1.jpg`.
- In your first message: confirm the crop with John (the whole fig. 1 panel, border bands and the small vase outlines
  below left out, as on the other plates) and get his OK for the IIIF download by name and size.

## Credit
- The plate's own text (if a plate), the museum's record, and the standard catalogue. Short house form, as the Knights
  and Assemblywomen entries in `play-image-plan.json`. A drawing carries no licence from a CC BY-SA photo (John,
  2026-10-08).

## Method
- A Gerhard black-figure plate: LESSONS' "Gerhard, black-figure plates" section, with `tools/hecuba.py` (Trinkschalen II Taf. XVI) and `tools/seven.py` (Seven Against Thebes, AV II Taf. XCI) as models. Traps: the boar's bristles, the jar's rim and Eurystheus' raised arms, the incised lines inside the black, added white and red, and the shields and helmets.
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
  `docs/redesign/drawings/HANDOFF-plates-39.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Confirm with John before each download (name and size), previews included.
- Before the records step, merge the latest main (the other sessions fill the same record files: keep every other
  entry, rerun the contact sheet).

## Records, when he approves
- `tools/heraclidae.py` and `heraclidae.svg`; fill the play's entry (`work_id` `heraclidae`) in `play-image-plan.json`
  (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry. Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid `heraclidae`; render `imgs/drawn-heraclidae.png` at 700 px high on #fbf9f4 with
  rsvg-convert; `imgs/orig-heraclidae.jpg` a crop of the source you traced), run `build7.py`, read the artifact first (the
  other sessions publish to it too), diff the live page against your build card by card, and publish `index.html`
  with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch42/HANDOFF.md` and do it: draw the Children of Heracles plate with
> PhotoCraft on a new branch `claude/redesign-plates-39`. Start by confirming the crop with me and asking for the download.
