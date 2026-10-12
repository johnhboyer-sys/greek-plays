# Handoff: Electra (Sophocles) drawing with PhotoCraft (Laborde, Vases Lamberg I, pl. VIII), 2026-10-10

One session, one drawing. John picked it on Plate Picks on 2026-10-09 (10-7Ba; record in
`.remember/sweep2-2026-10-04/rulings.md`: "Laborde, Vases Lamberg I (1813), pl. VIII (Vienna KHM IV 689); asked about a
bigger copy"). A second session draws Persians at the same time (`claude/redesign-plates-20`, `.remember/batch18/`);
others may be running (Wasps on plates-17, Bacchae on plates-15). Don't touch their branches, worktrees or notes.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Electra (Sophocles), key 10-7Ba | A. de Laborde, *Collection des vases grecs de M. le comte de Lamberg* I (Paris, 1813), pl. VIII | `claude/redesign-plates-19`, `.claude/worktrees/redesign-plates-19` | `.remember/batch17/` |

## The source
- Scan: https://digi.ub.uni-heidelberg.de/diglitData/image/laborde1813bd1/4/Planche_07_8.jpg (1952 x 2786, the leaf
  with pl. VII above and pl. VIII below; page https://digi.ub.uni-heidelberg.de/diglit/laborde1813bd1/0122).
  Licence: Public Domain Mark 1.0 (the volume's IIIF manifest, checked 2026-10-10). The card's crop in full-scan px:
  376, 1259, 1657, 2089. John asked about a bigger copy: check the IIIF service for a larger size than the 1952 px
  leaf (`https://digi.ub.uni-heidelberg.de/iiif/2/laborde1813bd1%3APlanche_07_8.jpg/full/full/0/default.jpg` and
  the `info.json`), and say in one line what the largest is.
- The plate: a colour aquatint, red figures on a black ground with the interior lines drawn, the family of the Élite
  plates. Orestes holds out an urn to Electra, who is veiled and raises a hand to her chin; Pylades stands behind
  him; all three wear or carry cloaks, the two men hold spears. Nothing touches but the spear shaft behind Orestes.
  The crop catches a sliver of paper above and the top of the meander band below: leave both out.
- Size: the figures are 740-750 px tall, under the usual 800 px floor; work at UP = 4 if 3 leaves curves rough, and
  check faces and hands at 20x. An engraver's tidy rendering of the vase, so it may differ from the vase.
- Nudity: Orestes and Pylades are nude under their cloaks, genitals drawn: draw as printed (John, 2026-10-09).
- Preview: `.remember/sweep6-2026-10-08/page/imgs/10-7Ba.jpg`.
- The play: direct. Orestes brings Electra the urn of his supposed ashes (Soph. El. 1098-1226). Laborde ties it to
  those lines himself; Séchan (1926, fig. 44) agrees but says the painter changed details.

## Ask John first (one message, start it with "Electra (PhotoCraft)")
- The download OK (name the file, the source, and the size), with the preview crop and the largest size the IIIF
  service gives.

## Credit
- Read Laborde's own text for pl. VIII (Heidelberg OCR; the text pages sit behind a bot check: read them in the
  browser pane, one page at a time; bulk `fetch` gets the check page, not the text).
- The vase is probably Vienna, Kunsthistorisches Museum IV 689: the KHM has an online record "Glockenkrater:
  Pylades, Orestes und Elektra", about 350 BC, Lamberg collection, bought 1815
  (https://www.khm.at/objektdb/detail/57936/, opens in the browser pane; decline non-essential cookies). Check that
  it is the same vase (subject, shape, figures), note what the museum reads and dates, and whether it has a photo
  (the KHM allows download for private use only; publishing needs a reproduction request: the drawing traces the
  1813 plate, not the photo). Then Beazley or Trendall if it is Italiote. Title: on Helen John titled as the museum
  reads it; here the museum and Laborde agree on the subject, so say so and take the museum's wording unless it
  differs.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes
  the SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel
  grid; read his marks literally.
- Your models: the Élite tools merged today, `tools/phoenician_women.py`, `tools/iphigenia_aulis.py` and
  `tools/wealth.py` (red figures on black, outlines on the ground outside the clay). Read
  `docs/redesign/drawings/LESSONS.md` whole, above all the Élite section's 2026-10-09 and 2026-10-10 entries: pin the
  line weight after pass 1 and diff the whole plate after each round; bands of solid paint touching the ground read
  as ground (wall them, `WALLS`); John's short lines across such a junction mean "this is paint" (`DROP`); clay he
  calls ground (`OPEN`).
- This plate's traps: Electra's veil over her head and hand (keep the veil's edge and her fingers apart); the urn's
  small marks (route through `dots` at their printed width); the two spear shafts, long and thin (keep them whole
  and straight); the aquatint's grain must not become lines.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe (Phoenician Women).
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-19.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here (gitignored);
  never commit it.
- Before the records step, merge the latest main (the Persians session fills the same record files: keep every other
  entry, rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.
- When John approves, update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Electra to `settled.json` (wid `electra-soph`; render
  `imgs/drawn-electra-soph.png` at 700 px high on #fbf9f4 with rsvg-convert; `imgs/orig-electra-soph.jpg` from
  `imgs/10-7Ba.jpg`), run `build7.py`, read the artifact first (another session may have published since), and
  publish `index.html` with the two new images to that URL.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch17/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Electra (Sophocles) (Laborde, Vases Lamberg I, pl. VIII, Orestes hands Electra the urn), on a new
> branch `claude/redesign-plates-19`. Your first message to me asks me to OK the download.
