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
