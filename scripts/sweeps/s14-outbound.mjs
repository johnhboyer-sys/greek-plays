// S14: outbound links. Findings-only sweep; writes build/sweeps/s14-outbound.tsv.
// See build/sweeps/brief-tier3-checks.md.
//
// Plain Node ESM, no new dependencies, in the style of s5-crawl.mjs: reuses
// its listPages() to get the exact 1,271-page population, and Node's native
// fetch for the live checks (no undici/axios add).
import { readFile, mkdir, writeFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { listPages } from './s5-crawl.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const DIST = path.join(repo, 'app/dist');
const OUT = path.join(repo, 'build/sweeps');
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';
const TIMEOUT_MS = 20000;
const RECHECK_DELAY_MS = 10 * 60 * 1000;

function tsv(rows) { return rows.map(r => r.map(v => String(v ?? '').replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n') + '\n'; }
function decodeEntities(s) { return s.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>'); }

// ---------- 1. extraction ----------
async function extractFromHtml(urlMap) {
  const pages = await listPages(DIST);
  for (const route of pages) {
    const file = route === '/404.html' ? path.join(DIST, '404.html') : path.join(DIST, route.replace(/^\//, ''), 'index.html');
    let html;
    try { html = await readFile(file, 'utf8'); } catch { continue; }
    const seenOnPage = new Set();
    for (const m of html.matchAll(/\shref="([^"]+)"/g)) {
      const raw = decodeEntities(m[1]);
      if (!/^https?:\/\//i.test(raw)) continue;
      if (seenOnPage.has(raw)) continue;
      seenOnPage.add(raw);
      addUrl(urlMap, raw, route, 'html');
    }
  }
}

async function* walkFiles(dir) {
  let entries;
  try { entries = await readdir(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walkFiles(p);
    else if (e.isFile() && e.name.endsWith('.json')) yield p;
  }
}
async function extractFromJson(urlMap) {
  const dataDir = path.join(DIST, 'data');
  for await (const file of walkFiles(dataDir)) {
    let text;
    try { text = await readFile(file, 'utf8'); } catch { continue; }
    if (!/https?:\/\//.test(text)) continue;
    const rel = path.relative(DIST, file);
    for (const m of text.matchAll(/"(https?:\/\/[^"\\]+)"/g)) {
      addUrl(urlMap, m[1], `/${rel}`, 'json-data');
    }
  }
}
function addUrl(urlMap, url, pageId, source) {
  let entry = urlMap.get(url);
  if (!entry) { entry = { url, pages: new Set(), source }; urlMap.set(url, entry); }
  entry.pages.add(pageId);
}

// ---------- 2. per-host rate-limited GET ----------
// Per host: strictly serialized with a 1s gap after each request finishes
// before the next one starts. That's more conservative than "2 at a time,
// 1s apart" (never more than 1 in flight per host) but honors the spirit of
// the brief's rate limit and is simplest to get right for archive.org/Perseus.
const hostChains = new Map();
function withHostLimit(host, fn) {
  const prev = hostChains.get(host) || Promise.resolve();
  const runPromise = prev.then(() => fn());
  const settleThenWait = runPromise.then(() => sleep(1000), () => sleep(1000));
  hostChains.set(host, settleThenWait);
  return runPromise;
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchWithRedirects(url) {
  let current = url, hops = 0, lastStatus = null;
  const seen = new Set();
  while (hops <= 10) {
    if (seen.has(current)) return { error: 'redirect-loop', hops, finalUrl: current };
    seen.add(current);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    let res;
    try {
      res = await fetch(current, { method: 'GET', redirect: 'manual', signal: controller.signal, headers: { 'User-Agent': UA, Accept: 'text/html,*/*' } });
    } catch (e) {
      clearTimeout(timer);
      return { error: e.name === 'AbortError' ? 'timeout' : (e.cause?.code || e.message), hops, finalUrl: current };
    }
    clearTimeout(timer);
    lastStatus = res.status;
    const loc = res.headers.get('location');
    if ([301, 302, 303, 307, 308].includes(res.status) && loc && hops < 10) {
      current = new URL(loc, current).toString();
      hops++;
      continue;
    }
    let title = '', h1 = '';
    const ct = res.headers.get('content-type') || '';
    if (/text\/html/i.test(ct)) {
      try {
        const text = await res.text();
        title = (text.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] || '').replace(/\s+/g, ' ').trim();
        h1 = (text.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i)?.[1] || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      } catch {}
    } else {
      try { res.body?.cancel?.(); } catch {}
    }
    return { status: res.status, finalUrl: current, hops, title, h1 };
  }
  return { error: 'too-many-redirects', hops, finalUrl: current, status: lastStatus };
}

function classify(originalUrl, result) {
  if (result.error) return { flag: true, reason: result.error === 'timeout' ? 'timeout' : `dns/network: ${result.error}` };
  if (result.status >= 400) return { flag: true, reason: `http-${result.status}` };
  const origHost = new URL(originalUrl).host;
  const finalHost = new URL(result.finalUrl).host;
  if (result.hops > 0 && finalHost !== origHost) return { flag: true, reason: `redirect-to-other-host (${origHost} -> ${finalHost})` };
  const origPath = new URL(originalUrl).pathname.replace(/\/+$/, '');
  const finalPath = new URL(result.finalUrl).pathname.replace(/\/+$/, '');
  if (result.hops > 0 && origPath.length > 1 && (finalPath === '' || finalPath === '/')) return { flag: true, reason: 'redirect-to-homepage (moved deep link)' };
  const soft404 = /\b(not found|page not found|error 404|404 error|no such (page|item|article))\b/i;
  if (result.status === 200 && (soft404.test(result.title) || soft404.test(result.h1))) return { flag: true, reason: `soft-404 (title/h1: "${(result.title || result.h1).slice(0, 60)}")` };
  return { flag: false, reason: '' };
}

async function checkOne(url) {
  const host = new URL(url).host;
  const result = await withHostLimit(host, () => fetchWithRedirects(url));
  const cls = classify(url, result);
  return { url, ...result, ...cls };
}

async function main() {
  const urlMap = new Map();
  await extractFromHtml(urlMap);
  await extractFromJson(urlMap);
  const urls = [...urlMap.keys()].sort();
  console.log(`S14: ${urls.length} unique external URLs across ${(await listPages(DIST)).length} pages`);

  const firstPass = new Map();
  await Promise.all(urls.map(url => checkOne(url).then(r => firstPass.set(url, r))));
  const flagged = urls.filter(u => firstPass.get(u).flag);
  console.log(`S14: first pass done. ${urls.length - flagged.length} OK, ${flagged.length} flagged`);

  let recheck = new Map();
  if (flagged.length) {
    console.log(`S14: waiting ${RECHECK_DELAY_MS / 60000} min before re-checking ${flagged.length} flagged URLs...`);
    await sleep(RECHECK_DELAY_MS);
    await Promise.all(flagged.map(url => checkOne(url).then(r => recheck.set(url, r))));
    const stillFlagged = flagged.filter(u => recheck.get(u).flag);
    console.log(`S14: recheck done. ${flagged.length - stillFlagged.length} recovered, ${stillFlagged.length} confirmed broken`);
  }

  const rows = [['url', 'source', 'pages_count', 'example_page', 'status', 'final_url', 'redirect_count', 'flag_reason', 'recheck_status', 'confirmed_broken']];
  for (const url of urls) {
    const entry = urlMap.get(url);
    const r1 = firstPass.get(url);
    const r2 = recheck.get(url);
    rows.push([
      url,
      entry.source,
      entry.pages.size,
      [...entry.pages][0],
      r1.status ?? r1.error ?? '',
      r1.finalUrl ?? '',
      r1.hops ?? '',
      r1.flag ? r1.reason : '',
      r2 ? (r2.status ?? r2.error ?? '') : '',
      r2 ? (r2.flag ? 'yes' : 'no') : '',
    ]);
  }
  await mkdir(OUT, { recursive: true });
  await writeFile(path.join(OUT, 's14-outbound.tsv'), tsv(rows));
  console.log(`S14: wrote ${path.join(OUT, 's14-outbound.tsv')}`);
  console.log(`S14 SUMMARY: unique=${urls.length} ok=${urls.length - flagged.length} flagged=${flagged.length} confirmedBroken=${[...recheck.values()].filter(r => r.flag).length}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(() => { process.exitCode = 0; }).catch(e => { console.error(e); process.exitCode = 1; });
}
