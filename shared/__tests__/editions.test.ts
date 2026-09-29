import { afterEach, describe, expect, it, vi } from 'vitest';
import { getWork } from '../lib/works';
import { changeEdition, loadEdition, type EditionState } from '../lib/edition-state';
import { editionBase, fetchBook, fetchConcordance, readerHref } from '../lib/data';
import { editionPlace } from '../lib/edition-place';
import { editionCopyCitation } from '../lib/edition-citation';
import type { BookData } from '../lib/data';
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
    await fetchConcordance('flag-off-fixture', 'tlg');
    expect(urls.filter(url => url.includes('/ed/'))).toHaveLength(0);
    expect(urls.filter(url => url.includes('concordance'))).toHaveLength(0);
  });
  it('loads the concordance through the data root and caches it', async () => {
    (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ = 'https://data.test';
    const urls: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
      urls.push(String(url));
      return { ok: true, json: async () => ({ '1203': '1202' }) } as Response;
    });
    expect(await fetchConcordance('agamemnon', 'smyth-loeb')).toEqual({ '1203': '1202' });
    await fetchConcordance('agamemnon', 'smyth-loeb');
    expect(urls).toEqual(['https://data.test/agamemnon/ed/smyth-loeb/concordance.json']);
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

describe('edition place', () => {
  const book = (...refs: string[]) => ({ segments: refs.map(ref => ({
    id: ref, column: ref, greek: [{ n: Number(ref.replace(/\D/g, '')), ref, text: 'λόγος', tokens: [] }], english: null,
  })) }) as BookData;
  it('keeps a printed ref present in both editions', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1202', '1203'), { '1203': '1202' })).toBe('1203');
  });
  it('maps an edition ref to TLG when the printed ref is absent', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1202', '1204'), { '1203': '1202' })).toBe('1202');
  });
  it('inverts the concordance from TLG to an edition', () => {
    expect(editionPlace('1202', 'tlg', 'smyth-loeb', book('1201', '1203'), {}, { '1203': '1202' })).toBe('1203');
  });
  it('uses the nearest lower ref when neither direct nor mapped ref exists', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1199', '1201', '1205'))).toBe('1201');
    expect(editionPlace('1203', 'tlg', 'smyth-loeb', book('1199', '1201', '1205'))).toBe('1201');
  });
});

describe('edition copy citation', () => {
  const start = { column: '1203', line: null };
  it('leaves reference text as it was', () => {
    const copy = editionCopyCitation('agamemnon', 'tlg', start, start, 1, 'morshead');
    expect(copy?.text).toBe('(Aesch. Ag. 1203)');
    expect(copy?.url).toBe('/aeschylus/agamemnon?loc=1203&trans=morshead');
  });
  it('names the editor and includes ed in a non-reference URL', () => {
    const copy = editionCopyCitation('agamemnon', 'smyth-loeb', start, start, 1, 'smyth');
    expect(copy?.text).toBe('(Aesch. Ag. 1203 (Smyth))');
    expect(copy?.url).toBe('/aeschylus/agamemnon?loc=1203&trans=smyth&ed=smyth-loeb');
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
