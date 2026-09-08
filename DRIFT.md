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
