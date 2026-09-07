# The Greek Drama Reader — CLAUDE.md

Static Astro + Svelte site: parallel Greek/English reader for the 44 complete Greek plays (Aeschylus 7, Sophocles 7, Euripides 19, Aristophanes 11), with a bench of public-domain translations per play for side-by-side comparison. Repo lives at `~/Developer/greek-plays`. Forked 2026-09-05 from `~/Developer/classical-philosophy-reader` (the Lyceum seed; fork SHA in `DRIFT.md`) with verse/English machinery ported from `~/Developer/homer-reader` and speaker tooling from `~/Developer/plato-reader`. Sister repos are READ-ONLY from here. Node 22; Python pipeline `pipeline/drama_pipeline` via its `.venv`. Plan of record: `~/.claude/plans/using-the-aristotle-reader-delightful-sky.md` (copied to `docs/plan.md` at P0).

Later this corpus mounts into the Lyceum Reader as the Drama wing (`corpora/drama/`), so it keeps the Lyceum contracts: `schemas/`, `registry:` blocks in `manifests/*.yaml` + `manifests/authors.yaml`, the generated registry, v1 `manifest.json` per work, the route registry.

## Hard rules

- Greek source is TLG (licensed, local, Diogenes-readable, `-y` verse export). **Corpus source text is never committed.** Never modify `/Applications/Diogenes.app`.
- Website translations: public-domain only, judged by **US** rules (pre-1931 as of 2026). The PD allowlist (`pipeline/drama_pipeline/public_domain_translations.yaml`) is fail-closed; **Eugene O'Neill Jr.'s own 1938 Aristophanes translations (Perseus's default English) are DENIED.** A PD text as hosted by a reputable site (Perseus, MIT Classics) is used as hosted, later editorial edits included (John, 2026-09-05; the MIT Classics precedent). Copyright rulings are John's.
- **Aristophanes is unexpurgated** (John, 2026-09-05): the 1912 Athenian Society *Eleven Comedies* is primary; bowdlerized versions (Rogers, Hickie) ride only as comparison slots.
- **No play-switcher inside the reader** (John): the running head's author and play are links back out; no `<select>` switchers, no library sheet.
- **Transposed lines keep the edition's printed order** (John, 2026-09-05): a line the editor moved (Ag. 1290 printed before 1284) stays where it is printed, numbered as printed; never re-sort into numeric order. `citation.transpositions` is a validator allowlist, not a reorder instruction. Flagged in `REVIEW-CHECKLIST.md` for John's review at the complete build. The same posture for a ref the edition prints twice (Septem 803/810 doublet, Helen's two lacunae at 1226, Troades' split 170): declared in `citation.repeated_refs`, printed as is, never merged or renumbered.
- Speaker attribution in color (Plato reader's `speaker-colors.ts`), stable per character across every column.
- Deploying is John's call — never deploy without explicit go-ahead. Hosting: Cloudflare Pages (app) + R2 (data) via `PUBLIC_DATA_ROOT`; free tier; surface anything that would cost money BEFORE doing it. `PUBLIC_SITE_ORIGIN` stays unset until a real domain exists (never bake `*.pages.dev`).
- Verify functionally, not with screenshots (screenshots only for John's design review, both themes).
- All data fetches go through the `data.ts` data-root override.
- Reader-facing copy (blurbs, plates, landing prose) is DRAFT until John approves it.
- Commit as you go once gates are green; push to a `claude/` branch promptly in worktrees. Main-branch merges, deploys, money, naming/domains, copyright, canon calls route through John.
- Maintain `DRIFT.md`: one line per shared-core file diverged from the fork point, same commit.

## Build & verify

- `nvm use 22` before any npm/vitest/astro command (system node is v24).
- Gates: `npx vitest run` in `shared/` and `app/`; `pipeline/.venv/bin/python -m pytest` in `pipeline/`; `npm run build` in `app/` (zero-works build must stay green); `PUBLIC_READER_FIXTURES=1` fixture build; `npm run build:public` from the root is the ship gate — it exceeds the 10-min tool timeout, run it detached and never start a second build while one runs.
- `build/stage1` is single-work scratch: always `all --work <id>`, never a lone later stage.
- TLG export recipe: `docs/tlg-phi-export.md` (Diogenes 4.7.2 native `-y`; one invocation per author: 0085, 0011, 0006, 0019; scratch prefs dir pointing at `~/Documents/CLAUDE CODE ARISTOTLE PROJECT/TLG Files/TLG`).
- Work numbers come from `TLG Files/TLG/DOCCAN2.TXT` / the export's `authtab.xml`, never guessed: Aeschylus 001–007, Sophocles 001–007, Euripides **034–052** (052 = Rhesus), Aristophanes 001–011 (editions differ per play — per-work `expected_sourcedesc`).

## Orchestration

Fable is the orchestrator; the global `delegate` skill governs spawns (pass `model:` explicitly; cross-family verification; 5-agent cap). Philological judgment (lineation, sigla, meter) goes to Opus; repo lore and taste stay on Claude; adversarial review before John's gates goes to Codex/Grok. Karpathy's rules (global CLAUDE.md) bind every brief.

## Working with John

Philosophy professor, competent Greek. He wants this site to be amazing: design is a first-class phase with mockups he picks from, and the scansion feature (if built) must look genuinely good. Explain architecture decisions; check in at milestones, not every step.

## Dictionary (John, 2026-09-05): Grammata T8 for ALL LSJ on the site

Every LSJ entry the site shows — the word popup AND the `/lemma` pages — is served by Grammata's T8 lookup (`https://grammata.pages.dev/t8/lookup.js`, `lookup(word, el, { lang: 'grc', key })`), never rendered from local shards. Do not vendor, pin, proxy, cache-bust or restyle the module: one grammata deploy updates every reader site (architecture decided 2026-08-29, aristotle-reader HANDOFF-LSJ §0–1). The site ships no LSJ shard HTML; it ships only `data/lsj-heads.json` (headword + homograph letter, aristotle `app/scripts/build-lsj-heads.mjs`) so cards are keyed by dictionary entry. Pipeline stage5 may still emit shards for the desktop/Lyceum mount; the web build must not fetch them.
