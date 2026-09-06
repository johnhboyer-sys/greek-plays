import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Reader from '../components/Reader.svelte';
import type { BookData } from '../lib/data';
import type { Work } from '../lib/works';

// Reader-layer acceptance for P1 (docs/p1-probe.md): a play-line segment's
// strophe marker renders as its own element (never part of the clickable
// Greek text), its speaker renders as an ordinary lead-in via the existing
// speakers.ts path (speakerWork generalization of the old `stephanus &&`
// gates), and its DOM id/gutter are keyed by the line's own printed ref —
// mirrors reader-prose-flow.test.ts's fixture-mocking pattern.

vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const fixtures: Record<string, Work> = {
    PLAYLINE: {
      id: 'PLAYLINE', title: 'Fixture Play', abbr: 'Fix.', author: 'Test',
      language: 'grc', workType: 'verse', books: 1, bookLabels: ['1'],
      greekEdition: 'Test edition', greekSource: { short: 'Test', full: 'Test edition, full.' },
      translations: [],
      citation: { scheme: 'play-line', copyAbbr: 'Fix.' },
      blurb: 'Fixture for play-line Reader tests.',
    },
  };
  return {
    ...actual,
    getWork: (id: string) => fixtures[id] ?? actual.getWork(id),
    getWorkBySlug: (author: string, slug: string) =>
      fixtures[slug.toUpperCase()] ?? actual.getWorkBySlug(author, slug),
  };
});

async function flush() {
  await new Promise((r) => setTimeout(r, 0));
}

function book(): BookData {
  return {
    book: 1,
    segments: [
      {
        id: '1:1',
        column: '1',
        greek: [
          { n: 1, text: 'πρῶτος λόγος', tokens: [{ t: 'πρῶτος', o: 0, k: 'prwtos' }], ref: '1' },
        ],
        speakers: [{ line: 1, offset: 0, label: 'ΑΛΦΑ' }],
        english: null,
      },
      {
        id: '1:5',
        column: '5',
        greek: [
          { n: 2, text: 'δεύτερος λόγος', tokens: [{ t: 'δεύτερος', o: 0, k: 'deuteros' }], ref: '5a' },
          { n: 3, text: 'πέμπτος λόγος', tokens: [{ t: 'πέμπτος', o: 0, k: 'pemptos' }], ref: '5b', label: 'στρ. α.' },
          { n: 4, text: 'ἕκτος λόγος', tokens: [], ref: '6' },
          { n: 5, text: 'ἕβδομος λόγος', tokens: [], ref: '7' },
          { n: 6, text: 'δέκατος λόγος', tokens: [], ref: '10' },
          { n: 7, text: 'μέλος', tokens: [], ref: '106-107' },
          { n: 8, text: '', tokens: [], ref: 'post 107', role: 'lacuna' },
        ],
        speakers: [{ line: 2, offset: 0, label: 'Χο.' }],
        english: null,
      },
    ],
  };
}

describe('Reader.svelte play-line rendering (P1)', () => {
  it('renders a strophe marker as its own element, separate from the line text', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const marker = container.querySelector('.strophe-marker');
    expect(marker).toBeTruthy();
    expect(marker!.textContent).toBe('στρ. α.');
    // Never part of the clickable Greek text.
    const line = container.querySelector('.greek-line[id="L5b-3"]');
    expect(line).toBeTruthy();
    expect(line!.textContent).not.toContain('στρ');
  });

  it('renders the speaker as an ordinary lead-in (speakers.ts path)', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const line1 = container.querySelector('.greek-line[id="L1-1"]');
    expect(line1).toBeTruthy();
    expect(line1!.querySelector('.speaker')?.textContent).toBe('ΑΛΦΑ');
  });

  it('builds the DOM id from the line\'s own ref, not the internal segment column', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    // Segment "1:5"'s column is "5", but its one line's own ref is also "5"
    // here — pick a case where they'd diverge: segment id "1:1" carries
    // column "1" and its line's ref is "1" too in this fixture, so assert
    // the id is ref-derived generally by checking the reader never falls
    // back to the generic `L{seg.column}-{n}` (dense n) shape for a work
    // whose printed ref and dense ordinal already coincide is not a
    // discriminating case — assert via the reader's play-line jump helper
    // instead (exported for this purpose is out of scope; the id itself,
    // L{ref}-{n}, is asserted directly).
    expect(container.querySelector('#L1-1')).toBeTruthy();
    expect(container.querySelector('#L5b-3')).toBeTruthy();
  });

  it('keys gutter labels to printed refs and always shows suffixes and ranges', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const nums = Array.from(container.querySelectorAll('.line-num')).map((el) => el.textContent);
    // Line 1 (n=1, ref "1"): always shown. "5a" (n=2, not a multiple of 5,
    // not the first line): shown anyway because it isn't a plain integer.
    expect(nums).toContain('1');
    expect(nums).toContain('5a');
    expect(nums).toContain('5b');
    expect(nums).toContain('10');
    expect(nums).toContain('106-107');
    expect(nums).not.toContain('7');
  });

  it('keeps a lacuna out of the citation and scroll-spy target set', async () => {
    const { container } = render(Reader, { props: { work: 'PLAYLINE', bookNum: 1, bookData: book() } });
    await flush();
    const lacuna = container.querySelector('.greek-line.lacuna');
    expect(lacuna).toBeTruthy();
    expect(lacuna!.hasAttribute('id')).toBe(false);
    expect(lacuna!.classList.contains('target')).toBe(false);
    expect(container.querySelector('#Lpost_107-8')).toBeNull();
  });
});
