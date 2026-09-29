// Plan 4.5 / P3 success 5: a search of an edition's Greek index links to
// `?ed=<edition>&loc=<ref>`, and the line the reader lands on (that ref, in that
// edition's book) holds the token searched. Needs a built Agamemnon:
//   cd pipeline && .venv/bin/python -m drama_pipeline all --work agamemnon
//   ... all --work agamemnon --edition smyth-loeb
// It skips itself when the build is absent (build/ is git-ignored).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { greekFold } from '../lib/search';

const dist = resolve(process.cwd(), '../build/dist');
const built = existsSync(`${dist}/agamemnon/ed/smyth-loeb/search/form.json`) && existsSync(`${dist}/agamemnon/ed/smyth-loeb/book-01.json`);

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); history.replaceState({}, '', '/'); });

const QUERIES = ['καὶ', 'δὲ', 'γὰρ', 'θεοὺς', 'Ἄργος', 'πόλις', 'φρήν', 'ἄναξ', 'τέκνον', 'δόμος', 'χθονὸς', 'ἔπος'];

describe.skipIf(!built)('search hits from an edition index', () => {
  it('link to ?ed= and land on a line holding the token (100 sampled hits)', async () => {
    vi.stubEnv('PUBLIC_EDITIONS', '1');
    vi.spyOn(console, 'warn').mockImplementation(() => {}); // the other 43 plays are not built here
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      const url = String(input);
      urls.push(url);
      const file = `${dist}/${url.replace(/^.*?\/data\//, '')}`;
      return existsSync(file) && !file.endsWith('/')
        ? { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, 'utf8')) } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    const { default: Search } = await import('../components/Search.svelte');
    const page = render(Search);
    const picker = page.getByLabelText('Greek text to search') as HTMLSelectElement;
    expect(Array.from(picker.options).map(o => o.value)).toContain('smyth-loeb');
    await fireEvent.change(picker, { target: { value: 'smyth-loeb' } });
    const book: { segments: { greek: { ref?: string; tokens: { t: string }[] }[] }[] } =
      JSON.parse(readFileSync(`${dist}/agamemnon/ed/smyth-loeb/book-01.json`, 'utf8'));
    const lines = new Map(book.segments.flatMap(s => s.greek).map(l => [l.ref, l] as const));
    const input = page.container.querySelector('#grk-input') as HTMLInputElement;
    const form = page.container.querySelector('form.search-form') as HTMLFormElement;
    const hits: { query: string; href: string }[] = [];
    for (const query of QUERIES) {
      await fireEvent.input(input, { target: { value: query } });
      await fireEvent.submit(form);
      await waitFor(() => expect(page.container.querySelector('.search-btn')).not.toBeDisabled());
      await waitFor(() => expect(page.container.querySelectorAll('a.inst-ref').length).toBeGreaterThan(0), { timeout: 5000 });
      for (const a of Array.from(page.container.querySelectorAll('a.inst-ref')))
        hits.push({ query, href: a.getAttribute('href')! });
    }
    // One in n hits, spread across every query, so 100 is a sample and not a prefix.
    const sample = hits.filter((_, i) => i % Math.max(1, Math.floor(hits.length / 100)) === 0).slice(0, 100);
    expect(hits.length, `${hits.length} hits`).toBeGreaterThanOrEqual(100);
    expect(sample).toHaveLength(100);
    for (const { query, href } of sample) {
      const url = new URL(href, 'https://x.test');
      expect(url.searchParams.get('ed'), href).toBe('smyth-loeb');
      const line = lines.get(url.searchParams.get('loc')!);
      expect(line, `no line ${url.searchParams.get('loc')} in the Smyth book: ${href}`).toBeDefined();
      expect(line!.tokens.some(t => greekFold(t.t) === greekFold(query)), `${href} lacks ${query}`).toBe(true);
    }
    // The reference text was not fetched for these Greek-only searches' hits or indexes.
    expect(urls.filter(u => u.includes('/agamemnon/search/')).length).toBe(0);
    expect(urls.filter(u => u.includes('/agamemnon/ed/smyth-loeb/search/')).length).toBeGreaterThan(0);
  }, 60000);
});
