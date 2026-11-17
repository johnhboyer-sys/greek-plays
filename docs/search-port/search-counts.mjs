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
if (!flag('--base') || !flag('--out')) throw new Error('Usage: --base URL --out FILE.json');

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

const browser = await resolvePlaywright().chromium.launch({ headless: true, executablePath });
const results = [];
try {
  const page = await browser.newPage();
  for (const [name, params] of queries) {
    try {
      const url = new URL(`/search?${new URLSearchParams(params)}`, flag('--base')).href;
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
      results.push({ name, url, ...counts });
      console.log(name, counts.shown, `rows ${counts.page1_rows}`);
    } catch (error) { throw new Error(`${name}: ${error.message}`, { cause: error }); }
  }
  writeFileSync(flag('--out'), JSON.stringify(results, null, 2) + '\n');
} finally { await browser.close(); }
