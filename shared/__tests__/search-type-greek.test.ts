// "Type Greek": the Beta Code chart in a dialog over the search, ported from
// the Aristotle reader's search (its "⌨ Type Greek" button and "Beta Code"
// hint link, shared/components/Search.svelte there). The chart must tell the
// truth: every Beta Code key and example it prints folds to the same search
// key as the Greek it shows, and a Beta Code query finds what the Greek finds.
// "β Beta Code": the live toggle ported from Grammata's /words box
// (grammar-site src/pages/words.astro, src/lib/betacode.ts liveGreek; the
// liveGreek cases below are Grammata's tests/betacode.test.ts).
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Search from '../components/Search.svelte';
import { greekFold } from '../lib/search';
import { BETA_LETTERS, BETA_MARKS, BETA_EXAMPLES } from '../lib/beta-chart';
import { liveGreek } from '../lib/betacode';

afterEach(() => { vi.restoreAllMocks(); });

describe('Beta Code typed in the Greek box folds as the Greek does', () => {
  it.each([
    ['a)reth/', 'ἀρετή'],             // smooth breathing, acute
    ['h(donh/', 'ἡδονή'],             // rough breathing
    ['lo/gos', 'λόγος'],              // final sigma from s
    ['sofi/a', 'σοφία'],              // medial sigma from s
    ['th=|', 'τῇ'],                   // circumflex, iota subscript
    ['to\\n', 'τὸν'],                 // grave
    ['a)i+/ssw', 'ἀΐσσω'],            // diaeresis
    ['*)aga/memnwn', 'Ἀγαμέμνων'],    // capital, marks between * and letter
    ['*(/a|dhs', 'ᾍδης'],             // capital with iota subscript
  ])('%s = %s', (beta, greek) => {
    expect(greekFold(beta)).toBe(greekFold(greek));
    expect(greekFold(beta)).not.toBe('');
  });

  it('every letter in the chart folds to its Greek', () => {
    for (const L of BETA_LETTERS) {
      for (const g of L.greek.split(' / ')) expect(greekFold(L.beta), L.name).toBe(greekFold(g));
    }
  });

  it('every mark example and word example in the chart folds to its Greek', () => {
    for (const M of BETA_MARKS) {
      const [beta, greek] = M.example.split(' → ');
      expect(greekFold(beta), M.name).toBe(greekFold(greek));
    }
    for (const E of BETA_EXAMPLES.filter((e) => !e.beta.includes('*'))) {
      expect(greekFold(E.beta), E.beta).toBe(greekFold(E.greek));
    }
  });
});

describe('the search box', () => {
  const book = { book: 1, segments: [{ id: '1:1', column: '1',
    greek: [{ n: 1, ref: '1', text: 'λόγος', tokens: [{ t: 'λόγος', o: 0, k: 'lo/gos' }] }], english: null }] };
  const files: Record<string, unknown> = {
    '/agamemnon/search/meta.json': [{ id: '1:1', book: 1, column: '1', head: 'λόγος', tokens: 'logos', english_head: '' }],
    '/agamemnon/search/form.json': { logos: [[0, 0]] },
    '/agamemnon/book-01.json': book,
    '/agamemnon/chapters.json': {},
  };

  it('a Beta Code query with accents finds the Greek hit', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const hit = files[String(input).replace(/^.*?\/data/, '')];
      return hit
        ? { ok: true, status: 200, json: async () => hit } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    const page = render(Search);
    await fireEvent.input(page.container.querySelector('#grk-input')!, { target: { value: 'lo/gos' } });
    await fireEvent.submit(page.container.querySelector('form.search-form')!);
    await waitFor(() => expect(page.container.querySelectorAll('a.inst-ref').length).toBe(1), { timeout: 5000 });
  });
});

describe('Type Greek dialog', () => {
  const dialog = () => document.querySelector('[role="dialog"][aria-label="How to type Greek"]') as HTMLElement | null;

  it('is closed until asked for', () => {
    render(Search);
    expect(dialog()).toBeNull();
  });

  it('Type Greek opens the chart, focused, and Escape closes it and returns focus', async () => {
    const page = render(Search);
    const btn = page.getByRole('button', { name: 'Type Greek' });
    btn.focus();
    await fireEvent.click(btn);
    await waitFor(() => expect(dialog()).not.toBeNull());
    expect(document.activeElement).toBe(dialog());
    expect(dialog()!.querySelectorAll('.beta-grid li').length).toBe(BETA_LETTERS.length);
    expect(dialog()!.textContent).toContain('ἀρετή');
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(dialog()).toBeNull();
    expect(document.activeElement).toBe(btn);
  });

  it('the Beta Code hint opens it too; a click inside keeps it, the backdrop and × close it', async () => {
    const page = render(Search);
    await fireEvent.click(page.getByRole('button', { name: 'Beta Code' }));
    await waitFor(() => expect(dialog()).not.toBeNull());
    await fireEvent.click(dialog()!.querySelector('h2')!);
    expect(dialog()).not.toBeNull();
    await fireEvent.click(document.querySelector('.help-backdrop')!);
    expect(dialog()).toBeNull();

    await fireEvent.click(page.getByRole('button', { name: 'Type Greek' }));
    await waitFor(() => expect(dialog()).not.toBeNull());
    await fireEvent.click(page.getByRole('button', { name: 'Close' }));
    expect(dialog()).toBeNull();
  });

  it('Tab stays inside the dialog', async () => {
    const page = render(Search);
    await fireEvent.click(page.getByRole('button', { name: 'Type Greek' }));
    await waitFor(() => expect(dialog()).not.toBeNull());
    const close = page.getByRole('button', { name: 'Close' });
    const link = dialog()!.querySelector('a.ln') as HTMLElement;
    link.focus();
    await fireEvent.keyDown(window, { key: 'Tab' });
    expect(document.activeElement).toBe(close);
    await fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(link);
  });
});

describe('liveGreek (Grammata)', () => {
  it('TypeGreek conventions', () => {
    expect(liveGreek('lo/gos')).toBe('λόγος');
    expect(liveGreek('logosde')).toBe('λογοσδε');      // sigma flips back mid-word
    expect(liveGreek('Swkra/ths')).toBe('Σωκράτης');   // Shift capitals
    expect(liveGreek('qeo/j')).toBe('θεός');           // j is an explicit sigma
    expect(liveGreek('o(/ti')).toBe('ὅτι');
    expect(liveGreek('tw=|')).toBe('τῷ');              // circumflex, iota subscript
    expect(liveGreek('proi+')).toBe('προϊ');           // diaeresis
    expect(liveGreek('*(hra')).toBe('Ἡρα');            // '*' still makes a capital
    expect(liveGreek('*(/a|dhs')).toBe('ᾍδης');        // capital with iota subscript stays one letter
    expect(liveGreek('to\\n')).toBe('τὸν');            // grave
  });

  it('marks compose in any typed order', () => {
    expect(liveGreek('a)/')).toBe('ἄ');
    expect(liveGreek('a/)')).toBe('ἄ');
    expect(liveGreek('i/+')).toBe('ΐ');
    expect(liveGreek('i+/')).toBe('ΐ');
    expect(liveGreek('w=)|')).toBe('ᾦ');
    expect(liveGreek('w)=|')).toBe('ᾦ');
  });

  it('is idempotent on its own output', () => {
    for (const input of ['lo/gos', '/*ab', '*(hra', 'a *', 'tw=| kai\\', 'logos ', "d'", 'fron*']) {
      const once = liveGreek(input);
      expect(liveGreek(once), input).toBe(once);
    }
  });

  it('leaves unfinished business as typed; marks before * wait for the capital', () => {
    expect(liveGreek('/*ab')).toBe('Άβ');
    expect(liveGreek('*(')).toBe('*(');
    expect(liveGreek('/')).toBe('/');
  });

  it('re-normalizes Greek already in the box mixed with new ASCII', () => {
    expect(liveGreek('λόγοσ')).toBe('λόγος');
    expect(liveGreek('λο/gos')).toBe('λόγος');
  });

  it('keeps the search wildcard and the apostrophe the search folds', () => {
    expect(liveGreek('fron*')).toBe('φρον*');
    expect(liveGreek("d'")).toBe("δ'");
    for (const q of ['fron*', "d' a)/n", 'lo/gos kai\\', '*)aga/memnwn']) {
      expect(greekFold(liveGreek(q)), q).toBe(greekFold(q));
    }
  });
});

describe('β Beta Code toggle', () => {
  const toggle = (page: { container: HTMLElement }) => page.container.querySelector('button.tog') as HTMLButtonElement;
  const box = (page: { container: HTMLElement }) => page.container.querySelector('#grk-input') as HTMLInputElement;

  async function type(el: HTMLInputElement, value: string, caret = value.length) {
    el.value = value;
    el.setSelectionRange(caret, caret);
    await fireEvent.input(el);
  }

  it('starts off, and off it leaves Beta Code as typed', async () => {
    const page = render(Search);
    expect(toggle(page).getAttribute('aria-pressed')).toBe('false');
    await type(box(page), 'lo/gos');
    expect(box(page).value).toBe('lo/gos');
  });

  it('turned on, converts what is in the box and focuses it; typing then turns Greek', async () => {
    const page = render(Search);
    await type(box(page), 'lo/gos');
    await fireEvent.click(toggle(page));
    expect(toggle(page).getAttribute('aria-pressed')).toBe('true');
    expect(box(page).value).toBe('λόγος');
    expect(document.activeElement).toBe(box(page));
    await type(box(page), 'λόγος a)reth/');
    expect(box(page).value).toBe('λόγος ἀρετή');
    await fireEvent.click(toggle(page));
    await type(box(page), 'λόγος ἀρετή kai');
    expect(box(page).value).toBe('λόγος ἀρετή kai');
  });

  it('keeps the caret where it was when an earlier word changes', async () => {
    const page = render(Search);
    await fireEvent.click(toggle(page));
    // A mark typed after the first word's ο, the caret right after it.
    await type(box(page), 'λο/γος καί', 3);
    expect(box(page).value).toBe('λόγος καί');
    expect(box(page).selectionStart).toBe(2);
  });

  it('a query typed with it on searches as Greek', async () => {
    const book = { book: 1, segments: [{ id: '1:1', column: '1',
      greek: [{ n: 1, ref: '1', text: 'λόγος', tokens: [{ t: 'λόγος', o: 0, k: 'lo/gos' }] }], english: null }] };
    const files: Record<string, unknown> = {
      '/agamemnon/search/meta.json': [{ id: '1:1', book: 1, column: '1', head: 'λόγος', tokens: 'logos', english_head: '' }],
      '/agamemnon/search/form.json': { logos: [[0, 0]] },
      '/agamemnon/book-01.json': book,
      '/agamemnon/chapters.json': {},
    };
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const hit = files[String(input).replace(/^.*?\/data/, '')];
      return hit
        ? { ok: true, status: 200, json: async () => hit } as Response
        : { ok: false, status: 404, json: async () => ({}) } as Response;
    });
    const page = render(Search);
    await fireEvent.click(toggle(page));
    await type(box(page), 'lo/gos');
    expect(box(page).value).toBe('λόγος');
    await fireEvent.submit(page.container.querySelector('form.search-form')!);
    await waitFor(() => expect(page.container.querySelectorAll('a.inst-ref').length).toBe(1), { timeout: 5000 });
  });
});
