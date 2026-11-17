import { AUTHENTIC_IDS, HAS_SPEAKERS, NEAR_RULES, NEAR_WINDOW_DEFAULT } from './works';
// The search page's state as a query string, so a search can be shared,
// bookmarked, reloaded and stepped through with the back button.
//
// Only what the search actually ran on is written, and defaults are left
// out: a plain Greek search is ?g=λόγος, nothing more. ?g= and ?e= are also
// what the command palette hands off, so they keep their meaning here.
//
//   g, e     Greek and English queries
//   q        read only, never written: the search box of search.astro's
//            JSON-LD SearchAction. Greek script goes to g, anything else
//            to e (Beta Code reads the same as English, so it goes to e);
//            ignored when g or e is present, even empty
//   gm, em   Greek and English match: any | phrase (default all)
//   ef       0 = English words only as typed (default: any form of each)
//   m        form | text (default lemma: any form of the word); text is the
//            running text, the box a regular expression over it (PR 9)
//   pu       1 = running text: match punctuation (default: ignored)
//   acc      1 = match accents exactly
//   cs       read as absent: capitals are always ignored (ruling 5, 12 Nov
//            2026), so an old cs=1 link opens with case ignored; never written
//   xf       Greek forms set aside in the results' form panel: folded keys,
//            comma-separated (default: none)
//   xp       English phrases set aside in the results' phrase list, comma-
//            separated (default: none)
//   op       or (default and: both queries)
//   w        works: absent = all; "auth" = the authentic works (works.ts
//            authenticity unset or genuine); "EN,Cat" = these; "-Oec,MM" =
//            all but these. Every older spelling still reads as before.
//   t        the translation the English hits are narrowed to
//   wf       the work the hits are narrowed to (the results page's Works row)
//   l        the single-lemma search's picked keys, comma-separated
//   c        one per proximity slot: kind letter, then either "o" (joined
//            to the slot before by "or": one term with it, taking its
//            relation and target) or an optional relation letter (b before,
//            a after, n not near; none = near) and the 1-based number of the
//            earlier term it is measured from (none = term 1); colon,
//            payload — "f:λόγος", "la:logos,areth", "g:case.gen,number.pl",
//            "lo:hdonh" (or the term before), "lb2:luph" (before term 2).
//            A link written before joiners and targets reads as it did:
//            every slot joined by "and", every term measured from term 1
//   cw, cu   proximity window (default 5) and unit (default words)
//   co, cx   co=1: in this order; cx=0: drop hits that cross a chapter
//   sp, sn   the speaker filter: sp=only | except, sn the names, comma-separated
//            (default: anyone, and then sn is not written)
//   v        how the hits are grouped: form | grammar (default page, by work;
//            an old v=work reads as the default)
//   gf       the grammar facets ticked: cat.val, comma-separated, as a
//            proximity slot's g: payload — "case.gen,number.pl" (default: none)
//   ctx      how much text a hit shows: 1 (a line) | s (its whole section)
//            (default 3 lines). Not cx, which is the proximity chapter switch
//   so       the order of a results page: work | form | freq (default page)
//   ps       rows per results page: 20 | 100 (default 40); an old ps=c or ctx=c is 100
//   en, enr, enw  the plays' English near: the near word or phrase, b | a
//            (before, after; none = near), and the distance in words
//            (default 10). Written beside e, and with a proximity search
//
// The plays (search port): a proximity search keeps the English box beside
// it (e, em, ef, op, t, xp), joined by speech; the window opens at 10 words
// (NEAR_WINDOW_DEFAULT), and cu=line takes cw as lines either side, 0 to 10
// (default 0). A "q" slot is a phrase matched by headword, the Greek box's
// words as the first term: its payload the words, each a run of folds joined
// by "." where its headwords are known ("q:qeos.qea logos").
// The plays' old addresses (before the port) still open, read by
// decodeOldPlays below: lp, n, nt, ng, nf, nr, nw, nu, no, n2…, sh.

import {
  COMBO_TERMS_MAX,
  COMBO_WINDOW_MAX,
  lemmaHeads,
  type EngNear,
  type GrammarQuery,
  type LangOp,
  type MatchMode,
  type SearchMode,
  type SlotKind,
  type SpeakerFilter,
  type SlotRelation,
  type WindowUnit,
} from './search';
import {
  PAGE_SIZES, RESULT_CONTEXTS, RESULT_SORTS, RESULT_VIEWS,
  type Facets, type PageSize, type ResultContext, type ResultSort, type ResultView,
} from './result-views';

export interface UrlComboSlot {
  kind: SlotKind;
  relation: SlotRelation;
  or?: true;             // joined to the slot before by "or"
  target?: number;       // the earlier slot it is measured from (0-based); absent = 0
  text: string;          // phrase / form
  picked: string[];      // lemma
  grammar: GrammarQuery; // grammatical
  // The plays: a phrase matched by headword (kind 'phrase'), one list of
  // folds per word of `text`; a list left empty is looked up from the word
  // (resolveUrlLemmas). Absent on a phrase matched as written.
  options?: string[][];
  // The plays' old links: a lemma term whose headwords are to be looked up
  // from `text` (resolveUrlLemmas), its `picked` empty till then.
  resolve?: true;
}

export interface UrlCombo {
  slots: UrlComboSlot[];
  window: number;
  unit: WindowUnit;
  ordered: boolean;
  crossChapter: boolean;
}

export interface UrlSearch {
  grk: string;
  eng: string;
  grkMode: SearchMode;
  engMode: SearchMode;
  matchMode: MatchMode | 'text';
  accent: boolean;
  punctuation: boolean;     // running text: match the punctuation too
  caseExact: boolean;       // Greek: match capitals and small letters exactly
  langOp: LangOp;
  engForms: boolean;       // English: any form of each word
  works: string[];         // the selected works; every work = all
  trans: string | null;
  workFilter: string | null; // the one work the hits are narrowed to
  lemmas: string[];        // the single-lemma search
  xforms: string[];        // forms set aside in the form panel, as folded keys
  xphrases: string[];      // English phrases set aside in the phrase list
  combo: UrlCombo | null;  // a proximity search; it supersedes the rest
  speaker: SpeakerFilter | null; // whose words; null = anyone's
  view: ResultView;        // how the hits are grouped
  facets: Facets;          // the grammar facets ticked
  context: ResultContext;  // how much text a hit shows
  sort: ResultSort;        // the order of a results page
  pageSize: PageSize;      // hits per results page
  // The plays: the Greek edition a Greek-only search reads where a play holds
  // it (ed=); null for each play's reference text.
  ed: string | null;
  // The plays' English near (en=); null for none.
  engNear: EngNear | null;
}

export const emptyUrlSearch = (allWorks: string[]): UrlSearch => ({
  grk: '', eng: '', grkMode: 'all', engMode: 'all', matchMode: 'lemma',
  accent: false, punctuation: false, caseExact: false, langOp: 'or', engForms: true, works: [...allWorks], trans: null, workFilter: null,
  lemmas: [], xforms: [], xphrases: [], combo: null, speaker: null, view: 'page', facets: {},
  context: '3', sort: 'page', pageSize: '40', ed: null, engNear: null,
});

// The window a proximity search opens at: the plays' 10, Aristotle's 5.
const WINDOW_DEFAULT = NEAR_WINDOW_DEFAULT;
// The plays' line unit takes cw as lines either side, 0 (the same line) to 10.
const LINES_EITHER_SIDE = !!(NEAR_RULES as { linesEitherSide?: boolean }).linesEitherSide;
const LINES_MAX = 10;
const windowDefault = (unit: WindowUnit) => (unit === 'line' && LINES_EITHER_SIDE ? 0 : WINDOW_DEFAULT);

const MODES: SearchMode[] = ['all', 'any', 'phrase'];
const UNITS: WindowUnit[] = HAS_SPEAKERS ? ['words', 'line', 'turn', 'chapter'] : ['words', 'line', 'chapter'];
const KIND_LETTER: Record<SlotKind, string> = { phrase: 'p', form: 'f', lemma: 'l', grammatical: 'g' };
// The plays' phrase matched by headword.
const LEMMA_PHRASE = 'q';
const RELATION_LETTER: Record<SlotRelation, string> = { near: '', before: 'b', after: 'a', not: 'n' };
const KINDS = Object.fromEntries(Object.entries(KIND_LETTER).map(([k, v]) => [v, k as SlotKind]));
const RELATIONS = Object.fromEntries(Object.entries(RELATION_LETTER).map(([k, v]) => [v, k as SlotRelation]));

// A Greek letter: not Greek punctuation (U+037E, U+0387), and not Coptic.
const GREEK_LETTER = /(?=\p{L})\p{Script=Greek}/u;

// The named works value: the authentic works, as many as the registry has.
const AUTH = 'auth';
const authenticOf = (allWorks: string[]) => {
  const auth = new Set(AUTHENTIC_IDS);
  return allWorks.filter(id => auth.has(id));
};

const list = (s: string | null) => (s ?? '').split(',').map(x => x.trim()).filter(Boolean);

// A headword phrase's words, each by its folds where they are known.
const lemmaPhrasePayload = (slot: UrlComboSlot) => slot.text.trim().split(/\s+/)
  .map((w, i) => (slot.options?.[i]?.length ? slot.options[i].join('.') : w)).join(' ');

function encodeSlot(slot: UrlComboSlot): string {
  const lemmaPhrase = slot.kind === 'phrase' && !!slot.options;
  const payload = lemmaPhrase
    ? lemmaPhrasePayload(slot)
    : slot.kind === 'lemma'
      ? slot.picked.join(',')
      : slot.kind === 'grammatical'
        ? Object.entries(slot.grammar).map(([k, v]) => `${k}.${v}`).join(',')
        : slot.text.trim();
  const head = slot.or ? 'o' : `${RELATION_LETTER[slot.relation]}${slot.target ? slot.target + 1 : ''}`;
  return `${lemmaPhrase ? LEMMA_PHRASE : KIND_LETTER[slot.kind]}${head}:${payload}`;
}

// The old pos category is retired. Aristotle's marker (word class) remains
// live in the grammar grid; old pos links lose only that category.
const RETIRED_GRAMMAR = new Set(['pos']);

// null: not a slot. 'retired': a grammar term that asked only a retired
// category, so cannot be asked any more.
// A slot that asks nothing is `empty`: dropped, but its joiner and target are
// read so the slots after it keep theirs (decodeSlots).
function decodeSlot(raw: string): UrlComboSlot | null | 'retired' | { empty: UrlComboSlot } {
  const m = /^([pflgq])(?:(o)|([ban]?)([1-9]\d{0,2})?):(.*)$/s.exec(raw);
  if (!m) return null;
  const lemmaPhrase = m[1] === LEMMA_PHRASE;
  const slot: UrlComboSlot = { kind: lemmaPhrase ? 'phrase' : KINDS[m[1]], relation: RELATIONS[m[3] ?? ''], text: '', picked: [], grammar: {} };
  if (m[2]) slot.or = true;
  if (m[4]) slot.target = Number(m[4]) - 1;
  const payload = m[5];
  if (lemmaPhrase) {
    // Each word: its folds joined by "." (lower-case Beta Code letters), or
    // the word as typed, to be looked up.
    const words = payload.trim().split(/\s+/).filter(Boolean);
    slot.options = words.map(w => (/^[a-z'()\\/=|+]+(?:\.[a-z'()\\/=|+]+)*$/.test(w) ? w.split('.') : []));
    slot.text = words.join(' ');
  } else if (slot.kind === 'lemma') slot.picked = list(payload);
  else if (slot.kind === 'grammatical') {
    let retired = false;
    for (const pair of list(payload)) {
      const [k, v] = pair.split('.');
      if (k && v && RETIRED_GRAMMAR.has(k)) retired = true;
      else if (k && v) slot.grammar[k] = v;
    }
    if (retired && !Object.keys(slot.grammar).length) return 'retired';
  } else slot.text = payload.trim();
  const empty = slot.kind === 'lemma' ? !slot.picked.length
    : slot.kind === 'grammatical' ? !Object.keys(slot.grammar).length
    : !slot.text;
  return empty ? { empty: slot } : slot;
}

// The slots that ask something, with each target re-read as an index among
// them: one measured from a dropped slot is measured from what that one was;
// one naming no earlier slot, from the first. A first slot joins nothing; an
// "or" slot after a dropped term takes that term's place, relation and target.
function decodeSlots(raw: ReturnType<typeof decodeSlot>[]): UrlComboSlot[] {
  const out: UrlComboSlot[] = [];
  const at: number[] = [];   // URL slot index -> the kept slot standing for it
  // A dropped head, and the URL slots of its group dropped so far: the "or"
  // slot that takes its place stands for them all (Codex review, 12 Nov).
  let dropped: { relation: SlotRelation; target: number; slots: number[] } | null = null;
  raw.forEach((r, i) => {
    if (r === null || r === 'retired') { at.push(0); return; }
    const slot = 'empty' in r ? r.empty : r;
    const t = slot.target ?? 0;
    const target = t > 0 && t < i ? at[t] : 0;
    const joined = !!slot.or && i > 0;
    if ('empty' in r) {
      if (!joined) dropped = { relation: slot.relation, target, slots: [i] };
      else dropped?.slots.push(i);
      at.push(joined ? at[i - 1] : target);
      return;
    }
    if (joined && dropped) for (const k of dropped.slots) at[k] = out.length;
    const kept: UrlComboSlot = { kind: slot.kind, relation: slot.relation, text: slot.text, picked: slot.picked, grammar: slot.grammar,
      ...(slot.options ? { options: slot.options } : {}) };
    if (joined && dropped) {
      kept.relation = dropped.relation;
      if (dropped.target) kept.target = dropped.target;
    } else if (joined && out.length) kept.or = true;
    else if (target > 0) kept.target = target;
    if (!joined || dropped) dropped = null;
    at.push(out.length);
    out.push(kept);
  });
  return out;
}

// Percent-encoded as a query string, but with commas and colons left bare:
// they separate the parts of a value and read better as themselves.
function serialize(pairs: [string, string][]): string {
  return pairs.map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%2C/g, ',').replace(/%3A/g, ':')}`).join('&');
}

/** The query string (no leading "?") for a search; "" when there is none. */
// A combo the address bar keeps: two terms or more, not opening with NOT; or,
// since ruling 3 (2026-11-10), a lone grammar term, which runs once something
// narrows it.
const comboKept = (slots: UrlComboSlot[]) =>
  slots.length > 0 && slots[0].relation !== 'not' && (slots.length >= 2 || slots[0].kind === 'grammatical');

export function encodeSearchUrl(s: UrlSearch, allWorks: string[]): string {
  const out: [string, string][] = [];
  const put = (k: string, v: string) => out.push([k, v]);
  const combo = s.combo && comboKept(s.combo.slots) ? s.combo : null;
  const grk = s.grk.trim();
  const eng = s.eng.trim();
  // The English box beside a Greek search (or a proximity search, the plays).
  const english = (greek: boolean) => {
    put('e', eng);
    if (s.engMode !== 'all') put('em', s.engMode);
    if (!s.engForms) put('ef', '0');
    if (greek) put('op', s.langOp);
    if (s.engNear?.term.trim()) {
      put('en', s.engNear.term.trim());
      if (s.engNear.relation !== 'near') put('enr', s.engNear.relation[0]);
      if (s.engNear.window !== WINDOW_DEFAULT) put('enw', String(s.engNear.window));
    }
    if (s.trans) put('t', s.trans);
    if (s.xphrases.length) put('xp', s.xphrases.join(','));
  };
  if (combo) {
    for (const slot of combo.slots) put('c', encodeSlot(slot));
    if (combo.unit !== 'words') put('cu', combo.unit);
    if (combo.window !== windowDefault(combo.unit)) put('cw', String(combo.window));
    if (combo.ordered) put('co', '1');
    if (!combo.crossChapter) put('cx', '0');
    if (eng && LINES_EITHER_SIDE) english(true);
  } else {
    if (s.lemmas.length) put('l', s.lemmas.join(','));
    else if (grk) {
      put('g', grk);
      // The running text is one pattern: no word match mode belongs to it.
      const text = s.matchMode === 'text';
      if (s.grkMode !== 'all' && !text) put('gm', s.grkMode);
      if (s.matchMode !== 'lemma' && s.matchMode !== 'headword') put('m', s.matchMode);
      if (s.accent) put('acc', '1');
      if (text && s.punctuation) put('pu', '1');
    }
    if ((s.lemmas.length || grk) && s.xforms.length) put('xf', s.xforms.join(','));
    if ((s.lemmas.length || grk) && s.ed) put('ed', s.ed);
    if (eng) english(!!(s.lemmas.length || grk));
  }
  if (combo && s.trans && !(eng && LINES_EITHER_SIDE)) put('t', s.trans);
  if (combo && s.xforms.length) put('xf', s.xforms.join(','));
  if (!out.length) return '';
  if (s.speaker?.names.length) {
    put('sp', s.speaker.mode);
    put('sn', s.speaker.names.join(','));
  }
  if (s.view !== 'page') put('v', s.view);
  const gf = Object.entries(s.facets).flatMap(([k, values]) => values.map(v => `${k}.${v}`));
  if (gf.length) put('gf', gf.join(','));
  if (s.context !== '3') put('ctx', s.context);
  if (s.sort !== 'page') put('so', s.sort);
  if (s.pageSize !== '40') put('ps', s.pageSize);
  if (s.workFilter) put('wf', s.workFilter);
  const chosen = new Set(s.works);
  const auth = authenticOf(allWorks);
  const isAuth = auth.length > 0 && auth.length === chosen.size && auth.every(id => chosen.has(id));
  if (allWorks.some(id => !chosen.has(id))) {
    const inList = allWorks.filter(id => chosen.has(id));
    const outList = allWorks.filter(id => !chosen.has(id));
    put('w', isAuth ? AUTH : inList.length && outList.join(',').length < inList.join(',').length
      ? `-${outList.join(',')}`
      : inList.join(','));
  }
  return serialize(out);
}

/** Reads a search back from a query string. Unknown values fall back to defaults. */
export function decodeSearchUrl(search: string | URLSearchParams, allWorks: string[]): UrlSearch {
  const p = typeof search === 'string' ? new URLSearchParams(search) : search;
  const s = emptyUrlSearch(allWorks);
  const pick = <T extends string>(v: string | null, allowed: readonly T[], fallback: T): T =>
    allowed.includes(v as T) ? (v as T) : fallback;

  s.grk = (p.get('g') ?? '').trim();
  s.eng = (p.get('e') ?? '').trim();
  const q = (p.get('q') ?? '').trim();
  if (q && !p.has('g') && !p.has('e')) {
    if (GREEK_LETTER.test(q)) s.grk = q;
    else s.eng = q;
  }
  s.grkMode = pick(p.get('gm'), MODES, 'all');
  s.engMode = pick(p.get('em'), MODES, 'all');
  const m = p.get('m');
  s.matchMode = m === 'form' || m === 'text' ? m : 'lemma';
  s.accent = p.get('acc') === '1';
  s.punctuation = p.get('pu') === '1';
  s.caseExact = false;   // cs is ignored: case never matters
  s.engForms = p.get('ef') !== '0';
  s.trans = p.get('t') || null;
  const wf = p.get('wf');
  s.workFilter = wf && allWorks.includes(wf) ? wf : null;
  s.lemmas = list(p.get('l'));
  // A search opens on "and/or" (John, 16 Nov). A link from before that, a
  // Greek and English search with no op, meant "and" and still does; every
  // link written since names its op. op=or stays the inclusive or.
  s.xforms = list(p.get('xf'));
  const ed = p.get('ed');
  s.ed = ed && ed !== 'tlg' ? ed : null;
  s.xphrases = s.eng ? list(p.get('xp')).map(x => x.toLowerCase().replace(/\s+/g, ' ')) : [];

  const decoded = p.getAll('c').map(decodeSlot);
  const slots = decodeSlots(decoded).slice(0, COMBO_TERMS_MAX);
  // A first slot of NOT has nothing to stand apart from: no proximity search.
  // A combo with a term that can no longer be asked is not run as another.
  if (!decoded.includes('retired') && comboKept(slots)) {
    // Clamped as the window box clamps what is typed into it.
    const win = Number(p.get('cw'));
    const unit = pick(p.get('cu'), UNITS, 'words');
    s.combo = {
      slots,
      window: unit === 'line' && LINES_EITHER_SIDE
        ? (p.has('cw') && Number.isFinite(win) ? Math.max(0, Math.min(Math.trunc(win), LINES_MAX)) : 0)
        : win > 0 ? Math.max(1, Math.min(win, COMBO_WINDOW_MAX)) : WINDOW_DEFAULT,
      unit,
      ordered: p.get('co') === '1',
      crossChapter: p.get('cx') !== '0',
    };
  }
  // The plays' English near, beside the English box.
  const en = (p.get('en') ?? '').trim();
  if (en && s.eng && LINES_EITHER_SIDE) s.engNear = { term: en, relation: OLD_RELATIONS.get(p.get('enr') ?? '') ?? 'near', window: nearWords(p.get('enw')) };
  // The plays' addresses from before the port.
  if (LINES_EITHER_SIDE && !s.combo && OLD_PARAMS.some(k => p.has(k))) decodeOldPlays(p, s);
  // A search opens on "and/or" (John, 16 Nov). A link from before that, a
  // Greek and English search with no op, meant "and" and still does; every
  // link written since names its op. op=or stays the inclusive or.
  const op = p.get('op');
  s.langOp = op === 'and' || op === 'or' || op === 'xor' ? op : s.eng && (s.grk || s.lemmas.length || s.combo) ? 'and' : 'or';

  const sp = p.get('sp');
  const names = list(p.get('sn'));
  if ((sp === 'only' || sp === 'except') && names.length) s.speaker = { mode: sp, names };

  s.view = pick(p.get('v'), RESULT_VIEWS, 'page');
  s.context = pick(p.get('ctx'), RESULT_CONTEXTS, '3');
  s.sort = pick(p.get('so'), RESULT_SORTS, 'page');
  s.pageSize = pick(p.get('ps'), PAGE_SIZES, '40');
  // Citations only (ctx=c, and before it ps=c) gave way to the 100 page,
  // each row its reference and the words around its first hit (John, 16 Nov:
  // "Yes, replace it"), so such a link opens there.
  if (p.get('ctx') === 'c' || p.get('ps') === 'c') s.pageSize = '100';
  for (const pair of list(p.get('gf'))) {
    const [k, v, extra] = pair.split('.');
    // A name every object has ("constructor", "__proto__") is not a category,
    // and read as one would hand back a function where a list belongs.
    if (!k || !v || extra !== undefined || k in Object.prototype || RETIRED_GRAMMAR.has(k)) continue;
    const values = (s.facets[k] ??= []);
    if (!values.includes(v)) values.push(v);
  }

  const w = p.get('w');
  if (w === AUTH) s.works = authenticOf(allWorks);
  else if (w !== null) {
    const known = new Set(allWorks);
    const named = new Set(list(w.replace(/^-/, '')).filter(id => known.has(id)));
    s.works = w.startsWith('-')
      ? allWorks.filter(id => !named.has(id))
      : allWorks.filter(id => named.has(id));
  }
  return s;
}

// -- The plays' old addresses ----------------------------------------------
//
// Before the port, the plays wrote their Near search as the Greek box (g, m,
// gm) with lp (the ticked headwords of each typed word, "polis.polew~qeos"),
// n/nt/ng/nf/nr/nw/nu/no for the second term and n2…/n3… for more, each
// measured from the first word, sh for a grammar term alone, and en/enr/enw
// for English near. Such a link opens as the search it was (search port,
// decision 3): the Near terms become a proximity search on the plays' rules,
// a term whose headwords were not ticked looked up as the old page looked it
// up (resolveUrlLemmas), and with no m the Greek box matched forms, the old
// default. A plain g/e link carries none of these and reads as above.
// (en is new too: written beside e since the port, so it marks no old link.)
const OLD_PARAMS = ['lp', 'n', 'sh'];
const OLD_KINDS = new Map<string, SlotKind>([['g', 'grammatical'], ['l', 'lemma'], ['f', 'form'], ['p', 'phrase']]);
const OLD_RELATIONS = new Map<string, EngNear['relation']>([['n', 'near'], ['b', 'before'], ['a', 'after']]);
const OLD_GRAMMAR_KEYS = new Set(['case', 'number', 'gender', 'person', 'tense', 'mood', 'voice', 'degree', 'marker']);
const OLD_MORE = 2;   // the old page's further terms: n2 and n3
function oldGrammar(v: string | null): GrammarQuery | null {
  if (!v) return null;
  const pairs = v.split('~').map(pair => pair.split('.'))
    .filter(parts => parts.length === 2 && OLD_GRAMMAR_KEYS.has(parts[0]) && /^[a-z0-9_]+$/i.test(parts[1]));
  return pairs.length ? Object.fromEntries(pairs) as GrammarQuery : null;
}
const oldFolds = (v: string | null) => (v ?? '').split('.').map(f => f.trim()).filter(f => /^[a-z']+$/.test(f));
// Words 1 to 50, default 10, as the old Near and English near clamped them.
const nearWords = (v: string | null) => {
  const n = Number(v ?? NaN);
  return v !== null && Number.isFinite(n) ? Math.max(1, Math.min(Math.trunc(n), COMBO_WINDOW_MAX)) : WINDOW_DEFAULT;
};

// One old Near term: a phrase where it has several words (whatever its kind),
// else as its kind says; a lemma term's ticked headwords, or its word to look up.
function oldTerm(kind: SlotKind, text: string, grammar: GrammarQuery | null, picks: string[], relation: SlotRelation): UrlComboSlot | null {
  const slot: UrlComboSlot = { kind, relation, text: '', picked: [], grammar: {} };
  if (kind === 'grammatical') return grammar ? { ...slot, grammar } : null;
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  if (words.length > 1) return { ...slot, kind: 'phrase', text: words.join(' ') };
  if (kind === 'lemma') return picks.length ? { ...slot, text: words[0], picked: picks } : { ...slot, text: words[0], resolve: true };
  return { ...slot, kind: 'form', text: words[0] };
}

function decodeOldPlays(p: URLSearchParams, s: UrlSearch): void {
  // With no m the old Greek box matched forms.
  if (!p.has('m')) s.matchMode = 'form';
  else if (p.get('m') !== 'lemma' && p.get('m') !== 'form') s.matchMode = 'form';
  const lp = p.has('lp') ? (p.get('lp') ?? '').split('~').map(oldFolds) : null;
  const typed = s.grk.split(/\s+/).filter(Boolean);
  const lemma = s.matchMode === 'lemma';

  const kind = OLD_KINDS.get(p.get('n') ?? '');
  const second = kind ? oldTerm(kind, (p.get('nt') ?? '').trim(), oldGrammar(p.get('ng')), kind === 'lemma' ? oldFolds(p.get('nf')) : [],
    OLD_RELATIONS.get(p.get('nr') ?? 'n') ?? 'near') : null;
  if (second && typed.length) {
    // The first term: the Greek box, a phrase when it holds several words
    // (by headword in lemma mode, each word its ticked headwords or looked up).
    const first: UrlComboSlot = typed.length > 1
      ? { kind: 'phrase', relation: 'near', text: typed.join(' '), picked: [], grammar: {},
        ...(lemma ? { options: typed.map((_, i) => lp?.[i] ?? []) } : {}) }
      : lemma
        ? (lp?.[0]?.length ? { kind: 'lemma', relation: 'near', text: typed[0], picked: lp[0], grammar: {} }
          : { kind: 'lemma', relation: 'near', text: typed[0], picked: [], grammar: {}, resolve: true })
        : { kind: 'form', relation: 'near', text: typed[0], picked: [], grammar: {} };
    const slots = [first, second];
    for (let k = 2; k < 2 + OLD_MORE; k++) {
      const mk = OLD_KINDS.get(p.get(`n${k}`) ?? '');
      if (!mk) break;
      const more = oldTerm(mk, (p.get(`nt${k}`) ?? '').trim(), oldGrammar(p.get(`ng${k}`)), mk === 'lemma' ? oldFolds(p.get(`nf${k}`)) : [],
        OLD_RELATIONS.get(p.get(`nr${k}`) ?? 'n') ?? 'near');
      if (!more) break;
      slots.push(more);
    }
    const lines = p.get('nu') === 'l';
    s.combo = {
      slots,
      window: lines ? Math.max(0, Math.min(Math.trunc(Number(p.get('nw') ?? 0)) || 0, LINES_MAX)) : nearWords(p.get('nw')),
      unit: lines ? 'line' : 'words',
      // "In this order" was offered, and read, only with three terms.
      ordered: p.get('no') === '1' && slots.length > 2,
      crossChapter: true,
    };
    // The box's words are the first term now; its mode asks nothing more.
    s.grk = '';
    s.matchMode = 'lemma';
    s.grkMode = 'all';
    s.accent = false;
    return;
  }
  // A grammar term alone: Aristotle's lone grammar term, run once narrowed.
  const shape = oldGrammar(p.get('sh'));
  if (shape && !typed.length) {
    s.combo = { slots: [{ kind: 'grammatical', relation: 'near', text: '', picked: [], grammar: shape }], window: WINDOW_DEFAULT, unit: 'words', ordered: false, crossChapter: true };
    return;
  }
  // One word with its headwords ticked: the dictionary-word search.
  if (lemma && typed.length === 1 && lp?.[0]?.length) {
    s.lemmas = lp[0];
    s.grk = '';
  }
}

/** The headwords of each old-link lemma term (resolve) and of each word of a
 * headword phrase not yet known, looked up as the old page looked them up. */
export async function resolveUrlLemmas(s: UrlSearch): Promise<UrlSearch> {
  if (!s.combo?.slots.some(slot => slot.resolve || slot.options?.some(o => !o.length))) return s;
  const slots = await Promise.all(s.combo.slots.map(async slot => {
    if (slot.resolve) {
      const { resolve: _, ...rest } = slot;
      return { ...rest, picked: await lemmaHeads(slot.text) };
    }
    if (slot.options?.some(o => !o.length)) {
      const words = slot.text.split(/\s+/);
      return { ...slot, options: await Promise.all(slot.options.map((o, i) => (o.length ? o : lemmaHeads(words[i] ?? '')))) };
    }
    return slot;
  }));
  return { ...s, combo: { ...s.combo, slots } };
}

/** Whether the decoded state asks for a search at all. */
export const hasSearch = (s: UrlSearch) => !!(s.grk || s.eng || s.lemmas.length || s.combo);
