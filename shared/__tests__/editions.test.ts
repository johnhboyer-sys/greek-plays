import { afterEach, describe, expect, it, vi } from 'vitest';
import { getWork } from '../lib/works';
import { changeEdition, loadEdition, type EditionState } from '../lib/edition-state';
import { editionBase, fetchBook, readerHref } from '../lib/data';
import { assignSpeakerSlots } from '../lib/speaker-colors';

const work = getWork('agamemnon')!;
afterEach(() => { vi.restoreAllMocks(); delete (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__; });

describe('edition data', () => {
  it('uses the data-root override and a distinct edition book cache', async () => {
    (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://data.test';
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      urls.push(String(url));
      return { ok: true, json: async () => ({ segments: [] }) } as Response;
    });
    expect(editionBase('agamemnon', 'smyth-loeb')).toBe('https://data.test/agamemnon/ed/smyth-loeb');
    await fetchBook('agamemnon', 1, 'smyth-loeb');
    await fetchBook('agamemnon', 1);
    expect(urls).toEqual(['https://data.test/agamemnon/ed/smyth-loeb/book-01.json', 'https://data.test/agamemnon/book-01.json']);
  });
  it('makes no edition requests on the reference path used with the flag off', async () => {
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      urls.push(String(url));
      return { ok: true, json: async () => ({}) } as Response;
    });
    await fetchBook('flag-off-fixture', 1);
    expect(urls.filter(url => url.includes('/ed/'))).toHaveLength(0);
  });
  it('builds a link with ed only when it differs from the translation default', () => {
    expect(readerHref('agamemnon', { loc: '1203', ed: 'smyth-loeb', trans: 'smyth' }))
      .toBe('/aeschylus/agamemnon?loc=1203&trans=smyth');
    expect(readerHref('agamemnon', { loc: '1203', ed: 'tlg', trans: 'smyth' }))
      .toBe('/aeschylus/agamemnon?loc=1203&trans=smyth&ed=tlg');
    expect(readerHref('agamemnon', { loc: '1203', ed: 'smyth-loeb' }))
      .toBe('/aeschylus/agamemnon?loc=1203');
  });
});

describe('edition state', () => {
  it.each([
    ['greek', { trans: 'morshead', view: 'greek', ed: 'smyth-loeb' }, { ed: 'smyth-loeb', trans: 'morshead', view: 'greek' }],
    ['compare', { trans: 'compare', view: 'both', ed: 'smyth-loeb' }, { ed: 'tlg', trans: 'compare', view: 'both' }],
    ['aligned both', { trans: 'smyth', view: 'both', ed: 'smyth-loeb' }, { ed: 'smyth-loeb', trans: 'smyth', view: 'both' }],
    ['unaligned English', { trans: 'morshead', view: 'english', ed: 'smyth-loeb' }, { ed: 'smyth-loeb', trans: 'smyth', view: 'english' }],
    ['reference link', { trans: 'smyth', view: 'both', loc: '1203' }, { ed: 'tlg', trans: 'smyth', view: 'both' }],
    ['default', { trans: 'smyth', view: 'both' }, { ed: 'smyth-loeb', trans: 'smyth', view: 'both' }],
  ] as const)('%s', (_label, input, expected) => {
    expect(loadEdition(work, input)).toEqual(expected);
  });
  it('follows translation and view changes', () => {
    const start: EditionState = { ed: 'smyth-loeb', trans: 'smyth', view: 'both' };
    expect(changeEdition(work, start, { trans: 'morshead' }).ed).toBe('tlg');
    expect(changeEdition(work, { ...start, view: 'greek' }, { view: 'both', trans: 'morshead' }).ed).toBe('tlg');
    expect(changeEdition(work, { ed: 'tlg', trans: 'smyth', view: 'greek' }, { view: 'english' }).ed).toBe('tlg');
  });
  it('keeps shared names in the play roster slot', () => {
    const reference = ['Watchman', 'Chorus', 'Clytaemestra', 'Herald', 'Agamemnon', 'Cassandra', 'Aegisthus'];
    const edition = ['Chorus', 'Clytaemestra', 'Agamemnon', 'Cassandra'];
    const slots = assignSpeakerSlots(reference);
    const expanded = assignSpeakerSlots([...reference, ...edition.filter(n => !reference.includes(n))]);
    for (const name of edition) expect(expanded.get(name)).toBe(slots.get(name));
  });
});
