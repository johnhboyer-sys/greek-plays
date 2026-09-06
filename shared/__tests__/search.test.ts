import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import Search from '../components/Search.svelte';
import { englishOccurrences, greekFold, latinFold, search } from '../lib/search';

// Latin-language test work ids (unregistered in the real WORKS registry, so
// getWork() would otherwise resolve them to 'grc' and mask the Blocker 2
// asymmetry this file guards against): stubbed to `language: 'lat'` here,
// everything else in '../lib/works' stays real.
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  return {
    ...actual,
    getWork: (id: string) =>
      id.startsWith('TLat') ? { language: 'lat' } : actual.getWork(id),
  };
});

const meta = [
  { id: 's1', book: 1, column: '1094a', head: 'λόγος ἀρετή', tokens: 'logos areth', english_head: 'virtue is a habit of choice' },
  { id: 's2', book: 1, column: '1094b', head: 'ψυχή λόγος', tokens: 'yuxh logos', english_head: 'happiness and virtue together' },
  { id: 's3', book: 2, column: '1100a', head: 'τέχνη', tokens: 'texnh', english_head: 'craft concerns making' },
];

const greekIndex = {
  logos: [[0, 0], [1, 1]],
  areth: [[0, 1]],
  yuxh: [[1, 0]],
  texnh: [[2, 0]],
} satisfies Record<string, [number, number][]>;

const englishIndex = {
  virtue: [0, 1],
  habit: [0],
  choice: [0],
  happiness: [1],
  craft: [2],
  making: [2],
} satisfies Record<string, number[]>;

function json(data: unknown) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) } as Response);
}

describe('greekFold', () => {
  it.each([
    ['λόγος', 'logos'],
    ['lo/gos', 'logos'],
    ['*a)nqrwpos', 'anqrwpos'],
    ["ἀρετή'", "areth'"],
    ['ψυχή κόσμος', 'yuxhkosmos'],
  ])('folds %s', (input, expected) => {
    expect(greekFold(input)).toBe(expected);
  });
});

describe('latinFold', () => {
  // Mirrors pipeline/drama_pipeline/latin.py's fold() test cases exactly
  // (test_latin.py) — the query-side and index-build-side fold functions
  // must agree.
  it.each([
    ['vita', 'uita'],
    ['uita', 'uita'],
    ['coniunx', 'coniunx'],
    ['conjunx', 'coniunx'],
    ['VIRTUS', 'uirtus'],
    ['Virtus!', 'uirtus'],
    ['mālus', 'malus'],   // macron-carrying vowel folds to its base letter
    ['mălus', 'malus'],   // breve-carrying vowel folds to its base letter
    ['cælum', 'caelum'],  // æ ligature expands before folding
    ['fœdus', 'foedus'],  // œ ligature expands before folding
  ])('folds %s to %s', (input, expected) => {
    expect(latinFold(input)).toBe(expected);
  });
});

describe('search', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/lemma.json') || path.endsWith('/form.json')) return json(greekIndex);
      if (path.endsWith('/english.json')) return json(englishIndex);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns no results for empty queries or no works', async () => {
    await expect(search('', ' ', 'all', 'all', 'and', ['TEmpty'])).resolves.toEqual([]);
    await expect(search('logos', '', 'all', 'all', 'and', [])).resolves.toEqual([]);
  });

  it('supports all, any, and phrase modes', async () => {
    expect(await search('logos areth', '', 'all', 'all', 'and', ['TAll'])).toHaveLength(1);
    expect(await search('yuxh areth', '', 'any', 'all', 'and', ['TAny'])).toHaveLength(2);
    expect(await search('logos areth', '', 'phrase', 'all', 'and', ['TPhraseMiss'])).toHaveLength(1);
    expect(await search('areth logos', '', 'phrase', 'all', 'and', ['TPhraseHit'])).toHaveLength(0);
  });

  it('supports wildcards for Greek and English terms', async () => {
    const greek = await search('tex*', '', 'all', 'all', 'and', ['TGreekWildcard']);
    const english = await search('', 'hap*', 'all', 'all', 'and', ['TEngWildcard']);
    expect(greek.map((r) => r.meta.id)).toEqual(['s3']);
    expect(english.map((r) => r.meta.id)).toEqual(['s2']);
  });

  it('combines Greek and English boxes with AND or OR', async () => {
    const andHits = await search('logos', 'happiness', 'all', 'all', 'and', ['TAnd']);
    const orHits = await search('texnh', 'happiness', 'all', 'all', 'or', ['TOr']);
    expect(andHits.map((r) => r.meta.id)).toEqual(['s2']);
    expect(orHits.map((r) => r.meta.id)).toEqual(['s2', 's3']);
  });

  it.each([
    ['whitespace only', '   ', '\t'],
    ['pure punctuation', '!!!', '...'],
    ['regex metacharacters', '.*+?^${}()|[]\\', '.*+?^${}()|[]\\'],
    ['Greek string', 'λόγος τέχνη', 'virtue'],
    ['very long string', `${'logos '.repeat(500)}texnh`, `${'virtue '.repeat(500)}craft`],
  ])('does not throw for adversarial input: %s', async (_label, grk, eng) => {
    await expect(search(grk, eng, 'any', 'any', 'or', [`TAdv-${_label}`])).resolves.toEqual(expect.any(Array));
  });
});

// Blocker: search() previously folded EVERY work's source-language box with
// greekFold, regardless of the work's actual language — a Latin work's
// query for "vita" would never match an index built with the fold("vita",
// "lat") == fold("uita", "lat") equivalence, because the query side used
// Greek's Beta-Code fold table instead. These tests use a work id
// ('TLat...') the top-of-file `vi.mock('../lib/works', ...)` resolves to
// `language: 'lat'`, with a synthetic index built the way stage6_search.py
// would build it for a Latin work (fold(key, 'lat') keys).
describe('search — Latin work language dispatch', () => {
  const latMeta = [
    { id: 'l1', book: 1, column: '1.1', head: 'vita', tokens: 'uita', english_head: 'life is short' },
    { id: 'l2', book: 1, column: '1.2', head: 'coniunx cara', tokens: 'coniunx cara', english_head: 'a dear spouse' },
  ];
  // Index built with the u/v, i/j-unified fold — "vita"/"uita" both fold to
  // "uita"; "coniunx"/"conjunx" both fold to "coniunx" (latin.py's fold()).
  const latIndex = {
    uita: [[0, 0]],
    coniunx: [[1, 0]],
    cara: [[1, 1]],
  } satisfies Record<string, [number, number][]>;

  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(latMeta);
      if (path.endsWith('/lemma.json') || path.endsWith('/form.json')) return json(latIndex);
      if (path.endsWith('/english.json')) return json({});
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('matches "vita" and "uita" as the same query (exact)', async () => {
    const viaV = await search('vita', '', 'all', 'all', 'and', ['TLatExact']);
    const viaU = await search('uita', '', 'all', 'all', 'and', ['TLatExact']);
    expect(viaV.map((r) => r.meta.id)).toEqual(['l1']);
    expect(viaU.map((r) => r.meta.id)).toEqual(['l1']);
  });

  it('matches "coniunx" and "conjunx" as the same query (exact)', async () => {
    const viaI = await search('coniunx', '', 'all', 'all', 'and', ['TLatExact']);
    const viaJ = await search('conjunx', '', 'all', 'all', 'and', ['TLatExact']);
    expect(viaI.map((r) => r.meta.id)).toEqual(['l2']);
    expect(viaJ.map((r) => r.meta.id)).toEqual(['l2']);
  });

  it('supports a u/v-folded wildcard prefix query', async () => {
    // "con*" and "uit*" should prefix-match the folded ("uita"/"coniunx")
    // keys regardless of which u/v i/j spelling the user types.
    const hits = await search('con*', '', 'all', 'all', 'and', ['TLatWildcard']);
    expect(hits.map((r) => r.meta.id)).toEqual(['l2']);
  });

  it('matches a u/v-folded phrase query across the token sequence', async () => {
    // meta.tokens for l2 is the fold sequence "coniunx kara" -- a phrase
    // query spelled with the alternate convention ("conjunx cara") must
    // still hit it.
    const hits = await search('conjunx cara', '', 'phrase', 'all', 'and', ['TLatPhrase']);
    expect(hits.map((r) => r.meta.id)).toEqual(['l2']);
  });

  it('does not cross-match a Greek-work id\'s query against the Latin fold', async () => {
    // A work id NOT recognized as Latin by the mock (falls through to the
    // real registry, unregistered -> defaults to 'grc') must still use
    // greekFold, not latinFold -- "vita" under greekFold folds to a
    // different key than under latinFold (proving the two fold functions
    // are genuinely distinct, not just aliases), so it must not spuriously
    // hit an unrelated Greek-indexed work.
    expect(greekFold('vita')).not.toBe(latinFold('vita'));
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/lemma.json') || path.endsWith('/form.json')) return json(greekIndex);
      if (path.endsWith('/english.json')) return json(englishIndex);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
    const hits = await search('vita', '', 'all', 'all', 'and', ['TGreekUnaffected']);
    expect(hits).toEqual([]);
  });
});

describe('englishOccurrences', () => {
  it('returns one offset per matching token (repeats counted)', () => {
    // #11: "socrates" three times -> three offsets, not one.
    const text = 'Socrates asked; then Socrates replied, and Socrates smiled.';
    expect(englishOccurrences(text, ['socrates'], 'all')).toHaveLength(3);
  });

  it('finds a phrase whose occurrence is past the old 500-char cap', () => {
    // #5: the phrase sits well beyond character 500; token-based matching still finds it.
    const filler = 'word '.repeat(200);           // ~1000 chars
    const text = `${filler}you shall avail yourself of it`;
    const offs = englishOccurrences(text, ['shall', 'avail'], 'phrase');
    expect(offs).toHaveLength(1);
    expect(offs[0]).toBeGreaterThan(500);
  });

  it('matches whole tokens and prefix wildcards, not substrings', () => {
    const text = 'virtue and virtues and virtuous';
    expect(englishOccurrences(text, ['virtue'], 'all')).toHaveLength(1);   // not "virtues"/"virtuous"
    expect(englishOccurrences(text, ['virtu*'], 'all')).toHaveLength(3);   // prefix hits all three
  });
});

describe('search English occurrences (index integration)', () => {
  const longText = `${'filler word '.repeat(60)}the crux is that one shall avail nothing`;
  const engMeta = [
    { id: 's1', book: 1, column: '406a', head: '', tokens: '', english_head: longText },
  ];
  const engIndex = { shall: [0], avail: [0], filler: [0], word: [0], the: [0] };
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(engMeta);
      if (path.endsWith('/english.json')) return json(engIndex);
      if (path.endsWith('/lemma.json') || path.endsWith('/form.json')) return json({});
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it('phrase past char 500 is found (regression for the [:500] truncation)', async () => {
    const idx = longText.toLowerCase().indexOf('shall avail');
    expect(idx).toBeGreaterThan(500);
    const hits = await search('', 'shall avail', 'all', 'phrase', 'and', ['TEng500']);
    expect(hits).toHaveLength(1);
    expect(hits[0].engPositions).toEqual([idx]);
  });

  it('counts repeated English occurrences per segment', async () => {
    const hits = await search('', 'word', 'all', 'all', 'and', ['TEngCount']);
    expect(hits).toHaveLength(1);
    // "word" appears 60 times in the filler.
    expect(hits[0].engPositions).toHaveLength(60);
  });
});

describe('Search.svelte play-line result routing', () => {
  afterEach(() => vi.restoreAllMocks());

  it('loads an empty chapter outline and cites the matching printed line ref', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const path = String(url);
      if (path.endsWith('/agamemnon/search/meta.json')) return json([
        { id: '1:125', book: 1, column: '1', head: 'λόγος', tokens: 'logos', english_head: '' },
      ]);
      if (path.endsWith('/agamemnon/search/lemma.json')) return json({ logos: [[0, 0]] });
      if (path.endsWith('/agamemnon/chapters.json')) return json({});
      if (path.endsWith('/agamemnon/book-01.json')) return json({
        book: 1,
        segments: [{
          id: '1:125', column: '1', english: null,
          greek: [{ n: 125, ref: '147-150', text: 'λόγος', tokens: [{ t: 'λόγος', o: 0, k: 'logos' }] }],
        }],
      });
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });

    const { getByLabelText, getByRole, container } = render(Search);
    await fireEvent.input(getByLabelText('Greek'), { target: { value: 'λόγος' } });
    await fireEvent.click(getByRole('button', { name: 'Search' }));

    await waitFor(() => expect(container.querySelector('.inst-ref')).toBeTruthy());
    const link = container.querySelector('.inst-ref') as HTMLAnchorElement;
    expect(link.textContent).toBe('147-150');
    expect(link.getAttribute('href')).toBe('/aeschylus/agamemnon?hlg=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&loc=147-150');
    expect(container.querySelector('.search-note.warn')).toBeNull();
  });
});

// PUBLIC_DATA_ROOT mirrors data.ts's build-time root override (see
// data.test.ts's matching describe block) — search.ts derives its own
// DEFAULT_ROOT independently, so it needs its own coverage.
describe('PUBLIC_DATA_ROOT build-time root override', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it('prefixes every index fetch with PUBLIC_DATA_ROOT when set', async () => {
    vi.stubEnv('PUBLIC_DATA_ROOT', 'https://data.example.com/v1/');
    vi.resetModules();
    const fresh = await import('../lib/search');
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      urls.push(String(url));
      const path = String(url);
      if (path.endsWith('/meta.json')) return json(meta);
      if (path.endsWith('/lemma.json') || path.endsWith('/form.json')) return json(greekIndex);
      if (path.endsWith('/english.json')) return json(englishIndex);
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) } as Response);
    });
    await fresh.search('logos', '', 'all', 'all', 'and', ['TRoot']);
    expect(urls.length).toBeGreaterThan(0);
    expect(urls.every((u) => u.startsWith('https://data.example.com/v1/TRoot/search/'))).toBe(true);
  });
});
