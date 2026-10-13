# Handoff: redo eight early drawings with PhotoCraft (four sessions, two drawings each), 2026-10-09

John, 2026-10-09: "We gonna have to redo some of the settled and drawn. The photocraft method is so good, that these
earlier ones are looking not good: Antigone; ... Philoctetes; Oedipus at Colonus is okay, but i wonder if a second
pass in photocraft could do better; Medea looks like ass." Then: "redo the home page ones too", and "we have to change
the sophocles homepage image. that spear is far too long". (Oedipus Tyrannus is not here: John wants a new source for
it; a separate search.) Record: `.remember/sweep2-2026-10-04/rulings.md`. The side-by-side of each source and its
current drawing: Plate Picks, https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD ("Home page" and "Settled and drawn").

Each session redraws its two drawings, one after the other, with PhotoCraft, and replaces the old SVG under the SAME
file name (the site and drawings.json already point at it). This file is all you need; your prompt names your
session (R1-R4).

| Session | Drawings (old tool, SVG) | Source family | Branch / worktree | Notes folder |
|---|---|---|---|---|
| R1 | Antigone (`tools/antigone.py`, `antigone.svg`); Medea (`tools/medea.py`, `medea.svg`) | photos of vases | `claude/redesign-redo-r1` | `.remember/redo-2026-10-09/r1/` |
| R2 | Philoctetes (`tools/philoctetes.py`, `philoctetes.svg`); Oedipus at Colonus (`tools/oedipus_colonus.py`, `oedipus-coloneus.svg`) | photos; a book plate | `claude/redesign-redo-r2` | `.remember/redo-2026-10-09/r2/` |
| R3 | Aeschylus, the Pythia (`tools/pythia.py`, `aeschylus-pythia.svg`); Euripides, Iphigenia (`tools/iphigenia.py`, `euripides-iphigenia.svg`) | old plates | `claude/redesign-redo-r3` | `.remember/redo-2026-10-09/r3/` |
| R4 | Aristophanes, Mika (`tools/mika.py`, `aristophanes-mika.svg`). The Sophocles home figure is OPEN (see below): not part of R4 until John picks one | photo of a vase | `claude/redesign-redo-r4` | `.remember/redo-2026-10-09/r4/` |

Worktree for each: `.claude/worktrees/redesign-redo-r<N>`, branched off main. Copy this file in as
`docs/redesign/drawings/HANDOFF-redo.md` (first session to commit it; others skip if present on main) and commit.
Commit as you go and push. Merging is John's call.

## What carries over from the old drawings: John's decisions, not the old lines

Each drawing's entry in `docs/redesign/research/play-image-plan.json` (the `plays` list, or `playwrights` for the
home-page four) has `crop`, `status` and `credit` fields: the crop says what John decided the drawing holds and why.
Keep those decisions unless he changes them. His old traces and marks (`.remember/colonus/john_*`,
`docs/redesign/drawings/tools/philoctetes_traces.json`, and for Antigone the HAND_TRACE, FACE_TRACES and ARM_LINES
inside `tools/antigone.py`, in that tool's frame px; LESSONS, "John's traces") record where he put lines on faces, hands and feet: check the new lines against them there and show him any
place they disagree. The old tool shows how the source was cropped, levelled or flattened; reuse that geometry where
it was approved (the vase-unrolling work in `tools/vase_unroll.py` and the photo cameras/focal lengths), and redo the
line extraction in PhotoCraft.

## Per drawing

- **Antigone (R1)**: Berlin F 3240 (Darius Painter), four ArchaiOptix photos (CC BY-SA 4.0; URLs in the entry's
  source_file). Antigone alone, bound, as the crop says; erase the two mended breaks whole (LESSONS, cracks). John
  traced her himself once; his arm and fingers are the standard to meet.
- **Medea (R1)**: Cleveland 1991.1 (CC0), `1991.1_alt3_full.tif` per the entry. Medea in the serpent chariot, cut
  from the sun disk along its border, both netted sleeves kept. John: "looks like ass": the old one was a phase 1
  test. Dense pattern (serpents' scales, net sleeves): smooth, even lines, no grain.
- **Philoctetes (R2)**: Met 56.171.58, the Met photos `DP165159.jpg`, `DP165160.jpg` and Marie-Lan Nguyen's photo
  (all already in `.remember/philoctetes/`). Philoctetes with the rock and the bow case, as the crop says; John's
  head, feet and hands traces are in `philoctetes_traces.json`.
- **Oedipus at Colonus (R2)**: Green 2003 page scans, HathiTrust TIFFs already in `.remember/colonus/`
  (seq 6, 28, 31; John downloaded them). Oedipus between Ismene and Antigone with the altar. John: "okay, but i
  wonder if a second pass in photocraft could do better": show him the old and new side by side, and say plainly if
  the new is not better.
- **Aeschylus, the Pythia (R3)**: Bötticher (1859), Heidelberg `bwpr1859/4/010a.jpg`. The Pythia only, cut as the
  crop says (Apollo's foot erased, her stripe continued 45 px). Engraved plate, so the plate family is close to the
  Élite/Gerhard lithographs: read LESSONS' plate sections.
- **Euripides, Iphigenia (R3)**: Archäologische Zeitung 7 (1849) Taf. XII (Jaene's lithograph), Internet Archive
  `archaologischez07deut` page n156. Iphigenia with the tablet, key, chain and knob, as the crop says. A better scan
  of AZ 7 may exist (HathiTrust, Google Books, another IA copy): look, and ask John before downloading a second one.
- **Sophocles home figure: OPEN.** John, 2026-10-09: "we have to change the sophocles homepage image. that spear is
  far too long", then "let's not do Euphorbos necessarily". The orchestrator is gathering candidates (Euphorbos with
  a shorter spear among them); R4 does not touch `sophocles-euphorbos.svg` until John has picked.
- **Aristophanes, Mika (R4)**: Würzburg H 5697 (Schiller Painter), ArchaiOptix photo 04 (CC BY-SA 4.0). The old woman
  with the bowl only; the knife blade at her bowl cut away. John, 2026-10-09: no censorship for Aristophanes.

## Sources and downloads
Sources are never committed; keep them in your notes folder's `src/` (gitignored, under `.remember/`). Files already
on disk (Philoctetes, Colonus, and any in `.remember/batch*/src/`) need no new download. For the rest, your first
message to John asks him to OK the downloads by name and size, before fetching. Licences: Heidelberg and the
Internet Archive plates are public domain; Cleveland is CC0; the ArchaiOptix photos are CC BY-SA 4.0 (John,
2026-10-08: no licence is carried from CC BY-SA photos to the drawing; ask him if in doubt).

## Method
- Read `docs/redesign/drawings/LESSONS.md` all of it, and the sections for your source families; `README.md` (SVG
  format: 1000 units tall, `body` then `lines`); the Drawings section of `docs/redesign/DESIGN.md` (John's file,
  untracked in the main checkout: never edit it).
- Models from the PhotoCraft sessions, all approved: `tools/trojan_women_menelaus.py` (plate), `tools/heracles.py`
  (plate; on main once plates-11 merges, else on `origin/claude/redesign-plates-11`), `tools/acharnians.py` and
  `tools/clouds.py` (photos of vases, flattened, PhotoCraft).
- Every image step runs in PhotoCraft (`~/.local/bin/photocraft-cli`; `commands`, `run`, `convert`; MCP via
  `photocraft-cli mcp`); geometry (flattening, levelling) may stay in numpy/scipy; say so in the docstring. The SVG is
  written by `linework.trace_svg`.
- Lines smooth, even, unbroken; clay stops at the outlines (`held = ~fig`); trace the painted lines, not colour
  edges; faces and hands first (each finger at 20x; eyes never heavy). John does not want to trace: get the lines
  right and send him things to judge.
- Corrections on the pixel grid (`.remember/batch6/scripts/pxgrid.py`; red = ink, green = ground) or in PhotoCraft
  over a full-res export (blue = add, green = remove). Read his marks literally; ask in one line if unclear.
- Helper scripts (copy, don't edit): `.remember/batch5/scripts/`, `.remember/batch6/scripts/`.
- Nudity: draw as painted (John, 2026-10-09: "no censorship").

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Other sessions run at the same time (R1-R4, Ion on plates-11, perhaps others): don't touch their branches,
  worktrees or notes folders. You all fill the same record files: before the records step, merge the latest main
  into your branch, keep every other entry, and rerun the contact sheet.
- Keep `notes.md` and `timing.txt` (start and end of each drawing and pass) in your notes folder. Python venv in your
  scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are installed.

## Show John
Start every message with the drawing's name and "(PhotoCraft redo)". Send with SendUserFile: the OLD drawing beside
the NEW one and the source crop, light and dark, at 400 and 120 px; the whole new drawing at full width in both
themes; the full-res red overlay; close-ups of every face and hand at 4-6x. Look at all of them yourself first. Ask
his verdict with AskUserQuestion. Finish one drawing (approved and recorded) before the second, unless he says
otherwise.

## Records, when he approves each
- The new tool replaces the old one under the same name (keep the old in git history; say so in the commit); the new
  SVG replaces the old under the same name.
- Update the entry in `play-image-plan.json` (status: "Redrawn 2026-10-09 with PhotoCraft; approved by John";
  crop: what changed; credit: as short as the house form), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and add a dated LESSONS.md entry under the source family's heading.
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run with python directly).
- No outside review unless John asks for one. Check each credit against the museum's record and the publication's
  text yourself.
- Then stop and report: branch, commits, what John approved.

## Prompts

R1:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/redo-2026-10-09/HANDOFF.md` and do session R1: redraw
> Antigone and then Medea with PhotoCraft, replacing the old SVGs, on a new branch `claude/redesign-redo-r1`. Your
> first message to me asks me to OK the downloads you need and shows what each drawing will hold.

R2:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/redo-2026-10-09/HANDOFF.md` and do session R2: redraw
> Philoctetes and then Oedipus at Colonus with PhotoCraft, replacing the old SVGs, on a new branch
> `claude/redesign-redo-r2`. The sources are already on disk; your first message to me shows what each drawing will
> hold.

R3:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/redo-2026-10-09/HANDOFF.md` and do session R3: redraw the
> home-page Pythia (Aeschylus) and then Iphigenia (Euripides) with PhotoCraft, replacing the old SVGs, on a new branch
> `claude/redesign-redo-r3`. Your first message to me asks me to OK the downloads you need.

R4:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/redo-2026-10-09/HANDOFF.md` and do session R4: redraw the
> home-page Mika (Aristophanes) with PhotoCraft, replacing the old SVG, on a new branch `claude/redesign-redo-r4`.
> The Sophocles home figure is still open; leave it. Your first message to me asks me to OK the download you need.
