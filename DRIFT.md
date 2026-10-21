# DRIFT.md

Fork point: `~/Developer/classical-philosophy-reader` @ `233ec2547a39b9ba82f6743a92d5ecba45e7dc93` (2026-09-05).
Files ported from other siblings are listed with their source.

One line per file under `shared/`, `app/`, `scripts/`, `schemas/`, `pipeline/`
that diverges from the fork point for a drama-specific reason, added in the
same commit as the divergence, so a patch-forward from CPR knows what not to
overwrite. Format follows `~/Developer/homer-reader/DRIFT.md`.

## P0 — bootstrap (strip to a drama-ready core, zero-works gates green)

### pipeline/ (package renamed `reader_pipeline` → `drama_pipeline`; `READER_PY` → `DRAMA_PY`)

- `pipeline/pyproject.toml` — package name `reader-pipeline` → `drama-pipeline`.
- `pipeline/drama_pipeline/__main__.py` — `_stage1`'s lat dispatch replaced
  with a loud `SystemExit` (Latin/PHI removed); the unconditional
  `stage1_context_english`/`stage1_citation_expansion` calls, the
  verse-line/numeric_section/flat_numeric/fragment_scheme dispatch branches,
  and the Bekker-default `chapters_cfg` else-branch (Ross/Ostwald/Archive/
  Chapters, the `align/` aligner) all replaced with `NotImplementedError` —
  every one of those builders was CPR/Aristotle-corpus-specific with no
  drama use (docs/plan.md §1). `has_sections`/`perseus_stephanus` dispatch
  (stage1_stephanus_english.py) is the only builder path left live.
- `pipeline/drama_pipeline/preflight.py` — removed `dk_lang` import and all
  DK/Freeman/section-paragraph validation (`_validate_dk_work`,
  `_dk_expected_all_context_columns`, `_dk_decisions_for_preflight`,
  `_validate_freeman_kinds`, `_freeman_spine_columns`,
  `_validate_freeman_paratext`, `_validate_freeman_manifest_declarations`,
  `_whole_column_verbatim_columns`, `_ascending_marker_count`,
  `_validate_section_paragraph_columns`, `_freeman_override_columns`) —
  corpus-specific walkers/validators for deleted content; the `dk` scheme
  itself stays registered, now with a loud "no corpus-specific validation"
  problem instead. `work.language` now rejects anything but `'grc'`
  (previously `'grc'`/`'lat'`) with a clear message; `work.lexicon: false`
  is now never permitted (was a Latin-only affordance).
- `pipeline/drama_pipeline/stage1_greek.py` — removed the `dk_lang` import
  and the entire DK (Diels-Kranz) fragment/testimonium walker
  (`_dk_clean_line_text`, `_dk_role_blocks`, `_dk_merge_blocks`,
  `_dk_rejoin_hyphen_across_role_blocks`, `_dk_load_context_lang`,
  `_dk_walk_verse_div`, `_dk_walk_verse_div_prose_runs`,
  `_dk_normalize_quote_marks`, `_parse_fragments`, plus their regex
  constants) — corpus-specific, no drama use. `parse_spine`'s `dk`-scheme
  dispatch branch now raises `NotImplementedError` instead of calling the
  deleted walker.
- `pipeline/drama_pipeline/stage3_tokenize.py` — removed the `latin` import
  and Latin dispatch (`_is_latin_letter`, `_contains_latin`,
  `_is_no_op_numeral`, `_to_latin_lookup_key`) from `_LANGUAGE_PUNCT`/
  `_LANGUAGE_DISPATCH`/`_SPINE_FILENAMES` (now `grc`-only).
- `pipeline/drama_pipeline/stage4_morphology.py` — removed the `latin`
  import and lat branch from `_lookup_variants`/`_ANALYSES_FILENAMES`
  (now `grc`-only).
- `pipeline/drama_pipeline/stage5_lsj.py` — removed the lat entries from
  `_DICTIONARY_FILENAMES`/`_DIV_TAG`/`SHARD_DIR` and the entire Latin
  homonym-fan-out filter (`_lemma_parse_hints`, `_analysis_pos_class`,
  `_entry_pos_class`, `_is_crossref_stub`, `_filter_homonym_candidates`) —
  Latin-only, no drama use.
- `pipeline/drama_pipeline/stage6_search.py` — removed the `latin` import
  and lat branch from `fold()` (now `grc`-only).
- `pipeline/drama_pipeline/stage7_emit.py` — removed the `dk_witness`
  import and the DK apparatus-witness-split block in `emit_books` (`role`
  only exists on dk columns); `witnesses` is now unconditionally `None`.
- `pipeline/drama_pipeline/align/__init__.py`, `.../align/similarity.py` —
  the CPR `align/` subpackage was almost entirely dead code once the
  Bekker-default dispatch (Ross/Ostwald/aligner path) was removed; kept
  only `similarity.py` (zero-dependency TF-IDF `cos_matrix`, still used by
  `align_turns.py`'s LCS pairing) and rewrote `__init__.py` as a bare
  docstring stub (no longer re-exports `aligner.align`, since `aligner.py`/
  `reference.py`/`glossing.py`/`gloss_review.py`/`review_html.py`/its own
  `__main__.py` were deleted).
- `pipeline/drama_pipeline/validate_contracts.py` — an empty `--dist`
  (zero-works build) now prints "no works: ..." and continues (validates
  `--snapshot`/`--registry` alone) instead of exiting 1.
- `pipeline/drama_pipeline/verify_shared_lsj.py` — zero `analyses.json`
  files under `build/dist` now prints "no works: ..." and returns 0
  instead of failing.
- Deleted (no drama use, per docs/plan.md §1): `latin.py`,
  `stage1_latin.py`, `stage1_verse_line_english.py`, `dk_lang.py`,
  `dk_witness.py`, `stage1_freeman_english.py`, `stage1_context_english.py`,
  `stage1_citation_expansion.py`, `stage1_ross.py`, `stage1_ostwald.py`,
  `stage1_chapter_concordance_english.py`, `stage1_book_section_english.py`,
  `stage1_flat_english.py`, `stage1_chapters.py`, `stage1_perseus.py`,
  `stage1_archive.py`, `align/aligner.py`, `align/reference.py`,
  `align/glossing.py`, `align/gloss_review.py`, `align/review_html.py`,
  `align/__main__.py`, `align/README.md`, `tools/` (entire directory, ~40
  one-off CPR extraction scripts), `generate_review_html.py`.

### manifests/

- `manifests/authors.yaml` — emptied to `authors: []`, `school_groups: {}`,
  `work_order: []` (was the full 29-author/62-work CPR roster).

### scripts/

- `scripts/build-public.mjs` — `reader_pipeline`/`READER_PY` →
  `drama_pipeline`/`DRAMA_PY`; removed the multi-corpus mount loop
  (`mount-corpus.mjs`, deleted) and the LSJ-topup step (mounted-corpus-only,
  `lsj_topup.py` itself stays in the pipeline); removed the
  `verified > 20` INVENTORY floor; `CORPUS_VERSION`'s git-sha lookup falls
  back to `'nogit'` instead of crashing on a repo with no commits yet; zero
  declared works now logs "No works declared..." and still produces an
  (empty) `build/dist` instead of failing the post-build sanity check.
- `scripts/build-registry.mjs` — removed `aristotleVendoredSource` (read
  `corpora/aristotle/{registry,authors,groups}.yaml`, deleted along with
  all Lyceum-mount hub machinery) and its `CATEGORIES` groups; the
  generator now reads only `manifests/*.yaml` + `manifests/authors.yaml` +
  `fixtures/manifests/*`.
- `scripts/verify-fixture-build.mjs` — check (d) no longer expects the
  breadcrumb's "Switch author"/"Switch work" `<select>` placeholders
  (removed, see `app/src/components/Breadcrumb.svelte` below); asserts no
  `<select>` remains in the breadcrumb nav instead.
- `scripts/verify-registry-roundtrip.mjs` — `main()` now skips cleanly
  (prints a message, exits 0) when the repo has fewer than two commits or
  the `--baseline` ref doesn't resolve, instead of crashing `git rev-parse`.
- `scripts/emit-lyceum-manifest.mjs` — `listManifests()` returns `[]` for a
  zero-works `--dist` instead of throwing (an explicit `--work` with no
  match is still fatal).
- Deleted (hub-only Lyceum-mount machinery, no drama use before P6):
  `mount-corpus.mjs`, `lib/corpus-adapter/` (+ its tests),
  `probe-corpus-compat.mjs`, `vendor-aristotle-registry.mjs`,
  `audit-wave2-adoption.mjs`, `verify-discourses-lineation.mjs`,
  `verify-lined-source.mjs`, `adopt-export.mjs`, `ingest-review-export.mjs`
  (+ its test), `build-review-dashboard.mjs` (+ its test) and the two
  `review-dashboard-shell*.html`, `migrate-checklist-ids.mjs`,
  `extract-registry.mjs`, `lib/review-checklist.mjs` (parsed the deleted
  `REVIEW-CHECKLIST.md`, never actually present in this repo).

### shared/

- `shared/components/RunningHead.svelte` — removed `LibrarySheet` (deleted)
  entirely: the author/work names are now plain `<a>` links
  (`authorPath`/`workLanding`, wrapped in try/catch to fall back to the
  site root for a fixture id with no resolvable registry entry) instead of
  buttons opening a library-browse sheet; `sheet`'s type narrowed to
  `'contents' | null`. Matches the drama ruling: no play-switcher, no
  library sheet inside the reader.
- Deleted: `shared/components/LibrarySheet.svelte`.
- Comment-only path fixes (`pipeline/reader_pipeline/...` →
  `pipeline/drama_pipeline/...`, no logic change): `shared/styles/global.css`,
  `shared/components/WordPopup.svelte`, `shared/lib/search.ts`,
  `shared/lib/speakers.ts`, `shared/lib/data.ts`, `shared/lib/citation.ts`,
  `shared/lib/works.ts`.

### app/

- `app/src/lib/site.ts` — rewritten: `SITE_NAME = 'The Greek Drama Reader'`
  only; `LYCEUM_SITE_NAME`/`siteNameFor` removed (no Lyceum-chrome
  alternate skin in this fork).
- `app/src/pages/index.astro` — rewritten: always renders `ClassicHome`
  (the `LyceumHome`/`PUBLIC_LYCEUM_CHROME` branch removed, `LyceumHome`
  deleted).
- `app/src/components/ClassicHome.astro` — home-page meta description and
  the feedback-form mailto subject de-philosophy'd ("Classical Philosophy
  Reader" → "The Greek Drama Reader"; "Thales to Boethius" copy →
  drama-neutral placeholder marked `<!-- DRAFT copy: John approves -->`).
- `app/src/components/Landing.astro`, `app/src/components/ReaderShell.astro`
  — removed the entire `PUBLIC_LYCEUM_CHROME`/`lyceumChrome` branch (the
  `LyceumBand` sitewide chrome, the alternate `RunningHead`-driven reader
  chrome in ReaderShell, the `lyc-chrome` script) — only the plain-reader
  path remains, unconditional. ReaderShell.astro also dropped the
  `DkExplainer` (deleted) condensed-pointer block and its `dkChapterNum`/
  `dkNoSeries` consts.
- `app/src/pages/404.astro`, `search.astro`, `authors.astro`,
  `support.astro`, `lemma/grc/index.astro`, `lemma/grc/entry.astro`,
  `lemma/lat/index.astro`, `lemma/lat/entry.astro`, `[author]/index.astro`
  — same `PUBLIC_LYCEUM_CHROME` branch removal (`LyceumBand` import,
  `lyceumChrome` const, the conditional font `<link>`, the `<body>` class
  ternary, the chrome/no-chrome template fork) plus `siteNameFor(...)` →
  the plain `SITE_NAME` import; `[author]/index.astro` also dropped its
  `DkExplainer` usage and `dkChapterNum`/`dkNoSeries` consts. `authors.astro`
  and `search.astro` and `support.astro` additionally had their
  "ancient philosophers" SEO/lede copy replaced with drama-neutral text,
  marked `<!-- DRAFT copy: John approves -->`.
- `app/src/components/Breadcrumb.svelte` — removed both
  `<select class="work-switcher">` controls (and their now-dead
  `goAuthor`/`goWork` handlers, and the `resumeFor`/`workPath` imports they
  alone used) — crumbs are plain links only, per the drama ruling (no
  play-switcher inside the reader).
- `app/public/manifest.webmanifest` — name/short_name/description updated
  to The Greek Drama Reader.
- `app/public/data` — new symlink to `../../build/dist` (the CPR fork's
  copy of this repo's file tree had dropped this symlink; restored it,
  matching `~/Developer/classical-philosophy-reader/app/public/data`'s own
  tracked symlink — required for `PUBLIC_READER_FIXTURES=1`/`build:public`
  to find any built work data at all).
- Deleted: `app/src/components/LyceumBand.astro`, `LyceumHome.astro`,
  `DkExplainer.astro`, `app/src/lib/lyceum-catalog.ts`,
  `app/src/pages/catalog/[...slug].astro` (+ its directory).

### ADDING-A-WORK.md, package.json, .github/workflows/ci.yml, docs/verification-battery.md

- `ADDING-A-WORK.md` — replaced with a 20-line stub pointing at
  `docs/plan.md` (the real per-work recipe lands at P1 with the `play-line`
  scheme).
- `package.json` — `name` → `greek-drama-reader`.
- `.github/workflows/ci.yml`, `docs/verification-battery.md` — comment/path
  fixes only (`reader_pipeline`/`READER_PY` → `drama_pipeline`/`DRAMA_PY`);
  no structural changes were needed (ci.yml already carried no references
  to any of the deleted hub-only scripts or CPR corpora).

## Dictionary — Grammata T8 for all LSJ (John's ruling 2026-09-05, ported
from aristotle-reader per its `HANDOFF-LSJ.md` §0–1)

### shared/

- `shared/components/WordPopup.svelte` — cards are now keyed by dictionary
  entry (an analysis can name several LSJ keys; each gets its own card) and
  the entry itself is Grammata's T8 widget: opening a card mounts a
  `.grammata-mount` div and calls `loadGrammataLookup()`
  (`shared/lib/grammata.ts`) with `{ lang, key }`. Renders no local LSJ
  entry HTML; on a lookup failure the mount gets one line of status text,
  no local fallback render.
- `shared/lib/data.ts` — dropped the local-shard dictionary path
  (`LsjEntry`, `fetchLsjShard`, `lsjShard`) and the `lsj` field
  `lookupWord` used to return; added `fetchLsjHeads()` (fetches
  `lsj-heads.json` once through the active data root — headword +
  homograph letter only, for the popup/lemma-page card, never an entry).
- `shared/lib/html.ts` — dropped the local LSJ-entry renderer
  (`renderLsjEntry`, `outlineLsjSenses`, `stampSenseDepth`,
  `prefixLsjCitationHrefs` and their private helpers) — Grammata renders
  every entry now; `sanitizeHtml` (general corpus-HTML sanitizer, not
  LSJ-specific) is the only export left.
- `shared/lib/grammata.ts` (new) — `loadGrammataLookup()`, the ONE place
  that dynamically imports Grammata's `t8/lookup.js`
  (`/* @vite-ignore */`, memoized). Do not vendor, pin, proxy or
  cache-bust that URL elsewhere.
- `shared/styles/global.css` — dropped the local LSJ-entry rendering rules
  (`.lsj-entry`, `.lsj-sense`, `.lsj-section`, `.lsj-head`/`.lsj-gen`/
  `.lsj-etym` and friends) — dead now that Grammata owns the entry's own
  markup and styles; kept `.lsj-ambiguous-note` (the homonym fan-out
  label, still live in WordPopup.svelte).

### app/

- `app/src/components/LemmaEntry.svelte` — the `/lemma/<lang>/entry/` page
  mounts the same Grammata widget (`.grammata-mount[data-key]`) instead of
  `{@html renderLsjEntry(...)}`; dropped the `dictHtml` field from its
  fetched `LemmaData` shape.
- `app/src/lib/html.ts` — re-exports only `sanitizeHtml` now (was also
  `renderLsjEntry`/`outlineLsjSenses`/`stampSenseDepth`/
  `prefixLsjCitationHrefs`).
- `app/scripts/build-lsj-heads.mjs` (new) — builds `lsj-heads.json` (LSJ
  key → `{ head, hom }`) from the pipeline's LSJ shards; the site ships no
  shard HTML, only this small manifest.

### scripts/

- `scripts/build-public.mjs` — wired `app/scripts/build-lsj-heads.mjs`
  into `npm run build`, right after `verify_shared_lsj`.

## P1.1 — printed play order, duplicate refs, and canonical speaker rosters

- `pipeline/drama_pipeline/stage1_greek.py` — play-line parsing now rejects a repeated printed ref before segmentation.
- `pipeline/drama_pipeline/preflight.py` — the dist check rejects repeated play-line refs, and play-line manifests must declare a valid `speakers.sigla` map with `"—": null`.
- `pipeline/drama_pipeline/stage7_emit.py` — play-line segments stay in document order, speaker events gain canonical displays, and each book gains a first-appearance `speakerRoster`; the existing unmapped-siglum gate now serves both play-line and Stephanus works.
- `pipeline/gen_speaker_rosters.py` — ported the Plato roster helper for play-line build output and safe manifest-block rewrites.
- `pipeline/tests/test_scheme_play_line.py`, `pipeline/tests/fixtures/play_line/synthetic_transposition.xml` — cover printed transposition order, the required declaration, duplicate refs, canonical event displays, the unmapped gate, and roster order.
- `pipeline/drama_pipeline/scheme.py` — `play_line_kind` rejects a range whose end is not after its start (Sol review 2026-09-05 item 8; orchestrator edit).
- `pipeline/drama_pipeline/stage1_greek.py` — `_PLAY_LINE_STROPHE_RE` is case-sensitive: a capitalised siglum (`Στρ.`) stays a speaker (Sol review item 9; orchestrator edit).

## P1.1 web review fixes (2026-09-06)

- `shared/components/Reader.svelte` — play gutters use printed refs, and lacunae have no citation or scroll-spy target.
- `shared/components/Search.svelte` — empty play outlines form one group, and play hits cite and jump by `GreekLine.ref`.
- `shared/lib/citation.ts` — `post N` is not a location, and flat or reversed play-line ranges fail validation.
- `shared/lib/grammata.ts` — a failed remote-module import clears the cached loader so a later request retries.
- `shared/lib/speaker-colors.ts` — the collision-free speaker palette now has twelve slots.
- `shared/lib/works.ts` — one-book play-line readers use the bare work path as their sole URL.
- `shared/styles/global.css` — four contrast-checked speaker colors extend both themes and all speaker selectors.

## P1.2 fix round (Sol re-review, 2026-09-06)

- `shared/components/Search.svelte` — a chapterless (work-wide) result group opens by default like a single-instance group, instead of collapsing multi-hit play-line results behind a click.
- `shared/lib/search.ts` — added `invalidateSearchIndex(work)`, mirroring `data.ts`'s `invalidateBookCache`, so a test (or a future re-fetch need) can force a work's cached meta/lemma/form/english index files to reload.
## P2a — Agamemnon English pilot (2026-09-06)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` (new) — cuts
  Smyth's `<sp>/<l n>` prose onto Greek play-line segments, snaps missing
  anchors, keeps raw speaker turns, and extracts unique Loeb footnotes.
- `pipeline/drama_pipeline/__main__.py` — dispatches `play-line` manifests
  with `english.primary.model: perseus-play` to the new builder while keeping
  declared Greek-only plays sparse and safe from stale scratch files.
- `pipeline/drama_pipeline/preflight.py` — accepts the `perseus-play` source
  shape and checks every English id against a fail-closed public-domain list.
- `pipeline/drama_pipeline/stage2_validate.py` — treats anchorless play-line
  segments as the `perseus-play` model's stated sparse coverage, while keeping
  English-only ids fatal.
- `pipeline/drama_pipeline/public_domain_translations.yaml` (new) — positive
  US public-domain list for the planned tragedy and comedy translations, with
  O'Neill's 1938 Aristophanes translations denied in a source comment.
- `pipeline/drama_pipeline/stage7_emit.py` — emits the primary play
  translation's footnote map and reports raw English/Greek roster differences.
- `pipeline/tests/test_stage1_perseus_play_english.py` (new) — covers segment
  cuts, real ticks, snapping, deleted text, note labels, turns, and coverage.
- `pipeline/tests/test_public_domain_allowlist.py` (new) — covers allowlist
  success plus missing-file, unknown-id, and empty-list failures.
- `pipeline/tests/test_preflight.py` — points end-to-end legacy fixtures at
  their own small public-domain test list.
- `pipeline/tests/fixtures/preflight/public_domain_translations.yaml` (new) —
  keeps old corpus fixtures explicit under the new rights gate.
- `scripts/check-registry-agreement.mjs` — lets its corruption self-test use
  the one-translation pilot by adding a matched in-memory second slot.

## P2b — English-builder adversarial fixes (2026-09-06)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — speech-scoped
  attachment, packed-elder para/em-dash slices, same-speech snaps only,
  `speakers.english` aliasing on turns, `<stage>`/`<gap>` skip, hyphen-free
  footnote labels.
- `pipeline/drama_pipeline/stage2_validate.py` — perseus-play unmatched
  segments pass only when named in `english.gaps`.
- `pipeline/drama_pipeline/stage7_emit.py` — unmapped English speakers hard-
  fail; `footnotes: true` is copied onto the v1 translations entry.
- `pipeline/drama_pipeline/preflight.py` — allowlist walk covers every id
  stage7 can emit; denied patterns reject O'Neill on name/source even when
  the id is allowlisted.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `denied:` list
  with the O'Neill pattern.
- `pipeline/tests/test_stage1_perseus_play_english.py` — speech-scoped
  attachment, packed elders, cross-speech snap refusal, english.gaps,
  alias-table hard failure, `<stage>` skip, hyphen-free markers, footnotes
  flag.
- `pipeline/tests/test_public_domain_allowlist.py` — column_sources /
  summary_overlay walk plus O'Neill name/source denial on an allowlisted id.

## P2c — play-line English colours and footnotes (2026-09-06)

- `shared/lib/speakers.ts` — EnglishTurnBlock copies each turn's canonical
  `speaker` (the colour key).
- `shared/components/Reader.svelte` — play-line English lead-ins share
  data-spk with the Greek roster entry; play-line English `[^label]`
  markers (underscore labels included) open FootnotePopup.
- `shared/__tests__/speakers.test.ts` — buildEnglishTurnBlocks carries
  `speaker` onto blocks.
- `shared/__tests__/reader-play-line.test.ts` — play-line English/Greek
  data-spk parity, display fallback, underscore footnote control.

## P3 bench — Storr Antigone secondary (2026-09-07)

- `pipeline/drama_pipeline/bench_clean.py` (new) — Loeb facing-page OCR
  cleaner: locate play by title/next heading, drop Greek pages (ratio > 0.3),
  strip running heads/page numbers/line numbers, rejoin hyphens, fold own-line
  caps names into `NAME. text`.
- `pipeline/drama_pipeline/stage1_turn_english.py` — `format: loeb-ocr` and
  `run(..., slot="secondary")` writing `ross_chunks.json` as overlay pieces.
- `pipeline/drama_pipeline/__main__.py` — play-line `english.secondary` with
  `model: turn-text` dispatches the same builder.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `storr` note
  names the 1912 Sophocles Loeb.
- `pipeline/tests/test_bench_clean.py` (new), `test_stage1_turn_english.py`
  — loeb-ocr parse, overlay prefix, secondary `ross_chunks.json`.
- `docs/bench.md` (new) — cleaner recipe and per-play checklist.

## P2c — English line-owner attachment (2026-09-07)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — attach each
  `<l n>` to the Greek segment that owns that printed number, even on
  speaker mismatch; split a multi-n English `<sp>` across those segments
  (span-fill intervening speeches); keep speech-scoped snaps for anchors
  absent from the spine.
- `pipeline/drama_pipeline/stage2_validate.py` — lacuna auto-allow requires
  empty text; `_play_line_twin_segment_ids` allows repeated-ref seconds
  and lettered twins without a declared gap.
- `pipeline/tests/test_stage1_perseus_play_english.py` — line-owner split,
  span-fill, Cassandra 1077 on the line owner, twin validate().
- `pipeline/tests/test_scheme_play_line.py` — lacuna empty-text through
  `validate()`, mixed segment fails, twin id helper.

## P3.1 — comedy turn-text review fixes (2026-09-07)

- `pipeline/drama_pipeline/stage1_turn_english.py` — accepts alias-gated
  period-less and own-line speakers, preserves speech paragraphs, applies
  per-work line fixes, stops notes at headings, rejects roster gaps, reports
  paired length-ratio outliers, and attaches head residue to segment 0.
- `pipeline/tests/test_stage1_turn_english.py` — covers each parser fix against
  focused fixtures and the real Athenian Society comedy sources.

## P3.2 — play-line translation comparison (2026-09-07)

- `shared/components/Reader.svelte` — resolve each play-line picker id through
  its registry slot, render that slot's turn stack in single and compare mode,
  and show the aligned-passage gap when the chosen slot has no segment text.
- `shared/lib/data.ts`, `shared/lib/speakers.ts` — type structured overlay turns
  and recover turn data from legacy speaker-prefixed overlay text.

## Comedy comparison slots (2026-09-07)

- `manifests/clouds.yaml` — Hickie Bohn 1853 as `english.secondary` (`perseus-play`, bowdlerized comparison slot).
- `manifests/lysistrata.yaml` — Lindsay 1925 as `english.secondary` (`turn-text`, alignment approximate).
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `hickie` note names Bohn 1853 and the bowdlerized comparison slot; `lindsay` already listed.
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — `run(..., slot="secondary")` writes `ross_chunks.json` from a Perseus play TEI.
- `pipeline/drama_pipeline/__main__.py` — play-line `english.secondary` with `model: perseus-play` dispatches that builder.
- `pipeline/drama_pipeline/stage1_turn_english.py` — Lindsay own-line speakers may carry a trailing `(_stage_)`; ellipsis (`O....`) is not a speaker.
- `pipeline/tests/test_stage1_turn_english.py` — real `pg7700.txt` speech count and first/last speaker.
- `docs/bench.md` — comedy comparison-slot section.
- `shared/__tests__/reader-play-line.test.ts` — cover secondary selection,
  distinct compare columns, stable speaker colours, and sparse coverage.

## P3.2 — comedy turn-text follow-up (2026-09-08)

- `pipeline/drama_pipeline/stage1_turn_english.py` — restrict period-less
  speaker labels to a full alias, keep date lines in notes, and leave
  wrong-speaker head residue unassigned.
- `pipeline/drama_pipeline/__main__.py`,
  `pipeline/drama_pipeline/stage2_validate.py` — show speech mismatches and
  fail turn-text validation above the configured mismatch rate.
- `pipeline/tests/test_stage1_turn_english.py` — pin all eleven real source
  openings, note tails, cast-list residue, and the mismatch gate.
- `docs/play-line.md` — document the tighter parser and validation rules.

## Comedy comparison slots — Hickie / Rogers (2026-09-08)

- `pipeline/drama_pipeline/bench_clean_verse.py` — `--layout prose-inline` for Hickie Bohn 1853 (inline `Dic.` labels, dramatis abbreviation table, `Cuo. or Men.` choruses, `S. S.` sausage-seller, Demus-after-entrance).
- `pipeline/drama_pipeline/bench_clean.py` — Rogers Loeb titles, short-label expansion (`CA.` → `CALONICE`), `ARISTOPHANES` not a speaker.
- `pipeline/drama_pipeline/stage1_turn_english.py`, `__main__.py` — turn-text `english.third` writes `third_chunks.json`; `english.overlays[]` merges `overlays.json`.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `rogers` note names Loeb 1924 and bowdlerized comparison-only.
- `manifests/{acharnians,knights,wasps,peace,birds,thesmophoriazusae,frogs,ecclesiazusae,wealth}.yaml` — Hickie as `english.secondary`.
- `manifests/lysistrata.yaml` — Hickie as `english.third`, Rogers as overlay.
- `manifests/{thesmophoriazusae,ecclesiazusae,wealth}.yaml` — Rogers as `english.third`.
- `sources/bench/hickie/*.txt`, `sources/bench/rogers/*.txt` — cleaned comparison texts.
- `docs/bench.md` — Aristophanes Hickie/Rogers table.
- `pipeline/tests/test_bench_clean_verse.py`, `test_bench_clean.py`, `test_stage1_turn_english.py` — prose-inline special cases, Rogers short labels, third-slot `third_chunks.json`.

## P2d — tragedy attachment review fixes (2026-09-08)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — each numbered
  piece attaches once; owner-over-speaker only for a multi-segment English
  `<sp>`; a singleton mismatch repairs to the nearest same-speaker Greek
  speech within ±3 (earlier on a tie) or stays unmatched; lettered `<l n>`
  kept; `speech_mismatch_count` is all mismatch rows,
  `unresolved_mismatch_count` is rows with no `attached_to`. Secondary-slot
  `run(..., slot="secondary")` → `ross_chunks.json` kept.
- `pipeline/drama_pipeline/stage2_validate.py` — a lettered twin is
  auto-allowed only when the source TEI has no nonempty matching `<l n>`.
- `pipeline/tests/test_stage1_perseus_play_english.py` — P2d cases (1077
  repair, unresolved mismatch, Ag. 1203–1213 swap, translated 1270a).
- `docs/play-line.md` — English attachment contract (no six-line
  extension; lettered twins gated on the TEI).

## P2e — continuation coverage (2026-09-08)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — Greek
  segments inside an English speech's attached line span (or between a
  single attached anchor and the next English owner) get
  `english_covered_by` pointing at the segment that holds the piece;
  `covered_by_count` in `english_report.json`; alignment.json carries
  the parallel map. Lacunae and declared gaps stay unmarked.
- `pipeline/drama_pipeline/stage2_validate.py` — a segment with
  `englishCoveredBy` counts as covered, not unmatched.
- `pipeline/drama_pipeline/stage7_emit.py` — emit `englishCoveredBy` on
  the book segment (string segment id) when english is null.
- `pipeline/tests/test_stage1_perseus_play_english.py` — stichomythia
  fixture (1320 chunk, 1321–1324 covered by 1:1320, 1325 chunk),
  outside-span and lacuna unmarked, stage2 covered, stage7 field.
- `docs/play-line.md` — field and "translated above" reader behaviour.

## P3 bench — Storr's other six Sophocles plays (2026-09-08)

- `pipeline/drama_pipeline/bench_clean.py` — locate OCR-damaged or missing
  title pages, split mixed facing pages at Greek-head OCR variants, repair
  speaker-label OCR, keep numbered semi-choruses, and drop leaked heads,
  stage stubs, numbers, and scan glyphs.
- `pipeline/tests/test_bench_clean.py` — synthetic coverage for each new
  title, page-split, speaker-label, semi-chorus, stage, and glyph special case.
- `docs/bench.md` — per-play headings, report counts, roster aliases, and
  residual OCR notes for the six Storr sources.

## P2e — continuation coverage (2026-09-08, orchestrator)
- `shared/lib/data.ts` — `Segment.englishCoveredBy?: string` (play-line: this speech's English lives in the block anchored at that segment).
- `shared/components/Reader.svelte` — `playEngTurns` renders "Translated with the speech above ↑" (a `.eng-covered` button that scrolls to `col-<column>`) when `englishCoveredBy` is set and the shown translation has no piece, instead of the missing-passage dash; `scrollToSegment` helper.
- `shared/styles/global.css` — `.eng-covered` (italic, muted, underline on hover/focus).
- `shared/__tests__/reader-play-line.test.ts` — continuation-affordance test.

## P2f — attribution-difference line-owner attach (2026-09-08)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — a singleton
  speaker mismatch with no same-speaker Greek speech within ±3 attaches
  to the line owner and marks the chunk `speakerMismatch: {english, greek}`;
  drift still repairs to the nearest same-speaker speech without the flag.
  `attribution_differences` (+ count) in `english_report.json`.
- `pipeline/drama_pipeline/stage2_validate.py` — those attachments are
  real chunks, so they count as covered.
- `pipeline/drama_pipeline/stage7_emit.py` — emit `speakerMismatch` on
  the segment's english object.
- `pipeline/tests/test_stage1_perseus_play_english.py` — Messenger 1320 /
  Agamemnon flag, drift without the flag, packed elders and Seven 1040–1047.
- `docs/play-line.md` — P2f English attachment contract.
- `shared/lib/data.ts` — `EnglishChunk.speakerMismatch?: {english, greek}` (P2f: edition attribution difference recorded on the attached chunk).
- `shared/components/Reader.svelte` — play-line English lead-in carries `data-mismatch` + a title naming both attributions when the displayed chunk is the primary with `speakerMismatch`.
- `shared/styles/global.css` — `.turn-stack .speaker[data-mismatch]` dotted underline, help cursor.

## P2g — speaker resolution, loss gates, comedy speaker lines (2026-09-08)

- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — `_SpeechIndex`
  resolves Greek speakers through `stage1_turn_english._SiglaResolver`
  (stage7's `_norm_siglum` + `speakers.overrides` by printed ref) and owns
  `speakers_of` (the SET of a segment's mapped speakers); mismatch, repair
  and snap use set membership; continuation coverage requires a speaker
  intersection with the covering segment; a repaired attachment ticks a line
  the target itself prints; the duplicated `_speaker_report` is gone (it now
  reuses stage1_turn_english's, which already resolves with overrides).
- `pipeline/drama_pipeline/stage1_turn_english.py` — the periodless caps run
  ends before a single-letter capital; `_SPEAKER_LINE` requires space, `[`
  or end of line after the name's full stop; OCR-junk speeches take a
  never-matching `_OCR_JUNK` sentinel and a blank printed label; the length
  heuristic is reported as `length_ratio_outliers` and a real
  `turn_shifts` / `turn_shift_rate` is added.
- `pipeline/drama_pipeline/stage2_validate.py` — `_stage1_english_report`
  (fails closed on a missing / foreign report), `checks.attachment_loss`
  (`english.max_unresolved_mismatches`, default 0), `checks.alignment`
  reports `covered_ids` and allows them by reason,
  `checks.turn_text_mismatches` split into `turn_text_length_ratio` and
  `turn_text_turn_shift` (`english.max_turn_shift_rate`, default 0.05).
- `pipeline/drama_pipeline/__main__.py` — stage1 summary prints
  `unresolved=` / `covered=` (perseus-play) and `head_unassigned=`,
  `ratio_outliers=`, `turn_shifts=` (turn-text).
- `pipeline/tests/{test_stage1_perseus_play_english,test_stage1_turn_english,test_scheme_play_line}.py`
  and `pipeline/tests/fixtures/deterministic_stage2_stage3_golden.json`
  (`covered_ids` key).
- `manifests/{hippolytus,suppliants-aesch,lysistrata,oedipus-tyrannus,electra-soph}.yaml`
  — alias rows and the two Storr `line_fixes`.
- `docs/play-line.md` — §English and the turn-text contract.

## P2h — per-line speaker attribution, per-turn mismatch (2026-09-08)

- `pipeline/drama_pipeline/stage1_turn_english.py` — shared line-level speaker
  rule: `_segment_speaker_events` / `speaker_at(segment, line, sigla,
  prefer=…)` (offset-aware: line-start speaker plus antilabe shares);
  `_greek_segment_name` now pairs on the first line's offset-0 speaker and
  `_greek_segment_alt_names` lets a gap turn pair with a packed segment's
  second speaker (`_pair_turns` takes `greek_alt`).
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — `_SpeechIndex`
  gains `speaker_at` / `speaker_lines` / `packs_other_speaker`; owner check,
  repair search (candidate must speak a LINE; tick that line, earlier on a
  tie), off-spine snap and continuation coverage (the English speech's own
  speaker) all go per printed line; claims are `(segment, speaker)` pairs and
  never block the segment that prints the line; the P2f line-owner fallback
  refuses a packed other-speaker span and records an `attribution_hole`
  (`attribution_holes` + count + anomaly); `speakerMismatch` rides on the
  English TURN, the chunk-level copy only when every turn disagrees.
- `pipeline/drama_pipeline/stage2_validate.py` — `checks.attachment_loss`
  adds the dropped-text anomaly kinds (`unmatched_anchor`,
  `nless_slice_unattached`, `attribution_hole`, reported under `dropped`) to
  `unresolved_mismatch_count`; allowance still `english.max_unresolved_mismatches`.
- `pipeline/drama_pipeline/stage7_emit.py` — speaker-event refs read
  `seg["greek"] or seg["lines"]`, so `speakers.overrides` fire in the emit.
- `pipeline/tests/{test_stage1_perseus_play_english,test_stage1_turn_english}.py`
  — Seven's packed antilabe span, attribution-hole gating, coverage by English
  speaker, the Helen override in the emit, the line-level pairing rule.
- `shared/lib/data.ts` — `EnglishTurn.speakerMismatch?: {english, greek}`.
- `shared/lib/speakers.ts` — `EnglishTurnBlock.speakerMismatch` carried from
  the turn.
- `shared/components/Reader.svelte` — `playEngTurns` marks `data-mismatch` on
  the lead-in of the disagreeing turn alone (chunk-level flag only as a
  fallback for pre-P2h data).
- `docs/play-line.md` — §English: the per-line rule, holes, per-turn flag,
  `covered_ids` is continuation coverage only.

## P3 bench — Way Euripides secondary (2026-09-08)

- `pipeline/drama_pipeline/bench_clean.py` — Euripides Loeb titles (including
  INTRODUCTION / missing title page / `SUPPLIANTS ©` / catalog stop), mixed-case
  OCR speakers (`cycLops`, `Lycus`), truncated parentheticals, mid-line `NAME ᾿ verse`.
- `pipeline/tests/test_bench_clean.py` — synthetic coverage for those Way cases.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `way` is A. S. Way,
  Loeb 1912.
- `docs/bench.md` — Euripides/Way table (heading, pages, pairing, coverage, residual OCR).

## P3 bench — Morshead Aeschylus secondary (2026-09-08)

- `pipeline/drama_pipeline/bench_clean.py` — `--layout verse-own-line` dispatches
  to the English-only verse cleaner.
- `pipeline/drama_pipeline/bench_clean_verse.py` (new) — Morshead DJVU: cut by
  title, drop running heads/page numbers/stage dirs, emit Lindsay-style own-line
  speakers.
- `pipeline/drama_pipeline/stage1_turn_english.py` — `format: verse-own-line`
  uses `_parse_lindsay_speeches` without `The Persons of the drama.`
- `pipeline/drama_pipeline/public_domain_translations.yaml` — `morshead` note
  names the 1881/1904 House of Atreus and 1908 Suppliant Maidens volumes.
- `pipeline/tests/test_bench_clean_verse.py` (new), `test_stage1_turn_english.py`
  — verse-own-line parse, Io/Aegisthus OCR, wrapped stage dirs, page-number crumbs.
- `docs/bench.md` — Aeschylus/Morshead table (heading, lines kept, pairing, coverage, residual OCR).
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — P2i: repair distance
  on the speaker's own printed lines (a one-liner beats a packed span; a speech
  the speaker owns less than half of is no target), every on-spine anchor
  attaches with a per-turn `speakerMismatch` instead of an `attribution_hole`,
  lettered anchors match the share of an antilabe line, continuation coverage
  per printed line, nless snaps name the tick line's speaker.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P2i: `speaker_at` prefers the
  LAST same-name share of a line; `_assign_speeches` refuses to park a residual on
  a segment whose speaker it is not (`residual_unassigned`).
- `pipeline/drama_pipeline/stage2_validate.py` — P2i: `attribution_hole` kept in
  `_ATTACHMENT_LOSS_KINDS` as a guard; the builder emits no holes.
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — P2j: a multi-span
  speech flags the piece it leaves in another character's speech, like a
  singleton attribution difference.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P2j: a segment with no
  primary speaker takes only nameless residuals; `residual_unassigned` named in
  the module contract.
- `pipeline/drama_pipeline/stage2_validate.py` — P2j: turn-text
  `checks.turn_text_residual_unassigned` gates `residual_unassigned` against
  `english.max_residual_unassigned` (default 0), failing closed.
- `pipeline/drama_pipeline/__main__.py` — P2j: `residual_unassigned=` on every
  turn-text stage-1 summary line.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P3.3: a residual English
  speech is never dropped. It walks forward to the nearest segment between the
  surrounding pairs whose lines carry its speaker (`residual_grouped`), else
  parks on the cursor with a per-turn `speakerMismatch` (`residual_flagged`);
  `residual_unassigned` is left for a speech with no segment at all and reads 0
  on all eleven comedies and every comedy bench slot.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P3.4: pairing runs over
  Greek speaker EVENTS (`_greek_event_slots`, one slot per antilabe share)
  instead of segments, so a packed segment takes one clean pair per share and
  its chunk is assembled from the pieces its shares won, in share order.
  `_pair_turns` loses its alternative-name argument (a slot is one speaker) and
  `_greek_segment_alt_names` gives way to `_segment_speaks`, which scopes the
  residual park window to the segment as before. `pairing_rate` is now per
  event, with the old figure kept as `segment_pairing_rate`; `turn_shifts`
  compares same-name ordinals (the drift detector) instead of names.
- `pipeline/drama_pipeline/stage2_validate.py` — P3.4: the turn-text pairing
  floor reads the event-level `pairing_rate`; `max_turn_shift_rate` is **0.10**
  against the new ordinal-based rate (the 0.05 this line first recorded was
  never what shipped — corrected in P3.5, which made 0.10 the one default in
  code, `docs/play-line.md` and here).
- `pipeline/drama_pipeline/__main__.py` — P3.4: `flagged=` and `seg_rate=` on
  every turn-text stage-1 summary line.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P3.5: `_pair_turns` needs a
  real name on both sides (an unnamed slot is no longer a gap-zip wildcard);
  `_assign_speeches` takes `greek_segments` and walks in two passes — a share
  that IS the speaker first (reaching back to the head of the cursor's own
  segment, so a crossed antilabe parks each share on itself), then the P3.3
  segment-scoped fallback; a segment's turns are emitted in share order where
  it agrees with English order and in English order where they cross; the
  flagged park's `speakerMismatch.greek` is the event at the park offset. The
  gated `turn_shift_rate` is documented as an ONSET rate (`new_drifts /
  paired`), the cumulative figure staying in the report.
- `pipeline/drama_pipeline/stage2_validate.py` — P3.5: `turn_shift_rate` is read
  with `is None` semantics (a reported `0.0` is a value, not a missing number)
  and the error quotes the gated onset count; the pairing floor becomes its own
  check, `checks.turn_text_pairing_floor`, and no longer switches off the
  unmatched-hole allowance.
- `pipeline/drama_pipeline/__main__.py` — P3.5: `shift_cum=`, `new_drifts=` and
  the gated `shift_rate=` on every turn-text stage-1 summary line (the old
  `turn_shifts=` label printed the cumulative count as if it were the gate).
- `manifests/thesmophoriazusae.yaml` — P3.5/P3.6: `english.min_pairing_rate:
  0.85`, declared at the default with the measured 0.855 (432/505 events) on
  record, so three more lost pairs fail loudly.
- `pipeline/drama_pipeline/stage1_turn_english.py` — P3.6 (Grok read of P3.5,
  `docs/reviews/2026-09-08-grok-p35.md`): the residual park window widens to
  the last share of the segment the next pair sits on, so a speech named for
  a later share of that packed line parks on its own slot (Birds 666); the
  module docstring says chunks emit in share order only where that agrees
  with the English.
- `manifests/*.yaml` (118 translation names) — P4 (John, mockup comment 2026-09-08): the turn-text suffix "— alignment approximate" is now "— by speech": these slots align exactly by speaker turn and do not track lines inside a speech; the old hedge said nothing.
- `shared/lib/speakers.ts` — P4 Lane A: `EnglishTurnBlock` carries `turnIndex`
  (the `turns[]` entry it came from, `-1` for the leading pre-turn
  continuation), so the reader's per-line row model can map the k-th English
  turn onto the k-th Greek speaker event even where `buildEnglishTurnBlocks`
  drops an empty unlabeled turn.
- `shared/components/Reader.svelte` — P4 Lane A: play-line renders per-line
  turn rows (`playRows` + the `.play-row-split` grid, `playTurnStack` factored
  out of `playEngTurns`), marks an ode (`playOde`, a chorus speech over six
  lines) on its `.segment`, and heads compare mode with `playColLabel`
  ("<short> · <year> · by line|by speech", from the registry name's own
  suffix) beside a Greek-column heading (`playSegHead`). Every other scheme's
  markup is untouched — the compare heading hangs off the chapter-title
  spacer's existing `{#if}` as an `{:else if}` so no other work's `.greek-col`
  gains even an anchor node.
- `shared/styles/global.css` — P4 Lane A: a `.reader-body.play-line` layout
  section (the shared [number][speaker][text] gutter with the Greek siglum and
  the English lead-in hanging at the same rem indent, baseline-aligned rows,
  the `.play-row-split` contents grid, the 34em ode measure, the centred
  1.12× Greek-only column, and unboxed 1.5:1:1 compare with block speaker
  labels), no rules or ornament between speeches, plus the phone-width
  restatements of those gutters.
- `shared/styles/global.css` — P4 Lane B: the blend skin. One value-swap token
  layer after the base `:root`/dark blocks (vellum ground, iron-gall ink, Cardo
  for read text and Alegreya Sans SC for operated chrome, the genre accents and
  the plate band, selected by `data-genre` on `<html>`), the twelve `--spk-*`
  slots re-cut as the scriptorium pigments (all ≥ 4.5:1 on their own ground),
  the four hardcoded chevron strokes retinted off the dead teal accent, and two
  new sections: `.rh` (the running head's own skin, unprefixed so the Lyceum
  chrome's more specific rules still win) and `.plate` (the opening plate).
- `shared/components/Plate.svelte` — P4 Lane B, NEW: the play's opening plate
  (band, argument with its DRAFT tag, persons in order of appearance in their
  reader slot colours, the scholia margin, "Start reading →"). Static, no
  hydration; every string comes from the registry or the book's own roster.
- `shared/components/RunningHead.svelte` — P4 Lane B: an optional `siteName`
  prop renders the site name ahead of AUTHOR · PLAY (the blend's `.head .site`);
  nothing else in the component changed.
- `shared/components/Reader.svelte` — P4 Lane A2 (fix round, Grok P4a findings
  1–2): `playRows` now pairs each English turn with the next UNUSED Greek
  speaker event whose canonical display matches the turn's `speaker` (falling
  back to the next unused event), because the pipeline emits a crossed pair's
  English in ENGLISH order and k-th ↔ k-th put a turn on the other speaker's
  line; and the ode measure is decided book-wide by `playOdeIds`, where a
  segment with no speaker events (a 40-line split tail) inherits the speaker
  set of the last segment that has them.
- `shared/styles/global.css` — P4 Lane A2 (fix round, Grok P4a findings 3–4):
  the compare Greek heading takes the line-number gutter as `padding-left` so
  it starts on the verse, and `.strophe-marker` is floated (out of flow, a
  full-width band above the line it labels) so the row's baseline is the first
  verse line's, never the marker's.
- `shared/styles/global.css` — P4 Lane B2: the running head a play page really
  wears. `.page-header` sits on a 2px `--accent` rule (genre-switched); the
  breadcrumb's first crumb (`.header-title .home-link`, and its `.simple-header`
  restatement) is restyled as the site wordmark — small, uppercase, .12em
  letterspacing, quiet ink until hover; the header-bar tools (Contents,
  Support, Search/Lexicon, Settings) take `font-variant-caps: small-caps` and
  .04em tracking so the fallback stack matches Alegreya Sans SC.
- `app/src/components/Breadcrumb.svelte` — P4 Lane B2: the Home crumb IS the
  site name (`SITE_NAME`, no aria-label — the visible text names the
  destination); AUTHOR · PLAY set in `--font-english` (Cardo) at 400 on a quiet
  rule that takes the accent on hover; separators `›` → `·`. Still plain links,
  still no `<select>`.
- `app/src/pages/[author]/index.astro` — P4 Lane B2: `data-genre` on `<html>`
  from the author's registry `genre`, so an author landing page carries its
  own accent (malachite on Aristophanes) exactly as ReaderShell.astro does.
- `shared/lib/speakers.ts` — P4 Lane C: `playSigla` derives ONE Greek gutter
  siglum per canonical speaker from the labels a play's own edition prints —
  a printed label of ≤4 characters as printed (Χο., ΞΑ.), otherwise the first
  two letters of the fullest label in Greek title case with a medial sigma
  (ΦΥΛΑΞ → Φυ., ΑΙΣΧΥΛΟΣ → Αισ.) and any trailing enumerator kept (ΗΜΙΧΟΡΙΟΝ
  Αʹ → Ημ. Αʹ); colliding speakers lengthen to three then four letters, and a
  pair still colliding falls back to what the edition itself prints.
- `shared/components/Reader.svelte` — P4 Lane C: the Greek speaker lead-in
  shows the play's siglum (book-wide `sigla` map) and carries the full printed
  label in `title`/`aria-label`, so a full-word label no longer wraps in the
  3.4rem gutter. Greek column only; the English column is untouched.
- `shared/components/Plate.svelte` — P4 Lane C: numbered roster families
  (Agamemnon's Elder 1 … Elder 12) collapse into one uncoloured cast entry,
  "Elders 1–12", at the first member's place.
- `shared/__tests__/speakers.test.ts`, `shared/__tests__/reader-play-line.test.ts`,
  `shared/__tests__/plate.test.ts` — P4 Lane C: the four siglum rules, the
  collision case, the gutter siglum + title in the Reader, and the collapsed
  Persons entry.
- `shared/styles/global.css` — P4 Lane E: `--on-accent` on every filled control
  that sits on `var(--accent)` (`.toc-toggle` open, `.copy-cite-btn`) in place
  of `#fff`, which read 3.47:1 (tragedy) / 2.32:1 (comedy) on the lifted dark
  accents; the wordmark (`.rh .rhsite`, `.header-title .home-link`,
  `.simple-header` copy) moves from `--text-light` to `--text-mid` (3.11:1 →
  6.28:1 light, 8.09:1 dark); `.simple-header` takes `.page-header`'s 2px
  `var(--accent)` rule; the print sheet drops the never-loaded hardcoded
  "EB Garamond" for `var(--font-english)` and the plate prints as the play's
  title page — `.plate-go` hidden, band and rubrication dropped to the sheet's
  own ink, a page break before the text.
- `shared/lib/citation.ts` — P4 Lane E: `lastPrintedRef(segments)`, the last
  printed `greek[].ref` of a book (in printed order, never re-sorted) — what
  the plate's "Cite as" extent ends on. A segment's `column` is the chunk's
  FIRST ref, so citing that ran every play short (Ag. 1–1672 of 1673).
- `shared/components/Reader.svelte` — P4 Lane E: `playRows`' `claim` pairs an
  English turn with the next UNUSED event of its canonical speaker, else the
  POSITIONAL (k-th) event — never "the next unused event of any name"; a
  `speakerMismatch` turn skips the name pass entirely and keeps its positional
  line. `playOde` reads the chorus off the printed Greek siglum (ΧΟ/ΗΜΙΧ,
  uppercased and accent-stripped) or an English name matching /chorus/i, so
  "Danaids", "Handmaidens" and the Frogs' own chorus get the ode measure.
  `settleDeepLink` re-checks a `?loc=`/`#` target ~900ms (after
  `document.fonts.ready`) and ~2500ms after the opening scroll and, if it is
  off screen, jumps to it instantly once — a smooth scroll fired during
  hydration was being cancelled and stranding the reader at scrollY 0.
  `prefers-reduced-motion` gets the instant scroll from the start.
- `app/src/components/Landing.astro` — P4 Lane E: `data-genre` on `<html>` from
  the author's registry `genre`, as ReaderShell.astro and the author page do.
- `shared/__tests__/reader-play-line.test.ts`, `shared/__tests__/plate.test.ts`
  — P4 Lane E: same-display event pairing, the mismatch turn's positional line,
  the siglum-driven ode test, the deep-link settle (corrects once when the
  target reports off screen, never when it landed), and the printed-extent
  citation. The two ode fixtures now carry a siglum that matches their speaker.
- `shared/components/Reader.svelte` — P4 Lane F (Grok P4CE findings 1, 2, 4):
  `settleDeepLink` is abandoned outright by the first `wheel`/`touchmove`/
  `keydown` after the opening scroll (a check that only fires when the target
  is OFF screen would otherwise snap back a reader who scrolled away), holds
  `suppressArmUntil` through the LAST check + 1500ms rather than 1500ms from
  the correction, and runs a single check under `prefers-reduced-motion`;
  `onDestroy` cancels it. `isChorusEvent` takes ΒΑΤΡΑΧ- (and Βα. where the
  translator's name is "Frogs") for a chorus, so Aristophanes' frog-song takes
  the ode measure while Persians' Atossa and Suppliants' Pelasgus — both also
  printed Βα. — keep the dialogue measure. `claim`'s positional fallback takes
  event k only when it is unused: a name match having consumed it, the turn
  stacks in the last mapped row instead of doubling up on a spoken line.
- `shared/lib/speakers.ts` — P4 Lane F (Grok P4CE finding 3): `abbreviateLabel`
  peels an enumerator the edition GLUED to the name (Phoenissae's ΑΓΓΕΛΟΣΒ,
  Helen's ΘΕΡΑΠΩΝΒ) and keeps it as the siglum's tail, so the two messengers
  no longer share Αγ. A bare final letter is peeled only for Β/Γ, which end no
  Greek word; a bare final Α (ΚΑΣΣΑΝΔΡΑ, ΗΛΕΚΤΡΑ — 37 corpus labels) needs its
  numeral mark.
- `shared/lib/citation.ts` — P4 Lane F (Grok P4CE finding 5): `lastPrintedRef`
  skips `lacuna` and `heading` lines and walks back to the previous segment
  when one holds nothing else; the chunk's own `column` is the fallback only
  for a segment with no Greek lines at all.
- `shared/__tests__/reader-play-line.test.ts`, `shared/__tests__/speakers.test.ts`,
  `shared/__tests__/plate.test.ts` — P4 Lane F: the wheel that abandons the
  settle, the frogs' ode against Atossa's speech, the used-event positional
  fallback, the glued enumerator against a feminine ending, and the trailing
  lacuna-only segment's citation.
- `scripts/check-links.mjs` — 2026-09-08: a bare `?loc=N` on a play-line work is accepted when the page carries the line id `L<N>-<n>` or a range id `L<a>-<b>-<n>` with a ≤ N ≤ b (the reader's resolvePlayLineRef lands there); `col-N` exists only where a segment begins at N. Was 2,490 false positives; now 0 broken.
- `scripts/emit-wing.mjs` (new) + `scripts/build-public.mjs` — P6 2026-09-08: the Drama wing's snapshot.v1 entry is emitted from the manifests (build/dist/wing.drama.json) and validated in build:public; handoff note docs/lyceum-handoff.md.
- `shared/lib/works.ts`, `shared/components/Plate.svelte`, `app/src/components/ReaderShell.astro`, `shared/styles/global.css`, `shared/__tests__/plate.test.ts` — REVIEW-CHECKLIST 12, 2026-09-10: the registry's optional `synopsis` prints under the argument on the plate (`.plate-syn`), with the same DRAFT-prefix tag rule.
- `shared/components/Reader.svelte` — Astra lane A fixes, 2026-09-10: the scroll-spy's hash write drops `?loc=` (F2); hash and resume scroll to the English cell when the Greek is hidden (F3); English copies append the citation and `tr. <registry name>` under the copy setting (F6, John's ruling); a later antilabe share cites its own line (F7); a repeated printed ref's later segment anchor is `col-<ref>--<k>` and resume keeps the occurrence (F8); `playFlow` stands down in English-only view (F1); the footnote popup is keyed by note (F5).
- `shared/components/FootnotePopup.svelte`, `shared/lib/data.ts` — Astra lane A F4, F12: footnote HTML passes `sanitizeHtml` on every path; Tab/Shift-Tab from the dialog container stay inside it.
- `shared/lib/search.ts`, `shared/components/Search.svelte` — Astra lane A F10: `search()` returns `{ results, failed }`; a partial failure names the skipped plays with a Retry button (notice wording DRAFT).
- `shared/components/CommandPalette.svelte`, `shared/components/BekkerJump.svelte`, `app/src/components/ClassicHome.astro` — Astra lane A F8, F9: play-line printed ranges are accepted; resume text hides the `--<k>` occurrence suffix (the link keeps it).
- `shared/styles/global.css` — Astra lane A F1, F13: the zero-height split-row English rule applies only in `.view-both`; the skin's `--text-light` is #6d675d (light) and #928a7e (dark) for 4.5:1 (John, 2026-09-10).
- `shared/styles/global.css` — 2026-09-10 (John): play-line English lead-ins are right-aligned in their gutter, so every name ends the same 0.6em before its speech; compare mode keeps its left-aligned block label.
- `shared/styles/global.css` — 2026-09-10 (John): a hanging Greek siglum takes `text-indent: 0` (it inherited the line's -1.4em hanging indent and sat over the line numbers); a play-line number wider than its gutter overhangs left (`justify-content: flex-end`), never into the siglum; Ῥ (U+1FEC) alone comes from a private "GDR Rho Dasia" face (Gentium Book Plus, Google's `text=Ῥ` subset, `unicode-range: U+1FEC`) because Cardo's Ῥ hangs its breathing 33px left of the letter.
- `shared/components/Reader.svelte` — 2026-09-10 (John, Rhesus 16): `splitAntilabe` drops a speaker cut with no letter before it, so an editor's bracket stays with the share it opens ("[ Χο. θάρσει.") instead of printing as a line of its own.
- `shared/components/Plate.svelte`, `app/src/components/ReaderShell.astro`, `shared/styles/global.css` — 2026-09-10 (John): the plate's Persons list prints each person's Greek siglum in parentheses ("Chorus (Χο.)"), from the same `playSigla` map the reader's gutter uses; a collapsed numbered family carries none.
- `shared/styles/global.css` — 2026-09-10 (John): the play-line English lead-in takes the prose's line-height (`inherit`, was 1.15, stacked names too), so its baseline is its speech's first baseline instead of 4.5px above it.
- `shared/lib/speakers.ts` (`sentenceTicks`, new), `shared/components/Reader.svelte` (`playTickRows`) — 2026-09-10 (John, "option 1 … for now"): a line-keyed translation's English is cut into rows only where a sentence or speech begins, each start placed on the Greek line interpolated between the translation's sparse line markers; a marker mid-sentence no longer breaks the sentence across a gap.
- `shared/lib/speakers.ts` (`sentenceTicks`) — 2026-09-11, Grok review of 1219ece: no sentence end after a lone initial or a title ("H. W.", "Mr.", "St."); sentences may open with a digit, an ellipsis, a stop-and-dash, or a Greek word; speech starts cut at the turn's own offset; a leading space keeps the first marker; interpolation never runs past the segment's last line or across markers that run backwards.
- `shared/components/Reader.svelte` (`playFlow`) — 2026-09-11 (John, Persians 94): the English of a row starts level with the row's first Greek LINE, not the strophe marker ("στρ. γ.") banded above it in the same cell.
- `pipeline/drama_pipeline/stage1_greek.py` (`_segment_play_lines`), `pipeline/drama_pipeline/stage1_turn_english.py` (`_resolve_covered`) — 2026-09-11 (John, Persians 83): a long speech past the 40-line cap is cut where the primary line-keyed English opens a speech block (`<sp>`), past 80 lines at the next line it marks, at 100 regardless, so a segment opens where its English does (173 segments opened before their English; 1 now); a `covered` declaration whose line no longer opens a segment is skipped.
- `pipeline/drama_pipeline/stage1_greek.py`, `stage1_turn_english.py` — 2026-09-11, Grok review of fa76916: speech starts parsed from the TEI (top-level `<sp>`, first `<l n>` not inside a quoted speech); printed refs compared whole ("85a" ≠ "85"); a joined or lacuna ref never opens a segment, even at the hard stop; a covered line must match exactly. (Rejected: "a cover may lie after its line" is intended, "translated with the speech below".)
- `pipeline/drama_pipeline/stage1_turn_english.py` (`_spread_long_speeches`, new) — 2026-09-11 (John, Morshead's Agamemnon parodos): a speech-aligned translation's English for a long Greek speech is spread over the segments that continue that speech (no speaker change, no chunk of their own), each taking the share proportional to its Greek lines, cut at the nearest sentence start; the lead-in stays with the first.
- `shared/components/Reader.svelte` (`playTickRows`) — 2026-09-11 (John, Agamemnon 140-159): a single-speech segment whose translation carries no line markers (speech-aligned: Morshead, Storr, Way, the 1912 comedies) is anchored at its first Greek line, and sentenceTicks places each sentence by proportion to the segment's end, instead of the whole share sitting at the top.
- `pipeline/drama_pipeline/stage1_turn_english.py` (`_spread_long_speeches`), `shared/components/Reader.svelte` (`playTickRows`) — 2026-09-11, Grok review of b294d29 + 5748b3f: chunks the spread leaves alone keep their order; a chunk with offset-keyed notes or markers is not cut; the reader counts a segment as one speech only when its single speaker event opens it (first line, offset 0). Rejected: continuations swallowing covered or antilabe segments (every speaker change carries an event, which stops the spread).
- `shared/lib/speakers.ts` (`englishFlow`) — 2026-09-11 (John, Birds 48-53): a row's English is pushed only when the English above runs more than a pixel past its Greek, and only then by the gap; one-line stichomythia no longer walks down the page 8px a turn.
- `scripts/verify-pages-artifact.mjs`, `scripts/verify-inventory-hashes.mjs`, `scripts/build-public.mjs`, `scripts/emit-wing.mjs`, `pipeline/drama_pipeline/{config,stage7_emit,preflight}.py` — Astra lane B, 2026-09-11: the Pages gate finds a reader at every registry route (single-book roots included); the inventory gate reads the referenced SHA256SUMS files (99 verified) and the build fails on !ok; the wing emits a valid empty snapshot for zero works; a public build drops `private: true` translation slots from data, HTML, registry, and partner manifests (the local build keeps them). F2 (partner reading_route) held for John: the fix loosened the partner schema.
- `scripts/emit-lyceum-manifest.mjs`, `schemas/lyceum-manifest.v1.json`, `scripts/check-links.mjs` — Astra lane B F2, 2026-09-11: owner ruled the shorter address; a single-book play-line work's partner `reading_route` is the bare work route, the partner schema's pattern accepts it, and check-links.mjs fails the build if any emitted reading_route has no page.
- `app/public/sw.js` — Astra lane A F11: an offline navigation that misses its exact URL retries the cache ignoring the query string before `offline.html`.
- `shared/lib/speakers.ts` (`markStageDirections`, `directionRows`, `sentenceTicks`), `shared/components/Reader.svelte`, `shared/lib/data.ts` (`OverlayPiece.directionsBefore`), `shared/styles/global.css` (`.stage-dir`), `pipeline/drama_pipeline/{stage1_turn_english,bench_clean_verse}.py` — 2026-09-12 (John): Arrowsmith's stage directions kept; one between speeches takes a row of its own with an empty Greek cell while his column is on screen, one inside a speech prints inline in italics; a sentence cut never falls inside one.
- `shared/lib/speakers.ts` (`sentenceTicks`), `shared/components/Reader.svelte` (`playTickRows`), `pipeline/drama_pipeline/stage1_perseus_play_english.py` (`parse_translation`), `pipeline/drama_pipeline/stage1_turn_english.py` (`_spread_long_speeches`, `_continuation_kind`, `_greek_breaks`) — 2026-09-12 (John; the Agamemnon alignment audit and the Codex review of 64e49a3): a Perseus paragraph with no line number of its own gets no tick; an interpolated English sentence start moves to the nearest Greek sentence start within 1.5 lines; a one-word sentence stays with the piece before it; the speech spread crosses a speaker mark only when the English is stacked (a bare "—" after a chorus at 2.5x the column median, a mark of the same voice above the median, neither when the English would fall below half the median over that segment), cuts at the English turns where the English marks each change of voice, and opens each segment at its first Greek sentence start within 1.5 lines.
- `shared/lib/speakers.ts` (`splitAtDirections`, new; `EnglishTurnBlock.directionsBefore`), `shared/components/Reader.svelte` (`playEnglishSource`, play-row split, `playTurnStack`), `shared/lib/data.ts` (`EnglishTurn.directionsBefore`, `OverlayPiece.turnDirections`), `pipeline/drama_pipeline/stage1_turn_english.py` — 2026-09-12, Codex review of 7a9a16d: a direction before a later speech of one Greek segment (Clouds 1:866, 14 in Clouds and Birds) rides that speech's turn, not the earlier speech's text; the reader cuts the play rows there and gives it a row of its own with an empty Greek cell; where the speech shares a row with the one before (or in compare), it prints inline above the speech.
- `shared/lib/works.ts` (`TranslationRef.form`), `shared/lib/speakers.ts` (`sentenceTicks` minSpan, `MIN_PIECE_LINES`), `shared/components/Reader.svelte` (`proseMeasure`, `playTickRows` minSpan), `shared/styles/global.css` (`.prose-measure`), `manifests/*.yaml` (`form: prose|verse` on every registry translation) — 2026-09-12, gap-layout lane (for John's eye): a prose translation's play-line column runs at 80% of its track side by side and in compare, and its pieces inside a speech start at least 5 Greek lines apart; verse and undeclared translations keep today's layout.
- `app/src/components/ClassicHome.astro` — with a single period on the shelf (the drama corpus), the home page shows its authors directly, with no collapsible period heading (John, 2026-09-12).
- `pipeline/drama_pipeline/kosmos_clean.py` (new), `pipeline/tests/test_kosmos_clean.py` (new), `pipeline/drama_pipeline/public_domain_translations.yaml` (`kosmos`) — 2026-09-12 (John's licence ruling): the Kosmos Society / CHS Sourcebook's 13 tragedies as a third, speech-aligned column; the pages number every fifth line but never a speech start, so the converter drops the numbers and writes verse-own-line turn-text; each slot declares its own `license` (CC 3.0, not public domain).
- `app/src/pages/attribution.astro` — 2026-09-12: DRAFT credit paragraph for the Kosmos Society Sourcebook, every translator and reviser named.
- `shared/__tests__/registry-golden.test.ts` — 2026-09-12: golden hash after the Kosmos third slot on 13 plays.
- `pipeline/drama_pipeline/johnston_clean.py` (new), `pipeline/tests/test_johnston_clean.py` (new), `pipeline/drama_pipeline/public_domain_translations.yaml` (`johnston`) — 2026-09-12 (owner's open-licence ruling): Ian Johnston's verse translations of 23 plays as a speech-aligned third or overlay column; his bracketed Greek numbers fall every tenth line, never at a speech start, so the converter drops them and writes verse-own-line turn-text; each slot declares its own `license` (his free-use terms, not public domain).
- `app/src/pages/attribution.astro` — 2026-09-12: DRAFT credit paragraph for Ian Johnston.
- `shared/__tests__/registry-golden.test.ts` — 2026-09-12: golden hash after Ian Johnston's column on 23 plays and Gilbert Murray's on 11.
- `pipeline/drama_pipeline/murray_clean.py` (new), `pipeline/tests/test_murray_clean.py` (new), `pipeline/drama_pipeline/johnston_clean.py` (`write_turn_text` split out for it), `pipeline/drama_pipeline/public_domain_translations.yaml` (`murray-verse` gains `sources:`) — 2026-09-12: Gilbert Murray's rhyming verse on 11 plays (10 from Project Gutenberg, Frogs from Wikisource) as a speech-aligned third or overlay column; each play cut at its own heading and notes.
- `app/src/pages/attribution.astro` — 2026-09-12: DRAFT credit paragraph for Gilbert Murray.
- `shared/lib/speakers.ts` (`spaceTicks`, new; `sentenceTicks` loses `minSpan`), `shared/components/Reader.svelte` (`playTickRows`) — 2026-09-14, Codex review of gap-layout (review-gap-layout-findings.md): minSpan thinning moved out of `sentenceTicks` into `spaceTicks`, called only after a segment's candidates are mapped to real Greek lines, so a candidate the segment doesn't print can no longer consume span or suppress a valid cut after it; a cut on a speech start or the translator's own printed line marker is now protected from thinning outright, whatever its span from the piece before it.
- `pipeline/drama_pipeline/stage1_turn_english.py` (`_join_parts`, `_shown`, `_collapse_ws_lines` new, `parse_play_speeches`/`parse_translation`/`run` gain `verse`) — 2026-09-14 (John, "show verse as verse!!!!"): a `form: verse` translation's speech keeps the source's own line breaks (`\n` per printed line, `\n\n` between paragraphs) instead of the space-joined paragraph a prose translation gets; a `form: prose` or undeclared translation is byte-identical to before. `shared/components/Reader.svelte` (`verseForm`, `renderVerseTurn`, new), `shared/styles/global.css` (`.verse-line` gains `text-indent: -1.5em`): the play-line turn-text column renders each of those lines as its own block with a hanging indent for a browser-wrapped line, reusing the Lucretius-work `.verse-line` rule; a prose piece renders exactly as before.
- `shared/components/Reader.svelte`, `shared/components/Search.svelte` — 2026-09-24: play-line readers skip the absent paratext file, and search CSV files use the drama name.
- `pipeline/drama_pipeline/text_fixes.py`, the two play-English builders, `kosmos_clean.py`, `pipeline/tests/`, and affected play manifests — 2026-09-24: checked final English text fixes per slot and Windows-1252 repair in Kosmos extraction.
- `shared/lib/search.ts` — 2026-09-24: exact Greek form is the default; lemma queries resolve typed forms through shared shards; English hits carry translation ids and use each translation's text.
- `shared/components/Search.svelte` — 2026-09-24: exact form appears first, lemma readings appear with results, and English hits show the translator and open its reader slot.
- `shared/components/Reader.svelte` — 2026-09-24: the copy button waits for layout and stays in view; verse line blocks carry text separators.
- `shared/components/Search.svelte` — 2026-09-24: lemma labels show the resolved printed headword.
- `shared/lib/search.ts` — 2026-09-24: lemma resolution carries printed headwords beside folded keys.
- `shared/lib/copy-button.ts` — 2026-09-24: clamp the copy button's visible box below the header and within the viewport.
- `pipeline/drama_pipeline/hickie_clean.py`, Hickie benches, tests, `manifests/acharnians.yaml`, `manifests/birds.yaml`, and `manifests/frogs.yaml` — 2026-09-24: moved page-foot note tails and credited quotations out of speeches, split roster-backed title-case cues, pinned two Acharnians turns, and removed three obsolete Hickie note text fixes.
- `pipeline/drama_pipeline/stage1_turn_english.py` (`_apply_english_overrides` gains an optional `label`), `pipeline/tests/test_stage1_turn_english.py`, `manifests/birds.yaml` — 2026-09-24 (John): an `english_overrides` entry's `display` retags only the canonical name; `label`, new, also retags the shown English cue, for Birds' First Messenger, whose 1912 primary prints plain "MESSENGER" and collides on the page with the unnumbered Messenger's own "Messenger" label.
- `shared/components/Reader.svelte` — 2026-09-24: follow a changed `#<line>` hash on an open play (hashchange listener).
- `pipeline/drama_pipeline/stage1_turn_english.py` (`run` now writes `third_footnotes.json` / `overlay_<id>_footnotes.json`), `pipeline/drama_pipeline/stage7_emit.py` (`_footnotes_overlay_candidates`, `_merge_footnotes`, new), `pipeline/drama_pipeline/__main__.py` (per-work scratch cleanup gains the overlay-footnotes glob), `pipeline/tests/test_stage7_footnotes.py` — 2026-09-24: Rogers's 1924 Loeb Aristophanes footnote calls (Ecclesiazusae/Thesmophoriazusae/Wealth's `third`, Lysistrata's `overlays: rogers`) resolved nowhere because `run` computed but never wrote that column's footnotes; footnotes.json now merges the primary's notes with any `third`/`overlays` column flagged `footnotes: true`, disjoint keys required (a shared key is a hard failure); a play with no such column emits byte-identical to before.
- `shared/lib/speakers.ts` — 2026-09-24 (John, option C): `markLineNumbers` / `lineNumberHtml` carry each real translator tick through the turn slicing as a private-use mark and turn it into an empty `.eng-lnum` anchor after the word's first letter.
- `shared/components/Reader.svelte` — 2026-09-24 (John, option C): play-line turn blocks are built from the marked text (`markedTurns`, `playTickRows`' `sliceBlocks`), and `playTurnStack` renders the anchors.
- `shared/styles/global.css` — 2026-09-24 (John, option C): `.eng-lnum` draws the translator's line number from `data-n` in the English number gutter (compare: the column's outer margin, not drawn in English-only compare where the page margin is too narrow for it; phone compare: none), in the Greek gutter's face, size, and ink.
- `shared/components/Reader.svelte` — 2026-09-25: show brief clipboard success or failure by the copy button; tab focus on a footnote marker stays on the marker, while activation opens and focuses its note.
- `shared/components/FootnotePopup.svelte` — 2026-09-25: take and restore focus only when a marker opens the note by click or keyboard.
- `shared/components/CommandPalette.svelte` — 2026-09-25: name plays and line numbers in the palette input and help text.
- `shared/styles/global.css` — 2026-09-25: style clipboard feedback like the copy button.
- `pipeline/drama_pipeline/stage1_turn_english.py` (`_is_way_source`, `_clean_way_ocr_litter`, `_collapse_way_dash_run`, new), `pipeline/tests/test_stage1_turn_english.py`, and 15 Euripides manifests (`bacchae`, `hippolytus`, `ion`, `iphigenia-at-aulis`, `rhesus`, `trojan-women`, `heraclidae`, `phoenician-women`, `heracles`, `orestes`, `suppliants-eur`, `electra-eur`, `medea`, `alcestis`, `cyclops`) — 2026-09-25 (way-cleanup sweep, `build/sweeps/way-cleanup-2026-09-25.tsv`; round 2, `build/sweeps/brief-way-cleanup-r2.md`): a narrow cleaner scoped to `bench/way/` sources collapses a glued em-dash-plus-hyphen; individual `text_fixes` for the S11-confirmed one-offs and Ion 732-734's footnote fragment (the ION/Creusa mislabel itself was tried via `english_overrides` and reverted -- it broke `turn_text_turn_shift_secondary`). Round 2: the blanket mid-sentence-stray-stop rule was removed after an independent 50-sample check found the stop was real on the page in 6 of about 30 -- replaced by 5 individual, page/genie-confirmed `text_fixes` (heraclidae 288 and 711, heracles 888, phoenician-women 1758, suppliants-eur 820) and every other stop left as the OCR has it; Ion 1229 and Cyclops 253's one-off fixes were redone from the page/underlying scan (each had wrongly dropped real words along with the litter); Electra 903's stray-quote fix was reverted (the underlying bilingual scan prints the quote mark on both this line and the one before it -- a real gnomic-maxim convention, not litter). Round 3 (`build/sweeps/brief-way-cleanup-r3.md`): the asterisk rule (guessed elision-or-bare-insertion from a word list) is removed -- a second check found it wrong on 3 of 4 sampled instances (an opening quote read as a bare insertion) -- and replaced with one `text_fixes` entry per asterisk (about 27, across `bacchae`, `iphigenia-at-aulis`, `phoenician-women`, `heracles`, `orestes`, `suppliants-eur`, `medea`, `iphigenia-in-tauris`), each checked against its own archive.org page image or genie's independent OCR of it: an elision apostrophe, an opening quote, a misread question mark (iphigenia-at-aulis 427), or nothing, including one phantom line dropped entirely (iphigenia-at-aulis 1130, bled in from a footnote). Heraclidae 748's round-2 fix was still wrong (Grok's second check): "won me" belongs on the next printed line, not the "upon me," line. Rogers (`format: loeb-ocr`) is untouched.
- `pipeline/drama_pipeline/stage1_turn_english.py` — 2026-09-25: bracketed cue line fixes keep their speaker matching and pins while marking the affected turn and chunk `cueAdded`; plain cues keep their prior output.
- `shared/components/Reader.svelte` — 2026-09-25: added turn-text cues reach the turn stack from chunk data and print as bracketed speaker lead-ins in each play-line view.
- `shared/styles/global.css` — 2026-09-25: editorial speaker lead-ins use the muted text colour in both themes, including when speaker colours are on.
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — 2026-09-25: a line a `line_fixes` entry seats is exempt from the speaker repair and the antilabe walk (Seven 996-1004, Smyth).
- `pipeline/drama_pipeline/stage1_turn_english.py` — 2026-09-25: `english.<slot>.cuts` names the words a spread continuation opens with; stale cuts raise (Peace 1167, Hickie).
- `pipeline/tests/test_stage1_perseus_play_english.py` — 2026-09-25: tests for the line-fixed seat exemption.
- `pipeline/tests/test_play_segments.py` — 2026-09-25: tests for a declared spread cut.
- `manifests/peace.yaml` — 2026-09-25: Hickie `cuts` entry at 1167.
- `shared/styles/global.css`, `shared/components/Reader.svelte`, `shared/lib/speakers.ts` — 2026-09-26 (John's ruling, phone name-above): the phone abbreviation machinery tried first (`measurePhoneAbbreviations`, `wideWords`/`abbrevMap`, `abbreviateLeadInWord`/`resolveLeadInAbbreviations`, `leadNamesInColumn`/`bookLeadInWordsForColumn`, the per-column scoping, and their tests) is removed in favour of giving the name room instead of shrinking it: on a phone the speaker's name is a block of its own above the speech (English-only and Both), in its speaker colour; the speech starts at the column's left edge in English-only (Both keeps the Greek's own indent, unchanged), and the translator's `.eng-lnum` moves out of the now-gone left gutter to a fixed 2rem margin at the text column's right edge, reserved on every paragraph rather than only where a number falls. `playEnglishGutterWidth`'s combined desktop floor and `leadNamesInBook` (which feeds it) are unchanged.
- `pipeline/drama_pipeline/text_fixes.py` (`strings`, `hits_in`, new) — 2026-09-26: a turn's own `display` (its printed cue) is now a `text_fixes` target too, exact-value matched rather than substring-counted (a truncated cue is a literal prefix of the correctly spelled one printed everywhere else, so substring counting would double-count); `text` fixes are unaffected. `pipeline/tests/test_text_fixes.py` gains coverage.
- `manifests/agamemnon.yaml` — 2026-09-26: Johnston `text_fixes` corrects the truncated cue `CLYTAEMNESTR` (line 1476 of `sources/bench/johnston/agamemnon.txt`) to `CLYTAEMNESTRA`; the pre-existing alias mapping it to the right speaker is unchanged.
- `shared/styles/global.css` — 2026-09-28 (John): English line numbers sit right of the text in single-translation play-line views on desktop and phone; desktop English loses its left number gutter, phone Both keeps its Greek text indent, and compare keeps its own layout.
- `shared/styles/global.css`, `shared/components/Reader.svelte` — 2026-09-28 (John's word-panel blank/jump report): `.reader-body.word-open`'s `margin-right` (681-1800px band) no longer animates. A long play's whole text sits in one DOM tree, so narrowing the reading column to clear the panel can shift a click deep in the play by thousands of document pixels; an animated width change re-wraps that text every frame of the transition instead of once, and `pinAcrossReflow` (unchanged) chasing a still-moving target could overshoot. An instant width change reflows once and pinAcrossReflow's existing correction lands in the same frame.
- `pipeline/drama_pipeline/stage1_turn_english.py` — 2026-09-29: comparison pieces keep each prefixed cue's stage-1 resolved speaker in `cueSpeakers`.
- `shared/lib/data.ts` — 2026-09-29: document the optional, cue-aligned `OverlayPiece.cueSpeakers` field.
- `shared/lib/speakers.ts` — 2026-09-29: prefer emitted comparison cue speakers over roster name matching, with the old fallback for older books.
- `shared/components/Reader.svelte` — 2026-09-29: pass comparison pieces' resolved cue speakers to both lead sizing and turn rendering.
- `shared/lib/speakers.ts` — 2026-09-29: `extractPrefixedEnglishTurns` uses `cueSpeakers` only when its count equals the cues found (else the old matching), and, as stage 1 does, takes no lone capital as a cue (Murray's lettered parts of the chorus stay inside the Chorus speech; John).
- `manifests/clouds.yaml`, `manifests/lysistrata.yaml` — 2026-09-29 (John; Opus identity check): Pasias/Amynias → First/Second Creditor; Coulon's bare ΓΥ. is the women's leader from 798 and an unnumbered Woman from 830; generic WOMAN cues take the Greek speaker of their lines.

## Greek edition data (2026-09-29)

`manifest.v1.json` now has an optional `greekEditions` list. The reference
`editions` array still has one entry. `edition.v1.json` describes each
`ed/<id>/edition.json` file. These fields add data without changing the
existing reference edition contract.
- `pipeline/drama_pipeline/config.py` — 2026-09-29: builds an edition-scoped manifest and reads `DRAMA_BUILD_DIR` for isolated scratch data.
- `pipeline/drama_pipeline/__main__.py` — 2026-09-29: accepts `--edition`, selects the TEI Greek reader, and assembles the edition output.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29: checks Greek edition declarations, pair ownership, allowlist entries (one id may carry several allowlist entries, one per source volume: Smyth's 1922 and 1926 Loeb volumes), and stray edition dirs.
- `pipeline/drama_pipeline/stage3_tokenize.py` — 2026-09-29: strips printed angle brackets from lexical keys so a fresh reference build still keys those words.
- `pipeline/drama_pipeline/stage6_search.py` — 2026-09-29: emits Greek-only edition search and skips the shared lemma map.
- `pipeline/drama_pipeline/stage7_emit.py` — 2026-09-29: keeps installed editions, checks their roster against the reference, skips the shared LSJ merge, and writes edition data.
- `schemas/manifest.v1.json` — 2026-09-29: declares optional `greekEditions` metadata.
- `scripts/emit-lyceum-manifest.mjs` — 2026-09-29: maps declared Greek editions into the Lyceum edition list.
- `shared/lib/works.ts` — 2026-09-29: exposes optional Greek editions and each translation's own edition.
- `shared/lib/data.ts` — 2026-09-29: routes edition books, columns, and analyses through the data-root override with separate caches.
- `shared/lib/search.ts` — 2026-09-29: routes Greek index loads through an edition base while English stays on the reference.
- `shared/components/Reader.svelte` — 2026-09-29: accepts edition state from a host, reports translation and view changes, and uses the play roster for speaker colours.
- `shared/components/WordPopup.svelte` — 2026-09-29: reads parses from the Greek edition on screen.
- `shared/components/ReaderHost.svelte` — 2026-09-29: loads the chosen edition and remounts the reader when its book changes.
- `shared/lib/edition-state.ts` — 2026-09-29: applies the edition load and change rules for paired views and deep links.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29: the edition concordance check accepts a range value ("112-113") where the reference prints one line under two numbers.
- `pipeline/drama_pipeline/stage7_emit.py` — 2026-09-29: writes each edition's `concordance.json` (new `concordance.py` matches edition lines to reference lines, joining adjacent lines where lyric colometry differs).
- `schemas/concordance.v1.json` — 2026-09-29: new schema for the edition concordance; a value is one ref or an "a-b" range.
- `pipeline/drama_pipeline/concordance.py` — 2026-09-29: a joined span may start at the last line of the ±50 window, as a single line can (bound was `high - m + 1`).
- `shared/lib/data.ts` — 2026-09-29: `fetchConcordance(work, ed)` (edition ref to TLG ref, cached through the data root).
- `shared/lib/edition-place.ts`, `shared/lib/edition-citation.ts` — 2026-09-29: new; keep the reader's place across an edition switch (concordance first, else same ref, else nearest lower; 2026-09-29 reordered: the same number is different text where numbering drifts) and build the edition-aware copy citation.
- `shared/lib/resume.ts` — 2026-09-29: saves the edition beside the cite and `resumeHref` adds `?ed=` when editions are on.
- `shared/components/CommandPalette.svelte` — 2026-09-29: resume links go through `resumeHref`.
- `shared/components/Reader.svelte` — 2026-09-29: copy citation names the editor and appends an `ed=` link in a non-reference edition; saves `reader-loc-ed-<work>`.
- `shared/components/ReaderHost.svelte` — 2026-09-29: remounts the reader on an edition change only, placing the reader through the concordance.
- `shared/components/ReaderHost.svelte`, `shared/lib/edition-place.ts` — 2026-09-29: `?ed=` stays beside a `?loc=` or hash in a non-TLG edition; an edition switch rewrites `?loc=` to the mapped ref; a concordance range tries each ref in order.
- `shared/lib/data.ts` (`readerHref`) — 2026-09-29: beside a `loc`, keeps `ed` unless it is `tlg` (a bare `loc` reads in TLG numbering); without one, omits `ed` when it is the pair's own (Codex re-check).
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: skips XML comments inside `<l>` (Hecuba 387 crashed and leaked the comment into the Greek) and applies an edition's `text_fixes` (find/replace, one hit, fail-closed).
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: the lacuna test ignores XML comments and processing instructions, so `<l><gap reason="lost"/><!-- note --></l>` stays a declared lacuna.
- `pipeline/drama_pipeline/stage3_tokenize.py` — 2026-09-29: strips U+02BD, an opening quote in Perseus's Greek (Phil. 858), as edge punctuation.
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: skips XML comments inside `<l>` (Hecuba 387 crashed and leaked the comment into the Greek); applies an edition's `text_fixes` (find/replace, one hit, fail-closed); an edition with no line-anchored pair reads one speaker's consecutive `<sp>` blocks as one speech (the TLG's shape; Storr's turn-text pairing needs it).
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: an edition's `text_fixes` entry needs a `ref` and touches only that line (`find` once on it; absent or repeated ref fails); comment pins that an unlabelled `<sp>` continues the speech before it.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29: a Greek edition needs exactly one allowlist entry listing its source, and that entry must match editor, year, and status whole.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-09-29: `storr-loeb` and `murray-oct` split by volume year (Storr 1912/1913; Murray 1902 Hecuba, 1913 the rest), like `smyth-loeb`.
- `shared/components/Reader.svelte`, `shared/lib/edition-picker.ts` — 2026-09-29: the Greek-only view shows a plain `<select>` over the play's registry editions (reference first), built after mount by the `editionPicker` action so flag-off HTML is unchanged; a pick raises `editionChange` with `ed`.
- `shared/components/ReaderHost.svelte`, `shared/lib/edition-state.ts` — 2026-09-29: the reader remounts once when its own `?view=`/`?trans=`/saved choice differs from the server-rendered defaults on the same edition (it read `initialView` only at mount, so a saved Greek view opened as Both); `changeEdition` takes a Greek-view `ed` pick before compare and treats only a different translation as a translation change (Greek to Both keeps an aligned `ed`).
- `shared/components/Search.svelte`, `shared/lib/search.ts` — 2026-09-29: `search(..., ed?)` reads a chosen edition's Greek indexes for a Greek-only query in the plays that hold it; hits carry `ed`, link with `ed=` and `view=greek` through `readerHref`, and read their book from that edition.
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: an ano teleia glued to the next Greek word gets a space, as the comma and semicolon do (Clouds 1379 "ἐκεῖνον·ὦ" could not be keyed); no other Perseus Greek file read here has one.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-09-29: `greek_editions` gains `hall-geldart-oct`, one entry per volume year (1906: Acharnians to Birds; 1907: Lysistrata to Wealth).
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29: the raised-dot spacing covers U+0387 (ano teleia) as well as U+00B7 (Codex review).
- `app/src/components/ReaderShell.astro` — 2026-09-29: with `PUBLIC_EDITIONS=1` and a non-reference default edition, the meta description and the hidden intro sentence name that edition's `short` (`shownGreek`) instead of `greekSource.short`; flag off is byte-identical.
- `shared/components/ReaderHost.svelte` — 2026-09-29: an edition switch loads the concordance(s) the place rule needs even when the new book prints the same ref (the concordance outranks the same number); a failed load falls back to same ref, then nearest lower.
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29 (P4): an `ocr-tei` source is checked against its own directory's SHA256SUMS; every printed margin number (`rend="margin-N"`, `margin-apart-N`) must agree with the counted `n` (equal; inside a lyric or turn-over line; within its page), and `colon-N` tokens stay out of the text.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29 (P4): an `ocr-tei` edition's source must lie under `sources/ocr/` and, when present, match its directory's SHA256SUMS.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-09-29 (P4): `jebb` Greek edition (Cambridge 1893) for OT's OCR'd TEI.
- `scripts/check-registry-agreement.mjs` — 2026-09-29 (P4): an edition whose encoding licence is `none` (OCR'd TEI) names its text licence in the registry.
- `pipeline/drama_pipeline/stage1_tei_greek.py` — 2026-09-29 (P4 review): a joined `part="F"`/`"M"` line's `margin-N` and `margin-apart-N` are recorded and checked against the part's own ref, like any other line's; `<l>` may carry several `margin-N` tokens (a turn-over line printing two numbers), each checked.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29 (P4 review): `validate(..., editions=)` / `--editions` / `DRAMA_EDITIONS=1` (a build of editions): a declared `ocr-tei` source that is absent fails, and with `--public` so does a declared edition whose emitted dir is missing; off, an absent OCR source stays allowed for local dev. `scripts/build-public.mjs` passes `--editions` to preflight when `DRAMA_EDITIONS=1`.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-09-29 (P4 Jebb): `jebb` Greek editions for OC (1889), Antigone (1891), Electra (1894), and Ajax (1896), one entry per year, as for OT (1893).
- `scripts/ocr/jebb_to_tei.py` — 2026-09-29 (P4 Jebb review): the report lists every skipped number no printed number, note, hand fix, or joint Storr/TLG omission backs (`gaps`), and a whole verse the path leaves unnumbered takes the next free integer or is reported in `unmet`, never lettered quietly. Five built plays: no `n` changes.
- `scripts/ocr/jebb_to_tei.py` — 2026-09-29 (P4 Jebb review 2): a supplement page the OCR also has is an error; a hand fix (`NUMBER_FIXES`, a supplement's `n`) no longer excuses the gaps beside it (30 lyric gaps newly reported over OT, OC, Philoctetes, Trachiniae; TEI unchanged); antilabe shares join across a page break only at a 0.95 match. Seven plays: no `n` or TEI changes.
- `pipeline/drama_pipeline/anchor_map.py` (new) — 2026-09-29 (P4 Jebb re-key): `build_anchor_map` (the concordance matcher, source Greek to target Greek, plus the offset two matched neighbours share for a short line), `joined_targets` (the target lines the concordance joined two source lines into), and `remap_anchor`.
- `pipeline/drama_pipeline/stage1_perseus_play_english.py` — 2026-09-29 (P4 Jebb re-key): `english.<slot>.anchor_map: <edition id>` (edition alignment only) re-keys each `<l n>` from that edition's Greek count to this spine's, by text; each anchor may sit up to 3 lines off its mapped line where the speaker in force there disagrees with its English speaker (least-cost seating in strict order, `_apply_anchor_map`; an anchor whose text-mapped line already has its English speaker is pinned there and leaves only when the order forces it; a `line_fixes` anchor holds its seat and bounds its neighbours); two anchors share a seat only where the concordance joined their source lines; the report gains an `anchor_map` block (`speaker_moves`, `order_moves`, `order_breaks`, `shared_seats`) and `anchor_map.json` is written to `stage1/`; an order break (no seat keeps the order) fails the build unless the edition's alignment declares it in `order_breaks: [<English anchor>]`, and a declared break that does not occur fails as stale. No `anchor_map`: no change.
- `pipeline/drama_pipeline/config.py` — 2026-09-29 (P4 Jebb re-key): `Manifest.for_edition` records `anchor_editions` (the view of each edition an `anchor_map` names) and refuses a map to itself or an undeclared edition.
- `pipeline/drama_pipeline/preflight.py` — 2026-09-29 (P4 Jebb re-key): an edition's `alignment.<pair>.anchor_map` must name another declared edition.
- `shared/lib/edition-citation.ts` — 2026-09-29: a copied citation names the edition by its short label without the year, then the year ("Hall & Geldart 1906", not "Hall and W. M. Geldart 1906").
- `scripts/check-links.mjs` — 2026-09-30: with editions on, a bare `?loc=N` (or `ed=tlg`) also passes when the work's TLG `book-*.json` prints ref N, since the reader reads a bare `loc` in TLG numbering; `?ed=<other>&loc=N` still needs the page's own id. Was 3 broken on `/sophocles/antigone/800`; now 0.
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-10-01 (P4 Paley pilot): `paley` Greek edition (Harper & Brothers, New York, 1878, vol. 1) for Medea's OCR'd TEI.
- `scripts/ocr/paley_to_tei.py` (new) — 2026-10-01 (P4 Paley pilot): Paley's Genie OCR to the §3.1 TEI; imports `jebb_to_tei`'s alignment, numbering, margin and character checks (lending `number_lines` its hand-fix tables and no commentary lemmas for the call), with its own page heads, row parser (five number forms, strophe marks at the row's end, numbered sons), number runs placed by count, and `write_tei` (copied for Paley's header).
- `pipeline/drama_pipeline/public_domain_translations.yaml` — 2026-10-01 (P4 Way pilot): `way-loeb` Greek edition (Loeb, Heinemann, first printed 1912; scan the 1946 printing) for Medea's OCR'd TEI.
- `shared/__tests__/setup.ts` — 2026-10-04: same-origin fetches (happy-dom's `http://localhost:3000`, where nothing listens) reject at once with a `TypeError` instead of reaching the network; the unmocked `/data/<work>/paratext.json`, `lsj-heads.json` and like fetches take the same rejection path as before, without ~170 ECONNREFUSED `AggregateError` blocks in the vitest output. A rejection, not a 404, because data.ts caches a 404's `[]`/`{}` (paratext, lemmata) but evicts a rejection. Tests that spy on or stub fetch are unaffected.

## CI repair (2026-10-04)

CI had failed on every run since the first push (2026-09-09). The fixes:

- `.github/workflows/ci.yml` — 2026-10-04: the preflight fixture step sets `DRAMA_PUBLIC_DOMAIN_ALLOWLIST` to the fixture allowlist, as `test_preflight.py` does; the fixture build's link check passes `--allow-no-partner-manifests`.
- `scripts/check-links.mjs` — 2026-10-04: `--allow-no-partner-manifests` skips the reading_route check when no `manifest.lyceum.json` was read (a fixture build has none); without it, none is still a failure.
- `scripts/__tests__/check-links.test.mjs` — 2026-10-04: CLI test of a dist with no partner manifests, with and without the flag.
- `shared/components/Reader.svelte` — 2026-10-04: `playFlow`'s parameter type declares the `plRows` the call site passes (svelte-check error since 91d022b).
- `shared/__tests__/editions.test.ts` — 2026-10-04: the book fixtures carry `book: 1`, which `BookData` requires.
- `shared/__tests__/reader-context-english.test.ts`, `reader-freeman-source-frame.test.ts`, `reader-translation-credit.test.ts` — 2026-10-04: CPR c366c21's fixture type fixes, ported (`workType: 'continuous'`, `kind` on the segment, `series: 'B'`).
- `shared/__tests__/word-popup.test.ts` — 2026-10-04: the mocked `lookupWord` result drops the top-level `lsj`, which it lost at 3c76b5b.
- `pipeline/tests/test_bench_clean_verse.py` — 2026-10-04: the two tests that read `build/arrowsmith/genie-*.html` skip when it is absent, as the Hickie and Rogers tests do.
- `.github/workflows/ci.yml` — 2026-10-05: the app job runs `scripts/__tests__` (`node --test`), which no gate ran before.
- `scripts/__tests__/sweeps-b.test.mjs` — 2026-10-05: `findFont` also searches `/usr/share/fonts` (CI is Ubuntu; it looked only in macOS folders) and the two tests that need a font skip when there is none (Codex review).
- `app/src/components/ClassicHome.astro`, `app/src/lib/drawings.ts`, `app/src/pages/drawings/[name].svg.ts` — 2026-10-13, redesign phase 3: the home page is the vase frieze (docs/redesign/DESIGN.md, Home page; sketch home-sketches-round3.html, version A): the four playwrights' figures on one ground line, names and play counts, Resume and Search in the header, resources under the frieze; the shelves, cards and Start-here strip are gone. The figures are served from docs/redesign/drawings/ as static SVGs drawn with `<use>`.
- `app/src/pages/[author]/index.astro`, `app/src/components/SiteHeader.astro`, `app/src/components/Figure.astro`, `app/src/lib/author-groups.ts` — 2026-10-13, redesign phase 3: author pages rebuilt to the round-4 sketch (tint ground, figure hero, plays without boxes, the Oresteia and the Oedipus plays grouped first, Titles only toggle, Find a play on Euripides); the breadcrumb, citation-conventions list and support card are gone. Home and author pages share the header and the figure.
- `app/src/components/Playbill.astro`, `app/src/components/ReaderShell.astro`, `shared/components/ReaderHost.svelte`, `app/src/lib/drawings.ts`, `app/src/components/Figure.astro` — 2026-10-13, redesign phase 4: the play opens on the playbill (play-opening-round2.html) instead of Plate.svelte, with the edition picker on or off; ReaderHost takes `plate={false}` so it draws no Plate of its own (default true, so the shared behaviour stands). Play drawings come from the image plan's `final_image`.
- `app/src/pages/attribution.astro` — 2026-10-13: a Drawings section lists every drawing the site serves with its SVG's own credit (the CC BY-SA ones need it; Codex review).
- `app/src/components/ReaderShell.astro`, `app/src/styles/reader-drama.css` — 2026-10-13, redesign phase 5 step 1: `data-author` on the play reader's <body>; warm paper under the text, the author's tint in the running head, no rule under the running head or the reader controls.
- `app/src/styles/reader-drama.css` — 2026-10-13, redesign phase 5 step 2: speaker names run into the first line of each speech in both columns (sans small caps in the speaker colour, "Chorus." in the English); no speaker gutter; comparison unchanged.
- `app/src/components/SpeakerBar.astro`, `app/src/components/ReaderShell.astro` — 2026-10-13, redesign phase 5 step 3: a bar under the reader controls names the speaker once his name has scrolled away and his speech fills the top of the screen (reads the names the reader prints; off in comparison).
- `shared/components/Reader.svelte` — 2026-10-13, redesign phase 5 step 3 (John: "Alternating bilingual."): a play-line work opens bilingual on a phone too (other works keep the English-only phone default), and on a phone every speech is cut by playTickRows into pieces of at least MIN_PIECE_LINES Greek lines at sentence starts, so Greek and English alternate; desktop unchanged.
- `shared/components/Reader.svelte` — 2026-10-13: the phone cut applies only to single-speech segments (`singleSpeech`); dialogue keeps playRows (Codex review).

## UI pass 2, direction B "The Vase" (2026-10-20; docs/redesign/HANDOFF-ui-pass2-build.md)

- `app/src/styles/vase.css` — new: B's tokens as one value-swap layer over global.css's (paper, ink, mid, clay, the clay for small text, speaker slot 4 off the ink), and the chrome every page shares (head, icons, foot, measure).
- `app/src/components/SiteHeader.astro`, `app/src/components/ThemeToggle.astro`, `app/src/components/SiteFoot.astro` — B's head (the site name, a magnifier and a half-filled disc; the author after the site name on play pages; the stacked name on phones) and foot (pass 1's links and report form kept, the credit to johnhboyer.com); the theme switch is the disc on every page. SiteFoot is new; the report form moved there from ClassicHome.
- `app/src/components/Figure.astro`, `app/src/lib/drawings.ts` — figures in B's colours (lines --fig-ink, body --fig-body), whole, shrinking to a narrow box's width rather than cropping; author pages may have their own figure (`<author>-author`, Aristophanes' Getty krater).
- `app/src/components/ClassicHome.astro` — the home page: A's frieze in B's colours, figures one height in columns sized to them, every title as a run under its name, no intro line.
- `app/src/pages/[author]/index.astro` — the author page: name left, figure right (its column sized to the figure; a wide figure stands over the name on phones), the plays in two columns, the Oresteia and Oedipus groups kept; "Titles only", "Find a play" and the flag-gated Greek editions list gone (the play pages list each play's Greek texts).
- `app/src/components/Playbill.astro`, `app/src/pages/[author]/[work]/index.astro` — the playbill is the play's own page at the bare play URL (scene, titles, production, argument, Resume, persons, translations, Greek texts, synopsis, credit); ReaderShell no longer draws it above line 1.
- `app/src/pages/read/[author]/[work]/index.astro`, `shared/lib/works.ts` — new route: a play reads at /read/<author>/<work> (workPath), the bare path being its page (John, 2026-10-20). The tests that pinned the bare reader path follow: `shared/__tests__/works.test.ts`, `editions.test.ts`, `resume.test.ts`, `search.test.ts`, `search-editions-off.test.ts`, `search-edition-links.test.ts` (which now reads the play as the last path segment), `lyceum-manifest.test.ts`, and `app/src/__tests__/lemma-instance.test.ts`.
- `app/src/pages/read/[author]/[work]/section-[n].astro` — the alias redirects through workPath instead of spelling /book/<n>.
- `scripts/emit-lyceum-manifest.mjs`, `schemas/lyceum-manifest.v1.json` — a play's partner `reading_route` is /read/<author>/<work>; the schema accepts it (docs/lyceum-handoff.md, "Changed 2026-10-20").
- `app/src/components/ReaderShell.astro` — the playbill and its roster, sigla and last-line computations go (the play page has them).
- `scripts/check-links.mjs`, `scripts/__tests__/check-links.test.mjs` — `readerWorkOf`: with editions on, a bare `?loc=` is checked against the work's TLG data, and the work now comes from read/<author>/<work>/ as well as <author>/<work>/.
- `app/src/components/ReaderHead.astro` — new: a play's running head (spec §7.1): the site name, the author and the play as links; the picker (Greek text and translation, compare inside it), the views, Aa (size, width, spacing, speaker colours, copying, print), search and dark or light; menus in the ink frame. It drives Reader.svelte through `reader:set` and follows `reader:state`; the Greek view's citation and Perseus credit print under it.
- `app/src/components/ReaderShell.astro` — a play renders ReaderHead in place of the reader header (other works keep it); the Aa settings are applied before the first paint; `--header-h` measures either head.
- `app/src/styles/reader-drama.css` — rewritten for B: the measure and the Aa tokens, one size and leading for both columns, the Greek numbers left and the English right in the small-text clay, small-caps speaker names in their colours, the controls strip unshown, the word panel's frame, print.
- `app/src/components/SpeakerBar.astro` — B's type; it sits under either head.
- `shared/components/Reader.svelte` — `reader:set` / `reader:state` window events so a head outside the island drives view, translation, compare, edition, speaker colours and copying; a `[data-reader-head]` element counts as the sticky header in its two measurements.
- `shared/components/WordPopup.svelte`, `shared/lib/parse-words.ts` (new), `shared/__tests__/parse-words.test.ts` (new), `shared/__tests__/word-popup.test.ts` — the word panel (spec §7.6): the parse in words ("aorist indicative active, third singular"), the count as "N places in the plays", and the first entry open under its parse after every completed lookup.
- `app/src/__tests__/header-chrome.test.ts`, `app/src/__tests__/intro-edition.test.ts` — the head's claims for ReaderHead; the intro sentence read from the reader at read/<author>/<work>/.
- `shared/components/Search.svelte`, `shared/lib/beta-chart.ts` (new) — the search in B (spec §8.1, step 1): the boxes at the left, one row of pickers and checks each at the right (Greek words, forms, accents, the Greek text with editions on; the LSJ headwords found; English words; Together; In, with author checks and a wrapping play chooser), the count and CSV, each play's hits as whole verse lines under its title; only what this engine answers (no Near, Shape, phrase index, or `?` wildcard). The Beta Code chart moved to the new How to search page; the help modal, the collapsible chapter cards, and the authorship filter went.
- `app/src/pages/search.astro`, `app/src/pages/search/how.astro` (new), `app/src/pages/support.astro`, `app/src/pages/attribution.astro`, `app/src/pages/authors.astro`, `app/src/pages/404.astro`, `app/src/pages/lemma/grc/index.astro`, `app/src/pages/lemma/grc/entry.astro` — B's head and foot (spec §9: "B's head, foot, and tokens, nothing more"); How to search explains the controls (DRAFT).
- `shared/components/Reader.svelte` — a play keeps its place across a view switch (the line at the top comes back to the same height, or the English cell that holds it; a phone's Both view is far taller than its English, so the scroll offset alone landed far away), and a `?loc=` landing in English-only view lands on the English cell of the line, as the hash path already did (`shownFor`, `lineAtTop`; the search's hits open with `?loc=`).
- `app/src/components/ReaderHead.astro`, `app/src/styles/vase.css`, `app/src/styles/reader-drama.css`, `app/src/pages/lemma/grc/index.astro`, `app/src/pages/lemma/grc/entry.astro`, `shared/components/Search.svelte` — the §10.4 checks: B's head resets the shared `.rh` skin's letter-spacing and keeps each Aa row on one line on the desktop; the jumped-to line's tint is 14% clay so its clay number stays AA; a word longer than its line breaks in the reader, the lexicon index, and an entry's head (Ecclesiazusae 1169-1175, the dish word, scrolled the page sideways); the search's Together row is no longer dimmed (the mock shows it at full strength; dimmed, it failed AA).
- `shared/components/Reader.svelte`, `shared/components/Search.svelte`, `app/src/components/ReaderHead.astro`, `app/src/components/Playbill.astro` — fixes to Codex's review of the branch (2026-10-21): a view switch keeps the English that was at the top (the English cell and how far down it, not the segment's top; on a phone the piece comes in whole, Greek first, where it fits; `shownFor` maps either column to the other); `reader:set` with the edition already shown applies its view (ReaderHost remounts only for a different edition); the search names a play's Greek text only from the edition the engine searched, and only beside Greek hits; its pickers are bounded by their row (320px); the texts menu spans the window under the head between 681 and 1023px; focus moves to what replaced the compare button; the play page's Greek text links always name their edition.
- `shared/components/Reader.svelte` — fixes to Codex's recheck (2026-10-21): the place a view switch keeps is what the head's edge cuts (in Both, the English paragraph where no Greek line is within a line of the edge); an English cell with no height of its own (desktop split rows) is measured by its paragraph, after playFlow's timeout; the place carries a Greek line's id, to find a row the switch rebuilt (splitAtDirections); the comparison's second column (`.overlay-col`) counts as English, and a cell the new view does not draw gives way to its row's Greek; a stage direction's row, which holds no Greek, is keyed by the next speech's first line, and a view that drops the direction brings that speech to the top (Codex's final check); the second speaker's half of a shared line, whose number sits on the first half, is keyed by that line, at its foot (Acharnians 395).

## Way's own Greek keeps the Both view (2026-10-20)

- `shared/components/Reader.svelte` — 2026-10-20: `hasEnglish` also counts any non-primary translation's pieces (`secondaries` through `piecesFor`). Way's own Greek (`ed/way-loeb`) carries Way under `ross` with `english` null, so choosing Way's Medea with editions on dropped the reader to the Greek view.
- `shared/__tests__/reader-secondary-only.test.ts` — 2026-10-20: new; a book whose English sits only in the secondary slot keeps Both and all three view buttons.

## UI pass 2 follow-ups (2026-10-21; docs/redesign/HANDOFF-ui-pass2-next.md)

- `shared/components/Reader.svelte`, `shared/lib/speakers.ts`, `shared/__tests__/speakers.test.ts` — handoff §2, items 1 and 2 (spec §7.4): on a phone only a translation keyed by line (`alignment: line`) is cut into pieces, at sentence starts its own markers place, never a piece under five Greek lines (`phonePieceCuts`, first and last pieces included, a marker no exception); in dialogue each speech is first bounded by its speaker events (`playRows`) and a row holding one speech's English is cut (`phoneRows`); a speech-keyed translation stays whole (no proportional or line-for-line ticks on a phone). The desktop is unchanged.
- `app/src/components/ReaderShell.astro`, `shared/components/Reader.svelte`, `shared/components/ReaderHost.svelte` — handoff §2, item 3: on a phone (680px or less) a play's text waits for the reader to mount (`data-phone-pending`, set before the first paint, cleared once `phoneLayout` has drawn the phone's rows, or after 8s), so the server's desktop rows no longer flash and regroup. ReaderHost leaves its wrapper unstyled when not pending: the server's `visibility: visible` showed the default edition's text through the shell's `data-ed-pending` hold (Ajax with Storr opened on Jebb's text for the load).
- `shared/components/Reader.svelte` — handoff §2, item 4: crossing 680px (a phone turned, a window narrowed) keeps the reader's place. The place is noted as the reader scrolls (`notePlace`, `placeAtTop`), since the page is laid out at the new width before any event fires, and brought back after the rows regroup (`regroup`, the restore `setView` used, now `returnTo`), moved by the head's change in height; an English place is noted by its words (`wordsAt`, `wordsTop`: characters into the segment's English), since the phone's pieces and the desktop's rows are other cells over the same text.
- `app/src/styles/reader-drama.css`, `shared/components/Reader.svelte`, `shared/__tests__/reader-play-line.test.ts` — handoff §4, item 8, no sideways scroll on a phone: the phone's one grid track is `minmax(0, 1fr)` (a lyric passage's min-content widened `1fr` past a 320px screen in Seven Against Thebes, Suppliant Women (Aeschylus), Eumenides, and Ecclesiazusae); in English-only view, which the layout check did not open and which scrolled sideways at 390 too, a long English speaker name wraps at its spaces on a phone, an English word longer than its line breaks (`overflow-wrap: anywhere`), and a footnote call's no-wrap word (`renderThird`'s `.fn-anchor`) holds only a compound's last part, so the rest breaks at its hyphens.
- `shared/components/Reader.svelte`, `shared/styles/global.css` — handoff §4, item 5: in English-only view a play's segment whose English sits in another segment's paragraph (`englishElsewhere`: the column's covered-by, or the same speaker's continuation), which could only say "Translated with the speech above ↑" with no Greek beside it, is left out (`data-english-in`, hidden in `.view-english`); `shownFor` sends a link to its lines to that paragraph. Both and Greek views are unchanged.
- `shared/components/Reader.svelte` — fixes to Codex's review of the follow-ups (2026-10-21): the 680px media query's listener is removed when the reader is destroyed (a reader ReaderHost replaced for another edition could restore its old place on a turn), the place is noted at most every 150ms while the reader scrolls rather than once scrolling stops, and a bare `#col-` hash to a segment English-only view leaves out lands on the paragraph that holds its English.
