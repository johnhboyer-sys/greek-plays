# Drawings: handoff for a second session (2026-10-02)

You are making more of the redesign drawings while another session finishes
the Oedipus Tyrannus drawing (his hand). Leave `tools/oedipus_syracuse.py`
and `oedipus-tyrannus.svg` alone.

## Read first

- `DESIGN.md`, the Drawings section, and the "Drawings, phase 1" entries at
  the end of `decisions.md`. Both are untracked files in the main checkout:
  `/Users/johnboyer/Developer/greek-plays/docs/redesign/`.
- `README.md` in this folder: the SVG format, the tools, and how to rerun.
- `../research/play-image-plan.json`: one record per play. Fill in the record
  for each drawing.
- Memory: redesign-drawing-test, drawings-may-show-ending,
  drawings-show-the-plot, and vase-painting-public-domain.

## Where to work

- Make your own worktree and branch from `claude/redesign-drawings`:
  `git -C /Users/johnboyer/Developer/greek-plays worktree add .claude/worktrees/redesign-drawings-2 -b claude/redesign-drawings-2 claude/redesign-drawings`
- Commit as you go and push to `claude/redesign-drawings-2`. Merging is
  John's call. Conflicts should only come in appended or generated files:
  keep both entries in `drawings.json` and the README table, and rerun
  `tools/contact_sheet.py` for `contact-sheet.html`.
- Make a Python venv in your scratchpad (`numpy scipy scikit-image pillow`).
  potrace and rsvg-convert are installed. Sources are never committed; each
  tool's docstring names its source URL.
- The disk has about 4 GB free. Don't save `.npy` debug arrays, and delete
  large downloads when you are done with them.

## John's rulings (2026-10-02)

- Dark mode: dark lines on a figure filled with clay (the `body` path), as on
  a red-figure vase. Approved.
- Rights: "The vase's image ISN'T copyrighted even if the photo IS." A drawing
  may be traced from an in-copyright photo of an ancient vase; credit the
  photo. On this ruling the Syracuse drawing dropped its photo's CC BY-NC-SA.
  He has not said whether it also frees drawings made from CC BY-SA photos;
  until he does, keep those CC BY-SA, as DESIGN.md says.
- No nudity. Whole figures only, cut along their own outlines.
- Show the play: its own action first, then backstory the plot turns on.
  Never a myth scene the play only mentions; he turned down Oedipus killing
  the Sphinx for that. Endings are fine.
- Detail matters. Engraved and lithographed plates gave the best drawings.
  Sparsely painted vases give sparse drawings; he found Berlin F 2355 and
  Würzburg H 5697 too thin. He looks closely at faces, hands, fingers, and
  hair, and he spots every missing line.

## Decided, not yet drawn

1. **Sophocles' home-page figure:** the shepherd Euphorbos carrying the
   infant Oedipus. Paris, Cabinet des Médailles 372, Attic neck-amphora by
   the Achilles Painter, c. 450–445 BC. Photo: Commons, "Achilles Painter -
   ARV 987 4 - Euphorbos with the infant Oidipous - man - Paris BnF CabMed
   372 - 04.jpg", 3069x4254, CC BY-SA 4.0, by ArchaiOptix. Photos 01–03 show
   other angles, and a public-domain photo by Bibi Saint-Pol is 2300x1642.
   It replaces `sophocles-oedipus.svg` (Berlin F 2355) on the home page.
2. **Antigone:** Antigone bound, brought before Creon. Berlin F 3240, an
   Apulian amphora by the Darius Painter, c. 350–320 BC. Photo: Commons,
   "Darius Painter - RVAp 18-23 - Antigone - judgement of Paris - Eros with
   youths and women - Berlin AS F 3240 - 04.jpg", 5472x3648, CC BY-SA 4.0,
   by ArchaiOptix. The search agent measured her at about 3,250 px tall.
   Cut her out alone. The guard's cord touches her wrists, two mended breaks
   cross her arm and skirt, and Heracles and Creon stay out.
3. **Oedipus at Colonus:** an Apulian calyx-krater near the De Schulthess
   Painter, 340s BC, in the Geddes collection, Melbourne, A 5:8 (Taplin,
   *Pots and Plays*, 2007, no. 27). The only image is the 942x641 plate on
   p. 101 of the free Getty PDF
   (https://media.getty.edu/Text/6f3674dd-413a-56da-bec2-9da5564907df.pdf,
   PDF page index 111), where Oedipus is about 350 px tall. The ruling above
   makes it usable. Ask John first whether he wants Oedipus alone or the
   group with his daughters on the altar. Upsample 4x before thresholding,
   as `pythia.py` does, and expect a simpler drawing.

## Open questions for John

- Philoctetes: Met 56.171.58, Philoctetes seated alone on Lemnos. The photo
  is by Marie-Lan Nguyen, CC BY 2.5, and the figure is about 2,000 px tall.
  It was proposed, but he hasn't ruled. CC BY is not on DESIGN.md's list,
  though it is looser than CC BY-SA.
- Can a playwright figure double as its play's drawing? DESIGN.md says every
  play gets its own. The cases are the Pythia (Eumenides), Iphigenia
  (Iphigenia in Tauris), and Mika (Thesmophoriazusae).
- Iphigenia at Aulis: the Met 31.11.2 test failed (`rejected/`).

## The other plays

First leads for every play are in `../research/sources-2026-10-02/`. They
come from a Codex web search and are unverified, so open each image before
trusting it. Most are rated weak; search for better ones, in DESIGN.md's
order of sources. Sonnet search agents using the Wikimedia Commons API
worked well; brief them with the rulings above.

## Method that worked

- Write one script per drawing in `tools/`, holding its crop, cut points,
  and hand fixes, with the reason for each. Copy the closest model:
  `pythia.py` or `iphigenia_tauris.py` for engraved plates; `medea.py`,
  `mika.py`, or `oedipus_syracuse.py` for red-figure photos.
- **Engraved plates:** find lines with `ink_lines`. Cut along the figure's
  own lines with `livewire`, using `STRAIGHT` across blank paper. Upsample
  small scans 4x.
- **Red-figure photos:** build a clay mask, by brightness or by red minus
  blue for shiny glaze. Leave out wide glaze joined to the background. Find
  painted lines with `ink_lines`. Draw zones by hand wherever the mask goes
  wrong.
- **What John liked on the Syracuse Oedipus, after three rounds:**
  - Hair made of tiny curls drawn solid, with its curly outline.
  - A dense beard drawn solid, with its long strands kept as light lines.
  - Face lines redrawn as even lines along their centres (`pen`).
  - Cracks erased, and the lines they broke joined up again.
  - A flaked staff redrawn straight, with the change recorded.
- **Hands:** keep them out of solid masses, and draw each finger clearly.
  He traced Oedipus's hand himself to show what he wants.
- **Checks before showing John:** run `qa_overlay` (the drawing in red over
  its source; any grey line still showing is a missed line) and `qa_dark`.
  Look at each drawing at 1,400 px and at display size on the author tint,
  light and dark. Show him before-and-after crops.
- **Records:** fill in the drawing's entry in `play-image-plan.json`
  (`source_file`, `credit`, `license`, `crop`, `alt_text`, `shows`, `method`,
  `result`). Add it to `drawings.json` and the README table, then rerun
  `tools/contact_sheet.py`.
- **Review:** before calling a batch done, have Codex or Grok check it,
  since a Claude session made it: a visual audit of the QA tiles, plus the
  records and licences. Route by the budget board. Their findings are
  evidence, not rulings.
