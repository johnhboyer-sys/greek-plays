// node --test "scripts/__tests__/site-params.test.mjs"
// The site's origin and base path as build parameters. The failing cases come first.
// The plays already had PUBLIC_SITE_ORIGIN (optional: unset, no canonical
// origin and no sitemap); SITE_BASE is new and replaces the link check's
// READER_BASE_PATH, so one name means one thing.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { siteParams } from '../site-params.mjs';

test('an origin that is not a bare http(s) origin is refused, and the message names it', () => {
  for (const bad of ['greekdrama.example.org', 'https://example.org/reader', 'ftp://example.org', 'https://example.org?x=1',
    'https://user@example.org', ' https://example.org', 'https://example.org/#x']) {
    assert.throws(() => siteParams({ PUBLIC_SITE_ORIGIN: bad }), (e) => e.message.includes('PUBLIC_SITE_ORIGIN') && e.message.includes(JSON.stringify(bad)), bad);
  }
});

test('a base that does not start and end with "/" is refused', () => {
  for (const bad of ['mirror', '/mirror', 'mirror/', '//', '/a//b/', '/a b/', '/../', 'https://example.org/', '/a/?x', '/a/#b']) {
    assert.throws(() => siteParams({ SITE_BASE: bad }), (e) => e.message.includes('SITE_BASE') && e.message.includes(JSON.stringify(bad)), bad);
  }
});

test('unset or empty, the parameters give today\'s build: no origin, the root', () => {
  assert.deepEqual(siteParams({}), { site: undefined, base: '/' });
  assert.deepEqual(siteParams({ PUBLIC_SITE_ORIGIN: '', SITE_BASE: '' }), { site: undefined, base: '/' });
});

test('set, they are taken as given; trailing slashes on the origin are dropped, as before', () => {
  assert.deepEqual(siteParams({ PUBLIC_SITE_ORIGIN: 'https://greekdrama.johnhboyer.com' }), { site: 'https://greekdrama.johnhboyer.com', base: '/' });
  // CI's fixture build passes "https://ci-staging.example/" on purpose.
  assert.deepEqual(siteParams({ PUBLIC_SITE_ORIGIN: 'https://ci-staging.example//' }), { site: 'https://ci-staging.example', base: '/' });
  assert.deepEqual(siteParams({ PUBLIC_SITE_ORIGIN: 'http://localhost:8080', SITE_BASE: '/a/b-c_d.e~f/' }), { site: 'http://localhost:8080', base: '/a/b-c_d.e~f/' });
});

const LINKS = fileURLToPath(new URL('../check-links.mjs', import.meta.url));

test('the link check takes its base from the same parameter as the build, and no longer from READER_BASE_PATH', () => {
  const read = (env) => spawnSync(process.execPath, ['--input-type=module', '-e',
    `import { BASE } from ${JSON.stringify(LINKS)}; console.log(JSON.stringify(BASE));`],
  { encoding: 'utf8', env: { ...process.env, SITE_BASE: '', READER_BASE_PATH: '', ...env } });
  assert.equal(read({}).stdout.trim(), '""');
  assert.equal(read({ SITE_BASE: '/mirror/' }).stdout.trim(), '"/mirror"');
  assert.equal(read({ READER_BASE_PATH: '/mirror' }).stdout.trim(), '""');
  const bad = read({ SITE_BASE: 'mirror' });
  assert.notEqual(bad.status, 0);
  assert.match(bad.stderr, /SITE_BASE/);
});

// Homer's review of phase 2: under /mirror/, a root-relative link that leaves
// out the base points outside the site, though the file it names is in dist.
test('under a base, a root-relative link without the base is broken; with it, it resolves', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'links-base-'));
  try {
    const check = (href, base) => {
      writeFileSync(path.join(dir, 'index.html'), `<a href="${href}">x</a>`);
      mkdirSync(path.join(dir, 'search'), { recursive: true });
      writeFileSync(path.join(dir, 'search', 'index.html'), '<p>x</p>');
      return spawnSync(process.execPath, [LINKS, dir, '--allow-no-partner-manifests'], { encoding: 'utf8', env: { ...process.env, SITE_BASE: base } });
    };
    assert.equal(check('/search/', '/').status, 0);
    assert.equal(check('/mirror/search/', '/mirror/').status, 0);
    const r = check('/search/', '/mirror/');
    assert.equal(r.status, 1, r.stdout + r.stderr);
    assert.match(r.stdout, /broken: 1/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('robots.txt names the sitemap under the base, and only when there is an origin', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'robots-'));
  try {
    const run = (env) => {
      mkdirSync(path.join(dir, 'dist'), { recursive: true });
      writeFileSync(path.join(dir, 'dist', 'robots.txt'), 'User-agent: *\nAllow: /\n');
      const r = spawnSync(process.execPath, [fileURLToPath(new URL('../../app/scripts/postbuild-robots.mjs', import.meta.url))],
        { cwd: dir, encoding: 'utf8', env: { ...process.env, PUBLIC_SITE_ORIGIN: '', SITE_BASE: '', ...env } });
      assert.equal(r.status, 0, r.stderr);
      return spawnSync('cat', [path.join(dir, 'dist', 'robots.txt')], { encoding: 'utf8' }).stdout;
    };
    assert.equal(run({}), 'User-agent: *\nAllow: /\n');
    assert.equal(run({ PUBLIC_SITE_ORIGIN: 'https://ci-staging.example/' }),
      'User-agent: *\nAllow: /\n\nSitemap: https://ci-staging.example/sitemap-index.xml\n');
    assert.equal(run({ PUBLIC_SITE_ORIGIN: 'https://mirror.example.org', SITE_BASE: '/mirror/' }),
      'User-agent: *\nAllow: /\n\nSitemap: https://mirror.example.org/mirror/sitemap-index.xml\n');
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

// Grok's read of #18: the sitemap filter read paths as if the site were at
// the root, so under /mirror/ it kept the redirect shims and dropped the
// play pages. It now reads each path below the base.
import { inSitemap } from '../site-params.mjs';

test('the sitemap filter reads paths below the base', () => {
  for (const base of ['/', '/mirror/']) {
    const at = (p) => `https://example.org${base}${p}`;
    assert.equal(inSitemap(at(''), base), true, base);
    assert.equal(inSitemap(at('euripides/medea/'), base), true, base);          // a play's page
    assert.equal(inSitemap(at('read/euripides/medea/'), base), true, base);     // its reader
    assert.equal(inSitemap(at('euripides/'), base), true, base);
    assert.equal(inSitemap(at('texts/euripides/medea/'), base), false, base);   // an alias
    assert.equal(inSitemap(at('euripides/medea/1000/'), base), false, base);    // a citation shim
    assert.equal(inSitemap(at('read/euripides/medea/section-3/'), base), false, base);
    assert.equal(inSitemap(at('lemma/grc/entry/'), base), false, base);
  }
});
