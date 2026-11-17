// A tick never maps outside its segment's Greek lines. Libation Bearers'
// Smyth tick 165 stands past every in-order ref of its segment (the edition
// prints 165 out of order), and mapped to one line past the last, where the
// stretch held no Greek and dropped out of the search snippet.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { lineTicks } from '../lib/english-place';
import { bekkerEnglish, pairUnits, unitAtEnglish } from '../lib/paired-hit';
import { englishWords } from '../lib/search';
import type { Segment } from '../lib/data';

const line = (n: number, ref: string) => ({ n, ref, text: 'α', tokens: [{ t: 'α', o: 0, k: 'a' }] });
const english = { id: 'smyth', slot: 'english' as const };

describe('a final tick whose ref the edition prints out of order', () => {
  // Refs 165 (moved up), 160, 161, 162: the tick 165 has no in-order line at or after it.
  const lines: [number, string][] = [[100, '165'], [101, '160'], [102, '161'], [103, '162']];
  const text = 'One. Two. Take your share.';
  const seg: Segment = {
    id: '1:160', column: '160', greek: lines.map(([n, r]) => line(n, r)),
    english: { text, notes: [], markers: [], bekker: [{ n: 160, offset: 0, real: true }, { n: 165, offset: 10, real: true }] },
  };

  it('stays on the segment’s last line', () => {
    const ns = lineTicks(seg, seg.english!.bekker).map(t => t.n);
    expect(Math.max(...ns)).toBeLessThanOrEqual(103);
  });

  it('keeps the closing English with a Greek line', () => {
    expect(bekkerEnglish(seg, english, 100, 104)).toContain('Take your share');
  });
});

const dist = resolve(process.cwd(), '../build/dist');
const plays = existsSync(dist) ? readdirSync(dist).filter(p => existsSync(`${dist}/${p}/book-01.json`)) : [];
const book = (play: string) => JSON.parse(readFileSync(`${dist}/${play}/book-01.json`, 'utf8')) as { segments: Segment[] };

describe.skipIf(!plays.length)('ticks on the built plays', () => {
  it('none maps outside its segment’s lines, in any translation', () => {
    const outside: string[] = [];
    for (const play of plays) {
      for (const seg of book(play).segments) {
        if (!seg.greek.length) continue;
        const lo = seg.greek[0].n, hi = seg.greek.at(-1)!.n;
        const pieces = [seg.english, ...(seg.secondary ?? seg.ross ?? []), ...(seg.third ?? []), ...Object.values(seg.overlays ?? {}).flat()];
        for (const piece of pieces) {
          for (const t of lineTicks(seg, piece?.bekker ?? [])) if (t.n < lo || t.n > hi) outside.push(`${play} ${seg.id} ${t.n}`);
        }
      }
    }
    if (outside.length) console.log(`outside: ${outside.length}`, outside.slice(0, 5));
    expect(outside).toEqual([]);
  }, 120000);

  it.skipIf(!plays.includes('libation-bearers'))('Libation Bearers: Smyth’s "startling news" has Greek', () => {
    const b = book('libation-bearers');
    const seg = b.segments.find(s => s.id === '1:165')!;
    const at = seg.english!.text.indexOf('startling');
    const real = lineTicks(seg, seg.english!.bekker);
    expect(seg.english!.text.slice(at - 5, at + 40)).toContain('startling');
    expect(real.every(t => t.n <= seg.greek.at(-1)!.n)).toBe(true);
    const ix = pairUnits(b as never, [english]);
    const words = englishWords(seg.english!.text);
    expect(unitAtEnglish(ix, seg, english, words.findIndex(w => w.word === 'startling')).english.smyth).toContain('startling news');
  });
});
