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
