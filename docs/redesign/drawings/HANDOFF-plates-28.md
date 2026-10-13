# Handoff: Birds drawing with PhotoCraft (Cecil Smith, JHS 2, 1881, pl. XIV: the bird dancers), 2026-10-12

One session, one drawing. John picked it on 2026-10-12 20:34: "34-Q2a for birds. get full plate though". The card
(sweep 3, lane Q2) showed only the left dancer; John wants the whole picture: both bird dancers and the piper. Other
sessions are running (Women at the Thesmophoria on `claude/redesign-plates-26`, Orestes on `claude/redesign-plates-27`,
Euphorbos on `claude/redesign-plates-25`, Assemblywomen on `claude/redesign-plates-29`, Medea in its own session):
don't touch their branches, worktrees or notes.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Birds (Aristophanes), key 34-Q2a | C. Smith, *Journal of Hellenic Studies* 2 (1881), pl. XIV (fig. B.1 in the sweep notes) | `claude/redesign-plates-28`, `.claude/worktrees/redesign-plates-28` | `.remember/batch26/` |

## The source
- The copy the sweep found: Zenodo record https://zenodo.org/records/1960286 (JSTOR Early Journal Content, CC0), PDF
  `https://zenodo.org/api/records/1960286/files/article.pdf/content`, page 2: the plate picture embedded at about
  1887 x 1220 px (the PDF page scan 3222 x 4394). Zenodo blocks the browser pane; curl works. Preview of the left
  dancer only: `.remember/sweep6-2026-10-08/page/imgs/34-Q2a.jpg`. Sweep notes: `.remember/sweep3-2026-10-05/lane-Q2.md`
  and `page/crops.json` (key 34-Q2a).
- "Get full plate": first look for a better copy of pl. XIV (JHS plates were issued separately; try JSTOR, HathiTrust,
  Google Books, the Internet Archive's plate volumes, Heidelberg, Gallica). Say in one line what you find and its size.
  Your first message asks John to OK each download by name, source and size.
- The plate: a colour plate on a tan ground of a black-figure oinochoe (British Museum B 509 per the sweep brief;
  check), c. 500-480 BC: two dancers in bird masks with red crests and spotted wings, and a piper (aulos player). The
  left dancer about 1,160-1,190 px tall in the PDF image. The pipe touches the left dancer's beak; his wing meets the
  second dancer: one group.
- Nudity: the right dancer may carry a small phallus (a brown mark). Draw as painted (John, 2026-10-09: "it's
  aristophanes. no censorship").
- The play: thematic: a comic chorus dressed as birds, some sixty years before Birds (414 BC). Say so plainly.

## Ask John first (one message, start it with "Birds (PhotoCraft)")
1. The download OK (each file by name, source, size), with the crop of the whole picture.
2. What the drawing holds: the two dancers and the piper whole, and any ground line or border the plate prints.
3. The style: black-figure as Cyclops (`tools/cyclops.py`, a coloured plate of a black-figure vase, approved
   2026-10-12) and Hecuba: the black solid, the incisions as clay lines, the added red as a `tone` wash, added white as
   `white` paths. Show a small test of a bird mask and the piper's hands in both themes.

## Credit
- Read Smith's article (the same PDF) for the vase, its museum number and his reading. Then the British Museum's
  collection record and the Beazley Archive (painter, date). House form as the Cyclops entry in
  `docs/redesign/research/play-image-plan.json`. Title as the museum reads it.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft; `linework.trace_svg` writes the SVG; faces, masks and hands first (each finger at 20x, eyes never
  heavy); John corrects in PhotoCraft or on a pixel grid; read his marks literally. Send the red overlay with every
  pass.
- Models: `tools/cyclops.py` and `tools/hecuba.py` (black-figure plates), `tools/wealth.py` (added white). Read
  `docs/redesign/drawings/LESSONS.md` whole: the black-figure section, "Checks that caught real faults", "John's
  traces", the 2026-10-10 to 10-12 entries (pin the line weight after pass 1; diff the whole plate after each round;
  `OPEN`, `DROP`; John's short lines meaning "this is paint").
- This plate's traps: the spotted wings (small marks at their printed width through `dots`); thin incisions inside
  touching silhouettes (keep them); the pipe (straight and whole); the plate's printing screen and the PDF's JPEG
  blocks must not become lines; the small scale (UP 4 if needed).
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe. Keep it under 30 MB.
- Python venv in your scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless). potrace and
  rsvg-convert are installed. John may be on Remote Control: send every image with SendUserFile and ask with
  AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-28.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` here; sources in `src/` here (never committed).
- Before the records step, merge the latest main (keep every other entry, rerun the contact sheet). The play's entry in
  `play-image-plan.json` is still the placeholder.

## Records, when he approves
- `tools/birds.py` and `birds.svg`; the play's entry in `play-image-plan.json` (`json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun `tools/contact_sheet.py`, a dated
  LESSONS entry under the black-figure section. Rerun the tool: the SVG byte for byte the same. `tools/test_linework.py`
  and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add Birds to `settled.json` (wid `birds`; `imgs/drawn-birds.png` at 700 px high on #fbf9f4 with rsvg-convert;
  `imgs/orig-birds.jpg` a crop of the whole picture), take `birds` out of the in-progress chip line in `build7.py`, run
  `build7.py`, read the artifact first (another session may have published since), and publish `index.html` with the
  two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch26/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Birds (Smith, JHS 2, 1881, pl. XIV: the whole picture, two bird dancers and the piper), on a new
> branch `claude/redesign-plates-28`. Your first message to me asks me to OK the download, what the drawing holds, and
> the style.
