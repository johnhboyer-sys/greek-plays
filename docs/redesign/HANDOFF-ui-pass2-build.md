# Handoff: UI second pass, building direction B "The Vase" (2026-10-20)

For the session that builds the chosen design into the Astro app. John chose
direction B on 20 October 2026 and settled every page type the same day. This
file is the spec. The mockup is the reference; where this file and the mockup
disagree, the mockup wins, except where a ruling below says otherwise. Where
this file says "John's call", ask him in chat before building; never guess.

## 1. Status and what you are building

- Branch `claude/ui-pass2` (worktree `.claude/worktrees/ui-pass2`), cut from
  the first overhaul pass `claude/project-thread-8ykl6l` (13 October,
  `docs/redesign/HANDOFF-overhaul-pass1.md`). `main` is 54 commits ahead
  (drawings, CI); merge it first (§2).
- The mockup: `docs/mockups/2026-10-20-directions/`. Open `index.html` in a
  browser (the figures are missing until you run `make-masks.py`, which needs
  `rsvg-convert` and Pillow; the layout and type show without them). Keys:
  `2` = direction B, arrows = pages, `t` = theme, `p` = phone. The right-hand
  panel on each page carries John's rulings for that page.
- Source of truth for every measurement: `style.css`, the block that starts
  `/* B · The Vase */` (`.dir-b` rules, the `@container mock (max-width: 700px)`
  block is the phone), plus `.dir-b .pg-search` and `.dir-b .wp`, and the shared
  `.rd-*` reader rules near line 149. Markup: `app.js`, the `T.b.*` templates,
  `bHeadOf`, `readerRows`/`row`, `PANEL`. Data: `data/works.json` (derived
  from the manifests; the app reads the manifests directly), `data/samples.json`
  (Medea 1116–1180 in Murray 1902 and Coleridge, open texts from Perseus).
- Every page type is decided: home, author, play, reader, search, word panel.
  Reader tweaks may still come from John while you build; take them as they
  arrive.
- John's own words for each ruling are in the commit messages on the branch
  (`git log claude/ui-pass2 -- docs/mockups/2026-10-20-directions`), and the
  key ones are quoted in §12.

## 2. Branch, process, gates

1. `nvm use 22`. Merge `main` into `claude/ui-pass2` and get every gate green
   before touching the UI: `npx vitest run` in `shared/` and `app/`,
   `pipeline/.venv/bin/python -m pytest` in `pipeline/`, `npm run build` in
   `app/`, the fixture build (`PUBLIC_READER_FIXTURES=1`). The ship gate
   `npm run build:public` from the root exceeds the tool timeout: run it
   detached, never two at once.
2. Commit as you go once gates are green; push the branch. Never merge to
   `main`, never deploy, never spend money: those are John's.
3. Every rule in the repo `CLAUDE.md` stands: TLG Greek never leaves the
   machine (screenshots and anything shared use the open editions in
   `app/public/data/<work>/ed/`); Grammata's T8 module is used as it comes and
   never restyled, vendored or proxied; no play switcher in the reader; speaker
   colours stable per character; transposed and repeated lines as printed;
   reader-facing copy is DRAFT until John approves it, so use the manifest
   fields and write no new copy; `DRIFT.md` gets a line for every `shared/`
   file you change; Oxford commas.
4. Orchestration (`CLAUDE.md`): pass `model:` on every spawn; implementation
   and verification never share a model family; adversarial review by Codex or
   Grok before John's gate. Load the global `delegate` skill before the first
   spawn.
5. John reviews by screenshots, both themes, 1440 and 390 wide, at milestones
   (§10), not by watching. Verify everything else functionally.
6. Pass 1's open items stay open unless you touch the code they live in
   (`HANDOFF-overhaul-pass1.md`, Reviews): the long first speech inside a
   multi-speaker segment on a phone; the `phoneLayout` first-paint flash;
   re-grouping on rotation.

## 3. The design, in one page

B is the vase: black, clay, and paper, and one ground line. Everything on the
site stands on, or hangs from, a single 2px line in ink. There are no other
rules, no boxes, cards, shadows, tints, or colour fields anywhere. The only
exception is the edge John picks for the reader's drop-down (§7.5).

### 3.1 Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| paper | `#f3ecdf` | `#15110f` | page and menu backgrounds |
| ink | `#171310` | `#efe6d6` | text, the ground line, figure lines (light) |
| mid | `#6b5f52` | `#b3a594` | secondary text, controls at rest, icons |
| line | = ink | = ink | the 2px ground line |
| clay | `#c8743f` | `#c8743f` | figure bodies, hover |
| clay-deep | `#a85a2b` | `#d9895a` | Greek titles and names, the current item, line numbers, chevrons |
| fig-body | `#c8743f` | `#c8743f` | the `body` path of every drawing |
| fig-ink | `#171310` | `#15110f` | the `lines` path of every drawing (dark: the paper colour) |

Contrast, measured: ink 15.7:1 and mid 5.3:1 on light paper; clay-deep on
light paper is **4.29:1**, which passes AA only for large text. The mock uses
clay-deep for the reader's line numbers (0.72rem) and for small links
("Full synopsis", "choose plays", chevrons). Candidates that pass for small
text: `#9d5226` (4.87:1), `#964e24` (5.24:1). John's call: a darker clay for
small text, or mid for the numbers. In the dark theme everything passes
(clay-deep 6.9:1, mid 7.8:1). The mock's `--purple` is unused; drop it.

Pass 1's author tints (`DESIGN.md`, Author tints) and its Attic orange
`#d4875a` are superseded: no tints on any page, figures in clay.

### 3.2 Type

- Cardo for everything readers read: Greek, English, titles, names, the site
  name, the reader's picker labels. Alegreya Sans only for controls, labels,
  counts, dates, and notes under things. Alegreya Sans SC stays loaded for
  the shared components; B uses no heavy sans and no second serif.
- Google Fonts as the app loads them today (`search.astro` has the link).
- Body text: 1.15rem / 1.62 in both reader columns, Greek and English the
  same size and the same ink. English is never smaller than the Greek.
- Sizes per page are in §4–§8; the stylesheet has the rest.

### 3.3 Figures

Every drawing is the SVG from `docs/redesign/drawings/`, drawn through the
existing `Figure.astro` / `lib/drawings.ts` / `pages/drawings/[name].svg.ts`
path (`<use>` of `/drawings/<name>.svg#fig`). The SVG's `lines` path takes
`currentColor`; its `body` path takes `--fig-body`; `tone` paths keep their
own opacity. Set `color` to fig-ink and `--fig-body` to clay, in both themes.
The dark theme is the black glaze: clay body, lines in the paper colour, so
the figure reads as red-figure. The mock's PNG masks (`make-masks.py`) were
only a way to colour the SVGs inside one HTML file; do not use them.

Whole figures only, standing on the line, never cropped, never shrunk below
the sizes in §4–§6 to fit a column: the columns size to the figures. No
small silhouettes anywhere (John rejected the bands). Where a play has no
drawing yet, leave the same height empty, as pass 1 does.

Which drawing stands for which author and play comes from `drawings.json`
and `research/play-image-plan.json` on `main` after the merge (home figures
by author id; author-page figures: Aristophanes' home figure is the king, his
author page shows the Getty krater, see the commit `d6d7d77`). The mock's
`HOME_FIG`/`AUTHOR_FIG` were stand-ins.

### 3.4 Chrome, on every page

- Head: the site name, "The Greek Drama Reader", in Cardo 1.35rem ink, a link
  home. At the right, two icons and nothing else: a magnifier (search) and a
  half-filled disc (dark or light). Inline SVG, 19px, stroke 1.5 in
  `currentColor` (mid), clay on hover, `aria-label` "Search" and "Dark or
  light". No words "Search" or "Dark", no Resume, no "All works", no
  "Lexicon" in the head. The icon markup is `ICO` in `app.js`.
- On play pages the head reads "The Greek Drama Reader · Euripides", the
  author's name a link to his page, in mid, Cardo 1.35rem (§6).
- On phones the author and play pages (and the reader) use the stacked site
  name: two lines, "The Greek" over "Drama Reader", 0.72rem, line-height
  1.05. The home and search pages keep the one-line name on phones.
- Foot: "Search the plays · Greek lexicon · Texts and licences · Support",
  Alegreya Sans 1rem mid, wrapping; `margin: 3.5rem 0 3rem`.
- No site description anywhere ("We don't need to say what the site is").
  Pass 1's home intro line goes.
- No Greek in chrome: running heads and search headings carry English
  titles only. Greek titles belong on the play page and in author lists.
- Never write "the reference Greek" or "reference text" in copy; name the
  editor ("with Paley's Greek"). The picker's control label "Reference text"
  from the shared reader is the one allowed use, as a control, and B does
  not use it.
- No sideways scrolling anywhere, at any width: rows wrap.
- The page content sits in `.wrap`: max-width 86rem, padding 0 3rem (phone
  0 1rem).

## 4. Home

Reference: `T.b.home`, `.dir-b .frieze`, `.dir-b .nm`, `.page .contents.runs`.

Desktop:

- Head (§3.4). No intro line.
- The frieze: four columns, one per playwright, in a grid whose column
  widths are each figure's aspect ratio in `fr` (`friezeVars()` in `app.js`:
  `--cols`, `--sum`, `--pairmax`), so all four figures stand at ONE height,
  `--h: min(300px, (100cqw - 10rem) / sum-of-ratios)`, and no figure is ever
  shrunk to a quarter. Each column: the figure box `height: h + .6rem` with
  the 2px ground line as its bottom border, the figure flush on the line,
  centred. The four boxes touch, so the line runs the width of the page.
- Under each figure, centred: the Greek name (Cardo 1.5rem, clay-deep), the
  English name (Cardo 2.8rem, ink, a link to the author page), the count
  ("7 plays", Alegreya Sans 1rem, mid).
- Under the names, the plays as a RUN of titles: one paragraph per author,
  comma-separated English titles, each a link in ink, Cardo 1.02rem / 1.45,
  centred, `max-width: 16em` so it wraps into several lines (Euripides' 19
  over about seven), no Greek titles, no list. The runs sit in the same
  grid columns as the frieze (no column gap) so each run is centred under
  its name. Every title is listed, never a sample.
- Foot (§3.4).

Phone (390): the frieze two by two (`--h: min(170px, (100cqw - 3rem) /
pairmax)`, row gap 1.6rem); names 1.15rem / 1.7rem; the runs one column, full
width, each led by the author's name in mid ("Aeschylus: Persians, Seven
Against Thebes, …"). The whole page was 1177px tall in the mock; keep it near
that.

App: replace `ClassicHome.astro`'s frieze and resources block. Pass 1's
"Resources" and "collections" under the frieze: collections are still open
(DESIGN.md, Still open); the mock shows none. Put nothing there.

## 5. Author page

Reference: `T.b.author`, `.dir-b .pg-author`.

Desktop:

- Head (§3.4).
- Hero: a grid `1fr 24rem`, column gap 3rem, `align-items: end`, margin-top
  2.2rem, areas `"hx lead" / "ab lead"` with rows `1fr auto`. Left, bottom-
  aligned: the Greek name (Cardo 2.2rem, clay-deep), the English name (Cardo
  5rem / 1), the dates and count ("c. 480–406 BC · 19 plays", Alegreya Sans
  1.1rem, mid), then the blurb from `manifests/authors.yaml` (Cardo 1.35rem,
  max-width 30em). Right: the author's figure at 360px on its own ground
  line (the 2px border under the 24rem column only; the text column has no
  line), bottom-aligned with the text.
- The list of plays: `columns: 2; column-gap: 4rem; margin-top: 2.6rem`,
  each play `break-inside: avoid`, padding `.6rem 0 .9rem`: the English title
  (Cardo 1.7rem, a link to the play page), the Greek title after it (Cardo
  1.2rem, clay-deep), the blurb (1.12rem / 1.45, max 34em), the production
  note (Alegreya Sans .92rem, mid). The manifests supply all four.
- Foot.

Phone: the hero grid `1fr 8.5rem`, areas `"hx lead" / "ab ab"`: the name
block (Greek 1.4rem, English 3rem, dates) beside the figure at 180px, the
block bottom-aligned and SHORTER than the figure; the blurb (1.1rem) under
both at full width. Nothing beside a figure may rise above the figure's top
(John, 20 October). No ground line under the phone figure (the mock sets
`border-bottom: 0` there). The list in one column; titles 1.45rem, Greek
1.05rem, blurbs 1.05rem; production notes hidden.

App: `pages/[author]/index.astro`, `lib/author-groups.ts`. Open, John's call
(§11): the mock's list is flat and in the manifest's order; pass 1 groups the
Oresteia and the Oedipus plays first with notes, and has the "Titles only"
toggle and "Find a play" on Euripides. Ask whether the groups, the toggle,
and Find a play survive inside the two-column list.

## 6. Play page

Reference: `T.b.play`, `bPlayBody`, `.dir-b .pg-play`. The play page is its
own page at the bare play URL (§9), for readers and for search engines. It
carries no lines of the text ("pointless").

Desktop:

- Head: "The Greek Drama Reader · Euripides" + icons.
- The scene: the play's whole drawing, centred, at 460px, on a ground line
  the full width of `.wrap` (`height: 460px + .5rem; border-bottom: 2px`),
  margin-top 1.4rem. `max-width: 100%` (a wide scene shrinks to the width,
  still whole; it is never cropped or pushed to one side).
- Title block, a grid `1fr auto`, `align-items: end`, gap 2rem, margin-top
  1.5rem. Left: the Greek title (Cardo 3rem / 1, clay-deep), then the
  English title (Cardo 3.6rem / 1, margin-top .25rem). The Greek is five
  sixths of the English ("slightly smaller font"). Right, bottom-aligned:
  "Euripides · first staged City Dionysia, 431 BC, third prize, behind
  Euphorion and Sophocles" (Alegreya Sans 1.25rem, mid; the author's name a
  link in ink; the production text from the manifest).
- The argument, one sentence from the manifest: Cardo 1.5rem / 1.4, max 32em,
  margin-top 1.4rem.
- Three columns, `1.1fr 1.2fr 1fr`, gap 3.5rem, margin-top 2.6rem, each with
  a heading in Alegreya Sans 1rem mid:
  1. "Persons, in order of appearance": each row a grid `3.2rem 1fr`, the
     Greek siglum in the speaker's colour, then the name (Cardo 1.15rem /
     1.55). Colours from `shared/lib/speaker-colors.ts` by roster slot
     (`lib/speaker-roster.ts`).
  2. "Translations": each a link into the reader (Cardo 1.15rem, ink) with a
     line under it in Alegreya Sans .92rem mid: form · year · "aligned by
     line" or "aligned by speech" · "with Paley's Greek" (the editor the
     translation pairs with; where the repo records none, the play's first
     Greek text). Years only where the repo holds one (DESIGN.md, Data to fix).
  3. "Greek texts": each edition's name (Cardo 1.05rem, a link into the
     reader in Greek view with that edition) and its year (Alegreya Sans
     .92rem mid). Under them "Cite as Eur. Med. 1–1419" in the facts style
     (Alegreya Sans 1rem / 1.45, mid, the label in ink 500).
- `<details>` "Full synopsis (tells the ending)": summary in Alegreya Sans
  1.05rem clay-deep; the synopsis in Cardo 1.1rem / 1.5; max 40em.
- The drawing's credit: Alegreya Sans .85rem / 1.4, mid, max 44em: "Drawing:
  " + the SVG's `<desc>`.
- Foot.

Phone: the scene at 220px; the title block in one column (English 2.4rem,
Greek 2rem); the argument 1.2rem; the three columns stacked, gap 1.6rem; the
stacked site name with "· Euripides" beside it, icons at the right.

No buttons. The translations are the way into the reader. Resume: DESIGN.md
wants a Resume line where a saved place exists; the mock has none. John's
call (§11): a plain link under the argument, "Resume at 1116" (DRAFT), or
nothing.

App: `components/Playbill.astro` becomes this page; `pages/[author]/[work]/
index.astro` renders it alone (today it renders the reader with the playbill
above line 1).

## 7. Reader

Reference: `T.b.reader`, `bMenus`, `readerRows`/`row`, `.dir-b .pg-reader`,
the shared `.rd-*` rules, and `PAGE_NOTES.reader.b` in `app.js`.

### 7.1 The running head

One line on the desktop, sticky at the top, paper background, the 2px ground
line as its bottom border, `padding: .7rem 2rem 0`, `align-items: flex-end`,
gap 1.6rem. No figure, no line counter, no shadow.

- Left, Cardo 1.15rem: "The Greek Drama Reader" (mid, a link home) · "Euripides"
  (ink, a link to the author page) · "Medea" (clay-deep, a link to the play
  page). All three links; the site name was missing from pass 1's reader and
  John asked for it.
- Right (`margin-left: auto`, Alegreya Sans 1rem, mid, the current item in
  ink), four controls and the two icons:
  1. The picker: "Paley 1878 · Coleridge ▾", Alegreya Sans 1rem like the
     other controls, the chevron `▾` at .7em in clay-deep. The label is the
     Greek edition's short name and year, then the translator's surname. It
     opens the two-column menu (§7.5).
  2. The views: "Greek  Both  English", gap .9rem.
  3. "Aa" (Cardo 1.15rem): opens the text menu (§7.5).
  4. The two icons (§3.4): magnifier → search; disc → theme.
- Phone (390): the head wraps into two lines. Line 1: the stacked site name
  (0.72rem) · Euripides · Medea (1rem), all centred on one midline, and the
  two icons at the right-hand end of this line. Line 2: the picker, the
  views, Aa (0.9rem, gap .75rem, wrapping if it must). The icons are never on
  line 2.

### 7.2 The rows

The text sits in `.rd-wrap`: max-width 80rem, padding `2.2rem 2.5rem 6rem`
(phone `1.2rem 1rem 4rem`). The body is a grid of two columns, `1.05fr 1fr`,
column gap 3rem, one grid row per speech (`.rd-row` is `display: contents`;
`.rd-g` and `.rd-e` are the cells, `padding-bottom: 1.3rem`).

Greek column, one block per line: a grid `2.8rem 1fr` (phone 2.2rem), gap
.6rem, baseline-aligned. The number sits in the LEFT margin column, right-
aligned, Alegreya Sans .72rem, tabular, in `--num` (clay-deep, see §3.1).
Numbers show on every fifth line, on the first line of the passage, and on
any line printed out of order; otherwise the margin is empty. The text is
Cardo 1.15rem / 1.62. The first line of a speech begins with the siglum in
small caps Cardo in the speaker's colour ("Μη."), margin-right .3em.
Antilabe (a line shared by two speakers, `part: 'F'`) indents the second part
by `--part-indent`.

English column: one paragraph per speech, Cardo 1.15rem / 1.62, with
`padding-right: 2.6rem` for the numbers, which sit absolutely in that RIGHT
margin at the translation's own markers (`.rd-e .p .n`), same size and colour
as the Greek numbers. The paragraph begins with the speaker's name in small
caps in the same colour ("Medea."). Translators' stage directions are italic
in mid and marked as the translator's. John: "Let's keep the different
colored speaker labels though."

The Greek and English of each speech start on the same line (DESIGN.md).
Long speeches run as continuous columns on the desktop, no breaks.

### 7.3 Views

Greek, Both, English. Both is the default on every width (pass 1 opens
bilingual on plays). Greek view: the Greek column alone at the same measure,
numbers in the left margin. English view: the English alone, numbers right.
Comparison (several translations side by side) is not in the mock: keep pass
1's behaviour, in B's tokens, labels above the columns as today; stanza
alignment stays open (pass 1 handoff, Next 1).

### 7.4 Phone: speech by speech

In Both view on a phone the body is one column (`.rd-alt`): for each speech
the Greek block, then its English. The Greek keeps its number column at the
left (2.2rem + .6rem), so the Greek stands indented from the English, which
runs full width; this is what keeps them from running together (John,
12:58). A long speech comes in pieces: cut at the translation's own line
markers where the translation is keyed by line, never making a piece under
five Greek lines; a speech-keyed translation stays whole. The first piece
carries the name; later pieces (`.rd-row.cont`) carry no name and no gap
before them. Reconcile this with pass 1's `singleSpeech` cut in
`shared/components/Reader.svelte` (the mock's `readerRows` shows the cut).

### 7.5 Menus

The picker menu, under its control at the right (`top: calc(100% + 2px)`,
right-aligned, `min-width: 40rem`, paper background, `padding: 1rem 1.3rem
1.1rem`, z-index above the text), two columns (`1fr 1fr`, gap 1.6rem):

- "Greek text" (heading Alegreya Sans mid): each edition on its own row,
  the name (Cardo 1.1rem, ink; the current one clay-deep), under it the year
  and, where a translation pairs with it, "the text Coleridge translated"
  (Alegreya Sans .9rem, mid). Under the list a note in .9rem mid, max 24em:
  "Both and English views show each translation beside the Greek its
  translator used. The Greek view takes any edition." (DRAFT copy; the rule
  is John's edition-picker ruling of 28 September: matched pairs in the
  bilingual views, the picker chooses the Greek only when the view is Greek.)
- "Translation": each translation, the name (Cardo 1.1rem), under it form,
  year, alignment, "with Paley's Greek" (.9rem mid). Choosing a translation
  loads its paired Greek text.

The Aa menu (`min-width: 17rem`, right-aligned): heading "Text"; rows with a
3.2rem label in mid and the choices as links, the current one underlined in
ink: Size: Smaller · Normal · Larger; Width: Narrow · Normal · Wide; then
"Print this page". Proposed values (John sees them in the screenshots):
size 1.05 / 1.15 / 1.3rem; width 64 / 80 / 96rem. Persist size and width in
localStorage under drama-scoped keys. Print: a print stylesheet that drops
the chrome and prints the current view with its numbers.

The menu's edge, John's call (§11): the mock offers four treatments,
switchable in its notes panel (`state.menu`; CSS `.dir-b.menu-frame`,
`.menu-sheet`, `.menu-clay`, `.menu-dim`): an ink frame (1.5px ink on all
four sides, square corners); a lifted sheet (a hairline edge, `color-mix(in
srgb, var(--ink) 24%, transparent)`, 2px radius, and a soft shadow); a clay
rule (hairline edge, 3px clay along the top); a dimmed page (hairline edge,
and a fixed scrim of paper at 62% over the page behind). Build the one John
picks; it applies to both menus, both widths, both themes.

Phone: each menu opens as a fixed sheet, `left: 1rem; right: 1rem; top:
6.2rem`, `max-height: calc(100vh - 8rem)`, scrolling inside, the two columns
stacked (gap .8rem). A tap on the control toggles it; a tap elsewhere closes
it (the mock's `stage` click handler shows the toggle).

### 7.6 Word panel

Reference: `PANEL`, `wordPage`, `.wp` and `.dir-b .wp`. Tapping a Greek word
marks it (`mark.w`, a clay-tinted mark) and opens the panel: on the desktop a
fixed column at the right, 23rem wide, full height, paper, the text never
moving; on a phone a sheet from the bottom with a 2px ground line along its
top. The panel scrolls inside itself.

- Head: the tapped word (Cardo 2rem) on its own ground line (the 2px border
  under the head, inset 1.3rem from the panel's sides), a "×" at the right
  (Alegreya Sans 1.4rem, mid).
- The parse: the lemma (Cardo 1.45rem, clay-deep), the gloss (italic
  1.12rem), the morphology in words ("aorist indicative active, third
  singular", Alegreya Sans .95rem mid), "7 places in the plays" (a link,
  clay-deep). List every possible parse without choosing (DESIGN.md).
- Then Grammata's entry exactly as the T8 module renders it (`lookup(word,
  el, { lang: 'grc', key })` from `https://grammata.pages.dev/t8/lookup.js`),
  under a hairline in `color-mix(in srgb, currentColor 28%, transparent)` and
  a head "ἀνολολύζω · Logeion ↗". The site styles the panel around the
  module, never the module's own DOM. Cards are keyed by `data/lsj-heads.json`.

App: `shared/components/WordPopup.svelte` does the lookup today (desktop
popup, phone sheet, `asSheet`); give it B's frame through drama-scoped CSS
in `app/src/styles/reader-drama.css`; a change inside the shared component
gets a `DRIFT.md` line.

### 7.7 Speaker bar and the rest of pass 1's reader chrome

Pass 1 added `SpeakerBar.astro` under the running head (the speaker's name
once it scrolls away). The mock shows no bar and John did not rule on it:
John's call (§11). Pass 1's onboarding toast and old breadcrumb go. The
shared `RunningHead.svelte` already treats the author and work names as
links back out and drives Reader's view and translation controls through the
DOM; B's head is that line restyled, plus the picker, Aa, and the icons.

## 8. Search

Reference: `T.b.search`, `.dir-b .pg-search .pf3`, the hit groups.

### 8.1 Layout

Desktop: head (§3.4), then a grid `minmax(18rem, 26rem) 1fr`, gap `1rem
3.5rem`, max-width 80rem, `align-items: start`, margin `2rem 0 .4rem`.

Left column, the boxes: label "Greek" (Alegreya Sans 1.05rem, mid); the
Greek field (Cardo 1.8rem / 1.25, no box, a 1px ink underline, padding-
bottom .15rem; the placeholder in mid italic 1.4rem); label "English"; the
English field the same; then a row: "Search" (Alegreya Sans 500 1.1rem, clay-
deep) · "Phrase index" · "How to search" (underlined links in mid).

Right column, one row per control (`display: flex; flex-wrap: wrap; gap: .3rem
1rem; align-items: baseline`, Alegreya Sans 1rem), each led by a label in mid
at least 4.6rem wide. A picker (`.v`) is a word in ink underlined in clay-deep
with a clay-deep `▾`; a check (`.ck`) is "☐ word" in mid, "☑ word" in ink
with the box in clay-deep. The rows:

| Row | Controls |
|---|---|
| Greek | Any form of the word ▾ (or Only as typed) · Accents ignored ▾ (or Accents matter) · note "* and ? wildcards · Beta code works" |
| LSJ | the lemma candidates for what was typed, each a check in Cardo 1.08rem: "☑ ξίφος, τό — sword", "☐ ξιφίδιον, τό — dagger" · a link "the entries" |
| Near | a grammatical shape ▾ (or a word, a form, a lemma) · near ▾ (before, after) it, within 10 ▾ words ▾ (or lines) · ☐ In this order |
| Shape | verb ▾ · aorist ▾ · any mood ▾ · any voice ▾ · any person ▾ · any number ▾ (the second term's grammar) |
| English | All words ▾ (Any of them, Exact phrase) · Any form of the word ▾ (or Only as typed) · "in every translation" |
| Near | another word ▾ · near ▾ it, within 10 ▾ words ▾ |
| Together | Lines where both the Greek and the English match ▾ (or either, Greek only, English only) |
| In | All 44 plays ▾ · ☐ Aeschylus 7 · ☐ Sophocles 7 · ☐ Euripides 19 · ☐ Aristophanes 11 · a link "choose plays" |

Then the count line, margin-top 2.2rem: "7 lines in 3 plays" · "Export as
CSV". Then one group per play: a heading with the English title (Cardo
1.6rem) and "Aeschylus · Smyth 1926 · 2 lines" (mid), no Greek title and no
figure; the lines under it, each with its number in clay-deep at the left
and the matched word marked. Nothing else on the page: no h1 but a visually
hidden one, no "Lexicon"/"All works" links in the head.

Phone: one column, the boxes first, then the controls (rows at .95rem), then
Search. The "choose plays" picker is a wrapping list of checks, never a
sideways row.

### 8.2 Engine: build in two steps, the second is its own job

Step 1, B's layout over the engine this repo has (`shared/components/
Search.svelte`, 1766 lines, and `shared/lib/search.ts`): the Greek and
English fields; any form / only as typed (`grkMode`); accents
(`accentSensitive`); wildcards and Beta Code (the chart inside Search.svelte
becomes the "How to search" page, with the controls explained); English
all / any / phrase (`engMode`) and any form (`englishForms`); Together
(`langOp`); In (`works`); the lemma candidates the engine already returns
(`searchedLemmata`), shown as the LSJ row; the count and CSV export. The
rows the engine cannot answer yet (Near, Shape, the English Near, "Phrase
index") are not shown until step 2; do not fake them.

Step 2, the port John asked for ("I want the same advanced search as we
have on aristotle reader"). The Aristotle reader is `~/Developer/aristotle-
reader` (read-only; copy, never edit there). Its `shared/components/
Search.svelte` (65 KB) adds: combo search with two or more slots, each a
phrase, a form, a lemma, or a grammatical shape (`SlotKind`), related by
near, before, or after (`SlotRelation`), within N words or lines (`COMBO_
WINDOW_DEFAULT`, `COMBO_WINDOW_MAX`, `WindowUnit`), "In this order", cross-
chapter; grammar categories (number sg/pl/dual, tense, mood, voice, person,
and the nominal ones); a lemma picker with glosses (`fetchLemmaPickerShard`,
`fetchLemmaGlosses`, data under `lemma-picker/<letter>.json`); phrase
variants; URL-encoded search state (`shared/lib/search-url.ts`); the phrase
index (`shared/components/Phrases.svelte`, `pages/phrases.astro`, built by
its pipeline's n-gram stage); and the guide `pages/advanced.astro`. This
repo's pipeline (`pipeline/drama_pipeline`) has none of the data stages
behind those (no lemma picker shards, no glosses, no grammar index, no
phrases), so step 2 is engine, pipeline, and data work for 44 plays, not a
restyle. Scope it with John before starting; it is a session of its own,
after the pages in §4–§7 and step 1 are in. Everything copied from the
sister repo into `shared/` gets its `DRIFT.md` line.

## 9. Routing

- The bare play URL `/<author>/<work>/` is the play page (§6). Today
  `pages/[author]/[work]/index.astro` renders the reader there for bookless
  play-line works; that changes.
- The reader moves to `/read/<author>/<work>/` (the premise every direction
  shared; John did not object). A line opens the reader: `/<author>/<work>/
  <cite>` (`[cite].astro`) and the partner alias `/read/<author>/<work>/
  section-<n>/` (`read/[author]/[work]/section-[n].astro`) redirect there
  with `?loc=`. No `/book/1` alias for plays (the P1 ruling). Update
  `lib/citation-routes.ts`, `pages/read/_section-routes.ts`, the route
  registry the Lyceum mount expects, `scripts/check-links.mjs`, and the JSON-
  LD. Confirm the `/read/` path with John at the first milestone; it is a
  URL decision.
- The search stays at `/search/`; the lexicon at `/lemma/grc/`; texts and
  licences, support, attribution, 404 keep their routes and get B's head,
  foot, and tokens, nothing more.

## 10. Done, and the review John sees

Done means all of this is true on `claude/ui-pass2`, pushed:

1. `main` merged; every gate in §2 green; the ship gate run detached and
   green.
2. Home, author (Euripides, and Aeschylus for the Oresteia question), play
   (Medea), reader (Medea 1116–1180 in Both, Greek, and English, each menu
   open), search (ξίφος), and the word panel (ἀνωλόλυξε at Medea 1173) match
   the mock at 1440 and 390, in both themes, with open-edition Greek
   (Murray 1902 / Coleridge for Medea) in every screenshot.
3. Screenshots of all of the above in `docs/redesign/screenshots/pass2/`,
   named `<page>-<width>-<theme>.png`, for John's design review; he reviews
   design by eye, everything else is verified functionally.
4. No sideways scroll at 390 on any page (measure `scrollWidth` against
   `clientWidth`); no text beside a figure rising above the figure's top;
   every figure whole; both themes AA, with the clay-deep decision (§3.1)
   applied.
5. A Codex or Grok review of the branch before John's gate, findings fixed
   or listed.
6. `HANDOFF-overhaul-pass1.md`'s open items either closed or restated in a
   new handoff file for the next session.

## 11. John's calls still open: ask, do not guess

1. The drop-down's edge: ink frame, lifted sheet, clay rule, or dimmed page
   (§7.5). The mock's thread is open on the artifact.
2. Small text in clay-deep fails AA on light paper (4.29:1): darken it for
   small text, or set numbers and small links in mid (§3.1).
3. Author pages: do the Oresteia and Oedipus groups, the "Titles only"
   toggle, and "Find a play" survive in B's two-column list (§5)?
4. Resume on the play page: a plain link, or nothing (§6)?
5. The speaker bar under the reader's head (§7.7).
6. The reader at `/read/<author>/<work>/` (§9).
7. The stacked site name on the desktop author and play heads? John asked
   for phones; the desktop keeps one line unless he says otherwise.
8. Search step 2's scope and order (§8.2); the phrase index needs a
   pipeline stage.
9. The speaker palette's slot 4 near ink (pass 1, Data to fix) and the dark
   palette: unchanged by B; still John's.

## 12. The rulings, in John's words (20 October 2026)

- "doesn't need to have the same design as homer, tbh. i want fresh
  directions and options"; "avoid typical LLM ui tropes (buttons everywhere,
  eyebrow text, over explaining features, giant hero text with a single
  word italicized). don't want this to look like slop".
- "the Play pages shouldn't have the opening lines. pointless"
- "This scroll feature is annoying. we don't do this."; "NO SIDEWAYS
  SCROLL! Looks terrible"
- "don't like the font. too informal." (a heavy sans for titles: out)
- "whole image needs to be on screen OR we need Medea to be centered."
- "Cut this from all homepages. We don't need to say what the site is. The
  title and the list of authors and plays is fairly self-explanatory"
- "NO TO B FOR HOME AND AUTHOR." (B's scrolling bands and black-outlined
  small figures); "For home, let's give B the same layout as A"; "I do like
  how all the images are equal height. APply that equal height to B's
  homepage"; "the lists are LONG and vertical and remove reason to go to
  author pages"; "it makes the mobile homepage FUCKING LONG AS HELL to
  scroll"; "A's layout wit b's colors for home"
- "I like B's play page the best. Centered image with the clay fill; big
  title. the layout of cast and translations and greek editions is good
  too."; "B with C's banner raises issue of the color. we have the one
  accent color otherwise ... I think B's play page."
- "i think B for author."; "For word panel, B."
- "we don't need greek name on search page result headers"; "that applies
  to all versions"; "unnecessary clutter. remove from this and from B's
  search as well" (the small figures in search headings)
- "what does this even mean? does that refer to the greek edition? weird
  claude speak." (on "in the reference Greek")
- "remove." (the reader head's "1116 of 1419"); "REMOVE THE GREEK, MAKE THE
  ENGLISH TITLE IN THE ACCENT COLOR" (the reader head)
- "I kinda like how on mobile in the BOTH greek and english view the way A,
  C, and D stagger the english and greek so they don't run together. Can we
  apply that same style to B's mobile reader view?"; "ON desktop, I like how
  C has the greek lines in left margin/gutter and english has them in right
  margin/gutter. APply that to B's desktop reader."
- "We need a picker for translation AND greek edition. we need print
  option. and maybe also adjusting text size and width."; "how does the
  reader navigate back to home page or author pages?"; "drop it" (the small
  figure in the reader head); "those various controls are taking up too
  much space."; "greek on left of picker, english on right"; "'The Greek
  Drama Reader' as two lines, stacked. Compact." "for mobile, that is."
- "Let's keep the different colored speaker labels though"
- "I want the same advanced search as we have on aristotle reader"; "But i
  want the search menu to be far better looking and not at all clunky.";
  "um, thats nice and all but not power user"; "our value is partly in the
  simultaneous greek & english search with the advanced LSJ style
  searches."; "Put all the controls to the right of search boxes"
- "Let's have uniform dark/light mode icon on all pages and a search icon on
  all pages (rather than the words)"; "Equal height OR center the vertical
  alignment of 'The Greek Drama Reader' and 'Euripides - Medea'."; "Have
  the search and dark mode icon on the same line as play title" "but in the
  right hand corner"
- "Make this more elegant. Maybe a border arount the drop down so it
  doesn't look like it's just plopped on top of the text? Give me options"
- "And let's have the Stacked site logo on author and play pages too."; "Add
  author's name next to site name logo on play pages."
- "I don't like this extending ABOVE the image's height. Make image bigger
  or the description of playwright smaller so this can come down..."
- "slightly smaller font" (the play page's Greek title)
- "okay. i think its good. write a detailed spec handoff for opus"
