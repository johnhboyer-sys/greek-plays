// Screenshots of a search page at phone (390), sideways (844), and desktop
// (1440), light and dark, for John's look ruling (docs/search-port/).
//
//   node docs/search-port/shots.mjs --url URL --name NAME --out DIR [--wait SELECTOR] [--theme-attr]
//
// --wait: the selector that says the results are in (default: none, for a
// static page). --theme-attr: set html[data-theme] as well as the media
// query (the plays' ThemeInit and the mock read it). Each shot is the top of
// the page, at most about three screens, as JPEG.
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readdirSync } from 'node:fs';
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
const url = flag('--url'), name = flag('--name'), out = flag('--out'), wait = flag('--wait');
if (!url || !name || !out) throw new Error('Usage: --url URL --name NAME --out DIR [--wait SELECTOR] [--theme-attr]');
mkdirSync(out, { recursive: true });

const SIZES = [
  { id: 'phone', width: 390, height: 844, scale: 2, mobile: true, maxH: 2400 },
  { id: 'sideways', width: 844, height: 390, scale: 2, mobile: true, maxH: 1300 },
  { id: 'desktop', width: 1440, height: 900, scale: 1, mobile: false, maxH: 2000 },
];
const browser = await resolvePlaywright().chromium.launch({ headless: true, executablePath });
try {
  for (const size of SIZES) for (const theme of ['light', 'dark']) {
    const context = await browser.newContext({
      viewport: { width: size.width, height: size.height }, deviceScaleFactor: size.scale,
      isMobile: size.mobile, hasTouch: size.mobile, colorScheme: theme,
    });
    if (args.includes('--theme-attr')) {
      await context.addInitScript(t => {
        // Both readers' ThemeInit read this key.
        try { localStorage.setItem('ne-theme', t); } catch {}
        document.documentElement.setAttribute('data-theme', t);
      }, theme);
    }
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'load' });
    if (wait) await page.waitForSelector(wait, { timeout: 120000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(800);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    const file = join(out, `${name}-${size.id}-${theme}.jpg`);
    await page.screenshot({ path: file, type: 'jpeg', quality: 80, fullPage: true,
      clip: { x: 0, y: 0, width: size.width, height: Math.min(height, size.maxH) } });
    console.log(file);
    await context.close();
  }
} finally { await browser.close(); }
