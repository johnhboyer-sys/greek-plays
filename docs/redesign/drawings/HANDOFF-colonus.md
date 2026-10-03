# Handoff: the Oedipus at Colonus drawing (2026-10-02)

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
