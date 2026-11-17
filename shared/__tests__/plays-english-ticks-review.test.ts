// English ticks on a play's printed lines: five cases a static review raised
// (2026-11-17), each checked against the 44 built plays. One was a fault
// (a line ticked twice lost its first half); the rest pin the behaviour the
// rising-tick rule gives, measured on the real data. Real cases skip when
// build/dist lacks the play.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { englishPlace } from '../lib/english-place';
import { bekkerEnglish, pairUnits, unitAtEnglish, unitAtGreek } from '../lib/paired-hit';
import type { Segment } from '../lib/data';

const line = (n: number, ref: string, text = 'α') => ({ n, ref, text, tokens: text ? [{ t: text, o: 0, k: 'a' }] : [] });
const english = { id: 'smyth', slot: 'english' as const };
const segment = (lines: [number, string][], parts: [number, string][]): Segment => {
  let text = '';
  const bekker = parts.map(([n, s]) => { const tick = { n, offset: text.length, real: true }; text += s; return tick; });
  return { id: '1:x', column: 'x', greek: lines.map(([n, ref]) => line(n, ref)), english: { text, notes: [], markers: [], bekker } };
};

describe('a printed line the translation ticks twice (two speakers share it)', () => {
  const seg = segment([[5, '100']], [[100, 'First half. '], [100, 'Second half.']]);

  it('reads the line\'s whole English, both halves', () => {
    expect(bekkerEnglish(seg, english, 5, 6)).toBe('First half. Second half.');
  });

  it('pairs a hit in the first half with English that holds it', () => {
    const ix = pairUnits({ segments: [seg] } as never, [english]);
    expect(unitAtEnglish(ix, seg, english, 0).english.smyth).toContain('First half.');
    expect(unitAtGreek(ix, seg, 0).english.smyth).toBe('First half. Second half.');
  });
});

// The rising-tick rule (1b10f3e): a line printed out of order takes no tick.
// Pinned, not changed: on the built plays, English between two ticks follows
// the printed order, so a word read off between them lands on the moved line
// as often as it should (Bacch. 847, IA 1262, Phil. 273) as it lands a line
// off (Ag. 1290, Or. 546).
describe('a line printed out of order (Ag. 1290 before 1284)', () => {
  const seg = segment([[1250, '1282'], [1251, '1283'], [1252, '1290'], [1253, '1284'], [1254, '1285'], [1255, '1286'], [1256, '1291']],
    [[1282, 'Alpha beta. '], [1285, 'Gamma delta. '], [1290, 'Epsilon.']]);

  it('reads the moved line with the stretch printed around it', () => {
    expect(bekkerEnglish(seg, english, 1252, 1253)).toBe('Alpha beta.');
  });

  it('shows the English ticked for the moved line on the next line printed in order', () => {
    expect(bekkerEnglish(seg, english, 1256, 1257)).toBe('Epsilon.');
  });

  it('may cite a word between two ticks as the moved line, by its printed place', () => {
    expect(englishPlace(seg, english, [1], ['beta'], false)?.line).toBe(1252);
  });
});

// A lacuna the edition marks "post N" prints no number of its own and no
// Greek; its line reads the English around it, or none when nothing precedes.
describe('a lacuna line ("post 1226")', () => {
  it('reads the stretch it falls in', () => {
    const seg: Segment = { ...segment([[5, '100'], [7, '101']], [[100, 'A. '], [101, 'B.']]) };
    seg.greek.splice(1, 0, line(6, 'post 100', ''));
    expect(bekkerEnglish(seg, english, 6, 7)).toBe('A.');
  });

  it('reads none where it opens the segment, and no Greek hit can land there', () => {
    const seg: Segment = { ...segment([[7, '101']], [[101, 'B.']]) };
    seg.greek.unshift(line(6, 'post 100', ''));
    expect(bekkerEnglish(seg, english, 6, 7)).toBe('');
    expect(seg.greek[0].tokens).toEqual([]);
  });
});

// Two rising runs of one length: the first is kept. On the built plays this
// keeps every line's English (IA 665/653, Phoen. 1749/1747, Heracl. 558-563);
// the other choice would leave a line with none.
describe('two rising runs of one length (printed 10, 11, 1, 2)', () => {
  const seg = segment([[1, '10'], [2, '11'], [3, '1'], [4, '2']], [[1, 'One. '], [10, 'Ten.']]);

  it('keeps the first run, and every line reads English', () => {
    for (const n of [1, 2, 3, 4]) expect(bekkerEnglish(seg, english, n, n + 1)).toBe('One. Ten.');
  });
});

const dist = resolve(process.cwd(), '../build/dist');
const ajax = `${dist}/ajax/book-01.json`;

describe.skipIf(!existsSync(ajax))('Ajax 591, two speakers on one line (built data)', () => {
  it('pairs Tecmessa\'s half with the Greek', () => {
    const b = JSON.parse(readFileSync(ajax, 'utf8')) as { segments: Segment[] };
    const seg = b.segments.find(s => s.id === '1:591')!;
    const ix = pairUnits(b as never, [english]);
    expect(unitAtGreek(ix, seg, 0).english.smyth).toContain('Hush, no impiety!');
    expect(unitAtEnglish(ix, seg, english, 0).english.smyth).toContain('Hush');
  });
});
