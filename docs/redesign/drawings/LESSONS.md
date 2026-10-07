# Lessons from the plate drawings

Read this before you draw from a printed plate. When you finish one, add
what you learned: what went wrong, what fixed it, how long it took. Date
each entry and name the plate it came from. Keep entries short; the detail
belongs in the tool's comments. Correct an entry that turns out wrong
rather than adding a second one that contradicts it.

## Plate families

### Gerhard, *Auserlesene griechische Vasenbilder* (coloured lithographs, red figures on black)

- The method works as it stands: the black ground gives the outline, the
  plate's own lines come by local contrast, faces from the plate's paint at
  its own width. Hippolytus (Taf. CLXV, 4) took about 50 minutes and John
  approved it on the first pass (2026-10-06). `tools/hippolytus.py`.
- Thin things that cross open ground (a bowstring, an ankle strap) break up
  or lose their clay on the dark theme: trace them through their measured
  centres and pass them to `trace_svg` as `rim_lines` (2026-10-06).
- Gerhard numbers a vase's shape drawing and its painting separately (CLXV,
  3 is the amphora's shape, 4 its painting) and heads the text "CLXV, 3.4".
  Cite the figure you drew (2026-10-06).
- Not every Gerhard plate takes Hippolytus' line finder. On Women of Trachis
  (Taf. CXVI) its blur ran close lines together (the eyes, the pleats, a
  dotted band): John, "too blotchy". What worked: the plate's own paint
  (darker than grey 115, lightly smoothed) and its thin brown lines by a
  ridge filter (sato), at least 1.5 px wide, traced as drawn at the plate's
  weight (0.104%). About two hours over three passes (2026-10-07).
  `tools/trachiniae.py`.
- Where a figure crosses a border band (a crest, a spear, a sleeve), outline
  what is kept along the plate's own lines, then check the whole crossing at
  8x: Athena's sleeve outline first began at a fold 50 px low, and the
  straight border cut sliced across her sleeve. Band ornament seen through
  the figure (palmette leaves in the crest's base) goes too (John,
  2026-10-07).
- Cut along a border line's edge, not its centre: half a border line drawn
  as an outline comes out a line and a half wide (the soles, the crest's
  top) (2026-10-07).

### Furtwängler and Reichhold, *Griechische Vasenmalerei* (black pen lines on grey-brown, the ground a dark halftone)

- Budget hours, not minutes. Andromache (Taf. 34) took about ten hours over
  a day, most of it on John's traces and the blood (2026-10-06).
  `tools/andromache.py`.
- Where figures touch there is no ground between them: cut along the
  plate's own lines (livewire zones), decide early what is in and what is
  out, and say so when you show John.
- Line weight: the house weight (0.225%) ran close lines together (eyelids,
  curls, pleats). John chose 0.155%, then 0.11%. Draw the lines along their
  centres at that weight (`even_lines`, `centre_lines`) and trace with
  `trace_svg(weight="drawn")`: resampling or re-weighting in the tracer
  blurs a one-px gap shut, and the kilt's hems ran together (2026-10-06).
- Faint brown lines (anatomy, folds): a ridge filter finds them; redraw them
  along their centres. At the filter's own width they came out beaded and
  heavier than the black lines (2026-10-06).
- The line finder cannot give clean faces, hands, feet or dense drapery at
  this weight. John traced three faces, five hands, Priam's feet and the
  kilt. On the next FR plate, send him crops (3-6x) of every face and hand
  at the start, not after the first pass (2026-10-06).
- Check the source before you credit it: the FR text for Taf. 34 is pp.
  182-187 (the handoff said 201); Heidelberg's scan of Taf. 34 is from its
  first copy, added to the volume later (the handoff said the second). The
  page in the Heidelberg viewer says which copy, and its OCR finds the text
  pages (2026-10-06).

## John's traces

- He draws over a crop of the plate, or over a screenshot of a close-up, in
  Preview, and sends it in chat. The chat image is not a file you can read:
  the file is on his Desktop ("Screenshot ... PM.png", with a narrow
  no-break space before "PM", so glob for it) or in Downloads (2026-10-06).
- His colours: blue lines are black ink. Blue paint over his own outlines
  marks the shapes they close as blood. Green paint marks blood with no
  outline (dark and light green for darker and lighter blood). Black lines
  drawn over the overlay are lines the drawing missed; red lines over a
  screenshot are lines to add. A ring drawn round something means take it
  out (2026-10-06).
- Register his image to the crop by SIFT (OpenCV), with his marks painted
  out first: the median error was about 0.1 plate px. His strokes become
  polylines along their centres, marks wider than about 2.5 pen widths
  become filled shapes, small round marks standing alone become dots. The
  scripts are `map_trace.py` (strokes, filled marks, dots), `map_fill.py`
  (blue paint on a screenshot, placed by the close-up's ruler),
  `map_blood.py` (green paint on a crop) and `crisp.py` (sharp close-ups),
  kept with the batch's sources in `.remember/batch1-2026-10-06/scripts/`,
  outside git (2026-10-06).
- Laying a trace in (`apply_trace`): his strokes at the line weight; the
  plate's lines inside the shapes he closes go, and those within 6 plate px
  of his strokes. Where he traced only some of the lines in an area (the
  kilt), a plate line near his goes only when it runs along his (the same
  line drawn twice); lines that cross his stay (2026-10-06).
- potrace's speck filter drops a dot a line wide: pass dots to `trace_svg`
  as `dots`. A dot of his that lands off the figure is a slip of the pen
  (2026-10-06).
- Show him close-ups rendered straight from the SVG at the close-up's scale
  (plate | drawing | dark theme), not a small render enlarged: he judges the
  lines at full sharpness (2026-10-06).
- Never apply a reviewer's findings (Grok, Codex) without him: check each
  one against the plate, and show him crops of the ones that hold up
  (2026-10-06).

## Blood

On the vase, blood is thinned paint laid on in lighter brushstrokes. John's
rulings on Andromache (2026-10-06); `tools/andromache.py` holds them
(`BLOOD`, `PAINTED`, `BLOOD_T`, `BLEND_*`, `RIM`, `BIT`, `CHEST`, `ALTAR`,
`add_tone`).

- Draw it as a wash in the line colour, not as black lines: paths of class
  `tone`, between the body and the lines, with `fill-opacity` ("make the
  blood black ink that's been reduced in opacity, not solid grey").
- No black outlines on the blood. Where he outlined a streak (Priam's
  scalp), the outline is part of the wash ("No black blood outlines").
- Lines that cross the blood stay black and show through it ("you should be
  able to see black lines through the blood"). Where blood covers lines (the
  pleats on Priam's chest), take the blood out, join the lines through, and
  lay the wash back over them ("duplicate image, join the lines, then apply
  the blood with the wash gradient on top of it"). The dots of Priam's
  stubble stay black.
- The wash follows the plate. Its opacity runs from 0.25 where the plate is
  light (grey 140, after denoising) to 0.55 where it is darkest (85),
  smoothed over 2 plate px, in steps of 0.05. Each step is a path drawn over
  the larger step below it, at the opacity that brings the total to the
  step's value, so no seam shows between steps. Flat tones read as grey
  patches, and two tones side by side looked patchy; he chose the blend and
  asked for it subtle.
- Where its edges come from: where he outlined it, the shapes his outlines
  close. Where he painted it, the plate's own dark streak under his paint
  (darker than grey 132): his brush is broader than the streaks, and drawn
  as painted the wounds came out "absurdly big". The plate's darker rim just
  outside a wound goes too ("The black circular outlines for the wounds
  aren't in the original"). Where the line finder took blood for black ink
  (Priam's chest, the drips on the altar), the blood is the plate's dark,
  wider than the lines, inside a ring drawn round it.
- Trace the wash at the same size as the lines. Traced at another size, it
  fell out of register with them.

## Checks that caught real faults

- Rerun the committed tool: the SVG must come out byte for byte the same.
- `tools/test_linework.py` (the body path, dots, lines a px apart) and
  `tools/test_andromache_trace.py` (a fine diagonal stroke comes through
  whole). Write the failing case first.
- scipy's distance transform of an empty mask measures from just outside
  its corner: check `mask.any()` first (it drew a speck at (0, 0)).
- After any change to the tracer, look at close-ups of the faces, the blood
  and the densest lines before you show John.
- Render the body path alone and count its pixels outside the figure: there
  should be none. `trace_svg` gives a line with no clay beside it a clay
  rim; an outline wider than a line and a half counts as one, and on Women
  of Trachis the rims showed as clay slivers on the ground in 99 places.
  When tracing as drawn, pass everything outside the figures as
  `open_holes` (2026-10-07).
