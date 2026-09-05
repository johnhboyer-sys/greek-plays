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
