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
