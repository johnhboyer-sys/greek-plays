# Reader speed on a phone (2026-10-21)

John, 2026-10-21: "I also feel like the site isn't snappy enough"; "Speed is
separate session". Branch `claude/reader-speed-61778a`, from
`claude/ui-pass2-followups-e46800` at 81bb788.

## Before and after

A simulated mid-range phone: Chrome with the CPU slowed 4x (CDP), a 10 Mbit
line with a 40ms round trip, 390x844, no cache. Median of 5 loads, against
`astro preview` of an editions-on build (gzip on, as a host serves it).
"Text on screen" is the first moment a line of the reader's Greek is visible
in the viewport.

| | Medea before | Medea after | Frogs before | Frogs after |
|---|---|---|---|---|
| First paint (head, no text) | 0.25s | 0.24s | 0.25s | 0.24s |
| **Text on screen** | **2.77s** | **0.75s** | **2.85s** | **0.90s** |
| Reader ready (mounted) | 2.49s | 0.73s | 2.58s | 0.89s |
| Longest task (page frozen) | 1.21s | 0.15s | 1.26s | 0.17s |
| All long tasks, load to settled | 1.99s | 0.77s | 1.84s | 0.44s |
| Worst frame while scrolling | 21ms | 23ms | 43ms | 43ms |
| HTML, raw (gzipped) | 3235 KB (335 KB) | 712 KB (179 KB) | 4717 KB (518 KB) | 1291 KB (325 KB) |
| JS, gzipped | 126 KB | 126 KB | 126 KB | 126 KB |

Script: `probe-speed.mjs` in the session notes folder
(`side-session-notes/local_e29cee88-…/reader-speed/`).

## Where the time went

1. **The play's data went through a reactive proxy.** Astro handed the whole
   book to the reader island as a prop: it wrote it into the page as an
   HTML-escaped attribute (1.27 MB for Medea), and its Svelte hydrator wraps
   all props in a deep `$state` proxy, so every read of every word during
   hydration went through the proxy, and `afterUpdate` read through all of it
   again after every update. The book now goes into the page once, as JSON in
   a `<script type="application/json">`, and the reader reads it from there
   (`shared/lib/book-payload.ts`).
2. **The whole play was built before anything showed.** A phone held the text
   back until the reader had mounted (so the desktop's rows never flash), and
   mounting meant hydrating every line of the play. Now the page and the
   reader start with the segments that hold the first 60 Greek lines (about
   three phone screens). The rest is added after the text shows, a slice at
   a time, each slice about 30ms of work, so scrolling and taps get in between.
   The whole play is drawn by the time shown in the table.
3. **Each slice would have rebuilt the slices before it.** In this
   (legacy-mode) Svelte component an object in an `{#each}` counts as changed
   on every update, so the segment loop now runs over indices.

## What a reader sees

Nothing changes on screen, with three small exceptions:

- For a moment after the text appears, the rest of the play is still being
  added below (see "Whole play drawn" above). A search in the page (Ctrl-F)
  in that window misses the later lines. Print, a `?loc=` link, a `#line`, a
  search's highlights, and the "Translated with the speech below" link add
  what they need first.
- A `?loc=` link now lands the same way every time. It used to depend on a
  race between the opening smooth scroll and a correction made during it,
  which could carry the page past the line (Orestes 1347 in English-only view
  landed off screen on a phone). The correction now waits until the page has
  stopped scrolling.
- After a `?loc=` link, switching the view while the linked line is still on
  screen keeps that line where it is. Before, the switch kept the line at the
  top of the screen, which could push the linked line off the bottom.

## Search engines and readers without JavaScript

The page used to carry the whole play as text. Now it carries the first
screens as text and the whole play as data (JSON), which the reader turns into
text. Google runs the script and sees the whole play; a crawler that does not
run scripts, or a browser with scripts off, sees only the first screens. A
plain-text copy of the play after the reader would restore it for them, at
some cost in speed (not measured).

John, 2026-10-22: "keep it as is for now". Revisit near launch, if being
readable to crawlers that do not run scripts (AI search tools above all)
matters.

## Checks

All on the final build. `probe-first-paint` (no rows on screen but the
settled ones), `probe-phone-pieces` 26/26, `probe-rotate` 72/72, `probe-place`
22/22, `probe-place-wide` 180/180, `probe-covered` 0 misses (2 at the start
point), `probe-head`, `probe-views-sideways` 396/396, `final-checks.sh` (direction,
codex-fixes, resume, layout at 320-1440, axe). One probe change:
`probe-place` read the Greek line below the head's edge as "the place" where
the edge cuts the English of a phone piece (each piece's Greek sits above its
English). It now reads that English, as the reader does, and passes on the
old build and the new one alike.
