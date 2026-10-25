import { expect, it } from 'vitest';
import { decodeSearchUrl, encodeSearchUrl, emptyUrlSearch, hasSearch, type UrlSearch } from '../lib/search-url';
const works = ['A', 'B', 'C'];
it('keeps defaults aligned with the search form', () => {
  const state = emptyUrlSearch(works);
  expect(state.matchMode).toBe('form'); expect(state.engForms).toBe(true);
  expect(state.ed).toBe('tlg'); expect(hasSearch(state)).toBe(false);
  expect(encodeSearchUrl(state, works)).toBe('');
});
it.each(['g=λόγος', 'e=word', 'q=λόγος', 'q=word', 'q=lo%2Fgos'])('reads the existing handoff %s', query => {
  expect(hasSearch(decodeSearchUrl(query, works))).toBe(true);
});
it('does not let q replace explicit g or e, even when empty', () => {
  expect(hasSearch(decodeSearchUrl('g=&q=word', works))).toBe(false);
});
it('round-trips the full state', () => {
  const state: UrlSearch = { ...emptyUrlSearch(works), grk: 'λόγος', eng: 'word', grkMode: 'phrase', engMode: 'any', matchMode: 'lemma', accent: true,
    langOp: 'or', engForms: true, works: ['B'], ed: 'alt', lemmaPick: [['logos', 'logon'], []],
    near: { kind: 'grammatical', query: { case: 'nom' }, relation: 'after', window: 13, unit: 'line', ordered: true },
    shape: { mood: 'opt' }, engNear: { term: 'child', relation: 'before', window: 8 } };
  expect(decodeSearchUrl(encodeSearchUrl(state, works), works)).toEqual(state);
});
it('writes English "only as typed" and reads it back', () => {
  const query = encodeSearchUrl({ ...emptyUrlSearch(works), eng: 'man', engForms: false }, works);
  expect(query).toBe('e=man&ef=0');
  expect(decodeSearchUrl(query, works).engForms).toBe(false);
});
it('writes Near, picks and English near as short readable parameters', () => {
  const state: UrlSearch = { ...emptyUrlSearch(works), grk: 'μή', eng: 'sword', lemmaPick: [['polis'], ['qeos', 'qea']],
    near: { kind: 'grammatical', query: { mood: 'opt' }, relation: 'after', window: 1, unit: 'words', ordered: false },
    engNear: { term: 'hand', relation: 'near', window: 5 } };
  const query = encodeSearchUrl(state, works);
  expect(decodeURIComponent(query)).toBe('g=μή&e=sword&lp=polis~qeos.qea&n=g&ng=mood.opt&nr=a&nw=1&en=hand&enw=5');
  expect(query).not.toMatch(/%7B|%22/);   // no JSON
  expect(decodeSearchUrl(query, works)).toEqual(state);
});
it('keeps the typed word of a headword Near term', () => {
  const state: UrlSearch = { ...emptyUrlSearch(works), grk: 'ὦ', nearText: 'τέκνα',
    near: { kind: 'lemma', terms: ['teknon'], relation: 'near', window: 10, unit: 'line', ordered: true } };
  const back = decodeSearchUrl(encodeSearchUrl(state, works), works);
  expect(back.nearText).toBe('τέκνα');
  expect(back.near).toMatchObject({ kind: 'lemma', unit: 'line', ordered: true });
});
it('omits all works and the reference edition', () => {
  const query = encodeSearchUrl({ ...emptyUrlSearch(works), grk: 'logos' }, works);
  expect(query).toBe('g=logos');
});
it.each([[], ['A'], ['A', 'B'], ['A', 'B', 'C']].map(selected => [selected]))('round-trips selected works %j', selected => {
  const state = { ...emptyUrlSearch(works), eng: 'word', works: selected };
  expect(decodeSearchUrl(encodeSearchUrl(state, works), works).works).toEqual(selected);
});
it('supports an exclusion list and filters unknown work ids', () => {
  expect(decodeSearchUrl('g=x&w=-B,unknown', works).works).toEqual(['A', 'C']);
  expect(decodeSearchUrl('g=x&w=B,unknown', works).works).toEqual(['B']);
});
it('ignores junk values and malformed JSON', () => {
  expect(decodeSearchUrl('g=x&gm=no&em=no&m=no&acc=yes&op=no&ed=..%2Fx&lemmaPick=bad&near=[]&shape=1&engNear={}', works)).toEqual({ ...emptyUrlSearch(works), grk: 'x' });
});
it('clamps windows and drops invalid values', () => {
  const p = new URLSearchParams({ g: 'x', n: 'f', nt: 'x', nw: '999', nr: 'junk', nu: 'chapter', no: 'yes',
    en: 'word', enw: '-3', sh: 'case.nom~bad~bad.key.x~<b>.x', lp: "logos.LOGOS.1~" });
  const state = decodeSearchUrl(p, works);
  expect(state.near).toEqual({ kind: 'form', terms: ['x'], window: 50, relation: 'near', unit: 'words', ordered: false });
  expect(state.engNear?.window).toBe(1); expect(state.shape).toEqual({ case: 'nom' });
  expect(state.lemmaPick).toEqual([['logos'], []]);
  expect(decodeSearchUrl('g=x&n=zz&nt=y', works).near).toBeUndefined();
  expect(decodeSearchUrl('g=x&n=g', works).near).toBeUndefined();
  expect(decodeSearchUrl('g=x&n=constructor&nt=y', works).near).toBeUndefined();
  expect(decodeSearchUrl('g=x&n=f&nt=y&nr=constructor', works).near?.relation).toBe('near');
  expect(decodeSearchUrl('e=x&en=y&enr=__proto__', works).engNear?.relation).toBe('near');
});
it('counts a shape-only query as a search', () => {
  const state = { ...emptyUrlSearch(works), shape: { mood: 'opt' } };
  expect(hasSearch(state)).toBe(true);
  expect(decodeSearchUrl(encodeSearchUrl(state, works), works)).toEqual(state);
});
it('round-trips further Near terms, each with its own kind and relation', () => {
  const state: UrlSearch = { ...emptyUrlSearch(works), grk: 'ὦ',
    near: { kind: 'form', terms: ['τέκνον'], relation: 'after', window: 3, unit: 'words', ordered: true },
    nearMore: [{ kind: 'grammatical', query: { case: 'voc' }, relation: 'near' }, { kind: 'lemma', terms: ['qeos'], relation: 'before' }],
    nearMoreText: ['', 'θεῶν'] };
  const query = encodeSearchUrl(state, works);
  expect(decodeURIComponent(query)).toBe('g=ὦ&n=f&nt=τέκνον&nr=a&nw=3&no=1&n2=g&ng2=case.voc&n3=l&nt3=θεῶν&nr3=b');
  const back = decodeSearchUrl(query, works);
  expect(back.nearMore).toEqual([{ kind: 'grammatical', query: { case: 'voc' }, relation: 'near' }, { kind: 'lemma', terms: ['θεῶν'], relation: 'before' }]);
  expect(back.nearMoreText).toEqual(['', 'θεῶν']);
  expect(decodeSearchUrl('g=x&n2=f&nt2=y', works).nearMore).toBeUndefined();   // no first term, no more
});
