import { readFile, readdir, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createStaticServer, parseArgs as parseTier1Args } from './s5-crawl.mjs';

export const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export function parseArgs(argv, { seed = false } = {}) {
  const base = parseTier1Args([]);
  const out = { dist: '/Users/johnboyer/Developer/greek-plays/app/dist', out: base.out, match: '', limit: Infinity, seed: 1 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i], v = argv[++i];
    if (!['--dist', '--out', '--match', '--limit', ...(seed ? ['--seed'] : [])].includes(k) || !v) throw Error(`Unknown or incomplete argument: ${k}`);
    if (k === '--dist' || k === '--out') out[k.slice(2)] = path.resolve(v);
    else if (k === '--match') out.match = v;
    else { if (!/^\d+$/.test(v) || (k === '--limit' && +v < 1)) throw Error(`Invalid ${k}: ${v}`); out[k.slice(2)] = +v; }
  }
  return out;
}
export async function plays(options) {
  const entries = (await readdir(path.join(options.dist, 'data'), { withFileTypes: true })).filter(e => e.isDirectory()).map(e => e.name).sort();
  const selected = [];
  for (const id of entries) {
    if (!id.includes(options.match)) continue;
    const file = path.join(options.dist, 'data', id, 'book-01.json');
    try {
      const [book, manifest] = await Promise.all([readFile(file, 'utf8'), readFile(path.join(repo, 'manifests', `${id}.yaml`), 'utf8')]);
      const reg = manifest.slice(manifest.indexOf('\nregistry:'));
      const field = key => reg.match(new RegExp(`^  ${key}:\\s*['\"]?([^'\"\\n]+)`, 'm'))?.[1]?.trim();
      const block = reg.match(/^  translations:\s*\n([\s\S]*?)(?=^  [a-zA-Z][\w]*:|\Z)/m)?.[1] ?? '';
      const slots = [...block.matchAll(/(?:-\s*\{[^\n]*?id:\s*([^, }]+)[^\n]*?slot:\s*([^, }]+)[^\n]*?\}|-\s*id:\s*([^\n]+)([\s\S]*?)(?=\n\s*-\s*(?:id:|\{)|\n  [a-zA-Z]|$))/g)].map(m => ({ id: (m[1] ?? m[3]).trim(), slot: (m[2] ?? m[4]?.match(/slot:\s*([^\s\n]+)/)?.[1] ?? '').trim(), private: /private:\s*true/.test(m[0]) })).filter(x => x.slot && !x.private);
      selected.push({ id, author: field('author'), slug: field('slug'), title: field('title'), greekTitle: field('greekTitle'), copyAbbr: reg.match(/copyAbbr:\s*["']?([^"'\n]+)/)?.[1], slots, book: JSON.parse(book) });
      if (selected.length >= options.limit) break;
    } catch (e) { if (e.code !== 'ENOENT') throw e; }
  }
  return selected;
}
export const norm = s => String(s ?? '').replace(/\s+/g, ' ').trim();
export function slotValue(seg, slot) { return slot === 'english' ? seg.english : slot === 'secondary' ? seg.ross : slot === 'third' ? seg.third : seg.overlays?.[slot === 'overlay' ? '' : slot]; }
export function slotFor(seg, trans) { return trans.slot === 'overlay' ? seg.overlays?.[trans.id] : slotValue(seg, trans.slot); }
export function strings(v) { if (typeof v === 'string') return [v]; if (Array.isArray(v)) return v.flatMap(strings); if (v && typeof v === 'object') return Object.entries(v).filter(([k]) => !['title','credit','label','name','speaker','display','chapter','ref'].includes(k)).flatMap(([,x]) => strings(x)); return []; }
export function stripDiacritics(s) { return s.normalize('NFD').replace(/\p{M}/gu, '').normalize('NFC'); }
// Reader.svelte:2097-2133: held speaker events, >6 lines, every event chorus.
export function playOdeIds(segs) {
  const ids = new Set(); let held = [];
  for (const seg of segs) {
    const own = seg.speakers ?? []; if (own.length) held = own;
    const evs = own.length ? own : held;
    if (seg.greek.length > 6 && evs.length && evs.every(e => {
      const stem = stripDiacritics(e.label ?? '').toUpperCase();
      return stem.startsWith('ΧΟ') || stem.startsWith('ΗΜΙΧ') || stem.startsWith('ΒΑΤΡΑΧ') || (stem.startsWith('ΒΑ') && /^frogs$/i.test((e.display ?? '').trim())) || /chorus/i.test(e.display ?? '');
    })) ids.add(seg.id);
  }
  return ids;
}
export function sampleStrata(items, n = 60, seed = 1) {
  let state = seed >>> 0;
  const rand = () => ((state = (1664525 * state + 1013904223) >>> 0) / 2 ** 32);
  const cells = new Map();
  for (const item of items) {
    const cell = `${item.author}\t${item.kind}`;
    if (!cells.has(cell)) cells.set(cell, new Map());
    if (!cells.get(cell).has(item.key)) cells.get(cell).set(item.key, item);
  }
  const used = new Set();
  return [...cells].sort(([a],[b]) => a.localeCompare(b)).flatMap(([, map]) => {
    const picked = [...map.values()].map(x => ({ x, order: rand() })).sort((a,b) => a.order-b.order).filter(o => !used.has(o.x.key)).slice(0,n).map(o => o.x);
    for (const x of picked) used.add(x.key);
    return picked;
  });
}
export function probeWord(lines, otherSets, alphabet = /[\p{L}]{7,}/gu) {
  const candidates = new Map();
  for (const { text, ref } of lines) for (const m of String(text).matchAll(alphabet)) {
    const word = m[0].toLocaleLowerCase(); if (!candidates.has(word)) candidates.set(word, { word: m[0], ref });
  }
  return [...candidates.values()].sort((a,b) => otherSets.filter(s => s.has(a.word.toLocaleLowerCase())).length - otherSets.filter(s => s.has(b.word.toLocaleLowerCase())).length || b.word.length-a.word.length || a.word.localeCompare(b.word))[0] ?? null;
}
export function wordSet(lines) { return new Set(lines.flatMap(x => [...String(x.text).matchAll(/[\p{L}]{7,}/gu)].map(m => m[0].toLocaleLowerCase()))); }
export async function browserServer(dist) {
  const server = createStaticServer(dist);
  await new Promise((ok, fail) => { server.once('error', fail); server.listen(0, '127.0.0.1', ok); });
  const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || '/Users/johnboyer/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs').href);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/Users/johnboyer/Library/Caches/ms-playwright/chromium_headless_shell-local/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
  return { origin: `http://127.0.0.1:${server.address().port}`, browser, close: async () => { await browser.close(); await new Promise(ok => server.close(ok)); } };
}
export async function report(name, value, rows, out, columns = Object.keys(rows[0] ?? {})) {
  await mkdir(out, { recursive: true });
  await writeFile(path.join(out, `${name}.json`), JSON.stringify(value, null, 2)+'\n');
  const cell = v => String(v ?? '').replace(/[\t\r\n]+/g, ' ');
  await writeFile(path.join(out, `${name}.tsv`), [columns.join('\t'), ...rows.map(r => columns.map(c => cell(r[c])).join('\t'))].join('\n')+'\n');
}
export function main(meta, run) { if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(meta)) run().then(code => process.exitCode = code).catch(e => { console.error(e); process.exitCode = 1; }); }
