import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { checkReadingRoutes, readerWorkOf } from '../check-links.mjs';

const CHECK_LINKS = fileURLToPath(new URL('../check-links.mjs', import.meta.url));

// Astra lane B F2: every partner manifest's reading_route must resolve to a
// real page, or the partner catalogue links to a 404.

test('reports a reading_route with no matching page', () => {
  const routes = [{ source: 'data/agamemnon/manifest.lyceum.json', readingRoute: '/aeschylus/agamemnon/book/1' }];
  const pageDirs = new Set(['/aeschylus/agamemnon']);
  const broken = checkReadingRoutes(routes, pageDirs);
  assert.equal(broken.length, 1);
  assert.deepEqual(broken[0], {
    source: 'data/agamemnon/manifest.lyceum.json',
    readingRoute: '/aeschylus/agamemnon/book/1',
  });
});

test('passes when the reading_route page exists', () => {
  const routes = [{ source: 'data/agamemnon/manifest.lyceum.json', readingRoute: '/aeschylus/agamemnon' }];
  const pageDirs = new Set(['/aeschylus/agamemnon']);
  assert.deepEqual(checkReadingRoutes(routes, pageDirs), []);
});

// A play's reader is read/<author>/<work>/ (2026-10-20); with editions on, a
// bare ?loc= is checked against that work's TLG data, so the work must come
// from the right segment.
test('names the work of a reader page under read/ and of a book page', () => {
  assert.equal(readerWorkOf('read/euripides/medea/index.html'), 'medea');
  assert.equal(readerWorkOf('aeschylus/agamemnon/book/1/index.html'), 'agamemnon');
});

test('skips a null reading_route (no reader page expected)', () => {
  const routes = [{ source: 'data/foo/manifest.lyceum.json', readingRoute: null }];
  assert.deepEqual(checkReadingRoutes(routes, new Set()), []);
});

test('fails when no partner manifests were read', () => {
  const broken = checkReadingRoutes([], new Set(['/aeschylus/agamemnon']));
  assert.equal(broken.length, 1);
  assert.equal(broken[0].reason, 'no partner manifests found');
});

// CI's fixture build runs no partner-manifest emitter (build-public.mjs does),
// so its dist has none; it passes --allow-no-partner-manifests. The default
// stays strict for a public dist.
test('CLI: a dist with no partner manifests fails unless the caller allows none', () => {
  const dist = mkdtempSync(path.join(tmpdir(), 'check-links-'));
  try {
    writeFileSync(path.join(dist, 'index.html'), '<!doctype html><title>Home</title>');
    const strict = spawnSync(process.execPath, [CHECK_LINKS, dist], { encoding: 'utf8' });
    assert.equal(strict.status, 1, strict.stdout + strict.stderr);
    assert.match(strict.stdout, /no partner manifests found/);
    const allowed = spawnSync(process.execPath, [CHECK_LINKS, dist, '--allow-no-partner-manifests'], { encoding: 'utf8' });
    assert.equal(allowed.status, 0, allowed.stdout + allowed.stderr);
    assert.match(allowed.stdout, /broken: 0/);
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
});

test('checks every route independently across a mixed batch', () => {
  const routes = [
    { source: 'data/agamemnon/manifest.lyceum.json', readingRoute: '/aeschylus/agamemnon' },
    { source: 'data/republic/manifest.lyceum.json', readingRoute: '/plato/republic/book/1' },
    { source: 'data/enchiridion/manifest.lyceum.json', readingRoute: '/read/epictetus/enchiridion/section-1' },
  ];
  const pageDirs = new Set(['/aeschylus/agamemnon', '/read/epictetus/enchiridion/section-1']);
  const broken = checkReadingRoutes(routes, pageDirs);
  assert.equal(broken.length, 1);
  assert.equal(broken[0].readingRoute, '/plato/republic/book/1');
});
