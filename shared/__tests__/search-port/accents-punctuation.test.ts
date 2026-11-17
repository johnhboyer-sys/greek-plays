import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
// Aristotle's registry, which these tests were written against.
vi.mock('../../lib/works', () => import('./aristotle-works'));
import Search from '../../components/Search.svelte';
import type { BookData } from '../../lib/data';

const { fixtureBook } = vi.hoisted(() => ({
  fixtureBook: {
    book: 1,
    segments: [{
      id: 'seg1',
      column: '70a',
      greek: [{ n: 1, text: 'φίλος.] φιλος', tokens: [{ t: 'φίλος.]', o: 0, k: 'filos' }, { t: 'φιλος', o: 7, k: 'filos' }] }],
      english: { text: 'Word.', notes: [], markers: [], bekker: [{ n: 1, offset: 0, real: true }] },
      chapterStarts: [],
    }],
  } satisfies BookData,
}));

vi.mock('../../lib/search', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/search')>();
  return {
    ...actual,
    search: vi.fn(async () => ({
      results: [{ work: 'EN', meta: { id: 'seg1', book: 1, column: '70a' }, grkMatch: true, engMatch: false, grkPositions: [0, 1] }],
      failedWorks: [],
    })),
    searchCombo: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchPhraseVariants: vi.fn(),
    speakerRoster: vi.fn(async () => []),
  };
});

vi.mock('../../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/data')>();
  return {
    ...actual,
    fetchBook: vi.fn(async () => fixtureBook),
    fetchChapters: vi.fn(async () => ({ '1': [{ column: '70a', chapter: '70', line: '1' }] })),
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


// Accents on keeps a hit whose printed word carries punctuation: Alcestis 1095
// prints "φίλος.]", an exact φίλος (the old page's 102 → the new 101).
describe('Accents observed', () => {
  it('keeps a word printed with its punctuation, and drops one with other accents', async () => {
    window.history.replaceState(null, '', '/search?g=φίλος&acc=1&m=form');
    const { container } = render(Search);
    await vi.waitFor(() => expect(container.querySelector('li.instance')).not.toBeNull());
    // Two positions found; only the first carries the accents typed.
    expect(container.querySelectorAll('li.instance')).toHaveLength(1);
    expect(container.querySelector('li.instance')).toHaveTextContent('φίλος.]');
  });
});
