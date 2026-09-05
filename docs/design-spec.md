# Lyceum Reader — Design Spec

**Status: DRAFT. Not signed.** Records design direction John has already
ruled on (`LYCEUM-READER-SPEC.md` §P4 design log, 2026-08-27) plus the
mockup he approved as the pair's design of record. It transcribes rulings
into a buildable contract — it does not invent new design. Stops being a
draft, and this line changes, only when John signs it.

Source of the rulings: `LYCEUM-READER-SPEC.md` §P4. Source of the pixels:
the "Lyceum Home and Catalog" mockup, Round 5 ("the pair"), Artifact
`3ac32e78-1609-4a6a-8b5d-80467befa3b8`. Where this document and the mockup
disagree, the mockup wins and this document has a bug — flag it.

## 1. Scope

**In scope:** the site shell — sitewide chrome bar, homepage (cover band +
paper), Catalog page, wing/collection theming, and the shared behaviors
that hold across every page (nav, search, citation jump, settings, theme,
mobile).

**Out of scope:** the reader interior — parallel Greek/Latin + English
columns, word popups, the TOC sidebar, lemma pages. Governed by the
existing `shared/styles/global.css` and `ReaderShell.astro`, unchanged
here. "Follows the spec" means: every shell surface (chrome, homepage,
Catalog, future P5 wing landings) matches §2–§7; the reader interior is
untouched.

Also out of scope: P5 surfaces the Round-5 mockup doesn't show (wing
landings, work preview pages, faceted-catalog UI, curated-path pages).
P5 gets its own pass against this token set when built.

## 2. Tokens

Two token families coexist in `shared/styles/global.css`: **reader
tokens** (lines 19–95, unchanged) govern the interior; **shell tokens**
(new, below) govern chrome/homepage/Catalog. Same file, same
`:root` / `:root[data-theme="dark"]` mechanism, two palettes.

### 2.1 Reader tokens (existing — reference only)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--col-bg` | `#f5f6f2` | `#171d1e` | reader page background |
| `--page-bg` | `#eceee7` | `#101415` | reader gutter background |
| `--text` | `#171a1c` | `#dde4e3` | reader body text |
| `--text-mid` | `#545b5c` | `#a2adac` | reader secondary text |
| `--accent` | `#1f6f7a` | `#4fb8c4` | reader links/accents (teal) |
| `--border` | `#d4d8d3` | `#2a3334` | reader hairlines |

The shell does not reuse `--accent` — the ink/paper/bronze/laurel system
below is a separate palette, the way a book's cover differs from its page.

### 2.2 Shell tokens (new)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#f8f6f0` | `#131414` | shell page background |
| `--paper-raised` | `#fdfcf8` | `#191b1b` | raised panels on paper |
| `--ink` | `#17191a` | `#e6e6e1` | shell primary text |
| `--ink-mid` | `#575d5f` | `#a4aaa7` | shell secondary text |
| `--ink-faint` | `#878d8f` | `#7c827f` | shell tertiary text, counts |
| `--hairline` | `#17191a1a` | `#e6e6e124` | shell rules/borders |
| `--bronze` | `#8a6d3d` | `#c2a469` | reference accent (institute link, tool labels) |
| `--laurel` | `#2f6b4f` | `#6fae8f` | Greek wing accent |
| `--brick` | `#9c3b2e` | `#d08a77` | Roman wing accent |
| `--navy` | `#274b6d` | `#86a5c9` | American wing accent (reserved) |
| `--chrome-bg` | `#efede6` | `#1b1d1d` | sitewide chrome bar background |

### 2.3 Cover-band tokens (homepage only)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--cover` | `#1d4636` | `#122d22` | **PROVISIONAL** — cover band background |
| `--cover-text` | `#f2ead8` | `#ece5d3` | cover primary text (h1, lede base) |
| `--cover-soft` | `#c8d5c4` | `#a8b8a6` | cover secondary text (lede, "soon," counts) |
| `--gilt` | `#c9a44a` | `#c9a44a` | cover accent — institute label, wing-group labels |

**`--cover` is PROVISIONAL** — John: "not sure if green is the right
color, but let's stick with it for now" (design log, 2026-08-27). Ships as
laurel green now; expect it to change. Nothing downstream hardcodes
`#1d4636` — reference the token.

### 2.4 New font token

| Token | Value | Use |
|---|---|---|
| `--font-shell-sans` | `"Public Sans", system-ui, -apple-system, sans-serif` | shell UI text: chrome labels, `.lbl`, tool captions, facet bar |

Additive, not a replacement for `--font-ui` (the reader interior's UI
font). Public Sans loads from Google Fonts alongside Cardo/EB Garamond
(same `<link>`). `--font-greek`/`--font-english`/`--font-latin` are reused
for shell serif text (cover h1, hero duo, ledger names).

### 2.5 Wing/collection color rule

Collection colors — accents, links, section rules — come **only** from
the contrast-checked set in §2.2: `--laurel` (Greek), `--brick` (Roman),
`--navy` (American, reserved), `--bronze` (reference material — not a
wing). No ad hoc hex value for a new wing without adding it here and
passing the check below — the same discipline `speaker-colors.ts` already
applies to per-speaker color (fixed small palette, assigned by key), one
level up at the collection.

**The contrast rule (what the CI gate enforces):** text-on-ground pairs
(body, labels, links, captions) must meet **AA 4.5:1** in both themes.
Large text (≥24px/18.66px-bold) and non-text UI (borders, the 2px ledger
rule, focus rings) need **AA 3:1**. Every wing accent must be checked
against both `--paper` and `--chrome-bg`, in both themes, at its actual
rendered size — the mockup's `.lbl`/`.inst` classes run 0.5–0.6rem, which
is normal-text-sized and needs 4.5:1, not the 3:1 large-text floor.

**Measured against the mockup's current values** (2026-08-28, not yet
wired into CI — the target the future gate checks against):

| Pair | Light | Dark | AA 4.5:1? |
|---|---|---|---|
| `--ink` / `--paper` | 16.3:1 | 14.7:1 | pass |
| `--ink-mid` / `--paper` | 6.2:1 | 7.8:1 | pass |
| `--ink-faint` / `--paper` | 3.1:1 | 4.7:1 | **fails light** (§9) |
| `--bronze` / `--paper` | 4.48:1 | 7.7:1 | **fails light, marginal** (§9) |
| `--laurel` / `--paper` | 5.8:1 | 7.1:1 | pass |
| `--brick` / `--paper` | 6.3:1 | 6.7:1 | pass |
| `--navy` / `--paper` | 8.4:1 | 7.2:1 | pass |
| `--bronze` / `--chrome-bg` | 4.13:1 | 7.1:1 | **fails light** (§9) |
| `--laurel` / `--chrome-bg` | 5.4:1 | 6.6:1 | pass |
| `--cover-text` / `--cover` | 8.9:1 | 11.7:1 | pass |
| `--cover-soft` / `--cover` | 7.0:1 | 7.1:1 | pass |
| `--gilt` / `--cover` | 4.49:1 | 6.2:1 | **fails light, marginal** (§9) |

Three light-mode pairs sit at or under the floor. Not a blocker for
building against this spec; logged as an open item (§9) for John and the
future gate to resolve, not fixed here.

## 3. The lockup

"The Lyceum Reader" over a small "LYCEUM INSTITUTE" line — name first,
institute line second, always in that order, never side by side.

```html
<span class="lock">
  <span class="name">The Lyceum Reader</span>
  <a class="inst" href="https://lyceum.institute">Lyceum Institute ↗</a>
</span>
```

- `.name`: serif (`--font-english`), ~1rem, weight 500.
- `.inst`: `--font-shell-sans`, ~0.5rem, weight 600, letter-spacing 0.3em,
  uppercase; `--bronze` in the chrome bar and footer, `--gilt` in the
  cover band.
- `href` is **always** `https://lyceum.institute`, every instance, no
  exceptions — a real external domain, not an in-app route. `↗` is
  `aria-hidden`; the accessible name is the link text alone.

**Where it appears:** chrome bar (left, every page) and site footer
(homepage now; Catalog and future pages get the same footer in P5). Not
duplicated elsewhere.

## 4. Sitewide chrome contract

The chrome bar is present, identical in structure, on every shell page —
distinct from the reader interior's own header (`ReaderShell.astro`,
unchanged, stays inside a work).

**Fast paths**, left to right after the lockup: continue-reading (if a
saved position exists), Search (⌘K), Catalog, Lexica, Grammars, Sign in.
All render on every page except that a page omits the fast path to
itself (Catalog's own chrome drops "Catalog").

```html
<header class="chrome">
  <div class="in">
    <span class="lock">…as §3…</span>
    <nav class="tools" aria-label="Site">
      <a class="resume" href="{resume-url}">Continue: {work title} {citation}</a>
      <button type="button" class="cmdk-trigger" aria-label="Search (Command K)">
        Search <kbd aria-hidden="true">⌘K</kbd>
      </button>
      <a href="/catalog">Catalog</a>
      <a href="/lexica">Lexica</a>
      <a href="/grammars">Grammars</a>
      <a class="signin" href="https://lyceum.institute">Sign in</a>
    </nav>
  </div>
</header>
```

**ARIA contract:**

- `<header class="chrome">` needs no explicit `role` — as a top-level
  `<header>` it's the `banner` landmark implicitly; don't double it up.
- Fast paths sit in `<nav aria-label="Site">`, distinct from the reader's
  `aria-label="Books"`/`"Chapters"` navs and a future Catalog facet nav.
- "Continue" is a real `<a>` (it navigates), not a button.
- Search is a `<button>` that opens the ⌘K palette in place (matches
  `ReaderShell.astro`'s `aria-label` + `<kbd aria-hidden="true">`
  pattern) — not a link to a `/search` route. A no-JS fallback route is a
  P5 decision.
- "Sign in" is a real external `<a>` to `lyceum.institute` (identity is
  the Manager's, per spec §1/§7 — this repo never implements accounts).
- Any icon-only affordance follows the existing codebase rule:
  `aria-hidden="true"` on the glyph, `aria-label` on the ancestor.

## 5. The homepage grammar

"The cover, then the paper" (John, design log 2026-08-27): a full-bleed
cover band opens onto the paper below. One page, two registers, no
tab/toggle between them — the mockup's `.switch` bar is the artifact's own
review scaffold and ships as neither.

### 5.1 Cover band

Full-bleed (`--cover` background), in order: institute label
(`.inst.lbl`, gilt), `<h1>` "The Lyceum Reader" (serif,
`clamp(2.8rem, 7vw, 4.4rem)`, weight 500 — the page's one semantic h1),
lede (one sentence, `--cover-soft`, max 46ch), wing-grouped destination
nav (§5.2), a closing hairline rule (`--gilt`, 55% opacity).

A large, ~7%-opacity decorative glyph (currently Greek capital `Λ`) sits
behind the text, `aria-hidden="true"` — purely typographic, not a logo,
not the "roundel mark" John rejected. Scales 30rem → 18rem under 900px;
must never occlude text.

### 5.2 Wing-grouped destinations

Grouped, not flat. Order: **GREEK** (Homer, Plato, Aristotle, The
Philosophers, Drama — Plato and Aristotle sit *inside* Greek, not as
their own groups), **ROMAN**, **AMERICAN**, **REFERENCE** (Grammars,
Lexica).

```html
<nav class="wings" aria-label="Collections">
  <div class="wingrow">
    <span class="wlbl lbl">Greek</span>
    <a href="/homer">Homer<span class="ct2">2 WORKS</span></a>
    <a href="/plato">Plato<span class="ct2">18 DIALOGUES</span></a>
    <a href="/aristotle">Aristotle<span class="ct2">THE CORPUS</span></a>
    <a href="/philosophers">The Philosophers<span class="ct2">27 AUTHORS · 62 WORKS</span></a>
    <a href="/drama" class="soon" aria-disabled="true">Drama<span class="ct2">IN PREPARATION</span></a>
  </div>
  <div class="wingrow"> … Roman … </div>
  <div class="wingrow"> … American … </div>
  <div class="wingrow"> … Reference … </div>
</nav>
```

- `.wlbl`: `--font-shell-sans`, gilt, min-width 6.5rem (row alignment).
- A not-yet-open destination (Drama, American) renders `.soon`
  (`--cover-soft`, no wing color) with `aria-disabled="true"` — present,
  visibly and programmatically not a live link. `<a>` vs `<span>` is an
  implementation choice; either is fine as long as it never 404s.
- Group labels are exactly GREEK / ROMAN / AMERICAN / REFERENCE — no
  fifth top-level group without a design-log entry from John.

### 5.3 Paper

Below the cover, in order:

1. **Hero duo** ("Book of the Week") — `.lbl` line naming the work, then
   a 2-col grid (1-col ≤760px): source-language passage (`.gk`, serif)
   beside its English (`.en`, italic, `--ink-mid`), each with a `.ref`
   citation line in the *destination work's* wing color (not hardcoded
   laurel — the mockup's Aristotle example just happens to be Greek).
   Closes with a "Begin … in the {X} Reader →" link.
2. **Reading paths** (`.ways`) — 3-up grid (1-up ≤760px) of named curated
   paths, each with a `--bronze` top border, one-line description, and a
   count/start-point caption. P4 ships the grammar + static examples;
   real curation is P5.
3. **Ledger library** (`.ledger`, repeated) — one block per top-level
   destination. Structure is identical to the Catalog ledger (§6, the
   canonical definition); homepage copies may be previews, each with an
   "enter →" link colored in its wing accent.
4. **Tools trio** (`.toolrow`) — 3-up grid (1-up ≤760px): search,
   citation jump, word lookup. Explanatory copy only, no live controls.
5. **Trust strip** (`.trust`) — one paragraph, `--ink-mid`, max 62ch, top
   border 2px `--ink`, stating the sourcing/verification posture.
6. **Footer** — lockup (§3) left, link row right (`lyceum.institute`,
   About the texts, Attribution, Support the library).

## 6. The catalog page grammar

One page, the full ledger, one click from the homepage. Head:
`<h1>Catalog</h1>` + subtitle + a facet label row (`AUTHOR · COLLECTION ·
PERIOD · LANGUAGE · FORM`) — P4 ships the labels as static text; working
filters are P5.

**The ledger** (canonical structure — also governs homepage previews):

```html
<section class="ledger" aria-labelledby="ledger-philosophers">
  <header>
    <h2 id="ledger-philosophers">The Philosophers</h2>
    <span class="ct">GREEK &amp; LATIN · 27 AUTHORS · 62 WORKS</span>
    <a class="enter" href="/philosophers">enter →</a>
  </header>
  <span class="perlbl lbl">Presocratics</span>
  <div class="row">
    <span class="au">Thales</span>
    <span class="ws">Fragments · Testimonia</span>
    <span class="rng">DK 11</span>
  </div>
  <!-- …repeated per author, grouped under period labels… -->
</section>
```

- **Section rule**: `<h2>` + count sits on a **2px solid `--ink`** bottom
  border — the ledger's heaviest line, matched only by the trust strip's
  top rule.
- **Period labels** (`.perlbl` — "Presocratics," "Sophists," "Hellenistic
  & Roman"): `--bronze`, `.lbl` style, standalone lines, not part of a
  row. Only the DK-numbered philosophers ledger groups by period; Homer/
  Plato/Aristotle ledgers have none.
- **Author rows** (`.row`): 3-col grid `11rem 1fr 9rem` (1-col ≤700px) —
  author (`.au`, weight 500), works (`.ws`, `--ink-mid`), and a
  **tabular-numeral, right-aligned** citation-scheme range (`.rng`,
  `--ink-faint`, `font-variant-numeric: tabular-nums`) — DK number,
  Stephanus, Bekker, book count — never a raw page-count guess.
- A not-yet-joined collection (Roman, currently) gets `.ledger.roman` (or
  future `.ledger.<wing>`), recoloring `.enter` in that wing's accent;
  may read "visit →" instead of "enter →" for an external Institute site.
- Ledger order (both pages): The Philosophers, Homer, Plato, Aristotle,
  Roman, Grammars & Lexica — per the launch chunk order, not alphabetical.

## 7. Shared behaviors

Hold across every shell page and the reader interior; P4 extends their
surface to the new shell pages without changing them.

- **Nav**: every `<nav>` gets an `aria-label`; none unlabeled on a page
  with more than one.
- **Search placement**: the ⌘K trigger sits in the chrome bar (§4) on
  every page, same position, so keyboard muscle memory carries into the
  reader (`ReaderShell.astro`'s own `header-search` keeps its own
  position inside a work — the two are not merged in P4).
- **Citation jump**: `⌘K`'s citation parsing (`citation.ts`, `works.ts` —
  "Eth. Nic. 1094a", "DK 22 B30", "Smyth §2297") is unchanged; the
  homepage tools card (§5.3.4) documents it, doesn't reimplement it.
- **Settings**: reader-interior settings (font size, column width, view
  mode) stay scoped to the reader; no new settings surface in P4.
- **Theme**: `data-theme="light"|"dark"` on `<html>`, set by
  `ThemeInit.astro` pre-paint (`localStorage['ne-theme']`, defaults
  light regardless of OS), flipped by `ThemeToggle.astro` inside a
  `startViewTransition` when available. Shell tokens (§2.2–2.3) use the
  same `:root`/`:root[data-theme="dark"]` mechanism as reader tokens —
  one switch, one state, both palettes.
- **Mobile, including short-landscape**: governed by existing
  `global.css` breakpoints — `max-width: 680px` (portrait) and
  `orientation: landscape and max-height: 500px` (short-landscape, e.g.
  iPhone SE 667×375 — strips secondary chrome text, one-row controls).
  New shell layouts collapse at their own additive breakpoints: `760px`
  (hero/ways/toolrow), `700px` (ledger rows), `900px` (cover glyph).

## 8. Copy rules

Every shell string an agent writes (lede, path descriptions, tool
captions, trust strip, footer links) is governed by this repo's
`CLAUDE.md`: the vocabulary ban (no "frame/spine/slot/chunk/wave/column"
as jargon in reader-facing text) and the human-authorship rule
(agent-drafted copy is DRAFT until John approves it). This spec's own
example copy, quoted from the mockup, is draft under the same rule.

## 9. Open items

- **Cover color** (§2.3) is PROVISIONAL. Not a blocker for building
  against this spec; is a blocker for calling the homepage visually final.
- **Wing color values pending the contrast machinery** — §2.5's table
  shows four light-mode pairs at or under AA 4.5:1 (`--ink-faint`/
  `--paper` 3.1:1, `--bronze`/`--paper` 4.48:1, `--bronze`/`--chrome-bg`
  4.13:1, `--gilt`/`--cover` 4.49:1 marginal). Not this document's call —
  flagged for John and the future CI contrast gate (P4 accept criteria)
  to resolve, either by adjusting the value or by ruling the specific use
  exempt under the large-text 3:1 floor.
- **Brian's feedback round** is pending — per the P4 amendment, he has
  seen no designs yet; this direction goes to him after John signs it.
  Implementation starts only after that.
- **Naming decisions pending John**: the route paths used as examples
  (`/philosophers`, `/homer`, `/lexica`, `/grammars`) are illustrative,
  not ruled — actual route registry entries are a P5/route-registry call.
- **Drama shelf-vs-wing** and the other §8 open decisions in
  `LYCEUM-READER-SPEC.md` stay unresolved here too; §5.2 lists Drama
  under Greek "in preparation" per the current mockup without prejudging
  that call.
