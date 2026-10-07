# Handoff: plate drawings, second pair (Women of Trachis, Seven Against Thebes), 2026-10-06

Make two line drawings from Gerhard's *Auserlesene griechische Vasenbilder*
II (1843): *Women of Trachis* (code 09n) and *Seven Against Thebes* (02n).
John picked both sources on 2026-10-05
(`.remember/sweep2-2026-10-04/rulings.md`). Another session draws the Élite
pair (batch 3) at the same time: read "Working alongside batch 3". This
file is all you need; the session that wrote it is gone.

## Before you start

- Read `docs/redesign/drawings/LESSONS.md` first: what the first pair
  (Hippolytus, Andromache) taught, how John traces, the checks that caught
  real faults. Then `docs/redesign/drawings/README.md` (the SVG format, the
  tools) and the Drawings section of `docs/redesign/DESIGN.md` (John's file:
  never edit it). DESIGN.md's "No nudity" line is stricter than John's later
  ruling (2026-10-05): draw nudity as printed; only the comic costume phallus
  is out.
- Your model: `tools/hippolytus.py` (Gerhard AV III, red figures on black:
  about 50 minutes, approved on the first pass).
- Branch: if `claude/redesign-plates-1` has been merged into main, branch off
  main; if not, branch off `claude/redesign-plates-1` (it holds the linework
  changes this work needs: `rim_lines`, `dots`, `weight="drawn"`, and
  LESSONS.md). New branch `claude/redesign-plates-2`, in its own worktree.
  Copy this file into the branch as
  `docs/redesign/drawings/HANDOFF-plates-2.md` and commit it first. Commit as
  you go and push. Merging is John's call.
- Sources are never committed. Keep them in
  `/Users/johnboyer/Developer/greek-plays/.remember/batch2/src/` (gitignored),
  with `notes.md` and `timing.txt` beside them. Build a Python venv in your
  scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless);
  potrace and rsvg-convert are installed.
- Batch 1's helper scripts (sharp close-ups, mapping John's traces):
  `/Users/johnboyer/Developer/greek-plays/.remember/batch1-2026-10-06/scripts/`.
  They hold Andromache's paths and constants: copy and adapt them; don't
  edit the originals.
- Check the model budget board at session start. Load the `delegate` skill
  before your first subagent spawn.

## Sources: fetch exactly these two files and nothing else

John OK'd these downloads on 2026-10-05. Any other download needs his OK
first.

1. 09n: https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_116.jpg/full/full/0/default.jpg
   (2105 x 2780; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0241)
2. 02n: https://digi.ub.uni-heidelberg.de/iiif/2/gerhard1843bd2%3A000_Tafel_ROEM_091.jpg/full/full/0/default.jpg
   (1963 x 2767; page https://digi.ub.uni-heidelberg.de/diglit/gerhard1843bd2/0218)

Both public domain (1843). Read each Heidelberg page's licence mark before
you write the credit.

## 1. Women of Trachis (09n): draw this first

- Plate: Gerhard, AV II (1843), Taf. CXVI ("Herakles und Hyllos"); text pp.
  114-120. Read the text for the vase's shape, museum and provenance: the
  picking worker did not. Find the text pages in the volume's OCR on the
  Heidelberg viewer.
- Subject (John: "as proposed"; "Don't worry about the nudity"): the
  shoulder panel's four figures, each named on the vase: Athena (helmet,
  aegis, spear) at the left; Herakles (lion-skin hood) holding Deianeira by
  the wrist; Deianeira, veiled; Oineus (bearded, staff) at the right. Between
  Herakles and Deianeira, held across their arms, a small nude boy inscribed
  HYLLOS. Red figures on black. The play's story: Herakles, Deianeira, her
  father Oineus, their son Hyllos.
- Crop measured by the picking worker, full-scan px (x, y, w, h):
  `119, 155, 1733, 1454`. Herakles 1,083 px tall, Deianeira 1,069, Oineus
  1,108, Athena 1,268 (crest to foot).
- The hard parts:
  - All four interlock: Athena's hand and spear shaft touch Herakles' lion
    skin; Herakles' and Deianeira's hands clasp, with Hyllos across their
    arms; Deianeira's mantle overlaps Oineus' cloak. Draw all four, whole.
  - The spear tip and Athena's crest cross the palmette band above; the feet
    stand on the meander band below. The bands stay out. Inscriptions stay
    out.
  - A tiny mark at Hyllos' groin may be his genitals: check at 20x and draw
    what the plate shows.
- Black ground, so Hippolytus' method applies directly.

## 2. Seven Against Thebes (02n): show John a test first

- Plate: Gerhard, AV II (1843), Taf. XCI (Eriphyle); text pp. 28-30. Vase:
  an archaic black-figure hydria, in the Roman art trade when Gerhard
  published (read the text).
- Subject (John: "as proposed"): the lower panel. Eriphyle at the left,
  veiled, in a long dark mantle with white lines, dots and crosses, walking
  right; facing her, a four-horse team with raised forelegs; at the right,
  two armed men in the chariot behind shields, their spears crossing. The
  play's story: Amphiaraos, one of the Seven, and his wife Eriphyle, who sent
  him to the war. The plate's upper strip (armed men and a chariot) is a
  separate picture: out.
- Crop (x, y, w, h): `200, 765, 1550, 1047`. Eriphyle 933 px; the team 904;
  the whole group about 992.
- The hard parts:
  - It is black-figure: black silhouettes on the orange clay, with incised
    lines (thin light lines through the black) and added white. Neither
    method so far covers it, and the ground does not give the outline the
    way the black ground does on red-figure. How a black-figure figure should
    look in the house style, on the light page and on the dark theme's clay,
    is John's call. Before you draw the panel, show him a test of a small
    piece (Eriphyle's head, the lead horse's head) done one or two ways, in
    light and dark, and ask.
  - Eriphyle can't be cut from the horses: their raised forelegs cross her
    robe at hip and knee, and her foot meets their hooves. The crop holds the
    whole panel.
  - The panel is a curved band (orange from about y 730 to 1720 in the
    middle, 1820 at the corners), so the box takes in paper at the corners.

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

- `tools/trachiniae.py`, `tools/seven.py`; `trachiniae.svg`, `seven.svg`.
- Fill the `plays` entries (`work_id` "trachiniae", "seven-against-thebes")
  in `docs/redesign/research/play-image-plan.json`: `source_file`, `credit`,
  `license`, `crop`, `alt_text`, `shows`, `method`, `result`, `status`,
  `final_image`. Credit in the short house form: follow the hippolytus and
  andromache entries.
- Add both to `drawings.json` and the README table; rerun
  `tools/contact_sheet.py`. Add what you learned to LESSONS.md, dated.

## Review

One cross-family review for the pair (Claude never reviews Claude's work):
Grok or Codex, whichever the budget board leaves room for. A static read:
the overlays cut into thirds and the credits quoted into the brief, nothing
for it to run. Real faults only: missed lines, lines along flaws, wrong
facts. Don't apply its findings yourself: check each against the plate, show
John crops of the ones that hold up, and fix only what he approves.

## Working alongside batch 3

Another session draws the Élite pair (`claude/redesign-plates-3`) at the
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
