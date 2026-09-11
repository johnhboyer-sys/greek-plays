# Lyceum handoff — mounting the Drama wing (P6)

Status: prepared 2026-09-08; the mount itself happens in the Lyceum repo
(`~/Developer/classical-philosophy-reader`, read-only from here) in its own
session. Everything the mount needs is emitted by this repo's `npm run
build:public`; nothing is hand-authored on the Lyceum side except the two
small YAML files sketched below.

## What this repo emits (all under `build/dist/`)

| Artifact | Where | Contract |
|---|---|---|
| Work data, 44 dirs | `build/dist/<work>/` (`book-01.json`, `analyses.json`, `chapters.json`, `columns.json`, `footnotes.json`, `search/`) | the reader's `data.ts` shapes; play-line additions listed below |
| Partner manifest per work | `build/dist/<work>/manifest.json` | `schemas/manifest.v1.json`; `route: /<author>/<slug>`; the `registry:` block verbatim (now with `production` and `argument`) |
| Route registry | `build/route-registry.json` | `schemas/route-registry.v1.json`; 44 routes, unique, author-scoped (`/sophocles/electra`, `/euripides/electra`) |
| Wing entry | `build/dist/wing.drama.json` | a complete `snapshot.v1` document holding `wings[0]` = `drama` (44 memberships, 4 featured, 1 path); validated by `drama_pipeline.validate_contracts --snapshot` in the build |
| Shared LSJ shards | `build/dist/lsj/` | same shape as the aristotle corpus; the web build does NOT use them (Grammata T8, CLAUDE.md) |
| LSJ heads | `app/public/data/lsj-heads.json` | built by `app/scripts/build-lsj-heads.mjs` |

Validators the build runs: `validate_contracts --dist build/dist --registry
build/route-registry.json`, the snapshot check on the wing entry,
`check-registry-agreement.mjs`, `check-links.mjs` (0 broken over 11,778 links
at 5d64263).

## Lyceum-side files to add (sketch)

`corpora/drama/mount.yaml`, after the aristotle precedent:

```yaml
corpus: drama
source_env: DRAMA_DATA_DIR
source_default: ../greek-plays/build/dist
exclude: [lemmata, lemmata.json, lemma-map, lemma-picker, ngrams, reports, wing.drama.json]
search_exclude: [offsets.json, grammar-dict.json, grammar-col.bin]
citationRoutes: true
```

`corpora/drama/groups.yaml` — two shelves, not `schools`:

```yaml
groups:
  - numeral: I
    title: Tragedy
    works: [persians, seven-against-thebes, suppliants-aesch, prometheus-bound, agamemnon, libation-bearers, eumenides,
            ajax, antigone, trachiniae, oedipus-tyrannus, electra-soph, philoctetes, oedipus-coloneus,
            alcestis, medea, heraclidae, hippolytus, andromache, hecuba, suppliants-eur, electra-eur, heracles,
            trojan-women, iphigenia-in-tauris, ion, helen, phoenician-women, orestes, bacchae, iphigenia-at-aulis, rhesus, cyclops]
  - numeral: II
    title: Comedy
    works: [acharnians, knights, clouds, wasps, peace, birds, lysistrata, thesmophoriazusae, frogs, ecclesiazusae, wealth]
```

Snapshot: splice `wings[0]` of `wing.drama.json` into
`fixtures/snapshot.lyceum.json`; add `drama` to the taxonomy's author
period order if the catalog groups by period (all four authors are
`classical`). The `genre` field on the authors is additive and must not be
read as a school.

## Code the Lyceum must carry (a copy, not a merge)

The registries in both repos are kept whole, so the play-line scheme is
COPIED into the Lyceum's `scheme.py` / `citation.ts` with its tests:

- `pipeline/drama_pipeline/scheme.py`: the `play-line` entry, `_VERSE_LINE_RE`
  / range / `post N` grammar, `verse_line_kind`, `verse_line_order_key`;
  `refs.py` dispatch on `play_line_scheme`.
- `shared/lib/citation.ts`: `makePlayLineScheme`, `parseLocation` /
  `formatLocValue` for the bare-line form, `UNIT_NOUN_SINGULAR['play-line']`,
  `lastPrintedRef`; parity tests with the Python grammar
  (`shared/__tests__/play-line.test.ts`, `pipeline/tests/test_scheme_play_line.py`).
- `app/src/lib/citation-routes.ts`: the `stride` option (one shim per 50
  lines), and `app/src/pages/[author]/[work]/index.astro`'s rule that a
  bookless play-line work renders the reader at the bare path (no
  `/book/1`).

Reader-core divergences are listed one per line in `DRIFT.md` (fork SHA at
the top). The ones the Lyceum's shared core must absorb for plays to render:

- `shared/lib/data.ts`: `GreekLine.ref`, `GreekLine.label` (strophe marks),
  `Segment.englishCoveredBy`, `EnglishTurn.speakerMismatch`, `speakerRoster`.
- `shared/lib/speakers.ts`: `lineRenderParts` speaker parts with offsets
  (antilabe), `buildEnglishTurnBlocks` with `turnIndex`, `playSigla`.
- `shared/components/Reader.svelte`: the `playLine` branches — per-line turn
  rows (`playRows`), the shared gutter, `playOde`, the play-line compare
  layout, `settleDeepLink`, `resolvePlayLineRef`.
- `shared/components/Plate.svelte` + `ReaderShell.astro`'s plate props and
  `data-genre` on `<html>`.
- `shared/styles/global.css`: the `.reader-body.play-line` section and the
  P4 token block (`--accent`/`--band` by `data-genre`, the pigment `--spk-*`
  slots, Cardo + Alegreya Sans SC). The Lyceum shell decides whether the
  Drama wing keeps this skin as its wing theme (LYCEUM-READER-SPEC §P4:
  "wing theming via guarded palette") — the token block is value-swap
  revertible by design.

## Copy status

Every `argument`, the wing description and the path description carry the
`DRAFT — ` prefix until John approves them in the manifests
(REVIEW-CHECKLIST 12). The Lyceum should print them as they come; the
prefix is the honesty marker, not a bug.

## Sizes (2026-09-08, 44 works)

`build/dist` ≈ 181 MB before the public prune; site 1,272 pages + 44
partner manifests; the R2 estimate in `docs/plan.md` (100–150 MB after
prune) stands to be measured at P5.

## Reading routes for plays (2026-09-11)

Every play is a single-book `play-line` work, and the site builds no
`/book/1` page for one (`app/src/pages/[author]/[work]/book/[n].astro`
skips it; the play reads at its bare work route instead). The owner ruled
2026-09-11: partner manifests for these 44 works now advertise the bare
`reading_route` (`/<author>/<work>`, no `/book/1`) rather than a dead link.
The partner's `reading_route` pattern must accept this shorter form. Every
other work is unchanged: a multi-book work still advertises
`/<author>/<work>/book/<n>`, and a section work still advertises
`/read/<author>/<work>/section-<n>`.
