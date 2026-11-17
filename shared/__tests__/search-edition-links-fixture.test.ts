// Deterministic check, no build needed (the built-Smyth check in
// search-edition-links.test.ts skips without build/dist): a search of the fixture
// edition (fixtures/data/sample-work/ed/mini) links every hit with `ed=mini` and
// `view=greek`, and each hit's loc names a mini-book segment holding the token.
// The env is set before any import, since works.ts reads PUBLIC_READER_FIXTURES
// when it loads.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { greekFold } from '../lib/search';

vi.hoisted(() => {
  vi.stubEnv('PUBLIC_EDITIONS', '1');
  vi.stubEnv('PUBLIC_READER_FIXTURES', '1');
});

afterEach(() => { vi.restoreAllMocks(); history.replaceState({}, '', '/'); });

describe('search hits from the fixture edition index (always runs)', () => {
  it('every hit carries ed=mini and view=greek, and lands on a segment holding the token', async () => {
    const fixtures = resolve(process.cwd(), '../fixtures/data/sample-work');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      // The ported engine's index names (search port); the fixture keeps the old ones.
      const file = `${fixtures}/${String(input).replace(/^.*?\/data\/sample-work\//, '').replace(/greek_(form|lemma)\.json$/, '$1.json')}`;
      // The ported page groups a hit under its book's outline; the fixture's
      // chapters.json is empty, so one chapter stands for the mini book.
      if (String(input).endsWith('/sample-work/chapters.json'))
        return { ok: true, status: 200, json: async () => ({ '1': [{ chapter: '1', column: '1.1', line: '1' }] }) } as Response;
      return existsSync(file) && /\.json$/.test(file)
        ? { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, 'utf8')) } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    const { default: Search } = await import('../components/Search.svelte');
    const page = render(Search);
    await fireEvent.change(page.getByLabelText('Greek text to search') as HTMLSelectElement, { target: { value: 'mini' } });
    const book: { segments: { column: string; greek: { tokens: { t: string }[] }[] }[] } =
      JSON.parse(readFileSync(`${fixtures}/ed/mini/book-01.json`, 'utf8'));
    const input = page.container.querySelector('#grk-input') as HTMLInputElement;
    const form = page.container.querySelector('form.search-form') as HTMLFormElement;
    const words = book.segments.flatMap(s => s.greek.flatMap(l => l.tokens.map(t => t.t)));
    expect(words.length).toBeGreaterThan(0);
    for (const [i, word] of words.entries()) {
      await fireEvent.input(input, { target: { value: word } });
      // Each word as spelled: the fixture has no lemma map (the ported page
      // searches by headword by default).
      if (i === 0) await fireEvent.click(page.getByRole('radio', { name: 'exact form' }));
      await fireEvent.submit(form);
      await waitFor(() => expect(page.container.querySelector('.search-btn')).not.toBeDisabled());
      await waitFor(() => expect(page.container.querySelectorAll('a.inst-ref').length).toBeGreaterThan(0), { timeout: 5000 });
      for (const a of Array.from(page.container.querySelectorAll('a.inst-ref'))) {
        const href = a.getAttribute('href')!;
        const url = new URL(href, 'https://x.test');
        expect(url.searchParams.get('ed'), href).toBe('mini');
        expect(url.searchParams.get('view'), href).toBe('greek');
        const seg = book.segments.find(s => s.column === url.searchParams.get('loc'));
        expect(seg, `no segment ${url.searchParams.get('loc')} in the mini book: ${href}`).toBeDefined();
        expect(seg!.greek.some(l => l.tokens.some(t => greekFold(t.t) === greekFold(word))), `${href} lacks ${word}`).toBe(true);
      }
    }
  }, 60000);
});
