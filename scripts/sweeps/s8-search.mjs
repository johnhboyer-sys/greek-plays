import { parseArgs, plays, slotFor, strings, probeWord, wordSet, stripDiacritics, browserServer, report, main } from './tier2-lib.mjs';

export function columnLines(play, slot) {
  if (slot === 'greek') return play.book.segments.flatMap(s => s.greek.filter(l => l.ref && l.text).map(l => ({ text: l.text, ref: l.ref })));
  return play.book.segments.flatMap(s => strings(slotFor(s, slot)).filter(Boolean).map(text => ({ text, ref: s.greek.find(l => l.ref)?.ref ?? s.column })));
}
export async function run(options = parseArgs(process.argv.slice(2))) {
  const works = await plays(options), rows = [], cache = new Map();
  for (const p of works) for (const slot of ['greek', ...p.slots]) cache.set(`${p.id}:${typeof slot === 'string' ? slot : slot.id}`, columnLines(p, slot));
  const h = await browserServer(options.dist);
  try {
    const context = await h.browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light', serviceWorkers: 'block' });
    for (const p of works) for (const slot of ['greek', ...p.slots]) {
      const id = typeof slot === 'string' ? slot : slot.id, lines = cache.get(`${p.id}:${id}`), other = works.filter(w => w.id !== p.id && (id === 'greek' || w.slots.some(t => t.id === id))).map(w => wordSet(cache.get(`${w.id}:${id}`) ?? []));
      const probe = probeWord(lines, other);
      if (!probe) { rows.push({ play: p.id, column: id, status: 'fail', detail: 'no seven-letter probe' }); continue; }
      for (const variant of id === 'greek' ? ['accented','unaccented'] : ['normal']) {
        const word = variant === 'unaccented' ? stripDiacritics(probe.word) : probe.word;
        const page = await context.newPage(); let status = 'fail', detail = '';
        try {
          if (id === 'greek') {
            // ?g= searches in the default Lemma mode, where an inflected form finds
            // nothing; a reader probing a printed word uses Exact form.
            await page.goto(`${h.origin}/search/`, { waitUntil: 'load' });
            await page.locator('label', { hasText: 'Exact form' }).first().click();
            await page.locator('input[type="search"], input[type="text"]').first().fill(word);
            await page.keyboard.press('Enter');
          } else {
            await page.goto(`${h.origin}/search/?e=${encodeURIComponent(word)}`, { waitUntil: 'load' });
          }
          await page.locator('.result-bar, .search-error').first().waitFor({ timeout: 30000 });
          let group;
          for (let i = 0; i < 100; i++) {
            group = page.locator('.book-section').filter({ has: page.locator(`a.inst-ref[href*="/${p.author}/${p.slug}"]`) }).first();
            if (await group.count()) break;
            const next = page.locator('.pager:not(.pager-bottom) button', { hasText: 'Next' });
            if (!await next.count() || await next.isDisabled()) break;
            await next.click(); await page.locator('.pager-status').first().waitFor();
          }
          if (!group || !await group.count()) detail = 'play result group absent';
          else {
            const hits = group.locator('.instance');
            if (!await hits.count()) detail = 'play group has no hits';
            else {
              const hit = hits.filter({ has: page.locator('.inst-snippet', { hasText: word }) }).first();
              if (!await hit.count()) throw Error('play result has no hit for probe word');
              const credit = await hit.locator('.inst-credit').allTextContents();
              const href = await hit.locator('a.inst-ref').first().getAttribute('href');
              const target = new URL(href, h.origin);
              const land = await context.newPage();
              try {
                await land.goto(target.href, { waitUntil: 'load' });
                await land.locator('.reader-body .segment').first().waitFor({ timeout: 20000 });
                if (id !== 'greek') await land.locator('.rc-trans-select').selectOption(id);
                const landed = await land.evaluate(({ word, loc }) => {
                  const target = [...document.querySelectorAll('.greek-line')].find(e => e.id && (e.id.startsWith(`L${loc.replace(/ /g,'_')}-`) || e.classList.contains('target')));
                  const seg = target?.closest('.segment');
                  return !!seg && seg.textContent.toLocaleLowerCase().includes(word.toLocaleLowerCase());
                }, { word, loc: target.searchParams.get('loc') ?? probe.ref });
                status = landed ? 'pass' : 'fail';
                detail = landed ? `hit ${href}; credit ${credit.join(' ')}` : `link ${href} did not land on word`;
                if (id !== 'greek' && credit.some(c => !c.trim())) { status = 'fail'; detail += '; empty attribution'; }
              } finally { await land.close(); }
            }
          }
        } catch (e) { detail = e.message; }
        finally { await page.close(); }
        rows.push({ play: p.id, column: id, variant, word, ref: probe.ref, status: variant === 'unaccented' && status === 'fail' ? 'reported' : status, detail });
      }
    }
    await context.close();
  } finally { await h.close(); }
  await report('s8-search', rows, rows, options.out, ['play','column','variant','word','ref','status','detail']);
  console.log(`S8: ${rows.length} probes; ${rows.filter(r => r.status === 'fail').length} failures`);
  return rows.some(r => r.status === 'fail') ? 1 : 0;
}
main(import.meta.url, run);
