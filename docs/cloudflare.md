# Cloudflare

How the plays are served, and how to deploy them. Written on 2026-11-23 from
the repository (`app/wrangler.jsonc`, `app/worker/index.js`) and from what the
live site answers; what could not be confirmed that way is marked. Deploying
is John's call (CLAUDE.md).

## What runs

| Piece | What it is | Where it is set |
|---|---|---|
| Worker `greek-drama-reader` | Serves `app/dist` as static assets, data included, at `greekdrama.johnhboyer.com` (custom domain) and `greek-drama-reader.johnhboyer.workers.dev` | `app/wrangler.jsonc` |
| The Worker's script | `app/worker/index.js`, run first for `/api/*` only: `/api/feedback` takes the feedback form's POST and emails John through the `FEEDBACK` email binding, at most 3 a minute per address (`FEEDBACK_LIMIT`); any other `/api/` path goes to the assets | `app/wrangler.jsonc` (`main`, `send_email`, `ratelimits`, `run_worker_first`) |
| Account | `6ff75c6d6c06d1092df2c7efd42077ba` | `scripts/deploy-cloudflare.mjs` |

There is no R2 bucket and no data root: the site and its corpus data are one
folder and one upload. A missing page gets `404.html` with status 404
(`not_found_handling: "404-page"`), and a folder's address its `index.html`
(`html_handling: "auto-trailing-slash"`).

What the live site answered on 2026-11-23: `server: cloudflare`; the home page
with `cache-control: public, max-age=0, must-revalidate`;
`strict-transport-security: max-age=2592000`; `GET /api/feedback` 405 (the
Worker's script answers); a missing page 404; `robots.txt` naming
`https://greekdrama.johnhboyer.com/sitemap-index.xml`; 101 pages in
`sitemap-0.xml`; `data/medea/manifest.json` naming `corpus_version`
`35d4981-2026-11-23`, so live was built from `35d4981` (PR #14's merge).

Not confirmed from here: the Worker's version id, the email routing's
destination settings and sender domain, and the Web Analytics setting. They
live in the Cloudflare dashboard, which only John's login reads.

## Limits that bind a deploy (free plan)

- 20,000 files in one Worker version; a build makes about 12,200.
- 25 MiB a file.
- The Worker's script runs only for `/api/*`; static assets do not count
  against the daily request limit.

`scripts/deploy-cloudflare.mjs` refuses a build over either file limit.

## To deploy

1. Build with the deploy's settings, from the root:

   ```
   DRAMA_EDITIONS=1 PUBLIC_EDITIONS=1 PUBLIC_SITE_ORIGIN=https://greekdrama.johnhboyer.com npm run build:public
   ```

2. Rehearse, which is the default and sends nothing:

   ```
   npm run deploy:cloudflare
   ```

   It refuses a build the Worker cannot serve whole (data on another host, no
   `data/`, `data/` left out of the upload, no `feedback-endpoint.json`, too
   many or too large files), one with under 90% of live's sitemap pages, a
   broken link, or data that fails the gates the mirror bundle runs
   (preflight `--public --editions`, the data contracts, the LSJ headwords,
   the lemma pages, JSON). Then it runs `wrangler deploy --dry-run`.

3. Deploy:

   ```
   npm run deploy:cloudflare -- --deploy
   ```

   The same gates, then `wrangler deploy` from `app/`, then the deploy tag:
   `deploy/<date>` at `HEAD`, pushed to origin (`deploy/<date>.2` for a
   second deploy that day). No tag if the tree has files git does not hold as
   committed, if this commit already has a deploy tag, or with `--no-tag`. A
   tag that fails after a deploy that succeeded is reported with the two
   commands to tag by hand; the deploy stands.

`wrangler` must be logged in to John's account (`npx wrangler@4 login`).

The tag starts `.github/workflows/release.yml`: a clean build of the tagged
commit, its bundle, a check that the bundle's data is what the site serves,
and a GitHub release with the bundle and its `SHA256SUMS`.

## Before this script

Until phase 3 there was no deploy script: sessions ran a full `build:public`
and then `npx wrangler@4 deploy` from `app/` with `CLOUDFLARE_ACCOUNT_ID` set.
`scripts/deploy-cloudflare.mjs` has not yet run a real deploy
(`DEPLOY-STATUS.md`).
