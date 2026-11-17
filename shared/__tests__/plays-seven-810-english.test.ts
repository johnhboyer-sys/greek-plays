// Seven Against Thebes, English search "dust" (real build data): the hit at
// the doubly printed 810 shows Smyth's English before it is opened. Skips when
// build/dist lacks the play.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { bekkerEnglish, pairUnits, unitAtEnglish } from '../lib/paired-hit';
import type { Segment } from '../lib/data';

const dist = resolve(process.cwd(), '../build/dist');
const built = existsSync(`${dist}/seven-against-thebes/book-01.json`) && existsSync(`${dist}/seven-against-thebes/search/english.json`);

afterEach(() => { vi.restoreAllMocks(); history.replaceState({}, '', '/'); });

describe.skipIf(!built)('Seven, English "dust", built data', () => {
  it('every English hit shows its words, the one at 810 included', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      const file = `${dist}/${String(input).replace(/^.*?\/data\//, '')}`;
      return existsSync(file) && !file.endsWith('/')
        ? { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, 'utf8')) } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    history.replaceState(null, '', '/search?e=dust&w=seven-against-thebes');
    const { default: Search } = await import('../components/Search.svelte');
    const { container } = render(Search);
    await waitFor(() => expect(container.querySelectorAll('li.instance').length).toBeGreaterThan(5), { timeout: 20000 });
    const rows = [...container.querySelectorAll('li.instance')];
    const empty = rows.filter(li => li.querySelector('.inst-en') && !(li.querySelector('.inst-snippet')?.textContent ?? '').trim());
    expect(empty.map(li => li.querySelector('.inst-ref')?.textContent)).toEqual([]);
    const at810 = rows.find(li => li.querySelector('.inst-ref')?.textContent?.trim() === '810')!;
    expect(at810.querySelector('.inst-snippet')?.textContent).toContain('dust');
  }, 40000);
});

// No build needed: two segments print the ref 810, and a tick names the line
// as printed (810) where the Greek counts on in running numbers (794, 796).
describe('English ticks on a play that prints a ref twice', () => {
  const line = (n: number, ref: string) => ({ n, ref, text: 'α', tokens: [{ t: 'α', o: 0, k: 'a' }] });
  const seg = (id: string, n: number, text: string): Segment => ({
    id, column: '810', greek: [line(n, '810')], english: { text, notes: [], markers: [], bekker: [{ n: 810, offset: 0, real: true }] },
  });
  const book = { segments: [seg('1:810', 794, 'Are they lying out there?'), seg('1:810.2', 796, 'Struck down in the dust.')] };
  const smyth = { id: 'smyth', slot: 'english' as const };
  it('reads each segment\'s English at its own line', () => {
    expect(bekkerEnglish(book.segments[1], smyth, 796, 797)).toBe('Struck down in the dust.');
    const ix = pairUnits(book as never, [smyth]);
    expect(unitAtEnglish(ix, book.segments[0], smyth, 0).english.smyth).toBe('Are they lying out there?');
    expect(unitAtEnglish(ix, book.segments[1], smyth, 4).english.smyth).toBe('Struck down in the dust.');
  });
});
