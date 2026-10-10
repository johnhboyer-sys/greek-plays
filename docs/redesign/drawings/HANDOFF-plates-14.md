# Handoff: Iphigenia at Aulis (Artemis, Élite II pl. XC), paused 2026-10-10 ~12:10

## State
- Helen (session A of batch 12) is done: approved by John, records committed, branch `claude/redesign-plates-12`
  pushed (last commit 06d2169), NOT merged (merging is John's call). Worktree `.claude/worktrees/redesign-plates-12`
  still exists. Phoenician Women is session B's (`claude/redesign-plates-13`), not ours.
- Next play, John: "On to next one". Chosen: Iphigenia at Aulis, pick 20-6Eb ("Artemis drawing her bow"):
  Lenormant and de Witte, Élite II (1857), pl. XC, Artemis alone (the woman with the infant on the other leaf
  is left out). Card: `.remember/sweep6-2026-10-08/page/crops6.json` key 20-6Eb.
- Crop preview sent to John: `preview_artemis.jpg` (this folder). The download question was asked; John's answer
  was "pause so i can restart computer". Download NOT yet OK'd: ask again first.

## The source
- Scan: https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1857bd2%3A455a_Planche_090.jpg/full/full/0/default.jpg
  (3475 x 2853, a double leaf printed upright; a faint crease between the figures; page
  https://digi.ub.uni-heidelberg.de/diglit/lenormant1857bd2/0618). Licence PDM 1.0 (manifest checked 2026-10-10).
- Artemis in full-scan px roughly x 320-1810, y 330-2340 (from the preview at 1/3.47, offset 180,239).
- Save to `src/` here (gitignored).

## Plan
- New branch `claude/redesign-plates-14` in worktree `.claude/worktrees/redesign-plates-14` off main.
- Tool `tools/iphigenia_aulis.py` from `tools/helen.py` (same plate family; read LESSONS' 2026-10-10 Helen entries):
  level (the double leaf may need alcestis-style levelling across the fold: check the frame's edges), weight own,
  dots by dark core (her dress is covered in dots), eyes and small marks via `dots`, outlines on the ground.
  The bowstring crosses open ground: measure its centre (heracles.py `STRINGS`, `bow_edge`) and pass as
  `rim_lines`; the arrow/quiver thin parts may need `keep`.
- Credit: read the Élite II text for pl. XC (list of plates on pages I-X, then the text), find the vase now
  (Beazley Archive record via the browser pane: www.beazley.ox.ac.uk/record/...; AGORHA cites Élite plates too).
  The sweep note says the editors read the infant as Iphigenia (doubtful).
- Scratch tools from session A (look.py, leak.py, bodycheck.py, sc.json) were in the old scratchpad and are
  gone; batch5/batch6 scripts remain (pxgrid, sclose, showset, full, gaps; redover needs its X0.. constants).
