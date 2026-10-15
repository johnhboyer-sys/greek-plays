# Lessons from the plate drawings

Read this before you draw from a printed plate. When you finish one, add
what you learned: what went wrong, what fixed it, how long it took. Date
each entry and name the plate it came from. Keep entries short; the detail
belongs in the tool's comments. Correct an entry that turns out wrong
rather than adding a second one that contradicts it.

The design brief is `docs/redesign/DESIGN.md` (its Drawings section governs these drawings); the phase
prompts are in `docs/redesign/PHASES.md`, the reasons in `docs/redesign/decisions.md`, and the approved
sketches in `docs/redesign/sketches/`. Read the brief before drawing.

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

- Trojan Women (Taf. CLXIX, 4, Menelaus and Helen), made with PhotoCraft: about three hours over four
  passes, approved by John 2026-10-08. `tools/trojan_women_menelaus.py` (2026-10-08).
- Drawing with PhotoCraft (John, 2026-10-07): every image step runs in `photocraft-cli` (crop, enlarge,
  grey, Gaussian blur, Maximum then Minimum for local contrast, Threshold); numpy only combines its
  masks and measures. It reran byte for byte. The red-figure method carried over whole; the tool's
  steps are the same, only run in PhotoCraft (2026-10-08).
- Black borders inside a figure (a shield's inner band, zigzag hems) run into the ground where the
  clay line between them fades to a px: the ground then floods the border and drops the clay beyond
  it. Find the leak with a least-cost path through the ground from the border to the open ground,
  and wall it where the path is narrowest (`WALLS`) (2026-10-08).
- The faintest folds print as dotted runs, grey 100-135 on clay 145-160. Local contrast at fine blur
  finds the dots; each run drawn along a curve fitted to it comes out an even line, and ends that point
  straight at each other (within 10 degrees) are joined across the print's gaps. Keep runs off the
  figure's edge: the print's darker band inside the outline passes for a fold (`FAINT`, `ALIGN_*`)
  (2026-10-08).
- A profile's lips and chin are clay bumps 3-4 px deep with a thin pale strip along them: the grey
  threshold made a wiggle of them. Three tries of my own made it worse (John: "The mouth is WORSE
  now"); John drew the line over the plate's pixels at 20x and it is drawn on his line (`PROFILE`).
  For a small part, send him the pixel grid first (2026-10-08).
- Gerhard's text can be wrong about where a vase is: he puts CLXIX, 3.4 in the Vatican; it is British
  Museum 1837,0609.71 (E 263), as the BM's 1896 catalogue says. Check the museum's record, which opens
  in the browser pane when a plain fetch meets its bot check (2026-10-08).

- Suppliant Women (III, Taf. CLVIII, Aithra and Theseus), made with PhotoCraft: about three hours over three passes,
  the source search included, approved by John 2026-10-13. `tools/suppliants_eur.py` (2026-10-13).
- John: "be sure to get all those clothing lines without breaks". The pleats print 1-2 px wide, often as dashes, and in
  places 2-4 px apart. Local contrast (Trojan Women) ran neighbours together and their centre lines grew rungs; the
  plate at half maximum kept them apart but broke the dashes (2350 line ends). What worked: blur the plate along its own
  lines first, PhotoCraft's Motion Blur at 12 angles, each px from the angle nearest the lines' direction there (the
  structure tensor's, smoothed over 4 plate px), then half maximum and centre lines: 917 ends, the pleats whole. Taking
  each px from the darkest of the 12 blurs instead is wrong: between two pleats a blur across a neighbour is darkest
  (2026-10-13).
- That blur smears short marks (the cuirass's hatching, scales and tassels, eyes). Use it only where the structure
  tensor's coherence says lines run parallel (drapery 0.8-0.95, marks 0.4-0.5), keep only its long centre-line pieces
  (15 plate px or more) mostly in such areas, and take the rest from the unblurred half maximum at its printed width.
  Two traps: the final speck filter dropped every small mark until the marks were spared from it, and the blurred
  smears of the marks, kept, "covered" the sharp ones so they were dropped as drawn twice (2026-10-13).
- Trojan Women's gap joiner asks a median contrast of only 4 along a join of ends that point at each other, across up to
  40 px; the clay's grain reads 7 at the median, 14-18 at the 90th percentile, and it drew straight strokes across
  Theseus' face. Ask 15 (the dashed lines' gaps read 20 and up), over at most 20 and 30 px (2026-10-13).
- Faint fold ends: follow each line end on along the plate's line, a step at a time onto the darkest of the three px
  ahead, while the mean contrast over the last 4 plate px stays 18 or more, for at most 12 px, stopping at other ink
  (`grow_ends`): 923 ends to 574, the candidate breaks (ends where the print runs on) 115 to 41 (2026-10-13).
- A sweep for breaks before showing John: for every line end inside the figure, sample the plate's contrast 2-9 plate px
  beyond it; where it stays over 12 until it meets ink, sheet the end (plate | drawing). Most are true ends (eye corners,
  curl tips, tapering folds); the rest are the breaks to mend (2026-10-13).
- John's blue strokes on faint lines: drawn along the plate's line through points read off his stroke (ordered by the
  longest path through its skeleton: walking from one end took a small branch and lost two strokes), kept within 2.5
  plate px of it, or a livewire cut across a curve where the plate's line is faint. A blue dot too small to be a stroke
  is taken as painted. Where his stroke lies over broken wiggles (fingers printed faint), take the old ink within 2.5 px
  out first (`REPLACE`). Where green takes out a drawn ring the plate prints as a solid dot, put the dot back
  (`AFTER_DOTS`) (2026-10-13).
- Hair printed only a shade lighter than the ground, with a darker rim and no clay line, joins the ground: find the
  leak by the shortest path through the dark from the hair to the open ground and wall it there (2026-10-13).

### Gerhard, black-figure plates (black silhouettes on orange clay, incised lines, added white)

- Show John a small test of the style first, both ways, light and dark. On
  Seven Against Thebes (Taf. XCI) he chose the silhouette (the black solid,
  the incisions open in it, a clay rim on the dark theme) over an outline
  drawing, then asked for more detail in the eye and the faces (2026-10-07).
  `tools/seven.py`.
- Incised hatching lies 3 px apart and the black between its strokes prints
  mid-grey: a threshold runs the strokes together. Smooth the plate along
  each stroke first (the structure tensor gives the direction), then take
  the light marks by a white top-hat (2026-10-07).
- The added white can be printed out of register: here about 8.5 px left of
  the shapes its black outlines give. Measure the shift on two or three
  outlines and move the white back; the white printed past an outline is
  ground (2026-10-07).
- Where the white's printed edge is ragged (Eriphyle's feet), draw the shape
  on the plate's own contour lines instead, and join the broken ones through
  the centres of their dashes (John: "The black lines of the foot are broken
  but should be connected"). The lines live in a data file
  (`tools/seven_feet.json`), so a trace from John can replace one
  (2026-10-07).
- About three hours: the style test, the face detail, and the feet
  (2026-10-07).
- After approval John traced Eriphyle's face and hands himself (about an
  hour and a half more). On black-figure his lines are the edges of the
  white: in each traced box the white is what his lines and the black
  enclose, filled from a seed; what his lines leave on the figure's side is
  black, on the ground's side ground. Close the black over its incisions
  less than for the feet, or not at all: closed 3 px, it shut a thin
  finger, and 1 px shut the face's narrow strip; 0 let the hand's fill run up
  the mantle's incisions, so the closing is set per traced box
  (`tools/seven_traces.json`). He cut the pupil he had drawn
  (2026-10-07).
- A line that closes an outlined band on the ground makes the band reserved
  clay, but it may still be larger than the size that counts as ground
  (the band ahead of the lead horse, 2219 plate px²): mark it (`BAND`) and
  check it on the dark theme (2026-10-07).

- Ajax (Taf. CCXI-CCXII, 4), made with PhotoCraft: about a day over two days and five passes, approved
  by John 2026-10-09. `tools/ajax.py` (2026-10-09).
- A double plate across the gutter: look for a copy photographed unfolded before drawing across the
  fold. Heidelberg's fold hid a strip of the Gorgon shield; the NYPL copy on HathiTrust has the plate
  as one flat foldout (its page list tags the page before it FOLDOUT). HathiTrust's Cloudflare check
  loops in the built-in browser; it passes in Chrome (Claude in Chrome). A torn strip in the NYPL
  sheet was filled from Heidelberg's scan, registered by SIFT and matched in tone (2026-10-09).
- Hatched rims (strokes 4-5 px apart, printed pale on this copy): Motion Blur along the band's own
  angle joins each stroke's dots into a ridge; each ridge is drawn straight, run out to the band's
  edges. The band's angle is the mean of its pieces; ruled as one set they drift off the strokes
  (`hatch_strokes`). The spread test that finds hatching also takes the print's mottled soft edge
  outside a profile: only bands with strokes, or wider than 5 px, stay out of the ground (it put a
  strip of clay along Phoenix's nose; John) (2026-10-09).
- The added white prints 2-6 px inside its outline: draw the outline as a curve on the printed line,
  found by reading outward from the white's edge, not as a band round the white (`white_outline`)
  (2026-10-09).
- Small ground pockets the figures close in print as clay, too small to pass for ground: John circled
  fourteen on the dark theme, where they show as clay (`POCKETS`) (2026-10-09).
- Check the vase, not only the plate, when something looks wrong: the copyist drew Briseis' hand
  twice (white on the crest, again in outline lower down); on the vase (photos by ArchaiOptix on
  Commons) she has one. John: remove the phantom hand. Gerhard's text also put the vase in Munich; the
  Beazley Archive (which cites the plate) and the photos put it in the Vatican (2026-10-09).

- Lysistrata (AV IV Taf. CCCVIII, 2, five water carriers), made with PhotoCraft: about four and a half
  hours over two days and four passes, approved by John 2026-10-09. `tools/lysistrata.py` (2026-10-09).
- This plate needs no levelling and no out-of-register shift: the clay is a warm channel (red less blue,
  PhotoCraft's Channel Mixer), the black and the added white plain thresholds (2026-10-09).
- The arms and hands: the plate's contour round the white is uneven, broken and specked, so drawn as
  printed it came out lumpy, and along its centres or its midline it broke up. What worked: the outline
  drawn from the skin's own shape, smoothed (Gaussian Blur then Threshold), as an even band just outside
  it. Do not close the skin over the gaps between fingers: they are 1-2 px of clay or grey, and a closing
  of even 1 px joins the fingers (2026-10-09).
- Then John traced the lowered hands himself in PhotoCraft, on a file of the whole picture at the tool's
  own 3x grid (plate, my pass in blue at 50%, an empty layer): no registration, his red layer read
  straight off the file. His fingertips are short strokes joined to the fingers' sides; the rule that
  lets my outline run on to meet the free end of one of his strokes must not count those joints as free
  ends, or the tips drop out and the print's blot shows through (John: "Close off the pinky. And remove
  that bit of black ink sticking out") (2026-10-09).
- Gerhard's text has the vase in the Feoli collection in Rome; Würzburg bought that collection in 1872,
  and the vase is Würzburg L 304 (the same pictures and painted names). The Beazley Archive's search
  pages did not answer from the browser pane; the American School's booklet *Women in the Athenian
  Agora* (fig. 3) gives the museum number (2026-10-09).

### Gerhard, *Trinkschalen und Gefässe des Königlichen Museums zu Berlin* (coloured lithographs, red figures on black)

- Heracles (II, Taf. XXI, side B), made with PhotoCraft: about three hours over two passes, approved by John
  2026-10-09. `tools/heracles.py`. The Auserlesene Vasenbilder method carried over, with these differences
  (2026-10-09).
- The plate prints two kinds of line: black, and pale brown (the lion's fur, the anatomy, the folds; their
  darkest grey stays above 105). Drawn black they read as heavy as the outlines; John chose them as a grey
  `tone` wash. Keep the test inside a box round where they are printed: elsewhere a black line's thinning end
  passes it, and the toes came out half black, half grey (`BROWN_BOX`) (2026-10-09).
- Its lines are finer (0.12% of the longer side, 1-2 px) and closer than the AV plates': at the house
  weight the eye's rings ran into a blot. Trace as drawn (`weight="drawn"`), and draw the eye and the toes
  from the plate's paint at its own width (`FACES`) (2026-10-09).
- A bowstring 1-2 px wide on the black: measure its centre row by row only where it is clear of the bow
  (the bow's clay pulled the centroid), fit a curve, and where it meets the bow take the bow's edge from a
  curve fitted above and below the junction. Drawn from guessed ends it ran beside the printed string
  (John: "way off") (`STRINGS`, `bow_edge`) (2026-10-09).
- Thin clay parts that end free (the arrow's shaft, 1-3 px of clay between its lines; the bow's tip) lose
  their clay to the body path's smoothing in `trace_svg`: pass them as `keep` (2026-10-09).
- Black paint inside the figure that meets the ground through a gap (the inside of the lion's ear, the
  quiver's black band) came out hollow in the light theme; John circled both. Wall each gap along the
  plate's own edge (`WALLS`), and look for hollow black areas in the light theme before showing him
  (2026-10-09).
- The text names no inventory number; Furtwängler's 1885 catalogue of the Berlin vases does (no. 2164, with
  "Abg. Gerhard, Trinksch. und Gefässe Taf. XXI") and says what is restored (here Herakles' legs). Its text
  is on the Internet Archive (`beschreibungderv00furt`): search the plate number (2026-10-09).
- Hecuba (II, Taf. XVI, black-figure: Neoptolemos leading Polyxena to Achilles' tomb), made with PhotoCraft in the
  black-figure silhouette (see that section): about an hour and a half over four passes, approved by John
  2026-10-10. `tools/hecuba.py` (2026-10-10).
- The added purple: John chose it as a grey `tone` wash (0.45) over the black, from a small test of three (wash,
  open, outline) (2026-10-10).
- A face drawn in incisions about 1 px wide (Achilles' shade, 25 px tall): no threshold, top-hat or blur along the
  strokes gave clean lines. Hand-placed strokes read off the plate's pixel grid at 12-14x did (`SHADE_STROKES`);
  a ridge filter outside the tool helped find them (2026-10-10).
- Where a figure is cut from one it overlaps, check what hangs over the overlap: the strip of Polyxena's dress
  over the hoplite's shield rim was left out by a cut along the shield's edge (John: "you missed part of her
  clothes"). Her outline there is the dress's outer incision, straight through it where the shield's white device
  touches it (a least-cost path ran round the device) (2026-10-10).
- A cut along the frieze's ground line also took the outline of the helmet's white crest band, which starts at the
  cut: keep the outline within a line's width of what the cut keeps (`keep_line`; John: "Missing outline line?")
  (2026-10-10).
- John's blue painted over a whole hand (the black between fingers he had greened out) is paint, not strokes:
  drawn along its centres at the line width it left flecks; taken as painted, with its pinholes filled
  (`FINGERS`, `FLECK`), it came clean (2026-10-10).
- Gerhard reads the animal at the tomb as Hecuba turned dog; Furtwängler 1885 (no. 1902) says it is a hare. The
  credit follows the museum's number from Furtwängler and the Beazley Archive (302032) (2026-10-10).

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
- Not every FR frieze can be cut into a few whole figures. Lysistrata's first try, two dancers from the
  round dance on Taf. 17/18, was dropped: each dancer's outer hand clasps a neighbour's, the thumb of one
  over the other's fingers, so no cut leaves a whole hand (John: "THe hands are the real issue. let's
  find another image"). Check the hands and feet at the edges of a crop before picking it (2026-10-08).
- Bacchae (Taf. 37, four maenads), made with PhotoCraft: about an hour over two passes, approved by John
  2026-10-12. `tools/bacchae.py`. The figures stand free of each other but for the staffs: no livewire cuts;
  the floor is the meander band's edge, measured column by column where the ground lies over it (2026-10-12).
- Taf. 37 is small (2385 px; a face about 60 px): lines by local contrast (a closing 2.5 plate px wide) drawn
  along their centres at 0.11%; the plain dark threshold took the thinned paint's broad strokes for lines
  (2026-10-10).
- The hair at the paint's threshold came out mottled, its brown curls open. Inside a box round each head the
  plate under grey 120, joined to the paint's dark cores, gives solid hair with the ivy leaves and berries
  open (`HEADS`). The eyes, about 12 px, drawn finer with the pupils as dots (`EYES`) (2026-10-10).
- The thinned paint (shadows in the folds, says the text): a `tone` wash, found as the plate darker than its
  closing over 16 plate px (wider than the broadest band; the scan's light falls off to the left), with the
  drawn lines taken out before the opening, so broad bands stay whole (2026-10-10).
- Clay islands on the ground (three leaves of a sprig) are lost when the figures are the clay joined to seeds.
  John ringed them in PhotoCraft: a ring whose inside lies off the figure puts the plate's own clay there back
  (`MARKS_FILES`). Check for free-standing leaves, berries and tips before showing him (2026-10-12).
- Medea (Taf. 90, the lower band of the Munich Medea krater), made with PhotoCraft: about five hours, approved
  by John on pass 5, 2026-10-12. `tools/medea.py`. It replaced a drawing from the Cleveland krater photo, whose
  fine lines were too faint to trace (John: "many fine details are left out. i'm not tracing all of those").
  When a photo's detail runs out, look for the vase in an old plate before tracing by hand (2026-10-12).
- Heidelberg's scans of F-R vol. II stop at 1645 px for Taf. 90 (its IIIF levels and the volume PDF alike),
  too small: its 1-2 px lines traced as dashes. John found a 3474 px photo of the plate on JSTOR (Williams
  College). HathiTrust holds only F-R's text volumes; the plates were loose portfolios (2026-10-12).
- On a plate this fine, the line finder drops what John calls "small lines broken or missing": short strokes
  (body hair, the serpents' bands, a dress's dots) fall under the centre-line step's length limit, and the
  tracer's speck filter takes what is left. Keep short marks at their printed shapes and pass them to
  `trace_svg` as `dots`; join line ends that face each other across a gap where the plate is dark between;
  lower the hysteresis floor (12) for faint lines (2026-10-12).
- Check a pass over the whole drawing, not just where John pointed: a map of the plate's line centres farther
  than a plate px from any drawn line. Its false alarms are the halos round white dots and the stippled grey of
  the thinned paint; the rest were real (2026-10-12).
- Added white on red-figure: lighter than the clay's own level round it (the scan's light varies across the
  band), drawn as `white` paths (as Wealth) with a `day` outline. Pale clay (the serpents) rises less: keep a
  large piece only where it is clearly lighter somewhere; keep small dots. Within a pale area cut by lines,
  white whole (the altar, the casket, the hilts) (2026-10-12).
- Grey thinned paint with white on it (Medea's sleeves and cap): a flat `tone` with the white open; John chose
  grey over ink for the sleeves. Build the PhotoCraft corrections file with the tone and the white as layers,
  not lines only, or John cannot see what he is marking (2026-10-12).

- Euphorbos with the infant Oedipus (III, Taf. 167, 1, the Sophocles home figure), made with PhotoCraft from
  Williams College's scan on JSTOR: about four and a half hours over a style test and six passes, approved by John
  2026-10-12. `tools/euphorbos.py` (2026-10-12).
- A close view that cuts off part of the figure (the crown): fill it from the whole plate, registered by SIFT
  (here exactly 2x, 0.22 px rms). Level after joining; check every grid you read points from is on the levelled
  image (a grid on the unlevelled one was 8 px off and put hand points beside the lines) (2026-10-12).
- Where a part runs off the black panel onto the paper (the spear), its printed lines there are the outline: the
  paper inside them is clay, the paper outside ground; seams where the two meet are redrawn straight (2026-10-12).
- At the F-R weight (0.11%) a 16 px eye ran into a blot: lines at the plate's own pen width (2.2 scan px), and the
  smallest faces drawn as curves through points read off the plate at 10-14x (splines, not livewire, which
  wandered). John wants the iris and pupil in a child's eye ("I want the iris and pupils!") (2026-10-12).
- "Find broken fine lines and complete them": a looser local-contrast pass kept where it runs on from a line's end
  or stands alone 25 scan px or more, then ends facing each other joined, and a free end run on straight to the line
  it points at (a wrapping stopping short of the leg's outline). Sheet every added piece on the plate and look:
  pieces meeting a line along its side made ticks, and loops ran round broad brushstrokes (2026-10-12).
- Orestes (II, Taf. 120.3, the Eumenides Painter's krater in the Louvre), made with PhotoCraft from Williams College's
  scan on JSTOR: about two and a half hours over two passes, the source search included, approved by John 2026-10-12.
  `tools/orestes.py`, on `bacchae.py`'s rules (2026-10-12).
- "See if you can find German reproduction": the museum's own bibliography leads there. The Yale krater's cites Michaelis
  1882 (Rokeby Hall), whose source, Matz in the *Archäologische Zeitung* 1873, dismisses the house's vases ("keine
  bemerkenswerthe Darstellung"): no old drawing. The same scene on another vase was in F-R, found from its
  Inhaltsverzeichnis on Heidelberg (the in-app browser reaches it; the Bash sandbox does not) (2026-10-12).
- Face lines on this plate print grey (90-130), not black: the dark threshold lost the sleeping Fury's closed eye, and
  local contrast alone drew every face line twice its width. Local contrast to find them, then cut at the half-maximum
  point between the clay round a line and the darkest plate within 2 px (PhotoCraft's Minimum), at 0.6 (`FACE_*`). Grey
  wash on a plate with none (the hatch's dark spots) is false: keep the wash to the one grey area (`OMPHALOS`) (2026-10-12).
- Thinned-paint hair (curls stippled over clay): a flat wash for the mass, cut where the curls end ("don't have
  hair bleed into face"), the curls as darker strokes on it, and a line where the mass meets the clay at the back;
  a paler strand against the black is hair too, with no cut into the outline (John: "there is no cut in")
  (2026-10-12).
- A broad dark brushstroke (the petasos cord) took the brim's pen lines with it: the cord only where the paint is
  broader than the pen lines, and the crown's wash averaged over its own clay, or it mottles and haloes the lines
  (2026-10-12).

### Lenormant and de Witte, *Élite des monuments céramographiques* (coloured lithographs, red figures on black)

- The Gerhard method works here too. Suppliant Women (III, pl. XX) took
  about 35 minutes and John approved it on the first pass (2026-10-07).
  `tools/suppliants_aesch.py`. Alcestis (II, pl. LIV) took about three
  hours, most of it on the fold (below). `tools/alcestis.py`.
- The hair prints as dark as the ground, inside a thin light line. Where
  that line fades, the hair joins the ground and drops out as ground: trace
  the light line through hand-placed points along its ridge (`HAIR` in
  `suppliants_aesch.py`), or wall the gap and name the hair as paint
  (`walls`, `paint` in `alcestis.py`) (2026-10-07).
- Fingers are clay strips 4-6 px wide with 2-3 px of ground between them:
  find the ground at less blur inside a box round the hand, and draw the
  outline finer there (`HAND`, `HAND_EDGE`) (2026-10-07).
- The house weight is a share of the longer side, so a drawing wider than
  tall gets heavier lines against its figures: on pl. XX her hem's border
  ran into the pleats. All three drawings use the plate's own weight
  (`weight="own"`, 0.14-0.17% of the longer side) (2026-10-07).
- On the dark theme a 2.5 px outline fills a thin part (a tuft, a leaf's
  tip, an ear, a toe) and leaves it no clay: cap the outline at 0.6 of the
  part's half-width. Mark all the ground as open (`held = ground & ~fig`),
  not only the pockets the figures close in, or `trace_svg`'s clay rim for
  thin lines strays onto it (a notch of clay at the horse's mouth)
  (2026-10-07).
- A plate printed across two pages: the Getty copy on the Internet Archive
  is bound tight and the gutter swallowed the bull's head. Heidelberg scans
  each double plate as one opening (vol. II is `lenormant1857bd2`; its IIIF
  manifest labels plates "Planche 54"). Look for another copy before you
  draw across a gutter, and ask John before you download it (2026-10-07).
- Flattening the fold (`level` in `alcestis.py`): the frame's top and
  bottom edges are printed straight, so straighten them column by column,
  take out each page's tilt, and widen each column near the fold by the
  height it lost. The page also slopes away from the camera there, which
  narrows it further by an amount the edges cannot show; John chose the
  estimate at which the bull's forehead dots come out round (camera at
  1 m), after two narrower ones looked "still too smooshed". A photo of
  the vase did not settle it: the bull's head sits where the vase turns
  away from the camera (2026-10-07).
- The handoff's facts were wrong in places; the sources put them right. Vol.
  II's title page reads 1857, not 1846. Pl. LIV's animal is a bull and its
  tree a palm (Élite II pp. 160-161, and the British Museum), not a cow and
  a bare tree; the vase is a Campanian neck-amphora, British Museum
  1867,0508.1122. On pl. XX Poseidon holds a sceptre, not a trident. The
  plates are signed in their margins (pl. XX "L. Petit, sc."; pl. LIV "A.
  Rey, sc." and "Lith. de Bineteau") (2026-10-07).
- Heidelberg's viewer pages now sit behind a bot check. Its IIIF manifests
  (`/diglit/iiif/<id>/manifest.json`) give the licence and the page labels,
  and IIIF image links open in the browser for reading the text pages
  (2026-10-07).

- Ion (II, pl. XLVI, Apollo on the tripod with the Pythia and a girl), made with PhotoCraft: about three
  and a half hours over five passes, approved by John 2026-10-09. `tools/ion.py` (2026-10-09).
- Don't carry the faint-line finder over from Trojan Women without looking: this plate prints every line
  solid, and the finder drew the paper's grain as short strokes beside the folds (John: "you added a lot of
  strokes that weren't in the original"). Turned off, 335 pieces went and none was a printed line
  (`FAINT_ON`) (2026-10-09).
- Draw the outline on the black ground outside the clay, not on the clay (John: "the black lines for the
  outer clay bands should be drawn on the black background, not on the clay itself"; every outline). Thin
  clay parts (the hair's reserved lines, fingers, the laurel) then keep their full width with no cap
  (`EDGE_OUT`) (2026-10-09).
- The hair prints as dark as the ground and is larger than the ground's size limit: ground must also reach
  the crop's edge, and the hair's clay line is found at fine blur (`FINE`) (2026-10-09).
- A plate printed sideways and photographed a little askew: fit the panel's four edges as lines on their
  straight stretches (start each search on the paper, past the scan's dark margins) and map the corners to
  a rectangle (`level`, a homography) (2026-10-09).
- John marks corrections in PhotoCraft on a .pcraft with the plate, the drawing in red and an empty marks
  layer; save it from the app before reading it (an unsaved file reads empty). Some marks land on the
  drawing's layer: read both layers by colour. Build the file with `photocraft-cli serve`
  (`--automation-read-root`/`--automation-write-root`, relative paths): open, copy, paste in place, new
  layer, save. Keep each round's marks in its own file, applied in order (`MARKS_FILES`) (2026-10-09).

- Helen (III, pl. LVII B, the warrior leading away a bride), made with PhotoCraft: about an hour and a quarter
  over two passes, the credit included, approved by John 2026-10-10. `tools/helen.py` (2026-10-10).
- The Élite's reading of a scene can differ from its own source's and the museum's. Its plate list and text
  say Menelaus taking Helen home; Gerhard, whose plate it copies (AV I, Taf. XLVI), and the British Museum,
  Beazley and LIMC say Idas and Marpessa. The Beazley Archive's record (it opens in the browser pane) cites
  both plates and so ties them to the vase. John: keep it for the play, titled as the museum reads it
  (2026-10-10).
- Weight "own" sets every line to the median width: 1 px lids ran into the pupil, and the dress's crosses and
  stars came out as blobs. Pass the eyes and small marks standing alone to `trace_svg` as `dots` (traced at
  their own size) and take them out of the main ink; a pupil that still traced as a ring is drawn from points
  read off the plate's grey values (`EYE_LINES`, `EYE_PUPIL`) (2026-10-10).
- Dots paler than the line threshold (a veil's dots, a hem's beads): keep small marks whose core is darker than
  60; the dots' cores read 0-30, specks of the print 90 and up. The local-contrast finder bridged some to the
  line beside them: cut its thin-only ink near the dots (`DOT_*`) (2026-10-10).
- Where hair leaked into the ground through a gap in its clay line, the fine-blur box (`FINE`) made it worse
  (the diadem went with it). A least-cost path through the dark from the hair to the ground found the gap
  (3 px, where the diadem's lower line stops short of the forehead); a wall there fixed it (2026-10-10).
- Look for dark areas printed a little lighter than the ground (grey 17-40 against 5-10) with no clay line
  round them: John asked "is there hair above the crown?", and there was. Stretch the darks to see them;
  the edge is where the plate turns lighter than the ground, measured column by column (`CROWN`). Ground that
  fingers close off against another figure is a pocket: it came out as black paint (John) (2026-10-10).

- Phoenician Women (I, pl. XXVIII, Europa on the bull and Phoenice), made with PhotoCraft: about an hour and a
  quarter over four passes, the credit included, approved by John 2026-10-10. `tools/phoenician_women.py`
  (2026-10-10).
- Pin the line weight after the first pass (`WEIGHT`, pass 1's median width over the longer side). With
  weight "own" his marks moved the median one pixel step and thinned every line on the plate. After each
  round, diff the whole plate against the last pass: only the marked places may change (2026-10-10).
- A band of solid paint that touches the ground (a girdle meeting the black at the hip, the band tied round a
  bull's tail) is read as ground: it came out as two outlines with the clay showing between. Wall it off
  where it meets the ground (`WALLS`), and check the masks: the first wall stopped short and the band still
  leaked past its end (2026-10-10).
- A short line John draws across such a junction means "this is paint", not a line to draw: twice it went in
  as ink. Use it as the wall and drop it from the marks (`DROP`); ask in one line when a mark could be
  either (2026-10-10).
- Clay the figures close in can be the vase's ground even where the plate prints it clay (under Europa's
  arm): John's call; open it with a point inside (`OPEN`) (2026-10-10).
- The .pcraft round trip: build it with `photocraft-cli serve` (open the plate and the red drawing, copy,
  paste in place, name the layer, add an empty "John marks" layer, save); `doc.select` takes `index`. Read
  the layer ids with `photocraft-cli info` before exporting: he may rename or duplicate his layer ("John
  marks copy"). Hide all layers but his, save as PNG, and check the red layer for his edits too
  (2026-10-10).

- Iphigenia at Aulis (II, pl. XC, Artemis pursuing a woman with a child, read by the Élite as Helen with the
  infant Iphigenia), made with PhotoCraft: about two and a half hours over two passes, the credit included,
  approved by John 2026-10-10. `tools/iphigenia_aulis.py` (2026-10-10).
- A big crop is slow: 2940 x 2032 plate px at UP 3 took 11 minutes and 2 GB a run. Fix the masks on
  sub-crops (the same tool on a box, the edge rule and out-of-box points dropped: seconds a run) and run the
  whole plate only to check and to show (2026-10-10).
- Bands of paint along a garment's edge that touch the ground (a mantle's borders, a sleeve's border) are
  too many and too long to wall one by one. Find them as the thin parts of the ground (what an opening of 8
  plate px takes away), sheet every one on the plate, and mark the bands with a point each (`PAINT`). John
  sorted the sheet in one look: the gaps between fingers and a strip between arm and drapery are ground.
  After the bands go, relabel the ground: pieces they cut off are paint too (2026-10-10).
- The gap joiner took the larger dots of a dress for broken line ends and bridged pairs of them, or ran a
  line on to a dot. Drop its pieces that touch only small marks or touch a dot (`JOIN_SMALL`, `JOIN_DOT`)
  (2026-10-10).
- A hair wall can close off ground: Artemis' hair walled, the black between her raised arm and her back
  became a pocket and filled as paint. Check the full drawing after every wall (`POCKETS`) (2026-10-10).
- A bowstring printed as black paint over the black ground (grey 3-6 against 7-9): place each straight run
  where the mean grey along it is least, searching half-px shifts of its ends (`STRINGS`) (2026-10-10).
- Wealth (III, pl. LVIII, Plutus with the cornucopia), made with PhotoCraft: about forty minutes over two
  passes, the credit included, approved by John 2026-10-10. `tools/wealth.py` (2026-10-10).
- Added white (hair, beard) over the black ground, no black outline on the vase: show John a small test of each house
  way on the head first. He chose white paths (as Clouds) with a black outline on the ground in day mode only, so the
  hair does not vanish into a light page: `trace_svg(day=...)` puts the lines in that area on a path of class "day",
  which the dark theme hides. The white path runs half a line onto the ground, under that outline, or the dark theme
  shows a rim of clay where the body's edge sits under the hidden line (2026-10-10).
- The white: light and not red (red less blue, PhotoCraft's Channel Mixer); a grey threshold alone counts the soft edge
  between the white and the black as clay and draws an outline round the hair (2026-10-10).
- A long staff crossing the ground with black bands (the sceptre): fit its two edges as lines where it is clear of the
  bands (sub-px, where the grey crosses 80) and wall along both a px out; the staff can widen along its length (here
  10 to 13 px), so fit each stretch on its own (`SCEPTRE`) (2026-10-10).
- Boxes that help on one plate can hurt on the next: a FACES box broke the eye's lid into pieces and a HANDS box lost
  the thumb under the cornucopia. The eye drawn on points read off the plate's grey map came out right at once
  (`EYE_LINES`), as Helen's (2026-10-10).
- A thin pale line down the plate through the figure is a crease if it runs on through the margins (dark on the paper):
  it draws nothing, as ground on the black and clay on the clay (2026-10-10).
- Check a close-up's panel offsets before reading coordinates off it: the first box to drop the line John flagged
  missed it by 20 px (2026-10-10).

- Knights (II, pl. XCIV, the Chiron vase: three comic actors at a stage), made with PhotoCraft: about an hour and a half
  over two passes, the credit included, approved by John 2026-10-13. `tools/knights.py`, on `iphigenia_aulis.py` and
  `wealth.py` (2026-10-13).
- Ask the edge calls before drawing, on a numbered sheet of the plate: John kept the post and roof, the bundle and the
  festoon, and dropped the names, in one answer (2026-10-13).
- This plate prints faint lines (fingers, toes, folds, the ladder's long lines: grey 100-150 on clay 200, a plate px
  wide). The main finder's blur broke them into dashes and lost some (John: "don't have broken ink lines", "don't
  ignore fainter lines (like on toes and fingers"). What worked: local contrast at less blur (0.35 plate px, the
  closing over 5) at two levels, the lower one kept only where it runs 5 plate px clear of the lines already found
  (shorter ones were blobs); then a joiner for ends that face each other, or face a line, where the fine contrast
  holds along the gap (`FAINT*`, `JF_*`). trojan_women's `join_breaks` skips dashes shorter than 3 plate px. Sheet
  every added piece and join on the plate first; then a map of the plate's line centres the ink misses came to 0
  (2026-10-13).
- Two hand-placed end points for a long faint line that bows slightly put a least-cost path off the line by up to 8 px:
  the joiner did it better (2026-10-13).
- A wall can cut off ground that reached the open black only through the band it walls (the hem): after every wall,
  list the large paint areas and mark the pockets (2026-10-13).
- Light flecks of the print inside a pocket become clay islands after the hole fill and are drawn as dots on the black:
  drop clay pieces under 30 plate px (`SPECK`, as Electra) (2026-10-13).
- The PhotoCraft file for John at the tool's 3x grid ran to 45 MB with the plate enlarged bicubic; enlarged by nearest
  neighbour (his plate-pixel grid) it was 19 MB (2026-10-13).
- John's green loop round a black area meant "this is ground", not "remove the ink": read as a pocket of ground
  (`POCKETS`), his blue laid in as ink (`MARKS_FILES` with green off) (2026-10-13).

### Laborde, *Collection des vases grecs de M. le comte de Lamberg* (colour aquatints, red figures on a dark ground)

- Electra (Sophocles) (I, pl. VIII, Orestes brings Electra the urn), made with PhotoCraft: about an hour and a half
  over two passes, the credit included, approved by John 2026-10-10. `tools/electra_soph.py` (2026-10-10).
- The Élite method carries over unchanged: ground grey about 60, clay 160, the same thresholds at UP 3; a full run
  takes 25 seconds. The leaf holds two plates: fit each panel edge on its own window (`EDGES`) (2026-10-10).
- The band the figures stand on bows up about 10 px under them. A ground line drawn straight between clear stretches
  ran up to 3.5 px off under the feet and cut through the 1-3 px of dark between the toes and the band: the toes came
  out open below (John: "look at the toes"). Measure the band's top in every column, going up from inside the band,
  and draw the sole as a band of line width along the cut wherever a figure stands on it; the outline alone left nubs
  under the gaps between toes (2026-10-10).
- The cut must sit a little above the band's soft edge (`GROUND_IN`): below it, a sliver of clay ran from Pylades'
  feet along the band to the crop's edge, and the edge rule dropped the whole figure (2026-10-10).
- The aquatint's grain leaves light specks in the ground that the ridge term keeps: drop clay pieces under 20 plate
  px once the figures are cut (`SPECK`). A FACES box took the grain on the clay as lid lines; one eye drawn on points
  was enough (2026-10-10).

### Gerhard, *Etruskische und kampanische Vasenbilder* (coloured lithographs, red figures on black)

- Libation Bearers (Taf. XXIV, the whole frieze: four figures, a throne and a footstool): about four
  hours' work over three passes, approved by John 2026-10-07. `tools/libation_bearers.py`.
- One leaf photographed open, the frame bent by up to 10 px (its bottom sagging, its sides leaning
  out). The four edges fitted (cubics top and bottom, lines at the sides) and mapped to a rectangle
  by a Coons patch (`level`) run straight within 1 px (2026-10-07).
- The faint glaze lines (anatomy, folds) print pale brown, 15-20 grey levels under the clay, too
  faint for the line finder in grey; in the blue channel they stand 30-55 under it (the clay is
  orange). Find them there, keeping pieces that are long, thin and apart from the black lines
  (`FAINT`) (2026-10-07).
- Breaks in the print: line ends facing each other across up to 10 px are joined where the plate's
  blue-channel contrast holds at 7 or more all the way across (true ends measured 0-6). The facing
  pairs fell from 158 to 66 (`JOIN_*`) (2026-10-07).
- Eyes and fine curls at the paint's own width by half maximum (darker than halfway between the
  line's core and the clay round it): local contrast drew them heavier than printed, a fixed
  threshold lost the lower lids. Electra's ringlets, clay rings on black hair: the same rule turned
  over (`half_max`, `RINGLETS`) (2026-10-07).
- The outline cap from alcestis.py (0.6 of a thin part's half-width, read off the skeleton) thinned
  the outline to nothing beside notches, where the skeleton puts out a spur: about 20 stretches broke
  up in tracing, one of which John found. Floor it at 1 plate px (`EDGE_MIN`). A check for the
  figure's edge with no line within 1.5 px found 25 gaps, then 2 (2026-10-07).
- Weight "own" is measured on the ink: with John's traced strokes added (wider than the plate's
  lines), every line came out heavier (median 2.4 to 3.0 px). Pin the first pass's weight
  (`WEIGHT`) (2026-10-07).
- Clay rims on the dark theme only along a thin light line at least 8 px long with paint on one
  side and ground on the other: a looser rule put clay rings round the leaves of Electra's wreath
  (`RIM_*`) (2026-10-07).
- The black ground printed dark brown inside a figure (under Aegisthus' jaw) came out as clay; John:
  "the blob here of clay is not part his body". Leave such ground open (`OPEN`) (2026-10-07).
- The vase went from Berlin (F 2184) to Moscow after the war. The Beazley Archive (no. 202912) gives
  Pushkin Museum 6528.3, the museum's own page inv. АВ 3742; the credit cites both (2026-10-07).

### Contour plates with no black ground (Hoernes, *Archäologische Zeitung* 1877: black pen lines on paper)

- Rhesus (AZ 35, 1877, Taf. 5, two youths on a night raid), made with PhotoCraft: about an hour and fifty minutes
  over a style test and one pass, approved by John 2026-10-10. `tools/rhesus.py` (2026-10-10).
- Compare every scan of the plate at full size before choosing: the IGNCA scan's 5120 px were JPEG blocks (the face
  mush), the Getty copy's 2365 px photo sharp. Register one to the other (SIFT): within 2 px under a similarity, the
  photo was flat. The Internet Archive's "orig" captures are numbered by leaf, not by viewer page: read the
  scandata (n228 was leaf 229; leaf 228 was blank). PhotoCraft cannot read JPEG 2000: convert to PNG first (2026-10-10).
- Lines at half maximum (darker than halfway between the paper and the line's darkest px nearby): local contrast
  alone took in each line's soft edge, and the hair's strokes ran together (2026-10-10).
- No ground to cut from: the figures' area is the paper the lines close off. The pen outline breaks at joints and
  where a line stops short of the next, so seal the gaps: open the paper by a disk (6 plate px here), take the
  pieces left as areas, and give every paper px to the nearest by a watershed on the distance to the ink, so slivers
  of ground stay with the ground. Then mark the pockets of ground the figures close (`POCKETS`) on a numbered map of
  the areas laid over the plate, not on a flat colour map (2026-10-10).
- An opening seals gaps narrower than its disk, but not a passage just as wide: when the lines were thinned the
  right youth leaked through an 11 px break behind his knee. Find a leak by the shortest path inside the opened
  paper from a point well inside the body to the crop's edge; it crosses the line at the break. Wall it
  (`WALLS`, for the area only, not drawn). A body that has turned to ground may instead have joined a pocket:
  check what area the body's point lands in before searching (2026-10-10).
- Spear shafts (12-22 px between their edge lines) are too narrow for the seal: fit each shaft's centre and width
  to the midpoints between its edge lines, read across it every 4 px from rough ends (`SHAFTS`) (2026-10-10).
- Drop specks by distance from the figures, not by touch: a toe's tip curl stands just off the foot (2026-10-10).
- John read a strip I took for cloak (between the forearm, the cloak's edge and the spear) as ground; he marked it
  on the whole dark view. On a contour plate, show the dark theme of the whole group early (2026-10-10).
- Weight: John asked for heavier lines than the plate's own (0.084%), then chose 0.12% of 0.12, 0.16 and the house
  0.225%: at 0.225% the hair's strokes ran into blots (2026-10-10).

- Persians (Heydemann, Hallisches Winckelmannsprogramm 8, 1883, the upper band of the folding plate), made with
  PhotoCraft: about seven hours over three days and four passes, approved by John 2026-10-12. `tools/persians.py`
  (2026-10-12).
- "Crisp and precise" (John): the lines at the plate's pen width, not the house weight. Show an A/B of two
  weights on one head; he chose the thinner, 0.8 plate px (2026-10-10).
- Shading finer than the scan resolves (hatch 2-3 px apart at 239 dpi) reads as a grey tone and traces as blobs.
  Its spectrum gave no clear peak; ask how to draw it. John: evenly, in its own kind. Hatch as thin lines that run
  along each band and follow both its sides (the share of the way across from one side to the other, split at
  the band's ends or along its sides; a line added where the band widens, every other one stopped where it
  narrows), drawn only inside the outlines; stipple as even dots that fit whole; a rim hatched along its curve.
  Straight hatch at one angle and lines as offsets of the outline were both rejected (2026-10-10).
- The area of each shaded patch: a polygon drawn round it, and inside it the plate's darker px, blurred, closed and
  opened; the plate's lines there kept only where they are long or at the patch's edge (the shading's own specks
  dropped) (2026-10-10).
- A wide frieze traced at the house 4000 px broke its finest scrolls when the lines were thinned: trace at 6400 px
  tall (`TRACE_H`). A run is then 11 minutes and over 2 GB: on this 8 GB Mac it crawled for an hour while other
  sessions held the memory. Check `vm.swapusage` and the other sessions' Python jobs before a full run
  (2026-10-12).
- Ground marked by area: a mark's whole enclosed area took in clay where a gap in a line joined it to the
  drawing (a horse's mane, a muzzle). Cut each marked area at its necks (`NECK`, 5 plate px) and keep the piece
  round the mark. And read "colour it in" marks on the sealed watershed areas, not the raw paper: through the
  pen's gaps the raw paper is one area with the background (2026-10-12).
- Show ground choices as numbered areas over the plate in day colours, not on the dark view: John ruled them by
  number in one message (2026-10-11).
- John's PhotoCraft marks, third form: blue ink, yellow clay, green "erase or ground". Read green by what it
  covers: ink mostly under it goes, the paper round it is ground (2026-10-12).
- Field ornaments on a contour plate (stars, plants, ground dots) are painted clay on the vase: clay shapes with
  no lines on the dark theme, lines on the light (`day`, `add_clay`); John kept it so when asked (2026-10-12).
- Paired fine strokes the scan runs together (a greave's edges) came out as blobs with holes: fill the slits and
  draw each pair as one line along its middle (`PAIRS`) (2026-10-12).

- Eumenides (Bötticher, *Der Omphalos des Zeus zu Delphi*, 1859, fig. 1, the whole plate: Orestes at Delphi), made with
  PhotoCraft: about two hours and fifty minutes over a style test and three passes, approved by John 2026-10-12.
  `tools/eumenides.py`, which also cuts the Aeschylus home Pythia from the same drawing (2026-10-12).
- Look for a larger scan, then compare at full size: Munich's copy (MDZ, 1.3x the px) was softer than Heidelberg's, and
  the plate's own source (Jahn 1839, Taf. I, in a library PDF) smaller. The plate's text names its source: read it
  (MDZ serves OCR per page as hOCR beside its IIIF manifest) (2026-10-12).
- A frieze the columns, rules and ground line close is all closed paper: every field area is a pocket. Mark them on
  the numbered area map at once (here 45 points), then check the dark theme of the whole plate for figures turned to
  ground: one point landed on Apollo's latticed boot, whose cells are smaller than the seal (2026-10-12).
- "Crisp, detailed" (John): faces about 35 px tall and the omphalos net's 1 px hatching came out as blots at the line
  weight. Found again inside boxes at less blur and a narrower core, and traced at their printed width as `dots`, with
  the main lines run a few px into each box so no seam shows where a box cuts the hair. No blur at all broke the
  lines and took in the paper's grain (2026-10-12).
- Paper the seal leaves unseeded (a sword's blade, the lattice cells) is clay unless it reaches the crop's edge; leaves
  narrower than the seal are sealed again inside a box at a smaller disk (a closing of the ink rounded them off and
  missed half) (2026-10-12).
- A filter that drops marks lying off the figures (a speck by a nose) also dropped a pale tassel hanging on the field:
  John found it. Exempt the parts that hang free (`net`), and fill them as clay (2026-10-12).
- Cutting one figure from an approved whole-plate drawing: her body is her own clay inside the cut and the lines that
  border it, not the whole plate's body, which counts every line touching clay (Apollo's shin line came in with it)
  (2026-10-12).

- Assemblywomen (Heydemann, *Vase Caputi mit Theaterdarstellungen*, Hallisches Winckelmannsprogramm 9, 1884, Taf. I:
  three comic actors), made with PhotoCraft: about four hours over two sittings, a style test and four passes, approved
  by John 2026-10-13. `tools/ecclesiazusae.py` (2026-10-13).
- The same series as Persians, but paler pen lines: at Persians' thresholds and half maximum the stage's posts broke into
  dashes and a 17 px gap opened in the stage's edge. Lower the local-contrast thresholds and take the line at 0.4 of
  the way to its core (2026-10-12).
- "Crisp and not staticy" (John): lines found as printed carry the scan's grain along their edges and read as pencil.
  Redraw every line along its centre at its printed width smoothed along it (as frogs.py), the width not read near a
  junction, where it swells. Keep out of the redraw what is solid (studs, a stippled hem band: closed and filled) and
  the pupils, which a centre line drops (a box per eye; a rule for solid marks in the heads took the hair's shading
  too). Seal the areas on the printed lines as well as the redrawn ones: the redraw opens hairline gaps and a door's
  panels went to ground (2026-10-13).
- Weight: John chose 1.6 plate px, twice Persians' 0.8, from an A/B of 0.8, 1.2 and 1.6 on two heads and drapery: 0.8
  "looks too much like a pencil drawing". Ask early on a contour plate (2026-10-13).
- Trace a wide plate tall (here 7200 px): at the house 4000 px the thin lines broke into dashes once weighted (2026-10-12).
- A beard printed as fine grey strokes went in as a stepped grey wash, as Frogs' goatee (John: "brushstrokes like with
  hair on other comedy plates"). The finer head finder from Eumenides (less blur, a narrow core) took the grey shading
  between curls for strokes and speckled the hair: not used (2026-10-12).
- The vase's frame line ran under the stage's posts, joined to them by the finder: drop the ink below a polyline read
  off the plate between the posts, not the pieces lying mostly below it (2026-10-12).
- John's marks all blue (ink) this time: laid in as `dots` at their own size, so the pinned weight did not move; the
  whole-plate diff showed changes only at his marks, and where his lines closed the string of figs, now clay
  (2026-10-13).
- Three test runs at once on this 8 GB Mac with other sessions running took ten minutes each and filled the swap: run
  A/B variants one at a time (2026-10-13).

- Oedipus Tyrannus (Raoul-Rochette, *Monumens inédits* I, 1833, pl. LXXVIII: the Sbani vase's lower row), made with
  PhotoCraft: about two and a quarter hours over the scan search and four passes, approved by John 2026-10-13.
  `tools/oedipus_tyrannus.py`, on `ecclesiazusae.py`'s rules (2026-10-13).
- Go back to the plate a copy was made from: Benndorf's 1890 plate cites Raoul-Rochette's of 1833, which Heidelberg
  serves with the figures 2.9 times as tall and sharper (the bird on the sceptre, the throne's winged figures). Read the
  text too: Raoul-Rochette reads the scene as an initiation; the Oedipus reading is Müller's and Welcker's, in Overbeck
  1853 (p. 62), whose text is on the Internet Archive. Heidelberg's text pages sit behind a bot check; their IIIF
  images open (2026-10-13).
- A lithograph prints the hair, wreaths and beards solid black. The centre-line redraw turned them into outlines: keep
  what an opening wider than the pen lines leaves (1.5 plate px) as printed, and the small dots too, which a centre line
  drops (`SOLID_R`, `DOT`) (2026-10-13).
- A row cut from a two-row plate: figures rise through the beaded line between the rows. Drop the pieces lying above it,
  but keep those lying wholly inside a box round each head; keeping every piece that touched a box kept the shield and
  feet of the row above. Where the rows truly touch (the staff top in a robe's hem), cut along a polygon (`ROW`, `KEEP`,
  `CUTS`) (2026-10-13).
- John's marks, fourth form: green ground, yellow "that area bounded by ink lines is clay", blue ink. A mark rules the
  closed area it mostly lies in (at least 0.3 of its largest share), so a stroke that strays over a line does not rule
  the next area as well; unsealed paper narrower than the seal is ruled the same way (`ruled`) (2026-10-13).

### Saglio, *Gazette archéologique* 1887 (chromolithograph, black figures on orange clay, thinned glaze)

- Cyclops (pl. 1, the blinding of Polyphemus, Louvre F 342), made with PhotoCraft in the black-figure silhouette: about
  two and three-quarter hours over a style test and three passes, the credit included, approved by John 2026-10-12.
  `tools/cyclops.py` (2026-10-12).
- The Internet Archive's original capture was far larger than its viewer page (6000 x 4000 against 2635 x 3625) and
  the book was photographed upside down: a half-turn, not the quarter-turn the preview card gave. Viewer page n418 was
  leaf 419. Each "orig" JP2 can be pulled alone from the tar's listing (690 KB here) (2026-10-12).
- Thinned glaze on the clay (smoke, flames) read as stepped washes, as the blood (John chose them over one flat wash).
  The smoke is redder than the clay: red less 1.6 green (PhotoCraft's Channel Mixer) parts it from the clay and from
  every mix of black and clay. The flames print as a dark stipple, so read them by darkness at a heavy blur (7 plate
  px); black inside the fire is only the solid black, opened and closed over the dot screen and smoothed. A lighter
  blur left the wash blotchy and the loops pinholed (John: "Clean the fire") (2026-10-12).
- Added white on this plate (the rock's patches) went in as ink (John: "those are patches but make them ink"), their
  reddish printed rims with them; keep the white finder in a box round the rock, or it takes a beard's light incision
  for white (2026-10-12).
- Faint brown lines on the clay (the hats' brims prolonged, which Saglio says are worn): least-cost paths along the
  dark through points read off the plate at 3x, smoothed along their length, in the wash (2026-10-12).
- A part lying over the border band (the club's end): its outline read off the plate and filled, the band's clay
  round it kept from becoming light marks (2026-10-12).
- The Louvre's collection site answered with a CAPTCHA; the Beazley Archive's record opened in the browser pane after
  its automatic check (2026-10-12).

### Smith, *Journal of Hellenic Studies* 2 (1881) (chromolithograph, black figures printed olive on tan clay, added red)

- Birds (pl. XIV, fig. B.1, the piper and the two bird dancers, British Museum 1842,0728.787), made with PhotoCraft in the
  black-figure silhouette: about an hour and twenty minutes over a style test and one pass, the credit included,
  approved by John 2026-10-12. `tools/birds.py` (2026-10-12).
- The plates of JHS 1-8 were issued apart from the text: the Getty's 400 ppi scan of vol. 2 on the Internet Archive has
  none, and HathiTrust refused curl. JSTOR's Early Journal Content copy on Zenodo has the plate as one 300 ppi JPEG
  page (`pdfimages -j`), heavily compressed: its 8 px blocks show at 4x (2026-10-12).
- The black prints olive, close to the clay in grey (141 against 155). No one channel parts them; a linear
  discriminant over k-means classes of the panel gave red less 0.18 green (the clay 160-166, the black 133, each
  about 5). Light incisions pass that test too, and broad ones survive the opening that keeps thin marks out of the
  ground: count a clay area as ground only if some px of it under the clay's grey lies 3 px deep in it (2026-10-12).
- Added red in its own path, in the plate's median red, no outline (John: "match the bright red with red"). PhotoCraft's
  Channel Mixer constant 50 adds 127.5 (2026-10-12).
- Close hatching that prints pale (the beards under the beaks) falls into the ground: give each band a polygon inside
  which all is figure, and read the hatching on the plate smoothed along its own angle (Motion Blur 5 px) by a white
  top-hat over 2 px; the plain 1 px top-hat lost it (2026-10-12).
- Paint darker than the black (the right dancer's arm strokes in black pigment): grey blurred 1.5 px, under 124,
  smoothed, drawn as thin clay lines on their centres (John). Small clay spots closed in the black (incised circles)
  are light marks, not ground, or the dark theme shows them as holes (2026-10-12).
- The white page round the frame: blue over 200. The print's soft edge where the bands meet the page, and along the
  red lines, reads as thin black: drop black thinner than 3 px near the page, and all black below the ground line. A
  fill of holes in the figures over the whole panel (the frame encloses it) brings the print's specks back: drop
  small pieces after it (2026-10-12).
- The whole panel at 4x does not fit in 8 GB; 3x (38 Mpx) peaks at 2 GB and runs in about 6.5 minutes, the oriented
  smoothing read one blur at a time (2026-10-12).
- The British Museum's collection page and the Beazley Archive's record both opened in the browser pane (WebFetch got
  403 and a bot check) (2026-10-12).

### Photos of vases (red-figure, taken off the vase with `tools/vase_unroll.py`)

- Acharnians (Würzburg H 4689, the seated warrior; four ArchaiOptix photos), made with PhotoCraft:
  about an hour and a quarter; approved by John on the first pass, then one fault he circled
  (2026-10-08). `tools/acharnians.py`.
- The CVA settles what a photographer's file page only reports: Würzburg 4's entry for H 4689 gave the
  painter and date, the provenance, the mask types, and that the warrior's knee is overpainted. German CVA
  volumes are open on publikationen.badw.de (PDF with a text layer: `pdftotext`, then search the
  inventory number) (2026-10-08).
- `vase_unroll.silhouette` wants a plain light background on both sides; in a museum case (a lekythos
  beside the vase, a chair behind it) it found nothing. Give rough guides to the outline and take the
  strongest light-to-dark step near them (`outline`); the band's edge likewise (`band_edge`) (2026-10-08).
- Clay against glaze by red less blue (PhotoCraft's Channel Mixer, monochrome [100, 0, -100]): the
  glaze's white sheen reads 0 with the glaze, clay 90-140 (2026-10-08).
- Where the sheen lies over the figure's edge, lay a second photo, lit otherwise, onto the same flat
  and compare the edges: decisive, and it overturned my own reading of a close-up (2026-10-08).
- A painted stroke that runs up to the figure's edge meets the ground's black there, and the drawing
  takes it for ground: the shield's top ray came out a hollow sliver (John: "this circled part should
  be black ink"; "looks terrible in day mode"). Wall it along the edge (`WALLS`), and look in the light
  theme for any band drawn hollow beside the outline (2026-10-08).
- On a worn photo, local contrast at the Gerhard plates' radius drew stains, the edges of white
  scratches and the brown strip along a mend. Cap the grey at the clay's level first (Levels, input
  white 140: exact; Curves bends the tones below its points), keep long thin pieces only, and keep off
  the mend (`FAINT`, `MEND`) (2026-10-08).
- Remove specks before joining breaks: glaze specks left in a flaked gap counted as a line crossed and
  blocked the join (2026-10-08).
- A second figure from another photo: fit that photo's camera to the finished vase model alone (profile and
  other cameras held), lay it onto the same flat, and check where the two photos overlap (here 2.5 px at the
  spear's tip). Keep the first figure's pipeline untouched, so the approved drawing cannot change, and pin
  the line weight to the approved width: weight "own" is a share of the longer side, and the wider canvas
  thinned every line (2026-10-08).
- Traced at 0.4 of the work px, a line's thin neck vanishes: eight breaks with ink across them, the
  approved warrior's belt among them, missed earlier because the gap check's angle limit dropped the pair.
  Thicken every line to a minimum width along its centre before tracing (`NECK`) (2026-10-08).
- White paint (hair, beard): no black outline, as on the vase; draw the edge along it in the tone
  (John: "the hair is all white strokes of paint, no black outline"). Its strokes: the black between the
  curls is ground (found at fine scale, but only inside the hair's outline: over the face the fine opening
  ran the ground through the jaw line and cut the head off), and the wash in steps following the paint's
  whiteness, as Andromache's blood. Threshold- and ridge-finding of single strokes on worn paint gave
  blobs and noise; John chose the stepped wash over a solid one (2026-10-08).
- Worn pale clay passes for white paint in grey and in red less blue alike; a sharper photo of the same
  spot (here 02) told them apart, and the hair's boxes were set to leave the jaw out (2026-10-08).
- Clouds (Louvre CA 7249, a phlyax scene: the master and his slave), from Marie-Lan Nguyen's photo: about
  eight hours over three passes, approved by John 2026-10-08. `tools/clouds.py` (2026-10-08).
- The source photo showed none of the vase's outline. The museum's own whole-vase photo gave the profile
  (outline, the line under the checkers, the strip under the ovolo as a ring), and the close photo's camera
  was fitted to points matched with it, its focal length from EXIF. Ask before downloading museum photos;
  use them only for the fit and to fill what the source cuts off (2026-10-08).
- A second figure further round the vase: flatten its part on its own and join the two at a seam in the
  ground. One wider flat moved the first figure by up to 16 px, which would have moved every point
  already measured on him (2026-10-08).
- Red less blue (PhotoCraft's Channel Mixer, which matches the arithmetic exactly) parts clay from glaze,
  but worn glaze photographs grey-blue and washed-out clay pale: ground is dark or bluish, not merely
  "not orange", or the faint lines at the feet join the ground and cut a foot off (2026-10-08).
- The painter's brown stripe of glaze along an outline drew a second outline inside the first: set the
  figure's edge at half the local clay level, and in the stripe's boxes keep only clay lighter than grey
  125 (`STRIPES`) (2026-10-08).
- Lines by local contrast came out beaded: fill pinholes, smooth the mask (Gaussian in PhotoCraft, cut at
  half), prune spurs, and redraw each line along its centre at its own width smoothed along the line
  (`even_lines`) (2026-10-08).
- Colour (John's asks): skin clay in both themes, clothes as washes, white hair as white strokes. Where no
  painted line parts two areas (hair from face, beard from shirt, arm from sleeve), don't guess: send
  John close-ups and register his marked screenshots to the flat (SIFT, or template matching for a
  screenshot of the drawing); his lines live in a data file (`clouds_marks.json`). Edges he did not
  draw follow the drawing's lines by a least-cost path (2026-10-08).
- White paint that the photo shows only as a paler, worn area reads as grain if its strength follows the
  photo alone: give it a floor (0.65 opacity), smooth it, and fade it toward the areas beside it, so it
  has no hard edge; John: "Thicker basically" (2026-10-08).
- John's marks arrive as chat images; not all reach the session's image folder. His Desktop holds the
  screenshots too ("Screenshot ... PM.png"): match them to the chat by size, and say when you use one he
  did not send (2026-10-08).
- Philoctetes redone with PhotoCraft (Met 56.171.58; the 2026-10-03 tool's flat and cut points kept): about six
  hours over five passes and two rounds on the hair, approved by John 2026-10-09. `tools/philoctetes.py` (2026-10-09).
- Brown hair as brushstrokes: only the brown paint (the clay between strokes left clear), a soft stepped tone for
  the mass with the curl strokes sharp on it (one blur for both smeared the curls into blotches); darker toward
  a black top of the head and drawn into it as very dark layered strokes, not solid ("he's not wearing a hat").
  No outline round the top and back of the head where a clay band rings it: on the light page the band goes to
  the page. Glare on glaze passes for light brown: measure the black top and a glossy brow on a second photo
  without glare, and require red less blue for the brown (2026-10-09).
- A dark brown band (a shadow at the foot) drawn as a wash following the paint reads better than solid black;
  the rock's brown washes too, as their strokes (2026-10-09).
- A part outside the scene's flat (the tree's boughs on the shoulder): flatten it on its own and lay it on by the
  similarity that fits the two flats along the seam (sampled both sides of the cut line; 0.65 px). One map for
  the whole frame missed by up to 17 px, the scene's flat bending at its edge (2026-10-09).
- With no outline at an edge, `trace_svg` crops to the ink and cut off the head: pass the area as `extent`
  (2026-10-09).
- Oedipus at Colonus redone with PhotoCraft (Green's pages and a found photo on Taplin's plate; the 2026-10-03
  registration, cut and hand strokes kept): about three hours over three passes, approved by John 2026-10-10.
  `tools/oedipus_colonus.py` (2026-10-10).
- Say plainly when a redo is not better: pass 1 lost the old drawing's curl detail (white hair as one grey wash).
  White curls on clay: a light tone over the mass with the painter's dark marks between the curls as crisp
  strokes. Keep the lines-off zone to the hair itself, not a box round the head: the robe's lines under the
  beard went with it (John marked them) (2026-10-10).
- Hand-placed strokes at a plate's own px round off small marks: draw them at twice the frame and trace from
  there ("faces need to be crisper"). Dark hair as many wash steps mottles round a face; two firm steps keep the
  face clear (2026-10-10).
- What reads as hair may be attire: a dark band with white ribs over Ismene's head is a headdress (John). Look at
  the clearest photo; draw it black with the ribs clear (a white top-hat, Minimum then Maximum) (2026-10-10).
- Antigone redone with PhotoCraft (Berlin F 3240; the 2026-10-02 flat, cut and John's traces kept): about an hour
  for pass 1, then John's corrections and four short rounds, approved by John 2026-10-10. `tools/antigone.py`
  (2026-10-09/10).
- A corrections file John can mark: the photo on the tool's own grid, pass 1 in red on a layer at 70%, and an empty
  layer for him (blue to add, green to remove). Read his layer alone (hide the others with `layer.select`
  {"layer": id} and `layer.setProps` {"visible": false}, then save a PNG); it lands on the tool's grid at zero
  offset. Keep it as a data file beside the tool. He may mark again in the same file: diff each save against the
  last and fold the changes in (green painted over his own blue removes it) (2026-10-10).
- Apply his marks as ink = (ink less green) plus blue, drawn as he drew them. Let her area follow: a space his blue
  encloses, or green leaves inside her, stays hers; green at her edge, outside his new line, is ground. Where two
  of his strokes run close (nose, chin), the clay between them is his: ask before closing it (2026-10-10).
- A small hole in the figure's area shows the dark ground in dark mode only: her eye read heavy there since pass 1.
  Close holes under a few hundred frame px^2 when the figure has no ground seen through it (2026-10-10).
- Wasps (Getty 96.AE.112, a phlyax stage scene; the Getty's three photos): about five hours over twelve passes, approved
  by John 2026-10-10. `tools/wasps.py` (2026-10-10).
- Museum photos without EXIF: fit the focal length by trying several and keeping the one where the fit's cost levels
  off (here 40000 px for all three, taken from one stand). The profile views match the front only at a turn near 90
  degrees: filter SIFT matches by the turn a cylinder implies before fitting, or the fit drops the front as outliers.
  `vase_unroll.silhouette` wants a light ground (L > 140); the Getty's grey (115-143) needs its own edge rule.
- A scene that wraps 130 degrees round a body tapering under it: the shear-free flat bowed the stage plank and fanned
  the outer figures out. John chose the flat with the rings straight and the meridians upright (x = R_C theta, y = arc
  length), widening the feet by up to 5% (2026-10-10).
- Read the white paint as the painter used it: John saw teeth under a moustache and a sheep (ram) mask where I saw a
  beard and hair; the Getty's record calls it a ram's head. Ask for a line where one area becomes another (he drew
  both) and keep a mask an object: its face sharp and outlined, its fleece painted (2026-10-10).
- The thinned glaze on clay (bodies, clothes) took six rounds: a stepped wash was "too blotchy", strokes found by
  elongation read as thin daubs, a blurred watercolour too faint. What he approved: each stroke repainted with
  PhotoCraft's own brush (paint.stroke, hardness 0, seeded, so it reruns byte for byte), broader than the mark, run
  along the contours (the level lines of the distance to the painted lines), few and faint, and never level (the
  wheel's streaks). Patterns on cloth: crisp-edged washes darker where the brush pooled (2026-10-10).
- The big dark areas the figures close in (behind a door, between legs) are ground; a fixed head box cut a beard's
  tail where it hangs over cloth and showed as a gap in the dark theme: check every white area's whole extent
  (2026-10-10).
- Frogs (Cleveland 1989.73, the whole of side A: the bust of Dionysos between two comic actors; the museum's TIF and three
  print views), made with PhotoCraft: about three hours over a style test and four passes, approved by John 2026-10-12.
  `tools/frogs.py` (2026-10-12).
- Museum prints are the full TIFs scaled down: give each view its focal length times its scale. A start from the outline
  alone let a side view's turn slide to a false solution at longer focal lengths; start each from the best fit's numbers,
  scaled (`START`) (2026-10-12).
- John was watching the session and gave the style live, one line at a time; each went into its own constant with his
  words. Two of his asks: the outline on the ground outside the clay, so thin clay (a vine) stays open ("ground with
  outline"); dark hair and a goatee as a wash "just above ink", not ink (2026-10-12).
- Lines redrawn along their centres smeared a mask's short faint strokes into blots. Near half maximum (a fraction of the
  way from the line's core to the clay round it), the grey first capped at the clay's level so white paint beside a line
  does not widen it, and only pieces with a truly dark core, came out clean (`HM_*`). Keep the faces out of any rule for
  dense paint: the eye's close lines were taken for hair (2026-10-12).
- A shaggy suit painted in white strokes over clay: outline the clay's own edge (the white closed and filled away) and let
  the strokes run on past it over the ground (John: "the back leg needs black outline. hairs should go over onto
  ground"); keep the rule to the suit, or white hair gets a dotted outline (`SUIT`, `TUFT_*`) (2026-10-12).
- Laying John's lines into the ink re-weighted every line: the pinned weight is a target, but the tracer measures the
  median width first, and his strokes (and the order of the fleck fill) moved it. Keep the main ink exactly as the pass he
  marked and add his strokes to the ink traced at its own size; then the diff shows only his places (2026-10-12).
- Paint that reaches the floor or the ground through a gap (a cloak's black by the floor, a mask's open mouth) is closed
  in by nothing: a point or a polygon marks it as paint and it joins the figure directly (`PAINT_PTS`, `PAINT_POLYS`)
  (2026-10-12).
- Women at the Thesmophoria (Getty 96.AE.113, Wasps' sister vase: three comic actors; the Getty's three photos), made
  with PhotoCraft: about four hours over five passes, approved by John 2026-10-12. `tools/thesmophoriazusae.py`
  (2026-10-12).
- Read the museum's own account of the scene before describing it to John: the handoff guessed an old man, a kneeling
  veiled figure and a king; the Getty reads a padded youth, an actor in a woman's dress with an old woman's mask, and
  Zeus. The same Getty stand needed a focal length of its own (30000 px here, 40000 for Wasps), and its clay was
  darker (the band's clay limit lowered) (2026-10-12).
- Faces drawn only from the dark core lose the paler, finer lines (John: "dont miss those finer lines please"): keep
  the dark lines at their own shape and add the line finder's paler lines where they lie away from them, grown back
  to meet them. A lower threshold over the whole figure bridged the dress's close folds; a 5 px contrast window
  (not 8) kept them apart (2026-10-12).
- Lines run on under white paint: keeping the hair's whole area free of lines broke the face's contours through the
  beard ("Some lines incomplete or missing"). Only the white paint itself is no line. Then sweep for line ends facing
  each other with paint under the gap: on a worn vase specks of wear cut the folds into dashes; close them (2026-10-12).
- Teeth on an open mouth that opens to the ground: the mouth's black counts as ground and the teeth fall out of the
  figure. Mark the mouth as paint (a polygon), and ask what is teeth and what is moustache: John drew the beard's
  area round the mouth; the white curve I took for teeth was moustache (2026-10-12).
- White hair as brushstrokes (John: "All lighter hair should be brush strokes", "wispy"): strokes centred on the
  white's skeleton came out as specks, because the painted strokes merge. Streamlines along the paint's grain (the
  grey's structure tensor), seeded at the lightest uncovered paint and run while on the paint, drawn with
  PhotoCraft's brush at the paint's width, read as brushwork. paint.stroke takes [x, y, pressure]: pressure tapers
  the stroke to a point at both ends. The greedy seeding takes a few minutes per run (2026-10-12).
- The Aristophanes home figure (Würzburg H 5697, the whole of side A: the Kinsman on the altar, Mika with her bowl; two
  ArchaiOptix photos), made with PhotoCraft: about five hours over two days, a source search and four passes, approved by
  John 2026-10-15. `tools/mika.py` (2026-10-15).
- "Look for German plates first": the CVA settles whether any can exist. Würzburg 4 says "Aus Rom. Erworben 1977", first
  published 1980, so no old plate; say so with the entry, and go to the photos (2026-10-14).
- Fit both photos to the same painted circle: `vase_unroll.band_edge` took the thin clay strip under the feet in one photo
  and the band's lower edge in the other, and the fit bent the profile to negative radii. Measure the band's lower edge
  in both (clay above, glaze below, clear all along). A loose first round, then the tight one: from a poor start every
  band point of one photo was dropped as an outlier. Check the model by laying both photos onto the flat: here within
  1 px everywhere (2026-10-14).
- A scene wrapping about ±55 degrees round the vase comes out about 1.3 times wider than the photo at its edges; the egg
  band's eggs, even on the flat, show it is right (2026-10-14).
- A foot at the vase's edge is out of focus in every photo: its toe lines print as soft bands. The grey's minima row by
  row on the two flats averaged lined up into four lines (John: "the feet (toes specifically) need to be traced
  clearly"); he then traced over the same four (2026-10-14).
- John set the photo's levels in PhotoCraft (adjustment layers) "to help" with the dress's fine lines, then drew them in
  blue. His adjustment layers replay exactly with `photocraft-cli run` (Brightness/Contrast, Levels, Vibrance), but the
  lines under his strokes, snapped from the adjusted photo, came out ragged (the clay's edge and the grain): draw his
  strokes as he drew them, at the line width, and take my ink out under them, or each line is drawn twice. Ask each
  round whether his blue replaces or adds: round 2 was "additive" (2026-10-14/15).
- His marks may land on any layer and he may re-save: list the layer ids before every export (a re-save renamed his layer
  and the first export missed his green), and read blue and green by colour from every layer (2026-10-15).
- Where his line becomes the outline (her soles drawn lower, the knife's edges on the ground side), let the figure reach
  his line's centre, not its outer edge, or the body's trace overshoots it and a sliver of clay shows on the dark theme;
  and pass his lines (traced as `dots`) to `trace_svg` as `extent`, or the crop is cut at the main ink (2026-10-14).
- Round 3's filled marks (a pupil, a dark spot on the veil) are short for their width; his thick zigzag is long: fill a
  mark when its skeleton is under four times its greatest width, in that round only (round 1 has wide crossings that are
  lines) (2026-10-15).
- Moving a drawing to a new use (2026-10-15): John made the Würzburg scene Women at the Thesmophoria's plate, the
  Getty krater the author page's figure and its crowned king the home figure. One figure cut from an approved whole
  drawing in the same tool (KING_*, as eumenides.py cuts the Pythia) leaves the whole drawing byte for byte as approved;
  check the box takes in every free end (the king's outstretched fingertips were cut off at first), and draw his lines
  at the whole drawing's traced width, not the house share of the smaller figure's longer side.

### Photos of vases, black-figure (a cup's tondo taken at a slant)

- Prometheus Bound (Vatican 16592, Laconian cup by the Arkesilas Painter; Daderot's photo), made with PhotoCraft in
  the black-figure silhouette: about seven hours over three days and eight passes, approved by John 2026-10-12.
  `tools/prometheus.py` (2026-10-12).
- A tondo shot at a slant: fit an ellipse to the clay's edge against the black band (1440 rays, half-maximum, outliers
  dropped) and map it to a circle by one affine map; on a shallow cup that left under half a px, so no unrolling.
  The border's painted rings fit as circles too, and John wanted them drawn: "It looks bad without the band"
  (2026-10-10).
- A ring of pale filler round a glued-back piece: trace it as a least-cost path through hand points, then carry each
  mask across it by a harmonic fill of its signed distance, measured over known px only (measured to the hole's edge,
  single px tipped it and the fill came out black); join the incisions it broke by hand, as automatic pairing joined
  the wrong hair locks (2026-10-10).
- The light falls off toward the rim (clay grey 150 in the middle, 30-90 at the edge): test clay against the clay's
  own grey round it, not a fixed level. The glaze's glare photographs light and blue, and over the capital light and
  warm: there test saturation too. A red channel less blue clips at 0 in PhotoCraft; the Channel Mixer's constant
  (50) keeps it whole (2026-10-10).
- Photo incisions found by top-hat came out broken and of every width: John found it "isn't precise enough". Redraw
  each as an even centre line, join small gaps, and fit the feathers as straight lines (2026-10-12).
- Added red fills its area edge to edge (John: "well defined area which is filled edge to edge"; the beard "solid one
  color"): fill the area, not the photo's patchy red. Ropes are "big thick rope lines" with "distinct separation":
  draw them on his centrelines, the separations black. Where the wash met incisions (the ribs) it swallowed them; keep
  incisions out of narrow red only, stop the wash at them, and in the end the ribs were his lines alone (2026-10-12).
- On a tondo, clay for the whole ground in both themes: the white ground "just doesn't work here" (John, 2026-10-11).
- John's PhotoCraft marks over five rounds: export his layer alone through `photocraft-cli serve` (layer.setProps
  visible false on the rest, doc.save png). His colours changed between rounds (green first "lines to draw whole",
  later "remove", i.e. a clay line): ask what each colour means each round, and confirm in plain words if he answers
  "confused" (2026-10-12).

## John's traces

- He draws over a crop of the plate, or over a screenshot of a close-up, in
  Preview, and sends it in chat. The chat image is not a file you can read:
  the file is on his Desktop ("Screenshot ... PM.png", with a narrow
  no-break space before "PM", so glob for it) or in Downloads (2026-10-06).
- When he traces over a crop you sent, the file in Downloads keeps your
  crop's name (`1_eriphyle_face.png`) or comes as `image-<digits>.png`; the
  chat image is the same file. A screenshot of the plate registers with a
  similarity transform (SIFT) as well as a crop does (2026-10-07).
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
- He may correct a whole pass in Photocraft, over the full-resolution export: a PSD at the
  drawing's 2000-px width, the pass in red over the plate, blue for ink to add and green for ink to
  take out. Read it with `photocraft-cli convert` (in `~/.local/bin`); it registers at zero offset,
  so his marks map straight to plate px as rings (`map_marks.py` in `.remember/batch4/b/scripts/`,
  outside git). A screenshot he sends later may hold paint that the file on his Desktop does not (he
  draws on it in the chat): locate the screenshot by matching it to the export, and read his marks
  off the chat image (2026-10-07).
- Photocraft has an MCP server (`photocraft-cli mcp`, with read and write roots). Place Embedded is
  disabled there: copy a layer in from a second document and Paste in Place (2026-10-07).

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
- When you fill a shape from a seed inside lines you drew, assert that the
  fill never reaches the edge of its box: it caught a contour line that
  stopped 5 px short of the black it should meet (Seven, 2026-10-07).
- Line ends that face each other across a short gap, in the finished SVG,
  find the breaks in the plate's printing (seven on pl. XX); check each by
  eye, since some are true ends (fingers, short strokes). A sweep for the
  plate's lines inside the figure that the drawing does not cover found
  only grain and stains on the Élite plates. `gaps.py` and `missed.py`,
  with `sclose.py` (close-ups rendered from the SVG), are kept in
  `.remember/batch3/scripts/`, outside git (2026-10-07).
