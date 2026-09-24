import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { parseArgs, plays, playOdeIds, sampleStrata, browserServer, report, main } from './tier2-lib.mjs';

export async function run(options = parseArgs(process.argv.slice(2), { seed: true })) {
  const works = await plays(options), tokens = [];
  for (const play of works) {
    const analyses = JSON.parse(await readFile(path.join(options.dist, 'data', play.id, 'analyses.json'), 'utf8'));
    const odes = playOdeIds(play.book.segments);
    for (const seg of play.book.segments) for (const line of seg.greek) for (const token of line.tokens ?? [])
      for (const parse of analyses[token.k] ?? []) for (const key of parse.lsj ?? []) if (key)
        tokens.push({ author: play.author, kind: odes.has(seg.id) ? 'ode' : 'dialogue', key, surface: token.t, play: play.id, line: line.ref, lemma: parse.lemma });
  }
  const sample = sampleStrata(tokens, 60, options.seed);
  const h = await browserServer(options.dist), results = [];
  let signature = '';
  try {
    const context = await h.browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light', serviceWorkers: 'block' });
    const page = await context.newPage(); await page.goto(h.origin + '/', { waitUntil: 'load' });
    await page.evaluate(async () => { window.__lookup = (await import('https://grammata.pages.dev/t8/lookup.js')).lookup; });
    const lookup = async key => page.evaluate(async key => {
      const el = document.createElement('div'); document.body.append(el);
      try {
        await Promise.race([window.__lookup('', el, { lang: 'grc', key }), new Promise((_, reject) => setTimeout(() => reject(Error('10s timeout')), 10000))]);
        return { text: el.innerText.trim(), html: el.innerHTML };
      } catch (e) { return { text: el.innerText.trim(), html: el.innerHTML, error: e.message }; } finally { el.remove(); }
    }, key);
    signature = (await lookup('__codex_no_such_lsj_key_982734__')).text;
    let next = 0;
    await Promise.all(Array.from({ length: Math.min(4, sample.length) }, async () => {
      while (next < sample.length) {
        const item = sample[next++];
        try {
          const got = await lookup(item.key);
          const state = got.error ? 'error' : got.text && got.text !== signature && !/^(not found|no entry|no results|word data is not available here\.?)/i.test(got.text) ? 'entry' : 'empty';
          results.push({ ...item, state, detail: (got.error ?? got.text).slice(0, 160) });
        } catch (e) { results.push({ ...item, state: 'error', detail: e.message }); }
      }
    }));
    await context.close();
  } finally { await h.close(); }
  const counts = [];
  for (const author of [...new Set(works.map(w => w.author))].sort()) for (const kind of ['ode','dialogue']) {
    const cell = results.filter(r => r.author === author && r.kind === kind), miss = cell.filter(r => r.state !== 'entry').length;
    counts.push({ author, kind, count: cell.length, entry: cell.length-miss, miss, missRate: cell.length ? miss/cell.length : 0, status: cell.length && miss/cell.length <= .1 ? 'pass' : 'fail' });
  }
  const misses = results.filter(r => r.state !== 'entry');
  await report('s7b-lsj-lookup', { seed: options.seed, notFoundSignature: signature, counts, misses, results }, counts, options.out, ['author','kind','count','entry','miss','missRate','status']);
  await report('s7b-lsj-misses', misses, misses, options.out, ['author','kind','key','surface','play','line','state','detail']);
  console.log(`S7b: ${results.length} keys; ${misses.length} misses; ${counts.filter(c => c.status === 'fail').length} failing cells`);
  return counts.some(c => c.status === 'fail') ? 1 : 0;
}
main(import.meta.url, run);
