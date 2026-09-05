#!/usr/bin/env node
// Lyceum P2 (docs/p2-plan.md §2) -- the registry GENERATOR. Reads the
// committed YAML data (manifests/*.yaml `registry:` blocks, manifests/
// authors.yaml, fixture manifests, and snapshot taxonomy) and
// emits shared/lib/registry.generated.ts, a
// gitignored ordinary static ES module exporting plain literal data:
//   CORPUS_WORKS, FIXTURE_WORKS, CORPUS_AUTHORS, FIXTURE_AUTHORS,
//   AUTHOR_PERIOD_ORDER_DATA, PERIOD_LABEL_DATA, SCHOOL_LABEL_DATA,
//   SCHOOL_GROUP_ORDER_DATA, START_HERE_DATA, WORK_CORPUS_DATA,
//   AUTHOR_WORK_GROUPS_DATA
//
// FIXTURE_* are emitted UNCONDITIONALLY, regardless of any env var here --
// stage 2's works.ts/authors.ts do their own `FIXTURES_ON ? FIXTURE_WORKS :
// []` gating at MODULE SCOPE (import.meta.env.PUBLIC_READER_FIXTURES, read
// where Vite/Astro can statically replace it). Gating here instead would
// break the vi.stubEnv fixture tests in shared/__tests__/authors.test.ts --
// see plan §2's load-bearing note. Stage 1 does not wire this file's output
// into works.ts/authors.ts at all (that's stage 2); this script exists in
// stage 1 purely so scripts/verify-registry-roundtrip.mjs has a generator to
// run and check.
//
// Object key order and array order are preserved end to end: each source is
// serialized straight from JS (JSON.parse of the snapshot / a real
// yaml.load()) into JSON.stringify'd literals below -- JSON syntax is valid
// TypeScript expression syntax, so there is no re-keying step anywhere that
// could reorder anything.
//
// Pluggable source list: yamlManifestSource reads the classical manifests.
// The Lyceum's vendored aristotleVendoredSource had no drama use and was
// removed (docs/plan.md §1).

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { loadYaml, REPO_ROOT as ROOT } from './lib/load-yaml.mjs';

const MANIFESTS = join(ROOT, 'manifests');
const FIXTURE_MANIFESTS = join(ROOT, 'fixtures', 'manifests');
const SNAPSHOT_PATH = join(ROOT, 'fixtures', 'snapshot.lyceum.json');
const OUT_PATH = join(ROOT, 'shared', 'lib', 'registry.generated.ts');

// P1 rule (plan §1 data-placement table): route ownership lives ONLY in the
// P3 route registry. The generator must never read `manifest.route` -- this
// is a hard assertion, not just a comment, since a `registry:` block that
// somehow picked up a `route` key would otherwise flow straight through.
function assertNoRoute(obj, label) {
  if (obj && typeof obj === 'object' && 'route' in obj) {
    throw new Error(
      `build-registry: ${label} carries a 'route' key -- P1 rule: route ownership is ` +
        `never read from the registry (see docs/p2-plan.md §1).`,
    );
  }
}

async function yamlManifestSource(yaml) {
  const authorsDocPath = join(MANIFESTS, 'authors.yaml');
  const authorsDoc = yaml.load(readFileSync(authorsDocPath, 'utf8'));
  if (!Array.isArray(authorsDoc?.work_order)) {
    throw new Error(`build-registry: ${authorsDocPath} has no work_order array.`);
  }

  const order = authorsDoc.work_order;
  const dupes = order.filter((id, i) => order.indexOf(id) !== i);
  if (dupes.length) {
    throw new Error(`build-registry: work_order has duplicate id(s): ${[...new Set(dupes)].join(', ')}`);
  }
  // Reverse coverage: a work manifest absent from work_order would otherwise
  // be silently excluded from the app (Sol review finding 7).
  const onDisk = readdirSync(MANIFESTS)
    .filter((n) => n.endsWith('.yaml') && !n.endsWith('-public.yaml') && n !== 'authors.yaml')
    .map((n) => n.slice(0, -'.yaml'.length));
  const unlisted = onDisk.filter((id) => !order.includes(id));
  if (unlisted.length) {
    throw new Error(`build-registry: manifest(s) not in ${authorsDocPath} work_order: ${unlisted.join(', ')}`);
  }

  const works = order.map((id) => {
    const manifestPath = join(MANIFESTS, `${id}.yaml`);
    const doc = yaml.load(readFileSync(manifestPath, 'utf8'));
    if (!doc || !doc.registry) {
      throw new Error(`build-registry: ${manifestPath} has no registry: block (run scripts/extract-registry.mjs).`);
    }
    for (const field of ['id', 'title', 'author', 'language']) {
      if (typeof doc.registry[field] !== 'string' || !doc.registry[field]) {
        throw new Error(`build-registry: ${manifestPath} registry.${field} must be a non-empty string.`);
      }
    }
    if (doc.registry.id !== id) {
      throw new Error(`build-registry: ${manifestPath} registry.id '${doc.registry.id}' != file id '${id}'.`);
    }
    assertNoRoute(doc.registry, manifestPath);
    return doc.registry;
  });

  if (!Array.isArray(authorsDoc.authors) || authorsDoc.authors.some((a) => typeof a?.id !== 'string')) {
    throw new Error(`build-registry: ${authorsDocPath} authors must be a list of objects with string ids.`);
  }
  return {
    corpusId: 'classical',
    works,
    authors: authorsDoc.authors,
    schoolGroups: authorsDoc.school_groups ?? {},
  };
}

const CORPUS_SOURCES = [yamlManifestSource];

async function loadFixtureSource(yaml) {
  const workPath = join(FIXTURE_MANIFESTS, 'sample-work.yaml');
  const authorsPath = join(FIXTURE_MANIFESTS, 'authors.yaml');
  const workDoc = yaml.load(readFileSync(workPath, 'utf8'));
  if (!workDoc || !workDoc.registry) throw new Error(`build-registry: ${workPath} has no registry: block.`);
  assertNoRoute(workDoc.registry, workPath);
  const authorsDoc = yaml.load(readFileSync(authorsPath, 'utf8'));
  if (!Array.isArray(authorsDoc?.authors) || authorsDoc.authors.length === 0) {
    throw new Error(`build-registry: ${authorsPath} has no authors[].`);
  }
  return { work: workDoc.registry, author: authorsDoc.authors[0] };
}

function loadTaxonomy() {
  const snapshot = JSON.parse(readFileSync(SNAPSHOT_PATH, 'utf8'));
  const { taxonomy, start_here: startHere = [] } = snapshot;
  if (!taxonomy) throw new Error(`build-registry: ${SNAPSHOT_PATH} has no taxonomy key (run scripts/extract-registry.mjs).`);
  if (!Array.isArray(startHere)) throw new Error(`build-registry: ${SNAPSHOT_PATH} start_here must be an array when present.`);
  const { author_period_order: authorPeriodOrder, period_label: periodLabel, school_label: schoolLabel } = taxonomy;
  if (!Array.isArray(authorPeriodOrder) || !periodLabel || !schoolLabel) {
    throw new Error(`build-registry: ${SNAPSHOT_PATH}'s taxonomy is missing author_period_order/period_label/school_label.`);
  }
  return { authorPeriodOrder, periodLabel, schoolLabel, startHere };
}

// Compile-time private-translation erasure. The app's own works.ts is a
// Vite-bundled module, so `import.meta.env.PUBLIC_SHOW_PRIVATE` folds the
// `!t.private || SHOW_PRIVATE` ternary away at build time and a private
// entry's text never reaches a public bundle. This generated file has no
// such fold -- it is a plain literal module written straight to disk by
// this script -- so a vendored `private: true` translation (the aristotle
// registry carries a few) would otherwise ship its name/text into every
// build regardless of env. Stripping it here, keyed off process.env rather
// than import.meta.env, keeps the erasure deterministic for this script's
// own runtime (tests/CI never set the flag, so they always see the
// stripped shape) and is what lets the attribution page's "everything here
// is public domain" claim hold on public builds.
function stripPrivateTranslations(works) {
  if (process.env.PUBLIC_SHOW_PRIVATE === '1') return works;
  return works.map((work) => {
    if (!Array.isArray(work.translations)) return work;
    const stripped = work.translations.filter((t) => !t?.private);
    if (stripped.length === work.translations.length) return work;
    return { ...work, translations: stripped };
  });
}

function renderExport(name, value) {
  return `export const ${name} = ${JSON.stringify(value, null, 2)};\n`;
}

async function main() {
  const yaml = await loadYaml();

  const sources = [];
  for (const loadSource of CORPUS_SOURCES) sources.push(await loadSource(yaml));
  const corpusWorks = stripPrivateTranslations(sources.flatMap((source) => source.works));
  const corpusAuthors = sources.flatMap((source) => source.authors);
  const schoolGroups = Object.assign({}, ...sources.map((source) => source.schoolGroups));
  const workCorpus = Object.fromEntries(
    sources.flatMap((source) => source.works.map((work) => [work.id, source.corpusId])),
  );
  const { work: fixtureWork, author: fixtureAuthor } = await loadFixtureSource(yaml);
  const { authorPeriodOrder, periodLabel, schoolLabel, startHere } = loadTaxonomy();
  // Vendored CATEGORIES groups (Lyceum P3's aristotle-only grouped-Works
  // rendering) had no drama use and were removed with the vendored source
  // above (docs/plan.md §1); every work is currently ungrouped.
  const authorWorkGroups = {};

  const banner =
    '// GENERATED FILE -- do not edit by hand.\n' +
    '// Run `node scripts/build-registry.mjs` (Lyceum P2, docs/p2-plan.md §2) to\n' +
    '// regenerate, from: manifests/*.yaml,\n' +
    '// fixtures/manifests/{sample-work,authors}.yaml, and fixtures/snapshot.lyceum.json\'s\n' +
    '// `taxonomy`/`start_here`. Gitignored.\n\n';

  const out =
    banner +
    renderExport('CORPUS_WORKS', corpusWorks) +
    '\n' +
    renderExport('FIXTURE_WORKS', [fixtureWork]) +
    '\n' +
    renderExport('CORPUS_AUTHORS', corpusAuthors) +
    '\n' +
    renderExport('FIXTURE_AUTHORS', [fixtureAuthor]) +
    '\n' +
    renderExport('AUTHOR_PERIOD_ORDER_DATA', authorPeriodOrder) +
    '\n' +
    renderExport('PERIOD_LABEL_DATA', periodLabel) +
    '\n' +
    renderExport('SCHOOL_LABEL_DATA', schoolLabel) +
    '\n' +
    renderExport('SCHOOL_GROUP_ORDER_DATA', schoolGroups) +
    '\n' +
    renderExport('START_HERE_DATA', startHere) +
    '\n' +
    renderExport('WORK_CORPUS_DATA', workCorpus) +
    '\n' +
    renderExport('AUTHOR_WORK_GROUPS_DATA', authorWorkGroups);

  mkdirSync(join(ROOT, 'shared', 'lib'), { recursive: true });
  writeFileSync(OUT_PATH, out);
  console.log(
    `Wrote ${OUT_PATH.replace(ROOT + '/', '')}: ${corpusWorks.length} corpus works, ` +
      `${corpusAuthors.length} corpus authors, 1 fixture work, 1 fixture author, ` +
      `0 aristotle CATEGORIES groups (vendored source removed).`,
  );
}

if (!existsSync(join(ROOT, 'shared', 'lib'))) {
  throw new Error(`build-registry: ${join(ROOT, 'shared', 'lib')} does not exist.`);
}

await main();
