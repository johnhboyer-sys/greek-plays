import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { search, invalidateSearchIndex, loadIndex, englishNearOccurrences, type AdvancedSearch } from '../lib/search';
import { searchCombo, searchGrammar, loadOffsets, type GrammarDict } from '../lib/search-advanced';
vi.mock('../lib/works', async importOriginal => ({
  ...await importOriginal<typeof import('../lib/works')>(),
  getWork: () => ({ language: 'grc', greekEditions: [{ id: 'alt' }] }),
}));
const meta = [
  { id: 'a', book: 1, column: '1', head: '', tokens: 'logos kalos', english_head: 'men love children', english_slots: { other: 'man sees a child' } },
  { id: 'b', book: 1, column: '2', head: '', tokens: 'qea logos', english_head: 'man far far far child', english_slots: { other: 'child loves man' } },
  { id: 'c', book: 2, column: '3', head: '', tokens: 'qea', english_head: 'man', english_slots: { other: 'child' } },
];
const form = { logos: [[0, 0], [1, 1]], kalos: [[0, 1]], qea: [[1, 0], [2, 0]] };
const lemma = { logos: [[0, 0], [1, 1]], kalos: [[0, 1]], qeos: [[1, 0]], qea: [[2, 0]] };
const english = { men: [[0, 'primary']], love: [[0, 'primary']], children: [[0, 'primary']],
  man: [[0, 'other'], [1, 'primary'], [1, 'other'], [2, 'primary']],
  child: [[0, 'other'], [1, 'primary'], [1, 'other'], [2, 'other']] };
const offsets = { token_count: 5, seg_base_offset: [0, 2, 4], book_bounds: [{ book: 1, start: 0 }, { book: 2, start: 4 }],
  segments: meta.map(m => ({ book: m.book, column: m.column, line_runs: [[1, m.id === 'c' ? 1 : 2]] })) };
const dict: GrammarDict = { token_count: 5, width: 2, categories: ['case'], reserved: { unkeyed: 0, unanalysed: 1 },
  sigs: [[], [], [{ case: ['nom'] }], [{ case: ['nom', 'voc'] }]] };
let column: Uint16Array | Uint32Array;
let files: Record<string, unknown>;
const json = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response);
beforeEach(() => {
  invalidateSearchIndex('Advanced');
  files = { 'meta.json': meta, 'form.json': form, 'lemma.json': lemma, 'english.json': english, 'offsets.json': offsets, 'grammar-dict.json': dict };
  column = Uint16Array.from([2, 0, 3, 2, 0]);
  vi.spyOn(globalThis, 'fetch').mockImplementation(url => {
    const path = String(url);
    if (path.includes('/lemma-map/')) return json({ qeous: [['qeos', 'qeo/s'], ['qea', 'qea/']] });
    if (path.endsWith('grammar-col.bin')) return Promise.resolve({ ok: true, arrayBuffer: async () => column.buffer } as Response);
    const file = path.split('/').pop()!;
    return file in files ? json(files[file]) : Promise.resolve({ ok: false, status: 404 } as Response);
  });
});
afterEach(() => vi.restoreAllMocks());
const run = (g = '', e = '', a?: AdvancedSearch, op: 'and' | 'or' = 'and', mode: 'lemma' | 'form' = 'form', ed?: string) =>
  search(g, e, 'all', 'all', op, ['Advanced'], mode, ed, a);
const near = (terms = ['qea']) => ({ kind: 'form' as const, terms, relation: 'after' as const, window: 2, unit: 'words' as const, ordered: false });

it('keeps a plain search byte-for-byte equal with no advanced state', async () => {
  const old = await run('logos', 'child');
  expect(old).toEqual({ failed: [], results: [{ work: 'Advanced', meta: meta[0], grkMatch: true, engMatch: true, grkPositions: [0], engPositions: [11], slotId: 'other', englishText: meta[0].english_slots.other },
    { work: 'Advanced', meta: meta[1], grkMatch: true, engMatch: true, grkPositions: [1], engPositions: [16], slotId: 'primary', englishText: meta[1].english_head },
    { work: 'Advanced', meta: meta[1], grkMatch: false, engMatch: true, grkPositions: [1], engPositions: [0], slotId: 'other', englishText: meta[1].english_slots.other }] });
  expect(await run('logos', 'child', {})).toEqual(old);
});
it('uses picked lemma folds for just the selected typed term', async () => {
  expect((await run('qeous', '', undefined, 'and', 'lemma')).results.map(r => r.meta.id)).toEqual(['b', 'c']);
  expect((await run('qeous', '', { lemmaPick: [['qea']] }, 'and', 'lemma')).results.map(r => r.meta.id)).toEqual(['c']);
  expect((await run('qeous', '', { lemmaPick: [[]] }, 'and', 'lemma')).results.map(r => r.meta.id)).toEqual(['b', 'c']);
});
it('puts only the anchor in grkPositions across a segment edge', async () => {
  const out = await run('kalos', '', { near: near() });
  expect(out.results.map(r => [r.meta.id, r.grkPositions, r.nearPositions])).toEqual([['a', [1], []], ['b', [], [0]]]);
});
it('uses per-position lemma choices for a typed phrase', async () => {
  const out = await search('qeous logos', '', 'phrase', 'all', 'and', ['Advanced'], 'lemma', undefined,
    { lemmaPick: [['qeos'], ['logos']], near: { ...near(['kalos']), relation: 'before' } });
  expect(out.results.map(r => [r.meta.id, r.grkPositions, r.nearPositions])).toEqual([['a', [], [1]], ['b', [0, 1], []]]);
});
it('supports a one-position phrase with several lemma options', async () => {
  const out = await searchCombo([{ kind: 'phrase', options: [['qeos', 'qea']], match: 'lemma' }, { kind: 'form', terms: ['logos'] }],
    { window: 1, unit: 'words', ordered: false }, ['Advanced']);
  expect(out.results.map(r => [r.meta.id, r.grkPositions, r.nearPositions])).toEqual([['b', [0], [1]]]);
});
it('returns a shape alone and its ambiguity in the Greek positions', async () => {
  const out = await run('', '', { shape: { case: 'nom' } });
  expect(out.results.map(r => [r.meta.id, r.grkPositions])).toEqual([['a', [0]], ['b', [0, 1]]]);
  expect(out.results[1].grammar?.[0]).toEqual({ values: { case: ['nom', 'voc'] }, certain: false });
});
it('keeps grammatical near information parallel to nearPositions', async () => {
  const out = await run('kalos', '', { near: { ...near(), kind: 'grammatical', query: { case: 'nom' }, relation: 'after' } });
  expect(out.results[1]).toMatchObject({ grkPositions: [], nearPositions: [0], grammar: [{ values: { case: ['nom', 'voc'] }, certain: false }] });
});
it.each(['and', 'or'] as const)('combines shape and English by segment with %s', async op => {
  const out = await run('', 'men', { shape: { case: 'nom' } }, op);
  expect(out.results.map(r => r.meta.id)).toEqual(op === 'and' ? ['a'] : ['a', 'b']);
});
it('ignores near and shape for a held Greek edition and reports it', async () => {
  const out = await run('kalos', '', { near: near(['missing']) }, 'and', 'form', 'alt');
  expect(out.results[0]).toMatchObject({ grkPositions: [1], ed: 'alt' });
  expect(out.unsupported).toEqual(['Advanced']);
  expect((await run('', '', { shape: { case: 'nom' } }, 'and', 'form', 'alt')).results).toEqual([]);
});
it('English forms are opt-in for both postings and highlights', async () => {
  expect((await run('', 'man child')).results.map(r => [r.meta.id, r.slotId])).not.toContainEqual(['a', 'primary']);
  expect((await run('', 'man child', { engForms: true })).results.find(r => r.meta.id === 'a' && r.slotId === 'primary')).toMatchObject({ slotId: 'primary', engPositions: [0, 9] });
});
it.each(['near', 'before', 'after'] as const)('verifies English near in one translation with relation %s', async relation => {
  const out = await run('', 'man', { engNear: { term: 'child', relation, window: 2 } });
  expect(out.results.map(r => [r.meta.id, r.slotId])).toEqual(relation === 'before' ? [['b', 'other']] : relation === 'after' ? [] : [['b', 'other']]);
});
it('never joins English terms from different translations', async () => {
  const out = await run('', 'man', { engNear: { term: 'child', relation: 'near', window: 50 } });
  expect(out.results.some(r => r.meta.id === 'c')).toBe(false);
});
it('locates each English near hit once, by where its runs start', () => {
  expect(englishNearOccurrences('old man sees young child and old man', ['old', 'man'], 'phrase', { term: 'young child', relation: 'after', window: 4 })).toEqual({ anchors: [0], partners: [13] });
});
it('English near also uses expanded forms', async () => {
  const out = await run('', 'man', { engForms: true, engNear: { term: 'child', relation: 'after', window: 2 } });
  expect(out.results.map(r => [r.meta.id, r.slotId, r.engPositions, r.engNearPositions])).toEqual([['a', 'primary', [0], [9]]]);
});
it('shares the per-play offsets cache and retries a failed binary load', async () => {
  expect(await loadOffsets('Advanced')).toBe(await loadOffsets('Advanced'));
  expect(vi.mocked(fetch).mock.calls.filter(([u]) => String(u).endsWith('offsets.json'))).toHaveLength(1);
  await Promise.all([loadIndex('Advanced', 'meta.json'), loadIndex('Advanced', 'grammar-dict.json')]);
  vi.mocked(fetch).mockRejectedValueOnce(new Error('offline'));
  await expect(searchGrammar({ case: 'nom' }, ['Advanced'])).rejects.toThrow();
  expect((await searchGrammar({ case: 'nom' }, ['Advanced'])).results).toHaveLength(2);
});
it('reads a 32-bit grammatical column', async () => {
  files['grammar-dict.json'] = { ...dict, width: 4 };
  column = Uint32Array.from([2, 0, 3, 2, 0]);
  expect((await run('', '', { shape: { case: 'nom' } })).results).toHaveLength(2);
});
it('rejects a short grammatical column', async () => {
  column = Uint16Array.from([2]);
  await expect(run('', '', { shape: { case: 'nom' } })).rejects.toThrow(/search index/);
});

it('skips lemma-map resolution for a picked term', async () => {
  await run('zztyped', '', { lemmaPick: [['logos']] }, 'and', 'lemma');
  expect(vi.mocked(fetch).mock.calls.some(([u]) => String(u).includes('/lemma-map/z.json'))).toBe(false);
});
it('keeps shard and binary requests under the runtime data root', async () => {
  const globals = globalThis as { __READER_DATA_ROOT__?: string };
  const previous = globals.__READER_DATA_ROOT__;
  globals.__READER_DATA_ROOT__ = 'https://root.example/reader';
  try {
    await run('logos');
    await run('', '', { shape: { case: 'nom' } });
    expect(vi.mocked(fetch).mock.calls.every(([u]) => String(u).startsWith('https://root.example/reader/'))).toBe(true);
    expect(vi.mocked(fetch).mock.calls.some(([u]) => String(u).endsWith('/grammar-col.bin'))).toBe(true);
    expect(vi.mocked(fetch).mock.calls.some(([u]) => String(u).endsWith('/search-shards/index.json'))).toBe(true);
  } finally {
    if (previous === undefined) delete globals.__READER_DATA_ROOT__;
    else globals.__READER_DATA_ROOT__ = previous;
  }
});
