# P2c report — English line-owner attachment (2026-09-07)

Pytest: `700 passed, 23 skipped in 1.08s`.

with-English **before** = speeches − the manifest's old `english.gaps` count (88 across 27 plays). with-English **after** = English chunks emitted. Unmatched lacuna-only and twin segments are not declared gaps, so after can be below speeches − declared.

All 33 tragedies build green. Declared gaps: **87**. The <15 target is not met: remaining holes have no usable covering `<l n>` in the Perseus TEI (lyric numbering every fifth line, `<del>`/`<gap>`-only lines, or a neighbour left empty after line-owner moved the one existing n).

| id | speeches | with-English before | with-English after | gaps declared |
|---|---:|---:|---:|---|
| persians | 192 | 190 | 190 | 1:1019, 1:1077 — no covering `<l n>` |
| seven-against-thebes | 181 | 171 | 174 | 1:367, 1:978, 1:979, 1:993, 1:992 — no covering `<l n>` |
| suppliants-aesch | 193 | 187 | 190 | 1:299, 1:314, 1:316 — no covering `<l n>` |
| prometheus-bound | 205 | 203 | 201 | 1:246, 1:247, 1:377, 1:387 — no covering `<l n>` |
| agamemnon | 233 | 233 | 231 | 1:1078, 1:1672 — no covering `<l n>` (Chorus 1077 is owned by Cassandra 1076) |
| libation-bearers | 205 | 202 | 202 | 1:169, 1:871, 1:872 — no covering `<l n>` |
| eumenides | 187 | 182 | 182 | 1:147, 1:148, 1:153, 1:154, 1:367 — no covering `<l n>` |
| ajax | 298 | 298 | 298 | — |
| antigone | 281 | 280 | 279 | 1:723, 1:1326 — no covering `<l n>` |
| trachiniae | 249 | 243 | 241 | 1:876, 1:877, 1:879, 1:881, 1:889, 1:892, 1:981, 1:1018 — no covering `<l n>` |
| oedipus-tyrannus | 429 | 427 | 426 | 1:624, 1:679, 1:1149 — no covering `<l n>` |
| electra-soph | 382 | 379 | 379 | 1:856, 1:987, 1:1428 — no covering `<l n>` |
| philoctetes | 363 | 362 | 361 | 1:442, 1:1044 — no covering `<l n>` |
| oedipus-coloneus | 451 | 447 | 445 | 1:179, 1:182, 1:194, 1:197, 1:533 — no covering `<l n>`; 1:183 — TEI n=183 is `<gap reason="lost"/>` only |
| alcestis | 295 | 294 | 294 | 1:368 — no covering `<l n>` |
| medea | 241 | 240 | 240 | — (1:1270a is a lettered twin, auto-allowed) |
| heraclidae | 206 | 206 | 205 | — (lacuna auto-allowed) |
| hippolytus | 289 | 286 | 287 | 1:572, 1:1387 — no covering `<l n>` |
| andromache | 202 | 200 | 200 | 1:528, 1:1271 — no covering `<l n>` |
| hecuba | 258 | 258 | 256 | 1:708, 1:1042 — no covering `<l n>` |
| suppliants-eur | 249 | 246 | 244 | 1:41, 1:632, 1:1158, 1:1162 — no covering `<l n>` |
| electra-eur | 361 | 357 | 356 | 1:652, 1:966 — no covering `<l n>`; 1:1100 — TEI n=1100 is entirely `<del>` |
| heracles | 269 | 268 | 264 | 1:899, 1:1058, 1:1061, 1:1064 — no covering `<l n>` |
| trojan-women | 207 | 205 | 205 | 1:592, 1:594 — no covering `<l n>` |
| iphigenia-in-tauris | 383 | 381 | 381 | 1:1188, 1:1474 — no covering `<l n>` |
| ion | 512 | 505 | 506 | 1:223, 1:224, 1:232, 1:721, 1:766, 1:783 — no covering `<l n>` |
| helen | 481 | 475 | 477 | 1:563, 1:657 — no covering `<l n>` |
| phoenician-women | 374 | 373 | 372 | 1:133 — no covering `<l n>`; 1:142 — TEI n=142 is entirely `<del>` |
| orestes | 469 | 469 | 467 | 1:144, 1:157 — no covering `<l n>` |
| bacchae | 305 | 302 | 300 | 1:591, 1:934 — no covering `<l n>`; 1:843a — lettered twin, TEI has no 843 |
| iphigenia-at-aulis | 374 | 373 | 373 | 1:1251 — no covering `<l n>` |
| rhesus | 203 | 197 | 202 | 1:946 — no covering `<l n>` |
| cyclops | 226 | 226 | 225 | — (lacuna auto-allowed) |

**Total declared: 87.** Twins auto-allowed (not declared): Septem `1:803.2`/`1:810.2`, Medea `1:1270a`, Bacchae `1:843b`.

## Rule as implemented

- `_SpeechIndex.segment_for_line` — the Greek segment that owns a printed integer.
- `parse_translation` first pass — attach every on-spine `<l n>` to that owner, even when the English speaker differs; each split chunk gets turn `{offset:0, speaker, display}` (`turn_key` is per speech per segment).
- Span-fill in `parse_translation` — a multi-n English `<sp>` covers `[min_n, max_n]` (last piece may extend up to 6 lines toward the next English n); an empty Greek segment in that range gets the nearest preceding numbered piece.
- `_resolve_slice_anchor` — anchors absent from the spine still snap only onto another line of the same English speech (packed elders at Ag. 1348–1371).
- `_play_line_twin_segment_ids` — repeated-ref second copies (`1:803.2`) and non-preferred lettered twins (`843b`, `1270a`).
- `_play_line_lacuna_segment_ids` — every line `role == lacuna` **and** empty text; mixed or text-bearing lacunae still fail `validate()`.

## Assumptions

- Cassandra/Chorus Ag. 1077 is on-spine: Chorus English attaches to Cassandra's segment (line owner). The old nearest-speaker redirect was the 88-gap bug. The test still exists and passes under this rule.
- Packed-elder para/em-dash splitting is unchanged.
- `<del>` / `<gap>` / `<stage>` text is not covering English.
- `english.gaps` is only for Greek speeches with no usable covering `<l n>`.
- Comedy manifests, `stage1_turn_english.py`, stage7, preflight, `shared/`, and `app/` were not edited for this task.
