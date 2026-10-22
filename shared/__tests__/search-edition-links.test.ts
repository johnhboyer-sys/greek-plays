import { getWork } from '../lib/works';
// Plan 4.5 / P3 success 5: a search of an edition's Greek index links to
// `?ed=<edition>&loc=<ref>`, and the line the reader lands on (that ref, in that
// edition's book) holds the token searched. Needs a built Agamemnon:
//   cd pipeline && .venv/bin/python -m drama_pipeline all --work agamemnon
//   ... all --work agamemnon --edition smyth-loeb
// The built-data block skips itself when the build is absent (build/ is git-ignored);
// the fixture block after it always runs.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { greekFold } from '../lib/search';

const dist = resolve(process.cwd(), '../build/dist');
const built = existsSync(`${dist}/agamemnon/ed/smyth-loeb/search/form.json`) && existsSync(`${dist}/agamemnon/ed/smyth-loeb/book-01.json`);

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); history.replaceState({}, '', '/'); });

const QUERIES = ['καὶ', 'δὲ', 'γὰρ', 'θεοὺς', 'Ἄργος', 'πόλις', 'φρήν', 'ἄναξ', 'τέκνον', 'δόμος', 'χθονὸς', 'ἔπος'];

describe.skipIf(!built)('search hits from a BUILT edition index (skipped when build/dist lacks Smyth)', () => {
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
    // Each play's Smyth book, loaded on demand; a hit is checked against its own play's book.
    type Line = { ref?: string; tokens: { t: string }[] };
    const books = new Map<string, Map<string | undefined, Line> | null>();
    const linesOf = (play: string) => {
      if (!books.has(play)) {
        const f = `${dist}/${play}/ed/smyth-loeb/book-01.json`;
        books.set(play, existsSync(f)
          ? new Map((JSON.parse(readFileSync(f, 'utf8')).segments as { greek: Line[] }[]).flatMap(s => s.greek).map(l => [l.ref, l] as const))
          : null);
      }
      return books.get(play)!;
    };
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
    // A hit carries ed=smyth-loeb exactly when its play has Smyth's edition
    // (all seven Aeschylus plays do); any other play's hit carries none.
    // A play reads at /read/<author>/<play> (2026-10-20); the play is the last segment.
    const playOf = (href: string) => new URL(href, 'https://x.test').pathname.split('/').filter(Boolean).at(-1)!;
    for (const { href } of hits) {
      const hasSmyth = !!getWork(playOf(href))?.greekEditions?.some((e) => e.id === 'smyth-loeb');
      expect(new URL(href, 'https://x.test').searchParams.get('ed'), href).toBe(hasSmyth ? 'smyth-loeb' : null);
    }
    // Hits in plays whose Smyth book is built here; one in n, spread across every query and play.
    const own = hits.filter(h => linesOf(playOf(h.href)));
    const sample = own.filter((_, i) => i % Math.max(1, Math.floor(own.length / 100)) === 0).slice(0, 100);
    expect(own.length, `${own.length} Smyth hits of ${hits.length}`).toBeGreaterThanOrEqual(100);
    expect(sample).toHaveLength(100);
    for (const { query, href } of sample) {
      const url = new URL(href, 'https://x.test');
      expect(url.searchParams.get('ed'), href).toBe('smyth-loeb');
      expect(url.searchParams.get('view'), href).toBe('greek');
      const line = linesOf(playOf(href))!.get(url.searchParams.get('loc')!);
      expect(line, `no line ${url.searchParams.get('loc')} in the Smyth book: ${href}`).toBeDefined();
      expect(line!.tokens.some(t => greekFold(t.t) === greekFold(query)), `${href} lacks ${query}`).toBe(true);
    }
    // The reference text was not fetched for these Greek-only searches' hits or indexes.
    expect(urls.filter(u => u.includes('/agamemnon/search/')).length).toBe(0);
    expect(urls.filter(u => u.includes('/agamemnon/ed/smyth-loeb/search/')).length).toBeGreaterThan(0);
  }, 60000);
});
