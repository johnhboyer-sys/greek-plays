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

Phases 1, 2, and 3 and the licence are four stacked draft PRs (#17, #18,
#19, #20). Nothing is merged or deployed. John paused heavy local runs on
2026-11-23 (the Mac went down with several sessions building): no full
build, no full `shared` or pipeline suite, and no browser on the Mac. CI
runs those: the full build on pull requests to `main` that are not drafts,
by hand, and on the `build-site` label (John's ruling, below).

| Phase 1 step | State |
|---|---|
| `extract` writes `corpus/greek/`; the build reads only those | Done: 44 files, 58,999 lines, 4,489,421 bytes. Stage 1 runs no program |
| Guard on the committed files, failing cases first | Done: every character Greek or one of 19 listed marks; every label a speaker or one of five strophe words and a stanza number; no named exception. 25 hand breaks each fail a test |
| The line file gives stage 1 the export's spine | Done: 88 spines (44 plays, full and public manifests), 20,860,780 bytes, byte for byte the same three ways |
| Export-shaped files elsewhere | Done: four fixtures pinned (decision 10, for John to overrule); 94 vendored Perseus and OCR TEI files allowed by their own `SHA256SUMS` |
| Morpheus table and LSJ pinned, folder from the environment | Done: the same two files as the siblings' pins, byte for byte; `inputs check` runs first in `build:public` |
| Machine paths out of the public build | Nothing on the build path. Two OCR cleaning tools, not run by the build, name the laptop's scan files |
| Test 1, a clean Linux build in CI | Passed: `site.yml` run 45253108089 (on `90c5e23`), 16 min 47 s; inputs fetched and matched their pins, preflight ok, 44 manifests checked, every dictionary key resolved, 1,318 pages and 12,795 links with 0 broken, 12,194 files |
| Test 2, against the snapshot | On that run's artifact: 12,194 files; 10,942 byte for byte, 3 pages and 2 bundles equal under 9 swaps, 26 differ for named reasons, 1,221 only in the build (the floor's gaps, by family), 2 only in the snapshot (the two bundles' old names). Stage 6 now sorts, so the 25 lemma-map files no longer depend on the disk (they change key order once at the next deploy) |
| Review by another model family | Done: Grok, a static read of the diff (session `01a209f7…`): ten findings, three fixed with failing tests first, seven answered (phase 1 record) |

| Phase 2 step | State |
|---|---|
| Build parameters for origin, base path, and the Grammata address | Done: `PUBLIC_SITE_ORIGIN` (the plays' existing name, optional) and `SITE_BASE` in `scripts/site-params.mjs`, read by the Astro config, `robots.txt`, and the link check; `PUBLIC_GRAMMATA_LOOKUP` in `shared/lib/grammata.ts`. `READER_BASE_PATH` is gone |
| Fonts self-hosted | Done: `app/public/fonts/`, 66 woff2 files (every one Google served for the pages' two queries, and the Ῥ subset), 6 families, each OFL text; 15 pages link `fonts/fonts.css`; no page names a Google font host |
| The feedback form hides where there is no `/api` | Done: the button shows only when the host serves `feedback-endpoint.json`, which the bundle leaves out; test 3 saw it hidden on the bundle |
| The mirror bundle | Done: `scripts/make-bundle.mjs`, 12,267 files, 445,933,017 bytes, 105 MB packed, 5 gates on 10,770 data files |
| No outside calls (test 3) | Green at `/` and at `/mirror/`: 9 of 9 visits, one outside host asked for (Grammata, allowed) |
| A build at a test base path passes the link check | Done: `/mirror/` at another origin, 1,318 pages, 12,898 links, 0 broken; the same folder checked as if at `/` fails (about 12,700 broken) |
| `check-served.mjs` | Homer's, unchanged |
| `Dockerfile`, Caddy, image workflow | Written; the image builds in CI only by hand or on the `build-image` label; not yet run |
| `ARCHITECTURE.md`, `RESTORE.md` | Written; `RESTORE.md`'s log is empty until a restore path is run |
| Review by another model family | Running (Grok, phases 2 and 3 together) |

## Phase 2 record

**Parameters.** The plays already had `PUBLIC_SITE_ORIGIN`, optional (unset
in CI's test builds: no canonical links and no sitemap). `site-params.mjs`
keeps that name and meaning (trailing slashes dropped, as before) and adds
`SITE_BASE`, which replaces the link check's own `READER_BASE_PATH`, so one
name means one thing. `robots.txt` names the sitemap under the base. The
app already built its links from `BASE_URL`; CI's first `/mirror/` build
found two pages that did not: the line-citation redirects and the `texts/`
aliases (3,482 broken links). Both now prefix the base; at the root it is
empty, so live's pages do not change. `PUBLIC_GRAMMATA_LOOKUP` is read in
the one module both callers load (`shared/lib/grammata.ts`).

**Fonts.** Aristotle's method (#232): Google's CSS for the two queries the
pages sent (Alegreya Sans, Alegreya Sans SC, and Cardo on screen; Bodoni
Moda and DM Mono for the print masthead), every rule and file kept, each
address made local: 65 rules and files. The Ῥ face (`GDR Rho Dasia`, a
Gentium Book Plus subset) moved from `shared/styles/global.css`, which named
Google's address, into `fonts.css` with its file and Gentium Book Plus's
licence. `scripts/__tests__/fonts.test.mjs` (Aristotle's, with the plays'
counts) holds the folder and the stylesheet to each other and fails a page
that names a Google font host; 19 pass. The service worker's branch for
Google's hosts stays, unreachable, as in Aristotle.

**The feedback form.** `app/worker/index.js` answers `/api/feedback` on the
Cloudflare Worker only. The button is now `hidden` until
`lib/feedback-endpoint.ts` reads `feedback-endpoint.json` and finds a
same-host address (12 tests, the failing cases first: a 404, a host that
answers every path with its home page, not JSON, no address, another host,
`//host`, a server error, a network error). The bundle leaves the marker
out (`HOST_FILES`); `deploy-cloudflare.mjs` (phase 3) refuses a build
without it.

**The bundle.** `make-bundle.mjs` is Homer's with the plays' gates: preflight
`--public --editions --web`, the data contracts, every LSJ key of the plays'
own analyses with a headword in `lsj-heads.json`, the lemma pages, and JSON.
CI's first run stopped at two of them, both gates of the bundle's own:
preflight looked keys up in LSJ shards the web build removes on purpose
(`--web` now skips only that lookup; `build:public`'s own preflight makes it
on `build/dist`), and the headword gate held the other editions' keys too.
**A gap found on the way, live today and left for John:** 189 LSJ keys in the
other Greek editions' analyses (`data/<play>/ed/<id>/analyses.json`; Jebb,
Smyth's Loeb, and others) have no headword in `lsj-heads.json`, which
`build-lsj-heads.mjs` builds from the plays' own analyses only, so the word
popup in those editions shows no headword for them. On the downloaded
build's data the five gates passed locally before the CI rerun: 18,145 keys,
7,405 lemma pages, 10,671 JSON files.

**Test 3.** `check-no-outside-calls.mjs`, drafted by an Opus agent from
Homer's (everything above its visits unchanged but names), with Grammata's
two hosts the only ones allowed and nine visits: Medea's reading page (1,500
Greek and 2,000 Latin letters at least), a word popup (headword, gloss,
parse), one speaker's lines (the search's speaker filter, Medea's), a
search (τέκνα, a hit linking into this build), a lexicon entry (τέκνον,
headword and works list from the site's data), the home page (44 plays), Medea's
own page, the feedback form (hidden, and the marker's 404 expected only where
the folder lacks it), and the reading page under the service worker. CI run
45264091146: `ok …/site at /: 9 of 9 visits, 374 requests to the site (0 not
found, 6 expected), 1 outside host asked for, it allowed (grammata.pages.dev
x2); control seen`, and at `/mirror/` `9 of 9 visits, 373 requests … (0 not
found)`. The browser fixtures were ported and not run (the Mac runs no
browser); the unit tests pass, 15.

**CI runs and minutes.** Run 45257010840 (bundle gates, fixed), 45259871277
(the base-path link check, fixed), 45264091146 (green, 17 min 55 s).

**Known and left.** As in the siblings: a saved search keeps whole paths,
base included, in the browser's storage.

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
the manifest's `work.greek_edition` ("Murray, Aeschyli tragoediae, 2nd ed.
(OCT, 1955)"), as in the siblings: the files name editions, never the TLG
(decision 3). The first cut wrote the export's own source statement there,
TLG numbers included; the lead's review caught it. `extract` holds the
export's statement to `work.expected_sourcedesc` before it writes, and the
statement goes no further; stage 1 holds the file's edition line to
`greek_edition`; the guard fails an edition line with a `(NNNN: NNN)` number
or the canon's words ("Trag.", "Comic.", "B.C.", "Ed. ", "Repr.", "TLG",
"Diogenes"), 11 planted cases first. The text is not NFC, as in the siblings.

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

**Test 1, a clean Linux build (2026-11-23).** `site.yml`, started by the
`build-site` label on #17, run 45253108089 at `90c5e23`: the two inputs
fetched from Diogenes's release and matched their pins; `build:public` with
the deploy's settings (`DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1
PUBLIC_SITE_ORIGIN=…`, and `CORPUS_VERSION=bf4c79c-2026-11-19`) ran in 15
minutes: preflight ok, `checked: 44 manifest(s), snapshot, registry`, "every
referenced dictionary key resolves", `Pages crawled: 1318; links checked:
12795; … broken: 0`. Then the app was rebuilt at `bf4c79c` over the same
data (55 seconds) and uploaded (104 MB packed). The run took 16 min 47 s; the
billing endpoint (`actions/runs/45253108089/timing`) reported `total_ms: 0`
when read right after.

**Test 2, on that artifact.** `node scripts/compare-snapshot.mjs
--sums=<snapshot>/SHA256SUMS --prefix=app/ --build=<artifact>/dist
--pages=<snapshot> --svelte=<bf4c79c's shared/components>
--svelte-at=/home/runner/work/greek-plays/greek-plays/shared/components
--floor --plays=manifests`:

```
FAIL …/dist: 10942 of 12194 build files are byte for byte what the snapshot holds; 0 live-only files allowed;
3 pages and 2 renamed bundles equal once 9 names are swapped (Svelte classes checked against 12 component paths);
26 differ, 1221 only in the build (a floor: counted, not failed), 2 only in the snapshot
```

Every difference has a named reason:

- 25 `data/lemma-map/*.json`: the same keys and values, in another order.
  Stage 6 (`build_lemma_map`) reads every play's analyses in the order the
  disk lists the folder, and a Mac's APFS lists it in its own hash order
  (`oedipus-coloneus`, `agamemnon`, `antigone`, `persians`, …: live's key
  order, inferred from live's own files), Linux in another. A first fix in
  `build-lemmata.mjs` was the wrong file (it writes no lemma map; CI's
  second bundle still differed) and is undone. Stage 6 now reads the plays
  in name order, so every build makes the same bytes, Mac or Linux; the next
  deploy changes the key order of these 25 files once (the same JSON). An
  exact match with live's current bytes is not possible on Linux: live's
  maps also hold a key (`zeunames`) that comes from the last play's
  in-memory analyses at stage 6, not from any committed file.
- `data/wing.drama.json`: its `generated` time.
- `_astro/Phrases.*.js` and `_astro/Search.*.js` (and so the 2 "only in the
  snapshot", their old names): the same token stream on both sides; every
  difference is a one-to-one rename of a minifier's short name (130 and 179
  names, none over two letters) or a Svelte class. esbuild picks short names
  by how often each letter occurs, and the folder-dependent class names
  change that. Aristotle's and Homer's swaps did not need this; their
  bundles came out equal.
- Only in the build, 1,221, the floor's gaps: 1,170 line-citation redirect
  pages (`<author>/<play>/<line>/index.html`), 44 `texts/` aliases,
  `data/lemmata-lat/_index.json`, and six bundles the snapshot's walk did not
  reach.

The compare turned red on one byte added to `data/medea/book-01.json`
(`differs: data/medea/book-01.json`) and on `data/medea/columns.json` taken
away (`only in the snapshot: data/medea/columns.json`), and green again
once each was put back. `--svelte-at` is new (with a failing test first): the
class names Svelte hashes from a component's path are computed for CI's
folder, since the build ran there.

**Review (Grok, 2026-11-23).** A static read of the phase 1 diff, briefed
with the claims and the places to look; ten findings.

Fixed, each with a failing test first and a hand break that fails it:
(1, High) the edition line was free text, so beta code, markup in
look-alike brackets, or a whole play could sit on it: it is now a short
bibliographic line (Latin letters, accented or not, digits, spaces, and
`.,:;'&()-`, at most 120 characters), and every manifest's edition passes;
(3) a stripped export could pass in a vendored folder if that folder's
`SHA256SUMS` were rewritten with it: the four lists are pinned by sha256 in
the test, and an unpinned list fails; (7) "Greek by its Unicode name" let in
Greek symbols that are not text (the obol sign, vocal notation): a character
is now a Greek letter or one of the three marks the editions print (ano
teleia, question mark, numeral sign), which are all the 44 files use.

Answered: (2) a strophe label with ASCII angle brackets would show ⟨ ⟩ in
the spine, where the old reader kept `<` `>`; no committed label has one,
and the 88 spines are byte for byte the old code's, so it is left as the
file's rule (angles are written ⟨ ⟩). (4) a file of `<l>` lines with no
numbers, no Diogenes marks, and no header is not the Diogenes XML in any
sense the scan guards; out of its reach, said in the test. (5) the three test
files allowed by name cannot hold a play between them (590 lines against
the Cyclops's 707), and a header or export name still fails. (6) the
README is prose, held to 4 KB and no markup, as in Homer's. (8) the unit
test compares two paths of the new code; the old code was compared by hand
(88 spines) and the pin holds the result. (9) `extract` reads an export
already on disk without a checksum; it holds the export's source statement
to the manifest, and any change to a line file is a reviewed diff. (10)
`lost_lines` counts lines only, as in the siblings.

**`CORPUS_VERSION`.** Each play's manifest names the commit and day it was
built from (88 files). `build:public` now takes `CORPUS_VERSION` from the
environment when set, so a build can make a past deploy's data byte for
byte; unset, it is as before.

## CI minutes (ruled by John, 2026-11-23)

The repo is private, so Actions minutes are paid for. Measured: a full
`site.yml` run takes about 17 minutes (16 min 47 s and 17 min 7 s), about
$0.10 at list price ($0.006 a Linux minute); the account is on the Pro plan,
and the repo had used about 300 private minutes in November when John
ruled. In October it used 384 minutes ($1.13 net). John, to the lead
session's question "Run the plays' full build on every PR to main, or by hand
only?", at 14:38: "Yes, on PRs". So `site.yml` runs on a pull request to
`main` that is not a draft (opened, new commits, reopened, marked ready), by
hand, and on the `build-site` label; never on a branch push. A draft's push
starts a run whose job skips at once (run 45261560673, on `f72bf82`).
Concurrency sits on the job, so a skipped run cancels nothing. The Image
workflow (phase 2) stays by hand or by the `build-image` label. Earlier the
same day John okayed one round of by-hand runs ("okay. run it this time").

## The licence (drafted 2026-11-23; John's to rule)

The pattern John ruled for Plato and Homer: MIT for the code in `LICENSE`,
CC0 1.0 on `corpus/greek/`, CC BY 4.0 on his own apparatus, and every other
source on its own terms, in a table at the head of `sources/INVENTORY.md`,
each line repeating what this repo and the site's attribution page already
state. Drafted so in the licence PR. What is new with the plays:

- **36 of the 44 Greek editions were printed after 1930** (Murray 1955,
  Diggle 1981-1994, Dain and Mazon 1955-1960, Dover 1968, MacDowell 1971,
  Ussher 1973); 8 are Coulon's Budé, 1923-1930. For Homer's 1931 Allen John
  answered "CC0 now". The draft puts CC0 on all 44 files, worded as a waiver
  of whatever rights John holds, since an editor's rights in his edition are
  not his to give.
- **The OCR'd Greek editions** (`sources/ocr/`: Jebb, Paley, Way) are John's
  transcriptions of public-domain books, and each file's header says "Not
  for redistribution until the owner rules on it". The draft leaves them
  unruled.
- **NonCommercial and NoDerivatives sources**: the Kosmos Society
  translations (CC BY-NC-ND 3.0) and Ian Johnston's (his non-commercial
  terms). Public releases (phase 3) would carry them once the repo is public.
- **The drawings** count as John's own apparatus (CC BY 4.0) in the draft.

## Decisions for John

- Decision 10 for the plays: keep the four export-shaped fixtures, pinned
  (as ruled for Plato and Homer), or replace them with made-up Greek.
