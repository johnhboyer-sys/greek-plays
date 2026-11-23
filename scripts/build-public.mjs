import { existsSync, lstatSync, mkdirSync, readdirSync, rmSync, readFileSync } from 'node:fs';
import { loadYaml } from './lib/load-yaml.mjs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const MANIFESTS = join(ROOT, 'manifests');

const gitVersion = spawnSync('git', ['rev-parse', '--short', 'HEAD'], {
  cwd: ROOT,
  encoding: 'utf8',
});
if (gitVersion.error) throw gitVersion.error;
// A from-scratch repo (docs/plan.md §1: `git init`, no commits yet) has no
// HEAD to name — fall back to a placeholder rather than crash; every commit
// after the first names a real short sha here as before.
const gitSha = gitVersion.status === 0 ? gitVersion.stdout.trim() : '';
const CORPUS_VERSION = `${gitSha || 'nogit'}-${new Date().toISOString().slice(0, 10)}`;

// uv is not installed on this machine (post-wipe); the pipeline runs from its
// checked-out venv. Override with DRAMA_PY if the interpreter lives elsewhere.
const PY = process.env.DRAMA_PY ?? join(dirname(fileURLToPath(import.meta.url)), '..', 'pipeline', '.venv', 'bin', 'python');

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? ROOT,
    env: { ...process.env, ...(options.env ?? {}) },
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed with status ${result.status}`);
  }
}

function dataDirProblem(path) {
  try {
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) {
      return existsSync(path) ? null : 'data not built yet: build/dist is a dangling symlink';
    }
    if (!stat.isDirectory()) {
      return 'data not built yet: build/dist exists but is not a directory';
    }
  } catch (error) {
    if (error?.code === 'ENOENT') {
      return 'data not built yet: build/dist does not exist';
    }
    throw error;
  }
  return null;
}

const works = readdirSync(MANIFESTS)
  // authors.yaml is the corpus author roster (P2), not a work manifest.
  .filter((name) => name.endsWith('.yaml') && !name.endsWith('-public.yaml') && name !== 'authors.yaml')
  .map((name) => name.slice(0, -'.yaml'.length))
  .sort((a, b) => a.localeCompare(b));

const publicWorks = new Set(
  readdirSync(MANIFESTS)
    .filter((name) => name.endsWith('-public.yaml'))
    .map((name) => name.slice(0, -'-public.yaml'.length)),
);

// Moved ahead of its original spot (just before the Astro build) so the
// translation-seam gate below — which borrows app/'s esbuild + js-yaml —
// has them available even on a from-scratch checkout with no app/node_modules
// yet; a no-op on every other run (the directory already exists).
if (!existsSync(join(ROOT, 'app', 'node_modules'))) {
  console.log('Installing app dependencies');
  run('npm', ['ci'], { cwd: join(ROOT, 'app') });
}

// Hard gate: each manifest's duplicated registry block must agree with its
// pipeline fields. This reads YAML only, so it runs before the corpus build.
console.log('\nChecking manifest <-> registry agreement');
const { checkRegistryAgreement } = await import('./check-registry-agreement.mjs');
const { checked, agreed, problems } = await checkRegistryAgreement();
console.log(`  ${agreed}/${checked} work(s) agree, ${problems.length} problem(s)`);
if (problems.length) {
  for (const p of problems) console.error(`  ${p}`);
  process.exit(1);
}

console.log('\nVerifying sources/INVENTORY.md SHA-256 declarations');
const { verifyInventoryHashes } = await import('./verify-inventory-hashes.mjs');
const inv = verifyInventoryHashes();
for (const w of inv.warnings) console.warn(`  warning: ${w}`);
console.log(`  ${inv.verified} hash(es) verified, ${inv.problems.length} problem(s)`);
if (!inv.ok) {
  for (const p of inv.problems) console.error(`  ${p}`);
  process.exit(1);
}
// The build's two inputs from outside the repo, checked once by checksum: a
// build made with another Morpheus table or another LSJ must not pass for this
// one. Each play's Greek is corpus/greek/<play>.tsv, and its other editions are
// in sources/; stage 1 never runs Diogenes (HANDOFF-PORTABILITY.md). Before
// anything is cleaned: a failed check leaves the last build.
console.log('\nChecking the Morpheus table and the LSJ against their pins');
run(PY, ['-m', 'drama_pipeline.inputs', 'check'], {
  cwd: join(ROOT, 'pipeline'),
});

console.log('\nCleaning generated public build output');
rmSync(join(ROOT, 'build', 'dist'), { recursive: true, force: true });
// Stage 8 merges every stream left here, so a stale one must not survive.
rmSync(join(ROOT, 'build', 'ngrams'), { recursive: true, force: true });
rmSync(join(ROOT, 'app', 'dist'), { recursive: true, force: true });

if (works.length === 0) {
  console.log('\nNo works declared in manifests/ yet — building a zero-works dist');
} else {
  for (const work of works) {
    const manifest = publicWorks.has(work) ? `${work}-public.yaml` : `${work}.yaml`;
    console.log(`\nBuilding ${work} from manifests/${manifest}`);
    run(PY, ['-m', 'drama_pipeline', 'all', '--work', work, '--public'], {
      cwd: join(ROOT, 'pipeline'),
      env: { CORPUS_VERSION },
    });
    if (process.env.DRAMA_EDITIONS === '1') {
      // The public manifest declares exactly which editions may be built.
      const jsYaml = await loadYaml();
      const declaration = jsYaml.load(readFileSync(join(MANIFESTS, manifest), 'utf8'));
      for (const edition of declaration.greek_editions ?? []) {
        console.log(`Building ${work} edition ${edition.id}`);
        run(PY, ['-m', 'drama_pipeline', 'all', '--work', work, '--edition', edition.id, '--public'], {
          cwd: join(ROOT, 'pipeline'), env: { CORPUS_VERSION },
        });
      }
    }
  }
}

const dataDir = join(ROOT, 'build', 'dist');
// The pipeline only creates build/dist while emitting a work; with zero
// works declared there is nothing to emit it, so create the empty
// directory here rather than let the sanity check below fail the build.
if (works.length === 0 && !existsSync(dataDir)) {
  mkdirSync(dataDir, { recursive: true });
}
const dataProblem = dataDirProblem(dataDir);
if (dataProblem) {
  console.error(dataProblem);
  process.exit(1);
}

// Turn-align each alternate public-domain translation onto its work's reference
// turnFlow, injecting alt[<id>] into the emitted book JSON (build/dist is what
// the app reads). Runs after every work is built so the reference exists. Each
// alternate translation declares itself with a sources/<dir>/align.json config.
const SOURCES = join(ROOT, 'sources');
const alignConfigs = existsSync(SOURCES)
  ? readdirSync(SOURCES)
      .map((dir) => join(SOURCES, dir, 'align.json'))
      .filter((p) => existsSync(p))
      .sort((a, b) => a.localeCompare(b))
  : [];
if (alignConfigs.length) {
  console.log('\nTurn-aligning alternate translations');
  for (const cfg of alignConfigs) {
    run(PY, ['-m', 'drama_pipeline.align_turns', '--config', cfg], {
      cwd: join(ROOT, 'pipeline'),
    });
  }
}

// Corpus phrase counts need every reference stream and emitted translation.
// Search shards copy the finished per-work indexes. Both require a corpus.
if (works.length) {
  console.log('\nBuilding corpus phrase index');
  run(PY, ['-m', 'drama_pipeline', 'stage8'], { cwd: join(ROOT, 'pipeline') });
  console.log('\nBuilding corpus search shards');
  run(PY, ['-m', 'drama_pipeline', 'stage9'], { cwd: join(ROOT, 'pipeline') });
}

// Cross-corpus citation index (Lyceum P3 stage 3, docs/p3-plan.md Settled
// decision 5): scans build/dist for every BUILT bekker/busse-scheme work
// (classical and any mounted corpus alike) and emits build/dist/citation-
// index.json, fetched by shared/lib/data.ts's fetchCitationIndex. Runs
// after the mount step (so a mounted corpus's works are already merged in)
// and before preflight -- preflight's own dist walk reads manifests/*.yaml,
// not dist files, so an extra file here doesn't perturb it.
console.log('\nBuilding cross-corpus citation index');
run('node', [join(ROOT, 'scripts', 'build-citation-index.mjs')]);

// Cross-corpus route ownership (Lyceum P3 stage 5, docs/p3-plan.md Settled
// decision 7): generated only from the committed registry, so it can catch
// route and name collisions even when no external corpus data is mounted.
console.log('\nBuilding cross-corpus route registry');
run('node', [join(ROOT, 'scripts', 'build-registry.mjs')]);
run('node', [join(ROOT, 'scripts', 'build-route-registry.mjs')]);

console.log('\nRunning corpus preflight validation');
// With DRAMA_EDITIONS=1 the editions were built above: preflight then also
// requires every declared edition's source and emitted dir.
run(PY, ['-m', 'drama_pipeline.preflight', '--public', ...(process.env.DRAMA_EDITIONS === '1' ? ['--editions'] : []), dataDir, MANIFESTS], {
  cwd: join(ROOT, 'pipeline'),
});

console.log('\nValidating versioned data contracts');
run(PY, [
  '-m', 'drama_pipeline.validate_contracts',
  '--schemas', join(ROOT, 'schemas'),
  '--dist', dataDir,
  '--snapshot', join(ROOT, 'fixtures', 'snapshot.lyceum.json'),
  '--registry', join(ROOT, 'build', 'route-registry.json'),
], {
  cwd: join(ROOT, 'pipeline'),
});

// Partner (Lyceum Reader Manager) manifest view: derived from each work's own
// manifest.json, written into the same build/dist/<work>/ directory. Must run
// before the Astro build below -- app/public/data is a symlink to build/dist,
// so Astro only ships files that exist here by the time it walks the tree.
// Same failure contract as every other step: a non-zero exit fails the build.
console.log('\nEmitting partner-catalog (Lyceum) manifests');
run('node', [join(ROOT, 'scripts', 'emit-lyceum-manifest.mjs')]);

// P6: the Drama wing's snapshot.v1 entry (build/dist/wing.drama.json), then
// the same validator the Lyceum runs over it. Same failure contract.
console.log('\nEmitting the Drama wing snapshot entry');
run('node', [join(ROOT, 'scripts', 'emit-wing.mjs')]);
run(PY, [
  '-m', 'drama_pipeline.validate_contracts',
  '--schemas', join(ROOT, 'schemas'),
  '--snapshot', join(ROOT, 'build', 'dist', 'wing.drama.json'),
], { cwd: join(ROOT, 'pipeline') });

// Safety gate for the shared (de-duplicated) LSJ dictionary: fail the build if
// any LSJ key referenced by any work's analyses.json is missing from the shared
// build/dist/lsj shards (which would make a word popup silently show no entry).
console.log('\nVerifying shared LSJ dictionary covers every referenced key');
run(PY, ['-m', 'drama_pipeline.verify_shared_lsj'], {
  cwd: join(ROOT, 'pipeline'),
});

// The word popup's headword manifest (LSJ key -> { head, hom }). Grammata's T8
// lookup serves every dictionary ENTRY at runtime (CLAUDE.md, "Dictionary"); this
// is the only LSJ-derived file the website reads. Writes `{}` at zero works.
console.log('\nBuilding the LSJ headword manifest (lsj-heads.json)');
run('node', ['scripts/build-lsj-heads.mjs'], { cwd: join(ROOT, 'app') });

// The search page's row tables (shared/lib/row-table.ts), one per play and
// edition, beside the books in build/dist: the data root serves them where it
// serves the books. After the books are final (aligned above), before the
// Astro build copies build/dist. Fails the build where a table's English
// units disagree with the page's.
console.log('\nBuilding the search row tables (rows.json)');
run('node', [join(ROOT, 'scripts', 'build-row-tables.mjs'), dataDir]);

// (app dependencies are ensured present earlier, ahead of the translation-seam gate)

// Private (copyright-encumbered) translations are hidden by default; a
// production build only carries them if PUBLIC_SHOW_PRIVATE=1. Force it off here
// so the public deploy can never leak them — even if the caller's shell happens
// to have that var set. (See SHOW_PRIVATE in app/src/lib/works.ts.)
console.log('\nBuilding Astro app (private translations hidden)');
run('npm', ['run', 'build'], {
  cwd: join(ROOT, 'app'),
  env: { PUBLIC_SHOW_PRIVATE: '0' },
});

// Deploy gate: every internal href, fragment anchor, Bekker deep link, and
// lemma page in the emitted site must resolve. CI's `site` job runs it too,
// when it is run (HANDOFF-PORTABILITY.md says when).
//
// Runs BEFORE the data prune below, on purpose: check-links's lemma
// cross-check reads dist/data/lemmata*/_index.json (and dist/data/lemmata*/
// <slug>.json) straight off disk to verify the lexicon index and its data
// files agree. Pruning first wouldn't fail that check loudly -- it would
// silently SKIP it (check-links.mjs treats a missing index as "nothing to
// check" so a from-scratch/fixture build isn't penalized), which would let a
// real index/data mismatch ship undetected. check-links must see the
// pre-prune, full-data dist to be a meaningful gate at all.
console.log('\nChecking link integrity of the built site');
run('node', [join(ROOT, 'scripts', 'check-links.mjs'), join(ROOT, 'app', 'dist')]);

// Grammata serves dictionary entries at runtime. Local LSJ/L&S shards are
// build inputs only and must never remain in either web artifact shape.
console.log('\nRemoving local dictionary shards from the web artifact');
rmSync(join(ROOT, 'app', 'dist', 'data', 'lsj'), { recursive: true, force: true });
rmSync(join(ROOT, 'app', 'dist', 'data', 'ls'), { recursive: true, force: true });

// Pages-artifact hygiene (Lyceum P6 plan, Settled decision 3 / docs/p6-plan.md
// Stage 1): once check-links has validated the full-data dist above, prune
// the rest of dist/data when this build shipped an off-origin PUBLIC_DATA_ROOT
// (R2 serves it instead) and assert the pruned artifact is what Cloudflare
// Pages should receive. A same-origin build keeps all non-dictionary data.
if (process.env.PUBLIC_DATA_ROOT) {
  console.log('\nPruning dist/data for off-origin build (PUBLIC_DATA_ROOT set)');
  run('node', [join(ROOT, 'app', 'scripts', 'postbuild-prune-data.mjs')], {
    cwd: join(ROOT, 'app'),
  });

  console.log('\nVerifying pruned Pages artifact');
  run('node', [
    join(ROOT, 'scripts', 'verify-pages-artifact.mjs'),
    join(ROOT, 'app', 'dist'),
    '--expect-data-root', process.env.PUBLIC_DATA_ROOT,
  ]);
}
