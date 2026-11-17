// A translation in number order ticks the printed line refs as they rise;
// the edition may print a line out of order (Ag. 1290 before 1284, Electra
// 693 before 685), and a tick moved to that line's running number would run
// backward. The English slicing reads ticks as rising, so a backward tick
// showed the wrong English, or none. Real cases skip when build/dist lacks
// the play.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { lineTicks } from '../lib/english-place';
import { bekkerEnglish, pairUnits, unitAtEnglish, unitAtGreek } from '../lib/paired-hit';
import { englishWords } from '../lib/search';
import type { Segment } from '../lib/data';

const line = (n: number, ref: string) => ({ n, ref, text: 'α', tokens: [{ t: 'α', o: 0, k: 'a' }] });
const english = { id: 'smyth', slot: 'english' as const };
const segment = (lines: [number, string][], parts: [number, string][]): Segment => {
  let text = '';
  const bekker = parts.map(([n, s]) => { const tick = { n, offset: text.length, real: true }; text += s; return tick; });
  return { id: '1:x', column: 'x', greek: lines.map(([n, ref]) => line(n, ref)), english: { text, notes: [], markers: [], bekker } };
};

describe('English ticks where the edition prints a line out of order', () => {
  // As Agamemnon prints it: 1290 between 1283 and 1284.
  const seg = segment([[1250, '1282'], [1251, '1283'], [1252, '1290'], [1253, '1284'], [1254, '1285'], [1255, '1286'], [1256, '1291']],
    [[1282, 'Alpha beta. '], [1285, 'Gamma delta. '], [1290, 'Epsilon.']]);

  it('keeps the ticks rising', () => {
    const ns = lineTicks(seg, seg.english!.bekker).map(t => t.n);
    expect(ns).toEqual([...ns].sort((a, b) => a - b));
  });

  it('reads the line printed 1285 with its own English', () => {
    expect(bekkerEnglish(seg, english, 1254, 1255)).toBe('Gamma delta.');
  });

  it('shows an English hit in its own words', () => {
    const ix = pairUnits({ segments: [seg] } as never, [english]);
    expect(unitAtEnglish(ix, seg, english, 2).english.smyth).toContain('Gamma');
  });

  it('loses no English where two printed refs share one line (784-785)', () => {
    const range = segment([[779, '784-785'], [780, '786']], [[784, 'One. '], [785, 'Two. '], [786, 'Three.']]);
    expect(bekkerEnglish(range, english, 779, 780)).toBe('One. Two.');
  });
});

const dist = resolve(process.cwd(), '../build/dist');
const plays = existsSync(dist) ? readdirSync(dist).filter(p => existsSync(`${dist}/${p}/book-01.json`)) : [];
const book = (play: string) => JSON.parse(readFileSync(`${dist}/${play}/book-01.json`, 'utf8')) as { segments: Segment[] };

describe.skipIf(!plays.length)('English ticks on the built plays', () => {
  it('rise in every translation of every play, but where it ticks one printed line twice', () => {
    const backward: string[] = [];
    for (const play of plays) {
      for (const seg of book(play).segments) {
        const pieces = [seg.english, ...(seg.secondary ?? seg.ross ?? []), ...(seg.third ?? []), ...Object.values(seg.overlays ?? {}).flat()];
        for (const piece of pieces) {
          const raw = piece?.bekker ?? [];
          const ticks = lineTicks(seg, raw);
          ticks.forEach((t, k) => {
            if (k && (t.n < ticks[k - 1].n || (t.n === ticks[k - 1].n && raw.find(r => r.offset === t.offset)?.n !== raw.find(r => r.offset === ticks[k - 1].offset)?.n)))
              backward.push(`${play} ${seg.id} ${ticks[k - 1].n}->${t.n}`);
          });
        }
      }
    }
    expect(backward).toEqual([]);
  }, 60000);

  it.skipIf(!plays.includes('electra-eur'))('Electra 685-693: each English stretch stands by its own Greek', () => {
    const b = book('electra-eur');
    const seg = b.segments.find(s => s.id === '1:693')!;
    const ix = pairUnits(b as never, [english]);
    // The Greek printed 690 (the edition prints 693 first, then 685-692).
    const at690 = seg.greek.findIndex(l => l.ref === '690');
    const pos = seg.greek.slice(0, at690).reduce((n, l) => n + l.tokens.length, 0);
    expect(unitAtGreek(ix, seg, pos).english.smyth).toContain('good report');
    const words = englishWords(seg.english!.text);
    expect(unitAtEnglish(ix, seg, english, words.findIndex(w => w.word === 'triumph')).english.smyth).toContain('triumph');
  });
});
