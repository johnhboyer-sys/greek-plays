import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { readFontCmap } from './font-cmap.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const STYLESHEETS = [
  { url: 'https://fonts.googleapis.com/css2?family=Alegreya+Sans:wght@400;500;700&family=Alegreya+Sans+SC:wght@500;700&family=Cardo:ital,wght@0,400;0,700;1,400&display=swap', media: 'screen' },
  { url: 'https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,wght@1,600&family=DM+Mono:wght@400&display=swap', media: 'print' },
];
const chromeUA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
export function parseArgs(argv) {
  const o = { dist: path.join(repo, 'app/dist'), out: path.join(repo, 'build/sweeps'), fontsCache: path.join(repo, 'build/sweeps/fonts'), offline: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--offline') o.offline = true;
    else if (['--dist', '--out', '--fonts-cache'].includes(a) && argv[i + 1]) o[a === '--fonts-cache' ? 'fontsCache' : a.slice(2)] = path.resolve(argv[++i]);
    else throw new Error(`Unknown or incomplete argument: ${a}`);
  }
  return o;
}
export function parseRanges(value) {
  if (!value) return [[0, 0x10ffff]];
  return [...value.matchAll(/U\+([0-9a-f?]{1,6})(?:-([0-9a-f]{1,6}))?/gi)].map(([, a, b]) => {
    if (a.includes('?')) return [parseInt(a.replaceAll('?', '0'), 16), parseInt(a.replaceAll('?', 'F'), 16)];
    return [parseInt(a, 16), b ? parseInt(b, 16) : parseInt(a, 16)];
  });
}
export function parseFaces(css, media = 'screen') {
  return [...css.matchAll(/@font-face\s*\{([^}]*)\}/gi)].map(([, body]) => {
    const field = name => body.match(new RegExp(`(?:^|;)\\s*${name}\\s*:\\s*([^;]+)`, 'i'))?.[1]?.trim();
    const url = field('src')?.match(/url\(\s*['"]?([^'"\s)]+)['"]?\s*\)/i)?.[1];
    return { family: field('font-family')?.replace(/^['"]|['"]$/g, ''), style: field('font-style') || 'normal', weight: field('font-weight') || '400', ranges: parseRanges(field('unicode-range')), url, media };
  }).filter(f => f.family && f.url);
}
export function faceCovers(face, cp) { return face.ranges.some(([lo, hi]) => cp >= lo && cp <= hi) && face.cmap?.has(cp); }
const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0', ndash: '–', mdash: '—', hellip: '…', lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”', bull: '•', middot: '·', laquo: '«', raquo: '»', copy: '©', reg: '®', shy: '\u00ad' };
export function decodeEntities(text) {
  return text.replace(/&(#(?:x[0-9a-f]+|[0-9]+)|[a-z][a-z0-9]+);/gi, (whole, name) => {
    if (name[0] === '#') {
      const n = name[1]?.toLowerCase() === 'x' ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
      return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : '\ufffd';
    }
    return ENTITIES[name] ?? whole;
  });
}
export function visibleText(html) {
  return decodeEntities(html.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, ' ').replace(/<[^>]*>/g, ' '));
}
export function collectText(map, text, file) {
  const excerpt = text.replace(/\s+/g, ' ').trim();
  for (const char of text) {
    const cp = char.codePointAt(0);
    if (/\s/u.test(char) || cp < 32 || cp === 127) continue;
    let entry = map.get(cp);
    if (!entry) map.set(cp, entry = { count: 0, contexts: [] });
    entry.count++;
    const context = `${file}: ${excerpt.slice(0, Math.max(0, 80 - file.length - 2))}`;
    if (entry.contexts.length < 3 && !entry.contexts.includes(context)) entry.contexts.push(context);
  }
}
export function collectJson(map, value, file) {
  if (typeof value === 'string') collectText(map, value, file);
  else if (Array.isArray(value)) for (const item of value) collectJson(map, item, file);
  else if (value && typeof value === 'object') for (const item of Object.values(value)) collectJson(map, item, file);
}
async function* files(dir) {
  for (const ent of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) yield* files(p);
    else if (ent.isFile()) yield p;
  }
}
async function cached(url, dir, offline, ext) {
  const key = createHash('sha256').update(url).digest('hex');
  const p = path.join(dir, `${key}.${ext}`);
  try { return await readFile(p); } catch (e) { if (e.code !== 'ENOENT' || offline) throw new Error(`Missing cached ${url}: ${p}`); }
  const response = await fetch(url, { headers: { 'User-Agent': chromeUA } });
  if (!response.ok) throw new Error(`Fetch ${url}: HTTP ${response.status}`);
  const data = Buffer.from(await response.arrayBuffer());
  await writeFile(p, data);
  return data;
}
async function loadFaces(cache, offline) {
  await mkdir(cache, { recursive: true });
  const faces = [];
  for (const sheet of STYLESHEETS) faces.push(...parseFaces((await cached(sheet.url, cache, offline, 'css')).toString(), sheet.media));
  for (const face of faces) {
    if (!face.url.startsWith('https://fonts.gstatic.com/')) throw new Error(`Unexpected font URL: ${face.url}`);
    const data = await cached(face.url, cache, offline, 'woff2');
    const key = createHash('sha256').update(face.url).digest('hex');
    face.file = path.join(cache, `${key}.woff2`);
    face.cmap = await readFontCmap(face.file);
  }
  return faces;
}
function tsv(rows) { return rows.map(row => row.map(v => String(v ?? '').replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n') + '\n'; }
export async function run(options) {
  const faces = await loadFaces(options.fontsCache, options.offline);
  const data = new Map(), html = new Map();
  for await (const file of files(options.dist)) {
    const rel = path.relative(options.dist, file);
    if (rel.startsWith(`data${path.sep}`) && rel.endsWith('.json')) collectJson(data, JSON.parse(await readFile(file, 'utf8')), rel);
    if (rel.endsWith('.html')) collectText(html, visibleText(await readFile(file, 'utf8')), rel);
  }
  const selected = [
    ['Cardo 400', f => f.family === 'Cardo' && f.style === 'normal' && f.weight === '400'],
    ['Cardo 700', f => f.family === 'Cardo' && f.style === 'normal' && f.weight === '700'],
    ['Cardo italic 400', f => f.family === 'Cardo' && f.style === 'italic' && f.weight === '400'],
    ['Alegreya Sans 400', f => f.family === 'Alegreya Sans' && f.style === 'normal' && f.weight === '400'],
    ['Alegreya Sans SC 500', f => f.family === 'Alegreya Sans SC' && f.style === 'normal' && f.weight === '500'],
  ];
  const covers = (index, cp) => faces.some(f => selected[index][1](f) && faceCovers(f, cp));
  const rows = [];
  const add = (severity, category, cp, item) => rows.push({ sweep: 'S4', severity, category, page_or_font: `U+${cp.toString(16).toUpperCase().padStart(4, '0')}`, detail: `${String.fromCodePoint(cp)} count=${item.count}`, context: item.contexts });
  for (const [cp, item] of data) {
    if (!covers(0, cp)) add('fail', 'data-cardo-400', cp, item);
    if (!covers(1, cp)) add('info', 'data-cardo-700', cp, item);
    if (!covers(2, cp)) add('info', 'data-cardo-italic-400', cp, item);
  }
  for (const [cp, item] of html) if (![0, 3, 4].some(i => covers(i, cp))) add('fail', 'html-all-reading-faces', cp, item);
  await mkdir(options.out, { recursive: true });
  await writeFile(path.join(options.out, 's4-glyphs.json'), JSON.stringify({ stylesheets: STYLESHEETS, faces: faces.map(({ cmap, ...f }) => ({ ...f, glyphCount: cmap.size })), rows }, null, 2) + '\n');
  await writeFile(path.join(options.out, 's4-glyphs.tsv'), tsv([['sweep','severity','category','page_or_font','detail','context'], ...rows.map(r => [r.sweep,r.severity,r.category,r.page_or_font,r.detail,r.context.join(' | ')])]));
  const cps = new Set([...data.keys(), ...html.keys()]);
  await writeFile(path.join(options.out, 's4-codepoints.tsv'), tsv([['codepoint','character','data_count','html_count',...selected.map(x => x[0])], ...[...cps].sort((a,b) => a-b).map(cp => [`U+${cp.toString(16).toUpperCase().padStart(4,'0')}`,String.fromCodePoint(cp),data.get(cp)?.count ?? 0,html.get(cp)?.count ?? 0,...selected.map((_,i) => covers(i,cp) ? 'covered' : 'missing')])]));
  for (const category of new Set(rows.map(r => r.category))) console.log(`${category}: ${rows.filter(r => r.category === category).length} rows`);
  console.log(`S4: ${data.size} data and ${html.size} HTML codepoints; ${rows.filter(r => r.severity === 'fail').length} fail rows`);
  return rows.some(r => r.severity === 'fail') ? 1 : 0;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) run(parseArgs(process.argv.slice(2))).then(code => { process.exitCode = code; }).catch(e => { console.error(e); process.exitCode = 1; });
