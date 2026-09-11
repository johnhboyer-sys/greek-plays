import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { verifyArtifact, FILE_COUNT_LIMIT } from '../verify-pages-artifact.mjs';

const EXPECT_ROOT = 'https://staging-data.invalid/data';

function withTmpDir(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'verify-pages-artifact-test-'));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

// Builds a minimal-but-valid artifact: index.html at root, one reader page
// under [author]/[work]/book/[n]/index.html, and an sw.js already
// substituted with EXPECT_ROOT (mirrors what postbuild-sw.mjs emits).
function writeValidArtifact(dir) {
  writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
  const bookDir = join(dir, 'plato', 'republic', 'book', '1');
  mkdirSync(bookDir, { recursive: true });
  writeFileSync(join(bookDir, 'index.html'), '<html></html>', 'utf8');
  writeFileSync(join(dir, 'sw.js'), `const DATA_ROOT = ${JSON.stringify(EXPECT_ROOT)};\n`, 'utf8');
}

test('passes on a clean, pruned artifact', () => {
  withTmpDir((dir) => {
    writeValidArtifact(dir);
    const result = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, true);
    assert.equal(result.problems.length, 0);
    assert.equal(result.count, 3); // index.html, sw.js, book/1/index.html
  });
});

test('fails when dist/data is present', () => {
  withTmpDir((dir) => {
    writeValidArtifact(dir);
    const dataDir = join(dir, 'data');
    mkdirSync(dataDir, { recursive: true });
    writeFileSync(join(dataDir, 'corpus.json'), '{}', 'utf8');
    const result = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('data') && p.includes('present')));
  });
});

test('default limit matches the plan tripwire', () => {
  assert.equal(FILE_COUNT_LIMIT, 18000);
});

test('fails when file count meets the tripwire', () => {
  withTmpDir((dir) => {
    writeValidArtifact(dir); // 3 files: index.html, sw.js, book/1/index.html
    // `limit` is injectable so this test can hit the boundary exactly
    // without writing 18,000 real files -- production callers never pass it
    // and get the real FILE_COUNT_LIMIT.
    const atLimit = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT, limit: 3 });
    assert.equal(atLimit.ok, false);
    assert.ok(atLimit.problems.some((p) => p.includes('tripwire')));

    const underLimit = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT, limit: 4 });
    assert.equal(underLimit.ok, true);
  });
});

test('fails when sw.js does not carry the expected DATA_ROOT literal', () => {
  withTmpDir((dir) => {
    writeValidArtifact(dir);
    writeFileSync(join(dir, 'sw.js'), "const DATA_ROOT = '';\n", 'utf8');
    const result = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('sw.js') && p.includes('DATA_ROOT')));
  });
});

test('fails when sw.js is missing entirely', () => {
  withTmpDir((dir) => {
    writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
    const bookDir = join(dir, 'plato', 'republic', 'book', '1');
    mkdirSync(bookDir, { recursive: true });
    writeFileSync(join(bookDir, 'index.html'), '<html></html>', 'utf8');
    const result = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('sw.js not found')));
  });
});

test('fails when no reader page exists', () => {
  withTmpDir((dir) => {
    writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
    writeFileSync(join(dir, 'sw.js'), `const DATA_ROOT = ${JSON.stringify(EXPECT_ROOT)};\n`, 'utf8');
    const authorsDir = join(dir, 'authors');
    mkdirSync(authorsDir, { recursive: true });
    writeFileSync(join(authorsDir, 'index.html'), '<html></html>', 'utf8');
    const result = verifyArtifact({ distDir: dir, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('no reader page')));
  });
});

test('fails when dist directory does not exist', () => {
  withTmpDir((dir) => {
    const missing = join(dir, 'does-not-exist');
    const result = verifyArtifact({ distDir: missing, expectDataRoot: EXPECT_ROOT });
    assert.equal(result.ok, false);
    assert.equal(result.count, null);
    assert.ok(result.problems.some((p) => p.includes('does not exist')));
  });
});

const READER_HTML =
  '<html><body><div id="toc-sidebar"></div><button class="settings-toggle">Settings</button></body></html>';

function writeRegistry(dir, routes) {
  const path = join(dir, 'route-registry.json');
  writeFileSync(
    path,
    JSON.stringify({ schema_version: 'route-registry.v1', routes }, null, 2),
    'utf8',
  );
  return path;
}

// Astra lane B, F1: single-book play-line readers live at the bare work
// route (`/aeschylus/agamemnon/`), not under `/book/1`.
test('accepts a single-book reader at the registry work route', () => {
  withTmpDir((dir) => {
    writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
    writeFileSync(join(dir, 'sw.js'), `const DATA_ROOT = ${JSON.stringify(EXPECT_ROOT)};\n`, 'utf8');
    const workDir = join(dir, 'aeschylus', 'agamemnon');
    mkdirSync(workDir, { recursive: true });
    writeFileSync(join(workDir, 'index.html'), READER_HTML, 'utf8');
    const registryPath = writeRegistry(dir, [
      { route: '/aeschylus/agamemnon', corpus: 'drama', work: 'agamemnon' },
    ]);
    const result = verifyArtifact({
      distDir: dir,
      expectDataRoot: EXPECT_ROOT,
      registryPath,
    });
    assert.equal(result.ok, true, result.problems.join('; '));
    assert.equal(result.problems.length, 0);
  });
});

test('still accepts a multi-book /book/n reader named by the registry', () => {
  withTmpDir((dir) => {
    writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
    writeFileSync(join(dir, 'sw.js'), `const DATA_ROOT = ${JSON.stringify(EXPECT_ROOT)};\n`, 'utf8');
    const bookDir = join(dir, 'plato', 'republic', 'book', '1');
    mkdirSync(bookDir, { recursive: true });
    writeFileSync(join(bookDir, 'index.html'), READER_HTML, 'utf8');
    const registryPath = writeRegistry(dir, [
      { route: '/plato/republic', corpus: 'classical', work: 'republic' },
    ]);
    const result = verifyArtifact({
      distDir: dir,
      expectDataRoot: EXPECT_ROOT,
      registryPath,
    });
    assert.equal(result.ok, true, result.problems.join('; '));
  });
});

test('rejects a registry work route whose page is not a reader', () => {
  withTmpDir((dir) => {
    writeFileSync(join(dir, 'index.html'), '<html></html>', 'utf8');
    writeFileSync(join(dir, 'sw.js'), `const DATA_ROOT = ${JSON.stringify(EXPECT_ROOT)};\n`, 'utf8');
    const workDir = join(dir, 'aeschylus', 'agamemnon');
    mkdirSync(workDir, { recursive: true });
    writeFileSync(join(workDir, 'index.html'), '<html><body>landing plate</body></html>', 'utf8');
    const registryPath = writeRegistry(dir, [
      { route: '/aeschylus/agamemnon', corpus: 'drama', work: 'agamemnon' },
    ]);
    const result = verifyArtifact({
      distDir: dir,
      expectDataRoot: EXPECT_ROOT,
      registryPath,
    });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('no reader page')));
  });
});
