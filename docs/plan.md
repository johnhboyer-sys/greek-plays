# The Greek Drama Reader — build plan (`~/Developer/greek-plays`)

## Context

John wants a public, standalone parallel Greek/English reader for every complete Greek play in the local TLG corpus, tragedies and comedies, built on the reader family (aristotle-reader → plato-reader → classical-philosophy-reader/Lyceum, homer-reader). It ships on its own first and later mounts into the Lyceum Reader as the "Drama" wing the Lyceum spec already names (`LYCEUM-READER-SPEC.md` §1; open decision "drama shelf-vs-wing" §8). The selling point is **translation comparison**: several public-domain translations per play, side by side with the Greek.

## Rulings from John (2026-09-05)

- **Scope: 44 plays, four authors.** Aeschylus 7, Sophocles 7, Euripides 19 (incl. Rhesus, Cyclops), Aristophanes 11. Menander excluded (later wave). All TLG "Fragmenta" works excluded.
- **Hosting: Cloudflare Pages + R2**, same as the Lyceum target (CPR `docs/cloudflare-setup.md`), free tier.
- **Working name: The Greek Drama Reader**, corpus id `drama` (`SITE_NAME` is one line; naming stays John's).
- **Style: like the Homer Reader, not the Aristotle/Plato template.** A distinctive reading-first skin (homer-reader-plan §6), delivered as a token layer + chrome; John picks a direction from mockups. Recommended shape (John's "skin per play?" question): ONE skin, with a per-genre or per-author accent and a **per-play opening plate** (title, cast, setting, festival/date, one-line argument) — each play gets its own moment without 44 skins. A per-work accent token (`registry.accent`) is a one-line addition if wanted.
- **Speaker attribution in color, as in the Plato reader** (`shared/lib/speaker-colors.ts` + `speakers.ts` lead-ins): stable hue per character across the Greek and every translation column.
- **No play-switcher inside the reader.** Author and play in the running head are plain links back to `/author` and `/author/play`; the Breadcrumb `<select class="work-switcher">` and the RunningHead LibrarySheet are removed.
- **Translation comparison** is the product: every play carries a bench of PD translations in the existing slots (`english`, `secondary`, `third`, `overlay`…; picker + compare mode inherited).
- **Aristophanes unexpurgated**: 1912 Athenian Society *Eleven Comedies* is primary; Rogers, Hickie, Lindsay, Frere ride as comparison slots.
- **Scansion ("Idk")**: optional later phase (P7 below), not in the corpus build.

Standing rules inherited from every sibling: TLG source text never committed; website translations PD-US only (pre-1931), John rules on any exception; deploys, money, domains, naming, copyright are John's gates; verify functionally; all data fetches through the `data.ts` data-root override; Node 22 (`nvm use 22`); never edit sibling repos.

## Sources and copyright (verified 2026-09-05)

**Greek.** TLG via Diogenes 4.7.2 `-y` export (CPR `docs/tlg-phi-export.md`), one invocation per author. Work numbers and editions read from `TLG Files/TLG/DOCCAN2.TXT` (plain-text canon):
- TLG0085 Aeschylus 001–007 (Murray, OCT 2nd ed. 1955)
- TLG0011 Sophocles 001–007 (Dain–Mazon, Budé 1955–60)
- TLG0006 Euripides **034–052** (034 Cyclops … 051 IA, **052 Rhesus**; Diggle OCT 1981–94). 001–033 are fragments: out.
- TLG0019 Aristophanes 001–011 — **editions differ per play**: Coulon (Budé) for most, Dover 1968 (Nubes 003), MacDowell 1971 (Vespae 004), Ussher 1973 (Eccl. 010) → per-work `greekEdition` + per-work `expected_sourcedesc` FATAL gate (DRN precedent).
Never enumerate plays by "citation level = Line" (fragment works share it); use the explicit allowlist above. Diogenes turns TLG `{…}` speaker braces into `<label type="speaker">`, the element plato-reader already parses.

**English** (Perseus canonical-greekLit TEI vendored at a pinned SHA with SHA256SUMS + `sources/INVENTORY.md`; Gutenberg/archive.org for the rest):

| Author | Primary (line-keyed) | Perseus shape | Comparison bench (PD-US, pre-1931) |
|---|---|---|---|
| Aeschylus | H. W. Smyth, Loeb 1922–26 (`tlg0085.tlgNNN.perseus-eng2.xml`; Ag. = eng3) | `<sp><speaker>` + `<l n="1">`, `<l n="5">`… prose keyed every ~5 Greek lines; Loeb `<note>`s | Morshead verse 1881–1908; Plumptre 1868; Swanwick 1873; Browning's Agamemnon (Perseus eng4) |
| Sophocles | R. C. Jebb 1883–1900 (eng2; Trach. = eng3) | same + strophe/antistrophe/episode/choral textpart divs | Storr, Loeb verse 1912; Plumptre 1865; Campbell verse 1883 |
| Euripides | E. P. Coleridge 1891 (eng2; Rhesus = eng3) | same; `<l part="I|F">` split lines | A. S. Way, Loeb verse 1912; Gilbert Murray verse (Hipp., Bacch., Med., Tro., El., IT, Alc., Rhesus eng4; 1902–15); Potter 1781 |
| Aristophanes | **Athenian Society 1912** (anonymous, "literally and completely translated"; Gutenberg #8688 = Knights, Ach., Peace, Lys., Clouds; #8689 = rest). No line numbers. | — (Perseus English is only Clouds/Birds; elsewhere O'Neill 1938, NOT PD) | Rogers verse 1902–16; Hickie prose 1853 (Perseus TEI for Clouds/Birds, line-keyed); Lindsay's Lysistrata 1925 (Gutenberg #7700); Frere (Ach., Kn., Birds, Frogs) |

Rogers and Hickie are bowdlerized: comparison only, never primary. Which bench texts ship in wave 1 is decided per play by source quality (clean text, speaker labels present); the manifest shape does not change. John confirms US-PD status per translation before it ships; the fail-closed PD allowlist (ported from homer `public_domain_translations.yaml`) carries an explicit `# DENIED` entry for O'Neill 1938 so no future session reaches for Perseus's default Aristophanes English.

## Architecture decisions

### 1. Fork source and bootstrap
**Fork CPR** (`~/Developer/classical-philosophy-reader`, record HEAD SHA in `DRIFT.md`); **port two files from homer** (`pipeline/homer_pipeline/stage1_perseus_milestone_english.py`, `public_domain_translations.yaml`) and one from plato (`pipeline/gen_speaker_rosters.py`). Not a git clone: copy `pipeline/ shared/ app/ scripts/ schemas/ fixtures/ package.json CLAUDE.md REVIEW-CHECKLIST.md`, then `git init`.
- Rename Python package `reader_pipeline` → `drama_pipeline`; `READER_PY` → `DRAMA_PY` in `scripts/build-public.mjs`.
- **Strip:** all 62 manifests and `sources/*` (keep a fresh `INVENTORY.md`); Latin/PHI (`latin.py`, `stage1_latin.py`, `stage1_verse_line_english.py`, PHI branches in `config.py`/`preflight.py`); DK (`dk_lang.py`, `dk_witness.py`, `_parse_fragments`); one-off English builders (`stage1_ross/ostwald/freeman_english/chapter_concordance_english/book_section_english/flat_english/citation_expansion/context_english.py`); hub-only machinery (`corpora/`, `scripts/mount-corpus.mjs`, `scripts/lib/corpus-adapter/`, `probe-corpus-compat.mjs`, `vendor-aristotle-registry.mjs`, the mount loop in `build-public.mjs`); `docs/` except `tlg-phi-export.md`, `design-spec.md`, `verification-battery.md`; the `PUBLIC_LYCEUM_CHROME` band/home components.
- **Keep whole:** the full scheme registries in `scheme.py`/`citation.ts` (every scheme stays; `play-line` is ADDED) — deleting schemes breaks ~880 shared tests and makes every patch-forward a hand-merge. Keep `turns.py`, `align_turns.py`, `stage1_stephanus_english.py`'s turn walker (reused for bench alignment), `schemas/`, `registry:`-block manifests + `manifests/authors.yaml`, `build-registry.mjs`, `build-route-registry.mjs`, `check-registry-agreement.mjs`, `emit-lyceum-manifest.mjs`, the `PUBLIC_WING` seam, stage7's v1 `manifest.json` emitter.
- **DRIFT.md** in homer's format: one line per diverged shared-core file, added in the same commit.

### 2. Citation scheme: `play-line` (new; Homer semantics, CPR core)
CPR's `verse-line` = one segment per line (Lucretius) and lineless columns; homer's = one segment per book with user-facing lines. Drama needs homer's: **bookless (`books: 1`), one segment per play (or per act/scene boundary for scroll performance), lines user-facing, citation = bare line ("Ag. 1234"), `validation_mode: observed`**.
- Grammar: column `^[0-9]+$` (synthetic single column "1"), ref `^[0-9]+[a-z]?$`; reuse verbatim CPR's `_VERSE_LINE_RE`/`_VERSE_LINE_RANGE_RE`, `verse_line_kind`, `verse_line_order_key` (`scheme.py` ~272–310) and their TS twins `isVerseLineRange`/`verseLineOrderKey` (`citation.ts` ~317–331). Byte-identical regex sources in both files, `[0-9]` not `\d`, with parity tests as CPR does for `_FLAT_COLUMN_RE`.
- Manifest keys reused from DRN (`manifests/de-rerum-natura.yaml`, `stage1_latin._parse_verse`): `citation.lacunae` (by content `* * *`, bidirectional gate), `citation.transpositions` (required, may be empty, fail-closed), `citation.fingerprint` (re-export tripwire), `citation.title_labels` (hash-declared `<l n="t">` header drops).
- `GreekLine.ref?: string` (printed lineref, for suffixed lines like 47a) added ONLY if the P1 `<l n>` census shows non-integer tokens; otherwise `line: number` suffices.
- `bookFromColumn()` → null (mirror `makeFlatScheme`, `citation.ts` ~463); `formatLocValue` → "1234"; `parseLocation("1234")` → `{column:'1', line:'1234'}`; `UNIT_NOUN_SINGULAR['play-line'] = 'line'`; `refs.py` `column_key`/`ref_key` dispatch on a `play_line_scheme` property mirroring the `verse_line_scheme` sites.
- **URLs:** reader lives at `/aeschylus/agamemnon` with `?loc=1234` / `#1234` client-side (`[author]/[work]/index.astro` renders the reader for a `books===1` work instead of redirecting to `/book/1`); the static `[cite].astro` shim emits at a stride (every 50 lines + scene boundaries) via a `stride` option in `app/src/lib/citation-routes.ts` — not one page per line (~70k pages otherwise).
- Reader: `const playLine = cscheme.id === 'play-line'`; `.reader-body.play-line` class (hanging indent, lacuna/seam notes, ported from homer's `.verse-line` CSS); generalize the two `stephanus &&` gates in `Reader.svelte` (~1382, ~1438) to `speakerWork = stephanus || playLine`.

### 3. Speakers
- Greek: `stage1_greek._line_with_speakers` (~544) unchanged, called per `<l>` by a new `_parse_play` walker (model: `_parse_flat_stephanus` ~622). Antilabe = speaker event with `offset > 0`, already rendered by `speakers.ts lineRenderParts`. Chorus arrives as `{ΧΟ.}` → ordinary speaker. Strophe/antistrophe or other non-speaker head labels → additive `GreekLine.label?: string` rendered as a centered italic marker (homer's `sigla?` precedent). Stage directions (rare in TLG) → label, never citable text.
- English: per-speech `turns: [{offset, speaker, display}]` on each chunk (the shape `stage1_stephanus_english.py` already emits from `<sp><speaker>`), consumed by `buildEnglishTurnBlocks` unchanged.
- **Speaker colors:** `speaker-colors.ts` hashes displays into 8 slots (`--spk-0…7`); a 10+-speaker play (Orestes, Phoenissae) exhausts it → extend the palette to 12 contrast-checked slots and let the cast list (Landing) and reader share the whole-work roster (`collectDisplayOrder` over all books already guarantees the same hue in both).
- `sigla` maps (Greek siglum → canonical English name, required by stage7's loud roster gate): generate with plato's `gen_speaker_rosters.py` from the built spine + the Perseus `<speaker>` roster; one curation pass for the residue.
- `turnFlow`: emitted for every play; in P2 it is a **diagnostic** (per-play speaker-agreement rate in `build/dist/reports/`), and it is the **alignment spine for every non-lineated bench translation** (§4).

### 4. English ingestion — two builders
- **`stage1_perseus_play_english.py`** (port of homer's `stage1_perseus_milestone_english.py`, 709 lines): pin the walk to column "1", one chunk per play, real gutter ticks from `<l n>` anchors (`anchor_model: sp-line`) or `<milestone unit="line">` (`anchor_model: milestone`) — manifest key `english.<slot>.anchor_model`; Loeb `<note>` → `[^label]` footnotes (`footnotes: true` for Smyth); milestone-anomaly handling and `_nearest_line` carried over. **Gate A per play** (homer precedent): diff the TLG `<l n>` set against the Perseus `perseus-grc2` `<l n>` set and report the delta before ingesting English — Victorian translations track pre-OCT lineation; this is the project's largest alignment risk and its cheapest instrument.
- **`stage1_turn_english.py`** (new; port `turns.py` LCS pairing + the speech walker from `stage1_stephanus_english.py`; overlays injected like plato's `align_turns.py` alt payloads): for speaker-labelled text WITHOUT line numbers — Athenian Society 1912, Rogers, Hickie (non-Perseus plays), Lindsay, Frere, Morshead, Plumptre, Storr, Way, Murray, Potter. Parse Gutenberg/archive.org text into speeches (speaker names in caps at line start), pair against the Greek `<label type="speaker">` sequence, anchor a chunk at each paired turn start; bracketed line numbers in the source become extra anchors. Translation `name` carries "— alignment approximate" (homer's Pope precedent, no new field). Choral odes pair as single Chorus turns.
- Bench manifest shape: `english.primary` (line-keyed) + `english.secondary`/`third`/`overlays[]` each with `model: perseus-play | turn-text`, `source`, `id`, `name`, `year`; the PD allowlist must list every id (fail-closed).

### 5. Registry and data model
- `manifests/authors.yaml`: `aeschylus`, `sophocles`, `euripides`, `aristophanes`, all `period: classical`, `schools: []`, new additive `genre: tragedy | comedy` on Author (NOT `schools`, which would leak into the Lyceum's philosophical taxonomy). Home shelves derive from `genre` (I. Tragedy, II. Comedy) instead of period — DRIFT entry in `works.ts`; the future Lyceum mount supplies the same two groups via `groups.yaml`.
- Work order within an author: production date where secure, TLG order otherwise (the `works:` list is ordered).
- Ids/slugs: `id` = slug, English title where standard (`frogs`, `birds`, `clouds`, `libation-bearers`, `eumenides`), Latin/transliterated where that is the citation norm (`oedipus-tyrannus`, `oedipus-coloneus`, `philoctetes`, `bacchae`, `lysistrata`). Collisions: `electra-soph`/`electra-eur` and `suppliants-aesch`/`suppliants-eur` as ids with slug `electra`/`suppliants`, routes author-scoped (`/sophocles/electra`, `/euripides/electra`), unique in `route-registry.v1.json`.
- Per-work `registry:` block: `workType: verse`, `books: 1`, `bookLabels: ['1']`, `citation: {scheme: play-line, copyAbbr: 'Aesch. Ag.'}`, per-play `greekEdition`/`greekSource`, `translations[]` bench, `blurb` (PV and Rhesus: "authorship disputed" in the blurb, nothing in the data model), optional `accent` token, plus the opening-plate fields (`cast`, `setting`, `production`, `argument`) — human-authored or human-approved copy per CPR's rule.

### 6. Lyceum port readiness (emit from P0)
v1 `manifest.json` per work with `route: /aeschylus/agamemnon` and the `presentation` block; `registry:` blocks + `authors.yaml` consumed by `build-registry.mjs`; stage6-shape search, LSJ shards under the current renderer, structured license records, public-only `build/dist` (all translations PD → `assertNoPrivate` passes by construction); `scripts/emit-wing.mjs` producing the `snapshot.v1` `wings[]` entry (`id: drama`, 44 work ids, start-here picks). The Lyceum then needs only `corpora/drama/mount.yaml` (source `../greek-plays/build/dist`, the standard excludes), `groups.yaml` (Tragedy/Comedy), the snapshot entry, and a copy of `play-line` into its own `scheme.py`/`citation.ts` (a copy, not a merge, because the registries are kept whole).

### 7. Design (Homer-style, John picks)
Process = CPR P4: two or three directions as mockups (Artifact), John picks, direction goes to implementation as a token layer in `shared/styles/global.css` (`:root` / `:root[data-theme="dark"]`, revertible by value swap — homer's Aegean/Wine-dark precedent) + chrome. Drama-specific design points: the per-play opening plate; speaker lead-ins in color; choral odes set apart (indent, strophe/antistrophe markers); line numbers whispering in the gutter every 5; translation picker/compare as a first-class control; a reading mode (single column, one translation) as in Homer; WCAG AA in both themes. Reader chrome: `RunningHead` shows AUTHOR · PLAY as links (LibrarySheet removed), `Breadcrumb.svelte` loses the two `<select>` switchers, `ContentsSheet` stays (scene/ode outline). All reader-facing copy is draft until John approves.

## Phases (each: acceptance first, John's go, gates green)

Common gates: `nvm use 22`; `npx vitest run` in `shared/` and `app/`; `pipeline/.venv/bin/python -m pytest` in `pipeline/`; `npm run build:public` from root run DETACHED (`nohup … &`, one build owner); zero-works build green; `PUBLIC_READER_FIXTURES=1` fixture build green; `build/stage1` is single-work scratch → always `all --work X`.

**P0 — Bootstrap.** Copy/strip/rename per §1; `git init`, `DRIFT.md` with fork SHA, `CLAUDE.md`, `README.md`, `sources/INVENTORY.md`; retarget `shared/__tests__/{works,authors,palette,components}.test.ts` to a zero-works registry (homer's DRIFT lists the set). *Accept:* all gates green with zero works; `node scripts/verify-shared-imports.mjs` clean.

**P1 — Export probe + `play-line` freeze (Agamemnon).** One Diogenes invocation (`-n 0085 -y`); read `authtab.xml` to confirm numbers; answer the probe questions (wrapping div type? `<l n>` grammar census; where `<label type="speaker">` sits; how lacunae/stage directions/choral labels encode). Implement `play-line` in `scheme.py`, `citation.ts`, `refs.py`, `stage1_greek._parse_play`, `stage2_validate`, `stage7_emit`, `preflight.py`, `__main__.py`; `manifests/agamemnon.yaml`; `Reader.svelte` consts + `.play-line` CSS; stride `citationRoutes`; reader at `/aeschylus/agamemnon`. Tests: `pipeline/tests/test_scheme_play_line.py`, `shared/__tests__/play-line.test.ts` (model: homer `verse-line.test.ts`), TS↔Python grammar parity, a real antilabe line, a choral label. *Accept:* `python -m drama_pipeline all --work agamemnon --public` exits 0; `book-1.json` has every line with lineref and `speakers[]`; stage2 `ok`; fingerprint pinned and re-verified on a second export; ⌘K jump to `1234` round-trips; `/aeschylus/agamemnon?loc=1234` lands.

**P2 — Tragedy corpus (33 plays) with primaries.** Three invocations (0085, 0011, 0006); vendor Perseus eng2/grc2 at a pinned SHA; Gate A per play; `stage1_perseus_play_english.py`; PD allowlist with the O'Neill denial; `gen_speaker_rosters.py` pass; 33 manifests + `authors.yaml`. Tests: English builder over a real TEI fixture (anomalies, footnote-label uniqueness), PD gate fail-closed, roster completeness. *Accept:* 33 works build `--public`; Gate A deltas all declared; coverage ≥ threshold with residue in `english.gaps`; speaker-agreement report per play; `build-route-registry.mjs` → 33 unique routes; full `build:public` green; speaker palette holds for the largest cast.

**P3 — Aristophanes (11) + turn-aligned bench.** `stage1_turn_english.py`; `sources/gutenberg/` (#8688/#8689/#7700) and archive.org texts; 11 manifests; benches on the tragedians (Storr, Way, Murray, Morshead… as source quality allows). *Accept:* named-turn pairing ≥ 85% per play (reported); "alignment approximate" labels; compare mode shows ≥ 2 translations on every play; a test asserts an `o-neill` id is rejected by preflight.

**P4 — Design + shell.** Mockup directions → John picks → token layer + chrome + opening plates + no-switcher nav + reading mode; `docs/design-spec.md` rewritten for this site. *Accept:* both-theme screenshots recorded for John; contrast check in CI; the reader has no work switcher; every play page opens on its plate.

**P5 — Hosting + staging (John-gated).** Cloudflare: R2 bucket `greek-drama-reader-data` (rclone sync, CORS, cache-control per CPR `docs/cloudflare-setup.md`), Pages project by direct upload, `PUBLIC_DATA_ROOT` set, `PUBLIC_SITE_ORIGIN` unset until a domain exists; `DEPLOY-STATUS.md` ledger from the first deploy. *Accept:* staging origin serves every play from R2 data; link-integrity 0 broken; size report (est. 100–150 MB data, well inside R2 free tier; Pages artifact well under 20k files).

**P6 — Lyceum handoff.** `emit-wing.mjs` snapshot entry + a written mount note for the CPR repo (`corpora/drama/mount.yaml`, `groups.yaml`, `play-line` copy). *Accept:* the note lists every artifact and the CPR validator passes over the drama `manifest.json` set.

**P7 — Meter (optional, John's call after launch).** Port homer's `apparatus_scansion.py` architecture (syllabifier + quantity rules + relaxation solver, honest `confidence` flags) with an iambic-trimeter solver (12 positions, anceps at 1/5/9, resolutions) and anapests; lyric lines show only the edition's strophe/antistrophe structure, never a computed scan. **Presentation is the point (John: "needs to look really good"):** not Homer's gutter tag. Marks are set directly over the Greek syllables (‒ ⏑ ⏓ in a matching weight, aligned per syllable via per-token spans), foot boundaries as hairlines, resolutions and anceps distinguished, caesura marked, ambiguous scans dimmed rather than hidden; one keystroke toggle; the Greek line's own spacing and click-a-word popups must not shift. It gets its own mockup round in P4's design language before any code, and both themes are checked. *Accept:* ≥ 95% of trimeter lines in a spot-checked play scan "high" against a hand-scanned sample John or Opus checks; John signs the scansion mockup before implementation.

## Verification (end to end)
- Unit: the four gates above after every phase; scheme parity tests; PD gate; roster gate.
- Pipeline: `all --work <id> --public` per play; preflight 0 errors; `verify_shared_lsj` clean; `validate_contracts` over every `manifest.json` + route registry.
- Site: `npm run build:public` detached; `scripts/check-links.mjs` 0 broken; functional checks in the in-app browser (jump to a line, switch translation, compare mode, click-a-word popup on a play line, speaker colors consistent between cast list and text, no switcher present, mobile short-landscape reader intact).
- Data honesty: Gate A report + speaker-agreement report reviewed per play; both-theme screenshots only for John's design review.

## Risks
| Risk | Mitigation |
|---|---|
| Translation vs OCT line drift (Smyth/Jebb/Coleridge translate pre-OCT texts) — highest | Gate A per play before English ingestion; declared gaps |
| Export shape unknown until P1 | P1 is the probe; both wrapping-div branches specified |
| Aristophanes per-play editions | per-work `expected_sourcedesc` FATAL gate |
| Turn-aligned bench quality | ≥ 85% pairing bar, "alignment approximate" labels, residual grouped by scene |
| O'Neill 1938 reached for by mistake | fail-closed allowlist + written DENIED entry |
| Suffixed/non-monotonic choral numbering | census decides `GreekLine.ref?`; lacunae/transpositions gates |
| `[cite]` page explosion | stride routes + `?loc=` reader |
| Speaker palette exhaustion | 12-slot palette, whole-work roster |
| Build time / R2 size | detached builds; est. 15–30 min, 100–150 MB |

## Open for John (not blocking P0–P1)
Design direction (P4 mockups) · which bench translations ship in wave 1 per play · PV/Rhesus blurb wording · domain and launch timing · P7 meter go/no-go.

## Critical files to reuse
- `classical-philosophy-reader/pipeline/reader_pipeline/{scheme.py, stage1_greek.py, turns.py, stage1_stephanus_english.py, stage7_emit.py, preflight.py}`
- `classical-philosophy-reader/shared/lib/{citation.ts, speakers.ts, speaker-colors.ts, works.ts, authors.ts}`, `shared/components/{Reader.svelte, RunningHead.svelte}`, `app/src/components/Breadcrumb.svelte`, `app/src/lib/citation-routes.ts`
- `homer-reader/pipeline/homer_pipeline/{stage1_perseus_milestone_english.py, public_domain_translations.yaml, apparatus_scansion.py}`, `homer-reader/DRIFT.md`, `homer-reader/shared/__tests__/verse-line.test.ts`
- `plato-reader/pipeline/gen_speaker_rosters.py`, `plato-reader/pipeline/plato_pipeline/align_turns.py`
- `classical-philosophy-reader/{docs/tlg-phi-export.md, docs/cloudflare-setup.md, manifests/de-rerum-natura.yaml, schemas/*}`
