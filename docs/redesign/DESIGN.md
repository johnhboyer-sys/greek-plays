# Greek Drama Reader redesign: design brief

Decided with John, 1 October 2026. The reasons and the rounds of sketches that led here are in `decisions.md`. The sketches themselves are in `sketches/`. Open them in a browser; they show each page at desktop and phone width.

## The site

A reader for the 44 complete Greek plays, in Greek and English, with several translations per play and click-to-parse. About half the readers are translating the Greek, and about half read the English with the Greek beside it. Most visits return to a play already started.

## The look

Outline drawings of real Greek vases, set on a ground line like figures on a vase. Cardo for text and titles. Warm off-white pages. Each author has one muted tint, used on his own pages and in the reader's running head. No horizontal rules, boxes, cards or shadows.

## Author tints

| Author | Ground | Links and title colour |
|---|---|---|
| Aeschylus | #e2e7ec (slate) | #34536b |
| Sophocles | #e3e8df (sage) | #43603b |
| Euripides | #efe2dc (clay) | #8a3f30 |
| Aristophanes | #f0e7d2 (ochre) | #6e5114 |

All pass WCAG AA for body text and links in light mode. Dark-mode equivalents are still to be made and must pass AA too.

## Home page

Sketch: `sketches/home-sketches-round3.html`, version A.

- The four playwrights stand on one ground line, like a vase frieze, in four equal columns.
- Under each figure: the Greek name, smaller and grey; the English name, large; the play count, which links to the author page. No play titles; a partial list implies those are the only plays.
- Collections and other resources go underneath the frieze. Which collections is still open (see the end of this file).
- Search and Resume go in the header.
- On a phone, the frieze becomes two pairs of figures.
- The home page has no tint.

## Author pages

Sketch: `sketches/author-pages-round4.html`.

- The page ground is the author's tint.
- Hero: the author's figure on its ground line, then the Greek name, the English name (large), dates and play count, and the author blurb from `manifests/authors.yaml`.
- Plays are listed without boxes. On a desktop, each play has its title and Greek title on the left, and its blurb and production note on the right. On a phone, it shows only the title, Greek title and blurb, with no production note.
- Aeschylus: the Oresteia comes first, under one heading with one shared production note. Its three plays sit side by side, labelled first, second and third play. Then the other four plays.
- Sophocles: the Oedipus cycle comes first, in story order (Oedipus Tyrannus, Oedipus at Colonus, Antigone). A note says the plays were written years apart and not staged together. Then the other four plays.
- No side bars or block-quote styling for groups.
- Find a play appears on Euripides' page only. "Titles and notes / Titles only" toggle on every author page; remember the choice.

## Play opening

Sketch: `sketches/play-opening-round2.html`.

- Playbill layout: the play on the left, the cast and facts on the right. Stacked on a phone.
- Left: the play's own drawing on its ground line, with clear space below the header; the header never crops the drawing. Then the Greek title, the English title (large), the author (link), the one-sentence argument, then Resume (when a saved place exists) and Start. The full synopsis sits behind "Full synopsis (tells the ending)".
- Right: Persons, in order of appearance, in two columns, each name in its speaker colour with its Greek label. Then First staged, Greek texts (each with its year), Translations (each with form and year, and which Greek text it follows where the repo records it), and Cite as.
- The page ground is the author's tint.

## Reading view

Sketches: `sketches/reading-view-round2.html` and `sketches/reading-view-sketches.html` (sketch 2).

- The running head carries the author's tint. The text area is warm paper, #fbf9f4, the same for every author.
- No horizontal rules anywhere in the reading view, including under the running head.
- Speaker names run into the first line of each speech in both columns: Χο. in the Greek, "Chorus." in the English. No separate speaker gutter.
- The Greek and English of each speech start on the same line.
- English is never smaller than the Greek. Same size, same ink.
- Line numbers: every fifth line, the first line of the passage, and any line printed out of order.
- Translators' stage directions are marked as the translator's.
- Long speeches: on a desktop, the Greek and English each run as one continuous column, with small line numbers in the English at the translation's own markers. On a phone, five lines of Greek alternate with their English. A small bar under the running head names the speaker once his name has scrolled away.
- Comparison: each stanza starts on the same line in every column, with space between stanzas. Do not label strophe or antistrophe until the data marks them.
- Parsing: the tapped word is highlighted. On a desktop the panel opens beside the text; on a phone, as a sheet from the bottom. List every possible parse without choosing one. The dictionary entry is Grammata's, unchanged, and scrolls inside the panel so the text never moves.

## Drawings

- Every play gets its own drawing. Every playwright gets his own figure for the home page.
- Whole figures only, cut out along their outlines. No straight crop edges, no fragments of neighbouring figures.
- No nudity.
- One style: black line on a transparent ground, as SVG. Each SVG has two paths: the lines (`currentColor`) and the figure's area under them (a `body` path, transparent unless the page fills it). Light theme: dark lines, no fill. Dark theme: the lines stay dark and the figure is filled with clay, as on a red-figure vase; never light lines on dark (approved 2026-10-02). Matching line weight at display size. Format and tools: `drawings/README.md`.
- Sources, in this order: an ancient object linked to the play; an identified depiction of its myth or central figure; a labelled thematic object; an original drawing built from checked references.
- Pre-1931 line drawings of real vases are the best ready-made source: Hamilton/Tischbein (1791–95), Gerhard's *Auserlesene Vasenbilder* (1840–58), the *Monumenti inediti*, Furtwängler–Reichhold (1900–32; check each volume's date). Flaxman's Aeschylus plates (1795) are his own designs, not copies of vases; label them so if used.
- The Pronomos vase shows a satyr-play cast. Do not use it for the tragedians. The figures in the sketches are stand-ins cut from it.
- Rights: public domain, CC0 and CC BY-SA only. A drawing made from a CC BY-SA source is released under CC BY-SA, credits the original and says it was changed. Record the licence of the exact file used. The painting on an ancient vase is public domain even where a photo of it is not, so a drawing may be traced from an in-copyright photo (John, 2026-10-02).
- For each drawing, fill in its record in `research/play-image-plan.json`, plus whether it shows the play itself or a related subject.

## Fixed

- Cardo for reading text and titles; Alegreya Sans for controls.
- Light and dark themes, both AA. Check every page at 1440px and 390px.
- Use only data the repo holds. No invented dates, song divisions, entrances or metre.
- The text rules in `CLAUDE.md` stand: shared lines, transpositions, repeated refs, translator stage directions, Greek editions as printed.
- Reader-facing copy is DRAFT until John approves it. Use the manifest fields; do not write new copy.
- Changes to `shared/` get a line in `DRIFT.md`. Prefer drama-scoped tokens and files.
- The licensed TLG Greek never goes to an outside service. For screenshots and prototypes shared outside the machine, use the open editions in `app/public/data/<work>/ed/`.

## Data to fix

- Three manifests store the Greek title in unaccented capitals: Seven Against Thebes (ΕΠΤΑ ΕΠΙ ΘΗΒΑΣ), Trojan Women (ΤΡΩΙΑΔΕΣ), Helen (ΕΛΕΝΗ). They should read Ἑπτὰ ἐπὶ Θήβας, Τρῳάδες, Ἑλένη.
- Translation years per play: Murray's verse translations have only one year (his Hippolytus) for all plays; Johnston and Kosmos have only date ranges.
- The `line` field on segment speakers does not match where the speech starts (Jason shows at 434; he enters at 446). Do not build anything on it until it is checked.
- Speaker palette slot 4 (#3a3632) is close to the text colour; Cassandra gets it in Agamemnon. Replace it with a hue that stands out.

## Review checklist

Use this for the review pass, not the first draft. Reject a page if:

- Any horizontal rule, box, card, rounded container or shadow appears around authors, plays or speeches.
- A drawing is cropped by a straight edge, cut by the header, or shows another figure's fragments.
- English is set smaller or lighter than the Greek.
- A play list shows some titles but not all.
- Parchment, marble, Greek-key borders, laurels, columns, busts, or a tragedy/comedy mask pair appear as decoration.
- Tracked all-caps labels, ornamental numbering, slogans or filler copy appear.
- Any text fails AA contrast in either theme.

## Still open

- Which collections go under the home-page frieze. Candidates: the Electra story told three times; the war of Oedipus' sons told twice; Euripides in Aristophanes; the women of Troy; Heracles across the playwrights; the two Suppliant Women and the two Iphigenias.
- The order of plays on author pages after the groups: date of first performance, or start-here picks.
- Euripides grouped by myth, and Aristophanes grouped by subject. Drafts are in `decisions.md`.
- The University of Michigan Aristophanes covers as a reference.
