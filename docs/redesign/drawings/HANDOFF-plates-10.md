# Handoff: Acharnians drawing from a vase photo (Würzburg H 4689, the seated warrior), with PhotoCraft, 2026-10-08

Make one line drawing for Aristophanes' *Acharnians*: the seated, crested warrior from the phlyax scene on
the Apulian bell-krater Würzburg H 4689 (sweep 2 code 29b; John's pick 2026-10-05, "the seated warrior;
flatten first"). Every image step runs in PhotoCraft; John corrects on a pixel grid. This file is all you
need.

## The source (John OK'd this download 2026-10-05, "downlaod those"; fetch it again, it was not kept)

- https://upload.wikimedia.org/wikipedia/commons/3/38/McDaniel_Painter_-_RVAp_4-245_-_departure_of_warrior_as_phlyax_play_-_draped_youths_-_W%C3%BCrzburg_MvWM_H_4689_-_07.jpg
  (3648 x 5472; page
  https://commons.wikimedia.org/wiki/File:McDaniel_Painter_-_RVAp_4-245_-_departure_of_warrior_as_phlyax_play_-_draped_youths_-_W%C3%BCrzburg_MvWM_H_4689_-_07.jpg).
  ArchaiOptix, 2015-10-16, CC BY-SA 4.0. Save it to `.remember/batch10/src/` (gitignored); never commit it.
  Read its EXIF for the focal length.
- The figure: the seated warrior only, about 4,200 px tall: crested helmet, round shield, short sleeved
  chiton, right hand raised, seated on a stool. He touches only his stool and shield rim (keep both). The
  old man's spear tip comes in from the left: cut it off. Leave out the old man, the pillar, the stage and
  the ground. The sweep checked at 3x: no costume phallus (the chiton covers his lap). Check again: a
  costume phallus is out (John's one nudity rule).
- Other photos of H 4689 by ArchaiOptix are on Commons (the same set; -03 shows the old man). Use those
  that help fit the vase for flattening; they are the same licence and already covered by the OK, but
  list which you fetch.
- **Flatten first** (John's pick, and the memory on vase photos): `tools/vase_unroll.py`, fitted to the
  silhouette and a painted band, focal length fixed from EXIF, `flatten` rather than plain unrolling.
  Check the head against the most frontal photo before you show John.
- The vase, as sweep 1 read it (**verify before the credit**): Apulian red-figure bell-krater by the
  McDaniel Painter, c. 380-370 BC; CVA Würzburg 4 pl. 3.1-4; Trendall and Cambitoglou RVAp 4/245.
  Check the museum's record (Martin von Wagner Museum) and quote it.
- Rights: John's rulings say a drawing that traces only the ancient painting does not carry the photo's
  licence (Oedipus Tyrannus 2026-10-02, Philoctetes 2026-10-03); credit ArchaiOptix. But the earlier
  ArchaiOptix drawings (Euphorbos, Mika, Antigone) are listed in the README as CC BY-SA 4.0. Ask John
  in one line which applies before you fill the licence field; copyright calls are his.

## Method: your nearest models

- `tools/euphorbos.py`, `tools/antigone.py` (ArchaiOptix photos, flattened), `tools/philoctetes.py`:
  red-figure from vase photos, clay mask, lines by local contrast.
- `tools/oedipus_syracuse.py`: a South Italian vase photo with wear (cracks erased, worn lines joined).
- `tools/trojan_women_menelaus.py`: the PhotoCraft steps, faint lines, walls, a profile on John's line.
- Mika (`tools/mika.py`, `aristophanes-mika.svg`) is the other comic figure on the site; keep the two
  consistent in weight.

## The play

- A comic "departure of the warrior": the type of Lamachus, the crested general of *Acharnians*
  (572-625, 1071-1142). The link is the sweep's reading of the type, not a scholar's identification of
  this vase with the play. Say so in the `shows` field.

## What carries over from Trojan Women (batch 6, approved 2026-10-08, merged to main dead4d1)

- **John does not want to trace.** Get the lines right yourself; send him things to judge, not to draw.
- **Lines smooth, even, unbroken.** Faint lines print as dotted runs: find them by local contrast, draw
  each along a curve fitted to it, and join the pieces of one line across the gaps
  (`faint_lines`, `join_breaks` with `ALIGN_*` in `tools/trojan_women_menelaus.py`). Check every
  close-up at 4-6x for jagged or broken lines before you show him.
- **Clay (the dark theme's `body` fill) stops at the outlines.** Mark everything outside the figure as
  open (`held = ~fig`), or trace_svg's clay rims stray onto the ground.
- **Trace the printed/painted lines**, not the edges of coloured areas.
- **Faces and hands are where John looks first.** On Trojan Women the lips and chin took three tries of
  mine, each worse ("The mouth is WORSE now"); his own line, drawn on a pixel grid, settled it.

## Corrections: use the pixel grid (John, 2026-10-07: "showing the pixels is the most helpful way to give corrections")

When John flags a spot, or before you show him a face or hand you are unsure of, send him the source's
pixels at about 20x with a labelled 1 px grid (every 5th line blue, coordinates in yellow) and the
drawing's ink over it in translucent red. He draws on it: **red = where ink goes, green = ground (not
ink)**. Map his marks cell by cell (source px = x0 + image px / 20) and put the line exactly there.
Read his marks literally; if what he means is unclear, ask in one line before you run anything.
Script: `.remember/batch6/scripts/pxgrid.py` (svg, source image, cfg.json, x0 y0 x1 y1, K, out). Build
the grid on the image your tool works from (levelled or flattened, if it is).

## PhotoCraft

John's instruction (2026-10-07): use PhotoCraft for the image work. Every image step runs in it; small
numpy glue for combining masks and measuring is fine (say so in the tool's docstring). The SVG is still
written by `linework.trace_svg`.

- CLI: `~/.local/bin/photocraft-cli` (0.2.0). `commands [--json] [--filter x]` lists the commands with
  their params; `run <file> --cmd <id> --params '<json>' [--cmd ...] --out <file>`; `info`; `convert`.
- Commands used in batch 6: `image.crop {x,y,width,height}`, `image.imageSize {width,height,resample}`,
  `image.mode.grayscale`, `filter.blur.gaussianBlur {radius}`, `filter.other.maximum` / `minimum
  {radius, preserve:"squareness"}` (Maximum then Minimum on the blurred image, less the blurred image,
  is the local contrast `linework.ink_lines` uses), `image.adjustments.threshold {level}`. Also
  available: `image.rotation.arbitrary`, `filter.noise.median`, `filter.other.highPass`,
  `select.colorRange` (sampled colours or shadows), `select.toWorkPath` + `path.info` (vector paths).
- The `pc()` helper in `tools/trojan_women_menelaus.py` runs a chain of commands; copy it.
- Geometry (levelling a page, flattening a vase) is not image filtering: keep it in numpy/scipy and say
  so in the docstring. If any step can't run in PhotoCraft, say which and why.
- If you hand John files to mark up in PhotoCraft, make them `.pcraft` with a named empty layer.

## Before you start

- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/LESSONS.md` (all of it; above all the section for this plate's family,
  Checks, John's traces, and the 2026-10-08 PhotoCraft entries under the Gerhard red-figure heading),
  `docs/redesign/drawings/README.md` (SVG format: 1000 units tall, `body` path then `lines` path), and
  the Drawings section of `docs/redesign/DESIGN.md` (John's file, untracked in the main checkout: never
  edit it). DESIGN.md says whole figures only, no fragments of neighbouring figures.
- Branch: new `claude/redesign-plates-10` off main, in its own worktree `.claude/worktrees/redesign-plates-10`.
  Copy this file in as `docs/redesign/drawings/HANDOFF-plates-10.md` and commit it first. Commit as you
  go and push. Merging is John's call.
- Other drawing sessions may run at the same time (Clouds on plates-7 and others): don't touch their
  branches, worktrees or `.remember/batch*/` folders. You all fill the same record files: before the
  records step, merge the latest main into your branch, keep every other play's entry, and rerun the
  contact sheet.
- Keep notes and `timing.txt` in `.remember/batch10/`. Python venv in your scratchpad (numpy, scipy,
  scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are installed.
- Helper scripts (outside git; copy them, don't edit the originals):
  - `.remember/batch5/scripts/`:
    - `sclose.py` (source | drawing | dark | overlay close-ups; its cfg.json `box` must match the box
      the tool printed on THIS run)
    - `showset.py` (400/120 px set)
    - `gaps.py` (facing line ends)
    - `missed.py`
  - `.remember/batch6/scripts/`:
    - `pxgrid.py` (the pixel grid)
    - `redover.py` (full-res translucent red overlay; John asked for it before judging)
    - `full.py` (whole drawing at full width, both themes)
    - `claycheck.py` (body edge with no line over it)
    - `circles.py` (a sheet of the places John circled)
    - `clsbox.py`, `leak2.py` (ground/clay/paint maps; where ground leaks into a border)
  - Their crop constants (X0, Y0, UP) are batch 6's: set them for your tool.

## Show John

Start every message to him with "Acharnians (PhotoCraft)". Send with SendUserFile:

- source crop | light | dark at 400 and 120 px;
- the whole drawing at full width in both themes;
- the full-res red overlay (lines at about 55% opacity over the source);
- close-ups of every face and hand at 4-6x (source | drawing | dark | overlay), plus each face on the
  pixel grid.

Look at all of them yourself first, at full size, for jagged or broken lines, for clay past the
outlines, and for the faces against the source. Ask his verdict with AskUserQuestion. He may answer by
marking a pixel grid or circling places on the overlay: map his marks exactly.

## Records, when he approves

- `tools/acharnians.py` and `acharnians.svg`.
- Fill the `acharnians` entry in `docs/redesign/research/play-image-plan.json` (short house credit form, as the
  hippolytus and trojan-women entries), add to `drawings.json` and the README table, rerun
  `tools/contact_sheet.py`, and add a dated LESSONS.md entry under the plate family's heading.
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly; no pytest in the venv).
- **No outside review unless John asks for one.** On Trojan Women: "IVE REVIEWED IT. ITS VISUAL. VERIFY
  CITATION YOURSELF". Check the credit against the museum's own record and the publication's text
  yourself, and quote your sources. If a fetch hits a bot check, open the page in the browser pane
  (`mcp__Claude_Browser__navigate` + `get_page_text`); that worked for the British Museum. On Trojan Women
  the publication had the museum wrong: check both.
- Then stop and report: branch, commit, what John approved, the credit's sources.
