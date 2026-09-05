// Removes dist/data when the build shipped an off-origin PUBLIC_DATA_ROOT.
//
// astro build always copies public/data into dist/data — that copy is the
// full corpus (~555 MB, thousands of files today, growing with every wing).
// When PUBLIC_DATA_ROOT is set the app fetches corpus data from that origin
// (R2) instead, so the local copy is pure dead weight in the Pages artifact:
// it is what pushes the deploy toward Cloudflare Pages' 20,000-file cap
// (Lyceum P6 plan, Settled decision 3 / docs/p6-plan.md).
//
// NOT run as part of app's own `npm run build` chain: scripts/build-public.mjs
// runs check-links.mjs against this same dist BEFORE pruning (link checking,
// including the lemma index cross-check, needs the data files on disk), so
// build-public.mjs invokes this script itself, after check-links passes. A
// plain `npm run build` (same-origin, PUBLIC_DATA_ROOT unset, e.g. the
// zero-works/fixture builds) never needs pruning and this script no-ops.
import { existsSync, rmSync } from 'node:fs';

const root = process.env.PUBLIC_DATA_ROOT;
const DATA_DIR = 'dist/data';

if (root) {
  if (existsSync(DATA_DIR)) {
    rmSync(DATA_DIR, { recursive: true, force: true });
    console.log(`postbuild-prune-data: removed ${DATA_DIR} (PUBLIC_DATA_ROOT=${root})`);
  } else {
    console.log(`postbuild-prune-data: ${DATA_DIR} already absent (PUBLIC_DATA_ROOT=${root})`);
  }
} else {
  console.log('postbuild-prune-data: PUBLIC_DATA_ROOT unset, leaving dist/data in place');
}
