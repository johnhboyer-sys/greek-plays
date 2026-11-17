// The search page asks for no edition data, and its hits carry no `ed=`, unless
// PUBLIC_EDITIONS=1 and an edition is chosen (plan 4.6).
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Search from '../../components/Search.svelte';
import { search, invalidateSearchIndex } from '../../lib/legacy/search';

const book = { book: 1, segments: [{ id: '1:1', column: '1',
  greek: [{ n: 1, ref: '1', text: 'λόγος', tokens: [{ t: 'λόγος', o: 0, k: 'lo/gos' }] }], english: null }] };
const files: Record<string, unknown> = {
  '/agamemnon/search/meta.json': [{ id: '1:1', book: 1, column: '1', head: 'λόγος', tokens: 'logos', english_head: '' }],
  '/agamemnon/search/form.json': { logos: [[0, 0]] },
  '/agamemnon/book-01.json': book,
  '/agamemnon/chapters.json': {},
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

async function searchOnce(flag: boolean) {
  if (flag) vi.stubEnv('PUBLIC_EDITIONS', '1');
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  const urls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    urls.push(url);
    const hit = files[url.replace(/^.*?\/data/, '')];
    return hit ? { ok: true, status: 200, json: async () => hit } as Response : { ok: false, status: 404, json: async () => ({}) } as Response;
  });
  const page = render(Search);
  await fireEvent.input(page.container.querySelector('#grk-input')!, { target: { value: 'λόγος' } });
  await fireEvent.submit(page.container.querySelector('form.search-form')!);
  await waitFor(() => expect(page.container.querySelectorAll('a.inst-ref').length).toBe(1), { timeout: 5000 });
  const hrefs = Array.from(page.container.querySelectorAll('a.inst-ref')).map(a => a.getAttribute('href')!);
  return { page, urls, hrefs };
}

describe('search page without an edition choice', () => {
  // search-port lane 2: edition picker on the search page
  it.skip('flag off: no edition control, no /ed/ request, no ed= on a hit', async () => {
    const { page, urls, hrefs } = await searchOnce(false);
    expect(page.queryByLabelText('Greek text to search')).toBeNull();
    expect(urls.filter(u => u.includes('/ed/'))).toEqual([]);
    expect(urls.some(u => u.endsWith('/agamemnon/search/form.json'))).toBe(true);
    expect(hrefs).toHaveLength(1);
    expect(hrefs[0]).not.toContain('ed=');
    expect(hrefs[0]).toBe('/read/aeschylus/agamemnon?hlg=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&loc=1');
  });
  // search-port lane 2: edition picker on the search page
  it.skip('flag on, reference chosen (the default): the control shows, and still no /ed/ request or ed=', async () => {
    const { page, urls, hrefs } = await searchOnce(true);
    expect((page.getByLabelText('Greek text to search') as HTMLSelectElement).value).toBe('tlg');
    expect(urls.filter(u => u.includes('/ed/'))).toEqual([]);
    expect(hrefs[0]).not.toContain('ed=');
    expect(hrefs[0]).toBe('/read/aeschylus/agamemnon?hlg=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&loc=1');
  });
});

describe('search() with a Greek edition', () => {
  const seen = () => {
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      urls.push(String(input).replace(/^.*?\/data\//, ''));
      const path = String(input);
      const body = path.endsWith('/meta.json') ? [{ id: '1:1', book: 1, column: '5', head: 'λόγος', tokens: 'logos', english_head: 'word' }]
        : path.endsWith('/form.json') ? { logos: [[0, 0]] } : path.endsWith('/english.json') ? { word: [[0, '']] } : {};
      return { ok: true, status: 200, json: async () => body } as Response;
    });
    return urls;
  };
  afterEach(() => { for (const w of ['agamemnon', 'alcestis']) invalidateSearchIndex(w); });
  it('loads the edition\'s meta and form index, and tags each hit with the edition', async () => {
    const urls = seen();
    const out = await search('λόγος', '', 'all', 'all', 'and', ['agamemnon'], 'form', 'smyth-loeb');
    expect(urls.sort()).toEqual(['agamemnon/ed/smyth-loeb/search/form.json', 'agamemnon/ed/smyth-loeb/search/meta.json']);
    expect(out.results.map(r => [r.meta.column, r.ed])).toEqual([['5', 'smyth-loeb']]);
  });
  it('searches the reference for English, for the reference edition, and for a play without the edition', async () => {
    const urls = seen();
    const english = await search('', 'word', 'all', 'all', 'and', ['agamemnon'], 'form', 'smyth-loeb');
    const reference = await search('λόγος', '', 'all', 'all', 'and', ['agamemnon'], 'form', 'tlg');
    const lacking = await search('λόγος', '', 'all', 'all', 'and', ['alcestis'], 'form', 'smyth-loeb');
    expect(urls.filter(u => u.includes('/ed/'))).toEqual([]);
    expect([english, reference, lacking].flatMap(o => o.results.map(r => r.ed))).toEqual([undefined, undefined, undefined]);
  });
});
