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
English speech it came from. Each numbered piece attaches once. A Greek
speech between two anchors gets no copied text. When an English speech's
attached anchors span `[min_n, max_n]`, or a single attached anchor whose
Greek owner ends before the next English owner begins, every intervening
Greek segment whose printed integers all lie in that span and that has no
anchor of its own **and which the covering ENGLISH speech's own canonical
speaker also speaks** is marked `englishCoveredBy` with the segment id holding
the translator's block (for example `"1:1320"`) and keeps `english: null`.
Coverage never crosses speakers: another character's one-liner inside an
English block is a real hole, not a covered column, and must be declared in
`english.gaps` like any other. The reader shows "translated
above" and jumps to that speech instead of "no aligned passage". Stage 2
treats coverage as an allowance: a covered id stays in
`checks.alignment.unmatched_segments`, is listed in `covered_ids`, and is
allowed by reason. `covered_ids` is continuation coverage ONLY: an
attribution difference is an attached chunk, never a covered id. Lacunae and declared `english.gaps` ids
are not marked. `english.gaps` remains the residue that sits outside every
English span. The builder does not copy a piece onto intervening speeches
or extend a piece toward the next English `<sp>`. The stage-1 report
records `covered_by_count` beside `segments_with_chunk / segments_total`.

A Greek segment's speaker is resolved exactly as stage7 resolves it —
`_norm_siglum` plus `speakers.overrides` keyed by the event's printed ref
(Helen's `Θε.` is the Servant, Theonoe from 865, Theoclymenus from 1165) —
— but the unit of that decision is one PRINTED LINE, never the segment. A
segment is cut only at a line-start speaker event, so an antilabe (Seven
1005, where the Herald's label sits after an editorial bracket) packs two
speakers into one segment: `1:1004` is Ismene at 1004 and the Herald from
1005 to 1025. A line's speaker is the last event at or before its offset 0;
a mid-line event adds a second speaker to that same line, and a piece
anchored there belongs to whichever share the English `<sp>` names (Ismene
still owns the start of 1005). The segment's speaker SET says only that the
segment contains a speaker — it qualifies a repair candidate, and only for a
line that speaker actually speaks.

Lettered anchors matching `^\d+[a-z]+$` keep their text. They attach to an
exact printed ref such as `1270a` when the spine has one, then fall back to
the integer base within that same English speech. Any other anchor absent
from the spine may snap only onto another line of its own English speech,
never into a neighbouring speech. Line-owner attachment across different
Greek speakers applies only when one English `<sp>` has anchors in more
than one Greek segment. For a singleton mismatch, the builder uses the
nearest Greek speech within three lines in which that speaker actually
speaks a line, preferring the earlier speech on a tie (translator drift:
Ag. 1077 Chorus lands on Chorus 1078, no `speakerMismatch` flag); the
emitted tick is the nearest line of the target the speaker himself
speaks — earlier on a tie — never the English `n` of the neighbour the
piece came from. A claim is a `(segment, speaker)` pair, so one
character's repair no longer locks the speech against another's, and a
segment that itself prints the line is never claimed away from it.

If no such speech exists, the piece is an attribution difference between
the translator's base text and the TLG edition: it attaches to the Greek
speech that prints the line and the English TURN is marked
`speakerMismatch: {english, greek}` (canonical English speaker, the Greek
speaker of that printed line). Stage 7 carries it through on the turn; the
chunk-level copy is written only when EVERY turn of the chunk disagrees,
and the reader marks the lead-in of the disagreeing turn alone. The one
exception is a line owner that packs other characters and gives this
speaker no line of its own (Antigone's stichomythia against Seven
`1:1004`): filing her words in the Herald's column would be worse than
leaving them out, so the piece becomes an `attribution_hole` instead.

Every attribution difference is listed in
`build/stage1/english_report.json` as `attribution_differences:
[{greek_id, line, english_speaker, greek_speaker}]` with
`attribution_difference_count`; those segments carry an ordinary chunk and
pair like any other. Holes are listed as `attribution_holes:
[{greek_id, line, english_speaker, greek_speaker}]` with
`attribution_hole_count`, and each one also writes an
`attribution_hole` anomaly. Every snap and speech mismatch is written to
the same report (play, English line, Greek ref, both speakers).
`speech_mismatch_count` counts all such rows, while
`unresolved_mismatch_count` counts rows with no `attached_to` target.
Stage 2 gates the loss in `checks.attachment_loss`: it adds
`unresolved_mismatch_count` to the anomaly kinds that each mean one piece
of English reached no chunk — `unmatched_anchor`,
`nless_slice_unattached`, `attribution_hole` (reported per kind under
`dropped`) — and fails when the total exceeds
`english.max_unresolved_mismatches`, a per-work manifest allowance whose
default is `0`. It fails closed when `build/stage1/english_report.json` is
missing or belongs to another work — unattached English is translation the
reader never sees. The stage-1 summary line prints `unresolved=N
covered=N`.

The Greek spine owns the speech/40-line segment cuts. The builder emits at
most one English chunk per segment. A segment with no English is a hole:
stage2 accepts it only when it carries `englishCoveredBy`, when its id or
printed ref is declared in `english.gaps`, or when it is a lacuna-only
empty-text segment (`_play_line_lacuna_segment_ids`) or a repeated-ref
second copy / lettered twin (`_play_line_twin_segment_ids`). Stage 2
auto-allows a lettered twin only after reading the source TEI and finding
no nonempty exact `<l n>` for that ref. `english.gaps` is only for Greek
speeches whose line numbers have no covering `<l n>` in the TEI at all.
Any other unmatched id fails. stage7's id join leaves an undeclared hole's
`english` field null and, when stage1 marked the span, writes
`englishCoveredBy` (a string segment id) onto the emitted book segment.
The report records `segments_with_chunk / segments_total` as the coverage
ratio and `covered_by_count` as the continuation-coverage total.

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

For comedy `turn-text` sources, a printed `NAME.` label may stand alone — its
full stop must be followed by a space, a footnote marker (`NAME.[412]`) or the
end of the line, so a mid-prose abbreviation (`O.God!`) is not a speaker —
while `NAME text` without the period starts a speech only when `NAME` occurs in
the work's `speakers.english` aliases and is the whole capitalized name before
the first word with lowercase letters or before a single-letter capital
(`MYRRHINÉ I could not…` is Myrrhine, not "MYRRHINÉ I"; a name that begins
with one, `A HERALD`, keeps it). Blank source lines inside a speech remain
paragraph breaks. `english.<slot>.line_fixes` applies declared 1-based source
line replacements before parsing (the Storr scans' page signatures
`WOU. 4, F`, `VQL. I. R` are blanked there). Notes end only at `INDEX`,
`INTRODUCTION`, the next known comedy title, or the Gutenberg end marker.
Stage 1 stops on an English name outside the Greek roster, except for a
`format: loeb-ocr` bench slot, where an unaliased label is scanner junk: the
speech keeps its text but is given a never-matching canonical sentinel and a
blank printed label, so it never pairs and the reader shows it unattributed
(`speakers.unaliased_ocr_speakers` reports it).

The turn-text report carries two independent numbers.
`length_ratio_outliers` / `length_ratio_outlier_count` is the English/Greek
character-length dispersion (`speech_mismatches` is perseus-play's speaker
mismatch key and is not reused); stage 2 fails
`checks.turn_text_length_ratio` when `length_ratio_outlier_count / paired`
exceeds `english.max_mismatch_rate` (default `0.25`). `turn_shifts` /
`turn_shift_count` / `turn_shift_rate` counts pairs whose paired English
canonical speaker is not the Greek speaker; stage 2 fails
`checks.turn_text_turn_shift` above `english.max_turn_shift_rate` (default
`0.05`). Pairing only ever joins name-agreeing turns, so the shift rate reads
`0.000` today: it is the tripwire on that contract. Both checks fail closed
when the stage-1 report is missing or belongs to another work. English before
the first pair attaches to Greek segment 0 only when its canonical speaker
matches that segment; the report counts other head text as `head_unassigned`,
printed on the stage-1 summary line.

Preflight reads `pipeline/drama_pipeline/public_domain_translations.yaml` and
requires every translation id stage7 can emit (primary / secondary / third /
overlays / `column_sources` / `summary_overlay`) to occur in its positive
allowlist. A `denied:` pattern list then rejects any of those translations
whose id, name, translator, or source matches (O'Neill is denied even on an
allowlisted id). A missing or empty allowlist, or any unknown id, stops the
build.

## Printed-order ruling

Murray prints Ag. 1290 before 1284, so the reader keeps 1290 before 1284. `citation.transpositions` remains a required, bidirectional validator allowlist; it never asks the emitter to sort the text.
