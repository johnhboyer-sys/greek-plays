# Handoff: Assemblywomen drawing with PhotoCraft (Heydemann 1884, Taf. I: three comic actors), 2026-10-12

One session, one drawing. John picked it on 2026-10-12 20:34: "do session with 38-8Ma for assemblywomen". Other
sessions are running (Women at the Thesmophoria on `claude/redesign-plates-26`, Orestes on `claude/redesign-plates-27`,
Birds on `claude/redesign-plates-28`, Euphorbos on `claude/redesign-plates-25`, Medea in its own session): don't touch
their branches, worktrees or notes.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Assemblywomen (Aristophanes), key 38-8Ma | H. Heydemann, *Hallisches Winckelmannsprogramm* 9 (1884), Taf. I | `claude/redesign-plates-29`, `.claude/worktrees/redesign-plates-29` | `.remember/batch27/` |

## The source
- Page: https://digi.ub.uni-heidelberg.de/diglit/hwpr1884/0025. Find the image URL and the largest size in the
  volume's IIIF manifest (`https://digi.ub.uni-heidelberg.de/diglit/iiif/hwpr1884/manifest.json`) and read its licence
  (the 1883 volume is Public Domain Mark 1.0). Preview: `.remember/sweep6-2026-10-08/page/imgs/38-8Ma.jpg`; the card's
  crop is in the sweep 8 records (`grep -rl 38-8Ma .remember/sweep8*`).
- The plate: a pen outline with folds and mask detail, no ground fill. Three masked comic actors, named above in
  Greek: Philotimides at the left, an old man in a short tunic reaching toward a tray; Charis in the middle, an old
  woman in a long veiled cloak holding out the tray of cakes; Xanthias at the right, a slave with a hand at his
  bearded mouth. A bench between them, a flask hanging above. Each actor about 1,060-1,105 px tall. Charis's cloak
  overlaps the bench and the tray touches Philotimides and Charis: one group; Xanthias stands clear. The card left out
  the door at the left: ask John.
- The vase: Milan, the Caputi vase (A 0.9.2841 per the card; check), Apulian, a phlyax scene.
- Nudity: costume phalluses on Philotimides and Xanthias. Draw as printed (John, 2026-10-09: "it's aristophanes. no
  censorship").
- The play: thematic only: stock comic types (an old woman, an old man, a slave); the vase names no play. Say so
  plainly.

## Ask John first (one message, start it with "Assemblywomen (PhotoCraft)")
1. The download OK (name the file, source and size), with the preview crop.
2. What the drawing holds: the three actors with the bench, tray and flask; the painted names, the door, and the
   ground line in or out.
3. The style: a contour plate as Persians (`tools/persians.py`, Heydemann 1883, approved 2026-10-12) and Rhesus: pen
   lines, the figures' area the paper the lines close off, clay on the dark theme. Show a small test of Charis's mask
   and Xanthias's hand in both themes.

## Credit
- Read Heydemann's text for Taf. I (Heidelberg OCR; text pages sit behind a bot check: read them in the browser pane,
  one page at a time). Then the vase now (Milan, Civiche Raccolte Archeologiche; Trendall, PhV²; the museum's record if
  online) and check the credit against it. House form as the Persians entry. Title in one line to John.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step in
  PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes the
  SVG; faces, masks and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel
  grid; read his marks literally. Send the red overlay with every pass.
- Your model: `tools/persians.py` (the same programme series and engraver's style), then `tools/rhesus.py`. Read
  `docs/redesign/drawings/LESSONS.md` whole: the contour-plates entries (Rhesus, Persians), "Checks that caught real
  faults", "John's traces", the 2026-10-10 to 10-12 entries (pin the line weight after pass 1; diff the whole plate
  after each round; `OPEN`, `DROP`; John's short lines meaning "this is paint").
- This plate's traps: the masks' features (eyes, open mouths, wrinkles); the cakes on the tray (small marks at their
  printed width through `dots`); the veil's edge over Charis's hands; the bench legs; the fold if the plate is a
  foldout.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe. Keep it under 30 MB.
- Python venv in your scratchpad (numpy, scipy, scikit-image, pillow, opencv-python-headless). potrace and
  rsvg-convert are installed. John may be on Remote Control: send every image with SendUserFile and ask with
  AskUserQuestion.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-29.md`, commit first, commit as you go, push. Merging is John's call. If the
  branch name is taken when you start, take the next free number and say so.
- Keep `notes.md` and `timing.txt` here; the scan in `src/` here (never committed).
- Before the records step, merge the latest main (keep every other entry, rerun the contact sheet). The play's entry
  in `play-image-plan.json` is still the placeholder.

## Records, when he approves
- `tools/ecclesiazusae.py` and `ecclesiazusae.svg` (check the play's work id in `play-image-plan.json` and use it);
  the play's entry in `play-image-plan.json` (`json.dumps(d, indent=2, ensure_ascii=False)` round-trips it),
  `drawings.json`, the README table, rerun `tools/contact_sheet.py`, a dated LESSONS entry under the contour plates.
  Rerun the tool: the SVG byte for byte the same. `tools/test_linework.py` and `tools/test_andromache_trace.py` pass.
  No outside review unless John asks.
- Update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in `.remember/sweep6-2026-10-08/page/`;
  add the play to `settled.json` (wid as in `build7.py`'s play list; `imgs/drawn-<wid>.png` at 700 px high on
  #fbf9f4 with rsvg-convert; `imgs/orig-<wid>.jpg` from `imgs/38-8Ma.jpg`), take it out of the in-progress chip line in
  `build7.py`, run `build7.py`, read the artifact first (another session may have published since), and publish
  `index.html` with the two new images.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch27/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Assemblywomen (Heydemann 1884, Taf. I: three comic actors, Philotimides, Charis and Xanthias), on a
> new branch `claude/redesign-plates-29`. Your first message to me asks me to OK the download, what the drawing holds,
> and the style.
