import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
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

// A play's reader page draws only its first screens into the HTML; the rest
// of the play rides in the page as the book's JSON (shared/lib/book-payload.ts),
// so a ?loc= target is found among the ids the reader draws from it.
test('CLI: a ?loc= target in the reader page\'s book payload counts as found', () => {
  const dist = mkdtempSync(path.join(tmpdir(), 'check-links-'));
  try {
    const reader = path.join(dist, 'read', 'euripides', 'medea');
    mkdirSync(reader, { recursive: true });
    const book = { book: 1, segments: [
      { id: 's1', column: '1', greek: [{ n: 1, ref: '1' }] },
      { id: 's2', column: '50', greek: [{ n: 50, ref: '50' }, { n: 51, ref: '51' }] },
    ] };
    writeFileSync(path.join(reader, 'index.html'), `<!doctype html><title>Medea</title><script type="application/json" id="book-medea-1-tlg">${JSON.stringify(book)}</script><div id="col-1"><span id="L1-1"></span></div>`);
    writeFileSync(path.join(dist, 'index.html'), '<!doctype html><title>Home</title><a href="/read/euripides/medea?loc=51">51</a><a href="/read/euripides/medea?loc=99">99</a>');
    const run = spawnSync(process.execPath, [CHECK_LINKS, dist, '--allow-no-partner-manifests'], { encoding: 'utf8' });
    assert.equal(run.status, 1, run.stdout + run.stderr);
    assert.match(run.stdout, /broken: 1/);
    assert.match(run.stdout, /loc=99/);
    assert.doesNotMatch(run.stdout, /loc=51 /);
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
});
