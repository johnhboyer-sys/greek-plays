import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { searchGrammar, offsetRef, englishForms, englishTermMatcher } from '../lib/search-advanced';
const meta = [{id: '1', book: 1, column: '1094a', tokens: 'a b c d', head: '', english_head: ''}];
const json = (data: unknown) => Promise.resolve({ok: true, json: async () => data} as Response);
const grammarDict = {
  token_count: 4,
  width: 2,
  categories: ['case', 'gender', 'number'],
  reserved: { unkeyed: 0, unanalysed: 1 },
  sigs: [
    [],
    [],
    [{ gender: ['fem'], case: ['nom'], number: ['sg'] }],
    [{ gender: ['fem'], case: ['nom', 'voc'], number: ['sg'] }],
    [
      { gender: ['fem'], case: ['nom'], number: ['sg'] },
      { gender: ['fem'], case: ['acc'], number: ['pl'] },
    ],
  ],
};
const grammarOffsets = {
  token_count: 4,
  seg_base_offset: [0],
  segments: [{ book: 1, column: '1094a', line_runs: [[1, 4]] }],
  book_bounds: [{ book: 1, start: 0 }],
  chapter_bounds: [{ book: 1, chapter: '1', start: 0, accuracy: 'exact' }],
};
const grammarColumn = Uint16Array.from([0, 2, 3, 4]);

describe('searchGrammar', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/offsets.json')) return json(grammarOffsets);
      if (path.endsWith('/grammar-dict.json')) return json(grammarDict);
      if (path.endsWith('/grammar-col.bin')) {
        return Promise.resolve({ ok: true, arrayBuffer: () => Promise.resolve(grammarColumn.buffer) } as Response);
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it('returns nothing for an empty query or no works', async () => {
    await expect(searchGrammar({}, ['TGEmpty'])).resolves.toEqual({ results: [], failed: [] });
    await expect(searchGrammar({ case: 'nom' }, [])).resolves.toEqual({ results: [], failed: [] });
  });

  it('finds every token a query is possible for, and reports its offset', async () => {
    const { results } = await searchGrammar({ case: 'nom' }, ['TGNom']);
    expect(results).toHaveLength(1);
    // Tokens 1, 2 and 3 all license nom; token 0 has no analysis.
    expect(results[0].grkPositions).toEqual([1, 2, 3]);
  });

  it('calls a sole unambiguous reading certain', async () => {
    const { results } = await searchGrammar({ case: 'nom' }, ['TGCertain']);
    expect(results[0].grammar![0]).toEqual({ values: { case: ['nom'] }, certain: true });
  });

  // The honesty tier. Both of these would read as a single certain parse if
  // ambiguity were counted as "number of analysis records".
  it('does not call a syncretic single analysis certain', async () => {
    const { results } = await searchGrammar({ case: 'nom' }, ['TGSyncretic']);
    expect(results[0].grammar![1]).toEqual({ values: { case: ['nom', 'voc'] }, certain: false });
  });

  it('does not call a multi-analysis token certain', async () => {
    const { results } = await searchGrammar({ case: 'nom' }, ['TGMulti']);
    expect(results[0].grammar![2]).toEqual({ values: { case: ['acc', 'nom'] }, certain: false });
  });

  it('requires one single reading to satisfy every part of the query', async () => {
    // Token 3 licenses nom (reading 1) and pl (reading 2), but no reading
    // licenses both — a per-category union would wrongly match it.
    const { results } = await searchGrammar({ case: 'nom', number: 'pl' }, ['TGCorrelation']);
    expect(results).toHaveLength(0);
  });

  it('refuses to join files built from different runs', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/offsets.json')) return json({ ...grammarOffsets, token_count: 99 });
      if (path.endsWith('/grammar-dict.json')) return json(grammarDict);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
    await expect(searchGrammar({ case: 'nom' }, ['TGMismatch'])).rejects.toThrow(/grammar index/);
  });
});

describe('offsetRef names the line a token stands on', () => {
  // stage6 writes [n, count], or [n, count, sub] on a lettered line. 244b runs
  // 4, 5, 5a, 6 here: two tokens each.
  const offsets = {
    token_count: 8,
    seg_base_offset: [0],
    segments: [{
      book: 7,
      column: '244b',
      line_runs: [[4, 2], [5, 2], [5, 2, 'a'], [6, 2]] as ([number, number] | [number, number, string])[],
    }],
    book_bounds: [{ book: 7, start: 0 }],
    chapter_bounds: [],
  };

  it('carries the letter, so a token on 244b5a is not cited as 244b5', () => {
    expect(offsetRef(offsets, 2)).toMatchObject({ column: '244b', line: 5 });
    expect(offsetRef(offsets, 2)!.sub).toBeUndefined();
    expect(offsetRef(offsets, 4)).toMatchObject({ column: '244b', line: 5, sub: 'a' });
    expect(offsetRef(offsets, 5)).toMatchObject({ line: 5, sub: 'a' });
    expect(offsetRef(offsets, 6)).toMatchObject({ line: 6 });
  });

  it('reads an older build, whose runs carry no letter', () => {
    const older = { ...offsets, segments: [{ ...offsets.segments[0], line_runs: [[4, 2], [5, 2], [5, 2], [6, 2]] as [number, number][] }] };
    expect(offsetRef(older, 4)).toMatchObject({ line: 5 });
    expect(offsetRef(older, 4)!.sub).toBeUndefined();
  });
});

describe('English any form', () => {
  it('reaches plural and possessive forms, and back', () => {
    expect(englishForms('virtue')).toEqual(expect.arrayContaining(['virtue', 'virtues', "virtue's"]));
    expect(englishForms('virtues')).toEqual(expect.arrayContaining(['virtue', "virtue's"]));
    expect(englishForms("aristotle's")).toEqual(expect.arrayContaining(['aristotle', "aristotle's"]));
    expect(englishForms('body')).toEqual(expect.arrayContaining(['bodies', "body's"]));
    expect(englishForms('bodies')).toContain('body');
    expect(englishForms('class')).toContain('classes');
    expect(englishForms('causes')).toContain('cause');
    expect(englishForms('hero')).toContain('heroes');
  });

  it('knows the irregulars, and every -man compound', () => {
    expect(englishForms('man')).toEqual(expect.arrayContaining(['men', "man's", "men's"]));
    expect(englishForms('men')).toContain('man');
    expect(englishForms('woman')).toContain('women');
    expect(englishForms('statesmen')).toContain('statesman');
    expect(englishForms('child')).toEqual(expect.arrayContaining(['children', "children's"]));
    expect(englishForms('phenomena')).toContain('phenomenon');
    expect(englishForms('ox')).toContain('oxen');
  });

  it('leaves short words and wildcards alone, and keeps a singular in -s whole', () => {
    expect(englishForms('a')).toEqual(['a']);
    expect(englishForms('is')).toEqual(['is']);
    expect(englishForms('us')).toEqual(['us']);
    expect(englishForms('virtue*')).toEqual(['virtue*']);
    expect(englishForms('his')).not.toContain('hi');
    expect(englishForms('his')).not.toContain('hiss');
    expect(englishForms('genus')).not.toContain('genu');
    expect(englishForms('this')).not.toContain('thi');
  });

  it('gives a singular in -s its possessive', () => {
    expect(englishForms('class')).toContain("class's");
    expect(englishForms('basis')).toContain("basis's");
  });

  it('does not take an -s word that is no plural for one', () => {
    expect(englishForms('news')).not.toContain('new');
    expect(englishForms('politics')).not.toContain('politic');
    expect(englishForms('means')).not.toContain('mean');
    expect(englishForms('mean')).not.toContain('means');
    expect(englishForms('mean')).toContain("mean's");
  });

  it('does not take a determiner for the singular of a plural', () => {
    expect(englishForms('theses')).not.toContain('these');
    expect(englishForms('theses')).toContain('thesis');
    expect(englishForms('these')).toEqual(['these']);
  });

  it('gives a word in -ch both plurals', () => {
    expect(englishForms('stomach')).toEqual(expect.arrayContaining(['stomachs', 'stomaches']));
    expect(englishForms('church')).toContain('churches');
    expect(englishForms('epochs')).toContain('epoch');
  });

  it('matches a word by any form only when asked', () => {
    expect(['virtue', 'virtues', "virtue's", 'virtuous'].map(englishTermMatcher(['virtue'], true)))
      .toEqual([true, true, true, false]);
    expect(englishTermMatcher(['virtue'])('virtues')).toBe(false);
  });

});

it('matches plural possessives with this corpus tokeniser', () => {
  expect(englishForms('child')).toContain("children's");
  expect(englishForms('word')).toContain("words'");
  expect(englishForms("words'")).toContain('word');
  expect(englishTermMatcher(['word'], true)("words'")).toBe(true);
});
