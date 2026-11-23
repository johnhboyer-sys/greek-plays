# Architecture

How the site is made, what it needs, and what it calls. Written so that someone
with this repository and no access to its author's machines or accounts can
build the site and serve it. State and plans for the work that made this
possible are in `HANDOFF-PORTABILITY.md`; how to bring the site back from a
bundle or from source is `RESTORE.md`.

## The site is static, but for one form

Every page is a file. There is no database and no account system. A host needs
to do one thing: serve a folder of files over HTTPS, with `index.html` for a
folder and `404.html` for a missing page.

The one piece of server code is the feedback form's endpoint,
`app/worker/index.js`, which runs on the Cloudflare Worker that serves the site
and emails John. A plain static host has no such endpoint, so the form hides
itself there: its button shows only when the host serves
`feedback-endpoint.json`, which the Cloudflare deploy ships and the mirror
bundle leaves out (`app/src/lib/feedback-endpoint.ts`).

A build has two parts, served from one folder:

| Part | Folder in a build | Size (live, 2026-11-20) | What it is |
|---|---|---|---|
| App | `app/dist/` less `data/` | a few hundred files, about 65 MB | Pages, scripts, styles, fonts, drawings, share cards, the service worker |
| Corpus data | `app/dist/data/` | about 10,800 files, 385 MB | Per-play JSON: Greek and English, speakers, every Greek edition, lemmas, search indexes, phrase counts |

Unlike the sibling readers, the plays ship their data inside the site's own
folder; there is no separate data host.

## From sources to a site

```
corpus/greek/<play>.tsv   each play's Greek, one printed line per row (committed)
sources/                  the other Greek editions (Perseus TEI, OCR'd scans) and
                          the English translations (committed)
manifests/*.yaml          one per play: edition, translations, speakers, citation
greek-analyses.txt        Morpheus parse table   } not committed; pinned by
grc.lsj.xml               LSJ lexicon            } sha256, from Diogenes 4.7.2
        │
        ▼  pipeline/ (Python): stages 1–7 per play and per edition,
        │  the turn aligner, stages 8 and 9, and their gates
        │  (scripts/build-public.mjs)
build/dist/               corpus data
        │
        ▼  app/ (Astro and Svelte, Node 22), with shared/ compiled in
app/dist/                 the site
```

- **Greek text.** `corpus/greek/<play>.tsv` holds each play's main Greek as a
  plain line file; its README gives the format. The build reads them and runs
  no outside program. Making the files afresh (`python -m
  drama_pipeline.extract --all`) is a separate step for a machine that holds
  the digital source texts.
- **Two outside inputs.** The Morpheus table and the LSJ XML are not in the
  repository. `python -m drama_pipeline.inputs check` (in `pipeline/`) checks
  the copies it finds against pinned sizes and sha256 sums; the folder is
  named by `DIOGENES_DATA`. On a machine without Diogenes, `python -m
  drama_pipeline.inputs fetch --dir <folder>` downloads the Diogenes 4.7.2
  release (186 MB, pinned by sha256), takes the two files out of it, and
  holds each to its pin.
- **Full build.** At the root, `DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1
  PUBLIC_SITE_ORIGIN=https://greekdrama.johnhboyer.com npm run build:public`
  (the deploy's settings) checks the two inputs, runs the pipeline for every
  play and every Greek edition, the corpus-wide stages, the gates (preflight,
  the data contracts, the shared LSJ check), the app build, and the link
  check.
- **App-only build.** `PUBLIC_SHOW_PRIVATE=0 npm run build` in `app/`, with the
  same settings, when `build/dist/` is already there.
- **`shared/`** is the reader core this site has in common with its sibling
  readers. It is copied between the repositories, not linked (`DRIFT.md`).

## Build parameters

All are read at build time. Unset, each gives the build as it was before
they existed.

| Variable | Default | What it sets |
|---|---|---|
| `PUBLIC_SITE_ORIGIN` | unset | The origin in canonical links, share cards, the sitemap, and `robots.txt`. Unset: none of these (CI's test builds). The deploy sets `https://greekdrama.johnhboyer.com`; a mirror keeps it, so its canonical links name the primary |
| `SITE_BASE` | `/` | The path the site is served under, such as `/plays/` |
| `PUBLIC_DATA_ROOT` | unset | Where the app fetches corpus data. Unset: `<base>/data` on the site's own origin, which is how the plays are served |
| `PUBLIC_GRAMMATA_LOOKUP` | Grammata's `lookup.js` | The address of the dictionary script (see outside calls) |
| `DRAMA_EDITIONS`, `PUBLIC_EDITIONS` | unset | `1` builds and shows every Greek edition a play offers; the deploy sets both |
| `CORPUS_VERSION` | this commit and today | The version each play's manifest names; set it to rebuild a past deploy's data byte for byte |
| `PUBLIC_SHOW_PRIVATE` | unset | Must be unset or `0` for anything that leaves the machine; `build:public` forces `0` |
| `DIOGENES_DATA` | each manifest's path | The folder that holds the two outside inputs |

`scripts/site-params.mjs` reads the first two for the Astro config, for
`robots.txt`, and for the link check alike, and refuses a value that is not an
origin or a base path.

## What runs where today

| Piece | Where | Notes |
|---|---|---|
| Site and data | One Cloudflare Worker, `greek-drama-reader`, serving `app/dist` as static assets, at `greekdrama.johnhboyer.com` | The data is inside its assets; no R2 bucket |
| Feedback form | The same Worker's script, `app/worker/index.js`, for `/api/*` only | Email binding to John's address; a rate limit of 3 a minute |
| Source | GitHub, `johnhboyer-sys/greek-plays` (private) | A private copy on GitLab, `johnhboyer/greek-plays` |

## A copy any host can serve

Build with `PUBLIC_DATA_ROOT` unset (as the deploy does) and one folder is the
whole site. `scripts/make-bundle.mjs` packs that folder as one `.tar.gz`:

- without `feedback-endpoint.json`, so a mirror shows no form it cannot send;
- with a `SHA256SUMS` that names every file, so a copy can be checked with
  `shasum -a 256 -c SHA256SUMS`;
- only after the data has passed the build's data gates (preflight
  `--public --editions`, with the public-domain allowlist, and the data
  contracts), every LSJ key a play names has a headword, every lemma page in
  the index has its file, and every JSON file parses.

Unpacked at a web root, the bundle is the site. Its canonical links name the
primary, so a mirror does not compete with it in search results.

The `Dockerfile` at the root is the same thing in one command: its first stage
is the full build with its tools pinned, and its second serves the unpacked
bundle with Caddy on port 80.

## Outside calls a visitor's browser makes

| Host | For | State |
|---|---|---|
| None, for fonts | Web fonts | Served by the site (`app/public/fonts/`) since phase 2 |
| Grammata (`PUBLIC_GRAMMATA_LOOKUP`, and its packs on `pub-d505f3fd993b4e01b2ab095428d0493e.r2.dev`) | The LSJ entry in the word popup and on lexicon pages | Stays, by a ruling of 2026-08-29. With it refused, the popup still shows its own headword, gloss, and parses |

Links to the sibling readers, Perseus, Logeion, and the support page are plain
links a reader follows. The site carries no analytics or trackers of its own.

## Checks

| Check | Command | What it proves |
|---|---|---|
| Pipeline tests | `cd pipeline && uv run --with pytest pytest -q` | The stages, and that every character of every committed Greek line is Greek or a listed mark |
| Script tests | `node --test scripts/__tests__/*.test.mjs` | The build, snapshot, bundle, and outside-call scripts |
| App and shared tests | `cd app && npm test`; `cd shared && npm test` | The reader's code |
| Link check | `node scripts/check-links.mjs app/dist` | No broken link or anchor in a built site, at any base path (`SITE_BASE`) |
| Data gates | In `pipeline/`: `.venv/bin/python -m drama_pipeline.preflight --public --editions ../app/dist/data ../manifests` and `-m drama_pipeline.validate_contracts --schemas ../schemas --dist ../app/dist/data`; `make-bundle.mjs` runs both on the folder it packs | Every play and edition, the translation lists, the search indexes, and the data contracts |
| No outside calls | `node scripts/check-no-outside-calls.mjs` | In a browser whose every request passes a recorder that forwards nothing, the built site shows its pages and asks for no host off its allowed list. Needs Playwright and its Chromium |
| A host serves the bundle | `node scripts/check-served.mjs --origin=<host> --sums=<SHA256SUMS>` | A running host answers every file the bundle's list names with the listed bytes, a folder's address with its index, and a missing page with 404 and the 404 page |
| Same output | `node scripts/compare-snapshot.mjs --sums=<snapshot>/SHA256SUMS --prefix=app/ --build=app/dist --floor` (the page form is in `HANDOFF-PORTABILITY.md`, phase 1) | A build holds every file of a dated snapshot of the live site byte for byte. The plays' snapshot is a floor: files only the build has are counted, not failed |

Two builds of one commit in two folders differ in a few class names and bundle
file names: Svelte hashes a component's absolute path into its style class when
the component lives outside `app/`. `compare-snapshot.mjs` computes the
expected names and accepts those swaps and no others.
