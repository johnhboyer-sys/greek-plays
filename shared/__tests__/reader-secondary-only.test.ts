import { render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Reader from '../components/Reader.svelte';
import type { BookData } from '../lib/data';
import type { Work } from '../lib/works';

// Bug (UI pass 2 build, 2026-10-20): editions on, choosing Way's Medea dropped
// the reader to the Greek view. Way's own Greek (ed/way-loeb) carries Way in
// the secondary slot (`ross`) with `english` null, and `hasEnglish` looked only
// at `english`, so a book whose English sits in another slot counted as having
// none.
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const fixtures: Record<string, Work> = {
    SECONLY: {
      id: 'SECONLY', title: 'Fixture Secondary-Only Work', abbr: 'SECONLY',
      author: 'Test',
      language: 'grc' as const,
      workType: 'continuous' as const,
      books: 1,
      bookLabels: ['1'],
      greekEdition: 'Test edition',
      greekSource: { short: 'Test', full: 'Test edition, full citation.' },
      citation: { scheme: 'book-section' as const },
      blurb: 'Fixture work whose book carries English only in the secondary slot.',
      translations: [
        { id: 'prim', name: 'Primary Translator (Test, 1900)', short: 'Primary', slot: 'english' as const },
        { id: 'sec', name: 'Secondary Translator (Test, 1910)', short: 'Secondary', slot: 'secondary' as const },
      ],
    },
  };
  return {
    ...actual,
    getWork: (id: string) => fixtures[id] ?? actual.getWork(id),
    workPath: (id: string, book = 1) =>
      fixtures[id] ? `/test-author/${id}/book/${book}` : actual.workPath(id, book),
  };
});

const book: BookData = {
  book: 1,
  segments: [
    {
      id: 'seg-1',
      column: '1',
      greek: [
        { n: 1, text: 'λόγος ἀρετή', tokens: [{ t: 'λόγος', o: 0, k: 'logos' }, { t: 'ἀρετή', o: 6, k: 'areth' }] },
      ],
      english: null,
      ross: [{ chapter: '1', text: 'Virtue is discussed here.', cont: false }],
    },
  ],
};

async function flush(ms = 20) {
  await new Promise((r) => setTimeout(r, ms));
}

afterEach(() => {
  window.history.replaceState(null, '', '/');
});

describe('Reader.svelte with English only in the secondary slot', () => {
  it('keeps the Both view and offers all three view buttons', async () => {
    render(Reader, {
      props: { work: 'SECONLY', bookNum: 1, bookData: book, initialTranslation: 'sec', initialView: 'both' },
    });
    await flush();

    const toggle = document.querySelector('.view-toggle') as HTMLElement;
    const buttons = Array.from(toggle.querySelectorAll('button')).map((b) => b.textContent?.trim());
    expect(buttons).toEqual(['Greek', 'Both', 'English']);
    expect(toggle.querySelector('button.active')?.textContent?.trim()).toBe('Both');
    expect(document.querySelector('.rc-no-english')).toBeFalsy();
  });
});
