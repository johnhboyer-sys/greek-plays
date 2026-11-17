// The plays' search baseline: 14 searches run on a built site, each with the
// result bar's text, its total, its pages, and the rows page 1 draws.
// Adapted from aristotle-reader app/scripts/search-counts.mjs (origin/main,
// 16 Nov 2026) for the port of Aristotle's new search (docs/search-port/).
//
//   node docs/search-port/search-counts.mjs --base http://localhost:4321 --out counts.json
//
// The old bar reads "N lines in M plays · page X of Y". N is the page's own
// instance count (Search.svelte instCount: one per Greek hit position plus
// one per English hit, in every translation), not a count of verse lines.
// The ported bar (search port) reads "N speeches · M hits · page X of Y",
// whole in its title; the script reads either and records speeches and hits.
// Playwright comes from PW_DIR, the project, or the npx cache; the browser
// from CHROME_PATH or the installed headless shell 1228.
import { createRequire } from 'node:module';
import { existsSync, readdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
function resolvePlaywright() {
  if (process.env.PW_DIR) return require(process.env.PW_DIR);
  try { return require('playwright'); } catch {}
  const root = join(homedir(), '.npm', '_npx');
  if (existsSync(root)) for (const hash of readdirSync(root)) {
    const p = join(root, hash, 'node_modules', 'playwright');
    if (existsSync(p)) return require(p);
  }
  throw new Error('Playwright not found: set PW_DIR');
}
const SHELL = join(homedir(), 'Library', 'Caches', 'ms-playwright',
  'chromium_headless_shell-1228', 'chrome-headless-shell-mac-arm64', 'chrome-headless-shell');
const executablePath = process.env.CHROME_PATH || (existsSync(SHELL) ? SHELL : undefined);

const args = process.argv.slice(2);
const flag = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
if (!flag('--base') || !flag('--out')) throw new Error('Usage: --base URL --out FILE.json [--pages] [--extra "ctx=1&ps=20"] [--loads]');
// --pages: walk every page and record its rows (reference and link), so two
// builds can be compared row for row (compare-counts.mjs). --extra: settings
// added to every search. --loads: record the play books (book-NN.json) page 1
// fetches, with their bytes, until the network is quiet. From aristotle-reader
// app/scripts/search-counts.mjs (PR #208).
const walk = args.includes('--pages');
const loads = args.includes('--loads');
const extra = flag('--extra') ? new URLSearchParams(flag('--extra')) : null;

const queries = [
  ['Greek exact form', { g: 'δίκη' }],
  ['Greek lemma', { g: 'δίκη', m: 'lemma' }],
  ['Greek wildcard', { g: 'φιλ*' }],
  ['Beta Code typed', { g: 'dikh' }],
  ['Greek any word (lemma)', { g: 'θεός δαίμων', gm: 'any', m: 'lemma' }],
  ['Greek phrase', { g: 'ὦ Ζεῦ', gm: 'phrase' }],
  ['Accents observed', { g: 'φίλος', acc: '1' }],
  ['English', { e: 'justice' }],
  ['English phrase', { e: 'woe is me', em: 'phrase' }],
  ['English, no other forms', { e: 'god', ef: '0' }],
  ['Both, and', { g: 'δίκη', m: 'lemma', e: 'justice' }],
  ['Both, or', { g: 'δίκη', m: 'lemma', e: 'justice', op: 'or' }],
  ['Near: δίκη near θεός (lemmas)', { g: 'δίκη', m: 'lemma', n: 'l', nt: 'θεός' }],
  ['Oresteia only', { g: 'δίκη', m: 'lemma', w: 'agamemnon,libation-bearers,eumenides' }],
  ['Murray OCT edition', { g: 'δίκη', m: 'lemma', ed: 'murray-oct' }],
];

// Every page's rows, from the first to the last, by the pager's Next.
async function pageRows(page) {
  const rows = [];
  for (let i = 1; ; i++) {
    await page.waitForFunction(n => {
      const status = document.querySelector('.pager-status')?.textContent ?? '';
      return document.querySelectorAll('li.instance').length > 0 && !/Loading/.test(status)
        && (n === 1 || status.startsWith(`Page ${n} `));
    }, i, { timeout: 120000 });
    rows.push(await page.$$eval('li.instance', lis => lis.map(li => {
      const a = li.querySelector('a.inst-ref, a.cmp-ref, .cmp-ref');
      return `${a?.textContent?.trim()} ${a?.getAttribute?.('href') ?? ''}`;
    })));
    const next = page.locator('button.pager-next').first();
    if (!(await next.count()) || await next.isDisabled()) break;
    await next.click();
  }
  return rows;
}

const browser = await resolvePlaywright().chromium.launch({ headless: true, executablePath });
const results = [];
try {
  const page = await browser.newPage();
  for (const [name, params] of queries) {
    try {
      const query = new URLSearchParams(params);
      if (extra) for (const [k, v] of extra) query.set(k, v);
      const url = new URL(`/search?${query}`, flag('--base')).href;
      const books = new Map();
      const onResponse = async r => {
        const m = /\/data\/([^/]+)\/(?:ed\/[^/]+\/)?book-\d+\.json/.exec(r.url());
        if (!m) return;
        const body = await r.body().catch(() => null);
        books.set(r.url(), { play: m[1], bytes: body ? body.length : 0 });
      };
      if (loads) page.on('response', onResponse);
      await page.goto(url);
      // Done when the bar is up and page 1's rows have loaded (or an error shows).
      await page.waitForFunction(() => {
        const err = document.querySelector('.search-error');
        if (err) throw new Error(err.textContent.trim());
        const bar = document.querySelector('.result-count')?.textContent?.trim();
        if (!bar) return false;
        // The ported page draws its bar before the search ends; its live
        // region holds the count only once the search is done.
        const live = document.querySelector('p.sr-only[role="status"]');
        if (live && (!live.textContent.trim() || /Searching/.test(live.textContent))) return false;
        if (bar === 'No passages found.') return true;
        // Rows fill as books load (Aristotle's ruling D): the pager reads
        // "page 1 of …" until every book is in.
        const full = document.querySelector('.result-count').getAttribute('title') || bar;
        if (/of …/.test(full)) return false;
        const status = document.querySelector('.pager-status')?.textContent ?? '';
        return !/Loading/.test(status) && document.querySelectorAll('li.instance').length > 0;
      }, null, { timeout: 120000 });
      const counts = await page.evaluate(() => {
        const bar = document.querySelector('.result-count');
        const shown = (bar.getAttribute('title') || bar.textContent).trim().replace(/\s+/g, ' ');
        const num = v => Number(v.replaceAll(',', ''));
        const m = shown.match(/^([\d,]+) lines? in ([\d,]+) plays?/);
        const n = m ? null : shown.match(/^([\d,]+) (speech(?:es)?|hits?)(?: · ([\d,]+) hits?)?/);
        if (!m && !n && shown !== 'No passages found.') throw new Error(`Unreadable bar: ${shown}`);
        const pages = shown.match(/page \d+ of (\d+)/i);
        const rows = [...document.querySelectorAll('li.instance')];
        const speeches = n && /^speech/.test(n[2]) ? num(n[1]) : null;
        const hits = n ? (n[3] ? num(n[3]) : /^hit/.test(n[2]) ? num(n[1]) : null) : null;
        return {
          total: m ? num(m[1]) : hits ?? speeches ?? 0,
          plays: m ? num(m[2]) : null,
          speeches,
          hits,
          pages: pages ? Number(pages[1]) : m || n ? 1 : 0,
          page1_rows: rows.length,
          page1_greek_rows: rows.filter(r => r.querySelector('.inst-snippet.greek')).length,
          page1_english_rows: rows.filter(r => !r.querySelector('.inst-snippet.greek')).length,
          notes: [...document.querySelectorAll('.search-note, .sx-note')].map(n => n.textContent.trim().replace(/\s+/g, ' ')),
          shown,
        };
      });
      // A play that failed to load leaves a partial count behind a warning,
      // not an error (Search.svelte: failedWorks, pageError). Reject it.
      const failed = counts.notes.filter(n => /could not be searched|didn.t load/i.test(n));
      if (failed.length) throw new Error(`partial results: ${failed.join(' | ')}`);
      if (loads) {
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1500);
        page.off('response', onResponse);
        // A play's reader is /read/<author>/<play>: the play is the second part.
        const drawn = await page.$$eval('li.instance a.inst-ref, li.instance a.cmp-ref', as => [...new Set(as.map(a => /\/read\/[^/?#]+\/([^/?#]+)/.exec(a.getAttribute('href') ?? '')?.[1]).filter(Boolean))].sort());
        const read = [...new Set([...books.values()].map(b => b.play))].sort();
        counts.page1_loads = { books: books.size, plays: read.length, bytes: [...books.values()].reduce((n, b) => n + b.bytes, 0), drawn_plays: drawn.length, read, drawn };
      }
      if (walk) counts.rows = await pageRows(page);
      results.push({ name, url, ...counts });
      console.log(name, counts.shown, `rows ${counts.page1_rows}`);
    } catch (error) { throw new Error(`${name}: ${error.message}`, { cause: error }); }
  }
  writeFileSync(flag('--out'), JSON.stringify(results, null, 2) + '\n');
} finally { await browser.close(); }
