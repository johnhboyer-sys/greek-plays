# The Greek Drama Reader

*(Working title — naming is John's decision before the first public deploy.)*

A parallel Greek/English reader for the 44 complete Greek plays — Aeschylus,
Sophocles, Euripides, Aristophanes — with several public-domain translations
per play for side-by-side comparison, click-to-parse morphology, dictionary
lookups, search, and citation by line.

Forked from `~/Developer/classical-philosophy-reader` (see `DRIFT.md`); it
will later mount into the Lyceum Reader as its Drama wing. Plan of record:
`docs/plan.md`.

## Dev quickstart

Requires Node 22 (`nvm use 22`) and `uv`.

```
cd app && npm ci
cd ../shared && npm ci
cd ../pipeline && uv sync
```

Tests: `npx vitest run` in `app/` and `shared/`; `uv run pytest` in `pipeline/`.

## Licence

The code is MIT (`LICENSE`). The Greek line files in `corpus/greek/` are
CC0 1.0; John's own apparatus and drawings are CC BY 4.0. Everything under
`sources/`, and the site data built from it, keeps its own terms, which
`LICENSE` does not cover: some are NonCommercial or NoDerivatives. The table
at the head of `sources/INVENTORY.md` lists each.

## Copyright stance

The TLG's own files, its beta code, and the Diogenes export are licensed and
local and never committed; each play's Greek is committed as a plain line file
in `corpus/greek/` (`python -m drama_pipeline.extract` makes them).
Translations are used when their terms allow reproduction: public domain
by US rules (pre-1931, or a 1931-1963 US book whose copyright was never
renewed), a Creative Commons or other open licence, or the rights holder's
own free-to-use statement. Each licence's terms are honoured, and every
translator is credited on the attribution page. The pipeline's allowlist
is fail-closed. Aristophanes ships unexpurgated.
