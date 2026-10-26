import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { searchCombo, COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX, type ComboOptions } from '../lib/search-advanced';

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
  alpha: [[0, 2]],
  beta: [[0, 4]],
  delta: [[0, 3]],
  epsilon: [[0, 8]],
  zeta: [[0, 12]],
  eta: [[0, 19]],
  theta: [[1, 1]],
  iota: [[0, 10]],
  kappa: [[0, 5], [0, 12]],
  lambda: [[0, 18]],
  mu: [[1, 9]],    // global 29, last token of 1001a
  nu: [[2, 0]],    // global 30, first token of 1001b
  feu: [[0, 14], [0, 15], [0, 16]],   // φεῦ φεῦ φεῦ: two overlapping runs of φεῦ φεῦ
};

function json(data: unknown) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) } as Response);
}

const opts = (over: Partial<ComboOptions> = {}): ComboOptions => ({
  window: COMBO_WINDOW_DEFAULT, unit: 'words', ordered: false, ...over,
});
const slot = (...terms: string[]) => ({ kind: 'form' as const, terms });

describe('searchCombo', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/offsets.json')) return json(offsets);
      if (path.endsWith('/form.json')) return json(form);
      if (path.endsWith('/lemma.json')) return json(form);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('reports each hit with its own run and the partner that answered it, across passages', async () => {
    const out = await searchCombo([slot('mu'), { ...slot('nu'), relation: 'after' as const }], opts({ window: 1 }), ['N1']);
    const first = out.results.find(r => r.meta.id === '2:1001a');
    expect(first?.nearHits).toEqual([{ pos: 9, span: 1, partners: [{ segId: '2:1001b', pos: 0, before: false }] }]);
    // The partner's passage has no hit of its own to show.
    expect(out.results.find(r => r.meta.id === '2:1001b')?.nearHits).toEqual([]);
  });

  it('keeps overlapping runs of a phrase apart: φεῦ φεῦ φεῦ holds two hits of φεῦ φεῦ', async () => {
    const out = await searchCombo([{ kind: 'phrase' as const, terms: ['feu', 'feu'] }, slot('zeta')], opts({ window: 5 }), ['N2']);
    const hits = out.results.find(r => r.meta.id === '1:1000a')?.nearHits ?? [];
    expect(hits.map(h => [h.pos, h.span])).toEqual([[14, 2], [15, 2]]);
    expect(hits.every(h => h.partners.some(p => p.pos === 12 && p.before))).toBe(true);
  });

  it('needs at least two usable slots', async () => {
    await expect(searchCombo([slot('alpha')], opts(), ['C1'])).resolves.toEqual({ results: [], failed: [] });
    await expect(searchCombo([slot('alpha'), slot()], opts(), ['C2'])).resolves.toEqual({ results: [], failed: [] });
    await expect(searchCombo([slot('alpha'), slot('beta')], opts(), [])).resolves.toEqual({ results: [], failed: [] });
  });

  it('finds two terms inside the window and marks both tokens', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ window: 5 }), ['C3']);
    expect(results).toHaveLength(1);
    expect(results[0].meta.id).toBe('1:1000a');
    expect(positions(results[0])).toEqual([2, 4]);
  });

  it('respects the window size', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ window: 1 }), ['C4']);
    expect(results).toHaveLength(0);
  });

  it('is unordered by default and order-locked on request', async () => {
    const un = await searchCombo([slot('beta'), slot('alpha')], opts({ window: 5 }), ['C5']);
    expect(un.results).toHaveLength(1);
    const ord = await searchCombo([slot('beta'), slot('alpha')], opts({ window: 5, ordered: true }), ['C6']);
    expect(ord.results).toHaveLength(0);
  });

  it('never spans a book edge, however wide the window', async () => {
    const { results } = await searchCombo([slot('eta'), slot('theta')], opts({ window: COMBO_WINDOW_MAX }), ['C7']);
    expect(results).toHaveLength(0);
  });



  it('measures by line when the unit is a line', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ unit: 'line', window: 0 }), ['C10']);
    expect(positions(results[0])).toEqual([2, 4]);
    const none = await searchCombo([slot('alpha'), slot('epsilon')], opts({ unit: 'line', window: 0 }), ['C11']);
    expect(none.results).toHaveLength(0);
  });



  it('accepts a wildcard in a slot, including inside a phrase run', async () => {
    const form = await searchCombo([slot('alph*'), slot('bet?')], opts({ window: 5 }), ['CW1']);
    expect(positions(form.results[0])).toEqual([2, 4]);
    const phrase = await searchCombo(
      [{ kind: 'phrase', terms: ['delt*', 'beta'] }, slot('alpha')],
      opts({ window: 5 }), ['CW2'],
    );
    expect(positions(phrase.results[0])).toEqual([2, 3, 4]);
  });

  it('finds a window that needs a later occurrence than the first feasible one', async () => {
    const { results } = await searchCombo(
      [slot('iota'), slot('kappa'), slot('lambda')], opts({ window: 8 }), ['CG1'],
    );
    expect(results).toHaveLength(1);
    expect(positions(results[0])).toEqual([10, 12, 18]);
  });

  it('still rejects that group when the window is genuinely too small', async () => {
    const { results } = await searchCombo(
      [slot('iota'), slot('kappa'), slot('lambda')], opts({ window: 7 }), ['CG2'],
    );
    expect(results).toHaveLength(0);
  });

  it('marks both halves of a window that crosses a column boundary', async () => {
    const { results } = await searchCombo([slot('mu'), slot('nu')], opts({ window: 5 }), ['CX1']);
    expect(results.map((r) => [r.meta.id, positions(r)])).toEqual([
      ['2:1001a', [9]],
      ['2:1001b', [0]],
    ]);
  });

  it('will not satisfy two identical slots with one token', async () => {
    const one = await searchCombo([slot('alpha'), slot('alpha')], opts({ window: 5 }), ['CD1']);
    expect(one.results).toHaveLength(0);
    const two = await searchCombo([slot('kappa'), slot('kappa')], opts({ window: 8 }), ['CD2']);
    expect(positions(two.results[0])).toEqual([5, 12]);
  });

  it('never lets one word answer two terms, even different ones', async () => {
    // A word is not near itself: lemma alpha + form alpha needs two alphas.
    const { results } = await searchCombo(
      [{ kind: 'lemma', terms: ['alpha'] }, slot('alpha')], opts({ window: 5 }), ['CD3'],
    );
    expect(results).toHaveLength(0);
    // kappa stands at 5 and 12: two different words, so it is found.
    const two = await searchCombo([{ kind: 'lemma', terms: ['kappa'] }, slot('kappa')], opts({ window: 8 }), ['CD4']);
    expect(positions(two.results[0])).toEqual([5, 12]);
  });

  it('unions the heads a lemma slot carries', async () => {
    const { results } = await searchCombo(
      [{ kind: 'lemma', terms: ['beta', 'zeta'] }, slot('alpha')],
      opts({ window: 5 }), ['C13'],
    );
    expect(positions(results[0])).toEqual([2, 4]);
  });

  it('caps the window rather than trusting the caller', async () => {
    const { results } = await searchCombo([slot('eta'), slot('theta')], opts({ window: 9999 }), ['C14']);
    expect(results).toHaveLength(0);
  });

  it('measures each term from the first word on its own', async () => {
    // alpha 2, beta 4, epsilon 8. From alpha, epsilon is 6 words on: W=6 is needed.
    const fromAlpha = (w: number) => searchCombo([slot('alpha'), slot('beta'), slot('epsilon')], opts({ window: w }), [`CO-a${w}`]);
    expect((await fromAlpha(5)).results).toHaveLength(0);
    expect((await fromAlpha(6)).results).toHaveLength(1);
    // From beta, alpha is 2 before and epsilon 4 after: W=4 is enough, though
    // the three span 7 words (aristotle-reader fitted them all into W).
    const fromBeta = (w: number) => searchCombo([slot('beta'), slot('alpha'), slot('epsilon')], opts({ window: w }), [`CO-b${w}`]);
    expect((await fromBeta(3)).results).toHaveLength(0);
    expect((await fromBeta(4)).results).toHaveLength(1);
    // The order of the further terms does not matter.
    expect((await searchCombo([slot('beta'), slot('epsilon'), slot('alpha')], opts({ window: 4 }), ['CO-c4'])).results).toHaveLength(1);
  });

  it('measures a phrase before the first word from its last word', async () => {
    // delta beta covers 3-4; epsilon at 8 is 4 words after the phrase's end.
    const { results } = await searchCombo(
      [slot('epsilon'), { kind: 'phrase', terms: ['delta', 'beta'], relation: 'before' }],
      opts({ window: 4 }), ['CR8'],
    );
    expect(positions(results[0])).toEqual([3, 4, 8]);
  });

  it('keeps a phrase inside the unit it is measured in', async () => {
    const { results } = await searchCombo(
      [{ kind: 'phrase', terms: ['delta', 'beta'] }, slot('alpha')],
      opts({ unit: 'line', window: 0 }), ['CO7'],
    );
    expect(positions(results[0])).toEqual([2, 3, 4]);
  });

  it('reports ambiguity per slot, not per window', async () => {
    const { results } = await searchCombo([slot('alpha'), slot('beta')], opts({ window: 5 }), ['CO8']);
    expect(results[0].grammar).toEqual([
      { values: {}, certain: true },
    ]);
  });

  describe('slot relation', () => {
    it('near accepts a hit on either side', async () => {
      const { results } = await searchCombo(
        [slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'near' }],
        opts({ window: 5 }), ['CR1'],
      );
      expect(results).toHaveLength(1);
    });

    it('before requires the slot to end at or before the first slot begins', async () => {
      const ok = await searchCombo(
        [slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'before' }],
        opts({ window: 5 }), ['CR2'],
      );
      expect(ok.results).toHaveLength(1);
      const no = await searchCombo(
        [slot('beta'), { kind: 'form', terms: ['epsilon'], relation: 'before' }],
        opts({ window: 5 }), ['CR3'],
      );
      expect(no.results).toHaveLength(0);
    });

    it('after requires the slot to begin at or after the first slot ends', async () => {
      const ok = await searchCombo(
        [slot('beta'), { kind: 'form', terms: ['epsilon'], relation: 'after' }],
        opts({ window: 5 }), ['CR4'],
      );
      expect(ok.results).toHaveLength(1);
      const no = await searchCombo(
        [slot('beta'), { kind: 'form', terms: ['alpha'], relation: 'after' }],
        opts({ window: 5 }), ['CR5'],
      );
      expect(no.results).toHaveLength(0);
    });

    it('places each slot against the first, not against its predecessor', async () => {
      const { results } = await searchCombo(
        [
          slot('delta'),
          { kind: 'form', terms: ['alpha'], relation: 'before' },
          { kind: 'form', terms: ['beta'], relation: 'after' },
        ],
        opts({ window: 5 }), ['CR6'],
      );
      expect(positions(results[0])).toEqual([2, 3, 4]);
    });

    it('measures a preceding phrase by its end, not its start', async () => {
      const { results } = await searchCombo(
        [slot('epsilon'), { kind: 'phrase', terms: ['delta', 'beta'], relation: 'before' }],
        opts({ window: 5 }), ['CR7'],
      );
      expect(positions(results[0])).toEqual([3, 4, 8]);
    });
  });

  it('treats a phrase slot as a run and reports every token in it', async () => {
    const { results } = await searchCombo(
      [{ kind: 'phrase', terms: ['delta', 'beta'] }, slot('alpha')],
      opts({ window: 5 }), ['C15'],
    );
    expect(positions(results[0])).toEqual([2, 3, 4]);
  });
});

describe('slot identity', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/offsets.json')) return json(offsets);
      if (path.endsWith('/form.json')) return json(form);
      if (path.endsWith('/lemma.json')) return json(form);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('reads two lemma slots with the same heads as the same slot, whatever the tick order', async () => {
    const { results } = await searchCombo(
      [{ kind: 'lemma', terms: ['alpha', 'beta'] }, { kind: 'lemma', terms: ['beta', 'alpha'] }],
      opts({ window: 5 }), ['CID1'],
    );
    expect(positions(results[0])).toEqual([2, 4]);
    const none = await searchCombo(
      [{ kind: 'lemma', terms: ['alpha', 'eta'] }, { kind: 'lemma', terms: ['eta', 'alpha'] }],
      opts({ window: 5 }), ['CID2'],
    );
    expect(none.results).toHaveLength(0);
  });

  it('keeps a phrase slot ordered — "delta beta" and "beta delta" are two questions', async () => {
    const { results } = await searchCombo(
      [{ kind: 'phrase', terms: ['delta', 'beta'] }, { kind: 'phrase', terms: ['beta', 'delta'] }],
      opts({ window: 5 }), ['CID3'],
    );
    expect(results).toHaveLength(0);
  });
});

function positions(r: { grkPositions: number[]; nearPositions?: number[] }): number[] { return [...new Set([...r.grkPositions, ...r.nearPositions ?? []])].sort((a, b) => a - b); }

describe('comboWindows backtracking', () => {
  it('finds a match a greedy first pick would block', async () => {
    const { comboWindows } = await import('../lib/search-advanced');
    // Term 2 can use 1 or 2, term 3 only 1: taking 1 for term 2 must be undone.
    const off = { token_count: 10, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 10]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
    const hit = (start: number) => ({ start, span: 1, certain: true });
    const windows = comboWindows([[hit(0)], [hit(1), hit(2)], [hit(1)]], { window: 3, unit: 'words', ordered: false }, off);
    expect(windows.map(w => w.hits.map(h => h.start))).toEqual([[0, 2, 1]]);
  });
});

describe('which word a grammatical term marks', () => {
  it('prefers a word whose every reading fits over a nearer ambiguous one', async () => {
    const { comboWindows } = await import('../lib/search-advanced');
    const off = { token_count: 10, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 10]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
    const hit = (start: number, certain = true) => ({ start, span: 1, certain });
    // Anchor 5; an ambiguous vocative at 4 (ἐμέ), a sure one at 7 (παῖ).
    const windows = comboWindows([[hit(5)], [hit(4, false), hit(7)]], { window: 3, unit: 'words', ordered: false }, off);
    expect(windows.map(w => w.hits.map(h => h.start))).toEqual([[5, 7]]);
    // Only the ambiguous one in reach: the line still matches.
    const only = comboWindows([[hit(5)], [hit(4, false)]], { window: 3, unit: 'words', ordered: false }, off);
    expect(only).toHaveLength(1);
  });
});

describe('lines away', () => {
  it('counts lines either side of the first word, 0 being its own line', async () => {
    const { comboWindows } = await import('../lib/search-advanced');
    // Five lines of two tokens: line k holds tokens 2k and 2k+1.
    const off = { token_count: 10, seg_base_offset: [0], segments: [{ book: 1, column: '1', line_runs: [[1, 2], [2, 2], [3, 2], [4, 2], [5, 2]] }], book_bounds: [{ book: 1, start: 0 }] } as never;
    const hit = (start: number) => ({ start, span: 1, certain: true });
    const found = (n: number, partner: number) =>
      comboWindows([[hit(4)], [hit(partner)]], { window: n, unit: 'line', ordered: false }, off).length;
    expect(found(0, 5)).toBe(1);   // same line
    expect(found(0, 6)).toBe(0);   // next line
    expect(found(1, 6)).toBe(1);
    expect(found(1, 1)).toBe(0);   // two lines back
    expect(found(2, 1)).toBe(1);
  });
});
