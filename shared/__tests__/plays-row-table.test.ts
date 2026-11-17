// The row table (lib/row-table) against the rows the plays' page draws: each
// case runs a search through Search.svelte with the table in force; the page
// compares every book it reads with the table's count of it (bookRows) and
// says so on the console where they differ, and the count is also asked for
// directly. The books are a play's: speeches as segments, printed refs on
// running line numbers, English cut by ticks (lineTicks), a line two speakers
// share (two ticks at one line), a line printed out of order, two segments
// that print one column (Seven's 803/810), and a Greek edition's own book.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fireEvent, render, within } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Search from '../components/Search.svelte';
import type { BookData, GreekLine, Segment } from '../lib/data';
import { chapterPlaces } from '../lib/chapter-pages';
import { countRows, encodeRowBook, type RowTable } from '../lib/row-table';
import { englishQueryUnits, type SearchResult } from '../lib/search';
import { WORKS, getWork, searchableTranslations, workPath } from '../lib/works';

const { books, state } = vi.hoisted(() => {
  const line = (n: number, ref: string, text: string): GreekLine => ({
    n, ref, text, tokens: [...text.matchAll(/\S+/g)].map(m => ({ t: m[0], o: m.index!, k: m[0] })),
  });
  const seg = (id: string, column: string, greek: GreekLine[], english: string, ticks: [number, number][]): Segment => ({
    id, column, greek, english: { text: english, notes: [], markers: [], bekker: ticks.map(([n, offset]) => ({ n, offset, real: true })) },
  });
  // Printed refs from 101; the running numbers from 1.
  const speeches: BookData = {
    book: 1,
    segments: [
      seg('1:101', '101', [line(1, '101', 'α β γ'), line(2, '102', 'δ ε ζ'), line(3, '103', 'η θ ι'), line(4, '104', 'κ λ μ')],
        'Justice first. Then more words here. Justice again now.', [[101, 0], [103, 37]]),
      // 105 is shared by two speakers: the translation ticks it twice.
      seg('1:105', '105', [line(5, '105', 'ν ξ ο π'), line(6, '106', 'ρ σ τ')],
        'Hush, justice! Speak justice. And the last line.', [[105, 0], [105, 15], [106, 30]]),
      // 110 printed before 108 and 109.
      seg('1:107', '107', [line(7, '107', 'υ φ χ'), line(8, '110', 'ψ ω α'), line(9, '108', 'β γ δ'), line(10, '109', 'ε ζ η')],
        'Moved justice line. A line of justice. Justice last.', [[107, 0], [108, 20], [109, 39]]),
      // Two segments print one column.
      seg('1:111', '111', [line(11, '111', 'θ ι κ')], 'Are they lying out there?', [[111, 0]]),
      seg('1:111.2', '111', [line(12, '111', 'λ μ ν')], 'Struck down in the dust of justice.', [[111, 0]]),
    ],
  };
  // The edition prints the same speeches with another line in the first.
  const edition: BookData = {
    book: 1,
    segments: [
      seg('1:101', '101', [line(1, '101', 'α β'), line(2, '101a', 'γ δ ε'), line(3, '102', 'ζ η'), line(4, '103', 'θ ι κ λ')], '', []),
      seg('1:104', '104', [line(5, '104', 'μ ν ξ'), line(6, '105', 'ο π ρ')], '', []),
    ],
  };
  // Forty-five one-line speeches, for paging.
  const long: BookData = {
    book: 1,
    segments: Array.from({ length: 45 }, (_, i) => seg(`1:${201 + i}`, String(201 + i), [line(i + 1, String(201 + i), 'α β')], 'Justice here.', [[201 + i, 0]])),
  };
  return {
    books: { speeches, edition, long },
    state: {
      book: {} as Record<string, BookData>,
      table: {} as Record<string, RowTable>,
      fail: new Set<string>(),
    },
  };
});

vi.mock('../lib/search', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/search')>();
  return {
    ...actual,
    search: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchCombo: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchPhraseVariants: vi.fn(),
    speakerRoster: vi.fn(async () => []),
    loadOffsets: vi.fn(async () => { throw new Error('none'); }),
    loadEngChapters: vi.fn(async () => { throw new Error('none'); }),
  };
});

const keyOf = (work: string, ed?: string) => (ed && ed !== 'tlg' ? `${work}:${ed}` : work);
vi.mock('../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/data')>();
  return {
    ...actual,
    fetchBook: vi.fn(async (work: string, _n: number, ed?: string) => {
      if (state.fail.has(work)) throw new Error(`${work}: 503`);
      return state.book[keyOf(work, ed)];
    }),
    // Every segment a speech of its own, as chapters.json lists them.
    fetchChapters: vi.fn(async (work: string) => ({
      '1': state.book[work].segments.map(s => ({ column: s.column, chapter: s.id, line: String(s.greek[0].n) })),
    })),
    loadRowTable: vi.fn(async (work: string, ed?: string) => {
      const t = state.table[keyOf(work, ed)];
      if (!t) throw new Error('no table');
      return t;
    }),
  };
});

const translations = () => searchableTranslations(getWork('agamemnon')!);
const tableOf = (book: BookData): RowTable => ({ v: 1, t: translations().map(t => t.id), books: { '1': encodeRowBook(book, translations()) } });
const tables = (): Record<string, RowTable> => Object.fromEntries(Object.entries(state.book).map(([k, b]) => [k, tableOf(b)]));
let warn: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => ({ ok: false, status: 404, json: async () => ({}) }) as Response);
  state.fail.clear();
  state.book = { agamemnon: books.speeches, 'libation-bearers': books.speeches, 'agamemnon:paley': books.edition };
  state.table = tables();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, '', '/');
});

const ref = translations().find(t => t.slot === 'english')!.id;
const at = (id: string, r: Partial<SearchResult>, work = 'agamemnon'): SearchResult => ({
  work, meta: { id, book: 1, column: id.slice(2).replace(/\.\d+$/, '') },
  grkMatch: false, engMatch: false, grkPositions: [], ...r,
});
const eng = (positions: number[]) => [{ translation: ref, positions }];
const text = (el: Element | null) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();
const mismatches = () => warn.mock.calls.filter((c: unknown[]) => /the row table counts/.test(String(c[0])));

// The speech at a column and line, as the page's chapterLookup finds it.
const lookupOf = (book: BookData) => (column: string, line: number) => {
  const ci = book.segments.findIndex(s => s.column === column);
  let found = book.segments[0];
  for (const s of book.segments) {
    const si = book.segments.findIndex(x => x.column === s.column);
    if (si < ci || (si === ci && s.greek[0].n <= line)) found = s;
  }
  return { chapter: found.id };
};

// Runs the search with the tables in force; the rows drawn, once the page has
// read its book.
async function rows(url: string, results: SearchResult[]) {
  const { search } = await import('../lib/search');
  const { fetchBook, loadRowTable } = await import('../lib/data');
  vi.mocked(search).mockResolvedValueOnce({ results, failedWorks: [] });
  window.history.replaceState(null, '', url);
  const { container } = render(Search);
  await vi.waitFor(() => expect(fetchBook).toHaveBeenCalled());
  await vi.waitFor(() => expect(container.querySelectorAll('li.instance').length).toBeGreaterThan(0));
  await vi.waitFor(() => expect(text(container.querySelector('.result-count'))).not.toMatch(/of …/));
  // The table was asked for and answered: a case where it was not would pass
  // without comparing anything.
  expect(loadRowTable).toHaveBeenCalled();
  return container.querySelectorAll('li.instance').length;
}

const greekWord = 'g=' + encodeURIComponent('α');
const cases: [string, string, SearchResult[], string?][] = [
  ['Greek words on lines next to each other and apart', greekWord, [at('1:101', { grkMatch: true, grkPositions: [0, 1, 3, 9] })]],
  ['Greek and English in one tick unit, and English alone', `${greekWord}&e=justice`, [
    at('1:101', { grkMatch: true, engMatch: true, grkPositions: [1], engHits: eng([0, 6]) })]],
  ['a line two speakers share', `${greekWord}&e=justice`, [
    at('1:105', { grkMatch: true, engMatch: true, grkPositions: [0, 3, 5], engHits: eng([1, 3]) })]],
  ['a line printed out of order', `${greekWord}&e=justice`, [
    at('1:107', { grkMatch: true, engMatch: true, grkPositions: [0, 3, 5, 8, 10], engHits: eng([1, 6, 7]) })]],
  ['two segments that print one column', `${greekWord}&e=justice`, [
    at('1:111', { grkMatch: true, grkPositions: [0, 2] }),
    at('1:111.2', { grkMatch: true, engMatch: true, grkPositions: [1], engHits: eng([6]) })]],
  ['a run of several words, one into the next speech', `${greekWord}&gm=phrase`, [
    at('1:101', { grkMatch: true, grkPositions: [10, 11, 12], windows: [[10, 11], [11, 12]] }),
    at('1:105', { grkMatch: true, grkPositions: [2, 3, 6], windows: [[2, 3], [6]] })]],
  ['English alone in every speech', 'e=justice', [
    at('1:101', { engMatch: true, engHits: eng([0, 6]) }),
    at('1:105', { engMatch: true, engHits: eng([1, 3]) }),
    at('1:107', { engMatch: true, engHits: eng([1, 6, 7]) }),
    at('1:111.2', { engMatch: true, engHits: eng([6]) })]],
  ['a Greek edition\'s own book', `${greekWord}&ed=paley`, [
    at('1:101', { grkMatch: true, grkPositions: [0, 1, 5, 9], ed: 'paley' }),
    { ...at('1:104', { grkMatch: true, grkPositions: [0, 4] }), ed: 'paley' }], 'paley'],
];

describe('the plays\' row table counts the rows the page draws', () => {
  for (const [name, query, results, ed] of cases) {
    for (const ctx of ['1', '3', 's']) {
      it(`${name}, context ${ctx}`, async () => {
        const drawn = await rows(`/search?${query}&ctx=${ctx}`, results);
        expect(drawn).toBeGreaterThan(0);
        expect(mismatches()).toEqual([]);
        if (ed) {
          const { loadRowTable } = await import('../lib/data');
          expect(vi.mocked(loadRowTable).mock.calls.map(c => c[1])).toContain(ed);
        }
        // And the count itself, as the page asks for it (no offsets: each
        // hit in its outline speech).
        const q = new URLSearchParams(query).get('e') ?? '';
        const book = ed ? books.edition : books.speeches;
        expect(countRows(results, tables()[ed ? `agamemnon:${ed}` : 'agamemnon'].books['1'], {
          context: ctx as '1' | '3' | 's', places: chapterPlaces(new Map()), translations: translations(),
          chapterSection: false, playLine: true, lookup: lookupOf(book), engUnits: englishQueryUnits(q), engPhrase: false,
        })).toBe(drawn);
      });
    }
  }

  // Agamemnon: a hit in each of 45 one-line speeches (a row each), and
  // Libation Bearers one more. At 20 a page, page 1 is Agamemnon's.
  const long = () => { state.book = { agamemnon: books.long, 'libation-bearers': books.long }; state.table = tables(); };
  const two = [...books.long.segments.map(s => at(s.id, { grkMatch: true, grkPositions: [0] })),
    at('1:201', { grkMatch: true, grkPositions: [0] }, 'libation-bearers')];
  const url = `/search?${greekWord}&ctx=1&ps=20`;
  const playsRead = async () => {
    const { fetchBook } = await import('../lib/data');
    return [...new Set(vi.mocked(fetchBook).mock.calls.map(c => c[0]))].sort();
  };
  const pager = () => text(document.querySelector('.pager-status'));

  it('reads only the plays its page draws, the page count from the table', async () => {
    long();
    await rows(url, two);
    await vi.waitFor(() => expect(pager()).toBe('Page 1 of 3'));
    expect(document.querySelectorAll('li.instance')).toHaveLength(20);
    expect(await playsRead()).toEqual(['agamemnon']);
    expect(mismatches()).toEqual([]);
  });

  it('reads every play with no table, as before', async () => {
    long();
    state.table = {};
    const { search } = await import('../lib/search');
    vi.mocked(search).mockResolvedValueOnce({ results: two, failedWorks: [] });
    window.history.replaceState(null, '', url);
    const { container } = render(Search);
    await vi.waitFor(() => expect(text(container.querySelector('.pager-status'))).toBe('Page 1 of 3'));
    expect(container.querySelectorAll('li.instance')).toHaveLength(20);
    expect(await playsRead()).toEqual(['agamemnon', 'libation-bearers']);
  });

  it('keeps the next play on its own page where a play the table counted fails to load', async () => {
    long();
    state.fail.add('agamemnon');
    const { search } = await import('../lib/search');
    const { fetchBook } = await import('../lib/data');
    vi.mocked(search).mockResolvedValueOnce({ results: two, failedWorks: [] });
    window.history.replaceState(null, '', url);
    const { container } = render(Search);
    await vi.waitFor(() => expect(text(container.querySelector('.pager-status'))).toBe('Page 1 of 3'));
    await vi.waitFor(() => expect(vi.mocked(fetchBook).mock.calls.some(c => c[0] === 'agamemnon')).toBe(true));
    await new Promise(r => setTimeout(r, 50));
    // Page 1 is Agamemnon's rows, which did not load: Libation Bearers' row is not drawn there.
    expect(container.querySelectorAll('li.instance')).toHaveLength(0);
    expect(vi.mocked(fetchBook).mock.calls.some(c => c[0] === 'libation-bearers')).toBe(false);
    // Page 3 is Libation Bearers', where the table put it.
    const next = () => fireEvent.click(within(container.querySelector('.pager')! as HTMLElement).getByRole('button', { name: /Next/ }));
    await next();
    await vi.waitFor(() => expect(text(container.querySelector('.pager-status'))).toBe('Page 2 of 3'));
    await next();
    await vi.waitFor(() => expect(text(container.querySelector('.pager-status'))).toBe('Page 3 of 3'));
    await vi.waitFor(() => expect(container.querySelectorAll('li.instance').length).toBeGreaterThan(0));
  });

  it('reads every play, and draws the same rows, where the table disagrees with a play', async () => {
    // The first speech's English in a unit of its own: the table puts no
    // English hit with its Greek, so counts a row more than the play draws.
    long();
    const wrong = tables();
    const s0 = wrong.agamemnon.books['1'].s[0];
    s0.e = { ...s0.e, [ref]: [999, 1000, 999] };
    wrong.agamemnon.books['1'].u[999] = 0;
    state.table = wrong;
    const mixed = [{ ...two[0], engMatch: true, engHits: eng([0]) }, ...two.slice(1)];
    await rows(`/search?${greekWord}&e=justice&op=or&ctx=1&ps=20`, mixed);
    await vi.waitFor(() => expect(mismatches()).toHaveLength(1));
    await vi.waitFor(async () => expect(await playsRead()).toEqual(['agamemnon', 'libation-bearers']));
    await vi.waitFor(() => expect(pager()).toBe('Page 1 of 3'));
    expect(document.querySelectorAll('li.instance')).toHaveLength(20);
  });
});

// The built corpus, where it is here: an English search across the plays,
// 20 a page, with every play's table from build/scripts/build-row-tables.mjs.
// Page 1 reads only the plays it draws, and no play read disagrees.
const dist = resolve(process.cwd(), '../build/dist');
const built = existsSync(`${dist}/agamemnon/rows.json`) && existsSync(`${dist}/agamemnon/search/english.json`);
describe.skipIf(!built)('the row table on the built plays', () => {
  it('English "justice": page 1 reads its own plays, each as the table counts it', async () => {
    const { search, loadOffsets, loadEngChapters } = await import('../lib/search');
    const { fetchBook, fetchChapters, loadRowTable } = await import('../lib/data');
    const real = await vi.importActual<typeof import('../lib/search')>('../lib/search');
    const realData = await vi.importActual<typeof import('../lib/data')>('../lib/data');
    vi.mocked(search).mockImplementation(real.search);
    vi.mocked(loadOffsets).mockImplementation(real.loadOffsets);
    vi.mocked(loadEngChapters).mockImplementation(real.loadEngChapters);
    vi.mocked(fetchBook).mockImplementation(realData.fetchBook);
    vi.mocked(fetchChapters).mockImplementation(realData.fetchChapters);
    vi.mocked(loadRowTable).mockImplementation(realData.loadRowTable);
    const read = new Set<string>();
    vi.mocked(globalThis.fetch).mockImplementation(async input => {
      const path = String(input).replace(/^.*?\/data\//, '');
      if (/\/book-\d+\.json$/.test(path)) read.add(path.split('/')[0]);
      const file = `${dist}/${path}`;
      return existsSync(file) && !file.endsWith('/')
        ? { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, 'utf8')) } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    window.history.replaceState(null, '', '/search?e=justice&ps=20');
    const { container } = render(Search);
    await vi.waitFor(() => expect(container.querySelectorAll('li.instance').length).toBe(20), { timeout: 30000 });
    await vi.waitFor(() => expect(text(container.querySelector('.pager-status'))).toMatch(/^Page 1 of \d+$/), { timeout: 30000 });
    const paths = [...container.querySelectorAll('li.instance a[href]')].map(a => new URL((a as HTMLAnchorElement).href, 'https://x.invalid').pathname);
    const drawn = new Set(WORKS.filter(w => paths.some(p => p === workPath(w.id) || p.startsWith(`${workPath(w.id)}/`))).map(w => w.id));
    await new Promise(r => setTimeout(r, 200));
    expect(mismatches()).toEqual([]);
    expect(read.size).toBeGreaterThan(0);
    expect([...read].sort()).toEqual([...drawn].sort());
  }, 60000);
});
