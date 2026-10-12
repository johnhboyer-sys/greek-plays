# Handoff: Persians drawing with PhotoCraft (Heydemann 1883, the Persian king fleeing), 2026-10-10

One session, one drawing. John picked it on 2026-10-09 11:51 (1-7Pa; record in `.remember/sweep2-2026-10-04/rulings.md`:
"Heydemann, Hallisches Winckelmannsprogramm 8 (1883), top frieze (Naples H 3220)"). A second session draws Electra
(Sophocles) at the same time (`claude/redesign-plates-19`, `.remember/batch17/`); others may be running (Wasps on
plates-17, Bacchae on plates-15). Don't touch their branches, worktrees or notes.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Persians (Aeschylus), key 1-7Pa | H. Heydemann, *Hallisches Winckelmannsprogramm* 8 (1883), folding plate, top frieze | `claude/redesign-plates-20`, `.claude/worktrees/redesign-plates-20` | `.remember/batch18/` |

## The source
- Page: https://digi.ub.uni-heidelberg.de/diglit/hwpr1883/0029 (3682 x 2779 in the card; find the image URL and the
  largest size in the volume's IIIF manifest, https://digi.ub.uni-heidelberg.de/diglit/iiif/hwpr1883/manifest.json,
  Public Domain Mark 1.0, checked 2026-10-10). The card's crop of the top frieze in full-scan px: 258, 202, 3351, 1233.
- The plate: a pen contour drawing with the dress patterns drawn, no black ground. A Persian king in a cap,
  patterned sleeves and trousers flees in a four-horse chariot with a young driver, looking back, while a Greek
  horseman charges with a lance; at the right a Greek youth with a shield fights a Persian with a battle-axe. The
  horses of all three groups overlap. Sizes: the rider-and-chariot group about 930 px tall; the king alone about 430,
  the right-hand Greek about 800, the axe-man about 620. The right-hand Greek may be bare under his cloak: draw as
  printed (John, 2026-10-09: "no censorship").
- The book's fold runs faintly down the middle, through the chariot horses: erase it whole and join the lines it
  broke; draw nothing along it (John, 2026-10-02, "cracks leave no line").
- Preview: `.remember/sweep6-2026-10-08/page/imgs/1-7Pa.jpg`.
- The vase: Naples H 3220, an Apulian amphora from Ruvo (the Darius Painter's circle, check). Heydemann reads it as
  Alexander routing Darius III. The play: thematic only, a Persian king beaten by Greeks, in Persian dress; not a
  scene of the play.

## Ask John first (one message, start it with "Persians (PhotoCraft)")
1. The download OK (name the file, the source, and the size), with the preview crop.
2. What the drawing holds: the whole top frieze (chariot group, horseman, and the fight at the right), or the king's
   chariot group with the horseman alone. Whole figures only either way, no fragments of neighbours. Show the two
   crops side by side.
3. The style: a contour plate as Rhesus (merged today, `tools/rhesus.py`): pen lines, the figures' area the paper the
   lines close off, clay on the dark theme. Confirm with a small test of the king's head in both themes.

## Credit
- Read Heydemann's text for the plate (the programme's pages on Heidelberg; text pages sit behind a bot check: read
  them in the browser pane, one page at a time). Then the vase now: Naples, Museo Archeologico Nazionale H 3220 (the
  museum's record if online; Trendall, RVAp; the "Persians vase" literature) and check the credit against it.
  Title in one line to John: Heydemann's reading (Alexander and Darius) or the museum's.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes
  the SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel
  grid; read his marks literally.
- Your model: `tools/rhesus.py` (Hoernes's contour plate, approved and merged 2026-10-10, main 68d5733): pen lines at
  half maximum, the figures' area by a sealed watershed with pockets, shafts kept, walls. Read
  `docs/redesign/drawings/LESSONS.md` whole: the contour-plates entry Rhesus added, the Furtwängler-Reichhold section,
  "Checks that caught real faults", "John's traces", the 2026-10-10 entries (pin the line weight after pass 1, John
  set Rhesus's at 0.12%; diff the whole plate after each round; `OPEN`, `DROP`).
- This plate's traps: overlapping horses (legs, reins and harness cross; each leg whole), the dress patterns (small
  marks at their printed width through `dots`), the lance and spears (long, thin, straight and whole), the fold, and
  the small king (430 px: his face and hands at 20x).
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe (Phoenician Women).
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-20.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here (gitignored);
  never commit it.
- Before the records step, merge the latest main (the Electra session fills the same record files: keep every other
  entry, rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder.
- When John approves, update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Persians to `settled.json` (wid `persians`; render `imgs/drawn-persians.png`
  at 700 px high on #fbf9f4 with rsvg-convert; `imgs/orig-persians.jpg` from `imgs/1-7Pa.jpg`), run `build7.py`, read
  the artifact first (another session may have published since), and publish `index.html` with the two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch18/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Persians (Heydemann 1883, the Persian king fleeing in his chariot), on a new branch
> `claude/redesign-plates-20`. Your first message to me asks me to OK the download, what the drawing holds, and the
> style.
