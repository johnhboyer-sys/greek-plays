import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { search, invalidateSearchIndex, type AdvancedSearch } from '../../lib/legacy/search';
import { shardName, searchCombo } from '../../lib/legacy/search-advanced';
const meta = [
  { id: 'a', book: 1, column: '1', head: '', tokens: 'logos kalos', english_head: 'man loves child', english_slots: { other: 'men love children' } },
  { id: 'b', book: 1, column: '2', head: '', tokens: 'logos qea', english_head: 'child sees man' },
];
const indexes = {
  form: { logos: [[0, 0], [1, 0]], kalos: [[0, 1]], qea: [[1, 1]] },
  lemma: { logos: [[0, 0], [1, 0]], kalos: [[0, 1]], qeos: [[1, 1]] },
  english: { man: [[0, 'primary'], [1, 'primary']], child: [[0, 'primary'], [1, 'primary']], men: [[0, 'other']], children: [[0, 'other']] },
};
const shards: Record<string, Record<string, unknown>> = {};
const streams: Record<string, { shards: string[]; sources: Record<string, string> }> = {};
for (const [stream, idx] of Object.entries(indexes)) {
  streams[stream] = { shards: [], sources: { Shard: 'hash' } };
  for (const [word, posts] of Object.entries(idx)) {
    const name = shardName(word);
    if (!streams[stream].shards.includes(name)) streams[stream].shards.push(name);
    (shards[`${stream}/${name}.json`] ??= {})[word] = { Shard: posts };
  }
}
let listed = false;
let failShard = false;
let calls: string[];
const json = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response);
beforeEach(() => {
  listed = false; failShard = false; calls = [];
  invalidateSearchIndex('Shard'); invalidateSearchIndex('Unlisted');
  vi.spyOn(globalThis, 'fetch').mockImplementation(url => {
    const path = String(url); calls.push(path);
    if (path.endsWith('search-shards/index.json')) return listed ? json({ streams }) : Promise.resolve({ ok: false, status: 404 } as Response);
    const shard = path.split('search-shards/')[1];
    if (shard) return failShard ? Promise.reject(new Error('offline')) : json(shards[shard]);
    if (path.endsWith('meta.json')) return json(meta);
    if (path.endsWith('offsets.json')) return json({ token_count: 4, seg_base_offset: [0, 2], segments: meta.map(m => ({ book: 1, column: m.column, line_runs: [[1, 2]] })), book_bounds: [{ book: 1, start: 0 }] });
    const name = path.split('/').pop()!.replace('.json', '') as keyof typeof indexes;
    return json(indexes[name] ?? {});
  });
});
afterEach(() => vi.restoreAllMocks());
it('pins shardName to the stage-9 fixture', () => {
  const fixture = JSON.parse(readFileSync(resolve(__dirname, '../../../pipeline/tests/fixtures/search_shards.json'), 'utf8'));
  for (const { word, shard } of fixture.cases) expect(shardName(word)).toBe(shard);
});
it.each([
  ['logos', '', 'all', undefined],
  ['lo*', '', 'all', undefined],
  ['logos kalos', '', 'phrase', undefined],
  ['', 'man', 'all', undefined],
  ['', 'm*', 'all', undefined],
  ['', '*', 'all', undefined],
  ['', 'man child', 'phrase', undefined],
  ['logos', 'child', 'all', undefined],
  ['', 'man child', 'all', { engForms: true }],
  ['', 'man', 'all', { engForms: true, engNear: { term: 'child', relation: 'after', window: 2 } }],
] as const)('shards and per-play indexes agree for %s / %s / %s', async (g, e, mode, advanced) => {
  const run = () => search(g, e, mode, mode, 'or', ['Shard'], 'form', undefined, advanced as AdvancedSearch | undefined);
  const own = await run();
  invalidateSearchIndex('Shard'); calls = []; listed = true;
  expect(await run()).toEqual(own);
  expect(calls.filter(p => /\/search\/(form|english)\.json$/.test(p))).toEqual([]);
});
it('uses the per-play fallback for an unlisted source', async () => {
  listed = true;
  expect((await search('logos', '', 'all', 'all', 'and', ['Unlisted'])).results).toHaveLength(2);
  expect(calls.some(p => p.endsWith('Unlisted/search/form.json'))).toBe(true);
});
it('limits a prefix lookup to its listed shards', async () => {
  listed = true;
  await search('q*', '', 'all', 'all', 'and', ['Shard']);
  expect(calls.filter(p => p.includes('search-shards/form/')).every(p => p.endsWith('/qe.json'))).toBe(true);
});
it('retries a failed shard instead of caching failure', async () => {
  listed = true; failShard = true;
  // The lemma stream has not yet been read by these tests.
  await expect(search('qeos', '', 'all', 'all', 'and', ['Shard'], 'lemma')).rejects.toThrow(/search index/);
  failShard = false;
  expect((await search('qeos', '', 'all', 'all', 'and', ['Shard'], 'lemma')).results).toHaveLength(1);
});
it('uses the same shards for advanced wildcards and per-position lemma phrases', async () => {
  const run = () => searchCombo([{ kind: 'phrase' as const, options: [['logos'], ['qe?s']], match: 'lemma' as const }, { kind: 'form' as const, terms: ['logos'] }],
    { window: 2, unit: 'words' as const, ordered: false }, ['Shard']);
  const own = await run();
  expect(own.results).toHaveLength(2);
  listed = true; invalidateSearchIndex('Shard');
  expect(await run()).toEqual(own);
});

it('shares one lexical slice across plays in a combo query', async () => {
  listed = true;
  const chosen = { kind: 'form' as const, terms: ['logos'] };
  await searchCombo([chosen, { kind: 'form', terms: ['kalos'] }], { window: 2, unit: 'words', ordered: false }, ['Shard', 'Unlisted']);
  expect(calls.filter(p => p.endsWith('search-shards/index.json'))).toHaveLength(1);
});
