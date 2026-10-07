# Handoff: plate drawing, Libation Bearers (Gerhard, Taf. XXIV), 2026-10-07

Make one line drawing from Gerhard's *Etruskische und kampanische
Vasenbilder des Königlichen Museums zu Berlin* (Berlin, 1843), Taf. XXIV:
Orestes killing Aegisthus, for Aeschylus' *Libation Bearers* (code 06n).
John picked it on 2026-10-05, "WHOLE frieze"
(`.remember/sweep2-2026-10-04/rulings.md`). This file is all you need; the
session that wrote it is gone.

## This is a test

John runs two sessions on this same plate, at different effort levels, to
compare them. His first message gives you your label, A or B; if it doesn't,
ask him before you do anything else. Your label goes into your branch, your
folder and every message to him (below).

- Work on your own: never open the other session's branch, worktree, folder
  or notes, and don't compare yourself with it.
- Only one of the two branches will be merged. Write yours as if it will be.
- Keep `timing.txt` as you go (below): it is the test's record.

## Before you start

- Read `docs/redesign/drawings/LESSONS.md` first: what the earlier plates
  taught, how John traces, how blood is drawn, the checks that caught real
  faults. This plate needs the Élite section (2026-10-07) most: the plate's
  own line weight for a wide drawing, faces at the paint's own width, thin
  parts and open ground on the dark theme, checking every fact in the
  credit. Then `docs/redesign/drawings/README.md` (the SVG format, the tools)
  and the Drawings section of `docs/redesign/DESIGN.md` (John's file: never
  edit it).
- Nudity: draw it as printed (John, 2026-10-05). The rulings table still says
  "hide Aegisthus' penis"; John reversed that the same morning, and
  DESIGN.md's "No nudity" line is older and stricter. Aegisthus' small
  penis, drawn in thin line in the gap of his drape, stays.
- Your models: `tools/suppliants_aesch.py` (the Élite, red figures on black,
  a wide drawing of two figures: about 35 minutes, approved on the first
  pass) and `tools/hippolytus.py` (Gerhard, the same kind of plate).
  `tools/alcestis.py` holds two dark-theme fixes worth copying (in `draw`:
  the outline capped at 0.6 of a thin part's half-width; all the ground
  marked open), and `level`, should the scan's frame bend.
- Branch: if `claude/redesign-plates-3` has been merged into main, branch off
  main; if not, branch off `claude/redesign-plates-3` (it holds plates-1's
  linework changes and LESSONS.md, the Élite tools and the Élite lessons).
  New branch `claude/redesign-plates-4a` or `claude/redesign-plates-4b`, by
  your label, in its own worktree (`.claude/worktrees/redesign-plates-4a`
  or `-4b`). Copy this file into the branch as
  `docs/redesign/drawings/HANDOFF-plates-4.md` and commit it first. Commit
  as you go and push. Merging is John's call.
- Sources are never committed. Keep them in
  `/Users/johnboyer/Developer/greek-plays/.remember/batch4/<label>/src/`
  (`a` or `b`; gitignored), with `notes.md` and `timing.txt` in
  `.remember/batch4/<label>/`. Build a Python venv in your scratchpad
  (numpy, scipy, scikit-image, pillow, opencv-python-headless); potrace and
  rsvg-convert are installed.
- Helper scripts, outside git; copy and adapt them, don't edit the
  originals: `.remember/batch3/scripts/` (`sclose.py`, close-ups rendered
  straight from the SVG: plate | drawing | dark | overlay; `showset.py`, the
  set for John at 400 and 120 px; `zoom.py`, ruled close-ups of the plate;
  `gaps.py`, line ends facing each other across short gaps; `missed.py`,
  plate lines the drawing misses) and `.remember/batch1-2026-10-06/scripts/`
  (mapping John's traces).
- Check the model budget board at session start. Load the `delegate` skill
  before your first subagent spawn.

## Source: fetch exactly this file and nothing else

John OK'd it on 2026-10-05. Any other download needs his OK first.

- 06n: https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843%3AT_24.jpg/full/full/0/default.jpg
  (3510 x 2590; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843/0071)

Public domain (1843). Heidelberg's viewer pages sit behind a bot check: read
the licence in the volume's IIIF manifest
(`https://digi.ub.uni-heidelberg.de/diglit/iiif/gerhard1843/manifest.json`),
and open IIIF image links in the browser pane to read the text pages
(viewing a page is not a download).

## The plate

- The vase, as the picking worker read it (check it): a red-figure stamnos
  from Vulci, bought by Bunsen in 1832, in Berlin (no. 1007 in Gerhard's
  catalogue); text pp. 35-37. Its present Berlin inventory number and its
  painter were not looked up. Find them before you write the credit (the
  Berlin museums' online collection, the Beazley Archive, the CVA, read on
  the web); don't guess. Read the plate's margins for a signature.
- The scene: Clytemnestra at the left, in a pleated dress, raising an axe;
  Orestes, in helmet, cuirass and short skirt, stabbing Aegisthus, who sits
  wreathed on a throne, his feet on a footstool; Electra at the right, one
  hand at her head, the other arm held out. Red figures on black; every
  fold, hair line, hand and pattern is drawn.
- The picture, measured by the picking worker in the full scan (x, y, w, h):
  `584, 409, 2394, 1358`, borders included. The group is 1,243 px tall (axe
  top 469 to feet 1712). It is one plate on one leaf, photographed open:
  check that the frame's edges run straight before you draw; if they bend,
  level the scan first.
- Draw: the whole frieze, the four figures with the throne and the
  footstool, as one drawing (they are one linked group: Clytemnestra's hem
  lies under Orestes' rear foot, and Orestes' arms lock with Aegisthus').
- Leave out: the tongue band along the top (the axe head meets it: cut
  along the band's lower edge and keep the axe whole); the meander along
  the bottom (the feet and the footstool stand on it: cut along its top
  edge); the names painted on the ground (ΟΡΕΣΤΕΣ above Orestes' arm,
  letters by Aegisthus and at the top left: they drop out with the ground;
  check that none joins a figure); the drawing of the vase's shape below
  the frieze; the plate's number and signature.
- The hard parts:
  - Where Orestes and Aegisthus lock together: Orestes' left hand at
    Aegisthus' head, his sword hand at Aegisthus' chest, Aegisthus' arms.
    Check every face and hand at 20x against the plate, each finger a
    closed outline. Electra's open hand comes within about 80 px of
    Orestes' hand but does not touch it.
  - Blood runs down Aegisthus' chest from the wound, printed a darker red.
    Draw it as LESSONS.md's Blood section says (a wash in the line colour,
    the lines black through it), and show John close-ups before you settle
    it.
  - Close lines: Clytemnestra's pleats, Orestes' skirt and scale cuirass,
    the throne's palmettes and rosettes, Electra's zigzag borders. The
    frieze is wide (about 1.75 to 1), so the house weight would run them
    together: start at the plate's own weight and show John.
  - Eyes and fine face lines: never heavy (John, 2026-10-07: "Be sure not to
    use too heavy of a line on fine details like eyes"). Draw them from the
    plate's paint at its own width.

## The method

As in LESSONS.md. In short: the plate's own lines; solid black where the
plate paints solid; no washes but the blood. Check every face and hand at
20x against the plate; if one won't come clean, offer John a trace and send
him crops at 3-6x. A crack, a stain or a printing flaw gets no line. Before
you show John: look at the dark theme close up (thin parts keep their clay,
no clay strays onto the ground), run `gaps.py` and `missed.py` and look at
what they find, and rerun the committed tool: the SVG must come out byte for
byte the same.

## Show John

Start every message to him with "Libation Bearers (A)" or "Libation
Bearers (B)": he has several sessions open. Send, with SendUserFile: plate
crop | light | dark at 400 px and 120 px; the overlay; close-ups of every
face and hand, rendered straight from the SVG at the close-up's scale (plate
| drawing | dark | overlay). Name what you left in or out and why. Ask for
his verdict with AskUserQuestion. Fix what he asks, and show him again.

## Records, when he approves

- `tools/libation_bearers.py`; `libation-bearers.svg`.
- Fill the `plays` entry (`work_id` "libation-bearers") in
  `docs/redesign/research/play-image-plan.json`: `proposed_subject`,
  `status`, `source_candidate`, `final_image`, `credit`, `license`, `crop`,
  `alt_text`, `source_file`, `shows`, `method`, `result`. The entry now holds
  an older candidate (a photo in Madrid): replace it. Credit in the short
  house form: follow the hippolytus, andromache, suppliants-aesch and
  alcestis entries. The SVG's `desc` in the same short form.
- Add it to `drawings.json` and the README table; rerun
  `tools/contact_sheet.py`. Add what you learned to LESSONS.md, dated, under
  a new heading for Gerhard's *Etruskische und kampanische Vasenbilder*.

## Review

One cross-family review (Claude never reviews Claude's work): a Grok static
read (Sonnet→Grok through `grok-cc:grok-rescue`), or Codex if the budget
board shows Grok at 90% or more. Give it the overlay cut into thirds and the
credit with its sources quoted into the brief; nothing for it to run,
findings only. Ask it three questions about the images whose answers you
know, so you can tell it really looked. Real faults only: missed lines,
lines along flaws, wrong facts. Don't apply its findings yourself: check
each against the plate, show John crops of the ones that hold up, and fix
only what he approves.

## For the test: timing.txt and notes.md

- `timing.txt`: one line each, with the clock time: start; downloads done;
  first run; each pass shown to John (what changed since the last);
  John's words at each verdict; approved; records done; review back; done.
- At the end, put a short summary at the top of `notes.md`: how many passes
  John saw, what he corrected, what took longest, and anything you would do
  differently.

## Done means

The drawing approved by John, records filled, contact sheet rebuilt, review
run and the fixes he approved made, LESSONS.md updated, branch pushed,
`tools/test_linework.py` and `tools/test_andromache_trace.py` pass, the
committed tool reruns byte for byte. Then stop and report.
