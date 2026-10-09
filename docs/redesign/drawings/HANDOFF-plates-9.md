# Handoff: Lysistrata drawing from Furtwängler-Reichhold I Taf. 17/18 (round dance), with PhotoCraft, 2026-10-08

Make one line drawing for Aristophanes' *Lysistrata* from Furtwängler and Reichhold, *Griechische
Vasenmalerei* I (Munich, 1904), Taf. 17/18, "Attischer Krater aus Falerii" (sweep 2 code 35m, John's pick
2026-10-05): two dancing women facing each other, hands clasped. Every image step runs in PhotoCraft;
John corrects on a pixel grid. This file is all you need.

## The source (John OK'd this download 2026-10-05, "downlaod those"; fetch it again, it was not kept)

- https://digi.ub.uni-heidelberg.de/iiif/2/furtwaengler1904bd1%3A017_18.jpg/full/full/0/default.jpg
  (6184 x 2426; page https://digi.ub.uni-heidelberg.de/diglit/furtwaengler1904bd1/0018). Public domain
  (1904). Save it to `.remember/batch9/src/` (gitignored); never commit it.
- The pair (sweep 2's crop, full-scan px, x y w h): 2796 458 816 942. Left woman 878 px tall (diadem to
  toe), right woman 890. Long chitons and mantles; no nudity.
- **They touch their neighbours.** Each holds a third hand on the outer side: at the left edge the
  previous dancer's hand and wrist grip the left woman's hand; at the right edge the next dancer's hand
  clasps the right woman's. The next dancer's skirt and bare foot come into the bottom right corner, a
  sliver of the previous one's at the bottom left. DESIGN.md wants whole figures and no fragments of
  neighbours: cut each neighbour's hand away along the clasp, so our women's hands are whole (as
  Suppliant Women cut Poseidon's toes along Amymone's sole, `tools/suppliants_aesch.py`), and say
  where you cut when you show John. If a hand can't be made whole, show him the clasp on the pixel grid
  and ask.
- The ornament bands above and below the frieze are out.
- Check the source before you credit it (LESSONS, FR): read FR's text for Taf. 17/18 (from p. 98, per the
  sweep; Heidelberg's OCR finds the pages), and the vase's museum record: an Attic red-figure calyx-krater
  from Falerii, Rome, Villa Giulia, c. 450-440 BC (the sweep's reading; inventory not yet found).

## Method: Furtwängler-Reichhold (pen lines on grey-brown, the ground a dark halftone)

- Read LESSONS "Furtwängler and Reichhold" and `tools/andromache.py`. FR plates need the plate's own,
  finer weight (Andromache: 0.11%); draw lines along their centres and trace with `weight="drawn"`.
- Faces, hands, feet and dense drapery are what the line finder can't do cleanly. On Andromache John
  traced them; he does not want to trace now. Send him every face and hand on the pixel grid at the
  start, with your lines over them, and fix what he marks.
- Budget hours, not minutes (Andromache: about ten).

## The play

- A women's round dance at a festival: a women's chorus, the type of Lysistrata's women; the vase does not
  show the play. Sweep 2 marked the link "weak" and John picked it anyway. Say so in the `shows` field.

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
- Branch: new `claude/redesign-plates-9` off main, in its own worktree `.claude/worktrees/redesign-plates-9`.
  Copy this file in as `docs/redesign/drawings/HANDOFF-plates-9.md` and commit it first. Commit as you
  go and push. Merging is John's call.
- Other drawing sessions may run at the same time (Clouds on plates-7 and others): don't touch their
  branches, worktrees or `.remember/batch*/` folders. You all fill the same record files: before the
  records step, merge the latest main into your branch, keep every other play's entry, and rerun the
  contact sheet.
- Keep notes and `timing.txt` in `.remember/batch9/`. Python venv in your scratchpad (numpy, scipy,
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

Start every message to him with "Lysistrata (PhotoCraft)". Send with SendUserFile:

- source crop | light | dark at 400 and 120 px;
- the whole drawing at full width in both themes;
- the full-res red overlay (lines at about 55% opacity over the source);
- close-ups of every face and hand at 4-6x (source | drawing | dark | overlay), plus each face on the
  pixel grid.

Look at all of them yourself first, at full size, for jagged or broken lines, for clay past the
outlines, and for the faces against the source. Ask his verdict with AskUserQuestion. He may answer by
marking a pixel grid or circling places on the overlay: map his marks exactly.

## Records, when he approves

- `tools/lysistrata.py` and `lysistrata.svg`.
- Fill the `lysistrata` entry in `docs/redesign/research/play-image-plan.json` (short house credit form, as the
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
