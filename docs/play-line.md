# `play-line` — the drama citation scheme as built (P1, 2026-09-05)

Proven on Agamemnon (`manifests/agamemnon.yaml`, TLG 0085.005). Design facts: `docs/p1-probe.md`.

## Contract

- Registered in `pipeline/drama_pipeline/scheme.py` (`Scheme.play_line_scheme`, `play_line_kind`, `play_line_order_key`, `_normalize_play_lineref`) and `shared/lib/citation.ts` (same regex source, `[0-9]` not `\d`; parity test in `shared/__tests__/play-line.test.ts` + `pipeline/tests/test_scheme_play_line.py`).
- Bookless: `books: 1`, one synthetic column `"1"`. The printed lineref is the citation: `GreekLine.ref` (string, required) beside the dense ordinal `line`. Ref grammar: `N` | `Na` (letter suffix) | `N-M` (a lyric line printed for two numbers) | `post N` (Diggle's empty-bracket lacuna placeholder → `role: 'lacuna'`, not citable). `post1226` and `289/290` are normalized at parse time.
- Lines are user-facing; copy citation `Aesch. Ag. 1234` (registry `citation.copyAbbr`); URL `/aeschylus/agamemnon?loc=1234` (also `#1234`); a number inside a range resolves to the range line.
- Speakers: `<label type="speaker">` → per-segment `speakers[{line, offset, label}]` (antilabe = offset > 0). Strophe markers (`στρ. α.`, `ἀντ. β.`, `ἐπῳδ.`, `μεσῳδ.`, `ἐφυμν.`, `Str. 1.`, `Ant.`, `Ep.`) are NOT speakers: `GreekLine.label`, rendered by `Reader.svelte` as `.strophe-marker`.
- Segments: one per speech (each speaker label opens a segment), capped at 40 lines (`stage1_greek._segment_play_lines`). Agamemnon: 233 segments, 1,637 lines, 220 speaker events, 58 strophe markers, 0 lacunae.
- Reader: `.reader-body.play-line` (hanging indent, gutter ref every 5 lines and on every suffixed/range line); the speaker-turn gates are `speakerWork = stephanus || playLine`.
- Routes: the reader lives at `/<author>/<slug>` (bookless works render directly; `/book/1` is kept as an alias); `[cite].astro` emits stride shims every 50 lines (`app/src/lib/citation-routes.ts`), e.g. `/aeschylus/agamemnon/1250` → `?loc=1250`; `/…/1234` is 404 by design.

## Manifest keys (copy `manifests/agamemnon.yaml`)

`work.{id, title, author, language: grc, tlg_author, tlg_work, greek_edition, lexicon: true, no_english: true (until P2), expected_sourcedesc}` — the sourceDesc string is a FATAL gate; take it verbatim from `docs/p2-works.md`.
`citation.{scheme: play-line, title_labels: [{sha256_16, note}], lacunae: {"1": [...]}, transpositions: {"1": [...]}, fingerprint: {count, sha256}}` — all four bidirectionally gated: run stage1 once, copy the values it reports, run again to confirm.
`books: [{n: 1, start, end}]`; `sources.{tlg_dir_env, …}`; `registry:` block (`workType: verse`, `books: 1`, `bookLabels: ['1']`, `citation: {scheme: play-line, copyAbbr}`, `translations: []`, `blurb: "DRAFT — …"`), checked against the pipeline fields by `scripts/check-registry-agreement.mjs`.

## Export path

`build/export/tlg<author>/Diogenes-Resources/xml/tlg/tlg<author><work>.xml`. stage1 never invokes Diogenes when the file exists; if missing it prints the recipe (`docs/tlg-phi-export.md`) and fails. All four authors are exported already (never committed).

## Open for John

**Transposed lines.** Murray prints Ag. 1290 before 1284; the reader shows it in numeric order after 1289 (the Lucretius/DRN precedent: citation order). The probe recommended printed order instead. Decide before P2 builds 30 more plays with transpositions.
