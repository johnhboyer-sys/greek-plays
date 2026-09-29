import { render } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import Reader from '../components/Reader.svelte';
import type { BookData } from '../lib/data';

// Flag off: ReaderShell mounts Reader with no `edition` prop. Nothing on that
// path, mounting, switching translation, or copying, may ask for an edition
// book or a concordance.
afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

it('makes no /ed/ and no concordance request without an edition prop', async () => {
  const urls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    urls.push(String(url));
    return { ok: false, status: 404, json: async () => ({}) } as Response;
  });
  const book = { book: 1, segments: [{ id: '1:1', column: '1',
    greek: [{ n: 1, ref: '1', text: 'λόγος', tokens: [{ t: 'λόγος', o: 0, k: 'lo/gos' }] }], english: null }] } as BookData;
  render(Reader, { props: { work: 'agamemnon', bookNum: 1, bookData: book } });
  await new Promise(r => setTimeout(r, 50));
  expect(urls.filter(u => u.includes('/ed/') || u.includes('concordance'))).toEqual([]);
});
