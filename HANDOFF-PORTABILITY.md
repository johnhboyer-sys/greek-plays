# Handoff — portability (the plays)

The plays' port of the portability track. The plan, John's rulings
(decisions 1 to 10), and the worked examples live in the sibling repos:
`johnhboyer-sys/aristotle-reader` (`HANDOFF-PORTABILITY.md`, PRs #228, #231
to #236), `plato-reader` (#130 to #136), and `homer-reader` (#78 to #81).
Read Aristotle's "Goal" (the five tests), "Decisions", and "Plan" first.
This file records what the port did here, what was decided and why, and what
failed. Rewrite it as state changes.

The goal, in one line: the site builds from a clone plus checksummed inputs,
with no laptop; any static host can serve it; and copies live off GitHub and
Cloudflare.

## State (2026-11-23)

Phase 1 is in a draft PR (#17). Nothing is merged or deployed. John paused
heavy local runs on 2026-11-23 (the Mac went down with several sessions
building): no full build, no full `shared` or pipeline suite, and no browser
on the Mac. CI runs those, and the full build runs in CI only by hand (the
repo is private, so its minutes are John's money).

| Phase 1 step | State |
|---|---|
| `extract` writes `corpus/greek/`; the build reads only those | Done: 44 files, 58,999 lines, 4,493,538 bytes. Stage 1 runs no program |
| Guard on the committed files, failing cases first | Done: every character Greek or one of 19 listed marks; every label a speaker or one of five strophe words and a stanza number; no named exception. 25 hand breaks each fail a test |
| The line file gives stage 1 the export's spine | Done: 88 spines (44 plays, full and public manifests), 20,860,780 bytes, byte for byte the same three ways |
| Export-shaped files elsewhere | Done: four fixtures pinned (decision 10, for John to overrule); 94 vendored Perseus and OCR TEI files allowed by their own `SHA256SUMS` |
| Morpheus table and LSJ pinned, folder from the environment | Done: the same two files as the siblings' pins, byte for byte; `inputs check` runs first in `build:public` |
| Machine paths out of the public build | Nothing on the build path. Two OCR cleaning tools, not run by the build, name the laptop's scan files |
| Test 1, a clean Linux build in CI | Run by hand: see the phase 1 record |
| Test 2, against the snapshot | See the phase 1 record |
| Review by another model family | Not yet |

## Phase 1 record

**What reads the TLG.** All 44 plays' main Greek is a TLG edition
(`work.tlg_author`, `work.tlg_work`; four authors: 0085, 0011, 0006, 0019), so
all 44 get a line file. The other Greek editions a play offers (54 in all:
Murray's OCT and Hall-Geldart from Perseus, Smyth's and Storr's Loebs, Jebb,
Paley, and Way's Loeb from scans) are TEI files already committed under
`sources/perseus/` and `sources/ocr/`, read by `stage1_tei_greek`. They get
no line file.

**The export ran.** No export was on disk. Diogenes 4.7.2
(`xml-export.pl -c tlg -n <author> -y`), with `HOME` set and `TLG_DIR` at the
iCloud TLG folder, wrote each author in about two seconds, exit 0, into
`build/export/tlg<author>/` (the plays' recipe: one folder per author).
`extract` sets `HOME` itself.

**The format.** `corpus/greek/<play>.tsv`: three heading lines (`# work:`,
`# edition:`, `# columns: n<TAB>text`), then one row per `<l>` of the
export's body, in printed order. `n` is the line's number as printed (`1`,
`141a`, `208-209`, `289/290`, `post 410`, the export's `post1226`, and `t`
for a title). The text is the line with runs of white space made one space;
each `<label type="speaker">` stands in braces where the edition prints it.
The plays differ from Homer here: the export marks speakers and strophe marks
alike as speaker labels, and stage 1 tells them apart, so the labels must
survive with their places; a flattened line would lose them. The braces get
no space added: stage 1 drops a strophe mark outright, and the words either
side must meet as they did. Two more changes, both what stage 1 already did:
ASCII angle brackets are written ⟨ ⟩ (so no `<` or `>` is left in a file), and
the title line is its text alone (stage 1 hashes it). The `# edition:` line is
the export's `<sourceDesc>`, which stage 1 holds to the manifest's
`work.expected_sourcedesc`. The text is not NFC, as in the siblings.

The XML reader is shared: `greek_lines.rows_from_tree` is now the only way
stage 1 reads a play's export, so the old path and the line file meet in one
function (`_parse_play_rows`). It raises on shapes the old reader passed over
and no export has: anything in the body but its lines, a line inside a line,
a child of a line other than `label`, `pb`, `lb`, `space`, `hi`, a label of
another type or inside another element, a line with no number, an empty play,
and a brace in the edition's own text.

**What the export holds** (all 44 plays, 2026-11-23): 58,999 lines directly in
`<body>`; 16,528 speaker cues, 666 strophe marks (6 glued to a speaker in one
label), 52 lacunae, 1,026 words joined across lines, 33 titles; the manifests
declare 83 transposed blocks, 6 repeated refs, and 7 ref fixes, all matched.
Latin appears only in labels: Coulon's and Dain-Mazon's `Str.`, `Ant.`,
`Ep.`, `Epod.`, `Epode.`, and stanza numbers 1. to 12.

**The guard.** `greek_lines.forbidden` reads every line: the headings, each
number (ASCII digits only), each label, and each text. A text character is
Greek by its Unicode name or one of 19 marks (space, full stop, comma,
elision, hyphen, en and em dash, square and round brackets, ⟨ ⟩, « », the
three quotation marks, the crux, and the metrical ⏑ ⏓ ×). A label's words are
Greek and marks, or one of the five strophe words, or a stanza number.
Markup characters and control characters fail anywhere; braces only round a
label; one title at most. Planted cases in `test_greek_lines.py` (147 of
them, among them every ASCII letter, digit, and beta-code sign alone), and
the holes Homer's reviews found are closed from the start: an empty play, a
number `01` or in Arabic-Indic digits, a tab in a heading, namespace-prefixed
and upper-case tags, a tracked symlink, a file deleted from the working tree.
25 hand breaks of the guard, the reader, stage 1, `extract`, and the export
scan each fail a test; the first run of the breaks found one that passed (a
Latin "a" let into the marks), and a test now refuses each letter alone.

**How it was proved.** The spine stage 1 writes, for all 44 plays and both
manifests (full and public), is byte for byte the same three ways: the old
code (`origin/main`, run from a `git archive` copy) on the export, the new
code on the line file, and the new code on the export: 88 files, 20,860,780
bytes. `test_corpus_greek.py` pins the 44 spines (10,430,390 bytes, one hash
over each spine's sha256), so a change to a file or to stage 1 that moves one
fails. Three Clouds and Bacchae tests that skipped without an export now run
on the line files and pass.

**Export-shaped files elsewhere (decision 10).** The scan reads every blob in
git's index (Homer's method). Allowed more than 30 export lines: the four
fixtures pinned by size and sha256 (`play_line/synthetic6.xml`,
`play_line/synthetic_transposition.xml`, `stephanus/edge_cases.xml`,
`stephanus/euthyphro_p2_3.xml`), on the strength of John's rulings for Plato
(2026-11-21) and Homer (2026-11-23, "keep em"), listed for him to overrule;
the 94 vendored TEI files (81 Perseus, 13 OCR), each listed by its hash in its
folder's `SHA256SUMS` and holding none of Diogenes's own marks
(`quantity=`, `rend="indent(`, speaker labels); and three test files that
build Perseus-shaped TEI by hand, each held to a line ceiling. Out of its
reach: compressed or encoded copies, submodules, untracked files.

**The two outside inputs.** `greek-analyses.txt` and `grc.lsj.xml` in this
Mac's Diogenes 4.7.2 match the siblings' pins byte for byte, so
`inputs.py` is Homer's with its names changed. `DIOGENES_DATA` names the
folder; the manifests' path inside Diogenes.app is the local default.

**What changed between the snapshot and today.** The snapshot (2026-11-20)
holds the deploy of `bf4c79c` (its data names `bf4c79c-2026-11-19`). Live was
redeployed on 2026-11-23 from `35d4981` (#14's merge; live's
`data/agamemnon/manifest.json` names `35d4981-2026-11-23`). `git diff
bf4c79c c1cf9b9` outside docs and sweeps touches only the app and `shared/`
(#14, #15): the lexicon index page, the lemma-accents table, and the search
code. Live's `data/lemma-accents.json` differs from the snapshot's; a play
book (`medea/book-01.json`) does not. So test 2 compares the build's data
with the snapshot as is, and the pages with an app built at `bf4c79c` over
the same data.

**`CORPUS_VERSION`.** Each play's manifest names the commit and day it was
built from (88 files). `build:public` now takes `CORPUS_VERSION` from the
environment when set, so a build can make a past deploy's data byte for
byte; unset, it is as before.

## Decisions for John

- Decision 10 for the plays: keep the four export-shaped fixtures, pinned
  (as ruled for Plato and Homer), or replace them with made-up Greek.
- CI minutes: the `site` workflow runs only by hand. Its triggers for good
  wait on the minutes one run billed (phase 1 record, to come).
