# Handoff: Wealth drawing with PhotoCraft (Élite III pl. LVIII, Plutos), 2026-10-10

One session, one drawing. John picked it on Plate Picks on 2026-10-08 (39-Ba; record in
`.remember/sweep2-2026-10-04/rulings.md`). It comes after Iphigenia at Aulis (`claude/redesign-plates-14`, its own
session): don't touch that branch, Hecuba/Bacchae's (`claude/redesign-plates-15`), or their notes folders.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Wealth (Aristophanes), key 39-Ba | Lenormant and de Witte, *Élite des monuments céramographiques* III (1858), pl. LVIII | `claude/redesign-plates-16`, `.claude/worktrees/redesign-plates-16` | `.remember/batch15/` |

## The source
- Scan: https://digi.ub.uni-heidelberg.de/diglitData/image/lenormant1858bd3/4/303_Planche_ROEM_058.jpg
  (4272 x 2818, a double plate printed upright; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0387).
  Licence: Public Domain Mark 1.0 (the volume's IIIF manifest, checked 2026-10-10).
- The figure: Plutos at the far left of a Triptolemos frieze, an old man with white hair and beard, in a long chiton
  and mantle, holding a long banded sceptre and a cornucopia (a snail shell and leaves at its mouth). Box in full-scan
  px about x 121-926, y 591-1938 (the card's crop); he is about 1,250 px tall, well above the floor.
- Leave out the next woman (her torch and hem come in at the right edge): whole figures only, no fragments of
  neighbours (DESIGN.md, Drawings). A thin vertical line runs down the plate through the top of the sceptre (in the
  preview at about a third of the width): find out whether it is a crease, a join, or printed, and keep it out of the
  drawing. The double plate's fold is far to the right, clear of him. The signature "Lith. de Fourquemin" below the
  panel stays out.
- Preview of the crop: `preview_plutos.jpg` here (the Plate Picks card image).
- The play: Plutos (Wealth) is the god of the play; the vase shows him sighted, not blind as in the play. A character
  of the play in another story, not a scene of it.

## Ask John first (one message, start it with "Wealth (PhotoCraft)")
1. The download OK (name the file, the source, and the size), with the preview crop.
2. The white hair and beard. They are added white over the black ground, with no black outline. Earlier rulings:
   Acharnians (the old man's white hair and beard as strokes in a stepped grey `tone` wash, John chose B of two) and
   Clouds (white hair as `class="white"` paths, in colour). Offer those two as the choice, with a small test of each
   on this head before pass 1.

## Credit
- Read the Élite III's plate list and its text for pl. LVIII yourself: what Lenormant and de Witte call the vase and
  the scene, where the vase was, whom they name. The card says a hydria from Nola with Triptolemos.
- Then find where the vase is now (Beazley Archive record in the browser pane; the museum's own record if there is
  one) and check the credit against it, as on Ion, Helen, and Phoenician Women. On Helen John titled the drawing as
  the museum reads it; on Phoenician Women (vase lost) he chose the Élite's reading. If the readings differ, ask in
  one line.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step
  in PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg`
  writes the SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a
  pixel grid.
- Your model is `tools/phoenician_women.py` (Élite, PhotoCraft, approved and merged 2026-10-10, main f46ef57), with
  `tools/helen.py` and `tools/ion.py`. Read `docs/redesign/drawings/LESSONS.md` whole, above all the Élite section's
  2026-10-09 and 2026-10-10 entries:
  - Pin the line weight after pass 1 (`WEIGHT`); after each round, diff the whole plate against the last pass.
  - Bands of solid paint that touch the ground (here: the sceptre's black bands, the girdle at his waist, the
    cornucopia's dark inside, the mantle's folds where they open onto the ground) read as ground. Wall them off
    (`WALLS`) and check the masks before pass 1.
  - A short line John draws across such a junction means "this is paint": use it as the wall and drop it (`DROP`).
  - Clay the figure closes in can be the vase's ground (`OPEN`): John's call.
  - The sceptre is long and thin: check it stays whole and straight (a `keep` mask if the opening eats it).
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/` (`run.py`, `red.py`, `build.py`, `export.py`);
  copy them to your scratchpad and change the tool name and the box. LESSONS has the recipe (Phoenician Women entry).
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-16.md`, commit first, commit as you go, push. Merging is John's call.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here (gitignored);
  never commit it.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other
  entry, rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.
- When John approves, also update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Wealth to `settled.json` (render `imgs/drawn-wealth.png` at 700 px high
  on #fbf9f4 with rsvg-convert; `imgs/orig-wealth.jpg` from `imgs/39-Ba.jpg`), run `build7.py`, and publish
  `index.html` with the two new images to that URL.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch15/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Wealth (Élite III, pl. LVIII, Plutos with the cornucopia), on a new branch
> `claude/redesign-plates-16`. Your first message to me asks me to OK the Heidelberg download and how to draw the
> white hair and beard.
