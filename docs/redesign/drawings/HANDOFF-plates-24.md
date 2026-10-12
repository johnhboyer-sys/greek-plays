# Handoff: Orestes at Delphi, the whole of Bötticher's plate, with PhotoCraft, 2026-10-12

One session, one drawing. John, 2026-10-12 12:08: "Let's also do the whole of [Karl] Bötticher's drawing of the
Apulian volute-krater by the Black Fury Painter, and not just the Pythia. It's a great plate." Today only the Pythia
is drawn from it (`aeschylus-pythia.svg`, `tools/pythia.py`, the Aeschylus home-page figure, marked "To redo in
PhotoCraft"). Other sessions are running (Persians on `claude/redesign-plates-20`, Prometheus Bound on
`claude/redesign-plates-21`, Frogs on `claude/redesign-plates-23`): don't touch their branches, worktrees or notes.

| Subject | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Orestes at Delphi (Aeschylus, Eumenides) | C. Bötticher, *Der Omphalos des Zeus zu Delphi* (Berliner Winckelmannsprogramm, Berlin, 1859), plate fig. 1 | `claude/redesign-plates-24`, `.claude/worktrees/redesign-plates-24` | `.remember/batch22/` |

## The source
- Page: https://digi.ub.uni-heidelberg.de/diglit/bwpr1859/0011; image
  https://digi.ub.uni-heidelberg.de/diglitData/image/bwpr1859/4/010a.jpg; IIIF `bwpr1859%3A010a.jpg`, largest size
  1775 x 2341 (info.json, checked 2026-10-12). Licence: Public Domain Mark 1.0 (the volume's IIIF manifest, checked
  2026-10-12). The Commons copy is a blurred 1.5x upscale of the same scan: don't use it.
- Fig. 1 sits at the top of the leaf, about 244, 185 to 1745, 888 in full-scan px (check it); figs. 2-4 below (the
  omphalos and the temple plan) are not part of the drawing.
- The plate: a pen contour drawing, no black ground. Left to right: an Ionic column; the Pythia fleeing, hands raised,
  in a starred shawl and a dress with a black stripe, past a tripod and laver; above her a Fury as a black silhouette
  with snakes; Apollo striding, arm stretched out, in a patterned cloak; Orestes crouched with his sword at the
  omphalos, which is wrapped in a patterned net; a laurel tree; Artemis in a short patterned dress with spears and
  two hounds; an Ionic column. Hanging shields, a wreath and animal heads along the top; the ground line below.
- Size: the figures are only about 450-500 px tall in this scan, well under the 800 px floor. Look for a larger scan of
  the same plate first (Google Books, HathiTrust, another library's copy of the programme, the Internet Archive): say in
  one line what you find, and ask John before downloading a second one. Otherwise work at UP = 4 or more and check
  faces, hands and the net at 20x.
- The vase: the Black Fury Painter's volute-krater, Naples (check the number: Naples 82270 / H 3249 is the usual
  reading; Trendall, RVAp). Bötticher's drawing is an engraver's rendering and may differ from the vase.
- The play: direct. The Pythia flees the temple at the start of Eumenides (34 ff.); Orestes at the navel-stone, Apollo
  and the sleeping Furies follow (64 ff.).

## Ask John first (one message, start it with "Orestes at Delphi (PhotoCraft)")
1. What the drawing is for: the Eumenides play image (still open: 07-Ra was a fallback), the Aeschylus home-page figure
   in place of the Pythia alone, or both (the whole plate for the play, the Pythia cut from the new drawing for the
   home page).
2. What it holds: the whole frieze between the two columns, with the columns, the hanging objects along the top, and
   the ground line, or the figures and their furniture alone. Show the crop.
3. The style: a contour plate as Rhesus and Persians (pen lines; the figures' area the paper the lines close off; clay
   on the dark theme); the Fury, the stripe and other black areas solid. Show a small test of the Pythia's head and
   Orestes's face in both themes.
4. A larger scan, if you found one (name, source, size).

## Credit
- Read Bötticher's own text for the plate (Heidelberg OCR; the text pages sit behind a bot check: read them in the
  browser pane, one page at a time). Then the vase now (Naples, Museo Archeologico Nazionale; the museum's record if
  online; Trendall, RVAp; Beazley Archive or LIMC "Orestes") and check the credit against it. Title in one line to John.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes
  the SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel
  grid; read his marks literally. Send the red overlay with every pass.
- Your models: `tools/rhesus.py` (Hoernes's contour plate: pen lines at half maximum, the figures' area by a sealed
  watershed with pockets, shafts kept, walls) and the Persians tool if it is merged by then (`tools/persians.py`).
  Read the old `tools/pythia.py` for John's decisions on the Pythia (her shawl ends, the stripe), not for its lines.
  Read `docs/redesign/drawings/LESSONS.md` whole: the contour-plates entries, "Checks that caught real faults", "John's
  traces", the 2026-10-10 to 10-12 entries (pin the line weight after pass 1; diff the whole plate after each round;
  `OPEN`, `DROP`; John's short lines meaning "this is paint").
- This plate's traps: the omphalos net and the patterned cloaks and dresses (small marks at their printed width through
  `dots`); the spears and the sword (long, thin, straight and whole); the laurel's leaves; the hounds behind Artemis's
  legs; Apollo's foot over the Pythia's hem (both kept now: nothing is cut out); the small scale.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe. Keep it under 30 MB so
  John can mark it on his phone.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.
- John may be on Remote Control: send every image with SendUserFile and ask with AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-24.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here (gitignored);
  never commit it.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- The tool and SVG named for what John says it is for (`tools/eumenides.py` and `eumenides.svg` for the play; if the
  home figure changes too, say how before touching `aeschylus-pythia.svg`). Fill the matching entry in
  `docs/redesign/research/play-image-plan.json` (the `plays` list, or `playwrights` for the home figure;
  `json.dumps(d, indent=2, ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun
  `tools/contact_sheet.py`, and a dated LESSONS entry under the contour plates. Rerun the tool: the SVG comes out byte
  for byte the same. `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless
  John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`.
  For the play: add Eumenides to `settled.json` (wid `eumenides`; `imgs/drawn-eumenides.png` at 700 px high on #fbf9f4
  with rsvg-convert; `imgs/orig-eumenides.jpg` a crop of fig. 1) and mark its pick in `picks.json`. For the home figure:
  re-render `imgs/drawn-aeschylus-pythia.png` and clear its redo note. Run `build7.py`, read the artifact first
  (another session may have published since), and publish `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch22/HANDOFF.md` and do it: one line drawing with
> PhotoCraft of the whole of Bötticher's 1859 plate of the Black Fury Painter's krater (Orestes at Delphi: the Pythia,
> Apollo, Orestes at the omphalos, Artemis, the Fury), on a new branch `claude/redesign-plates-24`. Your first message
> to me asks what the drawing is for, what it holds, and the style.
