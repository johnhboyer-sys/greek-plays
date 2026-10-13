# Handoff: Suppliant Women (Euripides), a line drawing with PhotoCraft from Gerhard AV III Taf. CLVIII, 2026-10-13

One session, one drawing. John picked the plate on 2026-10-13 (12:30) after the Aison pelike (Athens NM 1185,
`claude/redesign-plates-30`) was dropped for good ("we are ditching this vase"); 12:34: "start the drawing here".
Other sessions are running (Knights on `claude/redesign-plates-33`): don't touch their branches, worktrees or notes.

| Play | Source | Branch / worktree | Notes folder |
|---|---|---|---|
| Suppliant Women (Euripides) | E. Gerhard, *Auserlesene griechische Vasenbilder* III (1847), Taf. CLVIII, text pp. 31-32 "Theseus und Äthra": a red-figure calyx-krater from Vulci, then in the Palagi collection, Milan; now Bologna, Museo Civico Archeologico PU 285 (Methyse Painter; Beazley Archive 207341). Heidelberg scan, Public Domain Mark | `claude/redesign-plates-34`, `.claude/worktrees/redesign-plates-34` | `.remember/batch33/` |

## What the drawing holds
- The panel's three figures: Aithra (named ΑΙΘΡΑ) holding out two phialai; Theseus (ΘΕΣΕΥΣ) in a cuirass with
  a chlamys over his arm and a long staff (Gerhard: a spear without a visible point); the youth leaning on a staff at
  the right (Gerhard: Peirithoos; the Beazley Archive: a draped youth). Left out: the vase's shape drawing below,
  the plate number, the names painted on the ground (ask John).

## John's rulings
- 2026-10-13 12:30: "be sure to get all those clothing lines without breaks. Detail matters for something like this
  plate." The pleats print 1-2 px wide, in places 1-2 px apart: trace at an upscale, draw along their centres, join the
  print's breaks, check every pleat run end to end at 8x before showing him.

## Method
- As `tools/trojan_women_menelaus.py` (Gerhard AV III, PhotoCraft) and `tools/helen.py` (outline on the ground,
  EDGE_OUT; eyes from the plate's grey map; dots; pinned WEIGHT after pass 1). Every image step in PhotoCraft.
- Send the red overlay with every pass; John may be on Remote Control (SendUserFile, AskUserQuestion).

## Records, when he approves
- `suppliants-eur.svg` (new), `tools/suppliants_eur.py`; the play's entry in `play-image-plan.json`, `drawings.json`,
  the README table, `tools/contact_sheet.py`, a dated LESSONS entry under Gerhard AV; rerun byte for byte; the two
  tests pass. Plate Picks as in HANDOFF-plates-32.md. Merging is John's call.
