# Handoff: UI overhaul, first pass (2026-10-13)

Branch `claude/project-thread-8ykl6l`, pushed, not merged (John: keep as a
branch; more changes to come). Ten commits on main `182b42a`. Every gate in
CLAUDE.md passed at the last ship-gate run (`npm run build:public`: 1271
pages, 0 broken links); the phone commit `02226e3` passed tests, the site
build and the fixture build, and its ship-gate run is still to do.

Read first: `docs/redesign/DESIGN.md`, `PHASES.md`, `decisions.md` (a
"Home page, built" entry was added), the sketches in `sketches/`.

## What is built

- **Home** (`app/src/components/ClassicHome.astro`): the round-3 A frieze on
  warm paper (#fbf9f4; dark #1c1a17). Figures in Attic orange (#d4875a, dark
  lines, both themes) and each author's English name and play count in his
  colour: John's pick of four colour versions (screenshots in
  `screenshots/home-colour-2026-10-13/`). Two pairs below 64rem. Resources
  under the frieze; no collections (still open). Intro line is DRAFT.
- **Author pages** (`app/src/pages/[author]/index.astro`): round-4 sketch on
  the author tint; Oresteia and the Oedipus plays grouped first
  (`app/src/lib/author-groups.ts`, notes are DRAFT); Titles only toggle
  (localStorage `drama-author-view`); Find a play on Euripides. The sketch's
  thin rules were left out (DESIGN.md forbids rules). The old breadcrumb,
  citation-conventions list and support card are gone.
- **Play opening** (`app/src/components/Playbill.astro`, rendered by
  `ReaderShell.astro` above line 1 for play-line works, editions flag on or
  off; `ReaderHost.svelte` takes `plate={false}`): the round-2 playbill.
  Drawing from the image plan's `final_image`, its SVG `<desc>` as credit;
  persons in two columns with speaker colours and sigla; translations with
  form, year (only where the name holds one), alignment, and "from X's
  Greek" when editions are on.
- **Reading view** (`app/src/styles/reader-drama.css`, scoped by
  `body[data-author]`): step 1 warm paper, tinted running head, no rules;
  step 2 speaker names run into the first line in both columns (comparison
  untouched); step 3 desktop long speeches were already continuous; speaker
  bar (`app/src/components/SpeakerBar.astro`); phones open bilingual on plays
  and alternate Greek and English in pieces of at least five lines
  (`shared/components/Reader.svelte`, two edits).
- **Shared pieces**: `SiteHeader.astro` (wordmark, Resume, Search, theme),
  `Figure.astro` (drawings on a ground line via `<use>`),
  `app/src/lib/drawings.ts` + `pages/drawings/[name].svg.ts` (serves the
  drawings from `docs/redesign/drawings/`, body fill from `--fig-body`).
  Texts and licences now lists every served drawing's credit.

Screenshots of the real site: `docs/redesign/screenshots/` (home, author
pages, playbill, reading-view 1-3).

## Reviews

Codex GPT-6-Sol at medium, read-only, three runs. Run 1 (home/author/play):
3 fixed, 1 wrong (dark playbill does switch), 2 to John (below). Run 2
(reading view 1-3): all 7 fixed. Run 3 (phone alternation): see the end of
this file.

## Open for John

- Restore the Citation conventions section on author pages? (Codex asked.)
- Clouds and Prometheus keep their own body colours, not Attic orange.
- Collections under the home frieze; author-page play order after groups.

## Next

1. Reading view step 4: comparison, stanza starts aligned across columns
   (DESIGN.md; sketch reading-view-round2 case B). Labels in comparison are
   still above each column.
2. Step 5: parse panel beside the text on desktop, sheet on phone.
3. Test passages from PHASES.md phase 5: Agamemnon 1202-1213, Frogs 1-15,
   Medea 1271-1292, Libation Bearers ~869, Medea 410-445 compared, Medea
   1136-1230 on a phone.
4. Data fixes (own branch): Greek titles in capitals (Seven, Trojan Women,
   Helen); speaker palette slot 4 near ink (Cassandra, Agamemnon); Greek
   sigla print unaccented; translation years for Kosmos, Johnston, Murray.
5. Undrawn plays show an empty drawing space: Agamemnon, Peace, Children of
   Heracles, Electra (Eur.), Iphigenia in Tauris. John: no drawing session
   for Agamemnon now.
6. The reader's running head is still the old chrome (breadcrumb, Support
   button); the onboarding tip toast covers screenshots.

## Gotchas

- Screenshots: Playwright from `~/.npm/_npx/9833c18b2d85bc59/node_modules/playwright`
  with `executablePath` the cached `chromium_headless_shell-1228`; remove
  `astro-dev-toolbar` before shooting the dev server.
- `app/src/__tests__/header-chrome.test.ts` pins `<html lang="en"
  data-genre={genre}>` in ReaderShell and the author page, so data-author
  sits on `<body>`.
- Astro scoped styles scope only the last compound, so `:root[data-theme]
  .x` works inside a component.
- The project thread has hit its 24-attachment limit; link files in text.
