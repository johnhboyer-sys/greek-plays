import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { verifyInventoryHashes } from '../verify-inventory-hashes.mjs';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));

function withTmpDir(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'verify-inventory-hashes-test-'));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function sha256(text) {
  return createHash('sha256').update(text).digest('hex');
}

// Astra lane B, F4: the inventory points at SHA256SUMS files, not inline hashes.
test('reads SHA256SUMS files referenced by the inventory', () => {
  withTmpDir((dir) => {
    mkdirSync(join(dir, 'sources', 'perseus'), { recursive: true });
    const payload = 'perseus-file\n';
    writeFileSync(join(dir, 'sources', 'perseus', 'tlg.xml'), payload);
    writeFileSync(
      join(dir, 'sources', 'perseus', 'SHA256SUMS'),
      `${sha256(payload)}  tlg.xml\n`,
    );
    const inventory =
      '# Source inventory\n\nPer-file SHA-256 in `sources/perseus/SHA256SUMS`.\n';
    const result = verifyInventoryHashes(inventory, { root: dir });
    assert.equal(result.ok, true, result.problems.join('\n'));
    assert.equal(result.verified, 1);
    assert.equal(result.problems.length, 0);
  });
});

test('reports a SHA256SUMS mismatch', () => {
  withTmpDir((dir) => {
    mkdirSync(join(dir, 'sources', 'gutenberg'), { recursive: true });
    writeFileSync(join(dir, 'sources', 'gutenberg', 'pg7700.txt'), 'actual\n');
    writeFileSync(
      join(dir, 'sources', 'gutenberg', 'SHA256SUMS'),
      `${'0'.repeat(64)}  pg7700.txt\n`,
    );
    const inventory = 'SHA-256 in `sources/gutenberg/SHA256SUMS`.\n';
    const result = verifyInventoryHashes(inventory, { root: dir });
    assert.equal(result.ok, false);
    assert.ok(result.problems.some((p) => p.includes('HASH MISMATCH')));
  });
});

test('zero declarations without an empty-source declaration is an error', () => {
  const result = verifyInventoryHashes('# inventory\n\nNo hashes here.\n', {
    root: '/tmp/does-not-need-to-exist',
  });
  assert.equal(result.ok, false);
  assert.ok(result.problems.some((p) => /zero|no declaration|empty/i.test(p)));
});

test('explicit empty source set allows zero declarations', () => {
  const result = verifyInventoryHashes(
    '# inventory\n\nempty source set — no vendored files yet.\n',
    { root: '/tmp/does-not-need-to-exist' },
  );
  assert.equal(result.ok, true);
  assert.equal(result.verified, 0);
  assert.equal(result.problems.length, 0);
});

test('build-public.mjs fails the inventory gate on !ok', () => {
  const src = readFileSync(join(SCRIPT_DIR, '..', 'build-public.mjs'), 'utf8');
  assert.match(
    src,
    /if\s*\(\s*!inv\.ok\s*\)/,
    'build-public.mjs must honor verifyInventoryHashes().ok, not only problems.length',
  );
});
