# Handoff: plate drawings, third pair (Suppliant Women, Alcestis), 2026-10-06

Make two line drawings from Lenormant and de Witte's *Élite des monuments
céramographiques*: Aeschylus' *Suppliant Women* (code 03n) and *Alcestis*
(11n). John picked both sources on 2026-10-05
(`.remember/sweep2-2026-10-04/rulings.md`). These are the first plates from
the Élite, so note what goes wrong. Another session draws a Gerhard pair
(batch 2) at the same time: read "Working alongside batch 2". This file is
all you need; the session that wrote it is gone.

## Before you start

- Read `docs/redesign/drawings/LESSONS.md` first: what the first pair
  (Hippolytus, Andromache) taught, how John traces, the checks that caught
  real faults. Then `docs/redesign/drawings/README.md` (the SVG format, the
  tools) and the Drawings section of `docs/redesign/DESIGN.md` (John's file:
  never edit it). DESIGN.md's "No nudity" line is stricter than John's later
  ruling (2026-10-05): draw nudity as printed; only the comic costume phallus
  is out.
- Your model: `tools/hippolytus.py` (a printed plate of red figures on
  black, where the black ground gives the outline: about 50 minutes,
  approved on the first pass). Both Élite plates here are red figures on
  black too.
- Branch: if `claude/redesign-plates-1` has been merged into main, branch off
  main; if not, branch off `claude/redesign-plates-1` (it holds the linework
  changes this work needs: `rim_lines`, `dots`, `weight="drawn"`, and
  LESSONS.md). New branch `claude/redesign-plates-3`, in its own worktree.
  Copy this file into the branch as
  `docs/redesign/drawings/HANDOFF-plates-3.md` and commit it first. Commit as
  you go and push. Merging is John's call.
- Sources are never committed. Keep them in
  `/Users/johnboyer/Developer/greek-plays/.remember/batch3/src/` (gitignored),
  with `notes.md` and `timing.txt` beside them. Build a Python venv in your
  scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless);
  potrace and rsvg-convert are installed.
- Batch 1's helper scripts (sharp close-ups, mapping John's traces):
  `/Users/johnboyer/Developer/greek-plays/.remember/batch1-2026-10-06/scripts/`.
  They hold Andromache's paths and constants: copy and adapt them; don't
  edit the originals.
- Check the model budget board at session start. Load the `delegate` skill
  before your first subagent spawn.

## Sources: fetch exactly these three files and nothing else

John OK'd these downloads on 2026-10-05. Any other download needs his OK
first.

1. 03n: https://digi.ub.uni-heidelberg.de/iiif/2/lenormant1858bd3%3A303_Planche_ROEM_020.jpg/full/full/0/default.jpg
   (1976 x 2871; page https://digi.ub.uni-heidelberg.de/diglit/lenormant1858bd3/0341)
2. 11n, left leaf (Apollo): https://iiif.archive.org/iiif/gri_33125009347440$637/full/full/0/default.jpg
   (2436 x 3000)
3. 11n, right leaf (Admetus): https://iiif.archive.org/iiif/gri_33125009347440$638/full/full/0/default.jpg
   (2342 x 3000; page https://archive.org/details/gri_33125009347440/page/n637/mode/1up)

Public domain (1858, 1846). Before you write the credits, read Heidelberg's
licence mark on its page, and the Internet Archive item's rights statement
(it is the Getty Research Institute's copy).

## 1. Suppliant Women (03n): draw this first

- Plate: Lenormant and de Witte, *Élite des monuments céramographiques* III
  (Paris, 1858), pl. XX; text p. 55. Vase: a Nola amphora, formerly in the
  Durand collection, then M. Paravey's, Paris (per the plate list); where it
  is now was not looked up. Read the text, and try to find the present
  location before you write the credit.
- Subject (John: "as proposed (Amymone and Danaus; cut off Poseidon)"):
  Amymone, running, in chiton and mantle, hands out; Danaus, bearded, in a
  himation, with a staff. Red figures on black. The play's link: Amymone is
  one of the Danaids; Danaus is a character in the play.
- The plate is printed sideways: rotate the scan 90 degrees clockwise (IIIF
  rotation 90 gives it upright). Crop measured by the picking worker, in the
  unrotated scan (x, y, w, h): `256, 143, 1328, 1643`; in the upright frame,
  x 1085-2728, y 256-1584. Danaus 1,212 px tall, Amymone about 1,200.
- The hard parts:
  - Poseidon, nude, strides in at the left: he is out. A strip of his cloak,
    his bare forearm and hand reaching toward Amymone, the lower end of his
    trident shaft (it stops about 60 px short of her sleeve) and the toes of
    his front foot (they touch her left foot at the lower left) come into the
    crop: cut them off cleanly and join her lines across where his toes met
    her foot.
  - Amymone and Danaus don't touch (her raised mantle tip and his pointing
    fingertip are about 45 px apart): one drawing holds both.

## 2. Alcestis (11n): ask John one thing first

- Plate: Lenormant and de Witte, *Élite* II (Paris, 1846), pl. LIV, a plate
  printed across two leaves; text p. 160. Vol. II is not at Heidelberg: the
  scan is the Getty copy on the Internet Archive, item
  `gri_33125009347440`, leaves 637 and 638. Vase: a Nola amphora, Blacas
  collection per the plate list (now the British Museum: not checked; check
  before you write the credit).
- Subject (John: "as proposed (Apollo; Admetus on his horse)"): on the left
  leaf, Apollo Nomios, a youth in a mantle with a laurel wreath and a staff,
  beside a cow and a bare tree; on the right leaf, Admetus, wreathed, in a
  mantle, riding a bridled horse. Red figures on black. The play's
  backstory: Apollo served Admetus as his herdsman (prologue, lines 1-9).
- Crops (x, y, w, h): leaf 637, `992, 695, 1444, 1480` (Apollo 1,135 px,
  wreath to toe); leaf 638, `0, 757, 1441, 1423` (Admetus and the horse
  1,340 px, wreath to hoof).
- The hard parts:
  - Two leaves, photographed as book pages with margins. The cow is cut by
    leaf 637's right edge; its head is on leaf 638 (a sliver of orange about
    20 px wide at its left edge, probably horn or muzzle). The scan's dark
    binding strip runs along leaf 638's left edge (about 8 px). The
    engraver's signature at the bottom of leaf 637 stays out.
  - Ask John before you draw it: one drawing joined across the gutter, or
    two (Apollo with the cow and the tree; Admetus on his horse). Look first
    at how much the gutter loses, and show him.
  - The horse is a stallion and his penis is drawn: draw it as printed.

## The method

As in LESSONS.md. In short: the plate's own lines, drawn even; solid black
where the plate paints solid; no washes (blood is the one exception). Check
every face and hand at 20x against the plate, every finger a closed outline;
if one won't come clean, offer John a trace and send him crops at 3-6x. A
crack, a stain or a printing flaw gets no line. Rerun the committed tool
before you show John: the SVG must come out byte for byte the same. Time
each drawing in `timing.txt` (start, shown, approved).

## Show John

For each drawing: plate crop | light | dark, at 400 px and 120 px, plus the
overlay, sent with SendUserFile. Name what you left in or out and why. For
close-ups, render straight from the SVG at the close-up's scale. Draw one,
show it, then the other.

## Records, when he approves

- `tools/suppliants_aesch.py`, `tools/alcestis.py`; `suppliants-aesch.svg`,
  `alcestis.svg` (or two Alcestis SVGs, if John wants two drawings).
- Fill the `plays` entries (`work_id` "suppliants-aesch", "alcestis") in
  `docs/redesign/research/play-image-plan.json`: `source_file`, `credit`,
  `license`, `crop`, `alt_text`, `shows`, `method`, `result`, `status`,
  `final_image`. Credit in the short house form: follow the hippolytus and
  andromache entries.
- Add both to `drawings.json` and the README table; rerun
  `tools/contact_sheet.py`. Add what you learned to LESSONS.md, dated, under
  a new heading for the Élite.

## Review

One cross-family review for the pair (Claude never reviews Claude's work):
Grok or Codex, whichever the budget board leaves room for. A static read:
the overlays cut into thirds and the credits quoted into the brief, nothing
for it to run. Real faults only: missed lines, lines along flaws, wrong
facts. Don't apply its findings yourself: check each against the plate, show
John crops of the ones that hold up, and fix only what he approves.

## Working alongside batch 2

Another session draws the Gerhard pair (`claude/redesign-plates-2`) at the
same time.

- Touch only your own tools and records. Leave `tools/linework.py` alone
  unless you must; if you must, add an option rather than change what the
  existing calls do, add a test to `tools/test_linework.py`, and rerun
  `tools/hippolytus.py` and `tools/andromache.py` from
  `/Users/johnboyer/Developer/greek-plays/.remember/batch1-2026-10-06/src/`:
  both SVGs must come out byte for byte unchanged.
- `drawings.json`, the README table, `play-image-plan.json` and LESSONS.md
  change on both branches: keep to your own entries and rows.
  `contact-sheet.html` is generated: rerun the script after a merge rather
  than merge it by hand.
- John has two sessions open: start each message to him with the play's
  name.

## Done means

Both drawings approved by John, records filled, contact sheet rebuilt,
review run and the fixes he approved made, LESSONS.md updated, branch
pushed, `tools/test_linework.py` and `tools/test_andromache_trace.py` pass.
Then stop and report; the next pair waits for John.
