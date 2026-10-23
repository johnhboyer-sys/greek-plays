import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getWork } from '../lib/works';
import { changeEdition, compareEdition, compareEditions, comparePair, defaultEdition, headEditionPick, loadEdition, type EditionState } from '../lib/edition-state';
import { editionBase, fetchBook, fetchConcordance, readerHref } from '../lib/data';
import { editionPlace, hasRef, invertConcordance } from '../lib/edition-place';
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
  it('keeps ed beside a loc unless it is tlg, since a bare loc reads in TLG numbering (plan 4.1 rule 4)', () => {
    expect(readerHref('agamemnon', { loc: '1203', ed: 'smyth-loeb', trans: 'smyth' }))
      .toBe('/read/aeschylus/agamemnon?loc=1203&trans=smyth&ed=smyth-loeb');
    expect(readerHref('agamemnon', { loc: '1203', ed: 'tlg', trans: 'smyth' }))
      .toBe('/read/aeschylus/agamemnon?loc=1203&trans=smyth');
    expect(readerHref('agamemnon', { loc: '1203', ed: 'smyth-loeb' }))
      .toBe('/read/aeschylus/agamemnon?loc=1203&ed=smyth-loeb');
  });

  it('without a loc, omits ed when it is the translation\'s own edition', () => {
    expect(readerHref('agamemnon', { ed: 'smyth-loeb', trans: 'smyth' })).toBe('/read/aeschylus/agamemnon?trans=smyth');
    expect(readerHref('agamemnon', { ed: 'tlg', trans: 'smyth' })).toBe('/read/aeschylus/agamemnon?trans=smyth&ed=tlg');
  });
});

describe('edition place', () => {
  const book = (...refs: string[]) => ({ book: 1, segments: refs.map(ref => ({
    id: ref, column: ref, greek: [{ n: Number(ref.replace(/\D/g, '')), ref, text: 'λόγος', tokens: [] }], english: null,
  })) }) as BookData;
  // The fixture edition's concordance: edition ref -> TLG ref or range, a lettered ref included.
  const fixture: Record<string, string> = JSON.parse(readFileSync(
    resolve(process.cwd(), '../fixtures/data/sample-work/ed/mini/concordance.json'), 'utf8'));
  it('lets the concordance win over the same printed ref: a shifted number is different text', () => {
    // Smyth 1203 is TLG 1202, and TLG also prints 1203 (other text): the concordance decides.
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1202', '1203'), { '1203': '1202' })).toBe('1202');
    expect(editionPlace('1202', 'tlg', 'smyth-loeb', book('1202', '1203'), {}, { '1203': '1202' })).toBe('1203');
    // A range value: the first ref the destination prints wins.
    expect(editionPlace('112', 'ed', 'tlg', book('111', '112', '113'), { '112': '111-112' })).toBe('111');
  });
  it('keeps a printed ref the concordance does not map', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1202', '1203'), { '1300': '1299' })).toBe('1203');
    expect(editionPlace('1203--2', 'tlg', 'smyth-loeb', book('1203'))).toBe('1203');
  });
  it('goes edition -> TLG through the concordance when the printed ref is absent', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1202', '1204'), { '1203': '1202' })).toBe('1202');
    expect(editionPlace('2a', 'mini', 'tlg', book('1', '2', '3', '4', '5', '6'), fixture)).toBe('3');
    expect(editionPlace('3', 'mini', 'tlg', book('1', '2', '4', '5', '6'), fixture)).toBe('4');
  });
  it('goes TLG -> edition by inverting the concordance, a range and a lettered ref included', () => {
    // Each book omits the TLG ref asked for, so the concordance decides.
    expect(editionPlace('3', 'tlg', 'mini', book('1', '2', '2a'), {}, fixture)).toBe('2a');
    expect(editionPlace('4', 'tlg', 'mini', book('2a', '3'), {}, fixture)).toBe('3');
    expect(editionPlace('5', 'tlg', 'mini', book('2a', '3'), {}, fixture)).toBe('3');
    expect(editionPlace('6', 'tlg', 'mini', book('2a', '3', '4'), {}, fixture)).toBe('4');
    expect(editionPlace('1202', 'tlg', 'smyth-loeb', book('1201', '1203'), {}, { '1203': '1202' })).toBe('1203');
  });
  it('takes the first edition line when several map to one TLG ref', () => {
    expect([...invertConcordance({ '10': '20', '10a': '20', '11': '21-22', '12': '22' })])
      .toEqual([['20', '10'], ['21', '11'], ['22', '11']]);
  });
  it('goes edition -> edition through TLG', () => {
    expect(editionPlace('2a', 'mini', 'other', book('3', '4'), fixture, { '4': '3' })).toBe('4');
  });
  it('uses the nearest lower ref when neither the ref nor the concordance answers', () => {
    expect(editionPlace('1203', 'smyth-loeb', 'tlg', book('1199', '1201', '1205'))).toBe('1201');
    expect(editionPlace('1203', 'tlg', 'smyth-loeb', book('1199', '1201', '1205'))).toBe('1201');
    expect(editionPlace('412a', 'mini', 'tlg', book('410', '412', '414'), {})).toBe('412');
    expect(editionPlace('1', 'tlg', 'mini', book('5', '6'), {}, fixture)).toBe('5');
  });
  it('finds a line inside a range the new edition prints as one', () => {
    expect(editionPlace('107', 'tlg', 'mini', book('105', '106-107', '108'))).toBe('106-107');
    expect(hasRef('107', book('106-107'))).toBe(true);
    expect(hasRef('109', book('106-107'))).toBe(false);
  });
  it('passes a null place through', () => {
    expect(editionPlace(null, 'tlg', 'mini', book('1'))).toBeNull();
  });
});

describe('edition copy citation', () => {
  const start = { column: '1203', line: null };
  it('leaves reference text and URL as they were', () => {
    const copy = editionCopyCitation('agamemnon', 'tlg', start, start, 1, 'morshead');
    expect(copy?.text).toBe('(Aesch. Ag. 1203)');
    expect(copy?.url).toBe('/read/aeschylus/agamemnon?loc=1203&trans=morshead');
    expect(editionCopyCitation('agamemnon', null, start, start, 1, 'morshead')).toEqual(copy);
  });
  it('names the editor and puts ed in the URL for a non-reference edition', () => {
    const copy = editionCopyCitation('agamemnon', 'smyth-loeb', start, start, 1, 'smyth');
    expect(copy?.text).toBe('(Aesch. Ag. 1203, Smyth 1926)');
    expect(copy?.url).toBe('/read/aeschylus/agamemnon?loc=1203&trans=smyth&ed=smyth-loeb');
  });

  it('names a two-editor edition by its short label, not a mangled surname', () => {
    const copy = editionCopyCitation('birds', 'hall-geldart-oct', { column: '100', line: null }, null);
    expect(copy?.text).toMatch(/, Hall & Geldart 1906\)$/);
  });
  it('names the editor for a range too', () => {
    const copy = editionCopyCitation('agamemnon', 'smyth-loeb', start, { column: '1210' }, 1, 'smyth');
    expect(copy?.text).toBe('(Aesch. Ag. 1203–1210, Smyth 1926)');
  });
});

describe('edition state', () => {
  it.each([
    ['greek', { trans: 'morshead', view: 'greek', ed: 'smyth-loeb' }, { ed: 'smyth-loeb', trans: 'morshead', view: 'greek' }],
    ['compare, no pair', { trans: 'compare', view: 'both', ed: 'smyth-loeb' }, { ed: 'tlg', trans: 'compare', view: 'both' }],
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

describe('a comparison\'s Greek text (John, 2026-10-23)', () => {
  // Eumenides: Smyth and Kosmos on Smyth's Loeb; Morshead and Johnston on the reference text.
  const eum = getWork('eumenides')!;
  const shared: [string, string] = ['smyth', 'kosmos'];
  const mixed: [string, string] = ['smyth', 'morshead'];
  it('offers the reference text and any edition both translations were made from', () => {
    expect(compareEditions(eum.greekEditions, shared)).toEqual(['tlg', 'smyth-loeb']);
    expect(compareEditions(eum.greekEditions, mixed)).toEqual(['tlg']);
    expect(compareEditions(eum.greekEditions, ['morshead', 'johnston'])).toEqual(['tlg']);
  });
  it('defaults to the shared edition, else the reference text', () => {
    expect(compareEdition(eum, shared)).toBe('smyth-loeb');
    expect(compareEdition(eum, mixed)).toBe('tlg');
    expect(defaultEdition(eum, 'compare', shared)).toBe('smyth-loeb');
    expect(defaultEdition(eum, 'kosmos')).toBe('smyth-loeb');
    // Hecuba: every translation on Murray's OCT, the reference text Diggle's.
    expect(compareEdition(getWork('hecuba')!, ['coleridge', 'way'])).toBe('murray-oct');
  });
  it.each([
    ['no ?ed=: the pair\'s default', { trans: 'compare', view: 'both', pair: shared }, { ed: 'smyth-loeb', trans: 'compare', view: 'both', pair: shared }],
    ['a bare ?loc= reads TLG', { trans: 'compare', view: 'both', pair: shared, loc: '100' }, { ed: 'tlg', trans: 'compare', view: 'both', pair: shared }],
    ['?ed=tlg is kept', { trans: 'compare', view: 'both', pair: shared, ed: 'tlg' }, { ed: 'tlg', trans: 'compare', view: 'both', pair: shared }],
    ['an offered ?ed= is kept', { trans: 'compare', view: 'english', pair: shared, ed: 'smyth-loeb', loc: '100' }, { ed: 'smyth-loeb', trans: 'compare', view: 'english', pair: shared }],
    ['an edition one side lacks: the link wins', { trans: 'compare', view: 'both', pair: mixed, ed: 'smyth-loeb' }, { ed: 'smyth-loeb', trans: 'smyth', view: 'both' }],
    ['the Greek view: a bare ?loc= reads TLG too', { trans: 'compare', view: 'greek', pair: shared, loc: '100' }, { ed: 'tlg', trans: 'compare', view: 'greek', pair: shared }],
    ['an unknown ?ed=', { trans: 'compare', view: 'both', pair: mixed, ed: 'nope' }, { ed: 'tlg', trans: 'compare', view: 'both', pair: mixed }],
  ] as const)('loads %s', (_label, input, expected) => {
    expect(loadEdition(eum, { ...input, pair: [...input.pair] as [string, string] })).toEqual(expected);
  });
  it('enters compare on the pair\'s default and keeps a picked text while the pair stands', () => {
    const single: EditionState = { ed: 'tlg', trans: 'morshead', view: 'both' };
    const entered = changeEdition(eum, single, { trans: 'compare', pair: shared });
    expect(entered).toEqual({ ed: 'smyth-loeb', trans: 'compare', view: 'both', pair: shared });
    const picked = changeEdition(eum, entered, { trans: 'compare', ed: 'tlg', pair: shared });
    expect(picked.ed).toBe('tlg');
    expect(changeEdition(eum, picked, { trans: 'compare', view: 'english', pair: shared }).ed).toBe('tlg');
    // A text one side lacks is refused; the comparison keeps its Greek.
    expect(changeEdition(eum, picked, { trans: 'compare', ed: 'smyth-loeb', pair: mixed }).ed).toBe('tlg');
    // A new pair takes its own default.
    expect(changeEdition(eum, picked, { trans: 'compare', pair: mixed }).ed).toBe('tlg');
    expect(changeEdition(eum, { ...picked, pair: mixed }, { trans: 'compare', pair: shared }).ed).toBe('smyth-loeb');
    // Leaving compare: the translation's own edition.
    expect(changeEdition(eum, entered, { trans: 'morshead', pair: shared })).toEqual({ ed: 'tlg', trans: 'morshead', view: 'both' });
    expect(changeEdition(eum, picked, { trans: 'kosmos', pair: shared }).ed).toBe('smyth-loeb');
  });
  it('restores the compare pair the reader restores', () => {
    expect(comparePair(eum)).toEqual(['smyth', 'morshead']);
    expect(comparePair(eum, ['kosmos', 'smyth'])).toEqual(['kosmos', 'smyth']);
    expect(comparePair(eum, ['gone', 'smyth'])).toEqual(['smyth', 'morshead']);
    expect(comparePair(eum, ['kosmos', 'kosmos'])).toEqual(['kosmos', 'smyth']);
  });
});

describe('the head\'s Greek text pick (ReaderHead.astro)', () => {
  const eds = [{ id: 'tlg', pairs: [] }, { id: 'smyth-loeb', pairs: ['smyth', 'kosmos'] }, { id: 'other', pairs: [] }];
  const at = (view: string, trans: string, pair: [string, string] = ['smyth', 'kosmos']) =>
    ({ view, trans, compareLeft: pair[0], compareRight: pair[1] });
  it('in the Greek view sets any edition', () => {
    expect(headEditionPick(at('greek', 'smyth'), eds[2]!, eds)).toEqual({ edition: 'other' });
  });
  it('in compare sets a text both translations stand beside, and nothing else', () => {
    expect(headEditionPick(at('both', 'compare'), eds[1]!, eds)).toEqual({ edition: 'smyth-loeb' });
    expect(headEditionPick(at('both', 'compare'), eds[0]!, eds)).toEqual({ edition: 'tlg' });
    expect(headEditionPick(at('both', 'compare', ['smyth', 'morshead']), eds[1]!, eds)).toBeNull();
  });
  it('in Both and English brings the edition\'s translation, or opens the Greek view', () => {
    expect(headEditionPick(at('both', 'morshead'), eds[1]!, eds)).toEqual({ trans: 'smyth' });
    expect(headEditionPick(at('english', 'morshead'), eds[2]!, eds)).toEqual({ view: 'greek', edition: 'other' });
  });
});

describe('edition place, concordance ranges', () => {
  const book = (...refs: string[]) => ({ book: 1, segments: refs.map(ref => ({
    id: ref, column: ref, greek: [{ n: Number(ref), ref, text: 'λόγος', tokens: [] }], english: null,
  })) }) as BookData;
  it('tries each ref of a range before falling back to the nearest lower', () => {
    // Edition line 20 answers TLG 112-113; the TLG book prints 113 but not 112.
    expect(editionPlace('20', 'mini', 'tlg', book('105', '113'), { '20': '112-113' })).toBe('113');
    // The target edition maps 113 (not 112) to its line 30.
    expect(editionPlace('20', 'mini', 'other', book('25', '30'), { '20': '112-113' }, { '30': '113' })).toBe('30');
  });
});
