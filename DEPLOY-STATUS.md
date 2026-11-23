# Deploy status

What is live at `greekdrama.johnhboyer.com`, and from what. One line per
deploy, newest first. `docs/cloudflare.md` says how to deploy.

## Live

As read from the site on 2026-11-23: built from `35d4981` (PR #14's merge;
`data/<play>/manifest.json` names `corpus_version` `35d4981-2026-11-23`).
`main` has moved since only by PR #16, which added sweep scripts and design
files that the build does not read.

## Deploys

| Date | Commit | How | Tag | Notes |
|---|---|---|---|---|
| 2026-11-23 | `35d4981` | `build:public` and `wrangler deploy` by hand | none (no tag step then) | PRs #14 and #15: lemma accents, the lexicon's sort switch. Read from the site; the Worker's version id is recorded in a session's notes only, not confirmed here |
| 2026-11-19 | `bf4c79c` | by hand | none | The deploy the 2026-11-20 snapshot holds (its data names `bf4c79c-2026-11-19`) |
| 2026-10-24 | | by hand | none | Launch on the custom domain (`app/wrangler.jsonc`) |

Earlier deploys are not recorded here.

## The deploy script

`npm run deploy:cloudflare` (`scripts/deploy-cloudflare.mjs`, phase 3) has
not yet deployed for real. Its every branch is tested with fakes; its first
real run will be the first deploy with a `deploy/<date>` tag, and so the first
to start `release.yml`.
