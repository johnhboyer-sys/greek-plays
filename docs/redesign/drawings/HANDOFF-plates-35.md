# Handoff: the Aristophanes home figure, redrawn with PhotoCraft as the whole Thesmophoriazusae scene (Würzburg H 5697), 2026-10-14

One session, one drawing. John, 2026-10-14 12:00: "redo mika from women at the thesmophoria. i want the whole image, not
just mika. Have the session start by looking for alternative german repro plates." It replaces the home-page drawing
`aristophanes-mika.svg` (`tools/mika.py`, traced 2026-10-02 from a photo, before PhotoCraft; "To redo in PhotoCraft"
since 2026-10-09). The old drawing holds Mika alone; the new one holds the whole picture. Another session is running
(the Euripides home Iphigenia on `claude/redesign-plates-31`): don't touch its branch, worktree or notes.

| Subject | Vase | Branch / worktree | Notes folder |
|---|---|---|---|
| Aristophanes home figure: the parody of Telephus from Women at the Thesmophoria (Mnesilochus on the altar with the wineskin "baby" and the knife; Mika with her bowl) | Apulian red-figure bell-krater by the Schiller Painter, c. 370 BC, Würzburg, Martin von Wagner Museum H 5697 (RVAp 4/4a) | `claude/redesign-plates-35`, `.claude/worktrees/redesign-plates-35` | `.remember/batch38/` |

## Step 1: look for German reproduction plates of the vase (before anything else)
- John wants an old printed drawing of this vase, German first: a plate in vase style (interior lines; black ground
  best), as the plate families in `docs/redesign/drawings/LESSONS.md`. Search the vase's bibliography (Trendall-Cambitoglou
  RVAp 4/4a; Csapo; Taplin, *Comic Angels*; the Würzburg museum's catalogues, e.g. Langlotz, *Griechische Vasen in
  Würzburg*, 1932, and anything earlier); the BAPD/Beazley Archive; and the German journals and plate books on
  Heidelberg's digital library (Archäologische Zeitung, Jahrbuch and Antike Denkmäler of the Institut, Wiener
  Vorlegeblätter, Furtwängler-Reichhold, Bieber's *Denkmäler zum Theaterwesen*, 1920). Pre-1931 is public domain by
  John's rule; a later plate is his call.
- Open each one and see it. Never report that a plate shows the vase unless you saw it. If the vase was found or
  first published too late for an old plate, say so plainly, with the evidence.
- Report to John in your first message: each plate's citation, link, scan size, and a small crop (from a page you
  viewed, sent with SendUserFile). Ask him to pick, and to OK each download by name and size. If no old plate exists,
  propose the photo route (below) and wait for his answer.

## The vase and the scene
- Photos: ArchaiOptix on Commons, CC BY-SA 4.0, several views, e.g.
  https://commons.wikimedia.org/wiki/File:Schiller_Painter_-_RVAp_4-4a_-_Thesmophoriazousai_as_phlyax_play_-_youths_-_W%C3%BCrzburg_MvWM_H_5697_-_04.jpg
  (Commons category: Schiller Painter). The current home figure was traced from view 04.
- What it shows (check it yourself): the scene from Women at the Thesmophoria (689 ff.) where the Kinsman (Mnesilochus),
  caught at the festival, seizes a "baby" that turns out to be a wineskin, climbs the altar, and threatens it with a
  knife, while Mika, the woman whose "child" it is, holds out a bowl to catch its "blood". It is a parody of
  Euripides' Telephus. Report everything on side A (all figures, the altar, any stage or added objects) and propose
  the whole side as the drawing; ask John about the edges (border bands left out, as on the other plates).
- Nudity and costume phalluses: draw as painted (John, 2026-10-09: "it's aristophanes. no censorship").
- The old record (`playwrights`, Aristophanes, in `docs/redesign/research/play-image-plan.json`) has the old crop and
  credit; read it for the decisions, then replace them.

## Credit
- The plate's own text (if a plate), the museum's record, and RVAp. Short house form, as the Wasps and Assemblywomen
  entries in `play-image-plan.json`. The drawing carries no licence from a CC BY-SA photo (John, 2026-10-08).

## Method
- A plate: models `tools/ecclesiazusae.py` (Heydemann 1884, comic actors) and the plate families in LESSONS.
- A photo (only if John chooses it): flatten first (`tools/vase_unroll.py`; John, 2026-10-02); models `tools/wasps.py`,
  `tools/thesmophoriazusae.py` and `tools/frogs.py` (comic Apulian bell-kraters from photos); LESSONS' "Photos of vases"
  section all through.
- Read LESSONS whole, with the 2026-10-10 to 10-14 entries (pin the line weight after pass 1; diff the whole plate
  after each round; `OPEN`, `DROP`; John's short lines meaning "this is paint"; pupils as dots, both or neither).
- Every image step in PhotoCraft (`~/.local/bin/photocraft-cli`); geometry may stay in numpy/scipy; say so in the
  docstring. `linework.trace_svg` writes the SVG. Masks, faces, and hands first (each finger at 20x; eyes never heavy).
  Lines clean, crisp and even; cracks and wear leave no line.
- Traps: the knife and its blade where it meets the bowl; the wineskin's shape and its "baby" wrappings; the altar's
  edges; the masks' features; glare on the black glaze.
- Corrections: a PhotoCraft file John marks (scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe). Keep
  it under 30 MB so he can mark it on his phone.
- Send the red overlay with every pass. John may be on Remote Control: send every image with SendUserFile and ask
  with AskUserQuestion.
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-35.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder; sources in `src/` here (never committed).
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other entry,
  rerun the contact sheet).

## Records, when he approves
- Replace `aristophanes-mika.svg` and `tools/mika.py` in place (same names, so the home page keeps its link), unless
  John wants a new name now that the drawing is more than Mika: ask him. Update the Aristophanes entry in the
  `playwrights` list of `play-image-plan.json` (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it),
  `drawings.json`, the README table, rerun `tools/contact_sheet.py`, and a dated LESSONS entry. Rerun the tool: the
  SVG comes out byte for byte the same. `tools/test_linework.py` and `tools/test_andromache_trace.py` pass. No outside
  review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  re-render `imgs/drawn-aristophanes-mika.png` (700 px high on #fbf9f4 with rsvg-convert), replace
  `imgs/orig-aristophanes-mika.jpg` with the source you traced, update the entry in `home.json` (title, alt, source,
  link), and clear `home:aristophanes-mika` in `redo.json`. Run `build7.py`, read the artifact first (another session
  may have published since), diff the live page against your build, and publish `index.html` with the new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch38/HANDOFF.md` and do it: redraw the Aristophanes home
> figure with PhotoCraft as the whole scene of Würzburg H 5697 (Women at the Thesmophoria), on a new branch
> `claude/redesign-plates-35`. Start by looking for German reproduction plates of the vase, and report them to me.
