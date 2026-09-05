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

## Copyright stance

Greek source text (TLG) is licensed and local and is never committed.
Translations are public-domain by US rules (pre-1931); the pipeline's
allowlist is fail-closed. Aristophanes ships unexpurgated.
