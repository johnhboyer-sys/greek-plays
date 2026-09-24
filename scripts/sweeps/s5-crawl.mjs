import { createServer } from 'node:http';
import { readFile, readdir, stat, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const CONFIGS = [
  { name: 'light-mobile', theme: 'light', width: 375, height: 812, isMobile: true, hasTouch: true },
  { name: 'dark-mobile', theme: 'dark', width: 375, height: 812, isMobile: true, hasTouch: true },
  { name: 'light-desktop', theme: 'light', width: 1280, height: 800, isMobile: false, hasTouch: false },
  { name: 'dark-desktop', theme: 'dark', width: 1280, height: 800, isMobile: false, hasTouch: false },
];
export function parseArgs(argv) {
  const o = { dist: path.join(repo, 'app/dist'), out: path.join(repo, 'build/sweeps'), match: '', limit: Infinity, concurrency: 6, configs: CONFIGS.map(x => x.name) };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], v = argv[i + 1];
    if (!['--dist','--out','--match','--limit','--concurrency','--configs'].includes(a) || !v) throw new Error(`Unknown or incomplete argument: ${a}`);
    i++;
    if (a === '--dist' || a === '--out') o[a.slice(2)] = path.resolve(v);
    else if (a === '--match') o.match = v;
    else if (a === '--configs') {
      o.configs = v.split(',');
      if (!o.configs.length || o.configs.some(name => !CONFIGS.some(c => c.name === name))) throw new Error(`Invalid configs: ${v}`);
    } else {
      if (!/^\d+$/.test(v) || Number(v) < 1) throw new Error(`Invalid ${a}: ${v}`);
      o[a.slice(2)] = Number(v);
    }
  }
  return o;
}
const TYPES = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.mjs':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.json':'application/json; charset=utf-8', '.svg':'image/svg+xml', '.png':'image/png', '.webp':'image/webp', '.ico':'image/x-icon', '.webmanifest':'application/manifest+json', '.woff2':'font/woff2', '.txt':'text/plain; charset=utf-8' };
export function contentType(file) { return TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream'; }
export async function resolveStaticPath(dist, urlPath) {
  let decoded;
  try { decoded = decodeURIComponent(new URL(urlPath, 'http://localhost').pathname); } catch { return { file: path.join(dist, '404.html'), status: 404 }; }
  if (decoded.includes('\0') || decoded.split('/').includes('..') || decoded.includes('\\')) return { file: path.join(dist, '404.html'), status: 404 };
  const candidate = path.resolve(dist, '.' + decoded);
  if (candidate !== path.resolve(dist) && !candidate.startsWith(path.resolve(dist) + path.sep)) return { file: path.join(dist, '404.html'), status: 404 };
  for (const p of [candidate, path.join(candidate, 'index.html')]) {
    try { if ((await stat(p)).isFile()) return { file: p, status: 200 }; } catch (e) { if (e.code !== 'ENOENT' && e.code !== 'ENOTDIR') throw e; }
  }
  return { file: path.join(dist, '404.html'), status: 404 };
}
export function createStaticServer(dist) {
  return createServer(async (req, res) => {
    try {
      const { file, status } = await resolveStaticPath(dist, req.url || '/');
      const body = await readFile(file);
      res.writeHead(status, { 'Content-Type': contentType(file) });
      res.end(req.method === 'HEAD' ? undefined : body);
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' }); res.end(e.message);
    }
  });
}
async function* htmlFiles(dir) {
  for (const ent of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) yield* htmlFiles(p);
    else if (ent.isFile() && ent.name === 'index.html') yield p;
  }
}
export async function listPages(dist) {
  const pages = [];
  for await (const file of htmlFiles(dist)) {
    const route = path.relative(dist, path.dirname(file)).split(path.sep).filter(Boolean).join('/');
    pages.push(route ? `/${route}/` : '/');
  }
  try { if ((await stat(path.join(dist, '404.html'))).isFile()) pages.push('/404.html'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  return pages.sort();
}
export function classifyUrl(url, origin) {
  try { return new URL(url).origin === origin ? 'first-party' : 'third-party'; } catch { return 'first-party'; }
}
export function isThirdPartyOnly(message, origin) {
  const urls = message.match(/https?:\/\/[^\s)'"<>]+/g) || [];
  return urls.length > 0 && urls.every(url => classifyUrl(url, origin) === 'third-party');
}
const overflowProbe = () => {
  const width = window.innerWidth;
  const offenders = [];
  for (const el of document.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.right <= width + 1) continue;
    let clipped = false;
    for (let p = el.parentElement; p; p = p.parentElement) {
      if (['auto','scroll','hidden'].includes(getComputedStyle(p).overflowX)) { clipped = true; break; }
    }
    if (clipped) continue;
    const short = `${el.tagName.toLowerCase()}${[...el.classList].slice(0,2).map(c => '.' + CSS.escape(c)).join('')}`;
    offenders.push({ path: short, right: Math.round(rect.right) });
    if (offenders.length === 5) break;
  }
  return { overflow: document.documentElement.scrollWidth - width, offenders, theme: document.documentElement.dataset.theme || null };
};
function tsv(rows) { return rows.map(r => r.map(v => String(v ?? '').replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n') + '\n'; }
export async function run(options) {
  const pages = (await listPages(options.dist)).filter(p => p.includes(options.match)).slice(0, options.limit);
  const modulePath = process.env.PLAYWRIGHT_MODULE || '/Users/johnboyer/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs';
  const executablePath = process.env.CHROMIUM_PATH || '/Users/johnboyer/Library/Caches/ms-playwright/chromium_headless_shell-local/chrome-headless-shell-mac-arm64/chrome-headless-shell';
  const { chromium } = await import(pathToFileURL(modulePath).href);
  const server = createStaticServer(options.dist);
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  let browser;
  const rows = [], summary = [];
  try {
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch({ executablePath });
    let done = 0;
    for (const config of CONFIGS.filter(c => options.configs.includes(c.name))) {
      const context = await browser.newContext({ viewport: { width: config.width, height: config.height }, isMobile: config.isMobile, hasTouch: config.hasTouch, colorScheme: config.theme, serviceWorkers: 'block' });
      await context.addInitScript(t => { try { localStorage.setItem('ne-theme', t); } catch {} }, config.theme);
      let next = 0;
      const worker = async () => {
        while (next < pages.length) {
          const route = pages[next++], id = `${route} [${config.name}]`;
          const local = [];
          const add = (severity, category, detail, context = '') => local.push({ sweep: 'S5', severity, category, page_or_font: id, detail, context });
          let page;
          try {
            page = await context.newPage();
            page.on('console', msg => { if (msg.type() === 'error') add(isThirdPartyOnly(msg.text(), origin) ? 'info' : 'fail', 'console-error', msg.text()); });
            page.on('pageerror', err => add('fail', 'page-error', err.message));
            page.on('requestfailed', req => add(classifyUrl(req.url(), origin) === 'first-party' ? 'fail' : 'info', 'request-failed', `${req.url()} ${req.failure()?.errorText || ''}`, classifyUrl(req.url(), origin)));
            page.on('response', res => { if (res.status() >= 400 && !(route === '/404.html' && res.url() === origin + route && res.status() === 404)) add(classifyUrl(res.url(), origin) === 'first-party' ? 'fail' : 'info', 'request-failed', `${res.status()} ${res.url()}`, classifyUrl(res.url(), origin)); });
            await page.goto(origin + route, { waitUntil: 'load', timeout: 30000 });
            try { await page.waitForLoadState('networkidle', { timeout: 8000 }); }
            catch (e) { if (e.name === 'TimeoutError') add('info', 'slow-idle', 'Network idle wait exceeded 8000 ms'); else throw e; }
            const state = await page.evaluate(overflowProbe);
            if (state.theme !== config.theme) add('fail', 'theme-mismatch', `expected ${config.theme}, got ${state.theme}`);
            if (state.overflow > 1) add('fail', 'overflow', `${state.overflow}px`, state.offenders);
          } catch (e) { add('fail', e.name === 'TimeoutError' ? 'timeout' : 'crawl-error', e.message); }
          finally {
            if (page) await page.close().catch(() => {});
            rows.push(...local);
            summary.push({ page: route, config: config.name, failCount: local.filter(r => r.severity === 'fail').length });
            if (++done % 50 === 0) console.log(`S5 progress: ${done}/${pages.length * options.configs.length} page-loads`);
          }
        }
      };
      await Promise.all(Array.from({ length: Math.min(options.concurrency, pages.length) }, () => worker()));
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  await mkdir(options.out, { recursive: true });
  await writeFile(path.join(options.out, 's5-crawl.json'), JSON.stringify({ rows, summary }, null, 2) + '\n');
  await writeFile(path.join(options.out, 's5-crawl.tsv'), tsv([['sweep','severity','category','page_or_font','detail','context'], ...rows.map(r => [r.sweep,r.severity,r.category,r.page_or_font,r.detail,JSON.stringify(r.context)])]));
  await writeFile(path.join(options.out, 's5-summary.tsv'), tsv([['page','config','fail_count'], ...summary.map(r => [r.page,r.config,r.failCount])]));
  for (const category of new Set(rows.map(r => r.category))) console.log(`${category}: ${rows.filter(r => r.category === category).length} rows`);
  console.log(`S5: ${summary.length} page-loads; ${rows.filter(r => r.severity === 'fail').length} fail rows`);
  return rows.some(r => r.severity === 'fail') ? 1 : 0;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) run(parseArgs(process.argv.slice(2))).then(code => { process.exitCode = code; }).catch(e => { console.error(e); process.exitCode = 1; });
