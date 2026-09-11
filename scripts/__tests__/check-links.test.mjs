import { test } from 'node:test';
import assert from 'node:assert/strict';

import { checkReadingRoutes } from '../check-links.mjs';

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

test('skips a null reading_route (no reader page expected)', () => {
  const routes = [{ source: 'data/foo/manifest.lyceum.json', readingRoute: null }];
  assert.deepEqual(checkReadingRoutes(routes, new Set()), []);
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
