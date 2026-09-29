import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import type { BookData } from '../lib/data';

vi.mock('../components/Reader.svelte', async () => ({ default: (await import('./ReaderMountProbe.svelte')).default }));
import ReaderHost from '../components/ReaderHost.svelte';

const book = (ref: string) => ({ book: 1, segments: [{ id: ref, column: ref,
  greek: [{ n: 1, ref, text: 'λόγος', tokens: [] }], english: null,
}] }) as BookData;

afterEach(() => {
  vi.restoreAllMocks();
  delete (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__;
  localStorage.clear();
  history.replaceState({}, '', '/');
  delete (globalThis as typeof globalThis & { __readerProbeMounts__?: number }).__readerProbeMounts__;
});

it('keeps the mounted reader and anchor for a same-edition translation change, then remounts once for a new edition', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => ({ ok: true, json: async () => book('1203') }) as Response);
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 1, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  const probe = page.getByTestId('reader-probe');
  await fireEvent.click(page.getByText('same edition'));
  expect((globalThis as any).__readerProbeMounts__).toBe(1);
  expect(page.getByTestId('reader-probe')).toBe(probe);
  expect(probe.isConnected).toBe(true);
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('');
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1203');
});

it('places the anchor through the concordance when the new edition lacks the ref, and asks only for what it needs', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://d2.test'; // caches are keyed per root/book, so each test uses its own
  const urls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const u = String(url);
    urls.push(u);
    // The reference book prints 1202 only; the edition prints 1203.
    return { ok: true, json: async () => u.endsWith('concordance.json') ? { '1203': '1202' } : book(u.includes('/ed/') ? '1203' : '1202') } as Response;
  });
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 2, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  await fireEvent.click(page.getByText('same edition'));
  expect(urls.filter(u => u.includes('concordance'))).toHaveLength(0);
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1202');
  expect(urls.filter(u => u.includes('concordance'))).toEqual(['https://d2.test/agamemnon/ed/smyth-loeb/concordance.json']);
});

it('falls back to the nearest lower ref when the concordance is missing', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://d3.test'; // caches are keyed per root/book, so each test uses its own
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url).endsWith('concordance.json')
    ? { ok: false, status: 404 } as Response
    : { ok: true, json: async () => String(url).includes('/ed/') ? book('1203') : book('1201') } as Response);
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 3, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1201');
});
