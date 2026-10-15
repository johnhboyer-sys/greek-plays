# Handoff: Agamemnon, drawn with PhotoCraft from photos of Boston MFA 63.1246, 2026-10-15

One session, one drawing. John, 2026-10-15: "let's turn to getting the last remaining plates done." His pick (Plate
Picks): Boston MFA 63.1246, the Dokimasia Painter's calyx-krater, side A: Aegisthus stabs Agamemnon, caught in the
net-robe; Clytemnestra behind with the axe. Side B (Orestes kills Aegisthus) is not used. No old print exists: the
vase first appears in 1958, so this is a photo drawing.

| Subject | Vase | Branch / worktree | Notes folder |
|---|---|---|---|
| The murder of Agamemnon (Agamemnon 1343 ff., told from inside) | Attic red-figure calyx-krater, Dokimasia Painter, c. 460 BC, Boston, Museum of Fine Arts 63.1246 | `claude/redesign-plates-37`, `.claude/worktrees/redesign-plates-37` | `.remember/batch40/` |

## Step 1: find the best photos (before anything else)
- The museum page: https://collections.mfa.org/objects/153661 (MFA blocks curl; use the browser pane, and its own
  image download if it has one). Also Commons, the BAPD, Arachne, and published photos (Vermeule's 1966 article and
  later). Tracing from an in-copyright photo of an ancient vase is allowed (John, 2026-10-02); ask about each licence.
- Open each and see it. Report in your first message: each view, its size, its licence, and a small crop (SendUserFile).
  Propose the whole of side A between the border bands, and ask John about the edges. Wait for his pick and his OK on
  each download.
- The vase is curved: flatten first (`tools/vase_unroll.py`; John, 2026-10-02; LESSONS' "Photos of vases").

## Credit
- The plate's own text (if a plate), the museum's record, and the standard catalogue. Short house form, as the Knights
  and Assemblywomen entries in `play-image-plan.json`. A drawing carries no licence from a CC BY-SA photo (John,
  2026-10-08).

## Method
- A photo: flatten first; models `tools/wasps.py`, `tools/frogs.py`, `tools/thesmophoriazusae.py` and `tools/mika.py` (bell-kraters from photos), and LESSONS' "Photos of vases" section all through. Traps: the net-robe's mesh (draw it as painted, not as texture), the sword through it, the axe, the faces, glare on the black glaze, and the vase's mends.
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
  `docs/redesign/drawings/HANDOFF-plates-37.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Confirm with John before each download (name and size), previews included.
- Before the records step, merge the latest main (the other sessions fill the same record files: keep every other
  entry, rerun the contact sheet).

## Records, when he approves
- `tools/agamemnon.py` and `agamemnon.svg`; fill the play's entry (`work_id` `agamemnon`) in `play-image-plan.json`
  (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry. Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid `agamemnon`; render `imgs/drawn-agamemnon.png` at 700 px high on #fbf9f4 with
  rsvg-convert; `imgs/orig-agamemnon.jpg` a crop of the source you traced), run `build7.py`, read the artifact first (the
  other sessions publish to it too), diff the live page against your build card by card, and publish `index.html`
  with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch40/HANDOFF.md` and do it: draw the Agamemnon plate with
> PhotoCraft on a new branch `claude/redesign-plates-37`. Start by finding the best photos of the vase, and report them to me.
