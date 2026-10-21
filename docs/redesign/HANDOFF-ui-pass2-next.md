# Handoff: after UI pass 2, direction B (2026-10-21)

For the session after the build of direction B "The Vase". The build spec is
`HANDOFF-ui-pass2-build.md` (its §13 holds John's answers to the open calls,
20 October). This file closes that spec's §10.6: pass 1's open items restated,
the calls made while building, what was found and not fixed, and two scopes for
John. Nothing here is started.

## 1. State

- Branch `claude/ui-pass2-build-73023b`, pushed; worktree
  `.claude/worktrees/ui-pass2-build-73023b`. Not merged: merging to `main` and
  deploying are John's.
- Built: tokens, head and foot on every page, home, author pages, the play's
  own page at the bare URL, the reader at `/read/<author>/<work>/` with B's
  running head, menus, rows, and word panel, search step 1 with a How to
  search page, B's head and foot on the other pages.
- Screenshots for John: `docs/redesign/screenshots/pass2/`, 44 files,
  `<page>-<width>-<theme>.png` (1440 and 390, light and dark), open Greek only.
- Checks on the last build: a layout check over 102 pages and four open
  states (no sideways scroll, every figure whole, no text beside a figure
  above its top), clean at 360, 375, 390, and 1440 (320: §4, item 8); axe
  color-contrast, 0 failures in all 44 scenes; a place probe (every view
  switch from Medea 1116, both `?loc=` cases, reading on before a switch,
  Johnston's long segments; both widths), 22 of 22; a wider place probe
  (six readers, five switches, three depths, both widths), 178 of 178; a
  probe of stage directions and shared lines, 24 of 24; a probe of the fixes to
  Codex's review, 13 of 13; the Resume link, passing. Every gate in the repo
  CLAUDE.md is green.
- Ship gate (`npm run build:public`, detached, with `DRAMA_EDITIONS=1
  PUBLIC_EDITIONS=1` so `build/dist` keeps every open edition): passed on the
  final code, 21 October 02:11, and before that on `208ad1f`: all 44 plays
  and their editions, 1315 pages, 0 broken links. Its warnings predate this
  pass (editions whose licence status reads "unverified"; Vite's note on
  transition imports used only in the browser).
- The scripts (`gates.sh`, `build-editions.sh`, `shoot-pass2.mjs`,
  `check-layout.mjs`, `probe-place.mjs`, `probe-place-wide.mjs`,
  `probe-direction.mjs`, `probe-codex-fixes.mjs`, `probe-resume.mjs`,
  `final-checks.sh` to run them all, `codex-watch.sh`) are in the build
  session's notes folder,
  `~/Library/Application Support/Claude/side-session-notes/local_c2a8bee0-8423-4b25-b17c-e94a640edb9f/`.
  The npx Playwright that the MCP uses updates itself and then wants a browser
  that is not installed; the scripts load Playwright 1.62.1 and the installed
  headless shell 1228 (`PW_DIR`, `CHROME_PATH` override both).

## 2. Pass 1's open items, restated

Pass 1's three items (`HANDOFF-overhaul-pass1.md`, Reviews: 1, 3, and 4
below) and one place where the phone breaks spec §7.4 today (2). All four are
about the phone's speech-by-speech layout (`phoneLayout` in
`shared/components/Reader.svelte`), which this pass did not rework. Spec
§7.4's rule for that layout: cut a long
speech at the translation's own line markers where the translation is keyed
by line, never into a piece under five Greek lines; a speech-keyed
translation stays whole.

1. **A long first speech inside a multi-speaker segment stays whole** on a
   phone: `playRows` cuts only at speaker starts, and the phone path cuts only
   single-speech segments (`singleSpeech`, after Codex's pass 1 finding that a
   cut dialogue turn could land under the wrong speaker). Fix, per §7.4: bound
   each speech by its speaker events, then cut within it at the line-keyed
   translation's markers, five lines at least.
2. **A speech-keyed translation is cut on a phone**, against §7.4. A single
   speech in a translation with no line markers (Way, Morshead, Storr, the
   1912 comedies) gets sentence ticks placed by proportion (`playTickRows`,
   its `synthetic` branch, John's 11 September ruling for the desktop:
   "the Greek below stood bare"), and the phone path then cuts at those ticks.
   Under §7.4 the phone should keep such a speech whole. John's call whether
   the proportional ticks stay on the desktop.
3. **The first paint flashes** on a phone: `phoneLayout` starts false and is
   set on mount, so a phone draws the desktop rows first and then regroups.
   Not a hydration mismatch. A CSS-only first paint or a pre-hydration class
   on `<html>` (as the Aa settings use) would remove it.
4. **Rotation loses the place:** crossing 680px regroups the rows without
   keeping the reader's line. This pass added `placeAtTop()` and `shownFor()`
   to keep the place across a view switch; the same pair, run around the
   `phoneLayout` change, would fix rotation.

## 3. Calls made while building

All reader-facing wording is DRAFT for John.

- The foot keeps pass 1's report form and the sister-site links on every page
  but the reader; "Site by John H. Boyer" links to johnhboyer.com, and so does
  the closing credit on Texts and licences (its X link went too).
- Author pages: the figure column is sized to the figure (spec §3.3), so
  Aristophanes' Getty krater stands over the name on phones and Sophocles'
  phone name is smaller. The flag-gated "Greek editions" list left the author
  pages.
- Play page: "first staged" only where the production line opens with the
  festival or the date.
- Matched pairs kept: Both shows Paley beside Coleridge (the mock showed
  Murray's text under a Paley label).
- Search: Greek keeps All words / Any of them / Exact phrase; no ▾ on the
  plays summary; the LSJ row lists the headwords found, with no checks or
  glosses (the engine has none yet). The default Greek text reads "Each
  play's main text" in place of "Reference text" (spec §3.4). The Together
  row is no longer dimmed when a box is empty (dimmed, it failed AA; the mock
  shows it at full strength).
- Word panel: the first entry opens under its parse; "N places in the plays";
  the parse spelled out ("aorist indicative active, third singular").
- Speaker slot 4 (§13.10): `#9b2d72` light, `#e79ac7` dark.
- Aa values: size 1.05 / 1.15 / 1.3rem, width 64 / 80 / 96rem, spacing
  1.5 / 1.62 / 1.78. On the desktop the menu widens to keep each row on one
  line.
- The jumped-to line's tint is 14% clay (16% put its clay number at 4.48:1).
- A word longer than its line now breaks, in the reader, the lexicon index,
  and an entry's head (Ecclesiazusae 1169-1175, the dish word, scrolled pages
  sideways at every width).
- The reader keeps its place across a view switch, and a `?loc=` link in
  English-only view lands on the line's English. Both faults predate this
  pass; the phone's Both -> English landed at the play's end.
- B's head resets the letter-spacing it inherited from the shared head's
  `.rh` skin.
- Between 681 and 1023px the picker sits too far left for its 40rem menu to
  hang from it, so there the menu spans the window under the head, as on a
  phone (spec §7.5 hangs it from the control).
- A search result's heading names the Greek text only beside Greek hits,
  and only the edition the engine searched (a query with English terms
  searches each play's main text, whatever edition is chosen).
- On a phone, switching from English to Both brings the piece in whole,
  Greek first, where it fits on the screen; otherwise the English stays where
  it was.

## 4. Found, not fixed

1. With editions on, a translation whose edition book keeps its English
   anywhere but `english` opens in the Greek view, because Reader.svelte's
   `hasEnglish` checks only `english`: Way's Medea and Storr's Ajax (their
   books carry it under `ross`) and Murray's Medea (under `overlays`).
   Paley's and Jebb's books carry `english` and work. Pass 1's own selector
   does the same. Likely every Loeb or OCT pairing in the corpus.
2. The search engine has no English "any form" and no `?` wildcard; neither
   is shown. Search step 2 (§5) would bring both questions back.
3. Data, from pass 1's list and still open: Greek titles in capitals in the
   manifests' `greekTitle` (Helen, Trojan Women, Seven Against Thebes; copied
   from the TLG title line), which B prints large on the author and play
   pages; sigla printed without accents (Παις); no year for the Kosmos,
   Johnston, and Murray translations on the play page.
4. Agamemnon and Seven Against Thebes have no drawing yet; their pages keep
   the drawing's height empty (spec §3.3). Agamemnon is on
   `claude/redesign-plates-37`.
5. In English-only view, a speech whose English sits in the paragraph before
   it still shows "Translated with the speech above ↑", with no Greek beside
   it to explain it (pass 1's turn flow).
6. A `?loc=` link in English-only view centres the speech's English, as the
   hash path does; in a long speech the cited line can sit lower than the top.
7. svelte-check's one warning, `Plate.svelte` `startHref` unused, predates
   this pass.
8. At 320px, the narrowest phones, four readers still scroll sideways by 2
   to 27px (Seven Against Thebes, Suppliant Women (Aeschylus), Eumenides,
   Ecclesiazusae): the Greek column's grid track comes out wider than the
   screen in lyric passages (strophe markers, long lines). 360px and wider
   are clean on every page; the layout check takes `WIDTHS=320` to show it.

Codex's review of the branch: see §7.

## 5. Scope for John: search step 2

John: "I want the same advanced search as we have on aristotle reader"; "our
value is partly in the simultaneous greek & english search with the advanced
LSJ style searches." Step 1 put B's layout over this repo's engine; step 2 is
the engine, the pipeline, and the data, so it is a session of its own.

**What the Aristotle reader has** (`~/Developer/aristotle-reader`, read-only;
copy, never edit there):
- `shared/components/Search.svelte` (2,978 lines) and `shared/lib/search.ts`
  (1,625 lines): combined searches of two or more slots, each a phrase, a
  form, a lemma, or a grammatical shape, related by near, before, or after
  within N words or lines, in order or not; grammar categories (number,
  tense, mood, voice, person, case, gender, degree); a lemma picker with
  glosses; phrase variants.
- `shared/lib/search-url.ts` (213 lines): the search's state in the query
  string, so a search can be shared, bookmarked, and stepped through.
- The phrase index: `shared/components/Phrases.svelte` (1,618 lines),
  `pages/phrases.astro`; and the guide, `pages/advanced.astro` (740 lines).
- Fetchers in `shared/lib/data.ts`: `fetchLemmaPickerShard`,
  `fetchLemmaGlosses`, `fetchNgramShard`, `fetchNgramOccurrences`,
  `fetchSearchOffsets`, `fetchLemmaMapShard`.

**What this repo lacks.** The drama pipeline stops at stage 7. Its stage 6
(285 lines, against Aristotle's 633) writes the lemma, form, and English
postings but no `offsets.json`, no grammar index (`grammar-dict.json`,
`grammar-col.bin`, one grammar code per token), and no phrase streams. There
is no stage 8 (`stage8_ngrams.py`, recurrent phrases across the corpus,
sharded by initial letter, occurrences fetched on expand) and no stage 9
(`stage9_search_shards.py`, one corpus-wide index sharded by a word's first
two letters, so a query fetches only the shards its words fall in, not every
work's index; in Aristotle's corpus "happiness" is one shard of about 80 KB).
The lemma picker's data is built by Aristotle's
`app/scripts/build-lemmata.mjs`.

**Proposed order**, each its own commit with the gates green:
1. Pipeline: port stage 6's offsets and grammar index, then stages 8 and 9,
   for 44 plays; pytest for each; the validator checks (`check_grammar`,
   `check_offsets`, `check_ngram_streams`) come with them.
2. Data: the lemma picker shards and glosses; the fetchers in `data.ts`, each
   through the data-root override.
3. Engine: `search.ts` and `search-url.ts`, with their tests.
4. UI: the Near, Shape, and English Near rows the spec's §8.1 table shows,
   the phrase index ("Phrase index" beside Search), and How to search
   extended; in B's layout, not Aristotle's.

**Size.** Several days of work across pipeline, data, engine, and UI; the
data build for 44 plays adds to `npm run build:public`, which already
exceeds the tool timeout.

**John's calls before starting:** the order above, or the engine first over
the data step 1 already has; whether the phrase index ships in step 2 or
later.

## 6. Scope for John: the plates page

John: "maybe add a plates page with all the plates next to the originals with
full citation info?"; ruled its own job after this pass (§13.11).

**What exists.** `docs/redesign/drawings/drawings.json` records 49 drawings
(`slug`, `file`, `name`, `alt`, `source`, `method`, `verdict`). The `source`
field is a sentence, not a structured citation. 38 drawings come from
pre-1931 plates or drawings (public domain, so the original can be shown
beside the drawing); 11 were traced from photographs of the vases
(aristophanes, aristophanes-author, antigone, philoctetes, oedipus-coloneus,
acharnians, clouds, wasps, frogs, thesmophoriazusae, prometheus-bound). The
drawings are fine to show (John, 2 October: tracing from such photos is
allowed), but a photograph is the photographer's, so it appears only where
its licence allows reproduction and John agrees; otherwise the entry carries
a citation and a link to the museum.

**What the job needs.**
1. Gather the originals: the plate scans are not kept in one place (the
   plate handoffs point at `~/Downloads` and working folders). For each of
   the 38, fetch the scan from its public-domain host (Heidelberg, Gallica,
   Internet Archive, and others), crop the figure the drawing follows, and
   record the URL and licence.
2. Structure the citation: publication, volume, plate or figure, year, the
   vase (museum and inventory number), the scan's host and URL, the licence.
   A new field set in `drawings.json`; the sentence stays as the credit.
3. The page, in B: each drawing beside its original on one ground line, the
   citation under both, in the order of the plays; the photo-traced drawings
   with their citation and a link to the museum's page. Route to decide
   (`/plates/` or `/drawings/`); a link from the foot and from each play
   page's drawing credit.
4. Images: crops of the originals as compressed files, served like the
   drawings, so the page loads on a phone; the page counts against the
   static-asset budget.

**John's calls before starting:** the route and the page's name; whether the
11 photo-traced drawings appear with a citation only; whether the page links
from each play's credit line.

## 7. Codex's review of the branch

GPT-6.1-Sol at medium effort, read-only, over `git diff main...HEAD` for
`app`, `shared`, and `scripts` (2026-10-21, 00:25). Seven findings, all
medium; each checked against the code before fixing, and all seven fixed:

1. The play page's Greek text links dropped `ed` for the default pair's
   edition, so a reader with another translation saved opened that
   translation's Greek. The links now always name their edition.
2. In English-only view a view switch anchored on the segment's top, so
   inside a long segment the passage moved (219px, Johnston's Medea at
   1440; 410px, Coleridge at 390). It now anchors on the English cell at the
   head's edge and how far down it, and maps a hidden cell to its row's other
   column.
3. `reader:set` with an edition and a view returned early even when the
   edition was the one shown, and ReaderHost does not remount for the same
   edition, so in comparison the unpaired reference text left the view in
   Both. The view is now applied.
4. The search's pickers were unbounded, so at 320px the Together choice
   pushed the page sideways. They are bounded by their row, with an
   ellipsis.
5. The texts menu (40rem) hung from the picker ran off the left edge between
   681px and about 1000px. It spans the window under the head there.
6. A search with English terms credited the chosen Greek edition, which the
   engine ignores for such a query. The heading now names the edition from
   the results, and only beside Greek hits.
7. Entering or leaving the comparison hid the focused button. Focus now moves
   to the comparison choice, or back to "Compare two translations".

Verified with `probe-codex-fixes.mjs` (13 checks: the edition links, Paley
opening with Murray saved, comparison to the reference text, the texts menu
at 700 to 1100px, the search headings, focus by keyboard) and
`probe-place.mjs` (22 cases; the read-on cases measure how far the English
at the edge moves, and failed on the earlier code).

**Codex's recheck** (same thread, 01:17): findings 1 and 3 to 7 resolved;
finding 2 partly, with three cases still losing the place: a desktop split
row's English cell takes no height in Both (playFlow's facing page), so a
fraction of it is nothing; `splitAtDirections` regroups rows by view, so the
noted element can vanish in the switch; and the comparison's second column
(`.overlay-col`) was not scanned. Fixed: a zero-height cell is measured by
its paragraph after playFlow's timeout, the place carries a Greek line's id
to find a rebuilt row again (and a cell the new view does not draw gives way
to its row's Greek), and the scan and `shownFor` take the second column. A
wider probe then showed one more case: in Both, the head's edge can cut an
English paragraph with no Greek beside it (a phone's pieces set the Greek
above the English; a long translation runs past its Greek), and the place is
then that English, not the next Greek line. `probe-place-wide.mjs` checks the
place over six plays and translations (Frogs, Ecclesiazusae, Agamemnon, Ajax,
Medea with Johnston, Medea in comparison), five switches, three depths, both
widths: 164 of 178 on the reviewed commit, 178 of 178 now (two
Ecclesiazusae cases give the probe no anchor: its English runs in the turn
flow). Codex checked those
fixes (02:06): all three resolved, and one new case, also fixed: a stage
direction's row holds no Greek line to key on, so a switch to the Greek view,
which drops the direction, lost the place; such a row is now keyed by the
next speech's first line, and that speech comes to the top. The second
speaker's half of a shared line has no numbered line in its own row either
(Acharnians 395, the Slave's "Who's there?" after Dicaeopolis; the number
sits on the first half, in the row above): it keys on that shared line, at
its foot (John, 02:39: "Fix now"). `probe-direction.mjs`, both kinds, to
Greek and to English: 24 of 24.
