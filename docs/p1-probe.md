# P1 export probe — what the Diogenes `-y` export of the 44 plays looks like

Run 2026-09-05 (Diogenes 4.7.2, native `-y`, one invocation per author into
`build/export/tlg<author>/Diogenes-Resources/xml/tlg/`). Everything below is
measured on the real exports, not assumed. The `play-line` scheme and the
`_parse_play` walker are designed against these facts.

## Work numbers and editions (from each file's `<sourceDesc>`)

| Author | Works | Edition (verbatim `sourceDesc` tail) |
|---|---|---|
| TLG0085 Aeschylus | 001 Supplices, 002 Persae, 003 Prometheus vinctus, 004 Septem, 005 Agamemnon, 006 Choephoroe, 007 Eumenides | `"Aeschyli tragoediae, 2nd edn.", Ed. Murray, G. Oxford: Clarendon Press, 1955, Repr. 1960.` |
| TLG0011 Sophocles | 001 Trachiniae, 002 Antigone (vol. 1, 1955), 003 Ajax, 004 OT, 005 Electra (vol. 2, 1958), 006 Philoctetes, 007 OC (vol. 3, 1960) | `"Sophocle, vol. N", Ed. Dain, A., Mazon, P. Paris: Les Belles Lettres, …, Repr. … (1st edn. rev.).` — volume/year differ per play |
| TLG0006 Euripides | 034 Cyclops … 040 Hecuba (vol. 1, 1984); 041 Supplices … 046 Ion (vol. 2, 1981); 047 Helena … 052 Rhesus (vol. 3, 1994) | `"Euripidis fabulae, vol. N", Ed. Diggle, J. Oxford: Clarendon Press, YEAR.` |
| TLG0019 Aristophanes | 001 Ach., 002 Eq. (Coulon vol. 1, 1923); 003 Nubes (**Dover 1968**); 004 Vespae (**MacDowell 1971**); 005 Pax (Coulon vol. 2, 1924); 006 Aves, 007 Lys. (vol. 3, 1928); 008 Thesm., 009 Ranae (vol. 4, 1928); 010 Eccl. (**Ussher 1973**); 011 Plutus (vol. 5, 1930) | per play |

Every manifest pins its play's exact `sourceDesc` string as `expected_sourcedesc` (FATAL gate, DRN precedent). Euripides 001–033 and every author's trailing `Fragmenta`/`Epigrammata` works are exported too and are ignored.

## Document shape

- **No wrapping div.** `<body>` holds a flat sequence of `<l n="…">` elements. The first is `<l n="t">` carrying `<label type="head">` with the play's title in caps (`ΑΓΑΜΕΜΝΩΝ`) — a title-drop, hash-declared like DRN's `title_labels`.
- **`<l n>` grammar, corpus-wide** (58,966 lines): `int` 58,207 · `int-int` range 447 (a lyric line the edition prints as one line for two numbers, e.g. Ag. `106-107`, `131-134`) · `int[a-z]` 261 (Helena 30, Phoenissae 34, Orestes 66, Vespae 36, Eccl. 30 — editorial insertions/renumbering) · other 51: Diggle's **`post N`** (once `post1226`, no space — normalize) = an empty-bracket lacuna placeholder line (`&lt;<label>Οδ.</label> &gt;`), and Ecclesiazusae **`289/290`, `300/301`** (treat as a range).
- **Non-monotonic order** in 30 of 44 plays (0–7 places each; e.g. Ag. prints 1290 before 1284): the editor's transposition, numbers kept. Recommendation: **display document (edition) order, never re-sort**; `citation.transpositions` declares each place as a validator allowlist (bidirectional gate as DRN), and a jump to a transposed number lands on its printed position. No seam notes needed.
- **No `* * *` lacuna marks and no `<gap>`**; loss is shown by `post N` lines and by `[…]`/`†…†`/`⟨…⟩` sigla inside the text (kept verbatim; `speakers.ts locateToken` already tolerates bracketed words).
- **`<lb/>`** (36–86 per play): the edition's printed wrap inside one numbered line (long lyric lines). Rejoin as one line; do not emit a second line. **`<pb/>`** page breaks: strip. **`<space quantity="…"/>`**: typographic gap after a speaker label or for antilabe indentation: strip to a single space. `<hi rend="small|large|letter-spacing">`: strip tags, keep text.

## Speakers

- `<label type="speaker">` is the only label element besides the title `head`. It carries BOTH true speakers and strophe markers; the walker must classify:
  - **Speaker sigla**: `Χο.`, `Κλ.`, `ΚΡ.`, `ΔΙ.` (per-edition case), the full-caps name on first appearance (`ΦΥΛΑΞ`, `ΚΛΥΤΑΙΜΗΣΤΡΑ`), the unattributed dash `—`, semichorus `Χο.α`/`Χο.β`, numbered chorus members `1.`…`10.` (Ag. 1348–71), `ΠΑ. Αʹ` (Frogs). A roster maps every siglum to a canonical display (plato's `sigla` map + `gen_speaker_rosters.py`); full-caps first appearances map to the same character as the siglum.
  - **Strophe markers** (Murray `[στρ. α.`, `[ἀντ. β.`, `[ἐπῳδ.`, `[μεσῳδ.`, `[ἐφυμν. γ.`; Dain/Coulon `Str. 1.`, `Ant. 2.`, `Ep.`, `Epode.`, `Str. βʹ.`; bare `στρ.`/`ἀντ.`; Diggle prints none): rend `indent(59.5–75)` = right margin, placed AFTER the line's text. Classify by regex `^\[?(στρ|ἀντ|ἐπῳδ|μεσῳδ|ἐφυμν|Str|Ant|Ep|Epode)\b` → NOT a speaker: emit as `GreekLine.label` (a normalized form such as `str. α` / `ant. 2` / `ep.`) and strip from the text. One malformed case: `[ἀντ. α. Αν.` (a strophe mark glued to a speaker `Αν.`) — split.
- **Position**: labels sit at line start in the overwhelming majority; **antilabe is real and mid-line**: Cyclops 153 `Οδ. ἰδού. Σι. παπαιάξ…`, and Aristophanes has 50–120 multi-speaker lines per play (Frogs 5: `ΞΑ. … ⏎ ΔΙ. …` with a newline + `<space>` before the second speaker). `_line_with_speakers` already yields `{offset}` per label; the offset must be computed AFTER the `<space>`/`<lb/>`/newline normalization so it indexes the emitted text.
- Speaker counts per play: 185–733 labels; dashes up to 33 (Eumenides).

## Consequences for `play-line` (freeze)

- Bookless, one column `"1"`, segments cut per scene-sized block (e.g. every N lines or at each speech boundary ≥ the chunking the reader's virtual scroll needs); `lines_user_facing: true`; ref token grammar (byte-identical in `scheme.py` and `citation.ts`): `^[0-9]+$` | `^[0-9]+[a-z]$` | `^[0-9]+-[0-9]+$` | `^post [0-9]+$`. Order key: leading integer; `post N` sorts as `(N, 1)`; suffix letters after the plain number; ranges by their start. `289/290` is normalized to `289-290` at parse time.
- `GreekLine.ref: string` is REQUIRED (not optional): 759 non-integer tokens corpus-wide. `line: number` stays the dense ordinal.
- Citable: plain and suffixed lines, and any number inside a range (resolves to the range line). `post N` lines carry `role: 'lacuna'` and are not citable; they render as the edition's empty brackets with the speaker label.
- Validator (stage2, `observed`): every token matches the grammar; duplicates fail; non-monotonic places must be declared in `citation.transpositions`; `post N` lines must be declared in `citation.lacunae`; `citation.fingerprint` = sha256 over the ordered token list; `title_labels` hash-declared.
- Copy citation: `Aesch. Ag. 1234`; URL `/aeschylus/agamemnon?loc=1234` (+ stride shims).

## Gate A (2026-09-05, prototype run) — English anchors vs the TLG line set

Greek side: Perseus grc2 vs TLG line sets differ only inside choral odes (lyric colometry), 1–79 numbers per play, plus outliers Hercules (Perseus +214), Ion (TLG +158), IT (TLG +149) to inspect in P2. English side (what alignment actually uses):

| play | translator | `<l n>`/milestone anchors | anchors absent from TLG (need snapping) | max gap between anchors |
|---|---|---|---|---|
| 0085001 Supplices | Smyth | 502 (l n) | 3 [297, 312, 4097] | 3690 |
| 0085002 Persae | Smyth | 469 (l n) | 8 [93, 93, 262, 262, 879] | 10 |
| 0085003 Prometheus vinct | Smyth | 450 (l n) | 4 [526, 526, 552, 552] | 5 |
| 0085004 Septem contra Th | Smyth | 441 (l n) | 4 [181, 181, 811, 1080] | 10 |
| 0085005 Agamemnon | Smyth | 673 (l n) | 13 [167, 167, 437, 437, 488] | 1557 |
| 0085006 Choephoroe | Smyth | 476 (l n) | 4 [323, 323, 652, 652] | 7 |
| 0085007 Eumenides | Smyth | 429 (l n) | 6 [178, 178, 793, 793, 823] | 6 |
| 0011001 Trachiniae | Jebb | 529 (l n) | 0 [] | 7 |
| 0011002 Antigone | Jebb | 598 (l n) | 2 [977, 977] | 6 |
| 0011003 Ajax | Jebb | 583 (l n) | 6 [255, 354, 609, 609, 719] | 10 |
| 0011004 Oedipus tyrannus | Jebb | 741 (l n) | 9 [179, 179, 190, 190, 650] | 10 |
| 0011005 Electra | Jebb | 693 (l n) | 15 [504, 504, 505, 823, 823] | 10 |
| 0011006 Philoctetes | Jebb | 645 (l n) | 11 [212, 391, 391, 691, 691] | 10 |
| 0011007 Oedipus Coloneus | Jebb | 797 (l n) | 2 [1477, 1477] | 6 |
| 0006034 Cyclops | Coleridge | 361 (l n) | 2 [369, 369] | 6 |
| 0006035 Alcestis | Coleridge | 559 (l n) | 1 [985] | 5 |
| 0006036 Medea | Coleridge | 556 (l n) | 6 [204, 204, 214, 214, 431] | 5 |
| 0006037 Heraclidae | Coleridge | 422 (l n) | 0 [] | 5 |
| 0006038 Hippolytus | Coleridge | 625 (l n) | 3 [571, 571, 825] | 19 |
| 0006039 Andromacha | Coleridge | 494 (l n) | 6 [465, 529, 778, 790, 1010] | 6 |
| 0006040 Hecuba | Coleridge | 535 (l n) | 3 [648, 648, 1024] | 5 |
| 0006041 Supplices | Coleridge | 526 (l n) | 6 [48, 48, 55, 837, 837] | 5 |
| 0006042 Electra | Coleridge | 554 (l n) | 39 [860, 1214, 1360, 1365, 1370] | 5 |
| 0006043 Hercules | Coleridge | 800 (l n) | 93 [744, 769, 803, 907, 907] | 6 |
| 0006044 Troiades | Coleridge | 499 (l n) | 0 [] | 5 |
| 0006045 Iphigenia Tauric | Coleridge | 626 (l n) | 8 [233, 408, 644, 648, 654] | 5 |
| 0006046 Ion | Coleridge | 690 (l n) | 5 [123, 123, 509, 687, 687] | 1001 |
| 0006047 Helena | Coleridge | 799 (l n) | 1 [5563] | 5001 |
| 0006048 Phoenisae | Coleridge | 755 (l n) | 0 [] | 5 |
| 0006049 Orestes | Coleridge | 830 (l n) | 1 [1437] | 5 |
| 0006050 Bacchae | Buckley | 573 (l n) | 0 [] | 5 |
| 0006051 Iphigenia Aulide | Coleridge | 722 (l n) | 0 [] | 70 |
| 0006052 Rhesus | Coleridge | 431 (l n) | 2 [254, 254] | 5 |

**Reading (orchestrator):** the primaries are line-keyed every ~5 lines with `<l n>` (no milestones) and their numbers match the TLG set almost everywhere — the "translation vs OCT drift" risk is small for Smyth/Jebb/Coleridge; P2's builder snaps an absent anchor to the nearest TLG line and reports it. Handle in P2: Hercules (93 unmatched anchors — Coleridge's lineation diverges from Diggle's in the second half), Euripides' Electra (39), typo anchors (`4097` in Supplices, `5563` in Helena, `1080` in Septem), duplicate anchors (`167, 167` = a split `<l part>` pair, count once). **Bacchae's Perseus eng2 is T. A. Buckley (1850), not Coleridge** — PD, fine; the manifest names the real translator. Cyclops/Alcestis/Heraclidae etc. carry an `n="0"` first-speaker display line: skip it.
