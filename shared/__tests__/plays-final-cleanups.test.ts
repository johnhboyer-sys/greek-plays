// Last cleanups before the search port's PR, on the plays' own registry: the
// 100 page's Greek summary reads as words, and a running-text search says it
// ignores a chosen Greek edition.
import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Search from '../components/Search.svelte';
import type { BookData, GreekLine, Segment } from '../lib/data';
import type { SearchResult } from '../lib/search';
import { getWork } from '../lib/works';

const SEVEN = 'seven-against-thebes';
const { fixture } = vi.hoisted(() => {
  vi.stubEnv('PUBLIC_EDITIONS', '1');   // read when Search.svelte loads
  const line = (n: number, text: string): GreekLine => ({ n, ref: String(n), text, tokens: text.split(' ').map((t, i) => ({ t, o: i * 2, k: t })) });
  const seg = (id: string, column: string, english: string, ...greek: GreekLine[]): Segment => ({
    id, column, greek, english: { text: english, notes: [], markers: [] },
  });
  const fixture: BookData = {
    book: 1,
    segments: [seg('1:84', '84', 'Words.', line(84, 'α β γ'), line(85, 'δ ε ζ'), line(86, 'η θ ι'))],
  };
  return { fixture };
});

const HIT: SearchResult = { work: SEVEN, meta: { id: '1:84', book: 1, column: '84' }, grkMatch: true, engMatch: false, grkPositions: [4] };

vi.mock('../lib/search', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/search')>();
  return {
    ...actual,
    search: vi.fn(async () => ({ results: [HIT], failedWorks: [] })),
    searchCombo: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchPhraseVariants: vi.fn(),
    speakerRoster: vi.fn(async () => []),
    greekHitForms: vi.fn(async () => ({ byResult: new Map(), headwords: new Map(), failedWorks: [] })),
    greekHitGrammar: vi.fn(async () => ({ byResult: new Map(), failedWorks: [] })),
  };
});
vi.mock('../lib/running-text', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/running-text')>();
  return { ...actual, searchRunningText: vi.fn(async () => ({ results: [HIT], failedWorks: [] })) };
});
vi.mock('../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/data')>();
  return {
    ...actual,
    fetchBook: vi.fn(async () => fixture),
    fetchChapters: vi.fn(async () => ({ '1': [{ chapter: '84', column: '84', line: '84' }] })),
    fetchLemmaPickerShard: vi.fn(async () => ({})),
    fetchLemmaGlosses: vi.fn(async () => []),
  };
});

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => ({ ok: false, status: 404, json: async () => ({}) }) as Response);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, '', '/');
});

const text = (el: Element | null | undefined) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

describe('the 100 page summary of a verse hit', () => {
  it('runs the lines together as words, with no line numbers among them', async () => {
    window.history.replaceState(null, '', `/search?g=${encodeURIComponent('ε')}&m=form&ps=100&w=${SEVEN}`);
    const { container } = render(Search);
    const sum = await vi.waitFor(() => {
      const el = container.querySelector('.cmp-sum');
      expect(el).not.toBeNull();
      return el!;
    });
    expect(text(sum)).toBe('… α β γ δ ε ζ η θ ι …');
    expect(sum.querySelector('mark')!.textContent).toBe('ε');
  });
});

describe('a running-text search with a chosen Greek edition', () => {
  it('says it read each play’s main text, naming the plays that hold the edition', async () => {
    const ed = getWork(SEVEN)!.greekEditions!.find(e => e.id !== 'tlg')!.id;
    window.history.replaceState(null, '', `/search?g=${encodeURIComponent('ε')}&m=text&ed=${ed}&w=${SEVEN}`);
    render(Search);
    const note = await screen.findByText(/A search of the running text reads each play’s main Greek text/);
    expect(text(note)).toContain('not in the chosen edition');
    expect(text(note)).toContain(getWork(SEVEN)!.title);
  });

  it('says nothing where no edition is chosen', async () => {
    window.history.replaceState(null, '', `/search?g=${encodeURIComponent('ε')}&m=text&w=${SEVEN}`);
    const { container } = render(Search);
    await vi.waitFor(() => expect(container.querySelector('li.instance')).not.toBeNull());
    expect(screen.queryByText(/not in the chosen edition/)).toBeNull();
  });
});
