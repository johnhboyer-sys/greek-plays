# Handoff: the Oedipus at Colonus drawing (2026-10-02)

## Status, 2026-10-03 21:45: John's marks applied; awaiting his verdict

Since 18:45 (heads 11c63e5, f1e0a6e, pushed), all from John's marks:
- Ismene: brow and eye (19:01) and the profile from the nose down with a
  level mouth (21:32), all on screenshots of the found photo matched to the
  lines frame by SIFT. "She's not smiling": the mouth is level now.
- Oedipus' hand: it "read as lump" at display size, so the two raised
  fingers are each turned a little about their base (FINGER_SPREAD, 12 and
  7 degrees; HAND_LINES keep the measured outline). The two lower fingers
  follow his marks on p. 29 (21:31).
- Pieces of his strokes left just outside the outline are dropped (they
  showed as clay rings in dark mode).
- `.remember/colonus/scripts/marks_to_plate.py` carries red marks to plate px
  through a page's registration (or the lines frame).
- John: no Grok until Tuesday 2026-10-06. The Codex review ran at 18:28;
  rerun it (GPT-6-Sol, medium) once John signs off.

## Earlier status, 2026-10-03 18:45

- John found a clean photo of the scene online (547x560; probably from a
  Facebook post, source unknown; "don't worry about the credit"). Kept as
  `.remember/colonus/found.png`; the tool takes it as a fifth photo file.
  It is registered to the plate at run time (error 0.42 of its px; misfit
  over Ismene 0.1 plate px) and used only to find painted lines
  (LINES_ONLY): its glaze has sheen, so ground, outline, solid black and
  white still come from the plate. Ismene's garment now carries its folds
  (e34a3a2); her face stays from John's first trace. Awaiting John's verdict.
- The fringe fix (claude/redesign-drawings 6e7e3d3) is merged in (580a29e):
  lines byte-identical, body path changed, test_linework.py passes.
- Quick runs: `run_cached.py` now reads two cached frames,
  scratchpad `hathi/a_green.npy` (base) and `hathi/a_lines.npy` (lines);
  `.remember/colonus/scripts/build_frames.py` rebuilds both (4 min).
- Codex review (GPT-6-Sol, medium; brief `.remember/colonus/codex_review_brief.md`)
  done 18:32: a veil-corner loop, an altar speck, Ismene's broken borders,
  and one records mismatch, all fixed (bfe0b71); its question whether
  Oedipus' raised fingers read as one mass at display size is John's.
  Left: John's verdict (Ismene's new folds, Oedipus, the hand question).

## Earlier status, 2026-10-03 17:40: paused

Branch head after this commit; everything pushed.
- Oedipus (redrawn on p. 29) and Antigone (John's traces on p. 26) are in.
  John on Antigone: "could be crisper, but it's probably fine for the
  resolution we will use for the site". No verdict yet on Oedipus.
- Ismene: John traced her on p. 4 (17:00); first the face from it read badly
  ("oh god her face looks awful now"), then the clothing folds ("the new
  folds suck, just go back to what you had before for her garment"). She is
  back exactly as at 5532460. John: "we'd need higher res of her. this is
  the best we can get right now." His p. 4 trace is kept locally
  (`.remember/colonus/john_ismene_trace_1700.png`), not used. Idea to put to
  him: Green's catalogue entry runs pp. 27-29; we have pp. 26 and 29, so if
  p. 27 or 28 (HathiTrust seq 29, 30) shows the left half of the scene, that
  would give Ismene Antigone's sharpness.
- Cross-family review not run: Codex failed at 16:47 with "workspace is out
  of credits" (its rolling 5-hour window). Rerun it once the drawing is
  settled, on GPT-6-Sol at medium effort; the brief is saved in
  `.remember/colonus/codex_review_brief.md`, and the review images in
  `.remember/colonus/review/` need regenerating first.

## Earlier status, 2026-10-03 16:30

Done since 14:05 (heads dd8f476, 46fd033, pushed):
- Oedipus redrawn on p. 29: face lines on the painted marks (FACE_LINES,
  FACE_FINE, CLOSED_EYES), the face found by colour and closed by its lines;
  the dark marks between the curls of his hair and beard drawn solid
  (HAIR_MARK_T); the staff in its two visible parts (STAFF, STAFF_EDGES:
  the lower part leans the other way, so it is not one rod); the hand's
  outline from the column's edge on p. 29, with the ring finger reaching past
  the pinky (John's note); the neckline pleats and two folds by the hand
  along their centres (CHEST, MANTLE_FOLDS).
- Antigone's face, hand and forearm from John's own traces on p. 26
  (`.remember/colonus/john_antigone_trace_1602.png`,
  `john_antigone_arm_trace_1611.png`), mapped with
  `.remember/colonus/scripts/map_john_trace.py` (SIFT to the page at 1:1,
  then the page's registration); his filled areas stay solid
  (JOHN_ANTIGONE_FILLS).
- Records, README, and the SVG's credit now name Green's pages; contact
  sheet rebuilt. A full run from the page files gives the same SVG as the
  cached frame.
- John's red guide marks on p. 29: he re-saved the page clean, so the marks
  survive only in a crop; `.remember/colonus/john_marks_p29_recovered.png`
  rebuilds the marked page from it.

**Next.** John's verdict on Oedipus (sent 15:30) and Antigone (sent 16:25).
Then the cross-family review (Codex or Grok, per the budget board): QA
tiles, records, credit. Ismene is still drawn from the plate; p. 4 is too
noisy to help her, so ask John whether to leave her or have him trace her.

Tools in `.remember/colonus/scripts/`: `zoom_page.py` (a plate-px box
straight off p. 26 or p. 29, with rulers, the drawing, or strokes over it),
`page_lines.py` (centre lines of painted marks off a page), `review.py`
(photo | before | now), `display_crop.py` (a figure at display size, light
and dark), `slot.py`, `run_cached.py`.

## Earlier status, 2026-10-03 14:05: resumed on Green's pages

John found the sharper source: J. R. Green, *Ancient Voices, Modern Echoes*
(2003), in full view on HathiTrust (mdp.39015060089391, CC BY-NC-ND 4.0). He
downloaded three pages, kept in `.remember/colonus/`:
- seq 6 (p. 4): the whole vase, 1.8x the plate's scale; Taplin's plate is a
  copy of this photo.
- seq 28 (p. 26): the right half of the scene, 6.4x.
- seq 31 (p. 29): Oedipus's head and hand, 12.8x.

The tool now registers them to the plate when it runs (`load_green`: SIFT, a
RANSAC homography, and a thin-plate spline; plate→p4→p26→p29, errors 0.3,
0.2, and 0.1 plate px). It colour-matches them to the plate and lays p. 29
over p. 26 over the plate. Ismene and the altar's left end stay drawn from
the plate, because p. 4's print noise traced as wiggles. Every plate-px
constant still applies. A run takes about a minute; for quick iteration,
`.remember/colonus/scripts/run_cached.py` runs the tool on a cached frame
(`a_green.npy`).

**Next.** Re-place the hand-placed parts on the sharp photo, since the plate
blurred them:
- Oedipus's face: trace the painted dark lines (brows, closed lids, nose and
  nostril, moustache, mouth). John's red marks on p. 29
  (`john_marks_p29_seq31.tif`, carried into the frame as
  `john_guide_frame.npy`) are a rough guide to what he sees, not a trace.
- His hair and beard: draw the dark curl lines, as John marked them in the
  beard, plus the outline of the white mass.
- The staff: it now comes out as a heavy bar, because the rod no longer sits
  on the painted staff and the staff's sharp edges trace beside it.
- His chest: a row of tooth-like shapes; check what the paint shows there.
- His hand strokes.
- Antigone's face: the paint now shows it clearly, so trace it and show John
  both versions (his trace, and the paint).

Then show John the photo, before, and now at each place, plus the slots.

## Earlier status, 2026-10-03 11:30: on hold

John put the drawing on hold (11:29) until he can get a higher-resolution
print scan of the vase. The work is on `claude/redesign-colonus`, pushed and
not merged.

**Done.** John chose the three on the altar: Oedipus, Ismene, and Antigone,
with the columns and tripods left out (2026-10-02). `tools/oedipus_colonus.py`
traces the *Pots & Plays* plate at 4x. The records (image plan, `drawings.json`,
README, contact sheet) are filled in and marked on hold. John's review notes
are all applied:
- Oedipus's nose.
- The daughters' faces after his trace, registered from his screenshot by SIFT.
- Oedipus's mouth and beard curls.
- Antigone's eyes and smile, then her far eye.

A second photo, Digital LIMC 8569X101 (whole vase, black and white,
credit "Graham Geddes Collection (once)", CC BY-NC 4.0 on the LIMC site), was
downloaded with John's OK. It was used to read shapes the plate blurs and is
credited.

**Open.**
- John has not yet confirmed the faces after the last round.
- The cross-family review (Grok or Codex, routed by the budget board: QA
  tiles, records, credit) has not been run.
- Weak spots: Ismene's raised hand, and the zigzag ends of the two mantles.
- The dark-mode clay fringe fix is on `claude/redesign-fringe` (bf63143
  changes `linework.py` `trace_svg` and adds `tools/test_linework.py`). It
  merges with this branch except `contact-sheet.html`, which both branches
  regenerated: rerun `tools/contact_sheet.py` after merging, then rerun this
  drawing. Checked 2026-10-03 with a scratch copy of the tool: the lines are
  byte-identical; only the body changes. The clay sliver outside the outer
  outline is gone, and the clay within 1.5 px of the background drops from
  1,609 to 761 px at 1400 px wide.

**Scans John may bring, best first:**
1. The printed *Pots & Plays*, p. 101. The Getty PDF cut the plate to 150 dpi.
   A 600 dpi scan of the page makes Oedipus about 1,440 px tall instead of 360.
2. J. R. Green, *Ancient Voices, Modern Echoes* (2003), p. 4 and cat. 1,
   pp. 27–29. This is Taplin's own source.
3. Others, mostly black and white: *LIMC* V "Ismene I" 2; *RVAp* Suppl. 2
   pl. 33.4; *RVSIS* fig. 200; Aellen 1994 pl. 29; *CFST* Ap131; Taplin 1997,
   fig. 15.
4. Sotheby's London, 9 December 1985, lot 173.
5. The Trendall Research Centre at La Trobe University (unconfirmed).

**To resume with a new scan:**
- Keep every hand-placed point in the tool. They are all in px of the 942x641
  Getty plate: OUTLINE, the zones, FACE_LINES, HAND_LINES, John's trace
  (JOHN_*), and the rest.
- Register the scan to the plate (SIFT and a RANSAC homography, then ECC per
  region: the LIMC photo's homography was off by up to 8 plate px at
  Ismene's hand, where SIFT found few matches, and by 1–2 px elsewhere). Change
  `load()` to warp the scan into the same working frame (BOX at F = 4) instead
  of enlarging the plate. Every constant then still applies, and the 4x frame
  holds real detail.
- Re-check the thresholds tuned on the plate's colours: BLACK_L, WHITE_B,
  HAIR_GR, SOLID_L, PEEL_L, CURL_LOC, STROKE_T, and RIDGE_T.
- A sharp scan may show the painted face lines well enough to trace directly.
  Show John both versions.
- The local helper scripts are in
  `/Users/johnboyer/Developer/greek-plays/.remember/colonus/scripts/`
  (gitignored): `local_limc.py` (homography and ECC per region), `round4.py`
  (photo, LIMC, before, and now sheets), and `slot.py` (400 and 120 px slots,
  light and dark). The plate, the LIMC photo, John's trace screenshot, every
  review image sent to John, and `sources.md` are in `.remember/colonus/`.

## The original brief (2026-10-02)

Make the line drawing for *Oedipus at Colonus* from Taplin's vase. John
wants it, and he will review it closely. This file is all you need; the
session that wrote it is gone.

## Before you start

- Read `docs/redesign/DESIGN.md` (the Drawings section) and the end of
  `docs/redesign/decisions.md`. Both are untracked files in the main
  checkout: `/Users/johnboyer/Developer/greek-plays/docs/redesign/`.
- Read `README.md` in this folder (the SVG format and the tools) and
  `tools/oedipus_syracuse.py`. That file is the *Oedipus Tyrannus* drawing,
  which John approved tonight. It is your best model.
- Memory to read: drawings-cracks-leave-no-line, vase-painting-public-domain,
  drawings-show-the-plot, drawings-may-show-ending, redesign-drawing-test.
- A second session works on `claude/redesign-drawings-2` (the Euphorbos
  figure, then Antigone). Its `HANDOFF.md` lists Colonus as item 3. Run
  `git log --oneline claude/redesign-drawings-2`; if it shows any Colonus
  work, stop and ask John. Never touch that branch or its worktree, and don't
  message that session (John: "leave it be").
- *Oedipus Tyrannus* is finished. John: "Some things could be polished but we
  leave that alone." Don't edit `oedipus_syracuse.py` or
  `oedipus-tyrannus.svg`.

## Where to work

```
git -C /Users/johnboyer/Developer/greek-plays worktree add .claude/worktrees/redesign-colonus -b claude/redesign-colonus claude/redesign-drawings
```

Commit as you go and push to `claude/redesign-colonus`. Merging is John's
call. Make a venv in your scratchpad (`numpy scipy scikit-image pillow`).
`potrace`, `rsvg-convert`, and `pdfimages` are installed. /tmp is wiped at
reboot, so keep anything you need to survive in
`/Users/johnboyer/Developer/greek-plays/.remember/` (it is gitignored).

## The vase

- Apulian red-figure calyx-krater, close to the De Schulthess Painter, 340s
  BC, about 50.5 cm tall. Graham Geddes collection, Melbourne, A 5:8. It is
  Taplin, *Pots & Plays* (Getty, 2007) no. 27, pp. 100–102, with the plate on
  p. 101. Other references: RVAp Suppl. 2, 17/81, pl. 33.4; LIMC Oidipous 91
  and Ismene I 2; Trendall 1989, fig. 200; J. R. Green's 2003 Nicholson
  Museum catalogue, cat. 1; Taplin 1997 (*Cambridge Companion to Greek
  Tragedy*), fig. 15, p. 84. A search agent reported that Taplin 1997 gives
  the number as A5:3, which you should check. It also reported that the vase
  is said to be from Taranto and came on the market in 1985; this is
  unchecked too.
- The scene, as read by a search agent from the plate:
  - Oedipus sits facing front at the centre of a white altar, between two
    Ionic columns topped by tripods.
  - He has white hair and beard, his eyes are closed, and he holds a staff
    in one hand, the other hand raised as he speaks.
  - He wears a long chiton and himation, finely folded and without pattern.
  - Ismene (left, ornately dressed) and Antigone (right, veiled) sit at the
    ends of the altar, facing him.
  - Outside the group: a bearded man with a sceptre at far left (Creon;
    Green says Theseus), a youth at far right (Polynices, whose face is
    modern repaint), and an Erinys at upper right.
  - Oedipus is whole: no break or handle crosses him. His staff and drapery
    overlap the front of the altar, and his hand and staff cross the right
    column. The daughters do not overlap him.
- Taplin says the vase shows the Colonus story in ways that make sense only
  if you know the play. Put that, in your own words, in the record's `shows`
  field.

## The source image

There is only one: the plate in *Pots & Plays*, a 942x641 JPEG at 150 dpi.
Searches of Commons, Wikipedia, Flickr, museum and auction sites, and image
search found nothing larger. Get it from the Getty PDF, which is already in
John's Downloads:

```
pdfimages -j -f 112 -l 112 ~/Downloads/6f3674dd-413a-56da-bec2-9da5564907df.pdf plate
```

The PDF is also at
https://media.getty.edu/Text/6f3674dd-413a-56da-bec2-9da5564907df.pdf
(52.6 MB). Page 112 is book p. 101. Its 942x641 JPEG is the plate; the
other image on that page is the scanned text. `~/Downloads/Untitled 2.pdf`
(John's) holds the same JPEG, byte for byte.

Where things are, in plate px:
- His head (white hair) is at about (440, 235), from the top at y 221 down to
  his toes at y 572, so he is about 350 px tall.
- His robe is at about (470, 350). The altar is at about (420, 500). The
  columns are at about x 345 and x 545.
- The group spans about x 200–740 and y 200–590. Ismene's robe is at about
  (300, 480), Antigone's at about (600, 400).

Colours (luminance L):
- Black glaze: about 30.
- Clay figures: 145–160, orange (about RGB 227, 140, 55).
- Added white (the altar, the columns, his hair and beard): 200–220, cream
  (about RGB 250, 210, 150).

It is small. The Syracuse figure was about 2,900 px tall, and Oedipus here
is 350, with a face about 25 px across. Upsample 4x (Lanczos) before you
threshold, as `pythia.py` and `iphigenia_tauris.py` do (F = 4), and smooth
out the JPEG blocks first. Expect a simpler drawing, and say so to John at
the start.

## Rights and credit

John's ruling (2026-10-02): "The vase's image ISN'T copyrighted even if the
photo IS." The drawing traces only the ancient painting, so it does not carry
the photo's rights. Still credit the photo. Find the exact credit in the
PDF: the plate's caption, the cat. 27 entry (`pdftotext -f 110 -l 113`), and
the book's illustration credits. A search agent saw the credit "courtesy of
Graham Geddes" for the 1997 printing. Record the result the way the
`oedipus-tyrannus` record in `../research/play-image-plan.json` does.

## First, ask John

1. **The subject**, which he has not chosen yet. Show him both crops side by
   side:
   - **Oedipus alone**, on his altar seat. This matches the other drawings,
     which are single figures, and he is larger in a square slot.
   - **Oedipus with Antigone and Ismene on the altar**: the play's opening
     tableau of suppliants. The shape is wider, so the figures come out
     smaller in a square slot.
   - Either way, ask whether the altar comes in as his seat; the columns and
     tripods would stay out.
2. **A quick test** of his face and the hand with the staff at display size
   (400 and 120 px, light and dark), before you build the rest. The face is
   frontal, with closed eyes, at 25 px; if it reads badly, offer to draw it
   from his trace. He traced the Syracuse hand with his trackpad, and that
   worked.

## John's rulings from the Syracuse drawing

Apply them from the start.

- **It is a line drawing.** Give every shape a clean, complete outline; each
  finger is a closed outline. He rejected a version traced from the
  painter's marks: "The finger outlines are less distinct", then "Get the
  outlines. It's a line drawing."
- **Damage.** Erase a crack or a mended break whole, and draw nothing along
  it on either side. Join the painted lines it broke across it. "The
  outlines of the crack need to be gone." "Fill in the gaps of the lines
  where damage has erased parts." Where a part is badly damaged, he may let
  it stay rough; on Syracuse he did that for the hem and shoes. That is his
  call each time.
- **Where he looks hardest:** faces, hands, fingers, and hair. Draw small
  parts as hand-placed strokes along the paint (`drawn()` in
  `oedipus_syracuse.py`). When he marks up a screenshot, map his marks back
  exactly: match the screenshot to the photo with SIFT features, or keep each
  review image's crop origin and zoom. Never estimate from the picture.
- **Hair.** The Syracuse hair was black glaze curls, drawn solid with a
  curly outline, and he approved it. Here the hair and beard are added
  white, so don't fill them black: outline them, with a few strand lines.
  Show him early.
- **Every round,** show these side by side: the photo, before, and now, plus
  the whole figure in light and dark at display size. Keep messages short and
  plain. Don't polish past what he asks for.

## Tools that worked on Syracuse

All are in `tools/oedipus_syracuse.py` and `tools/linework.py`:
- `poly` zones for parts drawn by hand.
- `drawn()`: smooth strokes of even width through points.
- `join_gaps`: joins lines that wear has broken, where two ends face each
  other.
- `fold_lines`: hand-placed paths snapped to the paint.
- `join_pairs`: joins listed pairs of line ends.
- `crack_bands`, with `carry_across`: a crack's own lines erased, and the
  lines it broke carried across it.
- `trace_svg`, `qa_overlay`, `qa_dark`.

To find faint lines that the tracing missed, a ridge filter
(`skimage.filters.sato`, sigmas 1.5–3.5) on the photo worked well. Score each
candidate path by how much of it runs on a ridge, and check each one by eye.

## Records when done

- `../research/play-image-plan.json`, the `oedipus-coloneus` record. It still
  holds only a placeholder. Fill in:
  - `proposed_subject`, `status`, `source_candidate`, `final_image`
  - `credit`, `license`, `crop`, `alt_text`
  - `source_file`, `shows`, `method`, `result`
- `drawings.json` and the README table: add an entry for the drawing. Then
  rerun `tools/contact_sheet.py`.
- The output is `oedipus-coloneus.svg`, made by `tools/oedipus_colonus.py`.
- Before you call it done, have Grok or Codex review it, routed by the budget
  board: a visual check of the QA tiles, the records, and the credit.
