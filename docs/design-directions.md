# Design directions — for John to react to before the mockup round (P4)

Status: DRAFT, orchestrator-authored 2026-09-08. Nothing here is decided. The
rulings that bound it: like the Homer Reader (distinctive, reading-first, a
token layer over the shared reader core), not the Aristotle/Plato template;
one skin, with each play given its own opening moment rather than 44 skins;
speaker attribution in colour; no play-switcher inside the reader; the
comparison bench as a first-class control; WCAG AA in both themes; scansion,
if built later, gets its own mockup round.

What the reader interior already does (kept, restyled only): parallel
Greek/English columns, click-to-parse, Grammata dictionary, search, jump by
line, translation picker, compare mode, speaker colours, footnotes, print.

## What every direction must solve

1. The **cast** as a visual system: 12 stable hues, legible as small-caps
   lead-ins in both columns, readable by the colour-blind (hue + a subtle
   second cue: a small glyph or the lead-in's weight), never louder than the
   text.
2. The **choral ode** as a different texture: lyric set apart from dialogue
   (measure, indent, the strophe/antistrophe marks as marginal figures) so a
   reader feels the metre change without a label.
3. The **opening plate** per play: title in Greek and English, the author's
   name, festival and date where known, the cast in order of appearance
   (already coloured), a one-line argument (draft copy, John approves), and
   the translations on the bench — a page you'd want to pause on before the
   first line.
4. The **bench**: two translations side by side must read as a comparison,
   not two columns competing with the Greek — the Greek stays the spine, the
   English panes are the commentary.
5. The **line number** as a whisper: every fifth line, plus suffixed and
   range refs, in the gutter, never breaking the verse.

## Direction A — "The Orchestra"

The theatre as the organising metaphor, used structurally not decoratively.
Warm limestone page (the theatron), a deep terracotta accent (the skene's
painted wood), ink near-black with a blue-black for Greek. Type: a humanist
serif with real Greek (e.g. Brill or Gentium Plus for the Greek; a
matching Latin face), small-caps lead-ins. The opening plate is a
"programme": a full-bleed band in the play's accent with the Greek title set
large, cast listed like a playbill. Chorus passages sit on a faintly tinted
field with a hairline left rule. Tragedy and comedy share the skin; comedy's
accent shifts warmer (ochre) and its plates use a lighter hand.

Risk: terracotta-and-limestone is the expected "Greek" palette; it must be
executed with restraint or it reads as a museum gift shop.

## Direction B — "The Manuscript"

The medieval codex tradition that carried these plays: a cool cream page,
generous margins, marginal apparatus (strophe marks, line numbers, the
"translated above" note) set like scholia in a smaller size; speaker colours
drawn from manuscript pigments (red lead, ultramarine, malachite, ochre,
purple, carbon) so the palette has a historical logic rather than a
rainbow. The opening plate is a rubricated title page: the Greek title in
red, the cast as a list with coloured initials. Chorus odes indented as a
narrower measure with a discreet ornament at strophe/antistrophe turns.

Risk: manuscript cues can drift into pastiche (faux parchment, drop caps);
the discipline is typographic, not textural — no textures at all.

## Direction C — "The Score"

Drama as performance notation: a clean, almost editorial layout where the
speaker lead-in, the line number and the metre markers form a grid, the
Greek in a crisp modern face with excellent polytonic support, the English
in a quiet contrasting serif. Colours are cooler and fewer: one accent per
genre (a deep wine for tragedy, a green-black for comedy) with the cast
hues kept desaturated so they organise rather than decorate. The opening
plate is a "title card" on the dark ground: white text, the cast set as a
column, the argument beneath. This is the direction that best fits a future
scansion layer (the grid is already there).

Risk: can feel cold for texts this old; needs warmth in the type and the
plate imagery (a single line-drawn mask or column, not photography).

## What the mockup round will show

For each direction: the opening plate of Agamemnon; a page of dialogue with
a stichomythia run (Ag. 1203–1213) in both-columns mode with speaker
colours on; a choral ode (the parodos) in Greek-only mode; the same ode in
compare mode with Smyth and Morshead; the Frogs opening in comedy dress;
both themes; mobile. John picks one (or a blend); the winner becomes a token
layer in `shared/styles/global.css` + the plate component; nothing in the
reader's interaction model changes.

Open questions for John: per-genre accent or per-author? Should the plate
carry a short "how to read this" for a first-time reader (as Homer's Start
Here does)? Is there any image material he wants (vase paintings are PD but
crowd the page)?
