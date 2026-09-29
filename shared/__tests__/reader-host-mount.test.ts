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
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('');
  await fireEvent.click(page.getByText('new edition'));
  await waitFor(() => expect((globalThis as any).__readerProbeMounts__).toBe(2));
  expect(page.getByTestId('reader-probe').getAttribute('data-anchor')).toBe('1203');
});
