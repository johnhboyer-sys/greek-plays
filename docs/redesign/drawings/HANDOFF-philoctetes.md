# Handoff: the Philoctetes drawing (2026-10-03)

Make the line drawing for Sophocles' *Philoctetes*, from the Met's lekythos
of Philoctetes alone on Lemnos. John will review it closely. This file is all
you need; the session that wrote it is gone.

## Before you start

- Read `docs/redesign/DESIGN.md` (the Drawings section) and the end of
  `docs/redesign/decisions.md`. Both are untracked files in the main
  checkout: `/Users/johnboyer/Developer/greek-plays/docs/redesign/`.
- Read `README.md` in this folder (the SVG format and the tools), then your
  models:
  - `tools/antigone.py`: the closest. A red-figure photo taken off its vase
    with `tools/vase_unroll.py`, mends erased and joined, hands and face from
    John's own traces.
  - `tools/vase_unroll.py`: fits the vase and cameras, then flattens the vase
    without shear.
  - `tools/euphorbos.py`: several photos into one drawing; `strokes()` for
    hand-placed lines.
  - The finished *Oedipus Tyrannus* tool lives on another branch: `git show
    claude/redesign-drawings:docs/redesign/drawings/tools/oedipus_syracuse.py`
    (`drawn()`, every finger a closed outline).
- Memory to read: vase-photos-flattened, drawings-cracks-leave-no-line,
  vase-painting-public-domain, drawings-show-the-plot, drawings-may-show-ending,
  plain-drawing-credits, redesign-drawing-test.
- Other branches, none merged (merging is John's call):
  `claude/redesign-drawings` (*Oedipus Tyrannus*, approved);
  `claude/redesign-drawings-2` (Euphorbos and Antigone, approved; this file);
  `claude/redesign-colonus` (*Oedipus at Colonus*, another session's work in
  progress: never touch it or its worktree).

## Where to work

```
git -C /Users/johnboyer/Developer/greek-plays worktree add .claude/worktrees/redesign-philoctetes -b claude/redesign-philoctetes claude/redesign-drawings-2
```

Commit as you go and push to `claude/redesign-philoctetes`. Make a venv in
your scratchpad (`numpy scipy scikit-image pillow`); `potrace` and
`rsvg-convert` are installed. Sources are never committed. /tmp is wiped at
reboot, so keep anything that must survive in
`/Users/johnboyer/Developer/greek-plays/.remember/` (gitignored). The disk had
19 GB free on 2026-10-03.

## The vase

- Attic red-figure squat lekythos, c. 420 BCE, 15.7 cm tall. New York,
  Metropolitan Museum of Art 56.171.58 (Fletcher Fund, 1956; Met object
  254917, https://www.metmuseum.org/art/collection/search/254917). The Met's
  record names no painter; look for one (Beazley Archive) before writing the
  credit.
- What the photos show: Philoctetes alone, seated on a rock under a tree,
  bearded, his hair in curls, his head bowed. He wears a finely pleated
  chiton, with a himation over his lap; his legs are bare. One hand rests on
  the rock behind him; one leg is drawn up, the knee high. A band of crossed
  lines wraps his shin just above the foot, which reads as the bandage on
  his wound. His quiver or bow case, with its straps, leans on the
  rock below him. Check his lap at full size for the no-nudity rule; at
  preview size the himation covers it.
- Why it fits: it is the play's own situation, the man left on Lemnos with
  his wound and the bow, not a myth the play only mentions. Say so in the
  record's `shows` field.
- Proposed in the first drawings handoff as the Philoctetes source; John has
  not yet confirmed it.

## The photos

All three show the same side. Download them again; nothing is kept from the
session that found them.

1. **Met DP165159**, https://images.metmuseum.org/CRDImages/gr/original/DP165159.jpg,
   4000x4000, CC0 (the Met's Open Access: the object record says
   `isPublicDomain: true`). Evenly lit, the whole vase against grey. The
   vase's axis is at about x 2000; its half-width is 634 px at y 1650, 738 at
   2400, and 676 at 3000. He fills about x 1590-2690 and y 1750 (top of the
   hair) to 2990 (his foot): about 1,240 px tall. His knee and his foot lie
   near the vase's right edge, so that side is foreshortened here. A painted
   band runs under the scene (two dark lines, about y 3000-3060 near the
   middle), and a tongue pattern circles the shoulder (about y 1460-1575).
2. **Met DP165160**, https://images.metmuseum.org/CRDImages/gr/original/DP165160.jpg,
   3791x3792, CC0. The same side, the vase turned a little; whole outline.
   Neither Met file has EXIF.
3. **Marie-Lan Nguyen, 2011**, https://commons.wikimedia.org/wiki/File:Philoktetes_Lemnos_Met_56.171.58.jpg
   (file: https://upload.wikimedia.org/wikipedia/commons/d/d7/Philoktetes_Lemnos_Met_56.171.58.jpg),
   2150x2425, CC BY 2.5. Nikon D300S at 50 mm (EXIF): 4288 px across a
   23.6 mm sensor, so f is about 9,090 px; the file is a crop, so fit its
   centre (`crop: True`). It is the closest and looks most squarely at him:
   he is about 2,020 px tall (about x 340-2010, y 255-2280). Glare lies on
   the black glaze at the shoulder, above and beside his head.

What I would do, not yet tested: trace from photo 3, which has the most
detail. Fit the vase with all three: the Met views give the whole outline,
and the band under the scene is a circle. The Met photos have no EXIF, so
fit their focal lengths starting long (they look near-orthographic), and
check that the flat hardly moves across a range of values. Fix photo 3's
focal length from its EXIF.

## Rights and credit

- The Met photos are CC0; photo 3 is CC BY 2.5. John's ruling: the painting
  is public domain even where a photo is not, and a drawing traced from the
  photo does not carry the photo's licence. On that ruling the Oedipus
  Tyrannus drawing dropped its photo's CC BY-NC-SA ("drop it, with the
  license"). Credit the photographer either way. When you show John the
  first test, tell him which photo you traced and what licence the drawing
  carries; that call is his.
- The SVG `<desc>` takes the short house form (memory:
  plain-drawing-credits). The full credit goes in the `plays` entry with
  `work_id` "philoctetes" in `../research/play-image-plan.json`.

## First, ask John

1. **The subject:** is this lekythos his Philoctetes? Show him photo 3.
2. **The crop:** Philoctetes alone, or with the rock he sits on, or with the
   rock and the bow case. The tree stays out either way. The rock is painted
   in brown washes, and John: "the orange strokes don't translate to two
   tone" (said of a streak on Antigone's cheek); a rock would be its outline
   and its painted lines only.
3. **A quick test**, flattened, before building the rest: his face, hair,
   and the hand on the rock, at display size (400 and 120 px, light and
   dark). His hair and beard are curls in brown dilute paint inside a dark
   outline; on Oedipus Tyrannus John liked hair as tiny curls drawn solid
   with a curly outline. Offer to draw the hands and face from his trace.

If he turns Philoctetes down, the other Sophocles plays still without a
drawing have only unchecked leads, in
`../research/sources-2026-10-02/codex-lane-A.json`: *Electra* (Matera,
Graz Painter, Electra at Agamemnon's tomb, CC BY-SA 4.0, 3321x4974); *Ajax*
(Exekias, Boulogne, Ajax planting his sword, CC BY-SA 3.0; as far as I know
Exekias paints him naked, which John's no-nudity rule forbids; check);
*Women of Trachis* (Munich white-ground lekythos 1905, Heracles shooting
Nessos; worn, low detail; public domain).

## What John asked for on Euphorbos and Antigone

- **Take the painting off the vase first.** An unflattened figure reads as
  deformed ("smooshed like a Neanderthal"). Check the head against the photo
  that looks most squarely at it before you show him.
- **Partly hidden parts stay in:** "Don't leave out the other foot."
- **Breaks:** "connect the lines broken up by that slash." Erase a mend
  whole and join the painted lines across it (`join_across` in
  `antigone.py`).
- **Hands and face:** he looks hardest here ("hands need more work as do the
  face"). He traced Antigone's hands once and her face three times on
  screenshots, and the drawing follows his traces. Map his marks onto your
  frame by matching the screenshot to it with SIFT (the `*_TRACE` constants
  in `antigone.py`, registered to under half a pixel); a later trace replaces
  an earlier one inside its zone; where his outline encloses paint, draw it
  filled; an eye too small for outlines comes from the paint itself.
- **No washes:** brown dilute strokes are not drawn ("the orange strokes
  don't translate to two tone").
- **Credits short:** "you are overthinking the credit."

## Checks and review

- Each tool's `main()` takes an optional QA path and writes `qa_overlay` and
  `qa_dark` images. Rerun the committed tool before showing John; the SVG
  should come out byte for byte the same.
- Records: fill in the `plays` entry (`source_file`, `credit`, `license`,
  `crop`, `alt_text`, `shows`, `method`, `result`), add the drawing to
  `drawings.json` and the README table, and rerun `tools/contact_sheet.py`.
- Review before calling it done: on 2026-10-03 Grok 4.7 ran as a static read
  through the grok-cc companion, with the QA images cut into thirds; it can
  view images. Route by the budget board. Keep its credit checks to plain
  errors (wrong photographer, licence, or museum number).

## Still open from earlier

- Antigone: John has not answered two questions (her record's `result`): a
  small dark spot on her upper arm, kept because the vase paints it; her jaw
  and chin drawn as two close lines, with clay between them in dark mode.
  If he answers, make the change on your branch.
- From the first handoff: whether a playwright figure can double as its
  play's drawing; a new source for *Iphigenia at Aulis*.
