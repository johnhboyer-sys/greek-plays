import { afterEach, describe, expect, it, vi } from 'vitest';

// Near with a Greek edition chosen (search port): a play that holds the
// edition is not asked the Near search. Its first term is searched in the
// edition alone, and the play is named for the page's note, as on the old page.
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

const { searchComboInEdition } = await import('../lib/search');
import type { ComboOptions, ComboSlot, SearchResult } from '../lib/search';

const files: Record<string, unknown> = {
  'held/ed/oct/search/meta.json': [{ id: '1:5', book: 1, column: '5' }],
  'held/ed/oct/search/greek_form.json': { dikh: [[0, 3]] },
};
afterEach(() => vi.unstubAllGlobals());
const hit = (work: string): SearchResult => ({ work, meta: { id: '1:1', book: 1, column: '1' }, grkMatch: true, engMatch: false, grkPositions: [0] } as SearchResult);
const slots: ComboSlot[] = [{ kind: 'form', terms: ['δίκη'] }, { kind: 'form', terms: ['θεός'] }];
const opts: ComboOptions = { window: 10, unit: 'words', ordered: false };

describe('searchComboInEdition', () => {
  const nearRun = vi.fn(async () => ({ results: [hit('held'), hit('plain')], failedWorks: [] }));

  it('leaves Near off a play that holds the chosen edition, and names it', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: string) => {
      const path = String(input).replace(/^.*?\/data\//, '');
      return path in files ? { ok: true, status: 200, json: async () => files[path] } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    }));
    const out = await searchComboInEdition(slots, opts, ['held', 'plain'], 'oct', false, nearRun);
    expect(out.unsupported).toEqual(['held']);
    // The play without the edition keeps its Near hit; the other holds its first term, in the edition.
    expect(out.results.find((r) => r.work === 'plain')).toMatchObject({ meta: { id: '1:1' } });
    expect(out.results.find((r) => r.work === 'held')).toMatchObject({ ed: 'oct', meta: { id: '1:5' }, grkPositions: [3] });
    expect(out.results.filter((r) => r.work === 'held')).toHaveLength(1);
  });

  it('changes nothing for the main text, or an edition no play in the search holds', async () => {
    for (const ed of ['tlg', null, 'nobody']) {
      const out = await searchComboInEdition(slots, opts, ['held', 'plain'], ed, false, nearRun);
      expect(out.unsupported).toBeUndefined();
      expect(out.results.map((r) => r.work)).toEqual(['held', 'plain']);
    }
  });
});
