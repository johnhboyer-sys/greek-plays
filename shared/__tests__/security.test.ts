import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import FootnotePopup from '../components/FootnotePopup.svelte';
import { escapeRe, highlightPrefixMatches } from '../lib/text';

const XSS = '<img src=x onerror=alert(1)><p>safe note</p>';

afterEach(() => {
  vi.restoreAllMocks();
  delete (globalThis as { __READER_IMPORT_HAS_TRANS__?: unknown }).__READER_IMPORT_HAS_TRANS__;
  delete (globalThis as { __READER_IMPORT_FOOTNOTE_HOOK__?: unknown }).__READER_IMPORT_FOOTNOTE_HOOK__;
});

describe('FootnotePopup sanitizes HTML before {@html} (Astra lane A, F4)', () => {
  it('strips onerror from a drama footnote fetched through data.ts', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ '1': XSS }),
    } as Response);
    const { container } = render(FootnotePopup, {
      props: { work: 'F4Work', n: '1', transId: 'smyth', anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await waitFor(() => expect(container.querySelector('.footnote-text')).toBeTruthy());
    const body = container.querySelector('.footnote-text')!;
    expect(body.innerHTML).not.toMatch(/onerror/i);
    expect(body.querySelector('img')).toBeNull();
    expect(body.textContent).toContain('safe note');
  });

  it('strips onerror from an imported-translation footnote hook', async () => {
    (globalThis as {
      __READER_IMPORT_HAS_TRANS__?: (work: string, id: string) => boolean;
      __READER_IMPORT_FOOTNOTE_HOOK__?: (work: string, id: string, label: string) => string | null;
    }).__READER_IMPORT_HAS_TRANS__ = () => true;
    (globalThis as {
      __READER_IMPORT_FOOTNOTE_HOOK__?: (work: string, id: string, label: string) => string | null;
    }).__READER_IMPORT_FOOTNOTE_HOOK__ = () => XSS;
    const { container } = render(FootnotePopup, {
      props: { work: 'F4Work', n: '1', transId: 'imported', anchor: { x: 0, y: 0 }, onClose: vi.fn() },
    });
    await waitFor(() => expect(container.querySelector('.footnote-text')).toBeTruthy());
    const body = container.querySelector('.footnote-text')!;
    expect(body.innerHTML).not.toMatch(/onerror/i);
    expect(body.querySelector('img')).toBeNull();
  });
});

describe('regex helpers', () => {
  it.each(['(', '[', '*?', '\\', 'λόγος'])('escapes %s for direct RegExp use', (term) => {
    expect(() => new RegExp(escapeRe(term), 'u')).not.toThrow();
  });

  it.each([
    ['(', 'alpha ( beta', 'alpha <mark>(</mark> beta'],
    ['[', 'alpha [ beta', 'alpha <mark>[</mark> beta'],
    ['*?', 'alpha *? beta', 'alpha <mark>*?</mark> beta'],
    ['\\', 'alpha \\ beta', 'alpha <mark>\\</mark> beta'],
    ['λόγος', 'ὁ λόγος καλός', 'ὁ <mark>λόγος</mark> καλός'],
  ])('highlights %s without corrupting escaped text', (term, text, expected) => {
    expect(() => highlightPrefixMatches(text, [term])).not.toThrow();
    expect(highlightPrefixMatches(text, [term])).toBe(expected);
  });
});
