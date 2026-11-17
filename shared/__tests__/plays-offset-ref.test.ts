import { describe, expect, it, vi } from 'vitest';

// A play is cited by the line number the edition prints ("106-107" for a
// lyric pair, "160" where the running count says 147), which offsets.json
// carries per line in segments[i].refs when any line's differs from its
// running number (pipeline stage6). offsetRef and offsetCite read it
// (search port, data-contracts §5 item 12).
vi.mock('../lib/works', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/works')>();
  const play = { id: 'play', title: 'Play', abbr: 'Pl.', citation: { scheme: 'play-line' }, translations: [], bookLabels: [] };
  return { ...actual, getWork: (id: string) => (id === 'play' ? play : actual.getWork(id)) };
});

const { offsetRef, offsetCite } = await import('../lib/search');

const offsets = {
  token_count: 12,
  seg_base_offset: [0, 7],
  segments: [
    // Lines 104 and 105 print as 104 and "106-107".
    { book: 1, column: '104', line_runs: [[104, 4], [105, 3]], refs: ['104', '106-107'] },
    // No refs: every line prints its running number.
    { book: 1, column: '108', line_runs: [[106, 2], [107, 3]] },
  ],
  book_bounds: [{ book: 1, start: 0 }],
} as unknown as Parameters<typeof offsetRef>[0];

describe('a play hit cites its printed line', () => {
  it('offsetRef gives the printed ref beside the running line number', () => {
    expect(offsetRef(offsets, 5)).toMatchObject({ seg_idx: 0, pos: 5, line: 105, ref: '106-107' });
    expect(offsetRef(offsets, 0)).toMatchObject({ line: 104, ref: '104' });
  });

  it('a segment without refs prints its running numbers', () => {
    expect(offsetRef(offsets, 9)).toMatchObject({ seg_idx: 1, line: 107, ref: '107' });
  });

  it('offsetCite cites the printed line, not the segment', () => {
    expect(offsetCite('play', offsets, 5)).toBe('106-107');
    expect(offsetCite('play', offsets, 9)).toBe('107');
  });
});
