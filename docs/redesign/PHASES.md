# Redesign phases: prompts for Claude Code

Run each phase in a fresh session. Paste the prompt, let it work, and review what it hands back before starting the next phase. If you correct the same thing twice in one session, start a new session and put the correction into the prompt.

Every phase ends the same way: Claude takes Playwright screenshots, reads them, fixes what breaks the brief, and stops after three rounds of fixes. Then it shows you the screenshots.

---

## Phase 1: drawing test

```
Read docs/redesign/DESIGN.md, the Drawings section in particular, and docs/redesign/research/play-image-plan.json.

Goal: find out whether we can make consistent line drawings, and from what sources, before making all 48 (44 plays plus 4 playwright figures).

Make six drawings: one figure for each playwright's home-page feature, plus Medea (Cleveland Museum of Art 1991.1) and Iphigenia at Aulis (Met 31.11.2). For each:
1. Find the source. Prefer a pre-1931 published line drawing of a real vase. Otherwise use a CC0 museum photo.
2. Cut the figure out along its outline and convert it to SVG that meets the style rules. Try potrace or a similar command-line tool. Record the method and how well it worked.
3. Fill in its record in the image plan.

Put the files in docs/redesign/drawings/. Build one HTML contact sheet showing all six at 400px and 120px wide, in light and dark themes, on the warm paper and on each author tint. Screenshot it, read the screenshot, and fix anything that breaks the Drawings rules.

Then stop and report: which sources gave clean drawings, which failed, and what the remaining 42 need. Do not start on layouts.
```

## Phase 2: the rest of the drawings

Write this prompt after reviewing phase 1. It should name the method that worked and run in batches of about eight plays, each batch ending with a contact sheet for review.

## Phase 3: home page and author pages

```
Read docs/redesign/DESIGN.md (Home page, Author pages, Author tints, Fixed, Review checklist). Open docs/redesign/sketches/home-sketches-round3.html (version A) and docs/redesign/sketches/author-pages-round4.html in a browser and screenshot them; those are the targets.

Then read app/src/components/ClassicHome.astro and app/src/pages/[author]/index.astro, and how they get their data.

Implement the home page and the four author pages in the app. Use the drawings in docs/redesign/drawings/ where they exist; where one is missing, leave the figure space empty at the same size. Keep routes, built-work filtering, attribution notices and search working. Put drama-only styles in drama-scoped files; log any change to shared/ in DRIFT.md. Add dark-mode values for the author tints and check AA in both themes.

Done means: every gate in CLAUDE.md passes, and screenshots of home, Aeschylus, Sophocles, Euripides and Aristophanes at 1440 and 390, light and dark, match the sketches. List the differences you find and fix them. Then hand the screenshots to a subagent with the Review checklist and fix what it finds. Check keyboard focus order and 200% zoom. Commit to a claude/ branch.
```

## Phase 4: play opening

```
Read docs/redesign/DESIGN.md (Play opening, Fixed, Review checklist, Data to fix). Open docs/redesign/sketches/play-opening-round2.html and screenshot it; that is the target.

Then read app/src/components/Landing.astro, shared/components/Plate.svelte and app/src/components/ReaderShell.astro, and how the plate gets its cast, editions and translations.

Rebuild the play opening as the playbill layout. Persons in two columns with speaker colours and Greek labels. Greek texts and translations listed in full with years, from the manifests; where a year is missing, show none rather than guessing, and list the gaps for me. Synopsis behind "Full synopsis (tells the ending)". Resume first when a saved place exists.

Check Medea, Agamemnon, Frogs and Oedipus Tyrannus at 1440 and 390, light and dark. Same review and gates as phase 3. Commit to a claude/ branch.
```

## Phase 5: reading view

One change per session, in this order. Each is a short prompt pointing at the Reading view section of DESIGN.md and at `sketches/reading-view-round2.html`:

1. Warm paper ground, author tint in the running head, no horizontal rules.
2. Speaker names run into the first line of each speech in both columns; English the same size and ink as the Greek.
3. Long speeches: continuous columns with line markers on desktop; five-line alternation on phone; the speaker bar.
4. Comparison: stanza starts aligned across columns.
5. Parse panel beside the text on desktop, sheet on phone, with Grammata's entry scrolling inside it.

Test every change on these passages, confirming the exact ranges in the data first: Agamemnon 1202–1213, Frogs 1–15, Medea 1271–1292, Libation Bearers around 869, Medea 410–445 in three-column comparison, and the Messenger speech in Medea (1136–1230) on a phone. Also check translator switching, saved deep links, reduced motion, and phone widths around 390px.

---

## Working notes

- Give Claude pictures. Paste screenshots of what you like and what you don't.
- The review checklist goes to a separate reviewer, not into the first draft.
- Data fixes in DESIGN.md are separate small tasks. Do them on their own branch, not mixed into a layout phase.
