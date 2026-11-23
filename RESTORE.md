# Restore

How to bring the site back with this repository, or with a built bundle, and
no access to its author's machines or accounts. `ARCHITECTURE.md` says what
the site is made of; this file is the steps. The log at the end says which of
them have been run, when, and how long they took.

## Where the copies are

| What | Where | Notes |
|---|---|---|
| Source | GitHub, `johnhboyer-sys/greek-plays` (private) | Every play's Greek, the other Greek editions, the translations, the pipeline, and the app are all in it |
| Source, second copy | GitLab, `johnhboyer/greek-plays` (private) | Every branch and tag, as of 2026-11-21. Nothing keeps it current yet (phase 3). Only the owner can read it |
| A built bundle | None yet. CI's `site` workflow builds one only when run by hand (the repo is private, and its minutes are paid for) | A release for each deploy is phase 3 |
| The build's two outside inputs | Diogenes 4.7.2's release on GitHub, `pjheslin/diogenes` | 186 MB; pinned by sha256 in `pipeline/drama_pipeline/inputs.py` |

Both copies of the source are private, so today only the owner can restore
the site. A stranger can once John makes the repository public.

## From a bundle

A bundle is the whole site in one file. This takes minutes.

1. Unpack it and check every file:

   ```
   mkdir site && tar -xzf greek-plays-bundle.tar.gz -C site
   (cd site && shasum -a 256 -c SHA256SUMS --quiet)
   ```

   No output and exit 0 means every file is the one the build made. On Linux,
   `sha256sum --quiet -c SHA256SUMS` does the same.

2. Serve the folder at the root of a name, over HTTPS, on any static host.
   The host must do three things: answer a folder's address
   (`/read/euripides/medea/`) with that folder's `index.html`; answer a
   missing page with `404.html` and status 404; and send pages, stylesheets,
   and scripts with their usual types. It must not answer every unknown
   address with the home page.

3. Check the host. The check is a script in this repository
   (`scripts/check-served.mjs`; it needs Node 22 and nothing else), so run it
   from a checkout, with the path to the unpacked folder's list:

   ```
   node scripts/check-served.mjs --origin=https://<the host> --sums=<path to>/site/SHA256SUMS
   ```

   It asks the host for every file the list names and compares the bytes.
   `--every=50` reads a sample, for a host that should not get 12,000
   requests; `--concurrency=2` for a small server.

The bundle's canonical links name `greekdrama.johnhboyer.com`. That is right
for a mirror. A copy that is to be the site under another name is built from
source with `PUBLIC_SITE_ORIGIN` set. A bundle has no feedback form: the form
needs the Cloudflare Worker's `/api/feedback`.

## From source

Needs git, Node 22, [uv](https://docs.astral.sh/uv/), and the network.

```
git clone https://github.com/johnhboyer-sys/greek-plays.git
cd greek-plays
(cd pipeline && uv sync)
(cd app && npm ci)
export DIOGENES_DATA="$PWD/../diogenes-data"
(cd pipeline && uv run python -m drama_pipeline.inputs fetch --dir "$DIOGENES_DATA")
DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1 PUBLIC_SITE_ORIGIN=https://greekdrama.johnhboyer.com npm run build:public
node scripts/make-bundle.mjs --out=../greek-plays-bundle.tar.gz
```

`app/dist/` is then the site, and the last line packs it as a bundle after the
data has passed the data gates. For another name or a path under one, set
`PUBLIC_SITE_ORIGIN` and `SITE_BASE` before `npm run build:public`
(`ARCHITECTURE.md`, build parameters). `build:public` runs the pipeline with
`pipeline/.venv/bin/python`, which `uv sync` makes; `DRAMA_PY` names another.

If the Diogenes release is gone, any copy of `greek-analyses.txt` and
`grc.lsj.xml` with the pinned sums will do: put both in a folder, name it in
`DIOGENES_DATA`, and `(cd pipeline && uv run python -m drama_pipeline.inputs check)`
says whether they are the right files. Every install of Diogenes 4.7.2 has
them, under `dependencies/data`.

## With Docker and nothing else

```
docker build -t greek-plays .
docker run --rm -p 8080:80 greek-plays
```

The first line is the build from source inside a container; the second serves
the result at `http://localhost:8080`. Put a host that speaks HTTPS in front
of it.

## To make it the primary again

The primary is one Cloudflare Worker that serves `app/dist` and runs the
feedback form (`app/wrangler.jsonc`, `app/worker/index.js`): from `app/`,
`npx wrangler@4 deploy` after a full build. It needs the owner's Cloudflare
account, an email binding to a verified address, and a name to point at it. A
new owner needs their own.

## What a restore does not bring back

- The LSJ entry in the word popup and on lexicon pages comes from another site
  (Grammata). Without it the reader still shows its own headword, gloss, and
  parses.
- The feedback form, anywhere but on a Cloudflare Worker with the form's
  script.
- Translations that are not cleared for the public site are not in the
  public build, and no bundle holds them.

## Log

| Date | What was run | Result | Time |
|---|---|---|---|

Not yet run: any of it. The first entries come from CI's `site` and `Image`
workflows (`HANDOFF-PORTABILITY.md`).
