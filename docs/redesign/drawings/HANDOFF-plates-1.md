# Handoff: plate drawings, first pair (Andromache, Hippolytus), 2026-10-06

Make two line drawings from printed vase plates: *Andromache* (code 14n) and
*Hippolytus* (13m). John picked both sources on 2026-10-05
(`.remember/sweep2-2026-10-04/rulings.md`). These are the first of the 13
picked plates; they test the plate method on the two plate families most of
the batch uses (Furtwängler-Reichhold, Gerhard), so note what goes wrong.
John will review each closely. This file is all you need; the session that
wrote it is gone.

## Before you start

- Read `docs/redesign/DESIGN.md` (the Drawings section, line 71) and the end
  of `docs/redesign/decisions.md`. Both are untracked files in the main
  checkout, `/Users/johnboyer/Developer/greek-plays/docs/redesign/`; DESIGN.md
  is John's file, never edit it. Its "No nudity" line is older and stricter
  than his ruling: only the comic costume phallus is banned.
- Read `docs/redesign/drawings/README.md` (SVG format: `lines`, `body`,
  optional `tone`; house line weight; tools).
- Your model is the plate test from 2026-10-04:
  `.remember/sweep2-2026-10-04/test-fr44/maenad.py` (FR Taf. 44, done in
  7.5 minutes). It was written against the old
  `.claude/worktrees/redesign-drawings` copy of `linework.py`; import from
  your own worktree's `docs/redesign/drawings/tools/` instead (main's copy
  has the fringe fix and `open_holes`). Read its "Known limits" in
  `.remember/sweep2-2026-10-04/README.md`.
- Memory to read: drawings-trace-faces-hands, drawings-cracks-leave-no-line,
  drawings-show-the-plot, drawings-may-show-ending, nudity-only-comic-phallus-out,
  plain-drawing-credits, drawings-existing-line-drawings-first.

## Where to work

```
git -C /Users/johnboyer/Developer/greek-plays worktree add .claude/worktrees/redesign-plates-1 -b claude/redesign-plates-1 main
```

Copy this file into the branch as
`docs/redesign/drawings/HANDOFF-plates-1.md` and commit it first. Commit as
you go and push to `claude/redesign-plates-1`. Merging is John's call.

Make a venv in your scratchpad (`numpy scipy scikit-image pillow`; add
`opencv-python-headless` only if you need it); `potrace` and `rsvg-convert`
are installed. Sources are never committed. The scratchpad and /tmp are
wiped at reboot, so keep the source scans and notes in
`/Users/johnboyer/Developer/greek-plays/.remember/batch1-2026-10-06/`
(gitignored). The disk had 7 GB free on 2026-10-06: crop the 6734 px scan
before scaling it up.

## Downloads

John OK'd these downloads on 2026-10-05 08:52 ("downlaod those"); the copies
fetched then are gone. Fetch exactly these two files and nothing else. Any
other download needs his OK first.

1. 14n: https://digi.ub.uni-heidelberg.de/iiif/2/furtwaengler1904bd1%3A061_Tafel_34_1_Exemplar.jpg/full/full/0/default.jpg
   (6734 x 5505; page https://digi.ub.uni-heidelberg.de/diglit/furtwaengler1904bd1/0059)
2. 13m: https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1847bd3%3A190a_Tafel_ROEM_165.jpg/full/full/0/default.jpg
   (2078 x 2869; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1847bd3/0212)

Both public domain (1904, 1847).

## 1. Andromache (14n)

- Plate: Furtwängler and Reichhold, *Griechische Vasenmalerei* I (1904),
  Taf. 34, Heidelberg's second copy. Vase: the Vivenzio hydria, Kleophrades
  Painter, c. 480 BCE, Naples, Museo Archeologico Nazionale 2422 (Heydemann
  number; check it against the FR text p. 201 ff. or the Beazley Archive
  before writing the credit).
- Subject (John: "as proposed"): Neoptolemos killing old Priam, who sits on
  the altar with the dead Astyanax across his lap; the palm behind. The
  play's backstory: Neoptolemos is Andromache's master, Astyanax her son.
- Crop measured by the picking worker, full-scan px (x, y, w, h):
  `2960, 2525, 1420, 1605`. Neoptolemos is about 1,440 px tall (crest 2605,
  heel 4044).
- The hard parts:
  - **No black ground.** This copy prints black lines on grey-brown paper,
    so the maenad's trick (the ground gives the outline) does not work. The
    figure's edge must come from cuts along its own lines (`livewire`, as in
    `tools/pythia.py` and `tools/iphigenia.py`, both cut from printed
    plates).
  - **The group is crowded.** The kneeling Greek touches Neoptolemos' back
    (helmet and face cut by the crop's right edge; the scabbard tip reaches
    his skirt); another figure's raised arm overlaps the back of the helmet;
    the ring ornament touches the crest; a fallen half-nude Trojan lies under
    Neoptolemos' legs; another fallen head lies under the child's garment.
    Decide what is in and what is out, and say so when you show John: the
    worker judged the fallen man can't be left out because his body and
    Neoptolemos' rear leg overlap.
  - Astyanax is bare; at native size no genitals are drawn (a small mark at
    the hip reads as fingers). Check it yourself at 20x. Nudity is fine
    either way; only a comic costume phallus is out.

## 2. Hippolytus (13m)

- Plate: Gerhard, *Auserlesene Vasenbilder* III (1847), Taf. CLXV, titled
  "Theseus und Antiope"; text pp. 46-50 (read it for the vase's museum and
  shape: the worker did not). Red figures on black, two panels.
- Subject: the lower panel's Amazon (patterned dress, leggings, soft cap,
  bow in one hand, double axe raised in the other) fighting the hoplite at
  the left (crested helmet, bare chest, mantle, short chiton, shield,
  spear). The play's backstory: Hippolytus' mother is the Amazon taken by
  Theseus. Whether the plate's identification holds is not our call; the
  credit says what Gerhard titles it.
- Crop (x, y, w, h): `160, 1243, 1030, 1252`. Hoplite 1,202 px, Amazon
  1,180 px.
- The hard parts: his shield overlaps her chest and bow arm, his spear tip
  touches her bow hand, her front leg crosses his rear leg (draw both whole).
  At the crop's right edge a sliver of the second hoplite (shield rim, spear
  shaft, toes) comes in: cut it out cleanly. His spear point ends behind her
  skirt (about x 1040), inside the crop: erase it and join her lines across
  it. The axe head and an inscription sit near the right edge; inscriptions
  stay out.
- Black ground, so the maenad method applies directly.

## The method (both)

- Lines are the plate's own lines, drawn even at the house weight; solid
  black where the plate paints solid (hair, dark patterns). No washes.
- Faces and hands: check every finger, eye and lip at 20x against the plate;
  every finger a closed outline. John looks hardest here. If one won't come
  clean, offer him a trace rather than guess.
- A line broken by a crease, foxing or a printing flaw: join the line, draw
  nothing along the flaw.
- Each tool's `main()` takes an optional QA path and writes `qa_overlay`
  (any grey left showing is a missed line) and `qa_dark`. Rerun the
  committed tool before showing John; the SVG must come out byte for byte the
  same.
- Time each drawing (start, done), as `timing.txt` did for the maenad: the
  rest of the batch is planned from it.

## Show John

For each drawing: plate crop | light | dark, at 400 px and 120 px (the
contact-sheet sizes), plus the overlay. Send with SendUserFile. Name what
you left in or out of the crop and why. Draw one, show it, then the other;
don't build the second on a method he hasn't seen.

## Records, when he approves

- `tools/andromache.py`, `tools/hippolytus.py`; `andromache.svg`,
  `hippolytus.svg`.
- Fill the `plays` entries (`work_id` "andromache", "hippolytus") in
  `docs/redesign/research/play-image-plan.json`: `source_file`, `credit`,
  `license`, `crop`, `alt_text`, `shows`, `method`, `result`, `status`,
  `final_image`. Credit in the short house form.
- Add both to `drawings.json` and the README table; rerun
  `tools/contact_sheet.py`.

## Review

Implementation and review are never the same model family. Check the
budget board at session start: on 2026-10-06 Codex was benched
(credits depleted) and Grok had the most headroom, so the cross-family
review goes to Grok (grok-cc companion, a static read with the QA images cut
into thirds). Keep it to real faults: missed lines, lines along flaws, wrong
museum or inventory numbers. One review for the pair, not one per pass.

## Done means

Both drawings approved by John, records filled, contact sheet rebuilt,
cross-family review run and its fixes made, branch pushed, tests in
`tools/test_linework.py` still pass. Then stop and report; the next pair
waits for John.
