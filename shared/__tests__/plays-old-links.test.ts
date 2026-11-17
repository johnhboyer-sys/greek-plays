import { afterEach, describe, expect, it, vi } from 'vitest';
import { decodeSearchUrl, encodeSearchUrl, emptyUrlSearch, hasSearch, resolveUrlLemmas, type UrlComboSlot, type UrlSearch } from '../lib/search-url';

// The plays' addresses on the ported search (search port, lane 2, decision
// 3): links written before the port keep opening as the search they were,
// and the new address carries what the plays add (English beside a
// proximity search, English near, lines either side, headword phrases).
// Ported from legacy/search-url.test.ts.
const works = ['A', 'B', 'C'];
const decode = (q: string) => decodeSearchUrl(q, works);
const slot = (over: Partial<UrlComboSlot>): UrlComboSlot =>
  ({ relation: 'near', text: '', picked: [], grammar: {}, ...over }) as UrlComboSlot;

describe('the plays\' old addresses', () => {
  it.each(['g=λόγος', 'e=word', 'q=λόγος', 'q=word', 'q=lo%2Fgos'])('reads the existing handoff %s', query => {
    expect(hasSearch(decode(query))).toBe(true);
  });

  it('does not let q replace explicit g or e, even when empty', () => {
    expect(hasSearch(decode('g=&q=word'))).toBe(false);
  });

  it('opens a Near link as a proximity search, its English beside it, joined by "and"', () => {
    const s = decode(`g=${encodeURIComponent('μή')}&e=sword&lp=polis~qeos.qea&n=g&ng=mood.opt&nr=a&nw=1&en=hand&enw=5`);
    // No m: the old box matched forms, so the first term is the form μή.
    expect(s.combo).toEqual({
      slots: [slot({ kind: 'form', text: 'μή' }), slot({ kind: 'grammatical', relation: 'after', grammar: { mood: 'opt' } })],
      window: 1, unit: 'words', ordered: false, crossChapter: true,
    });
    expect(s.grk).toBe('');
    expect(s.eng).toBe('sword');
    expect(s.langOp).toBe('and');
    expect(s.engNear).toEqual({ term: 'hand', relation: 'near', window: 5 });
  });

  it('opens further Near terms, each with its own kind and relation, In this order with three', () => {
    const s = decode(`g=${encodeURIComponent('ὦ')}&n=f&nt=${encodeURIComponent('τέκνον')}&nr=a&nw=3&no=1&n2=g&ng2=case.voc&n3=l&nt3=${encodeURIComponent('θεῶν')}&nr3=b`);
    expect(s.combo?.slots).toEqual([
      slot({ kind: 'form', text: 'ὦ' }),
      slot({ kind: 'form', relation: 'after', text: 'τέκνον' }),
      slot({ kind: 'grammatical', grammar: { case: 'voc' } }),
      slot({ kind: 'lemma', relation: 'before', text: 'θεῶν', resolve: true }),
    ]);
    expect(s.combo).toMatchObject({ window: 3, unit: 'words', ordered: true });
    // A further term needs a first.
    expect(decode('g=x&n2=f&nt2=y').combo).toBeNull();
  });

  it('reads In this order only with three terms, as the old page did', () => {
    expect(decode('g=x&n=f&nt=y&no=1').combo?.ordered).toBe(false);
  });

  it('keeps the typed word of a headword Near term, in lines either side', () => {
    const s = decode(`g=${encodeURIComponent('ὦ')}&n=l&nt=${encodeURIComponent('τέκνα')}&nu=l&nw=10&no=1`);
    expect(s.combo?.slots[1]).toEqual(slot({ kind: 'lemma', text: 'τέκνα', resolve: true }));
    expect(s.combo).toMatchObject({ unit: 'line', window: 10 });
    // Its ticked headwords, where the link names them.
    expect(decode('g=x&n=l&nt=y&nf=teknon.teknos').combo?.slots[1]).toEqual(slot({ kind: 'lemma', text: 'y', picked: ['teknon', 'teknos'] }));
    // Lines: 0 (the same line) by default.
    expect(decode('g=x&n=f&nt=y&nu=l').combo).toMatchObject({ unit: 'line', window: 0 });
  });

  it('opens with 10 words where the link names no distance', () => {
    expect(decode('g=x&n=f&nt=y').combo?.window).toBe(10);
  });

  it('reads the Greek box by headword with m=lemma, a phrase by each word\'s headwords', () => {
    const one = decode('g=dikh&m=lemma&n=l&nt=qeos');
    expect(one.combo?.slots[0]).toEqual(slot({ kind: 'lemma', text: 'dikh', resolve: true }));
    const ticked = decode('g=dikh&m=lemma&lp=dikh&n=f&nt=qeos');
    expect(ticked.combo?.slots[0]).toEqual(slot({ kind: 'lemma', text: 'dikh', picked: ['dikh'] }));
    const phrase = decode('g=qeous logos&m=lemma&lp=qeos~&n=f&nt=kalos&nr=b');
    expect(phrase.combo?.slots[0]).toEqual(slot({ kind: 'phrase', text: 'qeous logos', options: [['qeos'], []] }));
    // In form mode a phrase is matched as written.
    expect(decode('g=qeous logos&n=f&nt=kalos').combo?.slots[0]).toEqual(slot({ kind: 'phrase', text: 'qeous logos' }));
  });

  it('clamps windows and drops invalid values', () => {
    const p = new URLSearchParams({ g: 'x', e: 'word', n: 'f', nt: 'x', nw: '999', nr: 'junk', nu: 'chapter', no: 'yes',
      en: 'word', enw: '-3', sh: 'case.nom~bad~bad.key.x~<b>.x', lp: 'logos.LOGOS.1~' });
    const s = decode(p.toString());
    expect(s.combo).toEqual({ slots: [slot({ kind: 'form', text: 'x' }), slot({ kind: 'form', text: 'x' })], window: 50, unit: 'words', ordered: false, crossChapter: true });
    expect(s.engNear?.window).toBe(1);
    expect(decode('g=x&n=zz&nt=y').combo).toBeNull();
    expect(decode('g=x&n=g').combo).toBeNull();
    expect(decode('g=x&n=constructor&nt=y').combo).toBeNull();
    expect(decode('g=x&n=f&nt=y&nr=constructor').combo?.slots[1].relation).toBe('near');
    expect(decode('e=x&en=y&enr=__proto__').engNear?.relation).toBe('near');
  });

  it('opens a grammar term alone as one', () => {
    const s = decode('sh=mood.opt~bad');
    expect(s.combo?.slots).toEqual([slot({ kind: 'grammatical', grammar: { mood: 'opt' } })]);
    expect(hasSearch(s)).toBe(true);
  });

  it('opens one typed word with its headwords ticked as the dictionary-word search', () => {
    const s = decode('g=logou&m=lemma&lp=logos.logon');
    expect(s.lemmas).toEqual(['logos', 'logon']);
    expect(s.grk).toBe('');
  });

  it('reads an old Greek and English link with no op as "and", with op=or as "and/or"', () => {
    expect(decode('g=x&e=y').langOp).toBe('and');
    expect(decode('g=x&e=y&op=or').langOp).toBe('or');
    expect(decode('g=x&e=y&n=f&nt=z').langOp).toBe('and');
  });

  it('keeps the edition', () => {
    expect(decode('g=x&ed=murray-oct').ed).toBe('murray-oct');
    expect(decode('g=x&ed=tlg').ed).toBeNull();
  });

  // Review fix 6: a Near search, and an English one, kept their edition.
  it('keeps the edition on every search it was set on, Near and English included', () => {
    for (const query of [`g=${encodeURIComponent('δίκη')}&n=f&nt=${encodeURIComponent('θεός')}&ed=smyth-loeb`,
      'c=f:a&c=f:b&e=word&ed=smyth-loeb', 'e=word&ed=smyth-loeb', 'g=x&e=word&ed=smyth-loeb']) {
      const s = decode(query);
      expect(s.ed, query).toBe('smyth-loeb');
      const q = encodeSearchUrl(s, works);
      expect(new URLSearchParams(q).get('ed'), query).toBe('smyth-loeb');
      expect(decode(q), query).toEqual(s);
    }
    // An address with nothing to search writes nothing, edition or not.
    expect(encodeSearchUrl({ ...emptyUrlSearch(works), ed: 'smyth-loeb' }, works)).toBe('');
  });

  // Review fix 4: the old page restricted each word of a multiword lemma
  // search to its ticked headwords (legacy search.ts lemmaPick), Near or not.
  it('keeps an old multiword lemma search\'s headword picks, and writes them back', () => {
    const s = decode('g=logou%20qeous&m=lemma&lp=logos~qea');
    expect(s).toMatchObject({ grk: 'logou qeous', matchMode: 'lemma', lemmaPick: [['logos'], ['qea']], combo: null });
    const q = encodeSearchUrl(s, works);
    expect(new URLSearchParams(q).get('lp')).toBe('logos~qea');
    expect(decode(q)).toEqual(s);
    // A word with nothing ticked is looked up as typed.
    expect(decode('g=logou%20qeous&m=lemma&lp=~qea').lemmaPick).toEqual([[], ['qea']]);
    // By form the picks asked nothing, as on the old page.
    expect(decode('g=logou%20qeous&lp=logos~qea').lemmaPick).toBeUndefined();
    expect(encodeSearchUrl({ ...emptyUrlSearch(works), grk: 'a b', matchMode: 'form', lemmaPick: [['x'], ['y']] }, works)).not.toContain('lp=');
  });

  it('writes the opened search in the new address, and reads it back the same', async () => {
    const s = decode(`g=${encodeURIComponent('ὦ')}&e=sword&n=f&nt=${encodeURIComponent('τέκνον')}&nr=a&nw=3&nu=l&en=hand&enr=b`);
    const q = encodeSearchUrl(s, works);
    expect(decodeURIComponent(q)).toBe('c=f:ὦ&c=fa:τέκνον&cu=line&cw=3&e=sword&op=and&en=hand&enr=b');
    expect(decode(q)).toEqual(s);
  });
});

describe('old Greek and English parameters keep their old meaning', () => {
  // On the old page a Greek box with no m matched the exact form; a link the
  // new page writes names m whenever it has Greek (John: keep old links).
  it.each([
    ['g=δίκη', 'δίκη', 'all'],
    ['g=φιλ*', 'φιλ*', 'all'],
    ['g=dikh', 'dikh', 'all'],
    ['g=ὦ Ζεῦ&gm=phrase', 'ὦ Ζεῦ', 'phrase'],
    ['q=δίκη', 'δίκη', 'all'],
  ])('reads %s as the exact form', (query, grk, grkMode) => {
    const s = decode(query);
    expect(s).toMatchObject({ grk, matchMode: 'form', grkMode });
  });

  it('reads m as given, and a blank page keeps the new default', () => {
    expect(decode('g=δίκη&m=lemma').matchMode).toBe('lemma');
    expect(decode('g=δίκη&m=form').matchMode).toBe('form');
    expect(decode('g=δίκη&m=text').matchMode).toBe('text');
    expect(emptyUrlSearch(works).matchMode).toBe('lemma');
    expect(decode('').matchMode).toBe('lemma');
    expect(decode('e=virtue').matchMode).toBe('lemma');
  });

  it('names m in every link it writes with Greek, and reads it back', () => {
    for (const matchMode of ['lemma', 'form', 'text'] as const) {
      const s: UrlSearch = { ...emptyUrlSearch(works), grk: 'δίκη', matchMode };
      const q = encodeSearchUrl(s, works);
      expect(new URLSearchParams(q).get('m')).toBe(matchMode);
      expect(decode(q)).toEqual(s);
    }
    // No Greek, no m.
    expect(new URLSearchParams(encodeSearchUrl({ ...emptyUrlSearch(works), eng: 'justice' }, works)).has('m')).toBe(false);
  });

  // The old English parameters, each absent: the same meaning as before.
  it('reads an old English link with em, ef, en, enr, enw absent as the old page did', () => {
    const s = decode('e=justice');
    expect(s).toMatchObject({ eng: 'justice', engMode: 'all', engForms: true, engNear: null, langOp: 'or' });
    expect(decode('e=justice&em=phrase').engMode).toBe('phrase');
    expect(decode('e=justice&em=junk').engMode).toBe('all');
    expect(decode('e=justice&ef=0').engForms).toBe(false);
    expect(decode('e=justice&en=right').engNear).toEqual({ term: 'right', relation: 'near', window: 10 });
    expect(decode('e=justice&en=right&enr=a&enw=3').engNear).toEqual({ term: 'right', relation: 'after', window: 3 });
    expect(decode('e=justice&acc=1').accent).toBe(true);
  });

  it('keeps the old "and" of a Greek and English link, now beside the exact form', () => {
    const s = decode('g=δίκη&e=justice');
    expect(s).toMatchObject({ langOp: 'and', matchMode: 'form' });
  });
});

describe('the plays\' new address', () => {
  it('keeps the English box beside a proximity search', () => {
    const s: UrlSearch = { ...emptyUrlSearch(works), eng: 'justice', engMode: 'phrase', engForms: false, langOp: 'or', trans: 'smyth',
      combo: { slots: [slot({ kind: 'lemma', picked: ['dikh'] }), slot({ kind: 'lemma', picked: ['qeos'] })], window: 10, unit: 'words', ordered: false, crossChapter: true } };
    const q = encodeSearchUrl(s, works);
    expect(decodeURIComponent(q)).toBe('c=l:dikh&c=l:qeos&e=justice&em=phrase&ef=0&op=or&t=smyth');
    expect(decode(q)).toEqual(s);
  });

  it('writes English near beside the English box, and only there', () => {
    const s: UrlSearch = { ...emptyUrlSearch(works), eng: 'man', engNear: { term: 'child', relation: 'after', window: 4 } };
    expect(decodeURIComponent(encodeSearchUrl(s, works))).toBe('e=man&en=child&enr=a&enw=4');
    expect(decode('e=man&en=child&enr=a&enw=4')).toEqual(s);
    expect(decode('g=x&en=child').engNear).toBeNull();
  });

  it('writes a window of 10 words as no window, and lines either side as cw', () => {
    const combo = (window: number, unit: 'words' | 'line') => ({ ...emptyUrlSearch(works),
      combo: { slots: [slot({ kind: 'form', text: 'a' }), slot({ kind: 'form', text: 'b' })], window, unit, ordered: false, crossChapter: true } });
    expect(encodeSearchUrl(combo(10, 'words'), works)).toBe('c=f:a&c=f:b');
    expect(encodeSearchUrl(combo(0, 'line'), works)).toBe('c=f:a&c=f:b&cu=line');
    expect(encodeSearchUrl(combo(2, 'line'), works)).toBe('c=f:a&c=f:b&cu=line&cw=2');
    expect(decode('c=f:a&c=f:b&cu=line&cw=2').combo).toMatchObject({ unit: 'line', window: 2 });
    expect(decode('c=f:a&c=f:b&cu=line&cw=99').combo).toMatchObject({ unit: 'line', window: 10 });
    expect(decode('c=f:a&c=f:b').combo?.window).toBe(10);
  });

  it('writes a headword phrase as a q slot, its words by their folds', () => {
    const s: UrlSearch = { ...emptyUrlSearch(works), combo: {
      slots: [slot({ kind: 'phrase', text: 'θεοὺς λόγος', options: [['qeos', 'qea'], ['logos']] }), slot({ kind: 'form', text: 'kalos', relation: 'before' })],
      window: 10, unit: 'words', ordered: false, crossChapter: true } };
    const q = encodeSearchUrl(s, works);
    expect(decodeURIComponent(q)).toBe('c=q:qeos.qea logos&c=fb:kalos');
    expect(decode(q).combo?.slots[0]).toEqual(slot({ kind: 'phrase', text: 'qeos.qea logos', options: [['qeos', 'qea'], ['logos']] }));
  });
});

describe('looking up an old link\'s headwords', () => {
  afterEach(() => vi.restoreAllMocks());

  it('fills each lemma term and each unknown phrase word from the lemma map, as the old page did', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(url => {
      const path = String(url);
      const body = path.endsWith('/lemma-map/t.json') ? { tekna: [['teknon', 'te/knon'], ['teknos', 'te/knos']] }
        : path.endsWith('/lemma-map/q.json') ? { qeous: [['qeos', 'qeo/s']] } : null;
      return Promise.resolve({ ok: !!body, status: body ? 200 : 404, json: async () => body } as Response);
    });
    const s = await resolveUrlLemmas(decode(`g=qeous zzz&m=lemma&n=l&nt=${encodeURIComponent('τέκνα')}`));
    expect(s.combo?.slots).toEqual([
      slot({ kind: 'phrase', text: 'qeous zzz', options: [['qeos'], ['zzz']] }),
      slot({ kind: 'lemma', text: 'τέκνα', picked: ['teknon', 'teknos'] }),
    ]);
  });
});
