# Handoff: Clouds drawing from a vase photo (Louvre CA 7249), with PhotoCraft, 2026-10-08

Make one line drawing for Aristophanes' *Clouds*: the master, a comic old man in a long robe, from the
phlyax scene on Louvre CA 7249 (sweep 2 code 31b; John's pick 2026-10-05, "the master; flatten first";
chosen as the next drawing 2026-10-08). Every image step runs in PhotoCraft. John corrects on a pixel
grid. This file is all you need.

## How the last drawing went (Trojan Women, batch 6), and what to carry over

- Approved on the fourth pass after about three hours. `tools/trojan_women_menelaus.py` on branch
  `claude/redesign-plates-6` (not merged; merging is John's call). Notes: `.remember/batch6/notes.md`.
- **John does not want to trace.** Get the lines right yourself; send him things to judge, not to draw.
- **Lines smooth, even, unbroken.** Faint lines print as dotted runs; find them by local contrast,
  draw each along a curve fitted to it, and join the pieces of one fold across the gaps. Check every
  close-up at 4-6x for jagged or broken lines before you show him.
- **Clay (the dark theme's `body` fill) stops at the outlines.** Mark everything outside the figure as
  open (`held = ~fig`), or trace_svg's clay rims stray onto the ground.
- **Trace the printed/painted lines**, not the edges of coloured areas.
- **Faces and hands are where John looks first.** The lips and chin took three tries of mine and got
  worse each time ("The mouth is WORSE now"). What settled it was his own line, drawn on a pixel grid.

## Corrections: use the pixel grid (John, 2026-10-07: "showing the pixels is the most helpful way to give corrections")

When John flags a spot, or before you show him a face or hand you are unsure of, send him the source's
pixels at about 20x with a labelled 1 px grid (every 5th line blue, coordinates in yellow) and the
drawing's ink over it in translucent red. He draws on it: **red = where ink goes, green = ground (not
ink)**. Map his marks cell by cell (source px = x0 + image px / 20) and put the line exactly there.
Read his marks literally; if what he means is unclear, ask in one line before you run anything.
Script: `.remember/batch6/scripts/pxgrid.py` (svg, source image, cfg.json, x0 y0 x1 y1, K, out). Here the
source is the flattened photo, so build the grid on the flat image your tool works from.

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
- The flattening (`tools/vase_unroll.py`) is geometry, not image filtering: keep it in numpy/scipy, and
  say so in the docstring. If any step can't run in PhotoCraft, say which and why.
- If you hand John files to mark up in PhotoCraft, make them `.pcraft` with a named empty layer.

## Source (not downloaded yet; John OK'd this download 2026-10-05, "downlaod those")

- Photo: https://upload.wikimedia.org/wikipedia/commons/4/41/Phlyax_scene_Louvre_CA7249.jpg
  (2300 x 2420; page https://commons.wikimedia.org/wiki/File:Phlyax_scene_Louvre_CA7249.jpg).
  Jastrow, 2008-03-07, CC BY 3.0 (Commons API, sweep 1 lane D). Save it to `.remember/batch7/src/`
  (gitignored), never commit it. Read its EXIF for the focal length.
- The master is the right-hand figure, about 2,200 px tall: long himation over a long chiton, bearded
  mask with curly hair, arm stretched out, thin fold lines. Leave out the slave at the left (he hitches a
  short tunic and may show a costume phallus: that is out, John's one nudity rule), the stage line, the
  black ground and anything else on the vase.
- Sweep notes: "thin but clear lines; the glaze is worn in places and the black ground is mottled, so
  check the lines at 100%. Photo is straight-on, with little curvature." Still flatten it (John's pick
  says "flatten first", and the memory on vase photos says always): a calyx-krater's wall slopes.
- Other photos of CA 7249 (Commons, the Louvre's collections site) would help the fit and fill worn
  spots. Look, list what you find, and ask John before downloading any.
- The vase, as sweep 1 read it (**verify before the credit**; John: "verify citation yourself"):
  Sicilian red-figure calyx-krater, Lentini-Manfria Group, c. 350-340 BC, h. 55.6 cm, bought 1985.
  Check the Louvre's own record (collections.louvre.fr). If a plain fetch hits a bot check, open it in
  the browser pane (`mcp__Claude_Browser__navigate` + `get_page_text`); that worked for the British
  Museum.
- Rights: the drawing traces only the ancient painting, which is public domain, so it does not carry
  the photo's licence (John's rulings: Oedipus Tyrannus 2026-10-02, Philoctetes 2026-10-03). Credit
  Jastrow. Copyright calls are John's: if anything here looks different, ask.
- Link to the play: a comic old man, the type of Strepsiades. The vase does not show *Clouds*; say so
  in the `shows` field ("related to the play", as earlier entries put it).

## Method: your nearest models

- `tools/philoctetes.py` and `tools/antigone.py`: red-figure from vase photos, flattened with
  `tools/vase_unroll.py` (fit the vase and camera to the silhouette and a painted band; fix the focal
  length from EXIF; `flatten`, not plain unrolling), clay mask, lines by local contrast.
- `tools/oedipus_syracuse.py`: a worn Sicilian vase photo (cracks erased, worn lines joined, a staff
  redrawn straight). Probably the closest in style to this vase.
- `tools/trojan_women_menelaus.py`: the PhotoCraft steps, faint dotted lines (`faint_lines`,
  `join_breaks` with `ALIGN_*`), walls where paint runs into the ground (`WALLS`), a profile on John's
  line (`PROFILE`).

## Before you start

- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/LESSONS.md` (all of it, but above all Checks, John's traces, and the
  2026-10-08 PhotoCraft entries under the Gerhard red-figure heading), `docs/redesign/drawings/README.md`
  (SVG format: 1000 units tall, `body` path then `lines` path), and the Drawings section of
  `docs/redesign/DESIGN.md` (John's file, untracked in the main checkout: never edit it).
- Branch: new `claude/redesign-plates-7` off `claude/redesign-plates-6` (it holds the newest LESSONS and
  the Trojan Women records), or off main if John has merged plates-6 by then. Own worktree
  `.claude/worktrees/redesign-plates-7`. Copy this file in as `docs/redesign/drawings/HANDOFF-plates-7.md`
  and commit it first. Commit as you go and push.
- Keep notes and `timing.txt` in `.remember/batch7/`. Python venv in your scratchpad (numpy, scipy,
  scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are installed.
- Helper scripts (outside git; copy them, don't edit the originals):
  - `.remember/batch5/scripts/`:
    - `sclose.py` (plate | drawing | dark | overlay close-ups; its cfg.json `box` must match the box the
      tool printed on THIS run)
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

## Show John

Start every message to him with "Clouds (PhotoCraft)". Send with SendUserFile:

- plate crop | light | dark at 400 and 120 px;
- the whole drawing at full width in both themes;
- the full-res red overlay (lines at about 55% opacity over the source);
- close-ups of the face and both hands at 4-6x (source | drawing | dark | overlay), plus the face on the
  pixel grid.

Look at all of them yourself first, at full size, for jagged or broken lines, for clay past the
outlines, and for the face against the photo. Ask his verdict with AskUserQuestion. He may answer by
marking a pixel grid or circling places on the overlay: map his marks exactly.

## Records, when he approves

- `tools/clouds.py` and `clouds.svg`.
- Fill the `clouds` entry in `docs/redesign/research/play-image-plan.json` (short house credit form, as
  the hippolytus and trojan-women entries), add to `drawings.json` and the README table, rerun
  `tools/contact_sheet.py`, and add a dated LESSONS.md entry (a new heading for photos drawn with
  PhotoCraft).
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly; no pytest in the venv).
- **No outside review unless John asks for one.** On Trojan Women: "IVE REVIEWED IT. ITS VISUAL. VERIFY
  CITATION YOURSELF". Check the credit against the museum's own record yourself, and quote your sources.
- Then stop and report: branch, commit, what John approved, the credit's sources.
