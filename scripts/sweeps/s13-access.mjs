// S13: access and devices. Findings-only sweep script; writes
// build/sweeps/s13-access.tsv (+ .json). See build/sweeps/brief-tier3-checks.md.
//
// Plain Node ESM, no new dependencies, in the style of s5-crawl.mjs: reuses
// its createStaticServer, and the same Playwright-by-path / axe-by-path
// convention.
import { readFile, mkdir, writeFile, unlink } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createStaticServer } from './s5-crawl.mjs';

const execFileP = promisify(execFile);
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const DIST = path.join(repo, 'app/dist');
const OUT = path.join(repo, 'build/sweeps');
const PLAYWRIGHT_MODULE = process.env.PLAYWRIGHT_MODULE || '/Users/johnboyer/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/Users/johnboyer/Library/Caches/ms-playwright/chromium_headless_shell-local/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const AXE_PATH = '/Users/johnboyer/.npm/_npx/0f94ee7615faf582/node_modules/axe-core/axe.min.js';
const LIGHTHOUSE_CLI = '/Users/johnboyer/.npm/_npx/0f94ee7615faf582/node_modules/lighthouse/cli/index.js';

const DEVICE_CONFIGS = [
  { name: 'light-desktop', theme: 'light', width: 1280, height: 900, isMobile: false, hasTouch: false },
  { name: 'dark-desktop', theme: 'dark', width: 1280, height: 900, isMobile: false, hasTouch: false },
  { name: 'light-phone', theme: 'light', width: 375, height: 812, isMobile: true, hasTouch: true },
  { name: 'dark-phone', theme: 'dark', width: 375, height: 812, isMobile: true, hasTouch: true },
];

const report = { generatedAt: new Date().toISOString(), axeByPage: [], axeSummary: [], keyboard: [], lang: [], speakerContrast: { light: null, dark: null, flagged: [] }, weight: [], lighthouse: null, manualChecks: [] };

function tsv(rows) { return rows.map(r => r.map(v => String(v ?? '').replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n') + '\n'; }

async function findLemmaPath() {
  try {
    const html = await readFile(path.join(DIST, 'lemma/grc/index.html'), 'utf8');
    const m = html.match(/href="([^"]*\/lemma\/grc\/entry\/\?w=[^"]+)"/);
    if (m) { const u = new URL(m[1], 'http://x'); return u.pathname + u.search; }
  } catch {}
  return '/lemma/grc/entry/?w=a';
}

function buildPageTypes(lemmaPath) {
  return [
    { id: 'home', path: '/' },
    { id: 'author-euripides', path: '/euripides/' },
    { id: 'play-both', path: '/aeschylus/agamemnon/' },
    { id: 'play-english', path: '/aeschylus/agamemnon/?view=english' },
    { id: 'play-greek', path: '/aeschylus/agamemnon/?view=greek' },
    { id: 'play-compare', path: '/aeschylus/agamemnon/', setup: setupCompare },
    { id: 'search', path: '/search/?q=Clytemnestra' },
    { id: 'lemma', path: lemmaPath },
    { id: 'attribution', path: '/attribution/' },
    { id: 'support', path: '/support/' },
    { id: '404', path: '/404.html' },
  ];
}

async function setupCompare(page) {
  await page.click('.settings-toggle', { timeout: 5000 }).catch(() => {});
  await page.waitForSelector('.settings-sidebar.open', { timeout: 5000 }).catch(() => {});
  const radios = page.locator('input[name="trans-mode"]');
  const count = await radios.count().catch(() => 0);
  if (count >= 2) await radios.nth(1).click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(150);
  await page.click('.settings-close', { timeout: 5000 }).catch(() => {});
}

// ---------- S13.1 axe ----------
async function runAxe(browser, origin, pageTypes) {
  const axeSrc = await readFile(AXE_PATH, 'utf8');
  const agg = new Map();
  for (const cfg of DEVICE_CONFIGS) {
    const context = await browser.newContext({ viewport: { width: cfg.width, height: cfg.height }, isMobile: cfg.isMobile, hasTouch: cfg.hasTouch, colorScheme: cfg.theme, serviceWorkers: 'block' });
    await context.addInitScript(t => { try { localStorage.setItem('ne-theme', t); } catch {} }, cfg.theme);
    for (const pt of pageTypes) {
      const page = await context.newPage();
      try {
        await page.goto(origin + pt.path, { waitUntil: 'load', timeout: 30000 });
        if (pt.setup) await pt.setup(page);
        try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
        await page.addScriptTag({ content: axeSrc });
        const results = await page.evaluate(() => window.axe.run(document, { resultTypes: ['violations'] }));
        for (const v of results.violations) {
          const key = `${v.id}|${v.impact}`;
          if (!agg.has(key)) agg.set(key, { rule: v.id, impact: v.impact, help: v.help, nodeCount: 0, pages: new Set(), example: v.nodes[0]?.target?.join(' ') ?? '', examplePage: `${pt.id} [${cfg.name}]` });
          const entry = agg.get(key);
          entry.nodeCount += v.nodes.length;
          entry.pages.add(`${pt.id} [${cfg.name}]`);
        }
        report.axeByPage.push({ page: pt.id, config: cfg.name, violationCount: results.violations.length, rules: results.violations.map(v => v.id) });
        console.log(`S13 axe: ${pt.id} [${cfg.name}] -> ${results.violations.length} violation rules`);
      } catch (e) {
        report.axeByPage.push({ page: pt.id, config: cfg.name, error: e.message });
        console.log(`S13 axe: ${pt.id} [${cfg.name}] -> ERROR ${e.message}`);
      } finally { await page.close().catch(() => {}); }
    }
    await context.close();
  }
  report.axeSummary = [...agg.values()]
    .map(e => ({ rule: e.rule, impact: e.impact, help: e.help, nodeCount: e.nodeCount, pagesAffected: e.pages.size, pages: [...e.pages], example: e.example, examplePage: e.examplePage }))
    .sort((a, b) => (sevRank(b.impact) - sevRank(a.impact)) || (b.pagesAffected - a.pagesAffected));
}
function sevRank(impact) { return { critical: 4, serious: 3, moderate: 2, minor: 1 }[impact] ?? 0; }

// ---------- S13.2 keyboard-only ----------
async function describeActive(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body || el === document.documentElement) return { tag: 'body' };
    const rect = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const label = el.closest('label');
    return {
      tag: el.tagName.toLowerCase(),
      cls: typeof el.className === 'string' ? el.className : '',
      role: el.getAttribute('role') || '',
      ariaLabel: el.getAttribute('aria-label') || '',
      ariaExpanded: el.getAttribute('aria-expanded'),
      ariaPressed: el.getAttribute('aria-pressed'),
      name: el.getAttribute('name') || '',
      type: el.getAttribute('type') || '',
      href: el.getAttribute('href') || '',
      text: (el.textContent || '').trim().slice(0, 50),
      labelText: label ? label.textContent.trim().slice(0, 50) : '',
      inViewToggle: !!el.closest('.view-toggle'),
      visible: rect.width > 0 && rect.height > 0,
      focusVisible: !(cs.outlineStyle === 'none' && (cs.boxShadow === 'none' || cs.boxShadow === '')),
    };
  });
}
const cls = info => (info.cls || '').split(/\s+/).filter(Boolean);
// A footnote marker opens its FootnotePopup on FOCUS, not click (Reader.svelte
// on:focus={onFootnoteFocus}), and FootnotePopup steals focus into itself on
// mount (FootnotePopup.svelte onMount -> dialogEl.focus()). So a plain Tab walk
// through footnote-dense text keeps getting diverted into these popups. Real
// finding (see the S13 return write-up), but it also has to be worked around
// here or a forward search past footnote markers never terminates. Escape
// dismisses the popup and restores focus to the marker (onDestroy), so we
// recover by escaping and continuing.
async function tabTo(page, matcher, { max = 100, shift = false } = {}) {
  let trapEscapes = 0;
  for (let i = 1; i <= max; i++) {
    await page.keyboard.press(shift ? 'Shift+Tab' : 'Tab');
    let info = await describeActive(page);
    if (info && (cls(info).includes('popup-close') || (info.role === 'dialog' && cls(info).includes('footnote-popup')))) {
      trapEscapes++;
      await page.keyboard.press('Escape');
      await page.waitForTimeout(60);
      continue;
    }
    if (info && info.tag !== 'body' && matcher(info)) return { found: true, steps: i, info, trapEscapes };
  }
  return { found: false, steps: max, info: null, trapEscapes };
}
async function freshPage(browser, origin, path = '/aeschylus/agamemnon/') {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', serviceWorkers: 'block' });
  await context.addInitScript(t => { try { localStorage.setItem('ne-theme', t); } catch {} }, 'light');
  const page = await context.newPage();
  await page.goto(origin + path, { waitUntil: 'load', timeout: 30000 });
  try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
  return { context, page };
}

// Each lettered step below gets its OWN fresh page load: "key presses it took"
// is measured per step from page load, and steps stay independent of each
// other's outcome (a failure in one can't cascade and starve the others of
// their Tab budget). closeSettings() also restores focus to .settings-toggle,
// so within a step, subsequent sub-searches can rely on that.
async function runKeyboard(browser, origin) {
  const log = (step, label, detail) => { report.keyboard.push({ step, label, ...detail }); console.log(`S13 keyboard ${step}: ${detail.result} - ${label}`); };

  // (a) open/close settings sidebar
  {
    const { context, page } = await freshPage(browser, origin);
    const rToggle = await tabTo(page, i => cls(i).includes('settings-toggle'), { max: 40 });
    if (!rToggle.found) {
      log('a', 'open/close settings sidebar', { result: 'FAIL', detail: 'settings-toggle not reached by Tab within 40 presses from load' });
    } else {
      await page.keyboard.press('Enter');
      await page.waitForTimeout(120);
      const openState = await page.evaluate(() => document.querySelector('.settings-sidebar')?.getAttribute('aria-hidden'));
      const focusOnOpen = await describeActive(page);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(80);
      const afterEscape = await page.evaluate(() => document.querySelector('.settings-sidebar')?.getAttribute('aria-hidden'));
      let closedViaButton = null, focusAfterClose = null, rClose = { found: false, steps: 0 };
      if (afterEscape !== 'true') {
        rClose = await tabTo(page, i => cls(i).includes('settings-close'), { max: 25 });
        if (rClose.found) {
          await page.keyboard.press('Enter');
          await page.waitForTimeout(120);
          closedViaButton = await page.evaluate(() => document.querySelector('.settings-sidebar')?.getAttribute('aria-hidden'));
          focusAfterClose = await describeActive(page);
        }
      } else { closedViaButton = 'true'; focusAfterClose = await describeActive(page); }
      log('a', 'open/close settings sidebar', {
        result: (openState === 'false' && closedViaButton === 'true') ? 'PASS' : 'PARTIAL',
        stepsToToggle: rToggle.steps,
        openedOk: openState === 'false',
        focusMovedIntoSidebarOnOpen: focusOnOpen && focusOnOpen.tag !== 'body',
        escapeClosedIt: afterEscape === 'true',
        closedViaCloseButton: rClose.found,
        closedOk: closedViaButton === 'true',
        focusReturnedToToggle: !!(focusAfterClose && cls(focusAfterClose).includes('settings-toggle')),
        detail: afterEscape === 'true' ? 'Escape closed it (a page-level keydown handler in ReaderShell.astro dispatches a close-settings event).' : 'Escape did NOT close it; closed via Tab to the × close button + Enter instead.',
      });
    }
    await context.close();
  }

  // (b) change the view and turn compare mode on
  {
    const { context, page } = await freshPage(browser, origin);
    // Pick "English" specifically, not just any unpressed view button: picking
    // "Greek" (Greek-only) is a legitimate dead end for THIS compound step --
    // .settings-trans (the translation picker AND the compare radios) is
    // display:none whenever view==='greek', since compare mode is about
    // showing two English translations side by side, which has nothing to
    // show in Greek-only view. That is correct, intentional behavior, not a
    // bug, but it does mean "change the view and turn compare mode on" isn't
    // completable in that order if English/Both isn't kept. Noted below.
    const rView = await tabTo(page, i => i.tag === 'button' && i.inViewToggle && i.ariaPressed === 'false' && i.text === 'English', { max: 25 });
    let viewChanged = false;
    if (rView.found) {
      await page.keyboard.press('Enter');
      await page.waitForTimeout(120);
      const after = await describeActive(page);
      viewChanged = after.ariaPressed === 'true';
    }
    const rReopen = await tabTo(page, i => cls(i).includes('settings-toggle'), { max: 15, shift: true });
    let compareOn = false, rCompareRadio = { found: false, steps: 0 };
    if (rReopen.found) {
      await page.keyboard.press('Enter');
      await page.waitForTimeout(250);
      rCompareRadio = await tabTo(page, i => i.tag === 'input' && i.name === 'trans-mode' && /compare/i.test(i.labelText), { max: 15 });
      if (rCompareRadio.found) {
        await page.keyboard.press('Space');
        await page.waitForTimeout(200);
        compareOn = await page.evaluate(() => !!document.querySelector('.overlay-col'));
      }
      const rClose2 = await tabTo(page, i => cls(i).includes('settings-close'), { max: 25 });
      if (rClose2.found) { await page.keyboard.press('Enter'); await page.waitForTimeout(120); }
    }
    log('b', 'change view and turn compare mode on', {
      result: (viewChanged && compareOn) ? 'PASS' : viewChanged ? 'PARTIAL' : 'FAIL',
      viewButtonReached: rView.found, stepsToViewButton: rView.steps, viewChanged,
      settingsReopened: rReopen.found,
      compareRadioReached: rCompareRadio.found, stepsToCompareRadio: rCompareRadio.steps, compareOn,
      detail: 'Changing the view (Greek/Both/English) works fine by Tab -- those are independent buttons. Turning ON compare mode does not: "Single translation" and "Compare two translations" are a native radio-button group (both exist in the DOM, both visible/display:block), and "Single translation" starts checked. Per standard browser radio-group behavior, Tab only ever lands on the CHECKED radio in a group; reaching the other one needs ArrowUp/ArrowDown/Left/Right, none of which is in the permitted key set. So with only Tab/Shift+Tab/Enter/Space/Escape, compare mode cannot be turned on from the settings sidebar at all -- confirmed empirically (Tab search for the "Compare two translations" radio exhausted its budget every run).',
    });
    await context.close();
  }

  // (c) choose a different translation
  {
    const { context, page } = await freshPage(browser, origin);
    const rSel = await tabTo(page, i => cls(i).includes('rc-trans-select'), { max: 25 });
    let valueChanged = false;
    if (rSel.found) {
      const before = await page.evaluate(() => document.querySelector('.rc-trans-select')?.value);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(150);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(80);
      const after = await page.evaluate(() => document.querySelector('.rc-trans-select')?.value);
      valueChanged = before !== after;
    }
    log('c', 'choose a different translation', {
      result: rSel.found && !valueChanged ? 'IMPOSSIBLE' : rSel.found ? 'PASS' : 'FAIL',
      controlFound: rSel.found, stepsToControl: rSel.steps, controlTag: 'select.rc-trans-select (native <select>, aria-label "English translation")',
      valueChangedWithPermittedKeysOnly: valueChanged,
      detail: 'The desktop translation picker is a native <select>. Enter/Space opens its native list, but MOVING the highlighted option needs ArrowUp/ArrowDown (or typing), neither in the permitted key set (Tab/Shift+Tab/Enter/Space/Escape). Confirmed empirically: pressing Enter then Escape left the value unchanged. So the control is reachable, but a different translation cannot actually be CHOSEN with only the permitted keys.',
    });
    await context.close();
  }

  // (d) open a word's analysis card and close it
  {
    const { context, page } = await freshPage(browser, origin);
    const rTok = await tabTo(page, i => cls(i).includes('tok'), { max: 30 });
    let opened = false, closedOk = false, focusRestored = false, focusMovedIntoDialog = false;
    if (rTok.found) {
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);
      opened = await page.evaluate(() => !!document.querySelector('.word-sidebar'));
      const focusInPopup = await describeActive(page);
      focusMovedIntoDialog = !!(focusInPopup && (focusInPopup.role === 'dialog' || cls(focusInPopup).includes('word-sidebar')));
      await page.keyboard.press('Escape');
      await page.waitForTimeout(400); // outro fly transition (~220-260ms) must finish before Svelte unmounts it
      closedOk = await page.evaluate(() => !document.querySelector('.word-sidebar'));
      const focusAfter = await describeActive(page);
      focusRestored = cls(focusAfter).includes('tok');
    }
    log('d', "open a word's analysis card and close it", {
      result: (opened && closedOk && focusRestored) ? 'PASS' : (opened || closedOk) ? 'PARTIAL' : 'FAIL',
      tokenReached: rTok.found, stepsToToken: rTok.steps, opened, focusMovedIntoDialog, closedViaEscape: closedOk, focusRestoredToToken: focusRestored,
    });
    await context.close();
  }

  // (e) "Copy with citation"
  {
    const { context, page } = await freshPage(browser, origin);
    const rCopyBtn = await tabTo(page, i => cls(i).includes('copy-cite-btn'), { max: 60 });
    log('e', 'use "Copy with citation"', {
      result: rCopyBtn.found ? 'PASS' : 'IMPOSSIBLE',
      footnotePopupDiversions: rCopyBtn.trapEscapes,
      detail: rCopyBtn.found
        ? `Reached after ${rCopyBtn.steps} tabs.`
        : 'The button only renders once copyBtnPos is set, and that only happens from a mouseup/selectionchange handler on a real text selection (Reader.svelte ~3228). None of Tab/Shift+Tab/Enter/Space/Escape creates or extends a text selection (that needs Shift+Arrow, not in the permitted key set), and there is no keyboard shortcut that triggers it directly. So with only the permitted keys, this control cannot be reached or used at all.',
    });
    await context.close();
  }

  // (f) reach the running-head links (Breadcrumb.svelte: a.bc-crumb, first
  // two focusables on the page — RunningHead.svelte's .rhp links exist in the
  // codebase but are not what this route renders).
  {
    const { context, page } = await freshPage(browser, origin);
    const rLink = await tabTo(page, i => i.tag === 'a' && cls(i).includes('bc-crumb'), { max: 10 });
    let navigated = false;
    if (rLink.found) {
      const hrefBefore = rLink.info.href;
      await page.keyboard.press('Enter');
      await page.waitForTimeout(400);
      navigated = page.url().includes((hrefBefore.split('/').filter(Boolean).pop()) || '\u0000');
    }
    log('f', 'reach the running-head links', {
      result: rLink.found ? (navigated ? 'PASS' : 'PARTIAL') : 'FAIL',
      linkReached: rLink.found, stepsToLink: rLink.steps,
      focusVisible: rLink.info?.focusVisible ?? null,
      href: rLink.info?.href ?? null,
      activatedAndNavigated: navigated,
    });
    await context.close();
  }
}

// ---------- S13.3 lang attributes ----------
async function runLangCheck(browser, origin) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', serviceWorkers: 'block' });
  await context.addInitScript(t => { try { localStorage.setItem('ne-theme', t); } catch {} }, 'light');
  const plays = [
    { id: 'agamemnon', path: '/aeschylus/agamemnon/' },
    { id: 'medea', path: '/euripides/medea/' },
    { id: 'birds', path: '/aristophanes/birds/' },
  ];
  for (const play of plays) {
    const page = await context.newPage();
    try {
      await page.goto(origin + play.path, { waitUntil: 'load', timeout: 30000 });
      try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
      const data = await page.evaluate(() => {
        const isGreek = s => /[Ͱ-Ͽἀ-῿]/.test(s);
        let total = 0, covered = 0;
        const missing = new Map();
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const txt = node.nodeValue;
          if (!txt || !isGreek(txt)) continue;
          total++;
          const el = node.parentElement;
          const withLang = el ? el.closest('[lang]') : null;
          const lang = withLang ? withLang.getAttribute('lang') : null;
          if (lang && (lang === 'grc' || lang.toLowerCase().startsWith('el'))) { covered++; continue; }
          const container = el ? `${el.tagName.toLowerCase()}${el.className ? '.' + String(el.className).trim().split(/\s+/).slice(0, 2).join('.') : ''}` : 'unknown';
          missing.set(container, (missing.get(container) || 0) + 1);
        }
        return { total, covered, htmlLang: document.documentElement.getAttribute('lang'), missing: [...missing.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15) };
      });
      report.lang.push({ play: play.id, htmlLang: data.htmlLang, greekTextNodes: data.total, coveredByLang: data.covered, coveragePct: data.total ? +((data.covered / data.total) * 100).toFixed(1) : null, missingContainers: data.missing });
      console.log(`S13 lang: ${play.id} -> ${data.covered}/${data.total} (${data.total ? ((data.covered / data.total) * 100).toFixed(1) : 'n/a'}%)`);
    } catch (e) {
      report.lang.push({ play: play.id, error: e.message });
    } finally { await page.close().catch(() => {}); }
  }
  await context.close();
}

// ---------- S13.4 speaker colour contrast ----------
function toRgbArr(rgbStr) { const m = (rgbStr || '').match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : [0, 0, 0]; }
function relLum([r, g, b]) { const f = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }; const [R, G, B] = [f(r), f(g), f(b)]; return 0.2126 * R + 0.7152 * G + 0.0722 * B; }
function contrastRatio(rgb1, rgb2) { const L1 = relLum(rgb1), L2 = relLum(rgb2); const [hi, lo] = L1 > L2 ? [L1, L2] : [L2, L1]; return (hi + 0.05) / (lo + 0.05); }

async function runSpeakerContrast(browser, origin) {
  for (const theme of ['light', 'dark']) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: theme, serviceWorkers: 'block' });
    await context.addInitScript(t => { try { localStorage.setItem('ne-theme', t); } catch {} }, theme);
    const page = await context.newPage();
    try {
      await page.goto(origin + '/aeschylus/agamemnon/', { waitUntil: 'load', timeout: 30000 });
      try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
      const data = await page.evaluate(() => {
        function parseColor(str) {
          const d = document.createElement('div');
          d.style.color = str; d.style.display = 'none';
          document.body.appendChild(d);
          const rgb = getComputedStyle(d).color;
          document.body.removeChild(d);
          return rgb;
        }
        const toRgb = s => (s.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);
        const speakerEl = document.querySelector('.speaker[data-spk]');
        let bgEl = speakerEl, bg = null;
        while (bgEl) {
          const c = getComputedStyle(bgEl).backgroundColor;
          if (c && !/rgba?\(0,\s*0,\s*0,\s*0\)/.test(c) && c !== 'transparent') { bg = c; break; }
          bgEl = bgEl.parentElement;
        }
        if (!bg) bg = getComputedStyle(document.body).backgroundColor;
        const root = getComputedStyle(document.documentElement);
        const slots = [];
        for (let i = 0; i < 12; i++) {
          const raw = root.getPropertyValue(`--spk-${i}`).trim();
          slots.push({ slot: i, hex: raw, fgRgb: toRgb(parseColor(raw)) });
        }
        return { theme: document.documentElement.dataset.theme || document.documentElement.getAttribute('data-theme') || 'unknown', background: bg, bgRgb: toRgb(bg), foundSpeakerEl: !!speakerEl, slots };
      });
      const results = data.slots.map(s => ({ ...s, background: data.background, ratio: +contrastRatio(s.fgRgb, data.bgRgb).toFixed(2) }));
      report.speakerContrast[theme] = { background: data.background, foundSpeakerElOnPage: data.foundSpeakerEl, slots: results };
      for (const r of results) {
        if (r.ratio < 4.5) report.speakerContrast.flagged.push({ slot: r.slot, theme, ratio: r.ratio, below3: r.ratio < 3 });
      }
      console.log(`S13 speaker contrast (${theme}): background ${data.background}, ${results.filter(r => r.ratio < 4.5).length}/12 below 4.5:1`);
    } catch (e) {
      report.speakerContrast[theme] = { error: e.message };
    } finally { await page.close().catch(() => {}); await context.close(); }
  }
}

// ---------- S13.5 weight ----------
async function seedCompareLocalStorage(browser, origin, playPath) {
  // Pass 1: use the real UI (mouse is fine here, only S13.2 is keyboard-only)
  // to switch a fresh session into compare mode, then read back whatever
  // localStorage keys it wrote so pass 2 can seed them before first paint.
  const context = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, colorScheme: 'light', serviceWorkers: 'block' });
  const page = await context.newPage();
  let seed = {};
  try {
    await page.goto(origin + playPath, { waitUntil: 'load', timeout: 30000 });
    try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
    await setupCompare(page);
    await page.waitForTimeout(200);
    seed = await page.evaluate(() => {
      const out = {};
      for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); out[k] = localStorage.getItem(k); }
      return out;
    });
  } catch (e) {
    console.log(`S13 weight: could not seed compare mode for ${playPath}: ${e.message}`);
  } finally { await page.close().catch(() => {}); await context.close(); }
  return seed;
}

async function runWeight(browser, origin) {
  const pages = [
    { id: 'orestes', path: '/euripides/orestes/' },
    { id: 'phoenician-women', path: '/euripides/phoenician-women/' },
  ];
  for (const p of pages) {
    const seed = await seedCompareLocalStorage(browser, origin, p.path);
    const context = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, colorScheme: 'light', serviceWorkers: 'block' });
    await context.addInitScript(seedObj => {
      try { for (const [k, v] of Object.entries(seedObj)) localStorage.setItem(k, v); } catch {}
      window.__greekTiming = null;
      const isGreek = s => /[Ͱ-Ͽἀ-῿]/.test(s);
      const check = () => {
        if (window.__greekTiming) return true;
        const el = document.querySelector('.tok, .greek-line, [lang="grc"]');
        if (el && isGreek(el.textContent || '')) { window.__greekTiming = performance.now(); return true; }
        return false;
      };
      document.addEventListener('DOMContentLoaded', () => {
        if (check()) return;
        const obs = new MutationObserver(() => { if (check()) obs.disconnect(); });
        obs.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
      });
    }, seed);
    const page = await context.newPage();
    let transferBytes = 0;
    page.on('requestfinished', async req => {
      try { const sizes = await req.sizes(); transferBytes += (sizes.responseBodySize || 0) + (sizes.responseHeadersSize || 0) + (sizes.requestHeadersSize || 0); } catch {}
    });
    try {
      const client = await context.newCDPSession(page);
      await client.send('Performance.enable');
      await page.goto(origin + p.path, { waitUntil: 'load', timeout: 30000 });
      try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
      await page.waitForTimeout(500);
      const greekTiming = await page.evaluate(() => window.__greekTiming);
      const domNodes = await page.evaluate(() => document.getElementsByTagName('*').length);
      const isCompare = await page.evaluate(() => !!document.querySelector('.overlay-col, .rc-col-name + .rc-col-name'));
      const metrics = await client.send('Performance.getMetrics');
      const heap = metrics.metrics.find(m => m.name === 'JSHeapUsedSize')?.value ?? null;
      report.weight.push({
        page: p.id, compareModeSeeded: Object.keys(seed).length > 0, compareConfirmedOnPage: isCompare,
        jsHeapUsedBytes: heap, domNodeCount: domNodes, totalTransferBytes: transferBytes,
        timeToFirstGreekLineMs: greekTiming != null ? +greekTiming.toFixed(1) : null,
      });
      console.log(`S13 weight: ${p.id} -> heap=${heap} dom=${domNodes} transfer=${transferBytes} firstGreekMs=${greekTiming}`);
    } catch (e) {
      report.weight.push({ page: p.id, error: e.message });
    } finally { await page.close().catch(() => {}); await context.close(); }
  }
}

async function runLighthouse(origin) {
  const url = origin + '/euripides/orestes/';
  // Scratch only -- the brief's output list for S13 is s13-access.tsv/.json;
  // Lighthouse's own raw JSON is parsed for a few fields into report.lighthouse
  // below and then deleted, not left behind as a third file in build/sweeps.
  const outPath = path.join(os.tmpdir(), `s13-lighthouse-${Date.now()}.json`);
  const args = [LIGHTHOUSE_CLI, url, '--output=json', `--output-path=${outPath}`, '--only-categories=performance,accessibility', '--form-factor=mobile', '--screenEmulation.mobile', '--chrome-flags=--headless=new --no-sandbox', `--chrome-path=${CHROMIUM_PATH}`, '--max-wait-for-load=45000'];
  try {
    const { stdout, stderr } = await execFileP('node', args, { cwd: repo, timeout: 90000, maxBuffer: 1024 * 1024 * 20 });
    const json = JSON.parse(await readFile(outPath, 'utf8'));
    report.lighthouse = {
      ran: true,
      performanceScore: json.categories?.performance?.score ?? null,
      accessibilityScore: json.categories?.accessibility?.score ?? null,
      lcpMs: json.audits?.['largest-contentful-paint']?.numericValue ?? null,
      tbtMs: json.audits?.['total-blocking-time']?.numericValue ?? null,
      cls: json.audits?.['cumulative-layout-shift']?.numericValue ?? null,
    };
    console.log('S13 lighthouse: ran OK', report.lighthouse);
    await unlink(outPath).catch(() => {});
  } catch (e) {
    report.lighthouse = { ran: false, reason: (e.stderr || e.message || String(e)).toString().slice(0, 500) };
    console.log('S13 lighthouse: FAILED -', report.lighthouse.reason);
  }
}

function buildManualChecks() {
  report.manualChecks = [
    { device: 'iPhone Safari', check: 'VoiceOver rotor over the reader', steps: 'Settings > Accessibility > VoiceOver on. Open /aeschylus/agamemnon/. Swipe right through the header, settings sidebar, a Greek token, and the word-analysis card; confirm each is announced with a sensible label and Greek text is read in a Greek voice/pronunciation.' },
    { device: 'iPhone Safari', check: 'Dynamic Type at largest accessibility size', steps: 'Settings > Accessibility > Display & Text Size > Larger Text, drag to max. Reload the reader; check no text is clipped or overlapping, and the settings sidebar sliders/selects stay usable.' },
    { device: 'iPhone Safari', check: 'Text-selection "Copy with citation" via native selection', steps: 'Long-press a line of English text to trigger the native iOS selection handles, extend the selection, and check whether the custom copy-with-citation button appears/works over a touch selection (S13.2 found no keyboard path; touch may differ).' },
    { device: 'Android Chrome/TalkBack', check: 'TalkBack over the settings sidebar and word popup', steps: 'Settings > Accessibility > TalkBack on. Open the reader, open Settings via the gear icon, swipe through sliders and the compare radios; confirm TalkBack announces slider values changing and radio state.' },
    { device: 'Android Chrome', check: 'Compare mode on a small/low-RAM device', steps: 'Open /euripides/orestes/ in compare mode on a mid-range Android phone; scroll through a full ode and check for jank or a tab crash (S13.5 measured only desktop-Chromium headless memory/CPU, not a real low-end device).' },
    { device: 'Firefox desktop', check: 'Visible focus ring through the same keyboard walk as S13.2', steps: 'Open /aeschylus/agamemnon/ in Firefox, repeat steps a-f from S13.2 (Tab/Shift+Tab/Enter/Space/Escape only); Firefox’s default focus ring differs from Chromium’s and its Tab order for custom listboxes/radios can differ too.' },
    { device: 'Firefox desktop', check: 'Print stylesheet', steps: 'Open the print control (Settings > Print, or Ctrl+P) on a play page and check the print preview: Firefox’s print engine renders @page/column CSS differently from Chromium’s, which is what axe/Lighthouse here actually exercised.' },
  ];
}

async function writeReports() {
  await mkdir(OUT, { recursive: true });
  await writeFile(path.join(OUT, 's13-access.json'), JSON.stringify(report, null, 2) + '\n');
  const rows = [['section', 'key', 'a', 'b', 'c', 'd', 'e']];
  for (const s of report.axeSummary) rows.push(['axe', s.rule, s.impact, s.nodeCount, s.pagesAffected, s.example, s.examplePage]);
  for (const k of report.keyboard) rows.push(['keyboard', k.step, k.label ?? '', k.result ?? '', JSON.stringify(k).slice(0, 300), '', '']);
  for (const l of report.lang) rows.push(['lang', l.play, l.htmlLang ?? '', l.coveragePct ?? '', `${l.covered ?? ''}/${l.greekTextNodes ?? ''}`, '', '']);
  for (const f of report.speakerContrast.flagged) rows.push(['speaker-contrast-flagged', `slot-${f.slot}`, f.theme, f.ratio, f.below3 ? 'below-3:1' : 'below-4.5:1', '', '']);
  for (const w of report.weight) rows.push(['weight', w.page, w.jsHeapUsedBytes ?? w.error ?? '', w.domNodeCount ?? '', w.totalTransferBytes ?? '', w.timeToFirstGreekLineMs ?? '', '']);
  if (report.lighthouse) rows.push(['lighthouse', 'orestes', report.lighthouse.ran, report.lighthouse.performanceScore ?? report.lighthouse.reason ?? '', report.lighthouse.accessibilityScore ?? '', report.lighthouse.lcpMs ?? '', '']);
  for (const m of report.manualChecks) rows.push(['manual', m.device, m.check, m.steps, '', '', '']);
  await writeFile(path.join(OUT, 's13-access.tsv'), tsv(rows));
  console.log(`S13: wrote ${path.join(OUT, 's13-access.json')} and .tsv`);
}

async function main() {
  const { chromium } = await import(pathToFileURL(PLAYWRIGHT_MODULE).href);
  const server = createStaticServer(DIST);
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ executablePath: CHROMIUM_PATH });
  try {
    const lemmaPath = await findLemmaPath();
    const pageTypes = buildPageTypes(lemmaPath);
    await runAxe(browser, origin, pageTypes);
    await runKeyboard(browser, origin);
    await runLangCheck(browser, origin);
    await runSpeakerContrast(browser, origin);
    await runWeight(browser, origin);
    await runLighthouse(origin);
    buildManualChecks();
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  await writeReports();
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then(() => { process.exitCode = 0; }).catch(e => { console.error(e); process.exitCode = 1; });
}
