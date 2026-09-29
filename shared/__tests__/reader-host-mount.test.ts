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
  history.replaceState({}, '', '/aeschylus/agamemnon');
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
  history.replaceState({}, '', '/aeschylus/agamemnon');
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
  history.replaceState({}, '', '/aeschylus/agamemnon');
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

it('keeps ?ed= while a ?loc= or line hash is in the URL, so a reload reads the same numbering', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?ed=smyth-loeb&trans=smyth&loc=1203');
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => ({ ok: true, json: async () => book('1203') }) as Response);
  render(ReaderHost, { work: 'agamemnon', bookNum: 1, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  const url = new URL(location.href);
  expect(url.searchParams.get('ed')).toBe('smyth-loeb');
  expect(url.searchParams.get('loc')).toBe('1203');
  history.replaceState({}, '', '/aeschylus/agamemnon?trans=smyth#1203');
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 1, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect(page.getAllByTestId('reader-probe').length).toBeGreaterThan(0));
  expect(new URL(location.href).searchParams.get('ed')).toBe('smyth-loeb');
});

it('rewrites ?loc= (and drops a stale hash) to the mapped ref after an edition switch, so a reload lands there', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon?ed=smyth-loeb&trans=smyth&loc=1203#1203');
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://d4.test';
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const u = String(url);
    return { ok: true, json: async () => u.endsWith('concordance.json') ? { '1203': '1202' } : book(u.includes('/ed/') ? '1203' : '1202') } as Response;
  });
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 4, bookData: book('1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1202');
  const url = new URL(location.href);
  expect(url.searchParams.get('loc')).toBe('1202');
  expect(url.hash).toBe('');
  // The TLG reference edition needs no ?ed= beside a ?loc=: a bare ?loc= reads in TLG numbering.
  expect(url.searchParams.get('ed')).toBeNull();
});

// Both books print 1203, but the concordance says the edition's 1203 is the reference's 1202:
// the concordance wins over the same printed ref (edition-place.ts), so the host must load it
// even when the new book has the ref.
const both = (...refs: string[]) => ({ book: 1, segments: [{ id: refs[0], column: refs[0],
  greek: refs.map((ref, i) => ({ n: i + 1, ref, text: 'λόγος', tokens: [] })), english: null,
}] }) as BookData;

it('lands on the concordance target when the new edition also prints the same ref', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon');
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://d5.test';
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const u = String(url);
    return { ok: true, json: async () => u.endsWith('concordance.json') ? { '1203': '1202' } : both('1202', '1203') } as Response;
  });
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 5, bookData: both('1202', '1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1202');
});

it('keeps the same ref when the concordance fails to load and the new edition prints it', async () => {
  history.replaceState({}, '', '/aeschylus/agamemnon');
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://d6.test';
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url).endsWith('concordance.json')
    ? { ok: false, status: 500 } as Response
    : { ok: true, json: async () => both('1202', '1203') } as Response);
  const page = render(ReaderHost, { work: 'agamemnon', bookNum: 6, bookData: both('1202', '1203'),
    serverEdition: 'smyth-loeb', speakerRoster: [], authorName: 'Aeschylus' });
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(1));
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1203');
});
