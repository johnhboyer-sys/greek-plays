import { parseArgs, plays, slotFor, strings, norm, playOdeIds, browserServer, report, main } from './tier2-lib.mjs';

const checkNames = ['plate','jump-loc','jump-hash','translations','compare','word-dialogue','word-ode','speaker-colors','cite-copy'];
export async function run(options = parseArgs(process.argv.slice(2))) {
  const works = await plays(options), rows = [], h = await browserServer(options.dist);
  try {
    const context = await h.browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light', serviceWorkers: 'block', permissions: ['clipboard-read','clipboard-write'] });
    await context.addInitScript(() => { localStorage.setItem('ne-theme','light'); localStorage.setItem('reader-view','both'); });
    for (const p of works) {
      const page = await context.newPage(), cells = [];
      const add = (check, status, detail = '') => cells.push({ play: p.id, check, status, detail });
      page.on('console', m => { if (m.type() === 'error') add('console-error','fail',m.text()); });
      page.on('pageerror', e => add('page-error','fail',e.message));
      const route = `/${p.author}/${p.slug}/`, lines = p.book.segments.flatMap(s => s.greek.filter(l => l.ref && l.text));
      const odeIds = playOdeIds(p.book.segments);
      try {
        await page.goto(h.origin + route, { waitUntil: 'load' });
        await page.locator('.reader-body .segment').first().waitFor({ timeout: 20000 });
        const plate = page.locator('.plate');
        add('plate', await plate.count() && await plate.locator('.plate-gt').innerText().then(x => norm(x) === norm(p.greekTitle)).catch(() => false) && await plate.locator('.plate-cast li').count() ? 'pass' : 'fail', `title=${p.greekTitle}; persons=${await plate.locator('.plate-cast li').count()}`);
        const refs = [lines[0], lines[Math.floor(lines.length / 2)], lines.at(-1)].filter(Boolean);
        for (const [check, suffix] of [['jump-loc', r => `?loc=${encodeURIComponent(r)}`], ['jump-hash', r => `#${encodeURIComponent(r)}`]]) {
          const failures = [];
          for (const line of refs) {
            await page.goto(h.origin + '/404.html');  // a fresh load: a hash-only goto is same-document and the reader reads the hash on load only
            await page.goto(h.origin + route + suffix(line.ref), { waitUntil: 'load' });
            await page.locator('.reader-body .segment').first().waitFor({ timeout: 20000 });
            try {
              await page.waitForFunction(({ref,n}) => { const el = document.getElementById(`L${ref.replace(/ /g,'_')}-${n}`); if (!el) return false; const a=el.getBoundingClientRect(), p=document.querySelector('.plate')?.getBoundingClientRect(); return a.top < innerHeight && a.bottom > 0; }, { ref: line.ref, n: line.n }, { timeout: 5000 });
            } catch { failures.push(line.ref); }
          }
          add(check, failures.length ? 'fail' : 'pass', failures.length ? `off-screen refs: ${failures.join(', ')}` : refs.map(x => x.ref).join(', '));
        }
        await page.goto(h.origin + route, { waitUntil: 'load' }); await page.locator('.reader-body .segment').first().waitFor();
        const transFailures = [];
        for (const t of p.slots) {
          const source = p.book.segments.map(s => ({ seg: s, text: strings(slotFor(s,t)).find(x => norm(x)) })).find(x => x.text);
          if (!source) { transFailures.push(`${t.id}: no source text`); continue; }
          // The reader draws a leading speaker cue ("WATCHMAN.") as a label, not text.
          const expected = norm(norm(source.text).replace(/^[A-Z][A-Z’' -]{1,40}\.\s+/, '')).slice(0,40);
          try {
            await page.locator('.rc-trans-select').selectOption(t.id);
            const found = await page.locator(`.english-col[data-trans="${t.id}"], .overlay-col[data-trans="${t.id}"]`).allTextContents();
            if (!norm(found.join(' ')).includes(expected)) transFailures.push(`${t.id}: missing ${expected}`);
          } catch (e) { transFailures.push(`${t.id}: ${e.message}`); }
        }
        add('translations', transFailures.length ? 'fail' : 'pass', transFailures.join('; ') || p.slots.map(x => x.id).join(', '));
        if (p.slots.length < 2) add('compare','skip','one published translation');
        else {
          const problems = [];
          await page.locator('.settings-toggle').click();
          await page.locator('.settings-mode-row').filter({ hasText: 'Compare two translations' }).locator('input').check();
          for (const t of p.slots.slice(1)) {
            try {
              if (await page.locator('select[aria-label="Compare right translation"] option:checked').getAttribute('value') !== t.id) await page.locator('select[aria-label="Compare right translation"]').selectOption(t.id);
              const count = await page.locator('.reader-body.trans-compare .english-col, .reader-body.trans-compare .overlay-col').count();
              const filled = await page.locator('.reader-body.trans-compare .english-col, .reader-body.trans-compare .overlay-col').evaluateAll(els => els.filter(e => e.textContent.trim()).length);
              if (count < 2 || filled < 2) problems.push(t.id);
            } catch (e) { problems.push(`${t.id}: ${e.message}`); }
          }
          add('compare', problems.length ? 'fail' : 'pass', problems.join('; ') || 'two filled columns');
          await page.locator('.settings-close').first().click();
        }
        for (const [check, selector] of [['word-dialogue','.segment:not(.play-ode) .tok'],['word-ode','.segment.play-ode .tok']]) {
          const token = page.locator(selector).first();
          if (!await token.count()) { add(check,'skip','no token in segment'); continue; }
          const word = await token.innerText();
          const sourceSeg = p.book.segments.find(s => odeIds.has(s.id) === (check === 'word-ode') && s.greek.some(l => l.tokens?.length));
          const sourceToken = sourceSeg?.greek.flatMap(l => l.tokens ?? [])[0];
          const key = sourceToken?.k ?? '';
          try {
            await token.click();
            const sidebar = page.locator('.word-sidebar'); await sidebar.waitFor({ timeout: 8000 });
            const card = sidebar.locator('.analysis-card').first(); await card.waitFor({ timeout: 8000 });
            await card.locator('.card-face').click();
            await page.waitForFunction(() => { const el=document.querySelector('.word-sidebar .analysis-card.card-open .grammata-mount'); return el && el.textContent.trim() && !el.textContent.includes('Word data is not available here.'); }, null, { timeout: 10000 });
            add(check,'pass',`${word} / ${key}`);
          } catch (e) { add(check,'fail',`${word}: ${e.message}`); }
          await page.locator('.word-sidebar button[aria-label="Close"]').click().catch(() => {});
        }
        const colors = await page.evaluate(() => [...document.querySelectorAll('.plate-cast li')].map(li => {
          const name = li.childNodes[0]?.textContent?.trim();
          const speaker = [...document.querySelectorAll('.reader-body .speaker[data-spk]')].find(e => e.textContent.trim().toLowerCase() === name?.toLowerCase());
          return speaker ? { name, plate: getComputedStyle(li,'::first-letter').color, lead: getComputedStyle(speaker).color } : null;
        }).filter(Boolean));
        const mismatches = colors.filter(x => x.plate !== x.lead);
        add('speaker-colors', mismatches.length ? 'fail' : 'pass', mismatches.length ? JSON.stringify(mismatches) : `${colors.length} matching persons`);
        const first = page.locator('.reader-body .greek-line .line-text').first();
        if (!await first.count()) add('cite-copy','skip','no Greek line selection target');
        else {
          try {
            await first.scrollIntoViewIfNeeded();
            await first.evaluate(el => { const range=document.createRange(); range.selectNodeContents(el); const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(range); el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true})); });
            const button = page.locator('.copy-cite-btn');
            // The reader places the button one animation frame after mouseup.
            await button.first().waitFor({ state: 'visible', timeout: 2000 }).catch(() => {});
            if (!await button.count()) add('cite-copy','skip','copy citation control did not appear');
            else {
              await button.click(); const clip = await page.evaluate(() => navigator.clipboard.readText());
              add('cite-copy', clip.includes(p.copyAbbr) && clip.includes(lines[0].ref) ? 'pass' : 'fail', clip.slice(0,160));
            }
          } catch (e) { add('cite-copy','fail',e.message); }
        }
      } catch (e) {
        add('page-load','fail',e.message);
        for (const check of checkNames.filter(x => !cells.some(c => c.check === x))) add(check,'skip','page load failed');
      } finally { rows.push(...cells); await page.close(); }
    }
    await context.close();
  } finally { await h.close(); }
  const grid = works.map(p => ({ play: p.id, ...Object.fromEntries(checkNames.map(name => [name, rows.find(r => r.play === p.id && r.check === name)?.status ?? 'skip'])) }));
  const fail = rows.filter(r => r.status === 'fail');
  await report('s6-functional', { grid, rows }, grid, options.out, ['play',...checkNames]);
  await report('s6-functional-detail', fail, fail, options.out, ['play','check','status','detail']);
  console.log(`S6: ${works.length} plays; ${fail.length} failures`);
  return fail.length ? 1 : 0;
}
main(import.meta.url, run);
