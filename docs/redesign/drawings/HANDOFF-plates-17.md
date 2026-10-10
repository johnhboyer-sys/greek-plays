# Handoff: Wasps, a line drawing with PhotoCraft from a Getty photo, 2026-10-10

One session, one drawing. John picked it on Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD; record in
`.remember/sweep2-2026-10-04/rulings.md`: "Wasps | 32-8Ma | John 15:04 (Getty 96.AE.112)", 2026-10-09). Every image
step runs in PhotoCraft; John corrects in PhotoCraft. This file is all you need.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Wasps (Aristophanes), key 32-8Ma | J. Paul Getty Museum 96.AE.112, Apulian red-figure bell-krater, Rainone Painter, about 370 BC; museum photo (CC0, Getty Open Content) | `claude/redesign-plates-17`, `.claude/worktrees/redesign-plates-17` | `.remember/batch16/` |

Other sessions run now: R1 Medea (`claude/redesign-redo-r1`), plates-13 Phoenician Women, plates-14 Iphigenia at Aulis,
plates-15 Hecuba and Bacchae, plates-16 Wealth (`.remember/batch15/`). Don't touch their branches or folders.

## The source
- Object page: https://www.getty.edu/art/collection/object/10403Y. The front view is 7870 x 8247; a preview crop is in
  `.remember/sweep6-2026-10-08/page/` (`32-8Ma.jpg`; crop box in full px 1930 2380 5830 4880). Get the full image's
  link from the Getty's IIIF manifest or the object page; look for other views of the same side (a second view helps
  fit the vase's shape, as Medea and Philoctetes used). Your first message asks John to OK each download by name and
  size, and shows a crop of what the drawing will hold.
- The scene: two old men in comic masks, white-haired and bearded, stand either side of a small bearded figure (a
  slave) behind a patterned chest; the right-hand old man leads the small figure by the hand and holds a stick; a door
  and a column at the left. The old men are about 2,150 px tall, the small figure about 700. They touch hands and the
  chest: cut them as one group. Propose to John whether the door and column come too.
- Nudity: the small figure wears a costume phallus. Draw it as painted (John, 2026-10-09: "it's aristophanes. no
  censorship").
- The play: thematic only. Two old men and a slave are stock types Wasps uses (Philocleon and Bdelycleon, Xanthias);
  the vase names no play and is some fifty years later than Wasps (422 BC). Say so plainly in the record.
- Credit: check the Getty's own record (painter, date, provenance, inventory) and use the short house form (see the
  Clouds and Acharnians entries in `docs/redesign/research/play-image-plan.json`). CC0: the drawing carries no licence
  from the photo.

## Method
- A photo of a vase: flatten it first (`tools/vase_unroll.py`; John, 2026-10-02: trace from the photo taken off the
  curve, shear-free). The Getty TIFF/JPEG may carry no focal length: fit the cameras and profile to the vase's outline,
  a painted band or ground line, and points matched between views (SIFT), as `tools/medea.py` (on
  `claude/redesign-redo-r1`) and `tools/philoctetes.py` do. Read LESSONS' "Photos of vases" section all through.
- Models (approved): `tools/clouds.py` and `tools/acharnians.py` (photos of comic vases), `tools/philoctetes.py`
  (PhotoCraft, washes for hair and shadow), `tools/antigone.py` (PhotoCraft, John's corrections file). Masks, white
  hair and beards: read the Colonus entries (white curls as a light tone with the painter's dark marks as crisp strokes)
  and the Philoctetes ones (stepped `tone` washes).
- Every image step runs in PhotoCraft (`~/.local/bin/photocraft-cli`: `commands`, `run`, `convert`, `serve`); geometry
  may stay in numpy/scipy; say so in the docstring. The SVG is written by `linework.trace_svg`.
- Lines clean, crisp and even (John, 2026-10-10: "Nice and clean and crisp"; "distinguish between cracks and damage
  from the actual painted lines"; cracks leave no line). Faces, masks and hands first (each finger at 20x; eyes never
  heavy). Check the dark theme for holes in a figure's area.
- Corrections: a PhotoCraft file John marks, as for Antigone (LESSONS, 2026-10-10): the flat on your tool's grid, your
  lines in red on a layer at 70%, an empty layer "John corrections (blue = add, green = remove)". Build it with
  `photocraft-cli serve`. Over 30 MB it will not send to his phone: put a copy on his Desktop. Read his layer alone,
  keep it as `tools/wasps_marks_1.png`, apply ink = (ink less green) plus blue, and diff each new save against the last.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Read `docs/redesign/drawings/LESSONS.md` all of it, `docs/redesign/drawings/README.md` (SVG format), and the Drawings
  section of `docs/redesign/DESIGN.md` (John's file, untracked in the main checkout: never edit it).
- Branch off main in your own worktree. Copy this file in as `docs/redesign/drawings/HANDOFF-plates-17.md`, commit
  first, commit as you go, push. Merging is John's call. Before the records step, merge the latest main into your
  branch, keep every other entry, and rerun the contact sheet.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in `.remember/batch16/`; sources in `.remember/batch16/src/`
  (never committed). Python venv in your scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless);
  potrace and rsvg-convert are installed. Helper scripts (copy, don't edit): `.remember/batch5/scripts/`,
  `.remember/batch6/scripts/`, `.remember/redo-2026-10-09/r1/show.py`.

## Show John
Start every message with "Wasps (PhotoCraft)". Send with SendUserFile: source crop | light | dark at 400 and 120 px;
the whole drawing at full width in both themes; the full-res red overlay; close-ups of every face, mask and hand at
4-6x. Look at all of them yourself first, at full size. Ask his verdict with AskUserQuestion.

## Records, when he approves
- `tools/wasps.py` and `wasps.svg`.
- Fill the play's entry in `docs/redesign/research/play-image-plan.json` (keep its format: `json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), add to `drawings.json` and the README table, rerun `tools/contact_sheet.py`,
  and add a dated LESSONS.md entry under "Photos of vases".
- Rerun the tool: the SVG must come out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass (run them with python directly).
- No outside review unless John asks for one. Then stop and report: branch, commits, what John approved, the credit's
  sources.
