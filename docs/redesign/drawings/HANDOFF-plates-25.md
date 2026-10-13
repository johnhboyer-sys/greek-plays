# Handoff: the Sophocles home figure, Euphorbos with the infant Oedipus, from Furtwängler-Reichhold Taf. 167, with PhotoCraft, 2026-10-12

One session, one drawing. John found the plate himself (2026-10-12 14:00, "found a better version of young oedipus
with the shepherd") and said start it (16:12). It replaces the old home-page drawing `sophocles-euphorbos.svg`
(`tools/euphorbos.py`, from ArchaiOptix photos), which is marked "To redo in PhotoCraft" and which John faulted:
"that spear is far too long" (2026-10-09). Other sessions may be running (Frogs on `claude/redesign-plates-23`,
Persians on `claude/redesign-plates-20`, Medea in its own session): don't touch their branches, worktrees or notes.

| Subject | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Sophocles home figure: Euphorbos with the infant Oedipus | A. Furtwängler and K. Reichhold, *Griechische Vasenmalerei* III, Taf. 167, 1 ("Amphora in Paris: Euphorbos mit dem Ödipuskind"; F. Bruckmann, Munich, 1927 at the foot) | `claude/redesign-plates-25`, `.claude/worktrees/redesign-plates-25` | `.remember/batch23/` |

## The source
- John downloaded it from JSTOR (Williams College community collection, "Furtwängler, Griechische Vasenmalerei";
  item https://www.jstor.org/stable/community.16370860). Copies, never committed: `.remember/batch23/src/`
  - `fr167-plate.jpg`: the whole plate, 3440 x 2615 (Achilles from the Vatican at the left, Euphorbos at the right).
  - `fr167-euphorbos-detail.jpg`: Euphorbos alone, 3440 x 2615; he is about 2,100 px tall.
  Both are heavy JPEGs (650-690 KB): look at the lines at 4x for compression blocks. If JSTOR's page offers a larger
  or less compressed download, say so in one line and ask John before fetching it. Heidelberg's scan of FR III
  (`furtwaengler1904bd3`) is another copy; compare it if it reaches this plate.
- Licence: plate printed 1927 (Germany), before 1931: public domain in the US by John's rule. JSTOR's own terms for the
  download: read them and tell John in one line; the copyright call is his.
- The plate: red figure on a black ground with all interior lines (the Furtwängler-Reichhold family). Euphorbos walks
  right, a petasos on his back, the infant Oedipus on his left arm against his shoulder, a mantle over that arm; he
  holds a long spear level in his right hand; painted names ΕΥΦΟΡΒΟΣ and ΟΙΔΙΠΟΔΑΣ; a meander band with saltire squares
  below. The spear runs past both edges of the black panel.
- The vase: Paris, Cabinet des médailles 372, Attic neck-amphora attributed to the Achilles Painter (ARV² 987.4;
  check the date and the BAPD number).
- The play: back story of Oedipus Tyrannus: the shepherd who carried the child is the play's key witness. The old
  drawing's record in `play-image-plan.json` (`playwrights`, Sophocles) has the earlier decisions.

## Ask John first (one message, start it with "Euphorbos (PhotoCraft)")
1. The spear: keep it as painted (past both panel edges), stop it at the panel's edges, or shorter. Show the options as
   small crops side by side.
2. What the drawing holds: Euphorbos and the child alone (names and meander left out, as on the other plates), or with
   the meander band.
3. The style: as Bacchae (`tools/bacchae.py`, Furtwängler-Reichhold, approved 2026-10-12): the black ground gives the
   outline; lines along their centres at the F-R weight; hair solid; thinned paint as a wash if the plate shows it.
   Show a small test of the two faces and the child's hands in both themes.

## Credit
- Read Furtwängler-Reichhold's text for Taf. 167 (vol. III; Heidelberg OCR if online). Then the Cabinet des médailles'
  record and the Beazley Archive. House form as the Bacchae and Andromache entries in
  `docs/redesign/research/play-image-plan.json`; title as the museum reads it.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes
  the SVG; faces and hands first (each finger at 20x, eyes never heavy; the child's face and fingers above all); John
  corrects in PhotoCraft or on a pixel grid; read his marks literally. Send the red overlay with every pass.
- Your models: `tools/bacchae.py` and `tools/andromache.py` (Furtwängler-Reichhold plates). Read the old
  `tools/euphorbos.py` for John's decisions, not for its lines. Read `docs/redesign/drawings/LESSONS.md` whole: the
  Furtwängler-Reichhold section, "Checks that caught real faults", "John's traces", the 2026-10-10 to 10-12 entries (pin
  the line weight after pass 1; diff the whole plate after each round; `OPEN`, `DROP`; John's short lines meaning
  "this is paint").
- This plate's traps: the chiton's many fine pleats (keep each line whole, don't let them merge); the petasos's rim
  against the black; the spear (long, thin, straight and whole) crossing his body and the mantle; the sandal straps
  and leg wrappings; JPEG blocks must not become lines.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe. Keep it under 30 MB so
  John can mark it on his phone.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.
- John may be on Remote Control: send every image with SendUserFile and ask with AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-25.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- Replace `sophocles-euphorbos.svg` and `tools/euphorbos.py` in place (same names, so the home page keeps its link),
  update the Sophocles entry in the `playwrights` list of `play-image-plan.json` (`json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun `tools/contact_sheet.py`, and a dated
  LESSONS entry under Furtwängler-Reichhold. Rerun the tool: the SVG comes out byte for byte the same.
  `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  re-render `imgs/drawn-sophocles-euphorbos.png` (700 px high on #fbf9f4 with rsvg-convert), replace
  `imgs/orig-sophocles-euphorbos.jpg` with a crop of the plate, point the home entry's source line and link at FR
  Taf. 167, clear its redo note, and take the Sophocles home figure out of the "Not settled" section (the Oedipus
  Tyrannus half of that section stays open). Run `build7.py`, read the artifact first (another session may have
  published since), and publish `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch23/HANDOFF.md` and do it: redraw the Sophocles home
> figure with PhotoCraft from Furtwängler-Reichhold Taf. 167 (Euphorbos with the infant Oedipus), on a new branch
> `claude/redesign-plates-25`. Your first message to me asks about the spear, what the drawing holds, and the style.
