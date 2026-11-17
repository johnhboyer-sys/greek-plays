import { describe, expect, it } from 'vitest';
import { chapterPlaces, eachHit } from '../lib/chapter-pages';
import type { Offsets, SearchResult } from '../lib/search';

// Two segments of one play may share a book and column: Seven against Thebes
// prints 803 and 810 twice (the doublet, CLAUDE.md "repeated_refs"), Helen
// has two lacunae after 1226. chapter-pages once mapped a hit's segment by
// "book:column", so a hit in the first 803 was counted in the second's speech.
// The excerpts below are the real meta.json and offsets.json rows (build of
// 16 Nov 2026), cut to the segments around the doublet.

// Seven against Thebes, segments 93-104 (base offsets 3936-4001).
const sevenMeta = [
  { id: '1:803', book: 1, column: '803' },      // 93
  { id: '1:804', book: 1, column: '804' },
  { id: '1:805', book: 1, column: '805' },
  { id: '1:806', book: 1, column: '806' },
  { id: '1:803.2', book: 1, column: '803' },    // 97
  { id: '1:807', book: 1, column: '807' },
  { id: '1:808', book: 1, column: '808' },
  { id: '1:809', book: 1, column: '809' },
  { id: '1:810', book: 1, column: '810' },      // 101
  { id: '1:812', book: 1, column: '812' },
  { id: '1:810.2', book: 1, column: '810' },    // 103
];
// Index 93 of the play is index 0 here: the seg the engine reports is the
// play's own index, so the excerpt keeps it by offsetting the arrays.
const pad = 93;
const sevenOffsets = {
  token_count: 5123,
  seg_base_offset: [...Array(pad).fill(0), 3936, 3943, 3948, 3955, 3961, 3968, 3973, 3980, 3985, 3992, 3997, 4001],
  segments: [...Array(pad).fill({ book: 1, column: '0', line_runs: [[1, 0]] }),
    ...sevenMeta.map((m, i) => ({ book: 1, column: m.column, line_runs: [[786 + i, [7, 5, 7, 6, 7, 5, 7, 5, 7, 5, 4][i]]] }))],
  book_bounds: [{ book: 1, start: 0 }],
  chapter_bounds: [
    { book: 1, chapter: '803', start: 3936, accuracy: 'exact' },
    { book: 1, chapter: '803b', start: 3961, accuracy: 'exact' },
    { book: 1, chapter: '810', start: 3985, accuracy: 'exact' },
    { book: 1, chapter: '810b', start: 3997, accuracy: 'exact' },
  ],
} as unknown as Offsets;

const hit = (meta: { id: string; book: number; column: string }, seg: number, pos: number): SearchResult =>
  ({ work: 'seven-against-thebes', meta, seg, grkMatch: true, engMatch: false, grkPositions: [pos] });

describe('two segments with one column', () => {
  const places = chapterPlaces(new Map([['seven-against-thebes', sevenOffsets]]));
  const speechOf = (r: SearchResult) => { let at = ''; eachHit(r, places, a => { at = a.chapter; }); return at; };

  it('counts a hit in the first 803 in its own speech, and one in the second 803 in the second', () => {
    expect(speechOf(hit(sevenMeta[0], 93, 2))).toBe('803');
    expect(speechOf(hit(sevenMeta[4], 97, 2))).toBe('803b');
  });

  it('does the same for 810', () => {
    expect(speechOf(hit(sevenMeta[8], 101, 0))).toBe('810');
    expect(speechOf(hit(sevenMeta[10], 103, 0))).toBe('810b');
  });

  it('keeps Helen\'s two lacunae after 1226 apart', () => {
    // Helen segments 368 and 369: both "post 1226", no tokens, base 7306.
    const helen = {
      token_count: 7400,
      seg_base_offset: [...Array(368).fill(0), 7306, 7306, 7306],
      segments: [...Array(368).fill({ book: 1, column: '0', line_runs: [[1, 0]] }),
        { book: 1, column: 'post 1226', line_runs: [[1232, 0]] },
        { book: 1, column: 'post 1226', line_runs: [[1233, 0]] },
        { book: 1, column: '1227', line_runs: [[1234, 6]] }],
      book_bounds: [{ book: 1, start: 0 }],
      chapter_bounds: [
        { book: 1, chapter: '1226', start: 7301, accuracy: 'exact' },
        { book: 1, chapter: 'post 1226', start: 7306, accuracy: 'exact' },
        { book: 1, chapter: 'post 1226b', start: 7306, accuracy: 'exact' },
        { book: 1, chapter: '1227', start: 7306, accuracy: 'exact' },
      ],
    } as unknown as Offsets;
    const p = chapterPlaces(new Map([['helen', helen]]));
    const first = { work: 'helen', meta: { id: '1:post 1226', book: 1, column: 'post 1226' }, seg: 368, grkMatch: true, engMatch: false, grkPositions: [0] } as SearchResult;
    const second = { ...first, meta: { id: '1:post 1226.2', book: 1, column: 'post 1226' }, seg: 369 };
    // Both open at 7306, the start of three speeches: each takes the last.
    expect(p.grk(first, 0).key).toBe(p.grk(second, 0).key);
    // The segment index is what places them: a result without it falls back
    // to the column, which names only one of the two.
    const third = { ...first, seg: 370, meta: { id: '1:1227', book: 1, column: '1227' } };
    expect(p.grk(third, 0).chapter).toBe('1227');
  });

  it('falls back to the column where a result carries no segment index', () => {
    const r = hit(sevenMeta[0], 93, 2);
    delete r.seg;
    // The column names the later of the two 803s.
    expect(speechOf(r)).toBe('803b');
  });
});
