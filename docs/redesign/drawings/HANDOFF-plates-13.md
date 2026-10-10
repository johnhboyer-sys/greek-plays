# Handoff: two Élite plate drawings with PhotoCraft, Helen and Phoenician Women, 2026-10-10

Two sessions, one drawing each, run side by side. Both plates are from Lenormant and de Witte, *Élite des monuments
céramographiques* (coloured lithographs, red figures on black), the family of Ion, Suppliants (Aeschylus) and
Alcestis, all approved. John picked both on 2026-10-08 (Plate Picks page,
https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD; record in `.remember/sweep2-2026-10-04/rulings.md`). Every image
step runs in PhotoCraft; John corrects on a pixel grid or in PhotoCraft. This file is all you need; your prompt names
your session (A or B).

| Session | Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|---|
| A | Helen (Euripides), key 22-6Ea | Élite III (1858), pl. LVII B | `claude/redesign-plates-12`, `.claude/worktrees/redesign-plates-12` | `.remember/batch12/a/` |
| B | Phoenician Women (Euripides), key 23-6Eb | Élite I (1844), pl. XXVIII | `claude/redesign-plates-13`, `.claude/worktrees/redesign-plates-13` | `.remember/batch12/b/` |

## A: Helen
- Scan: https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1858bd3%3A303_Planche_ROEM_057_B.jpg/full/full/0/default.jpg
  (1826 x 2768, printed sideways: rotate 90 clockwise; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0386).
  The preview crop in full-scan px of the unrotated scan (x0 y0 x1 y1): 448 470 1420 1224.
- The figures: Menelaus, bearded and bare-chested in a short armoured skirt with a spear, leads away veiled Helen; his
  hand rests on her shoulder. Draw the pair as one group. A wing tip of Eris enters at the left edge: leave it out
  (cut along the pair's own outlines). A nude youth elsewhere on the plate is outside the crop.
- Size: the pair is about 880 px tall, near the floor. Faces and hands are small: enlarge in PhotoCraft (4x has
  worked) and check them on the pixel grid before showing John.
- The play: Menelaus and Helen at the end of the Trojan War, the war that frames the play (in the play the real Helen
  waited in Egypt). Not BM E 263, the Gerhard plate used for Trojan Women: a different vase.

## B: Phoenician Women
- Scan: https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1844bd1%3APlanche_028.jpg/full/full/0/default.jpg
  (1790 x 2811, printed sideways: rotate 90 clockwise; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1844bd1/0478).
  The preview crop in full-scan px of the unrotated scan: 220 92 1480 2536.
- The figures: Europa sits sideways on a leaping bull, and a woman the editors call Phoenice gestures after them. The
  bull's tail touches her skirt. Propose to John: the whole group (woman, bull and Europa), or Europa on the bull
  alone. The woman is about 1,110 px tall; the bull with Europa about 1,010.
- The play: Europa is a Phoenician princess, sister of Cadmus, founder of Thebes; the play's chorus are Phoenician
  women. A thematic link, not a scene of the play.

## Sources and credits (both)
- Heidelberg, public domain. Your first message asks John to OK the one download, and shows a crop of what the
  drawing will hold. Read the licence in the volume's IIIF manifest
  (`https://digi.ub.uni-heidelberg.de/diglit/iiif/<record>/manifest.json`); the viewer pages sit behind a bot check,
  but IIIF image links open in the browser pane.
- Save the scan to your notes folder's `src/` (gitignored); never commit it.
- Read the plate's own text in the Élite (its explanation pages) for what Lenormant and de Witte say the vase is, where
  it was, and whom they name; then find where the vase is now and check the credit against the museum's record. Ion's
  credit traced its vase back through the Élite's text to Hamilton-Tischbein: do the same. On Trojan Women the
  publication had the museum wrong: check both. If a fetch hits a bot check, open the page in the browser pane.

## Method
- Read `docs/redesign/drawings/LESSONS.md` all of it; above all the Élite section (including the Ion entries of
  2026-10-09), the PhotoCraft entries, "Checks that caught real faults" and "John's traces".
- Your model is `tools/ion.py` (Élite, PhotoCraft, approved 2026-10-09 after five passes on John's marks: read its
  commits and `tools/ion_marks_*.png` for what he corrected). Also `tools/suppliants_aesch.py` and `tools/alcestis.py`
  (Élite; the dark-theme fixes: the outline capped at 0.6 of a thin part's half-width, all the ground marked open;
  `level` if the frame bends) and `tools/heracles.py` (PhotoCraft, approved 2026-10-09).
- Every image step runs in PhotoCraft (`~/.local/bin/photocraft-cli`: `commands`, `run`, `convert`; MCP via
  `photocraft-cli mcp`); rotation and levelling may stay in numpy/scipy; say so in the docstring. The SVG is written by
  `linework.trace_svg`.
- John does not want to trace: get the lines right yourself and send him things to judge. Lines smooth, even,
  unbroken; clay stops at the outlines (`held = ~fig`); trace the printed lines, not the edges of coloured areas;
  faces and hands first (each finger at 20x; eyes never heavy).
- Corrections: the source's pixels at about 20x with a labelled 1 px grid and the ink in translucent red
  (`.remember/batch6/scripts/pxgrid.py`; red = ink, green = ground), or a full-res export he marks in PhotoCraft
  (blue = add, green = remove; read it with `photocraft-cli convert`). Read his marks literally; ask in one line if
  unclear.
- Nudity: draw as printed (John, 2026-10-09: "no censorship").

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/README.md` (SVG format) and the Drawings section of `docs/redesign/DESIGN.md` (John's
  file, untracked in the main checkout: never edit it; whole figures only, no fragments of neighbours).
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-12.md` (session A) or leave it out (session B: A commits it; if A has not
  merged, copy it in yourself as `HANDOFF-plates-13.md`), commit first, commit as you go, push. Merging is John's call.
- Other sessions run at the same time (the other session of this pair, the redo sessions R1-R4, perhaps more): don't
  touch their branches, worktrees or notes folders. You all fill the same record files: before the records step,
  merge the latest main into your branch, keep every other entry, and rerun the contact sheet.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in your notes folder. Python venv in your scratchpad
  (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are installed. Helper scripts
  (copy, don't edit): `.remember/batch5/scripts/`, `.remember/batch6/scripts/`.

## Show John
Start every message with "Helen (PhotoCraft)" or "Phoenician Women (PhotoCraft)". Send with SendUserFile: source crop |
light | dark at 400 and 120 px; the whole drawing at full width in both themes; the full-res red overlay (lines at
about 55% over the source); close-ups of every face and hand at 4-6x, plus each face on the pixel grid. Look at all of
them yourself first, at full size. Ask his verdict with AskUserQuestion.

## Records, when he approves
- `tools/helen.py` and `helen.svg`, or `tools/phoenician_women.py` and `phoenician-women.svg`.
- Fill the play's entry in `docs/redesign/research/play-image-plan.json` (short house credit form, as the ion and
  hippolytus entries), add to `drawings.json` and the README table, rerun `tools/contact_sheet.py`, and add a dated
  LESSONS.md entry under the Élite heading.
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly).
- No outside review unless John asks for one. Then stop and report: branch, commits, what John approved, the credit's
  sources.

## Prompts

A:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch12/HANDOFF.md` and do session A: one line drawing with
> PhotoCraft for Helen (Élite III, pl. LVII B, Menelaus leading Helen), on a new branch `claude/redesign-plates-12`.
> Your first message to me asks me to OK the Heidelberg download and shows a crop of what the drawing will hold.

B:
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch12/HANDOFF.md` and do session B: one line drawing with
> PhotoCraft for Phoenician Women (Élite I, pl. XXVIII, Europa on the bull and Phoenice), on a new branch
> `claude/redesign-plates-13`. Your first message to me asks me to OK the Heidelberg download and proposes what the
> drawing holds.
