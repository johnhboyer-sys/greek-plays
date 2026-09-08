# P4 — the skin: implementation plan (design settled 2026-09-08)

The design is decided: the round-2 blend, `docs/mockups/2026-09-08-blend.html`
(artifact https://claude.ai/code/artifact/fe79e172-4db2-4ed6-832d-8dd7023fe603).
That file is the visual spec. Rulings behind it, all John's, 2026-09-08:

- Palette B (cool vellum ground, iron-gall ink, speaker colours from
  scriptorium pigments); rubric red is tragedy's accent, malachite comedy's;
  accent BY GENRE (never by author). Dark theme: deep grounds, the lightened
  accents for text only, bands keep a deep colour (never the lightened accent).
- Type: Cardo for everything a reader reads — Greek, English, titles, speaker
  lead-ins (small caps). A sans (Alegreya Sans SC) for everything a reader
  operates — running head, controls, compare labels, line numbers stay Cardo
  italic. "Cardo is great for body text and titles, but not menu options."
- Running head as in directions A/C: site name small, AUTHOR · PLAY as links
  back out (no switcher), controls right, a 2px genre-accent rule beneath.
- Plate (the play's opening screen): A's band on B's body. Band in the genre
  colour: Greek title large, English title small caps, author italic. Below,
  in ink: the one-line argument (DRAFT, coloured initial), PERSONS in order
  of appearance with coloured initials and an optional note each, a margin
  column of scholia-style notes (Production, Greek text, Translations, Cite
  as), and "Start reading →". No "how to read this" note. Plain words only:
  "Translations", never "bench"; "by speech", never "alignment approximate".
- Dialogue: both columns share ONE left structure: line-number gutter,
  speaker gutter, text. The Greek siglum and the English name hang in the
  speaker gutter at the same indent. The Greek speaker gutter is sized for
  sigla (~3.4rem), the English one for names (~7.5rem), so the Greek verse
  starts closer to its gutter than the English prose does (John, 14:47:
  "too much space between gutter and the greek").
  Every English turn sits on the row of the Greek line it starts on; turns
  that begin mid-line (antilabe) stack in that line's row; a mid-line speaker
  change stays inline in the Greek. Columns align on the first baseline.
  NO horizontal rules between turns. No ornament anywhere.
- Odes: a narrower measure (the lyric set apart), nothing else.
- Compare: three plain columns, Greek widest (1.5 : 1 : 1), NO boxes or
  panels; the ode/section heading sits inside the Greek column level with the
  translator labels ("Smyth · 1926 · by line", "Morshead · 1881 · by speech");
  each column's speaker label is a block above its text; no indent below.
- Greek-only mode: one centred reading column (~34em), larger Greek.
- Comedy dress = the same skin with the comedy accent: the plate band and the
  running-head rule go malachite.

## Lanes (each: acceptance first, gates green, cross-family read, commit)

### Lane A — reader layout (Opus; Reader.svelte + play-line CSS)
Per-line turn rows, the shared speaker gutter, unboxed compare with the
Greek widest and block labels, the ode measure, no rules. Data contract
unchanged (book-01.json as built). Acceptance in the brief.

### Lane B — tokens, chrome, plate (Opus, after A lands)
Token layer in `shared/styles/global.css` (`:root` / `[data-theme="dark"]`,
value-swap revertible), fonts (Cardo + Alegreya Sans SC via Google Fonts in
ReaderShell), `data-genre` on `<html>` from `authors.yaml` → `--accent`,
RunningHead restyle, the Plate component at the top of the play-line reader
page (deep links with `?loc`/`#` scroll past it), speaker palette to the
pigment set (12 slots, AA on both grounds).

### Registry content (orchestrator, manifests only, in parallel with A)
`greekTitle` for the eleven comedies; new registry keys `production` (festival,
date, prize — facts, with "date unknown" where it is) and `argument` (one
line, DRAFT until John approves) on all 44; `Work` type + registry
passthrough. No copy ships un-approved: the plate marks DRAFT copy as such.

### Verification
Gates after every lane: `shared` vitest, `app` vitest, pipeline pytest, `npm
run build` (1,272 pages), fixture build. Grok static read of each lane's diff.
Both-theme screenshots of the Agamemnon plate, Ag. 1203–1213, the parodos
in compare, and Frogs 1–15 for John's review at the end of Lane B.
