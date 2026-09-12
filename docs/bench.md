# Bench translations (comparison slots)

A second (or third) public-domain translation rides in `english.secondary`
(`model: turn-text` or `perseus-play`). The reader already picks
`english` / `secondary` / `third` / overlay; stage7 emits the second slot
as `ross` (the reader reads `secondary ?? ross`).

## Loeb OCR recipe (`bench_clean`)

Source: facing-page Loeb `_djvu.txt` under `sources/archive-org/`.

```
pipeline/.venv/bin/python -m drama_pipeline.bench_clean \
  --volume sources/archive-org/<id>.txt \
  --translator storr --play antigone --title ANTIGONE
```

Writes `sources/bench/<translator>/<play>.txt` (committed) and
`build/bench/<translator>/<play>.json` (pages kept/dropped, speakers,
suspicious lines). The cleaner (a) cuts the play by its title heading and
the next play’s heading or `END OF VOL`, (b) drops pages whose Greek-letter
ratio is > 0.3, (c) drops running heads, bare page numbers, marginal line
numbers, (d) rejoins hyphenated breaks, (e) folds a caps name on its own
line into `NAME. text`.

`--layout verse-own-line` is the English-only verse path (Morshead): no
Greek pages, speaker names stay on their own line for `format: verse-own-line`.

## Per-play checklist

1. Confirm the translator is on `public_domain_translations.yaml` (fail-closed).
2. Run the cleaner; check `speakers_found` against the Greek roster.
3. Special-case OCR damage in `bench_clean` (volume signatures, `VOR.` junk)
   rather than hand-editing the txt.
4. Manifest: `english.secondary` with `model: turn-text`, `format: loeb-ocr`
   (facing-page) or `format: verse-own-line` (Morshead),
   `source: bench/<translator>/<play>.txt`, `play:` = the title heading;
   `speakers.english_secondary` maps the printed caps names onto the roster
   (reuse `speakers.english` only when the printed names already coincide).
5. `registry.translations[]` entry, `slot: secondary`, name carries
   “— by speech”.
6. `drama_pipeline all --work <id> --public`; secondary pairing rate ≥ 0.85.

## Sophocles / Storr Loeb OCR (1912–13)

The six post-pilot sources below come from volume I
(`sophocleswitheng01soph.txt`) or volume II
(`in.ernet.dli.2015.183451.txt`). Counts are the cleaner report's page
chunks, not the book's printed page count. A correction pass on 2026-09-08 (three
Sonnet lanes, a Grok read against the Loeb, hand reverts; logs under
`build/storr/`, summary in REVIEW-CHECKLIST item 5) fixed some 600 scan
faults; a few dozen unreadable lines remain as scanned.

- `oedipus-tyrannus`: heading `THE KING`; 123 kept / 247 dropped.
  Speakers: `OEDIPUS`, `PRIEST`, `CREON`, `CHORUS`, `TEIRESIAS`, `JOCASTA`,
  `MESSENGER`, `HERDSMAN`, `SECOND MESSENGER`; `HERDSMAN` maps to the Greek
  roster's `Servant`. Residual examples include `[5` for “Is,” `1]` for “I,”
  and isolated Greek glyphs in 20 English or note lines.
- `oedipus-coloneus`: heading `OEDIPUS AT COLONUS`; 148 kept / 294 dropped.
  The scan omits OCR for the title page, so the cleaner starts at the first
  English running head after `DRAMATIS PERSONAE`. Speakers: `OEDIPUS`,
  `ANTIGONE`, `STRANGER`, `CHORUS`, `ISMENE`, `THESEUS`, `CREON`,
  `POLYNEICES`, `MESSENGER`. Residual examples include `[αἱ ismene`, `ΠῚ is`,
  and isolated Greek glyphs in 19 English or note lines.
- `ajax`: heading `AJAX`; 83 kept / 146 dropped. Speakers: `ATHENA`,
  `ODYSSEUS`, `AJAX`, `CHORUS`, `TECMESSA`, `MESSENGER`, `SEMI-CHORUS 1`,
  `SEMI-CHORUS 2`, `TEUCER`, `MENELAUS`, `AGAMEMNON`; the numbered
  semi-choruses map to the Greek roster's first and second semichoruses.
  Residual examples include `trai]`, `brazen-mnouthed`, `An@é@`, and isolated
  Greek glyphs in 16 English or note lines.
- `electra-soph`: heading `ELECTRA`; 146 kept / 277 dropped. Speakers:
  `AGED SERVANT`, `ORESTES`, `ELECTRA`, `CHORUS`, `CHRYSOTHEMIS`,
  `CLYTEMNESTRA`, `AEGISTHUS`; `AGED SERVANT` maps to `Paedagogus`.
  Residual examples include `staine@`, `s®elds`, `pertected`, and isolated
  Greek glyphs in 29 English or note lines.
- `trachiniae`: heading `TRACHINIAE`; 120 kept / 208 dropped. Speakers:
  `DEIANIRA`, `NURSE`, `HYLLUS`, `CHORUS`, `MESSENGER`, `LICHAS`,
  `SEMI-CHORUS 2`, `OLD MAN`, `HERACLES`; the semi-chorus maps to the Greek
  roster's second semichorus. Residual examples include `TuHERE`, `ehoeen`,
  `knowmg`, and isolated Greek glyphs in 23 English or note lines.
- `philoctetes`: heading `PHILOCTETES`; 119 kept / 136 dropped. Speakers:
  `ODYSSEUS`, `NEOPTOLEMUS`, `CHORUS`, `PHILOCTETES`, `SAILOR`, `HERACLES`;
  `SAILOR` maps to the Greek roster's `Merchant`. Residual examples include
  `and_groaning`, `sammer`, `Securelyeand`, `gvas`, and isolated Greek glyphs
  in 13 English or note lines.

For `oedipus-tyrannus`, pass `--next-title 'OEDIPUS AT COLONUS'`; this cuts
before the next play's argument because that title page has no OCR text.

## Euripides / Way Loeb OCR (1912)

A. S. Way, Loeb Classical Library, four volumes, verse. The vendored
`sources/archive-org/euripidesway01euriuoft.txt` … `euripidesway04euriuoft.txt`
are Greek-script Tesseract (`latin_letters=0`) and cannot feed the cleaner.
The committed `sources/bench/way/*.txt` were built from bilingual tesseract-5
OCR of the same 1912 Loeb: vol. 1 `euripides0000euri_y2n1`, vol. 2
`euripides0002arth`, vol. 3 `euripideswithan01waygoog`, vol. 4
`euripideswithan00waygoog`. English is on the recto. Counts are the cleaner
report's page chunks. Pass `--next-title` for the following play (Ion needs
`HIPPOLYTUS` because the title page has no OCR). Cyclops stops at the Loeb
publisher catalog. Way's printed headings differ from our ids.

Pairing is the stage-1 secondary `pairing_rate` (named Greek turns that got a
same-speaker English turn). Coverage is `segments_with_chunk / segments_total`.
The stage-2 floor is 0.85.

| id | heading | pages kept/dropped | pairing | coverage | residual OCR |
|---|---|---|---|---|---|
| `iphigenia-at-aulis` | `IPHIGENEIA AT AULIS` | 215 / 181 | 0.978 | 0.944 | `nith attendants`; `A 20mm Ces Om` |
| `rhesus` | `RHESUS` | 147 / 156 | 0.989 | 0.887 | `Where he 1s stationed` |
| `hecuba` | `HECUBA` | 218 / 178 | 0.968 | 0.934 | `nith Children`; isolated scan glyphs |
| `trojan-women` | `DAUGHTERS OF TROY` | 218 / 151 | 0.929 | 0.879 | `mith ASTYANAX`; `76C` for a line number |
| `helen` | `HELEN` | 256 / 267 | 0.968 | 0.948 | `mith the offerings` |
| `electra-eur` | `ELECTRA` | 221 / 88 | 0.949 | 0.925 | `How ?—1me thou mad'st` |
| `orestes` | `ORESTES` | 291 / 135 | 0.985 | 0.970 | `1f of his wedded wife`; `65C` |
| `iphigenia-in-tauris` | `IPHIGENEIA IN TAURICA` | 212 / 91 | 0.984 | 0.961 | `Orestes "—5so`; `uncle—4Ae` |
| `andromache` | `ANDROMACHE` | 212 / 82 | 1.000 | 0.965 | scattered `nife`/`mith` |
| `cyclops` | `CYCLOPS` | 134 / 116 | 0.973 | 0.969 | `I ?—4devil take you!` |
| `bacchae` | `THE BACCHANALS` | 185 / 91 | 0.890 | 0.852 | `PENTHEUS. 1go....`; isolated Greek glyphs |
| `heracles` | `MADNESS OF HERCULES` | 193 / 130 | 0.908 | 0.848 | `forms of 1n1s and Mapness`; `3h my son` |
| `heraclidae` | `CHILDREN OF HERCULES` | 111 / 90 | 0.782 | 0.767 | `Hurls 1otavs`; `shame t6o` |
| `phoenician-women` | `PHOENICIAN MAIDENS` | 196 / 146 | 0.900 | 0.869 | `Wuen Oedipus`; `Sulfilled the oracle` |
| `suppliants-eur` | `SUPPLIANTS` | 132 / 90 | 0.920 | 0.843 | `nith`/`Wuen` in the argument |
| `ion` | `ION` | 298 / 250 | 0.874 | 0.834 | `cHorus 10`; `10N (starteng back` |
| `hippolytus` | `HIPPOLYTUS` | 220 / 129 | 0.964 | 0.934 | `nith her handmaids`; `M30` |
| `medea` | `MEDEA` | 248 / 189 | 0.948 | 0.913 | `nife`/`mith` in the argument |
| `alcestis` | `ALCESTIS` | 189 / 145 | 0.955 | 0.936 | `nife`/`mith` in the argument |

`heraclidae` stays under 0.85: 167 English speaker-turns against 206 Greek
segments (stichomythia). Every recovered English turn already pairs; aliases
cannot invent labels the scan never printed. That is a `stage1_turn_english`
one-turn-to-one-segment ceiling, not a floor to lower.

For Ion, pass `--next-title HIPPOLYTUS`. For Cyclops, the cleaner stops at
`THE LOEB CLASSICAL` so the publisher list is not speakers.

## Aeschylus / Morshead verse (1881–1908)

E. D. A. Morshead, English-only verse, not a Loeb facing-page scan. Two
Archive.org volumes: `houseofatreusbei00aesc.txt` (1904: Agamemnon, The
Libation-Bearers, The Furies) and `suppliantmaidens00aesc.txt` (1908: The
Suppliant Maidens, The Persians, The Seven against Thebes, Prometheus Bound).
Speaker names sit on their own line in small caps (OCR as title-case, sometimes
all-caps or italic junk). Pass `--layout verse-own-line`; the cleaner emits
Lindsay-style own-line caps names for `format: verse-own-line`. Counts are
verse lines kept, not pages.

Pairing is the stage-1 secondary `pairing_rate`. Coverage is
`segments_with_chunk / segments_total`. The stage-2 floor is 0.85.

| id | heading | lines kept | pairing | coverage | residual OCR |
|---|---|---|---|---|---|
| `suppliants-aesch` | `THE SUPPLIANT MAIDENS` | 1395 | 0.881 | 0.803 | `Pours Nikis to the wave` |
| `persians` | `THE PERSIANS` | 1431 | 1.000 | 0.917 | `luill ta7'ry`; `e7iiuraps` |
| `seven-against-thebes` | `THE SEVEN AGAINST THEBES` | 1320 | 0.627 | 0.558 | `tha7ik Heaveti`; `Do7un with Eteocles` |
| `prometheus-bound` | `PROMETHEUS BOUND` | 1423 | 0.990 | 0.971 | `Hmitary land`; `When 1 behold` |
| `agamemnon` | `AGAMEMNON` | 2298 | 0.928 | 0.824 | `a7id Priam's town`; `Troja7i pride` |
| `libation-bearers` | `THE LIBATION-BEARERS` | 1471 | 0.985 | 0.932 | `shorn, 1 bring`; `mocking1 thine` |
| `eumenides` | `THE FURIES` | 1367 | 0.942 | 0.781 | `0 king Apollo`; `bear witness, Hell 1` |

`seven-against-thebes` stays under 0.85: 104 English speaker-turns against 161
named Greek segments. Murray cuts the parodos and kommos into many lyric
pieces; Morshead prints long Chorus odes and one combined Antigone/Ismene/Chorus
heading, and never labels Ismene. Every recovered English turn already pairs;
aliases cannot invent labels the scan never printed.

```
pipeline/.venv/bin/python -m drama_pipeline.bench_clean \
  --layout verse-own-line \
  --volume sources/archive-org/suppliantmaidens00aesc.txt \
  --translator morshead --play persians --title 'THE PERSIANS' \
  --next-title 'THE SEVEN AGAINST THEBES'
```

## Comedy comparison slots

Comedies keep the 1912 Athenian Society text as `english.primary` (unexpurgated).
Hickie and Rogers ride only as comparison slots (`english.secondary`,
`english.third`, or overlay). Do not add a character the Greek roster does
not already name.

- **Clouds / Hickie** (W. J. Hickie, Bohn 1853, prose, bowdlerized): Perseus TEI
  `sources/perseus/tlg0019.tlg003.perseus-eng2.xml`, `model: perseus-play`,
  `anchor_model: sp-line`, `footnotes: false`. Line-owner attachment, so the
  registry name has no “by speech” suffix. `speakers.english_secondary`
  maps each `<speaker>` string (trailing period as printed) onto
  `speakers.sigla` values.
- **Lysistrata / Lindsay** (Jack Lindsay, 1925, verse, unexpurgated): Gutenberg
  `sources/gutenberg/pg7700.txt`, `model: turn-text`, `play: LYSISTRATA` (the
  body title above `The Persons of the drama.`, not the PG header). Registry
  name carries “— by speech”. Pairing floor 0.85; if it misses,
  fix aliases (or the Lindsay own-line parser), never the floor.

### Aristophanes / Hickie prose (Bohn 1853)

W. J. Hickie, English-only prose. The vendored DLI scans
(`in.ernet.dli.2015.515629.txt`, `in.ernet.dli.2015.515630.txt`) are
tesseract `-l san` (0 Latin letters) and cannot feed the cleaner. The
committed `sources/bench/hickie/*.txt` were cleaned from the Google-digitized
1853 Bohn of the same edition (`comediesaristop01hickgoog` vol. 1,
`comediesaristop00hickgoog` vol. 2) with `--layout prose-inline`: inline
`Dic.` / `Dicæopolis (solus).` labels expanded from each play's dramatis
personae into `NAME. text` for `format: loeb-ocr`.

Clouds stays on the Perseus TEI (line-keyed). Pairing is stage-1
`pairing_rate`; coverage is `segments_with_chunk / segments_total`.

| id | translator | slot | pairing | coverage | residual OCR |
|---|---|---|---|---|---|
| `clouds` | Hickie | secondary (Perseus TEI) | line-keyed | — | Perseus `<speaker>` strings |
| `acharnians` | Hickie | secondary | 0.838 | 0.828 | `asq@int`; `Beeotian sté` |
| `knights` | Hickie | secondary | 0.764 | 0.757 | `Aras! alas`; `S. S.` sausage-seller |
| `wasps` | Hickie | secondary | 0.614 | 0.609 | `SOSEAS` for Sosias |
| `peace` | Hickie | secondary | 0.772 | 0.769 | `TRYGAOUS`; `THEORIA` |
| `birds` | Hickie | secondary | 0.821 | 0.816 | `PISTHETAIRUS`; `Pistu`/`Pista` |
| `lysistrata` | Hickie | third | 0.766 | 0.764 | `Caton.`; `Cuo. or Men.` |
| `thesmophoriazusae` | Hickie | secondary | 0.798 | 0.789 | `CLISTHENES`; `Myes.` for Mnesilochus |
| `frogs` | Hickie | secondary | 0.783 | 0.780 | `BACCHUS` for Dionysus; `ZBACUS` |
| `ecclesiazusae` | Hickie | secondary | 0.394 | 0.394 | `Buep`/`Bier`/`Burp` for Blepyrus |
| `wealth` | Hickie | secondary | 0.587 | 0.586 | `Pov`/`Pru` for Plutus |

`acharnians` stays under 0.85: Hickie never labels Pseudartabas, the
Megarian's girls, or the numbered semichoruses. Every recovered English
turn already pairs; aliases cannot invent labels the scan never printed.

`ecclesiazusae` and `wealth` stay well under 0.85 because the Google OCR
of speaker abbreviations is too damaged (Blepyrus, Plutus) to recover the
turns the page images print. That is an OCR ceiling, not a floor to lower
on the primary.

```
pipeline/.venv/bin/python -m drama_pipeline.bench_clean \
  --layout prose-inline \
  --volume /tmp/hickie1.txt \
  --translator hickie --play acharnians --title 'THE ACHARNIANS' \
  --next-title 'THE KNIGHTS'
```

### Aristophanes / Rogers verse (Loeb 1924)

B. B. Rogers, Loeb vol. 3 (`aristophanes0003benj_r6k0.txt`), facing-page
verse, bowdlerized — comparison only. `bench_clean` (loeb layout) plus a
per-play 2–3 letter expansion table (`CA.` → `CALONICE`). Slot: `third` on
thesmophoriazusae / ecclesiazusae / wealth (Hickie already occupies
secondary); overlay on lysistrata (Lindsay secondary, Hickie third).
`stage1_turn_english.run(..., slot="third"|"overlay")` writes
`third_chunks.json` or merges `overlays.json`.

| id | translator | slot | pairing | coverage | residual OCR |
|---|---|---|---|---|---|
| `lysistrata` | Rogers | overlay | 0.258 | 0.257 | `CA.`; `ty.` for LY.; Greek pages mixed in |
| `thesmophoriazusae` | Rogers | third | 0.475 | 0.470 | `MN.`; `E EU` |
| `ecclesiazusae` | Rogers | third | 0.407 | 0.407 | `Z BL`; `E CHR` |
| `wealth` | Rogers | third | 0.392 | 0.392 | `E CA`; `SCHR` |

Rogers stays under 0.85 on all four: the Loeb facing-page scan drops about
half the pages as Greek, and the remaining English speaker-turns are far
fewer than the Greek segments (bowdlerized cuts plus lost labels). Every
recovered English turn already pairs; aliases cannot invent labels the
scan never printed.

### Aristophanes / Arrowsmith verse (Michigan, 1961–62)

William Arrowsmith, *The Complete Greek Comedy* (unexpurgated) — `third`
slot on birds and clouds. Not an OCR scan: the source is the owner's own
History Genie OCR of the Fulcrum PDF (`.docx`, converted `textutil -convert
html` to `build/arrowsmith/genie-{birds,clouds}.html`, keeping the `<i>`
runs the plain-text conversion loses). `bench_clean_verse.
write_clean_genie_html` (`--layout genie-html`) bounds the play at its
"SCENE:" opening and "Notes" end matter, strips the per-page footer/page-
number/`---` triplet, strips a footnote `*`, strips the odd `$\qquad...$`
LaTeX artifact Genie left for a mid-line indent, and folds a staggered
shared line's nbsp-indented halves into plain left-aligned lines.

Arrowsmith's stage directions, sung odes, and a few emphasised one-line
exclamations are all set identically (a fully-italic paragraph); the
cleaner drops a fully-italic paragraph by default (matching Morshead: no
channel for stage directions in this format) and keeps one only if its
paragraph index is listed in `GENIE_DIALOGUE_OVERRIDES[play]` — every such
index was checked by hand against the printed page image, not guessed.
Arrowsmith also sets a phrase in bare caps for emphasis now and then (a
telegram, a shouted announcement); a bare all-caps line with no punctuation
is exactly what the shared verse-own-line reader takes for a new speaker
cue, so the cleaner folds any such line into a neighbouring verse line
(the format already joins consecutive lines of one speech with a space, so
this changes nothing about the rendered text). `GENIE_SPEAKER_RELABELS`
retags a printed speaker cue by paragraph index when Arrowsmith gives one
label to more than one Greek role (Birds' "MESSENGER" covers the Dover
text's First Messenger, the Herald, and the plain Messenger — checked
against `build/stage1/greek_spine.json`).

A word-level diff of the cleaned play text against each PDF's own
`pdftotext` layer (`sources/fulcrum/{birds,clouds}.txt`) found the PDF
layer wrong in nearly every disagreement and no Genie slip in the kept
dialogue text; see `build/arrowsmith/{birds,clouds}-changes.tsv`.

| id | heading | lines kept | pairing | shift rate | length-ratio outliers |
|---|---|---|---|---|---|
| `clouds` | `THE CLOUDS` | 2276 | 0.978 | 0.037 | 0.145 |
| `birds` | `THE BIRDS` | 2644 | 0.986 | 0.050 | 0.148 |

```
pipeline/.venv/bin/python -m drama_pipeline.bench_clean_verse \
  --layout genie-html \
  --volume build/arrowsmith/genie-clouds.html \
  --translator arrowsmith --play clouds --title "THE CLOUDS"
```
