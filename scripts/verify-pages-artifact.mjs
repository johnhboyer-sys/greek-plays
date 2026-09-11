#!/usr/bin/env node
// Hard gate for an R2-backed (off-origin data) Cloudflare Pages artifact
// (Lyceum P6 plan, Settled decision 3 / docs/p6-plan.md, Stage 1).
//
// Only meaningful for a build made with PUBLIC_DATA_ROOT set: it asserts the
// dist directory is the LEAN artifact that build should produce (no local
// data copy, file count safely under Cloudflare Pages' 20,000-file cap, a
// service worker that actually points at the off-origin data root, and at
// least one real reader page — not just an empty shell). The caller passes
// --expect-data-root with the exact value it built with; this script does not
// read env vars itself, so it can be pointed at any prior build's dist and
// still make a meaningful assertion.
//
// A same-origin build (PUBLIC_DATA_ROOT unset) is out of scope: it legitimately
// ships dist/data, so running this script against one is expected to fail the
// "no dist/data" check -- that failure is correct, not a bug in the gate.
import { existsSync, readFileSync, statSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(import.meta.url), '..', '..');
const FILE_COUNT_LIMIT = 18000;

function countFiles(dir) {
  let count = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = join(dir, entry.name);
    if (entry.isDirectory()) count += countFiles(child);
    else if (entry.isFile()) count += 1;
  }
  return count;
}

// Reader chrome that a landing plate / empty shell does not carry
// (ReaderShell: toc sidebar + settings). Astra lane B, F1.
function looksLikeReader(html) {
  return (
    html.includes('id="toc-sidebar"') ||
    html.includes('settings-toggle') ||
    html.includes('class="reader"') ||
    /component-url="[^"]*Reader/.test(html)
  );
}

function readerPageAt(distDir, route) {
  const rel = String(route || '').replace(/^\/+|\/+$/g, '');
  if (!rel) return false;
  const rootPage = join(distDir, rel, 'index.html');
  if (existsSync(rootPage) && looksLikeReader(readFileSync(rootPage, 'utf8'))) return true;
  const bookRoot = join(distDir, rel, 'book');
  if (!existsSync(bookRoot)) return false;
  for (const entry of readdirSync(bookRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const page = join(bookRoot, entry.name, 'index.html');
    if (existsSync(page) && looksLikeReader(readFileSync(page, 'utf8'))) return true;
  }
  return false;
}

function loadRegistryRoutes(registryPath) {
  if (!registryPath || !existsSync(registryPath)) return null;
  const doc = JSON.parse(readFileSync(registryPath, 'utf8'));
  return Array.isArray(doc?.routes) ? doc.routes : null;
}

// A reader page is one of:
//   /[author]/[work]/            — single-book play-line (route registry)
//   /[author]/[work]/book/[n]/   — every other work
// Distinct from the front-door, authors, search, and lemma routes, which
// exist even in an empty-corpus build. Astra lane B, F1.
function hasReaderPage(dir, routes = null) {
  if (Array.isArray(routes) && routes.length) {
    return routes.some((entry) => readerPageAt(dir, entry?.route));
  }
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (hasReaderPage(child)) return true;
    } else if (entry.isFile() && entry.name === 'index.html' && child.split('/').includes('book')) {
      return true;
    }
  }
  return false;
}

// `limit` defaults to the real tripwire and is only overridable so tests can
// exercise the boundary without writing 18,000 real files to a tmp dir.
function verifyArtifact({ distDir, expectDataRoot, limit = FILE_COUNT_LIMIT, registryPath }) {
  const problems = [];

  if (!existsSync(distDir) || !statSync(distDir).isDirectory()) {
    return { ok: false, count: null, problems: [`dist directory does not exist: ${distDir}`] };
  }

  const dataDir = join(distDir, 'data');
  if (existsSync(dataDir)) {
    problems.push(`${dataDir} is present -- expected pruned for an off-origin (PUBLIC_DATA_ROOT) build`);
  }

  const count = countFiles(distDir);
  if (count >= limit) {
    problems.push(`file count ${count} >= tripwire ${limit} (docs/p6-plan.md Settled decision 1)`);
  }

  const swPath = join(distDir, 'sw.js');
  if (!existsSync(swPath)) {
    problems.push(`${swPath} not found`);
  } else {
    const sw = readFileSync(swPath, 'utf8');
    // Mirrors app/scripts/postbuild-sw.mjs's own substitution exactly.
    const expected = `const DATA_ROOT = ${JSON.stringify(expectDataRoot)};`;
    if (!sw.includes(expected)) {
      problems.push(`${swPath} does not contain "${expected}" -- postbuild-sw substitution did not run or used a different root`);
    }
  }

  const routes = loadRegistryRoutes(registryPath);
  if (!hasReaderPage(distDir, routes)) {
    problems.push('no reader page (.../book/N/index.html) found under dist -- looks like an empty or failed build');
  }

  return { ok: problems.length === 0, count, problems };
}

function usage(message) {
  if (message) console.error(message);
  console.error('Usage: node scripts/verify-pages-artifact.mjs [DIST_DIR] --expect-data-root <url>');
  process.exit(2);
}

async function main() {
  const args = process.argv.slice(2);
  let distDir;
  let expectDataRoot;
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--expect-data-root') {
      i += 1;
      expectDataRoot = args[i];
    } else if (arg.startsWith('--expect-data-root=')) {
      expectDataRoot = arg.slice('--expect-data-root='.length);
    } else if (arg.startsWith('-')) {
      usage(`Unknown option: ${arg}`);
    } else if (!distDir) {
      distDir = arg;
    } else {
      usage('Specify the dist directory only once.');
    }
  }
  if (!expectDataRoot) usage('--expect-data-root <url> is required.');
  distDir = resolve(distDir || join(ROOT, 'app', 'dist'));

  const registryPath = join(ROOT, 'build', 'route-registry.json');
  const { ok, count, problems } = verifyArtifact({
    distDir,
    expectDataRoot,
    registryPath: existsSync(registryPath) ? registryPath : undefined,
  });
  console.log(`verify-pages-artifact: ${distDir}`);
  console.log(`  file count: ${count === null ? 'n/a' : count} (limit ${FILE_COUNT_LIMIT})`);
  if (ok) {
    console.log(`  OK -- no dist/data, sw.js carries PUBLIC_DATA_ROOT=${expectDataRoot}, reader pages present`);
  } else {
    for (const p of problems) console.error(`  FAIL: ${p}`);
  }
  process.exitCode = ok ? 0 : 1;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isMain) {
  main().catch((err) => {
    console.error(err.stack ?? String(err));
    process.exitCode = 1;
  });
}

export { verifyArtifact, countFiles, hasReaderPage, FILE_COUNT_LIMIT };
