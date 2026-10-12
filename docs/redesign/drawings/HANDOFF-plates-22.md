# Handoff: Cyclops drawing with PhotoCraft (Gazette archéologique 1887, pl. 1, the blinding of Polyphemus), 2026-10-12

One session, one drawing. John picked it on 2026-10-10 19:25 (28-7Da; record in `.remember/sweep2-2026-10-04/rulings.md`:
"For cyclops do 28-7Da"). Other sessions are running (Persians on `claude/redesign-plates-20`, Prometheus Bound on
`claude/redesign-plates-21`, perhaps Bacchae on plates-15 and Medea): don't touch their branches, worktrees or notes.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Cyclops (Euripides), key 28-7Da | E. Saglio, *Gazette archéologique* 12 (1887), pl. 1 | `claude/redesign-plates-22`, `.claude/worktrees/redesign-plates-22` | `.remember/batch20/` |

## The source
- Internet Archive `gazette-archeologique_1887_12`, page n418:
  https://archive.org/details/gazette-archeologique_1887_12/page/n418/mode/1up (leaf about 2635 x 3625, printed
  sideways: turn it 90 degrees clockwise; the card's crop in the unrotated leaf: 579, 435, 2045, 3170). Download only
  that page's image at full size (the IA page-image or IIIF URL), never the 442 MB JP2 tar or the 249 MB zip.
  Public domain (published 1887); read the item's licence field.
- The plate: a colour chromolithograph of a black-figure oinochoe (Louvre F 342, Theseus Painter, 550-500 BC):
  black silhouettes with thin incised lines and added red and white on an orange panel. Three men in short chitons
  and caps drive a long stake into the face of the reclining, bearded Polyphemus, who holds a club; ivy trails above
  and a fire burns at the left. Each man about 1,090 px tall; the panel about 2,700 x 1,470. The men overlap each
  other and Polyphemus: one group. The incised lines are thin and the purple faint. No nudity.
- Preview: `.remember/sweep6-2026-10-08/page/imgs/28-7Da.jpg`.
- The play: told. The blinding happens in the cave off stage and Odysseus reports it (Cyclops 663 ff.). The vase is
  Archaic and has no satyrs.

## Ask John first (one message, start it with "Cyclops (PhotoCraft)")
1. The download OK (name the file, the source, and the size), with the preview crop.
2. What the drawing holds: the group alone, or with the ivy and the fire. Whole figures only.
3. The style: black-figure as a silhouette, as Hecuba (`tools/hecuba.py`, merged 2026-10-10) and Ajax: the black solid,
   the incisions as clay lines, the added red as a `tone` wash, any added white as `white` paths (as Wealth). Show a
   small test of Polyphemus's head and the stake in both themes.

## Credit
- Read Saglio's article for the plate (same IA volume, OCR text in the item). Then the Louvre's record for F 342
  (collections.louvre.fr) and the Beazley Archive (attribution, date), and check the credit against them. Title as the
  museum reads it.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes the
  SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel grid;
  read his marks literally. Send the red overlay with every pass (John asked for it before approving Electra).
- Your models: `tools/hecuba.py` (black-figure silhouette, PhotoCraft), `tools/ajax.py`, and `tools/wealth.py` for
  added white. Read `docs/redesign/drawings/LESSONS.md` whole: the black-figure section, "Checks that caught real
  faults", "John's traces", and the 2026-10-10 entries (pin the line weight after pass 1; diff the whole plate after
  each round; `OPEN`, `DROP`; John's short lines meaning "this is paint").
- This plate's traps: thin incisions inside overlapping silhouettes (where two black bodies touch, the only border is
  an incision: keep it); the long stake across the group (straight and whole); the faint purple; the chromolitho's
  dot screen must not become lines; the fold or page edge if near.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe. Keep the .pcraft under
  30 MB if John marks it on his phone (Persians' was 33 MB and Mac-only): crop to the group.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.
- John may be on Remote Control: send every image with SendUserFile and ask with AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-22.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here (gitignored);
  never commit it.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.
- When John approves, update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Cyclops to `settled.json` (wid `cyclops`; render `imgs/drawn-cyclops.png` at
  700 px high on #fbf9f4 with rsvg-convert; `imgs/orig-cyclops.jpg` from `imgs/28-7Da.jpg`), run `build7.py`, read the
  artifact first (another session may have published since), and publish `index.html` with the two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch20/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Cyclops (Gazette archéologique 1887, pl. 1, the blinding of Polyphemus), on a new branch
> `claude/redesign-plates-22`. Your first message to me asks me to OK the download, what the drawing holds, and the
> style.
