# `play-line` — the drama citation scheme as built (P1, 2026-09-05)

Proven on Agamemnon (`manifests/agamemnon.yaml`, TLG 0085.005). Design facts: `docs/p1-probe.md`.

## Contract

- Registered in `pipeline/drama_pipeline/scheme.py` (`Scheme.play_line_scheme`, `play_line_kind`, `play_line_order_key`, `_normalize_play_lineref`) and `shared/lib/citation.ts` (same regex source, `[0-9]` not `\d`; parity test in `shared/__tests__/play-line.test.ts` + `pipeline/tests/test_scheme_play_line.py`).
- Bookless: `books: 1`, one synthetic column `"1"`. The printed lineref is the citation: `GreekLine.ref` (string, required) beside the dense ordinal `line`. Ref grammar: `N` | `Na` (letter suffix) | `N-M` (a lyric line printed for two numbers) | `post N` (Diggle's empty-bracket lacuna placeholder → `role: 'lacuna'`, not citable). `post1226` and `289/290` are normalized at parse time.
- Lines are user-facing; copy citation `Aesch. Ag. 1234` (registry `citation.copyAbbr`); URL `/aeschylus/agamemnon?loc=1234` (also `#1234`); a number inside a range resolves to the range line.
- Speakers: `<label type="speaker">` → per-segment `speakers[{line, offset, label, display}]` (antilabe = offset > 0). `label` keeps the edition's Greek siglum; `display` is the canonical English name from the required manifest `speakers.sigla` map, or null for the unattributed dash. Each book also carries `speakerRoster`, the non-null canonical displays in first-appearance order. Strophe markers (`στρ. α.`, `ἀντ. β.`, `ἐπῳδ.`, `μεσῳδ.`, `ἐφυμν.`, `Str. 1.`, `Ant.`, `Ep.`) are NOT speakers: `GreekLine.label`, rendered by `Reader.svelte` as `.strophe-marker`.
- Segments: one per speech (each speaker label opens a segment), capped at 40 lines (`stage1_greek._segment_play_lines`). Agamemnon: 233 segments, 1,637 lines, 220 speaker events, 58 strophe markers, 0 lacunae.
- Reader: `.reader-body.play-line` (hanging indent, gutter ref every 5 lines and on every suffixed/range line); the speaker-turn gates are `speakerWork = stephanus || playLine`.
- Routes: the reader lives at `/<author>/<slug>` only (bookless works render directly there; no `/book/1` route or alias is emitted); `[cite].astro` emits stride shims every 50 lines (`app/src/lib/citation-routes.ts`), e.g. `/aeschylus/agamemnon/1250` → `?loc=1250`; `/…/1234` is 404 by design.

## Manifest keys (copy `manifests/agamemnon.yaml`)

`work.{id, title, author, language: grc, tlg_author, tlg_work, greek_edition, lexicon: true, expected_sourcedesc}` — the sourceDesc string is a FATAL gate; take it verbatim from `docs/p2-works.md`. A Greek-only play must instead declare `work.no_english: true` and omit `english`.
`citation.{scheme: play-line, title_labels: [{sha256_16, note}], lacunae: {"1": [...]}, transpositions: {"1": [...]}, fingerprint: {count, sha256}}` — all four bidirectionally gated: run stage1 once, copy the values it reports, run again to confirm. Transpositions validate the export only: stage7 keeps document order and emits no play-line seam notes.
`speakers.sigla` is required and maps every observed Greek siglum to one canonical English display. Declare `"—": null`; any other unmapped siglum stops stage7 before it replaces prior dist output. Run `pipeline/.venv/bin/python pipeline/gen_speaker_rosters.py` to inspect observed sigla and proposed names, then add `--write` to replace only the manifest's `speakers:` block.
`books: [{n: 1, start, end}]`; `sources.{tlg_dir_env, …}`; `registry:` block (`workType: verse`, `books: 1`, `bookLabels: ['1']`, `citation: {scheme: play-line, copyAbbr}`, `translations: []`, `blurb: "DRAFT — …"`), checked against the pipeline fields by `scripts/check-registry-agreement.mjs`.

## Export path

`build/export/tlg<author>/Diogenes-Resources/xml/tlg/tlg<author><work>.xml`. stage1 never invokes Diogenes when the file exists; if missing it prints the recipe (`docs/tlg-phi-export.md`) and fails. All four authors are exported already (never committed).

## English

`english.primary.model: perseus-play` reads the vendored Perseus translation
TEI. Under `anchor_model: sp-line` the builder parses each `<sp>` into
speeches, then into slices. A speakerless `<sp>`, or one that contains
`<milestone unit="para"/>`, is split at every para milestone and at a
leading em-dash (the packed elders at Ag. 1348–1371 become twelve slices).
Each slice attaches to the Greek segment that owns the printed `<l n>`
(line-owner attachment: plain `1234`, suffix `47a`, range `106-107`,
`post 146`), even when the English speaker differs from the Greek speaker.
When one English `<sp>` has `<l n>` anchors in more than one Greek segment,
the builder splits it at those line numbers and emits one chunk per Greek
segment, each carrying the turn `{offset:0, speaker, display}` of the
English speech it came from. A Greek segment whose lines sit between two
of those anchors, with no `<l n>` of its own, receives the nearest
preceding numbered piece (Smyth numbers lyric every fifth line). An
anchor absent from the spine snaps only onto another line of the same
English speech, never into a neighbouring speech. A `<l n>` that sits
inside a different speaker's Greek speech still attaches to that line's
owner (Cassandra/Chorus Ag. 1077); the mismatch is reported, not
redirected. Every snap and
speech-mismatch is written to `build/stage1/english_report.json` (play,
English line, Greek ref, both speakers).

The Greek spine owns the speech/40-line segment cuts. The builder emits at
most one English chunk per segment. A segment with no English is a hole:
stage2 accepts it only when its id or printed ref is declared in
`english.gaps`, or when it is a lacuna-only empty-text segment
(`_play_line_lacuna_segment_ids`) or a repeated-ref second copy / lettered
twin (`_play_line_twin_segment_ids`). `english.gaps` is only for Greek
speeches whose line numbers have no covering `<l n>` in the TEI at all.
Any other unmatched id fails. stage7's id join leaves an undeclared hole's
`english` field null. The report records
`segments_with_chunk / segments_total` as the coverage ratio.

`speakers.english` maps each Perseus `<speaker>` string as printed onto the
canonical roster display (`"(A Second Elder)"` → `Elder 2`). Emitted English
turns carry `speaker` = canonical display (the colour key) and `display` =
the printed English label. An unmapped English speaker is a hard error in
stage7's roster gate.

Smyth's Loeb `<note resp="Smyth">` nodes become inline `[^label]` markers and
an emitted `footnotes.json` map. Labels use `{seqInPlay}.{sanitised raw}` so
repeated printed note numbers stay unique and hyphens become underscores
(`69-71` → `1.69_71`). `english.primary.footnotes: true` is copied onto the
emitted v1 `manifest.translations[]` entry. `<del>`, `<stage>`, and `<gap>`
text is dropped; tails are kept. Display-only `<l n="0">` lines are dropped.

For comedy `turn-text` sources, a printed `NAME.` label may stand alone, while
`NAME text` without the period starts a speech only when `NAME` occurs in the
work's `speakers.english` aliases. Blank source lines inside a speech remain
paragraph breaks. `english.primary.line_fixes` applies declared 1-based source
line replacements before parsing. Stage 1 stops on an English name outside the
Greek roster and reports paired speech-length ratio outliers; English before
the first pair attaches to Greek segment 0.

Preflight reads `pipeline/drama_pipeline/public_domain_translations.yaml` and
requires every translation id stage7 can emit (primary / secondary / third /
overlays / `column_sources` / `summary_overlay`) to occur in its positive
allowlist. A `denied:` pattern list then rejects any of those translations
whose id, name, translator, or source matches (O'Neill is denied even on an
allowlisted id). A missing or empty allowlist, or any unknown id, stops the
build.

## Printed-order ruling

Murray prints Ag. 1290 before 1284, so the reader keeps 1290 before 1284. `citation.transpositions` remains a required, bidirectional validator allowlist; it never asks the emitter to sort the text.
