import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import ReaderHost from '../components/ReaderHost.svelte';
import type { BookData } from '../lib/data';

const line = (n: number, ref: string, text: string) => ({ n, ref, text, tokens: [] });
const smyth = { book: 1, speakerRoster: ['Watchman'], segments: [
  { id: '1:1', column: '1', greek: [line(1, '1', 'σμύθη')], english: { text: 'Smyth', notes: [], markers: [] } },
] } as BookData;
const reference = { book: 1, speakerRoster: ['Watchman'], segments: [
  { id: '1:1', column: '1', greek: [line(1, '1', 'πρῶτον'), line(2, '2', 'δεύτερον')], english: { text: 'Smyth', notes: [], markers: [] } },
] } as BookData;

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); history.replaceState({}, '', '/'); });

it('shows the edition book and fetches the reference when Morshead is picked', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?ed=smyth-loeb');
  const urls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    urls.push(String(url));
    return { ok: true, json: async () => reference } as Response;
  });
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 1, bookData: smyth,
    serverEdition: 'smyth-loeb', speakerRoster: ['Watchman'], authorName: 'Aeschylus' });
  expect(page.container.textContent).toContain('σμύθη');
  const picker = page.container.querySelector('select.rc-trans-select') as HTMLSelectElement;
  expect(picker).not.toBeNull();
  await fireEvent.change(picker, { target: { value: 'morshead' } });
  await waitFor(() => expect(urls.some(url => url.endsWith('/agamemnon/book-01.json'))).toBe(true));
  await waitFor(() => expect(page.container.textContent).toContain('δεύτερον'));
  expect(page.container.querySelectorAll('.greek-line').length).toBe(2);
});
