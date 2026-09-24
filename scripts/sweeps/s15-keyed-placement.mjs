// REVIEW-CHECKLIST 15 audit (John, 2026-09-09, Agamemnon 195-215: Smyth's
// paragraph for the fourth antistrophe drawn five lines early). Measures,
// for every real (translator-printed) line-key tick in every play's
// line-keyed English slot, how far the rendered English start sits from its
// keyed Greek line, in Greek-line rows. Measurement only -- no fix, no
// change to Reader.svelte/speakers.ts/data/manifests.
//
// The built site is read straight from the main repo's app/dist (never
// built here); the worktree supplies only the manifests (citation.
// transpositions / repeated_refs) and this script. `app/node_modules` is a
// symlink into the main repo, so `js-yaml` (already a repo dependency, used
// elsewhere for manifest parsing) resolves from there via createRequire --
// no new dependency added.
import { readFile, readdir, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { createStaticServer } from './s5-crawl.mjs';
import { writeTsv } from './lib.mjs';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const worktreeRoot = path.resolve(scriptDir, '../..');
// The brief names this exact path: the current main-branch build, not the
// worktree (which carries no dist of its own).
const SITE_REPO = '/Users/johnboyer/Developer/greek-plays';
const DIST = path.join(SITE_REPO, 'app/dist');
const MANIFESTS_DIR = path.join(worktreeRoot, 'manifests');
const DEFAULT_OUT = path.join(SITE_REPO, 'build/sweeps');

const yamlRequire = createRequire(path.join(worktreeRoot, 'app', 'package.json'));
const yaml = yamlRequire('js-yaml');

export function parseArgs(argv = process.argv.slice(2)) {
  const o = { match: '', limit: Infinity, out: DEFAULT_OUT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], v = argv[i + 1];
    if (!['--match', '--limit', '--out'].includes(a) || v === undefined) throw new Error(`Unknown or incomplete argument: ${a}`);
    i++;
    if (a === '--match') o.match = v;
    else if (a === '--limit') { if (!/^\d+$/.test(v) || Number(v) < 1) throw new Error(`Invalid --limit: ${v}`); o.limit = Number(v); }
    else o.out = path.resolve(v);
  }
  return o;
}

// ---------------------------------------------------------------------------
// Pure helpers (unit-tested directly in scripts/__tests__/s15-keyed-
// placement.test.mjs). The in-browser measurement function below implements
// the same two algorithms again inline, because it runs inside a Playwright
// page.evaluate() sandbox that cannot import this module or close over a
// real DOM Range from Node -- see measureWork's evalInPage.
// ---------------------------------------------------------------------------

// Collapse every run of whitespace to a single space, keeping a map from
// each kept (normalized) character back to its index in the raw string --
// so a normalized-text match can be converted back to a raw offset (or, in
// the browser twin, a DOM text-node + local offset).
export function normalizeWithMap(text) {
  let normalized = '';
  const map = [];
  let prevWs = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (/\s/.test(c)) {
      if (!prevWs) { normalized += ' '; map.push(i); prevWs = true; }
    } else {
      normalized += c; map.push(i); prevWs = false;
    }
  }
  return { normalized, map };
}

// The whitespace-normalised 30-character (or shorter, near the end of the
// chunk) snippet starting at a tick's raw offset -- what we search for in
// the rendered English. null when there isn't enough text left to search
// for reliably (near-end-of-chunk tick): callers record that as
// unmeasurable rather than matching on a handful of characters.
export function snippetForOffset(rawText, offset, targetLen = 30, minLen = 12) {
  // Skip leading whitespace first, same as the reader's own tick handling
  // (Reader.svelte/speakers.ts's skipSpace) -- a tick's offset can land
  // right after the previous sentence's space, and the snippet should start
  // at the next word, not at a single collapsed space.
  let o = offset;
  while (o < rawText.length && /\s/.test(rawText[o])) o += 1;
  const { normalized, map } = normalizeWithMap(rawText);
  let normStart = map.findIndex((v) => v >= o);
  if (normStart === -1) normStart = normalized.length;
  const available = normalized.length - normStart;
  const len = Math.min(targetLen, available);
  if (len < minLen) return null;
  return normalized.slice(normStart, normStart + len);
}

// The raw-text index of a whitespace-normalised snippet's first character.
// -1 when the snippet isn't present at all. Used by the tests to exercise
// the normalization+search half of the DOM-Range matching without a DOM.
export function findSnippetRawIndex(fullRawText, normalizedSnippet) {
  const { normalized, map } = normalizeWithMap(fullRawText);
  const idx = normalized.indexOf(normalizedSnippet);
  if (idx === -1) return -1;
  return map[idx];
}

// The index, in a list of Greek-line row tops (any order), of the row
// closest to y. Ties keep the first (topmost) row, matching row order.
export function nearestRowIndex(tops, y) {
  let bestI = 0, bestD = Infinity;
  for (let i = 0; i < tops.length; i++) {
    const d = Math.abs(tops[i] - y);
    if (d < bestD) { bestD = d; bestI = i; }
  }
  return bestI;
}

// Distance, in Greek-line rows, between the row at targetIndex and whichever
// row's top is closest to y (the rendered English start's own top). 0 when
// the English lands on the keyed Greek line's own row; negative = English
// above (early), positive = below (late).
export function rowDistance(tops, targetIndex, y) {
  return nearestRowIndex(tops, y) - targetIndex;
}

// The DOM id Reader.svelte's segmentAnchorId gives each play-line segment's
// container: `col-<column>` for a column value's first segment, `col-
// <column>--<k>` for its k-th (a repeated printed ref, e.g. Seven Against
// Thebes' 803/810 doublet, gets two segments sharing one column value).
export function computeColumnIds(segments) {
  const counts = new Map();
  return segments.map((seg) => {
    const k = (counts.get(seg.column) ?? 0) + 1;
    counts.set(seg.column, k);
    return k <= 1 ? `col-${seg.column}` : `col-${seg.column}--${k}`;
  });
}

// ---------------------------------------------------------------------------
// Manifest citation data (transpositions / repeated_refs), read from the
// worktree's own manifests/ -- identical to main's at this SHA, and this is
// the one input the brief has us read from the worktree rather than dist.
// ---------------------------------------------------------------------------
async function loadCitation(workId) {
  const text = await readFile(path.join(MANIFESTS_DIR, `${workId}.yaml`), 'utf8');
  const doc = yaml.load(text) ?? {};
  const citation = doc.citation ?? {};
  return {
    transpositions: citation.transpositions?.['1'] ?? [],
    repeatedRefs: citation.repeated_refs?.['1'] ?? [],
  };
}

// A real tick's line number is inside a declared transposition block (its
// printed position doesn't match its numeric order, so "rows between" is
// ill-defined) or is a declared repeated ref (the same printed number on
// two different lines/segments) -- both flagged unmeasurable per the brief
// rather than guessed at.
function classifyRef(n, citation) {
  const num = Number(n);
  for (const b of citation.transpositions) {
    const s = Number(b.start), e = Number(b.end), before = Number(b.before);
    if ((!Number.isNaN(s) && !Number.isNaN(e) && num >= s && num <= e) || (!Number.isNaN(before) && num === before)) {
      return { reason: 'transposed-line', note: `citation.transpositions ${b.start}-${b.end} before ${b.before}` };
    }
  }
  for (const r of citation.repeatedRefs) {
    if (String(r.ref) === String(n)) return { reason: 'repeated-ref', note: r.note ? `citation.repeated_refs ${r.ref}: ${r.note}` : `citation.repeated_refs ${r.ref}` };
  }
  return null;
}

// ---------------------------------------------------------------------------
// Work discovery + tick collection (from the built data, never rebuilt).
// ---------------------------------------------------------------------------
async function discoverWorks(match, limit) {
  const dataDir = path.join(DIST, 'data');
  const entries = await readdir(dataDir, { withFileTypes: true });
  const works = [];
  for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!e.isDirectory() || !e.name.includes(match)) continue;
    try { await readFile(path.join(dataDir, e.name, 'book-01.json')); } catch { continue; }
    const manifest = JSON.parse(await readFile(path.join(dataDir, e.name, 'manifest.json'), 'utf8'));
    if (manifest.citation?.scheme !== 'play-line') continue; // this audit is play-line-only (John's rule is about the odes' line keys)
    works.push({ id: e.name, route: manifest.route, translations: manifest.translations ?? [] });
  }
  return works.slice(0, limit);
}

// Mirrors Reader.svelte's piecesFor/playEnglishSource: which segment field
// holds a slot's chunk(s), and which chunk of a multi-piece slot the reader
// actually renders (the continuation piece, or the first).
function sourceFor(seg, slotKind, overlayId) {
  if (slotKind === 'primary') {
    const e = seg.english;
    if (!e?.text?.trim()) return null;
    return { text: e.text, turns: e.turns ?? [], bekker: e.bekker ?? [] };
  }
  const pieces = slotKind === 'secondary' ? (seg.secondary ?? seg.ross ?? [])
    : slotKind === 'third' ? (seg.third ?? [])
    : (seg.overlays?.[overlayId] ?? []);
  const piece = pieces.find((p) => p.cont) ?? pieces[0];
  if (!piece?.text?.trim()) return null;
  return { text: piece.text, turns: piece.turns ?? [], bekker: piece.bekker ?? [] };
}

// Every real tick, for every slot that has at least one, across the whole
// work -- grouped by slot id. A slot with zero real ticks anywhere (every
// Aristophanes comedy today: turn-text alignment, no line markers) is
// simply absent from the map, per the brief's selection rule.
async function collectTicks(work) {
  const book = JSON.parse(await readFile(path.join(DIST, 'data', work.id, 'book-01.json'), 'utf8'));
  const segments = book.segments ?? [];
  const columnIds = computeColumnIds(segments);
  const slotDefs = work.translations.filter((t) => ['primary', 'secondary', 'third', 'overlay'].includes(t.slot));
  const bySlot = new Map();
  for (const slot of slotDefs) {
    const ticks = [];
    segments.forEach((seg, i) => {
      const src = sourceFor(seg, slot.slot, slot.id);
      if (!src) return;
      const real = (src.bekker ?? []).filter((t) => t.real);
      if (!real.length) return;
      const turnOffsets = new Set((src.turns ?? []).map((t) => t.offset));
      for (const t of real) {
        ticks.push({ columnId: columnIds[i], n: t.n, offset: t.offset, isTurnStart: turnOffsets.has(t.offset), rawText: src.text });
      }
    });
    if (ticks.length) bySlot.set(slot.id, ticks);
  }
  return bySlot;
}

// ---------------------------------------------------------------------------
// Browser measurement: one page load per (work, slot); one evaluate() call
// per page, grouped by segment, for every tick that survived pre-
// classification (transposed-line / repeated-ref).
// ---------------------------------------------------------------------------
function evalInPage({ transId, groups }) {
  function normalize(text) {
    let out = '', map = [];
    let prevWs = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (/\s/.test(c)) { if (!prevWs) { out += ' '; map.push(i); prevWs = true; } }
      else { out += c; map.push(i); prevWs = false; }
    }
    return { normalized: out, map };
  }
  function nearestRow(tops, y) {
    let bestI = 0, bestD = Infinity;
    for (let i = 0; i < tops.length; i++) { const d = Math.abs(tops[i] - y); if (d < bestD) { bestD = d; bestI = i; } }
    return bestI;
  }
  const out = [];
  for (const g of groups) {
    const seg = document.getElementById(g.columnId);
    if (!seg) { for (const t of g.ticks) out.push({ idx: t.idx, status: 'unmeasurable', reason: 'segment-missing' }); continue; }
    const greekLines = Array.from(seg.querySelectorAll('.greek-line'));
    const tops = greekLines.map((el) => el.getBoundingClientRect().top);
    const byRef = new Map();
    greekLines.forEach((el, i) => {
      const m = /^L(.+)-(\d+)(?:-c\d*)?$/.exec(el.id || '');
      if (!m) return;
      const ref = m[1].replace(/_/g, ' ');
      (byRef.get(ref) ?? byRef.set(ref, []).get(ref)).push(i);
    });
    const cols = Array.from(seg.querySelectorAll(`.english-col[data-trans="${transId}"]`));
    const nodes = [];
    let full = '';
    for (const col of cols) {
      const walker = document.createTreeWalker(col, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) { nodes.push({ node: n, start: full.length, len: n.nodeValue.length }); full += n.nodeValue; }
    }
    const { normalized, map } = normalize(full);
    function locate(rawIdx) {
      for (const rec of nodes) if (rawIdx >= rec.start && rawIdx < rec.start + rec.len) return { node: rec.node, offset: rawIdx - rec.start };
      const last = nodes[nodes.length - 1];
      return last ? { node: last.node, offset: last.len } : null;
    }
    for (const t of g.ticks) {
      const idxs = byRef.get(String(t.n));
      if (!idxs || idxs.length === 0) { out.push({ idx: t.idx, status: 'unmeasurable', reason: 'ref-absent' }); continue; }
      if (idxs.length > 1) { out.push({ idx: t.idx, status: 'unmeasurable', reason: 'ref-ambiguous-undeclared', note: `${idxs.length} DOM matches for this ref in this segment` }); continue; }
      const targetI = idxs[0];
      const normIdx = normalized.indexOf(t.snippet);
      if (normIdx === -1) { out.push({ idx: t.idx, status: 'unmeasurable', reason: 'text-not-found' }); continue; }
      const loc = locate(map[normIdx]);
      if (!loc) { out.push({ idx: t.idx, status: 'unmeasurable', reason: 'text-not-found', note: 'no text node at match' }); continue; }
      const range = document.createRange();
      range.setStart(loc.node, loc.offset);
      range.setEnd(loc.node, Math.min(loc.offset + 1, loc.node.nodeValue.length));
      const engTop = range.getBoundingClientRect().top;
      out.push({ idx: t.idx, status: 'ok', distance: nearestRow(tops, engTop) - targetI });
    }
  }
  return out;
}

async function measureWork(browser, origin, work, slotId, ticks, citation) {
  const rows = [];
  const toMeasure = [];
  for (const t of ticks) {
    const cls = classifyRef(t.n, citation);
    if (cls) { rows.push({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'unmeasurable', distance: '', note: `${cls.reason}: ${cls.note}` }); continue; }
    const snippet = snippetForOffset(t.rawText, t.offset);
    if (snippet == null) { rows.push({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'unmeasurable', distance: '', note: 'text-not-found: snippet too short (near end of chunk)' }); continue; }
    toMeasure.push({ ...t, snippet, idx: toMeasure.length });
  }
  if (!toMeasure.length) return rows;
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', serviceWorkers: 'block' });
  await context.addInitScript(() => { try { localStorage.setItem('ne-theme', 'light'); } catch { /* ignore */ } });
  const page = await context.newPage();
  try {
    const url = `${origin}${work.route}/?view=both&trans=${encodeURIComponent(slotId)}`;
    await page.goto(url, { waitUntil: 'load', timeout: 60000 });
    try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch { /* large static page: proceed anyway */ }
    await page.evaluate(() => (document.fonts && document.fonts.ready) ? document.fonts.ready : null);
    await page.waitForTimeout(400); // let playFlow's ResizeObserver/setTimeout(0) settle
    const groups = new Map();
    for (const t of toMeasure) {
      if (!groups.has(t.columnId)) groups.set(t.columnId, []);
      groups.get(t.columnId).push({ idx: t.idx, n: t.n, snippet: t.snippet });
    }
    const evalResults = await page.evaluate(evalInPage, { transId: slotId, groups: [...groups.entries()].map(([columnId, gticks]) => ({ columnId, ticks: gticks })) });
    const byIdx = new Map(evalResults.map((r) => [r.idx, r]));
    for (const t of toMeasure) {
      const r = byIdx.get(t.idx);
      if (!r) { rows.push({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'unmeasurable', distance: '', note: 'no result from page' }); continue; }
      if (r.status === 'ok') rows.push({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'ok', distance: r.distance, note: '' });
      else rows.push({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'unmeasurable', distance: '', note: r.note ? `${r.reason}: ${r.note}` : r.reason });
    }
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
  }
  return rows;
}

function buildSummary(rows) {
  const groups = new Map();
  for (const r of rows) {
    const key = `${r.play}\u0000${r.slot}`;
    if (!groups.has(key)) groups.set(key, { play: r.play, slot: r.slot, ticks_measured: 0, d_le_1: 0, d_gt_1: 0, unmeasurable: 0, max_abs_d: 0 });
    const g = groups.get(key);
    g.ticks_measured += 1;
    if (r.status === 'ok') {
      const ad = Math.abs(Number(r.distance));
      if (ad <= 1) g.d_le_1 += 1; else g.d_gt_1 += 1;
      if (ad > g.max_abs_d) g.max_abs_d = ad;
    } else {
      g.unmeasurable += 1;
    }
  }
  return [...groups.values()].sort((a, b) => a.play.localeCompare(b.play) || a.slot.localeCompare(b.slot));
}

export async function run(args = parseArgs()) {
  const works = await discoverWorks(args.match, args.limit);
  const modulePath = process.env.PLAYWRIGHT_MODULE || '/Users/johnboyer/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs';
  const executablePath = process.env.CHROMIUM_PATH || '/Users/johnboyer/Library/Caches/ms-playwright/chromium_headless_shell-local/chrome-headless-shell-mac-arm64/chrome-headless-shell';
  const { chromium } = await import(pathToFileURL(modulePath).href);
  const server = createStaticServer(DIST);
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ executablePath });
  const rows = [];
  try {
    const jobs = [];
    for (const work of works) {
      const bySlot = await collectTicks(work);
      for (const [slotId, ticks] of bySlot) jobs.push({ work, slotId, ticks });
    }
    const citationCache = new Map();
    const citationFor = async (workId) => {
      if (!citationCache.has(workId)) citationCache.set(workId, await loadCitation(workId).catch(() => ({ transpositions: [], repeatedRefs: [] })));
      return citationCache.get(workId);
    };
    let next = 0;
    const worker = async () => {
      while (next < jobs.length) {
        const job = jobs[next++];
        const citation = await citationFor(job.work.id);
        let jobRows;
        try {
          jobRows = await measureWork(browser, origin, job.work, job.slotId, job.ticks, citation);
        } catch (e) {
          jobRows = job.ticks.map((t) => ({ n: t.n, offset: t.offset, isTurnStart: t.isTurnStart, status: 'unmeasurable', distance: '', note: `page-error: ${e.message || e}` }));
        }
        for (const r of jobRows) rows.push({ play: job.work.id, slot: job.slotId, n: r.n, offset: r.offset, is_turn_start: r.isTurnStart, distance: r.distance, status: r.status, note: r.note });
        console.log(`S15: ${job.work.id} ${job.slotId}: ${jobRows.length} ticks`);
      }
    };
    await Promise.all(Array.from({ length: Math.min(4, jobs.length || 1) }, worker));
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
  await mkdir(args.out, { recursive: true });
  await writeTsv(path.join(args.out, 's15-keyed-placement.tsv'), rows, ['play', 'slot', 'n', 'offset', 'is_turn_start', 'distance', 'status', 'note']);
  const summary = buildSummary(rows);
  await writeTsv(path.join(args.out, 's15-keyed-placement-summary.tsv'), summary, ['play', 'slot', 'ticks_measured', 'd_le_1', 'd_gt_1', 'unmeasurable', 'max_abs_d']);
  const measured = rows.filter((r) => r.status === 'ok');
  const bad = measured.filter((r) => Math.abs(Number(r.distance)) > 1);
  console.log(`S15: ${rows.length} ticks; ${measured.length} measured (${bad.length} with |d|>1); ${rows.length - measured.length} unmeasurable`);
  const agRows = rows.filter((r) => r.play === 'agamemnon' && Number(r.n) >= 195 && Number(r.n) <= 250);
  if (agRows.length) console.log('S15: Agamemnon 195-250:', JSON.stringify(agRows));
  return bad.length ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  run(parseArgs(process.argv.slice(2))).then((code) => { process.exitCode = code; }).catch((e) => { console.error(e); process.exitCode = 1; });
}
