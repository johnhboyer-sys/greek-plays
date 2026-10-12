# Handoff: Rhesus drawing with PhotoCraft (Hoernes, AZ 35, 1877, Taf. 5), 2026-10-10

One session, one drawing. John picked it on Plate Picks on 2026-10-08 (27-P2a; record in
`.remember/sweep2-2026-10-04/rulings.md`). On 2026-10-10 he asked for a more detailed version or a photo of the
original. Sweep 10 found neither (report: `.remember/sweep10-rhesus/report.md`, read it), and John then asked for this
session. Other sessions are running (Iphigenia at Aulis on `claude/redesign-plates-14`, perhaps others): don't touch
their branches, worktrees or notes folders.

| Play | Plate | Branch / worktree | Notes folder |
|---|---|---|---|
| Rhesus (Euripides), key 27-P2a | M. Hoernes, "Vasenbilder", *Archäologische Zeitung* 35 (1877), Taf. 5 | `claude/redesign-plates-17`, `.claude/worktrees/redesign-plates-17` | `.remember/batch16/` |

## The source
- Scan: Internet Archive `in.gov.ignca.25813` (Archäologische Zeitung 1876-77), leaf n325:
  https://archive.org/details/in.gov.ignca.25813/page/n325/mode/1up. About 5120 x 6400, the plate printed sideways
  (turn it upright). A second scan of the 1877 volume exists (`archaologischez35deut`, from the Getty/Michigan copies):
  compare the two at the plate and use the sharper one. Public domain (published 1877).
- The plate: a plain contour drawing on cream paper, no black ground, slight toning. Two youths walk right: at the
  left a nude youth in a pointed hat with a crescent and a rim of discs, a belt and a cross-band set with discs (a
  large disc where they cross), one spear in his right hand and two over his left shoulder; ahead of him a youth in
  a helmet with a star-tipped crest and a chlamys, thrusting a spear, a round shield with a large star device. They
  overlap at the feet and the spears. Figures about 2,500-3,000 px along the long axis. Both nude, genitals drawn:
  draw them as printed (John, 2026-10-09: "no censorship").
- Preview: `.remember/sweep10-rhesus/previews/hoernes-az35-taf5-crop_27-P2a.jpg`.
- The vase (sweep 10): Sacken and Kenner, *Die Sammlungen des k.k. Münz- und Antiken-Cabinetes* (Vienna 1866),
  Kasten V, 2, no. 57: a red-figure krater "of fine style" from the Lamberg collection, side A the two youths, side B
  two cloaked figures. Modern KHM number, attribution and present display not found; no photo found. Hoernes reads
  the pair as Diomedes and Odysseus on the night raid (Iliad 10) and says it cannot be strictly proved; Sacken and
  Kenner call them ephebes. Read Hoernes's text yourself (AZ 35, p. 21; the OCR text is
  `25813_djvu.txt` in the IA item, around the words "Diomedes und Odysseus auf ihrem nächtlichen").
- The play: the night raid on the Trojan camp in which Diomedes and Odysseus kill Rhesus; Athena guides them. A
  direct link if Hoernes's reading holds.

## Ask John first (one message, start it with "Rhesus (PhotoCraft)")
1. The download OK (name the file, the source, and the size), with the preview crop.
2. The style: a contour plate with no black ground, so no ground to cut the figures out of. Offer what the outline
   plates did before (Andromache, Furtwängler and Reichhold: pen lines traced, the figures' area filled as clay on the
   dark theme), with a small test of the head of the left youth in both themes before pass 1.
3. The title, in one line: Hoernes's reading ("Diomedes and Odysseus on the night raid") or a plain one ("Two young
   warriors setting out at night", with Hoernes's reading in the notes). On Helen John titled the drawing as the
   museum reads it; on Phoenician Women and Wealth (no museum reading to hand) he chose the publication's reading.

## Method
- Follow the Method, Show John, and Records sections of `.remember/batch12/HANDOFF.md` as written: every image step
  in PhotoCraft (rotation and levelling may stay in numpy/scipy; say so in the docstring); `linework.trace_svg` writes
  the SVG; faces and hands first (each finger at 20x, eyes never heavy); John corrects in PhotoCraft or on a pixel
  grid; read his marks literally.
- Your models: `tools/andromache.py` (Furtwängler and Reichhold, a pen-line plate; read the LESSONS section on that
  family), and for the PhotoCraft pipeline and John's marks `tools/phoenician_women.py` and the Wealth tool merged
  today (main 9b34e8a: white hair, the new `day` option of `trace_svg`). Read `docs/redesign/drawings/LESSONS.md`
  whole, above all the Furtwängler-Reichhold section, "Checks that caught real faults", "John's traces", and the
  2026-10-10 entries (pinned line weight after pass 1; whole-plate diff after each round; John's short lines
  meaning "this is paint"; `OPEN`, `DROP`).
- This plate's own traps: the spears are long thin lines that cross both figures and each other (keep them
  straight and whole; they pass over and under arms); the star on the shield and the disc-studded bands are small
  solid marks (route them through `dots` at their printed width); the paper's toning and the crease or the IA
  scan's edges must not become lines. Fingers on the spear shafts first.
- The .pcraft round trip: scripts in `.remember/batch12/b/scripts/`; LESSONS has the recipe (Phoenician Women).
- Python: numpy, scipy, scikit-image, pillow, opencv-python-headless in a venv in your scratchpad (system python3
  lacks scipy). potrace and rsvg-convert are installed.

## Before you start
- Check the model budget board. Load the `delegate` skill before any subagent spawn.
- Branch off main in your own worktree (table above). Copy this file in as
  `docs/redesign/drawings/HANDOFF-plates-17.md`, commit first, commit as you go, push. Merging is John's call.
- Keep `notes.md` and `timing.txt` (start, end, each pass) in this folder. Save the scan to `src/` here
  (gitignored); never commit it.
- Before the records step, merge the latest main (other sessions fill the same record files: keep every other
  entry, rerun the contact sheet). The play's entry in `play-image-plan.json` is still the placeholder. The credit
  cites Hoernes's plate and Sacken and Kenner's entry, "present location not found" unless you find it.
- When John approves, also update Plate Picks (https://claude.ai/artifact/FZWiHnpDxWmp6Gs4paECxD): source in
  `.remember/sweep6-2026-10-08/page/`; add Rhesus to `settled.json` (render `imgs/drawn-rhesus.png` at 700 px high on
  #fbf9f4 with rsvg-convert; `imgs/orig-rhesus.jpg` from `imgs/27-P2a.jpg`), run `build7.py`, read the artifact
  first, and publish `index.html` with the two new images to that URL.

## Prompt
> Read `/Users/johnboyer/Developer/greek-plays/.remember/batch16/HANDOFF.md` and do it: one line drawing with
> PhotoCraft for Rhesus (Hoernes, AZ 35, 1877, Taf. 5, the two youths on the night raid), on a new branch
> `claude/redesign-plates-17`. Your first message to me asks me to OK the download, the style, and the title.
