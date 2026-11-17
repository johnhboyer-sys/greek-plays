import { afterEach, describe, expect, it, vi } from 'vitest';

// The plays' Greek editions on the ported engine (search port): a Greek-only
// search reads a play's edition where the play holds it (its indexes under
// <play>/ed/<id>/search/), tags each hit with the edition, and reads the
// reference text for English, for the reference, and for a play without it.
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

const { search, greekHitForms } = await import('../lib/search');

// Each play: one segment, "δίκη" at token 0; the edition's segment id differs.
const files: Record<string, unknown> = {
  'held/search/meta.json': [{ id: '1:1', book: 1, column: '1' }],
  'held/search/greek_form.json': { dikh: [[0, 0]] },
  'held/search/english.json': { justice: [[0, 2]] },
  'held/ed/oct/search/meta.json': [{ id: '1:5', book: 1, column: '5' }],
  'held/ed/oct/search/greek_form.json': { dikh: [[0, 3]] },
  'plain/search/meta.json': [{ id: '1:1', book: 1, column: '1' }],
  'plain/search/greek_form.json': { dikh: [[0, 0]] },
};
const asked: string[] = [];
function stubFetch() {
  asked.length = 0;
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const path = String(input).replace(/^.*?\/data\//, '');
    asked.push(path);
    return path in files
      ? { ok: true, status: 200, json: async () => files[path] } as Response
      : { ok: false, status: 404, json: async () => ({}) } as Response;
  }));
}
afterEach(() => vi.unstubAllGlobals());

describe('search() with a Greek edition', () => {
  it('reads the edition in a play that holds it and tags its hits', async () => {
    stubFetch();
    const out = await search('δίκη', '', 'all', 'all', 'or', ['held', 'plain'], 'form', false, undefined, 'oct');
    const held = out.results.find((r) => r.work === 'held')!;
    expect(held).toMatchObject({ work: 'held', ed: 'oct', meta: { id: '1:5' }, grkPositions: [3] });
    expect(asked).toContain('held/ed/oct/search/meta.json');
    // A play without the edition reads its reference text, untagged.
    const plain = out.results.find((r) => r.work === 'plain')!;
    expect(plain.ed).toBeUndefined();
    expect(plain.meta.id).toBe('1:1');
  });

  it('reads the reference text for a search with English, and for tlg', async () => {
    stubFetch();
    const both = await search('δίκη', 'justice', 'all', 'all', 'or', ['held'], 'form', false, undefined, 'oct');
    expect(both.results.every((r) => r.ed === undefined && r.meta.id === '1:1')).toBe(true);
    stubFetch();
    const ref = await search('δίκη', '', 'all', 'all', 'or', ['held'], 'form', false, undefined, 'tlg');
    expect(ref.results[0].ed).toBeUndefined();
    expect(asked.some((p) => p.includes('/ed/'))).toBe(false);
  });

  it('reads an edition hit\'s forms from the edition', async () => {
    stubFetch();
    const out = await search('δίκη', '', 'all', 'all', 'or', ['held'], 'form', false, undefined, 'oct');
    const forms = await greekHitForms(out.results, 'δίκη', 'form');
    expect(forms.failedWorks).toEqual([]);
    expect(forms.byResult.get('held:1:5')).toEqual(['dikh']);
  });
});
