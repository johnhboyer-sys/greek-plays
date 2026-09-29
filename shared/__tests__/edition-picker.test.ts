import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ReaderHost from '../components/ReaderHost.svelte';
import Reader from '../components/Reader.svelte';
import { getWork } from '../lib/works';
import { changeEdition, type EditionState, type ReaderView } from '../lib/edition-state';
import type { BookData } from '../lib/data';

const line = (n: number, ref: string, text: string) => ({ n, ref, text, tokens: [] });
const book = (ref: string, text: string) => ({ book: 1, speakerRoster: ['Watchman'], segments: [
  { id: '1:1', column: '1', greek: [line(Number(ref), ref, text)], english: { text: 'English', notes: [], markers: [] } },
] }) as BookData;
const smyth = book('5', 'σμύθη');
const reference = book('10', 'πρῶτον');

const work = getWork('agamemnon')!;
const props = { work: 'agamemnon', bookNum: 1, bookData: smyth, serverEdition: 'smyth-loeb', speakerRoster: ['Watchman'], authorName: 'Aeschylus' };
const fetchByEdition = () => vi.spyOn(globalThis, 'fetch').mockImplementation(async url =>
  ({ ok: true, json: async () => String(url).includes('/ed/') ? smyth : reference }) as Response);
const pickers = (root: HTMLElement) => Array.from(root.querySelectorAll<HTMLSelectElement>('select.rc-ed-select'));

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); history.replaceState({}, '', '/'); });

describe('the Greek-only edition picker', () => {
  it('lists exactly the registry editions, reference first, labelled with each short', async () => {
    history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
    fetchByEdition();
    const page = render(ReaderHost, props);
    await waitFor(() => expect(pickers(page.container)).toHaveLength(1));
    const [picker] = pickers(page.container);
    const options = Array.from(picker.options).map(option => [option.value, option.textContent?.trim()]);
    expect(options).toEqual(work.greekEditions!.map(e => [e.id, e.short]));
    expect(work.greekEditions![0].id).toBe('tlg');
    // The phone layout's settings sidebar carries the same list.
    const side = page.container.querySelector('.settings-body .settings-trans select[aria-label="Greek text"]') as HTMLSelectElement;
    expect(Array.from(side.options).map(o => o.value)).toEqual(work.greekEditions!.map(e => e.id));
    expect(options.length).toBeGreaterThan(1);
  });

  it('is absent in Both and English views', async () => {
    history.replaceState({}, '', '/aeschylus/agamemnon?view=both');
    fetchByEdition();
    const page = render(ReaderHost, props);
    await waitFor(() => expect(page.container.querySelector('.greek-line')).not.toBeNull());
    expect(pickers(page.container)).toHaveLength(0);
  });

  it('is absent when the reader has no edition prop (flag off) and for a play with one text', () => {
    history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
    const eng = { book: 1, segments: [{ id: '1:1', column: '1', greek: [line(1, '1', 'λόγος')], english: null }] } as BookData;
    const off = render(Reader, { props: { work: 'agamemnon', bookNum: 1, bookData: eng, initialView: 'greek' } });
    expect(pickers(off.container)).toHaveLength(0);
    expect(getWork('alcestis')!.greekEditions).toBeUndefined();
    const single = render(Reader, { props: { work: 'alcestis', bookNum: 1, bookData: eng, edition: 'tlg', initialView: 'greek' } });
    expect(pickers(single.container)).toHaveLength(0);
  });

  it('a pick sets ?ed=, shows that edition\'s refs, and survives a reload', async () => {
    history.replaceState({}, '', '/aeschylus/agamemnon?view=greek');
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
      urls.push(String(url));
      return { ok: true, json: async () => String(url).includes('/ed/') ? smyth : reference } as Response;
    });
    const first = render(ReaderHost, props);
    await waitFor(() => expect(pickers(first.container)).toHaveLength(1));
    expect(first.container.textContent).toContain('σμύθη');
    expect(first.container.textContent).not.toContain('πρῶτον');
    // Smyth is the default pair's own edition: no ?ed= yet. Pick the reference.
    expect(new URL(location.href).searchParams.get('ed')).toBeNull();
    await fireEvent.change(pickers(first.container)[0], { target: { value: 'tlg' } });
    await waitFor(() => expect(first.container.textContent).toContain('πρῶτον'));
    expect(first.container.textContent).not.toContain('σμύθη');
    expect(new URL(location.href).searchParams.get('ed')).toBe('tlg');
    expect(pickers(first.container)[0].value).toBe('tlg');
    first.unmount();
    // Reload: a fresh mount at the same URL, the server having rendered the default pair.
    const second = render(ReaderHost, props);
    await waitFor(() => expect(second.container.textContent).toContain('πρῶτον'));
    expect(second.container.textContent).not.toContain('σμύθη');
    await waitFor(() => expect(pickers(second.container)).toHaveLength(1));
    expect(pickers(second.container)[0].value).toBe('tlg');
    expect(new URL(location.href).searchParams.get('ed')).toBe('tlg');
    // Back to Smyth: ?ed= goes (it is the pair's own edition again).
    await fireEvent.change(pickers(second.container)[0], { target: { value: 'smyth-loeb' } });
    await waitFor(() => expect(second.container.textContent).toContain('σμύθη'));
    expect(new URL(location.href).searchParams.get('ed')).toBeNull();
  });

  it('?ed=X in Greek view renders X\'s refs', async () => {
    history.replaceState({}, '', '/aeschylus/agamemnon?view=greek&ed=tlg');
    fetchByEdition();
    const page = render(ReaderHost, props);
    await waitFor(() => expect(page.container.textContent).toContain('πρῶτον'));
    const gutters = Array.from(page.container.querySelectorAll('.greek-line .line-num')).map(n => n.textContent?.trim());
    expect(gutters).toContain('10');
    expect(gutters).not.toContain('5');
  });
});

describe('Greek to Both or English (plan 4.1)', () => {
  // Agamemnon: tlg and smyth-loeb; morshead is a reference-edition translation, smyth's own edition is smyth-loeb.
  const from = (ed: string, trans: string): EditionState => ({ ed, trans, view: 'greek' });
  // Reader always sends its translation with a view change.
  const toView = (state: EditionState, view: ReaderView, trans = state.trans) => changeEdition(work, state, { trans, view });
  it.each([
    // [label, greek-view state, view after, expected ed, expected trans]
    ['aligned via tlg: keeps the reference for any translation', from('tlg', 'smyth'), 'both', 'tlg', 'smyth'],
    ['aligned via tlg, English', from('tlg', 'morshead'), 'english', 'tlg', 'morshead'],
    ['aligned to its own edition: keeps it', from('smyth-loeb', 'smyth'), 'both', 'smyth-loeb', 'smyth'],
    ['unaligned: the translation\'s own edition wins', from('smyth-loeb', 'morshead'), 'both', 'tlg', 'morshead'],
    ['unaligned, English', from('smyth-loeb', 'morshead'), 'english', 'tlg', 'morshead'],
    ['compare is always the reference', from('smyth-loeb', 'compare'), 'both', 'tlg', 'compare'],
  ] as const)('%s', (_label, state, view, ed, trans) => {
    expect(toView(state, view)).toEqual({ ed, trans, view });
  });
  it('a Greek-view pick sets ed, even beside compare', () => {
    expect(changeEdition(work, from('tlg', 'smyth'), { trans: 'smyth', view: 'greek', ed: 'smyth-loeb' }))
      .toEqual({ ed: 'smyth-loeb', trans: 'smyth', view: 'greek' });
    expect(changeEdition(work, from('tlg', 'compare'), { trans: 'compare', view: 'greek', ed: 'smyth-loeb' }).ed).toBe('smyth-loeb');
  });
  it('picking a different translation in Both view still follows that translation\'s edition', () => {
    const both: EditionState = { ed: 'smyth-loeb', trans: 'smyth', view: 'both' };
    expect(changeEdition(work, both, { trans: 'morshead', view: 'both' }).ed).toBe('tlg');
    expect(changeEdition(work, { ed: 'tlg', trans: 'morshead', view: 'both' }, { trans: 'smyth', view: 'both' }).ed).toBe('smyth-loeb');
  });
});
