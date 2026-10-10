# Handoff: two plate drawings with PhotoCraft, Heracles and Ion, 2026-10-09

Make two line drawings, one after the other, from 19th-century plates John picked on 2026-10-08 (Plate Picks
page, https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD; record in
`.remember/sweep2-2026-10-04/rulings.md`, "John's picks from Plate Picks"). Both are coloured lithographs,
red figures on a black ground. Every image step runs in PhotoCraft; John corrects on a pixel grid. This file
is all you need.

1. **Heracles** (Euripides), key 18-6Ea: Gerhard, *Trinkschalen und Gefässe des Königlichen Museums zu
   Berlin* II (Berlin, 1850), Taf. XXI, the LEFT panel: Herakles in a lion-skin cap and cloak drawing his
   bow, quiver and shield behind him, alone in his panel. Do him first: one figure.
2. **Ion** (Euripides), key 7-6Ea: Lenormant and de Witte, *Élite des monuments céramographiques* II
   (Paris, 1857 at latest), pl. XLVI: Apollo seated on the Delphic tripod with a bowl and a bow, between
   the Pythia (with a jug) and Manto (with a laurel sprig). The three stand clear of one another.

## The sources (both Heidelberg, public domain; ASK JOHN TO OK THE TWO DOWNLOADS in your first message)

- Heracles: https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1850bd2%3AV_Tafel_21.jpg/full/full/0/default.jpg
  (2950 x 2311; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1850bd2/0055). The preview crop, in
  full-scan px (x0 y0 x1 y1): 24 116 1362 1932. Herakles is 1,460 px head to foot, 1,640 with the bow.
  The right panel (Poseidon) is not drawn. Leave out the panel frame and the meander base.
- Ion: https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1857bd2%3A455a_Planche_046.jpg/full/full/0/default.jpg
  (1720 x 2728, printed sideways: rotate 90 clockwise; page
  https://digi.ub.uni-heidelberg.de/diglit/lenormant1857bd2/0568). The preview crop, in full-scan px of the
  unrotated scan: 168 364 1523 2309. Apollo with the tripod is about 1,225 px.
- Save them to `.remember/batch11/src/` (gitignored); never commit them. Read the licence in each volume's
  IIIF manifest (`https://digi.ub.uni-heidelberg.de/diglit/iiif/<record>/manifest.json`); Heidelberg's
  viewer pages sit behind a bot check, but IIIF image links open in the browser pane.
- Before drawing, decide with John what each drawing holds. Proposals: Heracles alone with his bow
  (whole, as printed); Ion the whole group of three (DESIGN.md: whole figures only, no fragments of
  neighbours), or Apollo on the tripod alone if John prefers. One line each, with a crop image.

## The plays and the credits

- Heracles: Herakles the archer; in the play he kills his sons with his bow in his madness, and a
  messenger tells it. Nude under the cloak with a small phallus drawn: draw it as printed (John,
  2026-10-05/08: only a grotesque comic costume phallus is left out; ask on anything else unclear).
- Ion: Apollo and the Pythia at Delphi, where Ion is set; the Pythia is a character of the play. The
  plate's title reads the third woman as Manto. Apollo's chest is bare.
- Read each plate's own text (Gerhard's Trinkschalen text for Taf. XXI; Lenormant and de Witte's text for
  pl. XLVI) for what they say the vase is, where it was, and who they name. Then find where the vase is now
  (the Trinkschalen vases are Berlin's: look for the Antikensammlung number; the Élite vase may be in Paris
  or lost). Check the credit against the museum's own record and the publication's text yourself and quote
  your sources (on Trojan Women the publication had the museum wrong). If a fetch hits a bot check, open
  the page in the browser pane.

## Method: red figures on black (the family that goes well)

- Read `docs/redesign/drawings/LESSONS.md` all of it, above all: "Gerhard, *Auserlesene griechische
  Vasenbilder*" (the Trinkschalen plates are Gerhard's lithographs of the same kind, coloured, red figures
  on black; compare the scan with an AV plate before you assume the same settings), "Lenormant and de
  Witte, *Élite*", the PhotoCraft entries of 2026-10-07/08, "Checks that caught real faults", and "John's
  traces".
- Models: `tools/trojan_women_menelaus.py` (Gerhard AV, PhotoCraft, approved 2026-10-08; its `pc()`
  helper, `faint_lines`, `join_breaks`) for Heracles; `tools/suppliants_aesch.py` (Élite, approved on the
  first pass) and `tools/alcestis.py` (Élite; the dark-theme fixes: the outline capped at 0.6 of a thin
  part's half-width, all the ground marked open; `level` if the frame bends) for Ion.
- Both plates' preview crops looked clean (no gutter, fold or stain across the figures). Check at full
  size anyway; Élite plates are often printed sideways and some carry a centre crease.

## What carries over from the last plates (Trojan Women, Clouds, Acharnians; all approved 2026-10-08)

- **John does not want to trace.** Get the lines right yourself; send him things to judge, not to draw.
- **Lines smooth, even, unbroken.** Faint lines print as dotted runs: find them by local contrast, draw
  each along a curve fitted to it, and join the pieces of one line across the gaps. Check every close-up
  at 4-6x for jagged or broken lines before you show him.
- **Clay (the dark theme's `body` fill) stops at the outlines.** Mark everything outside the figure as
  open (`held = ~fig`), or trace_svg's clay rims stray onto the ground.
- **Trace the printed lines**, not the edges of coloured areas.
- **Faces and hands are where John looks first.** Check each finger at 20x; eyes never heavy.

## Corrections: use the pixel grid (John, 2026-10-07: "showing the pixels is the most helpful way to give corrections")

When John flags a spot, or before you show him a face or hand you are unsure of, send him the source's
pixels at about 20x with a labelled 1 px grid (every 5th line blue, coordinates in yellow) and the
drawing's ink over it in translucent red. He draws on it: **red = where ink goes, green = ground (not
ink)**. Map his marks cell by cell (source px = x0 + image px / 20) and put the line exactly there. Read
his marks literally; if what he means is unclear, ask in one line before you run anything. Script:
`.remember/batch6/scripts/pxgrid.py` (svg, source image, cfg.json, x0 y0 x1 y1, K, out); build the grid on
the image your tool works from (rotated, if it is). He may also correct in PhotoCraft over a full-res
export (a PSD; blue = add, green = remove; read it with `photocraft-cli convert`; LESSONS, John's traces).

## PhotoCraft

John's instruction (2026-10-07): every image step runs in PhotoCraft; small numpy glue for combining masks
and measuring is fine (say so in the tool's docstring). Geometry (rotating, levelling) may stay in
numpy/scipy; say so. The SVG is still written by `linework.trace_svg`.
- CLI: `~/.local/bin/photocraft-cli`. `commands [--json] [--filter x]`; `run <file> --cmd <id> --params
  '<json>' [--cmd ...] --out <file>`; `info`; `convert`. MCP: `photocraft-cli mcp` on stdio.
- Commands that worked: `image.crop`, `image.imageSize`, `image.mode.grayscale`,
  `filter.blur.gaussianBlur`, `filter.other.maximum` / `minimum` (preserve "squareness"),
  `image.adjustments.threshold`, Channel Mixer monochrome for clay against glaze (LESSONS),
  `image.rotation.arbitrary`, `filter.noise.median`, `filter.other.highPass`, `select.colorRange`,
  `select.toWorkPath` + `path.info`.
- If you hand John files to mark up in PhotoCraft, make them `.pcraft` with a named empty layer.

## Before you start

- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/README.md` (SVG format: 1000 units tall, `body` path then `lines` path) and
  the Drawings section of `docs/redesign/DESIGN.md` (John's file, untracked in the main checkout: never
  edit it).
- Branch: new `claude/redesign-plates-11` off main, in its own worktree
  `.claude/worktrees/redesign-plates-11`. Copy this file in as `docs/redesign/drawings/HANDOFF-plates-11.md`
  and commit it first. Commit as you go and push. Merging is John's call.
- Other drawing sessions may run at the same time (Ajax on plates-8, Lysistrata on plates-9): don't touch
  their branches, worktrees or `.remember/batch*/` folders. You all fill the same record files: before the
  records step, merge the latest main into your branch, keep every other play's entry, and rerun the
  contact sheet.
- Keep notes and `timing.txt` (start and end of each drawing, each pass) in `.remember/batch11/`. Python
  venv in your scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and
  rsvg-convert are installed.
- Helper scripts (outside git; copy them, don't edit the originals): `.remember/batch5/scripts/`
  (`sclose.py`, `showset.py`, `gaps.py`, `missed.py`) and `.remember/batch6/scripts/` (`pxgrid.py`,
  `redover.py`, `full.py`, `claycheck.py`, `circles.py`, `clsbox.py`, `leak2.py`). Their crop constants
  are batch 6's: set them for your tool.

## Show John

Start every message to him with "Heracles (PhotoCraft)" or "Ion (PhotoCraft)". Send with SendUserFile:
- source crop | light | dark at 400 and 120 px;
- the whole drawing at full width in both themes;
- the full-res red overlay (lines at about 55% opacity over the source);
- close-ups of every face and hand at 4-6x (source | drawing | dark | overlay), plus each face on the
  pixel grid.
Look at all of them yourself first, at full size, for jagged or broken lines, for clay past the outlines,
and for the faces against the source. Ask his verdict with AskUserQuestion. Finish Heracles (approved and
recorded) before starting Ion, unless John says otherwise.

## Records, when he approves each

- `tools/heracles.py` and `heracles.svg`; `tools/ion.py` and `ion.svg`.
- Fill the `heracles` and `ion` entries in `docs/redesign/research/play-image-plan.json` (short house credit
  form, as the hippolytus and trojan-women entries; John: "overthinking the credit"), add to
  `drawings.json` and the README table, rerun `tools/contact_sheet.py`, and add dated LESSONS.md entries
  under each plate family's heading (a new heading for the Trinkschalen plates if they differ from AV).
- Rerun each tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly).
- **No outside review unless John asks for one** (Trojan Women: "IVE REVIEWED IT. ITS VISUAL. VERIFY
  CITATION YOURSELF").
- Then stop and report: branch, commits, what John approved, each credit's sources.

## Prompt to start the session

> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch11/HANDOFF.md` and follow it: two line
> drawings with PhotoCraft, Heracles (Gerhard, Trinkschalen II, Taf. XXI, left panel) and then Ion (Élite
> II, pl. XLVI), on a new branch `claude/redesign-plates-11`. Your first message to me asks me to OK the
> two Heidelberg downloads and proposes what each drawing holds.
