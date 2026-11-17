// Codex review of the search port (16 Nov), the page's part, on the plays'
// own registry: editing a headword phrase drops its headwords (fix 2), an
// English hit keeps its segment where two segments print one ref (fix 3), and
// Near's lines unit takes 0 to 10 lines either side (fix 7).
import { fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Search from '../components/Search.svelte';
import type { BookData, GreekLine, Segment } from '../lib/data';
import type { SearchResult } from '../lib/search';
import { getWork } from '../lib/works';

const SEVEN = 'seven-against-thebes';
// Seven 810 as printed twice (citation.repeated_refs): 1:810 and 1:810.2.
const { fixture } = vi.hoisted(() => {
  const line = (n: number, text: string): GreekLine => ({ n, text, tokens: text.split(' ').map((t, i) => ({ t, o: i * 2, k: t })) });
  const seg = (id: string, column: string, english: string, ...greek: GreekLine[]): Segment => ({
    id, column, greek, english: { text: english, notes: [], markers: [] },
  });
  const fixture: BookData = {
    book: 1,
    segments: [
      seg('1:810', '810', 'Are they lying out there?', line(794, 'ἐκεῖθι κἦλθον')),
      seg('1:810.2', '810', 'Struck down in the dust.', line(796, 'κατεσποδημένοι ἀμφιλέκτως')),
    ],
  };
  return { fixture };
});

vi.mock('../lib/search', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/search')>();
  return {
    ...actual,
    search: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchCombo: vi.fn(async () => ({ results: [], failedWorks: [] })),
    searchPhraseVariants: vi.fn(),
    speakerRoster: vi.fn(async () => []),
    greekHitForms: vi.fn(async () => ({ byResult: new Map(), headwords: new Map(), failedWorks: [] })),
    greekHitGrammar: vi.fn(async () => ({ byResult: new Map(), failedWorks: [] })),
  };
});
vi.mock('../lib/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/data')>();
  return {
    ...actual,
    fetchBook: vi.fn(async () => fixture),
    fetchChapters: vi.fn(async () => ({ '1': [{ chapter: '810', column: '810', line: '794' }] })),
    fetchLemmaPickerShard: vi.fn(async () => ({})),
    fetchLemmaGlosses: vi.fn(async () => []),
  };
});

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => ({ ok: false, status: 404, json: async () => ({}) }) as Response);
  vi.spyOn(window, 'matchMedia').mockImplementation((media: string) => ({
    matches: media === '(min-width: 961px)', media, onchange: null, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false,
  }) as unknown as MediaQueryList);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, '', '/');
});

const text = (el: Element | null | undefined) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();
const lastCombo = async () => {
  const { searchCombo } = await import('../lib/search');
  return vi.mocked(searchCombo).mock.calls.at(-1)!;
};
async function arriveNear(qs: string) {
  window.history.replaceState(null, '', `/search?${qs}`);
  const page = render(Search);
  const { searchCombo } = await import('../lib/search');
  await vi.waitFor(() => expect(searchCombo).toHaveBeenCalled());
  await fireEvent.click(await screen.findByRole('button', { name: 'Change' }));
  await vi.waitFor(() => expect(screen.getByRole('group', { name: 'Proximity search' })).toBeInTheDocument());
  return page;
}
const editorSearch = () => document.querySelector<HTMLButtonElement>('button.prox-search')!;

describe('review fix 2: editing a headword phrase', () => {
  it('drops the headwords found for the old words, and searches the new words as typed', async () => {
    await arriveNear('c=q:qeos%20logos&c=f:kalos');
    expect((await lastCombo())[0][0]).toMatchObject({ kind: 'phrase', options: [['qeos'], ['logos']] });
    const term1 = document.querySelector<HTMLInputElement>('.combo-slot input.prox-field')!;
    await fireEvent.input(term1, { target: { value: 'ὦ Ζεῦ' } });
    await fireEvent.click(editorSearch());
    await vi.waitFor(async () => expect((await lastCombo())[0][0]).toEqual({ kind: 'phrase', terms: ['ὦ', 'Ζεῦ'], relation: 'near' }));
    expect(window.location.search).not.toContain('q:');
  });
});

describe('review fix 7: Near in lines', () => {
  it('offers 0 to 10 lines either side, keeps words and lines apart, and says it plainly', async () => {
    await arriveNear('c=f:a&c=f:b');
    const unit = screen.getByRole('combobox', { name: 'Distance measured in' }) as HTMLSelectElement;
    await fireEvent.change(unit, { target: { value: 'line' } });
    const lines = await screen.findByRole('spinbutton', { name: 'Distance in lines' }) as HTMLInputElement;
    expect(lines).toHaveAttribute('min', '0');
    expect(lines).toHaveAttribute('max', '10');
    expect(lines.value).toBe('0');
    await fireEvent.input(lines, { target: { value: '2' } });
    await fireEvent.click(editorSearch());
    await vi.waitFor(async () => expect((await lastCombo())[1]).toMatchObject({ unit: 'line', window: 2 }));
    expect(new URLSearchParams(window.location.search).get('cw')).toBe('2');
    await vi.waitFor(() => expect(text(document.querySelector('.prox-sum'))).toContain('within 2 lines'));
    // Back to words: the words keep their own 10.
    await fireEvent.click(await screen.findByRole('button', { name: 'Change' }));
    await fireEvent.change(screen.getByRole('combobox', { name: 'Distance measured in' }), { target: { value: 'words' } });
    expect((screen.getByRole('spinbutton', { name: 'Distance in words' }) as HTMLInputElement).value).toBe('10');
    // And back to lines: still 2. Then 0, the same line.
    await fireEvent.change(screen.getByRole('combobox', { name: 'Distance measured in' }), { target: { value: 'line' } });
    expect((screen.getByRole('spinbutton', { name: 'Distance in lines' }) as HTMLInputElement).value).toBe('2');
    await fireEvent.input(screen.getByRole('spinbutton', { name: 'Distance in lines' }), { target: { value: '0' } });
    await fireEvent.click(editorSearch());
    await vi.waitFor(async () => expect((await lastCombo())[1]).toMatchObject({ unit: 'line', window: 0 }));
    await vi.waitFor(() => expect(text(document.querySelector('.prox-sum'))).toContain('on the same line'));
  });
});

describe('review fix 3: an English hit where two segments print one ref', () => {
  it('opens the whole speech on its own segment', async () => {
    const primary = getWork(SEVEN)!.translations.find((t) => t.slot === 'english')!.id;
    const hit: SearchResult = {
      work: SEVEN, meta: { id: '1:810.2', book: 1, column: '810' }, grkMatch: false, engMatch: true, grkPositions: [],
      engHits: [{ translation: primary, positions: [4] }],
    };
    const { search } = await import('../lib/search');
    vi.mocked(search).mockResolvedValueOnce({ results: [hit], failedWorks: [] });
    window.history.replaceState(null, '', '/search?e=dust');
    const { container } = render(Search);
    const more = await screen.findByRole('button', { name: 'Show the whole speech' });
    const li = more.closest('li.instance')!;
    expect(text(li)).toContain('dust');
    await fireEvent.click(more);
    await vi.waitFor(() => expect(text(li.querySelector('.inst-snippet.greek'))).toContain('κατεσποδημένοι'));
    expect(text(li.querySelector('.inst-snippet.greek'))).not.toContain('ἐκεῖθι');
    expect(container.querySelectorAll('li.instance')).toHaveLength(1);
  });
});

describe('review fix 4: an old multiword lemma search on the page', () => {
  it('searches with its headword picks, keeps them in the address, and drops them when the words change', async () => {
    const { search } = await import('../lib/search');
    window.history.replaceState(null, '', '/search?g=logou%20qeous&m=lemma&lp=logos~qea');
    const { container } = render(Search);
    await vi.waitFor(() => expect(search).toHaveBeenCalled());
    expect(vi.mocked(search).mock.calls.at(-1)![11]).toEqual([['logos'], ['qea']]);
    expect(new URLSearchParams(window.location.search).get('lp')).toBe('logos~qea');
    const input = container.querySelector('#grk-input') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'logou qeou' } });
    await fireEvent.submit(container.querySelector('form.search-form')!);
    await vi.waitFor(() => expect(vi.mocked(search).mock.calls.at(-1)![0]).toBe('logou qeou'));
    expect(vi.mocked(search).mock.calls.at(-1)![11]).toBeUndefined();
    expect(window.location.search).not.toContain('lp=');
  });
  it('does not bring the picks back after a mode change, or after the words change and return', async () => {
    const { search } = await import('../lib/search');
    window.history.replaceState(null, '', '/search?g=logou%20qeous&m=lemma&lp=logos~qea');
    const { container } = render(Search);
    await vi.waitFor(() => expect(search).toHaveBeenCalled());
    const radio = (v: string) => container.querySelector(`input[name="matchmode"][value="${v}"]`) as HTMLInputElement;
    const run = async () => { const n = vi.mocked(search).mock.calls.length; await fireEvent.submit(container.querySelector('form.search-form')!); await vi.waitFor(() => expect(vi.mocked(search).mock.calls.length).toBeGreaterThan(n)); };
    await fireEvent.click(radio('form'));
    await run();
    await fireEvent.click(radio('lemma'));
    await run();
    expect(vi.mocked(search).mock.calls.at(-1)![11]).toBeUndefined();
    expect(window.location.search).not.toContain('lp=');
    // Words changed, searched, then the originals typed back.
    window.history.replaceState(null, '', '/search?g=logou%20qeous&m=lemma&lp=logos~qea');
    const input = container.querySelector('#grk-input') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'logou qeou' } });
    await run();
    await fireEvent.input(input, { target: { value: 'logou qeous' } });
    await run();
    expect(vi.mocked(search).mock.calls.at(-1)![11]).toBeUndefined();
    expect(window.location.search).not.toContain('lp=');
  });
});
