import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, readdir } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { brotliCompressSync, deflateSync } from 'node:zlib';
import { codepointsFromFont, readFontCmap } from '../sweeps/font-cmap.mjs';
import { collectJson, collectText, visibleText, parseRanges, faceCovers, parseFaces } from '../sweeps/s4-glyphs.mjs';
import { parseArgs, resolveStaticPath, contentType, listPages } from '../sweeps/s5-crawl.mjs';

async function findFont() {
  for (const root of ['/System/Library/Fonts', '/Library/Fonts']) {
    const names = await readdir(root).catch(() => []);
    for (const name of names.filter(n => /\.(ttf|otf)$/i.test(n))) {
      const file = path.join(root, name);
      try { if ((await readFontCmap(file)).has(0x41)) return file; } catch {}
    }
  }
  throw new Error('No system font with A');
}
test('reads a real system TTF or OTF cmap', async () => {
  const file = await findFont();
  assert.ok((await readFontCmap(file)).has(0x41), file);
});
test('reads a real WOFF2 from node_modules when installed', async t => {
  const root = path.join(process.cwd(), 'app/node_modules');
  async function find(dir, depth = 0) {
    if (depth > 5) return;
    for (const e of await readdir(dir, { withFileTypes: true }).catch(() => [])) {
      const p = path.join(dir, e.name);
      if (e.isFile() && e.name.endsWith('.woff2')) return p;
      if (e.isDirectory()) { const found = await find(p, depth + 1); if (found) return found; }
    }
  }
  const file = await find(root);
  if (!file) { t.skip('No WOFF2 in app/node_modules'); return; }
  assert.ok((await readFontCmap(file)).has(0x41), file);
});
test('reads synthetic WOFF2 and WOFF wrappers around a real cmap', async () => {
  const font = await readFile(await findFont());
  const n = font.readUInt16BE(4);
  let cmap;
  for (let i = 0; i < n; i++) {
    const p = 12 + i * 16;
    if (font.toString('ascii', p, p + 4) === 'cmap') cmap = font.subarray(font.readUInt32BE(p + 8), font.readUInt32BE(p + 8) + font.readUInt32BE(p + 12));
  }
  assert.ok(cmap);
  function base128(n) { const parts = [n & 127]; for (n >>>= 7; n; n >>>= 7) parts.unshift((n & 127) | 128); return Buffer.from(parts); }
  const compressed = brotliCompressSync(cmap);
  const w2 = Buffer.alloc(48); w2.write('wOF2'); w2.writeUInt16BE(1, 12); w2.writeUInt32BE(compressed.length, 20);
  assert.ok(codepointsFromFont(Buffer.concat([w2, Buffer.from([0]), base128(cmap.length), compressed])).has(0x41));
  const zip = deflateSync(cmap), w = Buffer.alloc(64); w.write('wOFF'); w.writeUInt16BE(1, 12); w.write('cmap',44); w.writeUInt32BE(64,48); w.writeUInt32BE(zip.length,52); w.writeUInt32BE(cmap.length,56);
  assert.ok(codepointsFromFont(Buffer.concat([w,zip])).has(0x41));
});
test('reads format 12 supplementary codepoints', () => {
  const cmap = Buffer.alloc(40);
  cmap.writeUInt16BE(1, 2); // one encoding record
  cmap.writeUInt16BE(3, 4); cmap.writeUInt16BE(10, 6); cmap.writeUInt32BE(12, 8);
  cmap.writeUInt16BE(12, 12); cmap.writeUInt32BE(28, 16); cmap.writeUInt32BE(1, 24);
  cmap.writeUInt32BE(0x1f600, 28); cmap.writeUInt32BE(0x1f601, 32); cmap.writeUInt32BE(1, 36);
  const font = Buffer.alloc(28); font.writeUInt16BE(1, 4); font.write('cmap', 12); font.writeUInt32BE(28, 20); font.writeUInt32BE(cmap.length, 24);
  const chars = codepointsFromFont(Buffer.concat([font, cmap]));
  assert.equal(chars.has(0x1f600), true);
  assert.equal(chars.has(0x1f601), true);
});
test('collects JSON leaves and visible HTML once on a synthetic dist', async () => {
  const dist = await mkdtemp(path.join(os.tmpdir(), 's4-fixture-'));
  await mkdir(path.join(dist, 'data/work'), { recursive: true });
  await writeFile(path.join(dist, 'data/work/lines.json'), JSON.stringify({ a: 'α & β', b: ['A', 'α'] }));
  await writeFile(path.join(dist, 'index.html'), '<!-- Z --><style>Q</style><script>R</script><p>A &amp; &#x3B1; &amp;amp;</p>');
  const data = new Map(), html = new Map();
  collectJson(data, JSON.parse(await readFile(path.join(dist, 'data/work/lines.json'))), 'data/work/lines.json');
  collectText(html, visibleText(await readFile(path.join(dist, 'index.html'), 'utf8')), 'index.html');
  assert.equal(data.get(0x3b1).count, 2);
  assert.equal(html.get(0x3b1).count, 1);
  assert.equal(html.has(0x5a), false);
  assert.equal(html.has(0x51), false);
  assert.equal(html.has(0x52), false);
  assert.equal(html.get(0x26).count, 2);
  assert.ok(data.get(0x3b1).contexts[0].length <= 80);
});
test('parses unicode ranges and requires both range and cmap', () => {
  const face = parseFaces("@font-face { font-family: 'Cardo'; font-style: italic; font-weight: 400; src: url(https://fonts.gstatic.com/x.woff2); unicode-range: U+0370-03FF,U+1F??; }")[0];
  face.cmap = new Set([0x3b1, 0x1f02, 0x41]);
  assert.deepEqual(parseRanges('U+1F??'), [[0x1f00, 0x1fff]]);
  assert.equal(faceCovers(face, 0x3b1), true);
  assert.equal(faceCovers(face, 0x41), false);
  assert.equal(faceCovers(face, 0x3b2), false);
});
test('S5 arguments, static paths, status and content types', async () => {
  assert.deepEqual(parseArgs(['--limit','2','--configs','dark-mobile','--match','foo']).configs, ['dark-mobile']);
  assert.throws(() => parseArgs(['--concurrency','0']));
  const dist = await mkdtemp(path.join(os.tmpdir(), 's5-fixture-'));
  await mkdir(path.join(dist, 'foo'));
  await writeFile(path.join(dist, 'foo/index.html'), '<h1>foo</h1>');
  await writeFile(path.join(dist, 'index.html'), '<h1>home</h1>');
  await writeFile(path.join(dist, '404.html'), '<h1>missing</h1>');
  assert.equal((await resolveStaticPath(dist, '/foo')).status, 200);
  assert.equal((await resolveStaticPath(dist, '/missing')).status, 404);
  assert.equal((await resolveStaticPath(dist, '/%2e%2e/etc/passwd')).status, 404);
  assert.equal(contentType('x.woff2'), 'font/woff2');
  assert.equal(contentType('x.webmanifest'), 'application/manifest+json');
  assert.deepEqual(await listPages(dist), ['/', '/404.html', '/foo/']);

});
