import { describe, expect, it } from 'vitest';
import { comboWindows, type ComboOptions } from '../lib/search';

// The search port's crossTurn fix (docs/search-port/near-engine.md, rule 12).
// ComboOptions documents crossTurn as "default true — keep hits that straddle
// a turn", but Aristotle's windows() read an unset crossTurn as false, so once
// a play carries turn_bounds a words-unit proximity search stopped at every
// speaker change. The plays' Near has always crossed speakers; only an explicit
// crossTurn: false keeps a match inside one speech.

// One play of 40 tokens on one line; a new speaker at token 20.
const offsets = {
  token_count: 40,
  seg_base_offset: [0],
  segments: [{ book: 1, column: '1', line_runs: [[1, 40]] }],
  book_bounds: [{ book: 1, start: 0 }],
  turn_bounds: [
    { book: 1, speaker: 'Watchman', start: 0, accuracy: 'exact' },
    { book: 1, speaker: 'Chorus', start: 20, accuracy: 'exact' },
  ],
} as unknown as Parameters<typeof comboWindows>[2];
const at = (...starts: number[]) => starts.map((start) => ({ start, span: 1, certain: true }));
const words = (over: Partial<ComboOptions> = {}): ComboOptions => ({ window: 5, unit: 'words', ordered: false, ...over });

describe('a words-unit proximity search and the speaker change', () => {
  it('crosses a speaker change when crossTurn is not set', () => {
    // 18 in the Watchman's speech, 21 in the Chorus's: three words apart.
    expect(comboWindows([at(18), at(21)], words(), offsets)).toHaveLength(1);
  });

  it('crosses it when crossTurn is true', () => {
    expect(comboWindows([at(18), at(21)], words({ crossTurn: true }), offsets)).toHaveLength(1);
  });

  it('stops at it only when asked (crossTurn: false)', () => {
    expect(comboWindows([at(18), at(21)], words({ crossTurn: false }), offsets)).toHaveLength(0);
    // Inside one speech it still finds the pair.
    expect(comboWindows([at(12), at(15)], words({ crossTurn: false }), offsets)).toHaveLength(1);
  });

  it('the turn unit still keeps both words in one speech', () => {
    expect(comboWindows([at(18), at(21)], words({ unit: 'turn' }), offsets)).toHaveLength(0);
    expect(comboWindows([at(2), at(18)], words({ unit: 'turn' }), offsets)).toHaveLength(1);
  });
});
