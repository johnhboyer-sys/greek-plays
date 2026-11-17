import { afterEach, describe, expect, it, vi } from 'vitest';

// Codex review of the search port (16 Nov), the engine's part: a search with
// English and a Greek edition (fix 1), an old multiword lemma search's
// headword picks (fix 4), and the Near-in-an-edition fallback for a headword
// phrase and a grammar term (fix 5).
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const play = (id: string, eds: string[]) => ({
    id, title: id, abbr: id, author: 'aeschylus', language: 'grc', bookLabels: [], citation: { scheme: 'play-line' },
    translations: [{ id: 'smyth', slot: 'english', short: 'Smyth', name: 'Smyth' }],
    greekEditions: eds.map((e) => ({ id: e, short: e, full: e, editor: e, year: 1900, kind: 'ocr', licence: null })),
    greekSource: { short: 'TLG', full: 'TLG' },
  });
  const works = { held: play('held', ['oct']), plain: play('plain', []) } as Record<string, unknown>;
  return { ...actual, getWork: (id: string) => works[id] ?? actual.getWork(id) };
});

const { search, searchComboInEdition } = await import('../lib/search');
import type { ComboOptions, ComboSlot, SearchResult } from '../lib/search';

// "λόγος θεός" at tokens 0–1 of each text; the edition's segment differs.
// The lemma map files λόγου under λόγος and θεούς under θεός and θεά.
const files: Record<string, unknown> = {
  'held/search/meta.json': [{ id: '1:1', book: 1, column: '1' }],
  'held/search/greek_lemma.json': { logos: [[0, 0]], qeos: [[0, 1]] },
  'held/search/greek_form.json': { logou: [[0, 0]], qeous: [[0, 1]] },
  'held/search/english.json': { word: [[0, 0]] },
  'held/ed/oct/search/meta.json': [{ id: '1:5', book: 1, column: '5' }],
  'held/ed/oct/search/greek_lemma.json': { logos: [[0, 4]], qeos: [[0, 5]] },
  'held/ed/oct/search/greek_form.json': { logou: [[0, 4]], qeous: [[0, 5]] },
  'plain/search/meta.json': [{ id: '1:1', book: 1, column: '1' }],
  'plain/search/greek_lemma.json': { logos: [[0, 0]], qea: [[0, 1]] },
  'plain/search/greek_form.json': { logou: [[0, 0]], qeous: [[0, 1]] },
  'plain/search/english.json': {},
  'lemma-map/l.json': { logou: [['logos', 'λόγος']] },
  'lemma-map/q.json': { qeous: [['qeos', 'θεός'], ['qea', 'θεά']] },
};
function stubFetch() {
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const path = String(input).replace(/^.*?\/data\//, '');
    return path in files
      ? { ok: true, status: 200, json: async () => files[path] } as Response
      : { ok: false, status: 404, json: async () => ({}) } as Response;
  }));
}
afterEach(() => vi.unstubAllGlobals());

const hit = (work: string): SearchResult => ({ work, meta: { id: '1:1', book: 1, column: '1' }, grkMatch: true, engMatch: false, grkPositions: [0] } as SearchResult);
const opts: ComboOptions = { window: 10, unit: 'words', ordered: false };

describe('review fix 4: a lemma search of several words, each by its ticked headwords', () => {
  it('searches each word only by its picks, and a word with none as typed', async () => {
    stubFetch();
    // Unpicked, θεούς is θεός or θεά: both plays answer.
    const all = await search('logou qeous', '', 'all', 'all', 'or', ['held', 'plain'], 'lemma');
    expect(all.results.map((r) => r.work).sort()).toEqual(['held', 'plain']);
    // θεούς picked as θεά only: only the play where it is θεά.
    const picked = await search('logou qeous', '', 'all', 'all', 'or', ['held', 'plain'], 'lemma', false, undefined, null, null, [[], ['qea']]);
    expect(picked.results.map((r) => r.work)).toEqual(['plain']);
  });
});

describe('review fix 1: a search with English and a Greek edition', () => {
  it('reads the main text in a play holding the edition, and names it', async () => {
    stubFetch();
    const both = await search('logou', 'word', 'all', 'all', 'and', ['held', 'plain'], 'form', false, undefined, 'oct');
    expect(both.results.find((r) => r.work === 'held')).toMatchObject({ meta: { id: '1:1' }, grkPositions: [0] });
    expect(both.results.every((r) => r.ed === undefined)).toBe(true);
    expect(both.mainText).toEqual(['held']);
    // Greek alone reads the edition, and English alone names no play.
    expect((await search('logou', '', 'all', 'all', 'or', ['held'], 'form', false, undefined, 'oct')).mainText).toBeUndefined();
    expect((await search('', 'word', 'all', 'all', 'or', ['held'], 'form', false, undefined, 'oct')).mainText).toBeUndefined();
  });

  it('runs Near on the main text in every play when the search has English, and names the plays holding the edition', async () => {
    const run = vi.fn(async () => ({ results: [hit('held'), hit('plain')], failedWorks: [] }));
    const slots: ComboSlot[] = [{ kind: 'form', terms: ['λόγου'] }, { kind: 'form', terms: ['θεούς'] }];
    const out = await searchComboInEdition(slots, opts, ['held', 'plain'], 'oct', false, run, true);
    expect(run).toHaveBeenCalledWith(slots, opts, ['held', 'plain']);
    expect(out.results.map((r) => [r.work, r.ed, r.meta.id])).toEqual([['held', undefined, '1:1'], ['plain', undefined, '1:1']]);
    expect(out.unsupported).toBeUndefined();
    expect(out.mainText).toEqual(['held']);
  });
});

describe('review fix 5: Near in an edition, a first term the edition search cannot read', () => {
  const run = vi.fn(async () => ({ results: [hit('plain')], failedWorks: [] }));

  it('searches a headword phrase in the edition by its words\' headwords', async () => {
    stubFetch();
    const slots: ComboSlot[] = [{ kind: 'phrase', options: [['logos'], ['qeos']], match: 'lemma' }, { kind: 'form', terms: ['καλός'] }];
    const out = await searchComboInEdition(slots, opts, ['held', 'plain'], 'oct', false, run);
    expect(out.unsupported).toEqual(['held']);
    expect(out.results.find((r) => r.work === 'held')).toMatchObject({ ed: 'oct', meta: { id: '1:5' }, grkPositions: [4, 5] });
  });

  it('searches a grammar term in the main text with Near, and names the plays, never a silent zero', async () => {
    const both = vi.fn(async () => ({ results: [hit('held'), hit('plain')], failedWorks: [] }));
    const slots: ComboSlot[] = [{ kind: 'grammatical', query: { case: 'gen' } }, { kind: 'form', terms: ['καλός'] }];
    const out = await searchComboInEdition(slots, opts, ['held', 'plain'], 'oct', false, both);
    expect(out.results.map((r) => r.work)).toEqual(['held', 'plain']);
    expect(out.unsupported).toBeUndefined();
    expect(out.mainText).toEqual(['held']);
  });
});
