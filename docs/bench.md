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

## Per-play checklist

1. Confirm the translator is on `public_domain_translations.yaml` (fail-closed).
2. Run the cleaner; check `speakers_found` against the Greek roster.
3. Special-case OCR damage in `bench_clean` (volume signatures, `VOR.` junk)
   rather than hand-editing the txt.
4. Manifest: `english.secondary` with `model: turn-text`, `format: loeb-ocr`,
   `source: bench/<translator>/<play>.txt`, `play:` = the title heading;
   `speakers.english_secondary` maps the printed caps names onto the roster
   (reuse `speakers.english` only when the printed names already coincide).
5. `registry.translations[]` entry, `slot: secondary`, name carries
   “— alignment approximate”.
6. `drama_pipeline all --work <id> --public`; secondary pairing rate ≥ 0.85.

## Sophocles / Storr Loeb OCR (1912–13)

The six post-pilot sources below come from volume I
(`sophocleswitheng01soph.txt`) or volume II
(`in.ernet.dli.2015.183451.txt`). Counts are the cleaner report's page
chunks, not the book's printed page count. The source text still has scattered
word- and character-level OCR faults; fixing those safely would need a full
check against the page images.

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

## Comedy comparison slots

Comedies keep the 1912 Athenian Society text as `english.primary` (unexpurgated).
A comparison translation rides only in `english.secondary`. Do not add a
character the Greek roster does not already name.

- **Clouds / Hickie** (W. J. Hickie, Bohn 1853, prose, bowdlerized): Perseus TEI
  `sources/perseus/tlg0019.tlg003.perseus-eng2.xml`, `model: perseus-play`,
  `anchor_model: sp-line`, `footnotes: false`. Line-owner attachment, so the
  registry name has no “alignment approximate”. `speakers.english_secondary`
  maps each `<speaker>` string (trailing period as printed) onto
  `speakers.sigla` values.
- **Lysistrata / Lindsay** (Jack Lindsay, 1925, verse, unexpurgated): Gutenberg
  `sources/gutenberg/pg7700.txt`, `model: turn-text`, `play: LYSISTRATA` (the
  body title above `The Persons of the drama.`, not the PG header). Registry
  name carries “— alignment approximate”. Pairing floor 0.85; if it misses,
  fix aliases (or the Lindsay own-line parser), never the floor.
