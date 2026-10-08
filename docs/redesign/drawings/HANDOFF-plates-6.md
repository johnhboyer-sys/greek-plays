# Handoff: Trojan Women plate drawing in PhotoCraft (Gerhard AV III Taf. CLXIX, 3-4), 2026-10-07

Make one line drawing for Euripides' *Trojan Women* from Gerhard, *Auserlesene griechische Vasenbilder* III
(Berlin 1847), Taf. CLXIX, nos. 3-4 (the bottom picture): Menelaus at Troy, his sword fallen at his feet,
between Helen (right, hand raised, lifting her skirt) and a companion fleeing (left). John picked it on
2026-10-07 17:33 and wants it made **with PhotoCraft**, in this fresh session. This file is all you need.

## Why this plate, and what went wrong before (read this)

The first Trojan Women attempt (black-figure, Taf. CCXIV, three women; branch `claude/redesign-plates-5`,
`.remember/batch5/notes.md`) was stopped by John: "looks like shit. lines are jagged. clay outside the arms",
then "i'm not really happy with the plate in general". What to carry over:

- **John does not want to trace.** "don't make me have to do this myself", "it's tedious work". Get the
  lines right yourself. Send him crops to judge, not to trace.
- **Lines must be smooth, even, unbroken.** "where black lines ... are broken, we join them"; "none of this
  rocky/patchy line"; "lines are jagged". Thresholding a scan gives grainy edges; skeleton-and-widen lines
  zigzag. Check every close-up at 4-6x for jagged edges before showing him.
- **Clay (the dark theme's `body` fill) must stop at the outlines**, never spill past them.
- **We trace the plate's printed lines**, not the edges of coloured areas ("we are tracing the black
  lines, not the white areas").
- Red-figure plates from this family went well with the house method: Hippolytus (Gerhard AV III Taf.
  CLXV, 4; `tools/hippolytus.py`) ~50 min, first-pass approval; Suppliant Women (Élite; `tools/suppliants_aesch.py`)
  ~35 min. The black ground gives the outline for free; interior lines by local contrast.

## PhotoCraft

John's instruction (2026-10-07): use PhotoCraft to make the drawing. Every image step should run in
PhotoCraft; small numpy glue for combining masks and measuring is fine (say so in the tool's docstring).

- CLI: `~/.local/bin/photocraft-cli` (0.2.0). `photocraft-cli commands [--json] [--filter x]` lists the
  748 engine commands with their params; `run <file> --cmd <id> --params '<json>' [--cmd ...] --out <file>`;
  `info <file> --compact`; `convert`. There is also an MCP mode (`photocraft-cli mcp`), not wired into Claude
  Code here; the CLI is enough.
- Commands that worked: `image.rotation.arbitrary {angle, direction}`, `image.crop {x,y,width,height}`,
  `image.imageSize {width,height,resample}`, `image.mode.grayscale`, `filter.noise.median {radius}`,
  `filter.blur.gaussianBlur {radius}`, `filter.other.highPass {radius}`, `image.adjustments.threshold {level}`,
  `select.colorRange {select:"sampledColors", points:[[x,y],...], fuzziness}` (also `"shadows"`),
  `select.modify.contract/expand {radius}`, `select.inverse`, `edit.fill {color}`, `filter.other.offset`,
  `layer.new.layer {name}`, `layer.quickExportAsPng {layer, path}`.
- **Vector output:** `select.colorRange {"select":"shadows"}` on a black-on-white mask, then
  `select.toWorkPath {tolerance}` and `path.info {"name":"work"}` returns the path as JSON (subpaths of
  knots with anchor/in/out Bezier handles, fillRule nonzero). At tolerance 0.5 it reproduces the mask pixel
  for pixel; at 2 it is about a third the size. Convert knots to SVG `C` segments
  (`batch5`'s `tools/trojan_women.py`, `work_path`, on branch `claude/redesign-plates-5`). Higher tolerance
  also smooths: try it as one way to get smooth lines.
- PhotoCraft's `.pcraft` files are what John opens (he has the app). If you ever hand him files, make them
  `.pcraft` with a named empty layer.

## Source (downloaded, OK'd by John)

- `/Users/johnboyer/Developer/greek-plays/.remember/batch6/src/gerhard1847bd3_169.jpg` (2078 x 2869), from
  https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_169.jpg/full/full/0/default.jpg
  (page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0216). Public domain (1847). Never commit it.
- Crop of the picture (research lane's estimate, check it): x 140, y 1380, w 1760, h 1160. Menelaus about
  1,050 px tall, the women about 1,000. Small previews: `.remember/sweep5-2026-10-07/previews/`.
- The vase, as the lane read it (verify before the credit; don't guess): British Museum E 263
  (1837,0609.71), Altamura Painter, red-figure belly amphora from Vulci, c. 470-450 BC; BM Catalogue of Vases
  III (1896) cites Gerhard AV III pl. 169, 3-4. The lane could not open the BM or Beazley pages (bot checks).
  Gerhard numbers the shape drawing and the painting separately: cite the figure you drew (LESSONS.md).
- Draw: the three figures, the shield, the fallen sword. Leave out: the plate number "4." and margin
  marks, the frame, any border band, any names on the ground. Nudity: none expected; the rule is draw as
  printed, only a comic costume phallus is out.

## Before you start

- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/LESSONS.md` (the Gerhard section, the Élite section, the checks), then
  `docs/redesign/drawings/README.md` (SVG format: 1000 units tall, `body` path then `lines` path, the
  plate's own weight) and the Drawings section of `docs/redesign/DESIGN.md` (John's file: never edit it).
  Read `tools/hippolytus.py` and `tools/suppliants_aesch.py` — your nearest models.
- Branch: new `claude/redesign-plates-6` off `claude/redesign-plates-3` (holds plates-1's linework changes,
  LESSONS.md and the Élite tools), in its own worktree `.claude/worktrees/redesign-plates-6`. Copy this file
  in as `docs/redesign/drawings/HANDOFF-plates-6.md` and commit it first. Commit as you go and push.
  Merging is John's call. Another session (Libation Bearers, `claude/redesign-plates-4b`) may be running:
  don't touch its branch, worktree or `.remember/batch4/`.
- Keep notes and `timing.txt` in `/Users/johnboyer/Developer/greek-plays/.remember/batch6/`. Python venv in
  your scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and rsvg-convert are
  installed.
- Helper scripts (outside git; copy, don't edit originals): `.remember/batch5/scripts/` has `sclose.py`
  (plate | drawing | dark | overlay close-ups rendered from the SVG; its cfg.json `box` must match the box the
  tool printed on THIS run — a stale box shifts the drawing against the plate), `showset.py` (400/120 px set,
  patched for SVGs with no potrace transform), `gaps.py`, `missed.py`, `map_pc.py` (reads a stroke layer out
  of a `.pcraft` file, no registration needed).

## Show John

Start every message to him with "Trojan Women (PhotoCraft)". Send with SendUserFile: plate crop | light |
dark at 400 and 120 px; the whole drawing at full width in both themes; close-ups of every face and hand
at 4-6x (plate | drawing | dark | overlay). Look at all of them yourself first, at full size, for jagged
or broken lines and for clay past the outlines. Ask his verdict with AskUserQuestion.

## Records, when he approves

`tools/trojan_women_menelaus.py` (or replace the batch-5 tool name if he prefers); `trojan-women.svg`. Fill
the `trojan-women` entry in `docs/redesign/research/play-image-plan.json` (short house credit form, as the
hippolytus entry), add to `drawings.json` and the README table, rerun `tools/contact_sheet.py`, add a dated
LESSONS.md entry on drawing with PhotoCraft. Rerun the tool: the SVG must come out byte for byte the same.
`tools/test_linework.py` and `tools/test_andromache_trace.py` pass. One cross-family review (Grok static
read via `grok-cc:grok-rescue`, or Codex GPT-6-Sol medium if Grok ≥90% on the board): overlay cut in
thirds, credit with sources quoted, findings only; check each finding against the plate and show John
before fixing. Then stop and report.
