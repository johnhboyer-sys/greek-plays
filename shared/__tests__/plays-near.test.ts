import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// The plays' Near rules on Aristotle's engine (search port, lane 2;
// docs/search-port/near-engine.md option A). Each rule is a ComboOptions
// switch that works.ts NEAR_RULES turns on for the plays; these are the
// legacy Near tests (legacy/search-combo.test.ts, search-advanced.test.ts),
// ported to the new engine with the switches on.
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const play = {
    id: 'Advanced', title: 'Advanced', abbr: 'Adv', author: 'aeschylus', language: 'grc', bookLabels: [], citation: { scheme: 'play-line' },
    translations: [
      { id: 'primary', slot: 'english', short: 'Primary', name: 'Primary' },
      { id: 'other', slot: 'secondary', short: 'Other', name: 'Other' },
    ],
    greekSource: { short: 'TLG', full: 'TLG' },
  };
  return { ...actual, getWork: (id: string) => (id === 'Advanced' ? play : actual.getWork(id)) };
});

const { searchCombo, comboWindows, search, COMBO_WINDOW_MAX } = await import('../lib/search');
const { NEAR_RULES, NEAR_WINDOW_DEFAULT } = await import('../lib/works');
const { chapterPlaces, eachHit } = await import('../lib/chapter-pages');
type ComboOptions = import('../lib/search').ComboOptions;
type SearchResult = import('../lib/search').SearchResult;

const json = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response);
const opts = (over: Partial<ComboOptions> = {}): ComboOptions => ({
  window: NEAR_WINDOW_DEFAULT, unit: 'words', ordered: false, ...NEAR_RULES, ...over,
});
const slot = (...terms: string[]) => ({ kind: 'form' as const, terms });
const positions = (r: { grkPositions: number[] }) => [...new Set(r.grkPositions)].sort((a, b) => a - b);

describe('the plays Near rules (legacy search-combo tests)', () => {
  const meta = [
    { id: '1:1000a', book: 1, column: '1000a' },
    { id: '2:1001a', book: 2, column: '1001a' },
    { id: '2:1001b', book: 2, column: '1001b' },
  ];
  const offsets = {
    token_count: 40,
    seg_base_offset: [0, 20, 30],
    segments: [
      { book: 1, column: '1000a', line_runs: [[1, 5], [2, 5], [3, 5], [4, 5]] },
      { book: 2, column: '1001a', line_runs: [[1, 5], [2, 5]] },
      { book: 2, column: '1001b', line_runs: [[1, 5], [2, 5]] },
    ],
    book_bounds: [{ book: 1, start: 0 }, { book: 2, start: 20 }],
  };
  const form: Record<string, [number, number][]> = {
    alpha: [[0, 2]], beta: [[0, 4]], delta: [[0, 3]], epsilon: [[0, 8]], zeta: [[0, 12]], eta: [[0, 19]],
    theta: [[1, 1]], iota: [[0, 10]], kappa: [[0, 5], [0, 12]], lambda: [[0, 18]],
    mu: [[1, 9]],    // global 29, last token of 1001a
    nu: [[2, 0]],    // global 30, first token of 1001b
    feu: [[0, 14], [0, 15], [0, 16]],   // φεῦ φεῦ φεῦ: two overlapping runs of φεῦ φεῦ
    alpha2: [[0, 2]],   // a second headword on alpha's word, as δικεῖν shares δίκη's
  };
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/offsets.json')) return json(offsets);
      if (path.endsWith('/greek_form.json') || path.endsWith('/greek_lemma.json')) return json(form);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });
  afterEach(() => vi.restoreAllMocks());

  // Two picked headwords may index one word (δίκη's fold is δικεῖν's too):
  // the term finds that word twice, and under byFirstWord the match was
  // listed twice (Libation Bearers 165, δίκη near θεός: 79 hits where the
  // old page had 74). It is one match.
  it('lists a word two picked headwords share once per match', async () => {
    const out = await searchCombo([slot('alpha', 'alpha2'), slot('beta')], opts(), ['Dup']);
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['1:1000a', [[2, 4]]]]);
  });

  it('opens at 10 words, as the plays Near did', () => {
    expect(NEAR_WINDOW_DEFAULT).toBe(10);
  });

  it('files a hit under its first word\'s passage, its partner counting on into the next', async () => {
    const out = await searchCombo([slot('mu'), { ...slot('nu'), relation: 'after' as const }], opts({ window: 1 }), ['N1']);
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['2:1001a', [[9, 10]]]]);
  });

  it('files a hit whose partner stands in the passage before under the first word\'s passage', async () => {
    const out = await searchCombo([slot('nu'), { ...slot('mu'), relation: 'before' as const }], opts({ window: 1 }), ['N1b']);
    // nu is word 0 of 1001b; mu, one word before, is word -1 of it.
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['2:1001b', [[0, -1]]]]);
  });

  it('keeps overlapping runs of a phrase apart: φεῦ φεῦ φεῦ holds two hits of φεῦ φεῦ', async () => {
    const out = await searchCombo([{ kind: 'phrase' as const, terms: ['feu', 'feu'] }, slot('zeta')], opts({ window: 5 }), ['N2']);
    const windows = out.results.find(r => r.meta.id === '1:1000a')?.windows ?? [];
    expect(windows.map(w => w.slice(0, 2))).toEqual([[14, 15], [15, 16]]);
    expect(windows.every(w => w.includes(12))).toBe(true);
  });

  it('counts "X near X" once for each X', async () => {
    const out = await searchCombo([slot('kappa'), slot('kappa')], opts({ window: 8 }), ['N3']);
    expect(out.results[0].windows).toEqual([[5, 12], [12, 5]]);
  });

  it('needs at least two usable slots', async () => {
    await expect(searchCombo([slot('alpha')], opts(), ['C1'])).resolves.toEqual({ results: [], failedWorks: [] });
    await expect(searchCombo([slot('alpha'), slot()], opts(), ['C2'])).resolves.toEqual({ results: [], failedWorks: [] });
    await expect(searchCombo([slot('alpha'), slot('beta')], opts(), [])).resolves.toEqual({ results: [], failedWorks: [] });
  });

  it('finds two terms inside the window and marks both tokens', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ window: 5 }), ['C3']);
    expect(results).toHaveLength(1);
    expect(results[0].meta.id).toBe('1:1000a');
    expect(positions(results[0])).toEqual([2, 4]);
  });

  it('respects the window size', async () => {
    expect((await searchCombo([slot('alpha'), slot('beta')], opts({ window: 1 }), ['C4'])).results).toHaveLength(0);
  });

  it('is unordered by default and order-locked on request', async () => {
    expect((await searchCombo([slot('beta'), slot('alpha')], opts({ window: 5 }), ['C5'])).results).toHaveLength(1);
    expect((await searchCombo([slot('beta'), slot('alpha')], opts({ window: 5, ordered: true }), ['C6'])).results).toHaveLength(0);
  });

  it('never spans a book edge, however wide the window', async () => {
    expect((await searchCombo([slot('eta'), slot('theta')], opts({ window: COMBO_WINDOW_MAX }), ['C7'])).results).toHaveLength(0);
  });

  it('measures by line when the unit is a line', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ unit: 'line', window: 0 }), ['C10']);
    expect(positions(results[0])).toEqual([2, 4]);
    expect((await searchCombo([slot('alpha'), slot('epsilon')], opts({ unit: 'line', window: 0 }), ['C11'])).results).toHaveLength(0);
    // One line either side reaches epsilon, on the next line.
    expect((await searchCombo([slot('alpha'), slot('epsilon')], opts({ unit: 'line', window: 1 }), ['C12'])).results).toHaveLength(1);
  });

  it('accepts a wildcard in a slot, including inside a phrase run', async () => {
    const f = await searchCombo([slot('alph*'), slot('bet?')], opts({ window: 5 }), ['CW1']);
    expect(positions(f.results[0])).toEqual([2, 4]);
    const phrase = await searchCombo([{ kind: 'phrase', terms: ['delt*', 'beta'] }, slot('alpha')], opts({ window: 5 }), ['CW2']);
    expect(positions(phrase.results[0])).toEqual([2, 3, 4]);
  });

  it('finds a window that needs a later occurrence than the first feasible one', async () => {
    const { results } = await searchCombo([slot('iota'), slot('kappa'), slot('lambda')], opts({ window: 8 }), ['CG1']);
    expect(results).toHaveLength(1);
    // kappa at 5, in range of iota too, is marked with the match (Aristotle's
    // R3, kept), never counted: one window.
    expect(results[0].windows).toHaveLength(1);
    expect(positions(results[0])).toEqual([5, 10, 12, 18]);
  });

  it('still rejects that group when the window is genuinely too small', async () => {
    expect((await searchCombo([slot('iota'), slot('kappa'), slot('lambda')], opts({ window: 7 }), ['CG2'])).results).toHaveLength(0);
  });

  it('will not satisfy two identical slots with one token', async () => {
    expect((await searchCombo([slot('alpha'), slot('alpha')], opts({ window: 5 }), ['CD1'])).results).toHaveLength(0);
    expect(positions((await searchCombo([slot('kappa'), slot('kappa')], opts({ window: 8 }), ['CD2'])).results[0])).toEqual([5, 12]);
  });

  it('never lets one word answer two terms, even different ones', async () => {
    const { results } = await searchCombo([{ kind: 'lemma', terms: ['alpha'] }, slot('alpha')], opts({ window: 5 }), ['CD3']);
    expect(results).toHaveLength(0);
    const two = await searchCombo([{ kind: 'lemma', terms: ['kappa'] }, slot('kappa')], opts({ window: 8 }), ['CD4']);
    expect(positions(two.results[0])).toEqual([5, 12]);
    // Aristotle's rule, with the switch off: one word answers both.
    const one = await searchCombo([{ kind: 'lemma', terms: ['alpha'] }, slot('alpha')], opts({ window: 5, distinctWords: false }), ['CD5']);
    expect(one.results).toHaveLength(1);
  });

  it('unions the heads a lemma slot carries', async () => {
    const { results } = await searchCombo([{ kind: 'lemma', terms: ['beta', 'zeta'] }, slot('alpha')], opts({ window: 5 }), ['C13']);
    expect(positions(results[0])).toEqual([2, 4]);
  });

  it('caps the window rather than trusting the caller', async () => {
    expect((await searchCombo([slot('eta'), slot('theta')], opts({ window: 9999 }), ['C14'])).results).toHaveLength(0);
  });

  it('measures each term from the first word on its own', async () => {
    const fromAlpha = (w: number) => searchCombo([slot('alpha'), slot('beta'), slot('epsilon')], opts({ window: w }), [`CO-a${w}`]);
    expect((await fromAlpha(5)).results).toHaveLength(0);
    expect((await fromAlpha(6)).results).toHaveLength(1);
    const fromBeta = (w: number) => searchCombo([slot('beta'), slot('alpha'), slot('epsilon')], opts({ window: w }), [`CO-b${w}`]);
    expect((await fromBeta(3)).results).toHaveLength(0);
    expect((await fromBeta(4)).results).toHaveLength(1);
    expect((await searchCombo([slot('beta'), slot('epsilon'), slot('alpha')], opts({ window: 4 }), ['CO-c4'])).results).toHaveLength(1);
  });

  it('measures a phrase before the first word from its last word', async () => {
    // delta beta covers 3-4; epsilon at 8 is 4 words after the phrase's end.
    const near = [slot('epsilon'), { kind: 'phrase' as const, terms: ['delta', 'beta'], relation: 'before' as const }];
    expect(positions((await searchCombo(near, opts({ window: 4 }), ['CR8'])).results[0])).toEqual([3, 4, 8]);
    // Start to start (Aristotle's rule) it is 5 away.
    expect((await searchCombo(near, opts({ window: 4, fromNearerEnd: false }), ['CR9'])).results).toHaveLength(0);
  });

  it('measures a word after a phrase from the phrase\'s last word', async () => {
    // delta beta covers 3-4; epsilon at 8 is 4 words on from beta.
    const near = [{ kind: 'phrase' as const, terms: ['delta', 'beta'] }, slot('epsilon')];
    expect(positions((await searchCombo(near, opts({ window: 4 }), ['CR10'])).results[0])).toEqual([3, 4, 8]);
    expect((await searchCombo(near, opts({ window: 4, fromNearerEnd: false }), ['CR11'])).results).toHaveLength(0);
  });

  it('keeps a phrase inside the unit it is measured in', async () => {
    const { results } = await searchCombo([{ kind: 'phrase', terms: ['delta', 'beta'] }, slot('alpha')], opts({ unit: 'line', window: 0 }), ['CO7']);
    expect(positions(results[0])).toEqual([2, 3, 4]);
  });

  it('reports ambiguity per slot, not per window', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ window: 5 }), ['CO8']);
    expect(results[0].grammar?.every(g => g.certain && !Object.keys(g.values).length)).toBe(true);
  });

  describe('slot relation', () => {
    it('near accepts a hit on either side', async () => {
      expect((await searchCombo([slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'near' }], opts({ window: 5 }), ['CR1'])).results).toHaveLength(1);
    });
    it('before requires the slot to end at or before the first slot begins', async () => {
      expect((await searchCombo([slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'before' }], opts({ window: 5 }), ['CR2'])).results).toHaveLength(1);
      expect((await searchCombo([slot('beta'), { kind: 'form', terms: ['epsilon'], relation: 'before' }], opts({ window: 5 }), ['CR3'])).results).toHaveLength(0);
    });
    it('after requires the slot to begin at or after the first slot ends', async () => {
      expect((await searchCombo([slot('beta'), { kind: 'form', terms: ['epsilon'], relation: 'after' }], opts({ window: 5 }), ['CR4'])).results).toHaveLength(1);
      expect((await searchCombo([slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'after' }], opts({ window: 5 }), ['CR5'])).results).toHaveLength(0);
    });
    it('places each slot against the first, not against its predecessor', async () => {
      const { results } = await searchCombo([
        slot('delta'),
        { kind: 'form', terms: ['alpha'], relation: 'before' },
        { kind: 'form', terms: ['beta'], relation: 'after' },
      ], opts({ window: 5 }), ['CR6']);
      expect(positions(results[0])).toEqual([2, 3, 4]);
    });
    it('measures a preceding phrase by its end, not its start', async () => {
      const { results } = await searchCombo([slot('epsilon'), { kind: 'phrase', terms: ['delta', 'beta'], relation: 'before' }], opts({ window: 5 }), ['CR7']);
      expect(positions(results[0])).toEqual([3, 4, 8]);
    });
  });

  it('treats a phrase slot as a run and reports every token in it', async () => {
    const { results } = await searchCombo([{ kind: 'phrase', terms: ['delta', 'beta'] }, slot('alpha')], opts({ window: 5 }), ['C15']);
    expect(positions(results[0])).toEqual([2, 3, 4]);
  });

  it('reads two lemma slots with the same heads as the same slot, whatever the tick order', async () => {
    const { results } = await searchCombo([{ kind: 'lemma', terms: ['alpha', 'beta'] }, { kind: 'lemma', terms: ['beta', 'alpha'] }], opts({ window: 5 }), ['CID1']);
    expect(positions(results[0])).toEqual([2, 4]);
    const none = await searchCombo([{ kind: 'lemma', terms: ['alpha', 'eta'] }, { kind: 'lemma', terms: ['eta', 'alpha'] }], opts({ window: 5 }), ['CID2']);
    expect(none.results).toHaveLength(0);
  });

  it('keeps a phrase slot ordered: "delta beta" and "beta delta" are two questions', async () => {
    const { results } = await searchCombo([{ kind: 'phrase', terms: ['delta', 'beta'] }, { kind: 'phrase', terms: ['beta', 'delta'] }], opts({ window: 5 }), ['CID3']);
    expect(results).toHaveLength(0);
  });
});

describe('placing the terms (legacy comboWindows tests)', () => {
  const off = { token_count: 10, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 10]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
  const hit = (start: number, certain = true) => ({ start, span: 1, certain });

  it('finds a match a greedy first pick would block', () => {
    // Term 2 can use 1 or 2, term 3 only 1: taking 1 for term 2 must be undone.
    const windows = comboWindows([[hit(0)], [hit(1), hit(2)], [hit(1)]], opts({ window: 3 }), off);
    expect(windows.map(w => w.hits.map(h => h.start))).toEqual([[0, 2, 1]]);
  });

  it('prefers a word whose every reading fits over a nearer ambiguous one', () => {
    // Anchor 5; an ambiguous vocative at 4 (ἐμέ), a sure one at 7 (παῖ).
    const windows = comboWindows([[hit(5)], [hit(4, false), hit(7)]], opts({ window: 3 }), off);
    expect(windows.map(w => w.hits.map(h => h.start))).toEqual([[5, 7]]);
    // Only the ambiguous one in reach: the line still matches.
    expect(comboWindows([[hit(5)], [hit(4, false)]], opts({ window: 3 }), off)).toHaveLength(1);
    // Index order with the switch off.
    expect(comboWindows([[hit(5)], [hit(4, false), hit(7)]], opts({ window: 3, preferCertain: false }), off)[0].hits.map(h => h.start)).toEqual([5, 4]);
  });

  it('prefers the nearest word among the sure ones', () => {
    const windows = comboWindows([[hit(5)], [hit(1), hit(3), hit(8)]], opts({ window: 5 }), off);
    expect(windows[0].hits.map(h => h.start)).toEqual([5, 3]);
  });

  it('counts lines either side of the first word, 0 being its own line', () => {
    // Five lines of two tokens: line k holds tokens 2k and 2k+1.
    const lines = { token_count: 10, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 2], [2, 2], [3, 2], [4, 2], [5, 2]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
    const found = (n: number, partner: number, either = true) =>
      comboWindows([[hit(4)], [hit(partner)]], opts({ window: n, unit: 'line', linesEitherSide: either }), lines).length;
    expect(found(0, 5)).toBe(1);   // same line
    expect(found(0, 6)).toBe(0);   // next line
    expect(found(1, 6)).toBe(1);
    expect(found(1, 1)).toBe(0);   // two lines back
    expect(found(2, 1)).toBe(1);
    // Aristotle's line unit: the same line, whatever the window.
    expect(found(2, 1, false)).toBe(0);
    expect(found(2, 5, false)).toBe(1);
  });

  it('counts a lacuna line as a line', () => {
    // Line 2 is a lacuna: no tokens.
    const lines = { token_count: 4, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 2], [2, 0], [3, 2]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
    const found = (n: number) => comboWindows([[hit(0)], [hit(2)]], opts({ window: n, unit: 'line' }), lines).length;
    expect(found(1)).toBe(0);
    expect(found(2)).toBe(1);
  });
});

describe('Near in a play with grammar and lemmas (legacy search-advanced tests)', () => {
  // Tokens: 0 logos, 1 kalos | 2 qea, 3 logos | (book 2) 4 qea.
  const meta = [
    { id: 'a', book: 1, column: '1' },
    { id: 'b', book: 1, column: '2' },
    { id: 'c', book: 2, column: '3' },
  ];
  const form = { logos: [[0, 0], [1, 1]], kalos: [[0, 1]], qea: [[1, 0], [2, 0]] };
  const lemma = { logos: [[0, 0], [1, 1]], kalos: [[0, 1]], qeos: [[1, 0]], qea: [[2, 0]] };
  const offsets = {
    token_count: 5, seg_base_offset: [0, 2, 4], book_bounds: [{ book: 1, start: 0 }, { book: 2, start: 4 }],
    segments: meta.map(m => ({ book: m.book, column: m.column, line_runs: [[1, m.id === 'c' ? 1 : 2]] })),
    chapter_bounds: [{ book: 1, chapter: '1', start: 0, accuracy: 'exact' }, { book: 1, chapter: '2', start: 2, accuracy: 'exact' }, { book: 2, chapter: '3', start: 4, accuracy: 'exact' }],
  };
  const dict = { token_count: 5, width: 2, categories: ['case'], reserved: { unkeyed: 0, unanalysed: 1 },
    sigs: [[], [], [{ case: ['nom'] }], [{ case: ['nom', 'voc'] }]] };
  // English, with word positions, one index per translation.
  // a: primary "men love children", other "man sees a child"
  // b: primary "man far far far child", other "child loves man"
  // c: primary "man", other "child"
  const english = { men: [[0, 0]], love: [[0, 1]], children: [[0, 2]], man: [[1, 0], [2, 0]], far: [[1, 1], [1, 2], [1, 3]], child: [[1, 4]] };
  const secondary = { man: [[0, 0], [1, 2]], sees: [[0, 1]], a: [[0, 2]], child: [[0, 3], [1, 0], [2, 0]], loves: [[1, 1]] };
  const column = Uint16Array.from([2, 0, 3, 2, 0]);
  const files: Record<string, unknown> = {
    'meta.json': meta, 'greek_form.json': form, 'greek_lemma.json': lemma, 'offsets.json': offsets, 'grammar-dict.json': dict,
    'english.json': english, 'english-secondary.json': secondary,
  };
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(url => {
      const path = String(url);
      if (path.endsWith('grammar-col.bin')) return Promise.resolve({ ok: true, arrayBuffer: async () => column.buffer } as Response);
      const file = path.split('/').pop()!;
      return path.includes('/Advanced/') && file in files ? json(files[file]) : Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });
  afterEach(() => vi.restoreAllMocks());
  const after = (terms: string[]) => ({ kind: 'form' as const, terms, relation: 'after' as const });

  it('puts the near word in the first word\'s passage across a segment edge', async () => {
    const out = await searchCombo([slot('kalos'), after(['qea'])], opts({ window: 2 }), ['Advanced']);
    // The near word in passage b is the hit's partner; passage b is no hit of its own.
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['a', [[1, 2]]]]);
  });

  it('uses per-position lemma choices for a phrase as the first term', async () => {
    const out = await searchCombo([{ kind: 'phrase', options: [['qeos'], ['logos']], match: 'lemma' }, { ...slot('kalos'), relation: 'before' }], opts({ window: 2 }), ['Advanced']);
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['b', [[0, 1, -1]]]]);
  });

  it('supports a one-position phrase with several lemma options', async () => {
    const out = await searchCombo([{ kind: 'phrase', options: [['qeos', 'qea']], match: 'lemma' }, slot('logos')], opts({ window: 1 }), ['Advanced']);
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['b', [[0, 1]]]]);
  });

  it('takes the surely nominative word as the near partner', async () => {
    const out = await searchCombo([slot('kalos'), { kind: 'grammatical', query: { case: 'nom' }, relation: 'after' }], opts({ window: 2 }), ['Advanced']);
    // Token 2 (nom/voc) is nearer, but token 3 is surely nominative and is
    // the partner: its reading is the one shown. Token 2, in range, is marked
    // with the match (R3), not counted.
    expect(out.results.map(r => [r.meta.id, r.windows])).toEqual([['a', [[1, 2, 3]]]]);
    expect(out.results[0].grammar?.[out.results[0].grkPositions.indexOf(3)]).toEqual({ values: { case: ['nom'] }, certain: true });
    const off = { ...offsets } as never;
    const chosen = comboWindows([[{ start: 1, span: 1, certain: true }], [{ start: 2, span: 1, certain: false }, { start: 3, span: 1, certain: true }]],
      opts({ window: 2 }), off, ['near', 'after']);
    expect(chosen[0].hits.map(h => h.start)).toEqual([1, 3]);
  });

  it('places further Near terms against the first word, each with its own relation', async () => {
    const hits = async (more: import('../lib/search').ComboSlot) =>
      (await searchCombo([slot('kalos'), after(['qea']), more], opts({ window: 2 }), ['Advanced'])).results.flatMap(r => r.windows ?? []);
    expect(await hits({ kind: 'form', terms: ['logos'], relation: 'after' })).toEqual([[1, 2, 3]]);
    expect(await hits({ kind: 'form', terms: ['logos'], relation: 'before' })).toEqual([[1, 0, 2]]);
    expect(await hits({ kind: 'grammatical', query: { case: 'voc' }, relation: 'before' })).toEqual([]);
  });

  it('counts a near hit in the speech of its first Greek word, not of the near word', async () => {
    const out = await searchCombo([slot('kalos'), after(['qea'])], opts({ window: 2 }), ['Advanced']);
    const places = chapterPlaces(new Map([['Advanced', offsets as never]]));
    const at: string[] = [];
    for (const r of out.results) eachHit(r, places, a => at.push(a.chapter));
    expect(at).toEqual(['1']);
  });

  const run = (eng: string, near: import('../lib/search').EngNear, forms = false) =>
    search('', eng, 'all', 'all', 'or', ['Advanced'], 'lemma', forms, undefined, null, near);
  const found = (results: SearchResult[]) => results.flatMap(r => (r.engHits ?? []).map(h => [r.meta.id, h.translation]));

  it.each(['near', 'before', 'after'] as const)('verifies English near in one translation with relation %s', async relation => {
    const out = await run('man', { term: 'child', relation, window: 2 });
    expect(found(out.results)).toEqual(relation === 'after' ? [] : [['b', 'other']]);
  });

  it('never joins English terms from different translations', async () => {
    const out = await run('man', { term: 'child', relation: 'near', window: 50 });
    expect(out.results.some(r => r.meta.id === 'c')).toBe(false);
  });

  it('English near also uses expanded forms, and counts each run of the box\'s words once', async () => {
    const out = await run('man', { term: 'child', relation: 'after', window: 2 }, true);
    const a = out.results.find(r => r.meta.id === 'a')!;
    expect(a.engHits).toEqual([{ translation: 'primary', positions: [0, 2], matches: [0], near: [2] }]);
  });

  it('leaves an English search with no near term as it was', async () => {
    const plain = await search('', 'man', 'all', 'all', 'or', ['Advanced'], 'lemma', false);
    expect(await run('man', { term: '  ', relation: 'near', window: 5 })).toEqual(plain);
  });
});

// The page marks an English near hit's near word with the box's words
// (ported from legacy/search.test.ts "shows an English near hit whole").
describe('marking English near on the page', () => {
  it('marks the box\'s word and the near word, however far apart', async () => {
    const { markEnglishHtml } = await import('../lib/english-hit');
    const far = 'man ' + 'quietly '.repeat(40) + 'child';
    const html = markEnglishHtml(far, [['man']], false, false, [['child']]);
    expect([...html.matchAll(/<mark>([^<]*)<\/mark>/g)].map(m => m[1])).toEqual(['man', 'child']);
    // With no near word, only the box's.
    expect([...markEnglishHtml(far, [['man']], false).matchAll(/<mark>([^<]*)<\/mark>/g)].map(m => m[1])).toEqual(['man']);
  });
});
