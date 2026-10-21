# Handoff: the Euripides home figure, Iphigenia with the letter, redrawn with PhotoCraft, 2026-10-13

One session, one drawing. John, 2026-10-13 08:51: "new session for the iphigenia with letter redo. starts by looking
for another version of the same plate". It replaces the home-page drawing `euripides-iphigenia.svg`
(`tools/iphigenia_tauris.py`, traced 2026-10-02 before PhotoCraft), marked "To redo in PhotoCraft" since 2026-10-09
(John: "redo the home page ones too"). The earlier plan for it is in `.remember/redo-2026-10-09/HANDOFF.md` (session
R3; the Pythia half is done). Other sessions are running (Assemblywomen on `claude/redesign-plates-29`, Suppliant Women
on `claude/redesign-plates-30`, an Oedipus source search in `.remember/batch28/`): don't touch their branches,
worktrees or notes.

| Subject | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Euripides home figure: Iphigenia with the letter tablet and the temple key (Iphigenia in Tauris 727 ff.) | R. Jaene's lithograph of the Duke of Buckingham's vase, *Archäologische Zeitung* 7 (1849), Denkmäler und Forschungen, Taf. XII, with O. Jahn's article | `claude/redesign-plates-31`, `.claude/worktrees/redesign-plates-31` | `.remember/batch30/` |

## Step 1: look for another copy of the same plate (before anything else)
- The current scan: Internet Archive `archaologischez07deut` (Getty Research Institute copy), leaf n156:
  https://archive.org/details/archaologischez07deut/page/n156. At its size Pylades' fingertips on the tablet cannot be
  told from the tablet's edge, and the fine grey lines are thin.
- Look for a better scan of AZ 7 (1849) Taf. XII: Heidelberg's digital library (it holds the Archäologische Zeitung),
  other Internet Archive copies, HathiTrust full view, Google Books, Gallica, BSB/MDZ. Also any other print of the same
  drawing (a later reprint or a reduced copy in a handbook), and whether the vase itself was published again in a
  better plate (find where the Buckingham vase is now).
- Open each one and see it. Report to John in your first message: each copy's link, its pixel size, and a small crop of
  her face, hands, and the tablet side by side with the same crop of the current scan (crops from pages you viewed,
  sent with SendUserFile). Ask him to pick one and to OK each download by name and size. If no better copy exists, say
  so and propose redrawing from the current scan.

## What the drawing holds (John's decisions, keep them unless he changes them)
- The `crop` field of the Euripides entry in the `playwrights` list of `docs/redesign/research/play-image-plan.json`:
  Iphigenia with the whole tablet, the temple key, its chain and knob, and her right forearm down its outer edge;
  Pylades, the temple door and steps, Artemis' foot, the attendant and her tray left out; the cut follows her veil's
  curve. Revised twice on 2026-10-02 after his review (forearm, key hand, chain, sandals, veil edge, whole tablet).
- Read `tools/iphigenia_tauris.py` for those decisions and its geometry, not for its lines.

## Credit
- Keep the entry's credit (Jaene, AZ 7, 1849, Taf. XII, Jahn's article); change the scan line if the source changes.
  Short house form.

## Method
- Lithograph with fine grey lines on paper. Models: `tools/iphigenia_aulis.py` (Élite lithograph, PhotoCraft),
  `tools/eumenides.py` (Bötticher plate, PhotoCraft), and the "Contour plates with no black ground" and Élite sections
  of `docs/redesign/drawings/LESSONS.md`. Read LESSONS whole, with the 2026-10-10 to 10-13 entries (pin the line
  weight after pass 1; diff the whole plate after each round; `OPEN`, `DROP`; John's short lines meaning "this is
  paint").
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); rotation and levelling may stay in numpy/scipy; say
  so in the docstring. `linework.trace_svg` writes the SVG. Face and hands first (each finger at 20x; eyes never
  heavy). Lines clean, crisp and even; foxing, stains and paper grain leave no line.
- Traps: the key's chain (each link whole), the tablet's edge where Pylades' fingers touch it, the veil's fine folds,
  the sandal straps.
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe).
  Keep it under 30 MB so he can mark it on his phone.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-31.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- Replace `euripides-iphigenia.svg` and `tools/iphigenia_tauris.py` in place (same names, so the home page keeps its
  link), update the Euripides entry in the `playwrights` list of `play-image-plan.json` (`json.dumps(d, indent=2,
  ensure_ascii=False)` round-trips it), `drawings.json`, the README table, rerun `tools/contact_sheet.py`, and a dated
  LESSONS entry. Rerun the tool: the SVG comes out byte for byte the same. `tools/test_linework.py` and
  `tools/test_andromache_trace.py` pass. No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  re-render `imgs/drawn-euripides-iphigenia.png` (700 px high on #fbf9f4 with rsvg-convert), replace
  `imgs/orig-euripides-iphigenia.jpg` if the source changed, update the home entry in `home.json` if its source line
  changes, and clear `home:euripides-iphigenia` in `redo.json`. Run `build7.py`, read the artifact first (another
  session may have published since), and publish `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch30/HANDOFF.md` and do it: redraw the Euripides home
> figure (Iphigenia with the letter, Archäologische Zeitung 1849 Taf. XII) with PhotoCraft, on a new branch
> `claude/redesign-plates-31`. Start by looking for another copy of the same plate, and report it to me.
