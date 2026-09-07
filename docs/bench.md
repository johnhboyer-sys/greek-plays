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
