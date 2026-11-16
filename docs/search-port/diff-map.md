# Porting Aristotle's new search into the plays: the difference map

Prepared 16 Nov 2026 from greek-plays `main` (`bf7f153`) and aristotle-reader `origin/main`
(`eae145a3f1`; its search code is the redesign merge `de57f687c6`, PR #195). Nothing in `shared/` or
`app/` changes here. The plan of record is aristotle-reader's `HANDOFF-SEARCH-PORT.md`; the port waits for
Aristotle's counting PR (`HANDOFF-SEARCH-FOLLOWUPS.md`, PR 1) and for John's two rulings for the plays
(counting unit, look), shown on the picture page.

## Rulings (John, 16 Nov)

- **(a) The counting unit is the speech** ("Count by speech/turn"). The speech runs from one speaker label
  to the next, as `units.py` cuts it, and it plays the role of Aristotle's chapter:
  - the bar counts speeches;
  - "and" means both words in the same speech;
  - pages hold whole speeches.

  The data has one gap. English is stored per segment, and a segment where two speakers share a line
  (antilabe) carries one English text for both speeches (§8). The pipeline needs speech bounds
  (`turn_bounds`) in `offsets.json` (§5).
- **(b) The look: the mock.** "Looks good for now", then "Yes, the mock": the picture page's third
  option, B's layout in the Vase's type and colours (`mock/vase-search.html`). The port restyles B's markup with
  the Vase's tokens (§6) and does not bring in `b.css`.
- **(c) The Greek–English join defaults to "and/or"** (John, for every reader's search, 16 Nov:
  "make 'and/or' the default setting for when search loads (it naturally suggests they can do greek
  only or english only OR both...)").
  - The search opens on the inclusive or, labelled "and/or"; "and" stays on offer.
  - This changes the plays' default: today `langOp` starts at `'and'`, and only `op=or` in the address
    asks for the or (`search-url.ts`).
  - **Old links with no `op`** meant "and". How they keep that meaning follows aristotle-reader's
    answer, not a separate choice here.
  - The baseline's "Both, and" search has no `op`; it relies on today's default. It is one of those old
    links, so re-measure it under the rule Aristotle settles.

## Headline

- **Rebuild on Aristotle's file; don't port hunk by hunk.** Of the plays' 1,797 lines of
  `Search.svelte`, 212 also appear in Aristotle's 5,442. 42 of the 77 hunks between them are
  both-changed, and they hold 1,114 of the plays' lines. The engine under the page differs the same way
  (`search.ts` plus the plays' `search-advanced.ts`: 381 lines shared of 1,547). Aristotle's page also
  stands on 13 library files and two stylesheets the plays don't have.
- **The plays' own search work is a short list:** about ten features (§4). Each comes back onto
  Aristotle's file as a feature with its own test, not as a merge of hunks.
- **The corpus is the larger job.** Aristotle's search reads data the plays' pipeline doesn't write:
  `running.json`, one English index per translation, speaker and unit bounds in `offsets.json` (§5).
  Some of it fails quietly when absent.
- **The plays' bar counts hits, not lines.** It says "N lines in M plays", but N counts hits: each
  Greek match plus each English match in every translation. A line with two matches counts twice, and
  one English word counts once per translator who uses it. Both are the faults John ruled out for
  Aristotle on 15–16 Nov.

## 1. Method

`hunks.py` and `bestbase.sh` in this folder do the sorting. `hunks.json` lists every hunk with its line
ranges and its first line.

- **Hunks:** `difflib` opcodes of the plays' file against Aristotle's `origin/main` file, line by line.
- **Sorting each hunk** needs a common base. The plays were forked from classical-philosophy-reader at
  `233ec2547a` (`DRIFT.md`). For each file, the base is whichever copy is nearest the plays' file: the
  CPR fork point, or an Aristotle commit touching it.
  - CPR fork point: `Search.svelte`, `search.ts`, `speakers.ts`, `data.ts`, `works.ts`,
    `global.css`.
  - Aristotle `8dabb65815` (19 Oct): `search-url.ts`. The plays ported it from Aristotle in October.
  - Aristotle `3a4c75a635`: `betacode.ts`.
- **The three sorts:**
  - **port:** only Aristotle's side differs from the base.
  - **keep:** only the plays' side differs.
  - **both:** both sides changed lines in the hunk.
- **The plays split the engine:** `search.ts` (671) plus `search-advanced.ts` (876, the advanced engine
  split out on 24 Oct). Together they are compared with Aristotle's one `search.ts`.
- **A caveat:** the base is the nearest copy, not a proven ancestor. Aristotle's July state and CPR had
  drifted about 140 lines apart in `search.ts` before either fork, so a few small "both" hunks are that
  drift.

## 2. The files

Lines are plays / Aristotle. Hunk columns read "hunks: plays lines / Aristotle lines".

| File (`shared/…`) | Plays | Aristotle | port | keep | both | Lines in common |
|---|---|---|---|---|---|---|
| `components/Search.svelte` | 1,797 | 5,442 | 19: 20 / 2,985 | 16: 451 / 83 | 42: 1,114 / 2,162 | 212 |
| `lib/search.ts` (+ plays' `search-advanced.ts`) | 1,547 | 2,870 | 24: 40 / 771 | 4: 470 / 0 | 44: 656 / 1,718 | 381 |
| `lib/search-url.ts` | 174 | 368 | 3: 1 / 5 | 5: 97 / 8 | 11: 42 / 321 | 34 |
| `lib/betacode.ts` | 199 | 223 | 0 | 12: 12 / 36 | 0 | 187 |
| `lib/speakers.ts` | 1,453 | 460 | 14: 22 / 30 | 9: 36 / 6 | 3: 978 / 7 | 417 |
| `lib/speaker-colors.ts` | 70 | 70 | 0 | 2: 2 / 2 | 0 | 68 |
| `lib/data.ts` | 1,115 | 874 | 20: 78 / 702 | 2: 9 / 0 | 15: 860 / 4 | 168 |
| `lib/works.ts` | 647 | 1,597 | 51: 322 / 1,410 | 3: 10 / 0 | 2: 145 / 17 | 170 |
| `styles/global.css` | 5,808 | 2,454 | 91: 1,765 / 309 | 27: 292 / 21 | 16: 1,987 / 360 | 1,764 |

These files are new in Aristotle and absent from the plays. All are port:

| File (`shared/…`) | Lines | What it does |
|---|---|---|
| `components/SavedSearches.svelte` | 141 | the `/saved` page |
| `styles/b-search.css` | 2,237 | the search page's styles (B) |
| `styles/b.css` | 1,391 | B's tokens and layout; the search stands on them |
| `lib/chapter-pages.ts` | 160 | counting and paging by chapter, from the index alone |
| `lib/search-pages.ts` | 57 | hit counts (`hitCount`, `engHitCount`) |
| `lib/result-views.ts` | 544 | Group by (work, form, grammar), context, facets |
| `lib/form-panel.ts` | 79 | the Filter panel's form list (excluded forms) |
| `lib/english-hit.ts` | 244 | an English hit's snippet and marks |
| `lib/english-place.ts` | 236 | where an English hit sits against the Greek |
| `lib/paired-hit.ts` | 433 | the Greek and English of one place, shown together |
| `lib/proximity-sentence.ts` | 110 | the proximity search read back as one sentence |
| `lib/running-text.ts` (+ `.worker.ts`, `running-match.ts`) | 458 | "running text" search over `running.json` |
| `lib/greek-keys.ts` | 70 | the on-screen Greek keyboard |
| `lib/saved-searches.ts` | 195 | saved searches |
| `lib/sect-ticks.ts`, `lib/corpus-tools.ts`, `lib/inscription.ts` | 378 | from Plato; dead code in Aristotle (port handoff §3); keep the plays' own, port none |

Notes on the table:

- **`Search.svelte`, port:**
  - the proximity editor and its sentence (Aristotle's lines 4,425 on);
  - the works picker;
  - the results rail;
  - the toolbar: Group by, Sort, Context, Per page;
  - the Filter and View sheets on the phone;
  - the word card;
  - Save search;
  - the chapter mapper (`2,286–3,989`, one 1,704-line hunk).
- **`Search.svelte`, keep:** the verse-line hit and its keyword-in-context (944–1,241), and the LSJ
  entry link with the How to search sheet and its Beta Code chart (1,368–1,497). The LSJ headword checks
  (70–314) sort as both: Aristotle rebuilt the same stretch of the base as its own Lemma switch.
- **`Search.svelte`, both:** the script head, the search state, the results markup, the styles. Every
  one is a different design of the same thing; none would merge.
- **`search.ts`, port:** English indexes per translation (`englishIndexFile`), the public search API,
  and per-work search.
- **`search.ts`, both:** the grammar engine (a 1,198-line Aristotle hunk against the plays' own), and
  English word matching and postings.
- **`search.ts`, keep:** the plays' Near engine (`comboWindows`, the variant reading cap). It lives in
  `search-advanced.ts`.
- **`search-url.ts`:** the two readers write different addresses for the same searches.
  - The plays: `lp`, `n`/`nt`/`nr`/`nw`/`nu`/`no`/`nf`, `n2`…`n3`, `sh`, `en`/`enr`/`enw`, `ed`.
  - Aristotle: `c=l:areth`, `cw`, `xforms`, `v`, `ps`, `w=auth`, and the rest.
  - Shared plays links in the wild must keep opening: the port needs a reader for the old plays address.
- **`speakers.ts`, `speaker-colors.ts`:** keep the plays' own (about 1,000 lines of their own work, most in a region Aristotle also changed, so it sorts as both). The
  search needs one export from it, `lineRenderParts`, which the plays already have.
- **`data.ts`, `works.ts`, `global.css`:** almost every port hunk is Aristotle's corpus (Freeman, DK,
  Bekker, `WING_CORPUS_WORKS`), not search. Port nothing wholesale; add only what the search imports
  (next list).

### What Aristotle's search imports from files the plays keep

| Import | Plays has it? |
|---|---|
| `works`: `workPath`, `WORK_ORDER`, `getWork`, `WORKS` | yes |
| `works`: `AUTHENTIC_IDS`, `HAS_SPEAKERS`, `SEARCH_GROUPS`, `searchableTranslations` | **no**; write plays' versions: no authentic split; the four playwrights as groups; every play has speakers; translations from the registry |
| `data`: `fetchBook`, `fetchChapters`, `fetchSections`, `fetchLemmaPickerShard`, `fetchLemmaGlosses`, the types | yes |
| `data`: `isChapterSection` | **no** |
| `citation`: `formatCite`, `formatLocValue`, `schemeFor` | yes (the plays' `play-line` scheme) |
| `betacode`: `betaToGreek`, `liveGreek` | yes |
| `betacode`: `betaQueryToGreek` | **no** (36 Aristotle lines, all port) |
| `speakers`: `lineRenderParts` | yes |

## 3. Hunk by hunk, or a rebuild?

**Rebuild.** Start from Aristotle's `Search.svelte` and its libraries, then add the plays' features
back one at a time.

- **There is little left to merge.** 212 of 1,797 plays lines survive in Aristotle's file. A
  hunk-by-hunk port would hand-resolve 42 both-changed hunks covering 1,114 lines, 62% of the plays' file, and
  each one is two different designs, not two edits to one design.
- **The plays' own work is easy to list.** It sits in a few places: the LSJ checks, the verse-line
  hits, the Near engine, the edition switch, and the How to search sheet (§4). A list can be
  rebuilt and tested item by item; a merge of 77 hunks cannot be checked as easily.
- **The direction of travel.** Aristotle's file is where the follow-ups land: counting, phrase Include
  and Exclude, the page-67 fix. Plato's port will start from the same file. Rebuilding on it keeps the
  plays one diff from the other readers. A hunk port would leave a third design to keep in step by
  hand.
- **The cost:**
  - the plays' Near and Aristotle's proximity editor do the same job with different engines and
    addresses, and only one can stay;
  - the plays' look has to be re-made on Aristotle's markup (ruling (b));
  - the corpus work in §5.
- **The engine is not a straight swap.** Aristotle's grammar and proximity engine (`search.ts`) is the
  one Plato and Homer will share. The plays' `search-advanced.ts` came from an older Aristotle and has
  its own Near rules, which John set on 25–26 Oct ("A near hit belongs to its first Greek word's
  passage"; lines away; "on either side of"). Put the plays' Near rules on Aristotle's engine as
  options, or keep the plays' engine behind Aristotle's page. That is the one engine decision for the
  port; it needs a test per Near rule either way.

## 4. What the plays' search does that Aristotle's must carry

| Feature | Where it lives now | In Aristotle's search? |
|---|---|---|
| Hits as verse lines: the whole printed line, the match marked, its line number (`GreekLine.ref`), transposed and repeated lines as printed | `Search.svelte` 944–1,241 (`lineKwic`) | No: Aristotle cuts a window of words across Bekker lines. A play hit must show whole lines, numbered as the edition prints them. |
| Speaker names on hits, in speaker colour | not on search hits today (reader only) | Partly: `HAS_SPEAKERS` and the speaker grouping came from Plato. Plays data has per-segment speakers, but no `turn_bounds` in `offsets.json` (§5). |
| Greek editions (`ed=`): search the chosen edition where a play holds it, else the reference text; the group heading names the text | `search.ts` (`useEd`), `greekTextOf` | No. |
| The LSJ headword checks under the Greek box (`lp=`), from the plays' lemma-map shards | `Search.svelte` 70–314 | Aristotle has its own Lemma switch and headword list (`fetchLemmaPickerShard`); one should stay. |
| Near: up to three terms (word, form, lemma, phrase, grammar), near, before or after, in words or lines, "on either side of" | `search-advanced.ts`, `search-url.ts` | Its proximity editor does the same with other rules and another address. Its distance units are words, line, turn (a speaker's turn, from Plato), and chapter, so lines and speeches are already there. |
| Shape (a grammar term alone or as the Near term) | `search-advanced.ts` | Yes (grammar terms). |
| English near (`en=`) | `search.ts` | No: Aristotle's proximity terms are Greek, and its address has no English near. |
| English per translation: each hit names its translator and opens that translation's slot in the reader | `search.ts` slots, `inst.credit` | Yes (translator row under each English hit, "OWEN · TAYLOR · EDGHILL"). |
| Choral parts (strophe, antistrophe) | not searchable today; strophe marks are `GreekLine.label` | No. Choral odes as a unit would need a scene/ode table first (picture page, ruling (a)). |
| Partial failure: "Some plays could not be searched" with Retry | `Search.svelte` | Aristotle has its own notice; check it names plays. |
| CSV export with the drama names | `Search.svelte` | Yes (Aristotle's columns: Work, Book, Chapter, Bekker…); columns become Play, Line, Speaker. |
| "How to search" page and the phrase index link | `app/src/pages/search/how`, `search/phrases` | Aristotle has its own help; the plays' page is John-approved copy. |
| Old shared plays addresses keep working | `search-url.ts` | No: needs a decoder for the plays' parameters. |

Nothing in Aristotle's search knows Bekker columns that a play lacks: its `citation.ts` scheme switch
(`schemeFor`) already carries the plays' `play-line` scheme. Its counting, though, is chapters
(`chapter_bounds`), and every play's `chapter_bounds` is empty: a play would count as one chapter. So the
plays must pick their unit (ruling (a)) before the counting code can run on them.

## 5. The corpus files the new search fetches

Checked against a fresh `npm run build:public` of `bf7f153` (16 Nov), whose `build/dist` holds each play's
files.

| File | Aristotle's search reads it for | The plays' build |
|---|---|---|
| `<play>/search/meta.json` | segment ids, books, columns | yes; it also carries each segment's English text (`english_head`, `english_slots`), which Aristotle's meta has not |
| `<play>/search/form.json`, `lemma.json` | Greek postings `[seg, token]` | yes, same shape |
| `<play>/search/english.json` | the main translation's postings `[seg, word]` | **different shape**: one file for every translation, postings `[seg, translation id]`, no word positions (the plays find English positions in the meta text) |
| `<play>/search/english-<slot>.json` | each further translation's postings | **no** |
| `<play>/search/offsets.json` | token places; `chapter_bounds` for counting, paging, and proximity | yes, but `chapter_bounds` is empty in every play, and there is no `turn_bounds` (speakers) |
| `<play>/search/grammar-col.bin`, `grammar-dict.json` | grammar terms, Group by grammar | yes; check the dictionary carries the `lemma` field Aristotle's data has since 13 Nov |
| `<play>/search/running.json` | "running text" search (regular expressions across word breaks) | **no** (Aristotle's stage 6 writes it) |
| `<play>/chapters.json` | chapter names over the hits | yes, empty (`{}`) |
| `<play>/sections.json` | "Show the whole section" | **no** |
| `<play>/book-01.json` | the hit's text | yes |
| `search-shards/index.json`, `<stream>/<shard>.json` | corpus shards: one fetch per word, not per play | yes (stage 9), streams `lemma`, `form`, `english`; but the English stream's sources are play ids holding `[seg, translation id]` postings, where Aristotle's are `<work>/<slot>` holding `[seg, word]` |
| `search-shards/vocab.json` | patterns with no literal prefix (`*ικος`) | **no**; Aristotle falls back to reading every shard (slow, not wrong) |
| `search-shards/accents/<shard>.json` | Accents on, from the shards | **no**; falls back quietly |
| `lemma-map/<letter>.json`, `lemma-picker/<letter>.json`, `lemmata/…` | Lemma switch, headword list, glosses | yes |

What this means for the port:

- **Quiet failures.** Three missing pieces would not show an error:
  - `vocab.json` and the accent shards: Aristotle catches the miss and takes a slower path.
  - The English shard sources: Aristotle reads `<work>/<slot>`, finds nothing under that name, and
    goes back to the per-work file.
  - The per-work `english.json`: Aristotle would read the plays' `[seg, translation id]` postings as
    `[seg, word position]`. That gives wrong places, not an error.

  Not tested; the port's first gate is a test for each.
- **Pipeline work, in the plays' stage 6 and stage 9:**
  - one English index per translation, with word positions;
  - `running.json`, if John wants running-text search for the plays;
  - `turn_bounds`, from the speakers the books already carry;
  - the bounds of whatever unit John rules (speech, scene, ode), in `chapter_bounds` or a new field;
  - `sections.json`, or a play version of "Show the whole …" (the speech, the ode).
- **Old indexes go too.** The plays' English search would read the new files. Once nothing reads the old
  `english.json` shape, remove it. Change `english_slots` in the meta to suit.

## 6. How the new search sits inside the Vase

The Vase (`docs/redesign/DESIGN.md`, `app/src/styles/vase.css`) and B (`b.css`) differ in ways the
search page shows at once.

- **Type:** the Vase sets everything in Cardo, with Alegreya Sans for controls and labels. B uses Oswald
  700 capitals for titles and the count, Literata for text, and its own sans for controls.
- **Colour:** the Vase has paper `#f3ecdf`, ink, mid, and one accent, the clay: `--clay-deep` at 24 px
  and over, `--clay-text` under. B has a grey-white ground and a red ink accent `#b42419`.
- **Rules and boxes:** the Vase has "no horizontal rules, boxes, cards or shadows". B draws a rule under
  each group head and between hits, boxes Save search, and fills the Search button red.
- **Layout:** B's layout fits the Vase. It has two fields side by side with "and" between them, option
  words underlined in the accent, a rail with the count and the facet lists, a toolbar, and on the
  phone a results bar with Filter and View. That is close to the Vase's own search page, which already
  has the two fields and the option rows (UI pass 2, §8).

So the port can keep B's markup and swap its dress:

- Write a `vase-search.css` for the plays in place of `b-search.css`. Keep the class names; change
  tokens, faces, and rules.
- Map B's tokens to the Vase's (`--red-ink` to `--clay-text`/`--clay-deep`, `--line` to `--hair` where
  a rule must stay, `--hl` to `--hit`).
- Drop the rules, boxes, and fill.
- Titles and the count go in Cardo, not Oswald.

The mock on the picture page does exactly this, with the plays' own data.

Rules that carry over from Aristotle's handoffs: never shrink type or tap targets (44 px), no explainer
text in the reader, no sideways scrolling (the plays' own rule, John 20 Oct).

## 7. Baseline

`search-counts.mjs` runs 15 searches on the built site and writes `counts-base-2026-11-16.json`. Run it
again after the port: every count that moves must be explained. `units.py` reads the corpus directly
(not the page) and gives the counts under each candidate unit, `units.json`. `shots.mjs` takes the
screenshots at the three widths and both themes.

| Search | Bar | Total | Plays | Pages | Rows on page 1 |
|---|---|---|---|---|---|
| Greek exact form | 72 lines in 27 plays · page 1 of 2 | 72 | 27 | 2 | 35 |
| Greek lemma | 424 lines in 42 plays · page 1 of 15 | 424 | 42 | 15 | 24 |
| Greek wildcard | 1621 lines in 44 plays · page 1 of 42 | 1,621 | 44 | 42 | 29 |
| Beta Code typed | 72 lines in 27 plays · page 1 of 2 | 72 | 27 | 2 | 35 |
| Greek any word (lemma) | 1999 lines in 44 plays · page 1 of 43 | 1,999 | 44 | 43 | 49 |
| Greek phrase | 164 lines in 34 plays · page 1 of 5 | 164 | 34 | 5 | 36 |
| Accents observed | 102 lines in 37 plays before accent filtering · page 1 of 3 | 102 | 37 | 3 | 39 |
| English | 521 lines in 42 plays · page 1 of 15 | 521 | 42 | 15 | 28 |
| English phrase | 180 lines in 38 plays · page 1 of 6 | 180 | 38 | 6 | 34 |
| English, no other forms | 2634 lines in 44 plays · page 1 of 43 | 2,634 | 44 | 43 | 44 |
| Both, and | 570 lines in 39 plays · page 1 of 16 | 570 | 39 | 16 | 30 |
| Both, or | 945 lines in 43 plays · page 1 of 26 | 945 | 43 | 26 | 37 |
| Near: δίκη near θεός (lemmas) | 74 lines in 26 plays · page 1 of 2 | 74 | 26 | 2 | 38 |
| Oresteia only | 96 lines in 3 plays · page 1 of 3 | 96 | 3 | 3 | 32 |
| Murray OCT edition | 422 lines in 42 plays · page 1 of 14 | 422 | 42 | 14 | 24 |

What the baseline shows:

- **The bar counts hits, not lines.** "Both, or" is 945 = 424 (Greek) + 521 (English), exactly. Each
  English hit counts once per translation that has it. On the δίκη and justice page, lines 414–415 of
  the *Seven* count four times: once for δίκη, and once for each of three translators' "Justice".
- **The lemma pulls in another verb.** δίκη as a lemma also ticks δικεῖν ("throw, cast"), because the
  two share a fold key. The page offers it as a check the reader can untick. The lemma count (424) is
  above the corpus count for the headword δίκη alone in `units.py` (407 word hits) for that reason.
- **Accents shows the unfiltered count.** The bar reads "102 lines in 37 plays before accent filtering",
  so the total is not the number of rows the pages draw.
- **Pages are cut by whole plays at about 40 hits.** Page 1 can hold 24 rows or 49.
- **Two display faults in the current results** (screenshots on the picture page). Smyth's English
  shows raw markup: `_Exit Melanippus._` (a stage direction) and `[^11.584]` (a footnote marker). Both
  are on page 1 of δίκη and justice, *Seven Against Thebes*. This is a follow-up for the current site,
  not part of the port.

## 8. The counting unit, for ruling (a)

Picture page: https://claude.ai/artifact/PpzSgrGBpP4cFN2G6erBx7. Numbers from `units.json`, all 44
plays, 58,966 lines.

| | Line | Speech | Scene | Choral ode |
|---|---|---|---|---|
| Units in the corpus | 58,966 | 16,572 | 566 | 264 |
| Lines per unit: median · 90% · longest | 1 | 1 · 7 · 203 | 65.5 · 237 · 1,209 | 32.5 · 89 · 298 |
| δίκη (lemma): units with a hit | 403 | 348 | 183 | 44 |
| justice, any translation | n/a | 270 | 146 | 41 |
| justice, main translation | n/a | 148 | 102 | 29 |
| δίκη and justice | n/a | 148 | 113 | 29 |

- **"And" can't be tested by line.** The English is stored by segment (one speech, cut at 40 lines), so
  no line can be tested for both words. 1,981 segments hold two speakers (antilabe); there the English
  goes to both speeches, which touches 9 of the 148 "and" speeches.
- **Scenes and odes are cut by a rule.** It reads speaker names and strophe marks (`units.py` says
  how). The corpus marks neither, and Euripides' Greek here prints no strophe marks. A real scene or ode
  unit needs a table per play, made by hand.
- **The speech is the nearest thing to Aristotle's paragraph.** It is a whole utterance with its
  speaker, and every translation is already stored that way, apart from lines two speakers share. That is my suggestion on the page, marked
  as mine.
