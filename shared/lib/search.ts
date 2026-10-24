// Search engine — operates on the prebuilt inverted indexes from Stage 6.
//
// Greek search: input is Unicode Greek OR TLG Beta Code (with optional * wildcards).
//   Converted to fold form (base Beta Code letters only) to match the index.
//   Beta Code letters already ARE the fold form (θ→q, φ→f, χ→x, ψ→y, ξ→c,
//   η→h, ω→w, …), so Latin input passes straight through; accents/breathings
//   (the ) ( / \ = | + markers) are stripped, matching the index's fold form.
// English search: whitespace-tokenized, lowercase.
// Phrase search: after intersection, verify token adjacency in segment data.
// Cross-language: AND (intersection) or OR (union) the two result sets.

import { getWork } from './works';
import { betaToGreek } from './betacode';
import { editionBase } from './data';
import { queryIndexes, comboSearchWork, grammarSearchWork, englishForms, englishTermMatcher,
  COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX,
  type SlotKind, type SlotRelation, type GrammarQuery, type ComboSlot, type QueryIndexes } from './search-advanced';

export interface AdvancedSearch {
  lemmaPick?: string[][];
  near?: { kind: SlotKind; terms?: string[]; query?: GrammarQuery;
    relation: SlotRelation; window: number; unit: 'words' | 'line'; ordered: boolean };
  shape?: GrammarQuery;
  engForms?: boolean;
  engNear?: { term: string; relation: SlotRelation; window: number };
}


// Honour Astro's base path. BASE_URL may lack a trailing slash, so strip + join.
// Same root precedence as data.ts (see its longer doc comment): a build-time
// `PUBLIC_DATA_ROOT` (e.g. the Cloudflare R2 data domain) overrides the
// BASE_URL-derived default, and the desktop app's runtime
// globalThis.__READER_DATA_ROOT__ override — read lazily so module-import
// order doesn't matter — wins over both.
const DEFAULT_ROOT = import.meta.env.PUBLIC_DATA_ROOT
  ? import.meta.env.PUBLIC_DATA_ROOT.replace(/\/+$/, '')
  : `${import.meta.env.BASE_URL.replace(/\/$/, '')}/data`;
export const ROOT = () =>
  (globalThis as { __READER_DATA_ROOT__?: string }).__READER_DATA_ROOT__ ?? DEFAULT_ROOT;
const searchBase = (work: string, ed?: string) => `${editionBase(work, ed)}/search`;

// -- Data types -----------------------------------------------------------

export interface SegMeta {
  id: string;
  book: number;
  column: string;
  head: string;
  tokens: string;  // space-joined fold token sequence
  english_head: string;
  english_slots?: Record<string, string>;
}

export type GrkIndex = Record<string, [number, number][]>; // fold → [[seg_idx, pos], ...]
export type EngIndex = Record<string, (number | [number, string])[]>;

// Greek search can match by dictionary headword ('lemma', every inflected form)
// or by the exact surface form as written ('form').
export type MatchMode = 'lemma' | 'form';

export const DEFAULT_MATCH_MODE: MatchMode = 'form';

async function lemmaTerms(terms: string[]): Promise<[string, string][][]> {
  return Promise.all(terms.map(async term => {
    if (term.includes('*')) return [[term, term]] as [string, string][];
    const folded = greekFold(term);
    if (!folded) return [[term, term]] as [string, string][];
    try {
      const file = `lemma-map/${folded[0]}.json`;
      let pending = _fileCache.get(file);
      if (!pending) {
        pending = fetch(`${ROOT()}/${file}`).then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status} for ${file}`);
          return r.json();
        });
        _fileCache.set(file, pending);
        pending.catch(() => { if (_fileCache.get(file) === pending) _fileCache.delete(file); });
      }
      const shard = await pending as Record<string, (string | [string, string])[]>;
      return shard[folded]?.length
        ? shard[folded].map(entry => typeof entry === 'string'
          ? [entry, displayLemma(entry)] as [string, string]
          : [entry[0], betaToGreek(entry[1])] as [string, string])
        : [[folded, displayLemma(folded)]] as [string, string][];
    } catch {
      return [[folded, displayLemma(folded)]] as [string, string][];
    }
  }));
}


// -- Per-work index loading (cached, lazy per file) -----------------------
//
// Each index file is fetched and cached on its own, and only when a query
// actually needs it (a Greek-only query never loads english.json, and only the
// lemma OR form index per its match mode). This keeps the request burst small:
// a Greek search over all works loads ~2 files/work, not 4 — which matters on
// Safari/WebKit, where a large simultaneous fetch burst can drop a request with
// "TypeError: Load failed" and (via Promise.all) sink the whole search.

const _fileCache = new Map<string, Promise<unknown>>();

export function loadIndex<T>(work: string, file: string, ed?: string): Promise<T> {
  const useEd = file === 'english.json' ? 'tlg' : ed;
  const key = `${work}/${useEd ?? 'tlg'}/${file}`;
  const cached = _fileCache.get(key);
  if (cached) return cached as Promise<T>;
  const p = fetch(`${searchBase(work, useEd)}/${file}`).then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${key}`);
    return file.endsWith('.bin') ? r.arrayBuffer() : r.json();
  });
  // Evict on failure so a transient drop can be retried — a rejected promise
  // must NOT stay cached (that would poison every later search in the tab).
  p.catch(() => { if (_fileCache.get(key) === p) _fileCache.delete(key); });
  _fileCache.set(key, p);
  return p as Promise<T>;
}

// Drop a work's cached index files (meta/lemma/form/english.json) so the next
// search re-fetches them. Mirrors data.ts's invalidateBookCache — same
// module-level-cache shape, same need to force a re-fetch outside normal
// browsing (tests that mock fetch differently per work run).
export function invalidateSearchIndex(work: string): void {
  for (const key of [..._fileCache.keys()]) {
    if (key.startsWith(`${work}/`)) _fileCache.delete(key);
  }
}

// Run `fn` over `items` with at most `limit` in flight at once (bounds the
// concurrent-fetch burst). Rejections propagate; callers that want per-item
// tolerance pass an `fn` that catches.
export async function pool<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i]);
    }
  });
  await Promise.all(workers);
  return out;
}

// -- Unicode Greek → Beta Code fold form ----------------------------------

const GREEK_BETA: Record<string, string> = {
  α:'a',β:'b',γ:'g',δ:'d',ε:'e',ζ:'z',η:'h',θ:'q',ι:'i',κ:'k',
  λ:'l',μ:'m',ν:'n',ξ:'c',ο:'o',π:'p',ρ:'r',σ:'s',ς:'s',τ:'t',
  υ:'u',φ:'f',χ:'x',ψ:'y',ω:'w',ϝ:'v',
};
const BETA_GREEK: Record<string, string> = Object.fromEntries(
  Object.entries(GREEK_BETA).filter(([g]) => g !== 'ς').map(([g, b]) => [b, g]),
);
export function displayLemma(fold: string): string {
  return [...fold].map((c, i) => c === 's' && i === fold.length - 1
    ? 'ς' : BETA_GREEK[c] ?? c).join('');
}

export function greekFold(input: string): string {
  const out: string[] = [];
  for (const ch of input.normalize('NFD')) {
    const lower = ch.toLowerCase();
    const b = GREEK_BETA[lower];
    if (b) out.push(b);                          // Unicode Greek → fold letter
    else if (lower >= 'a' && lower <= 'z') out.push(lower); // Beta Code Latin input
    else if (ch === "'") out.push("'");
    // skip combining marks, punctuation, Beta Code diacritics ) ( / \ = | +,
    // asterisk (handled by caller), and sigma-variant digits
  }
  return out.join('');
}

// -- Latin search fold -----------------------------------------------------
//
// Mirrors pipeline/drama_pipeline/latin.py's fold() exactly (memo §4.1):
// lowercase, u/v and i/j unified, NFD-decomposed BEFORE stripping non-base
// letters (so a macron/breve-carrying vowel folds to its base letter, not to
// nothing), with the æ/œ ligatures expanded first since Unicode NFD does not
// decompose them. Query-side counterpart to stage6_search.py's fold(key,
// 'lat') on the index-build side — both sides must agree or a Latin search
// silently misses everything.

const LATIN_LIGATURES: Record<string, string> = { æ: 'ae', œ: 'oe' };
const LATIN_FOLD_STRIP = /[^a-z']/g;

export function latinFold(input: string): string {
  let folded = input.toLowerCase();
  for (const [ligature, expansion] of Object.entries(LATIN_LIGATURES)) {
    folded = folded.split(ligature).join(expansion);
  }
  folded = folded.normalize('NFD').replace(/v/g, 'u').replace(/j/g, 'i');
  return folded.replace(LATIN_FOLD_STRIP, '');
}

// Per-language search-fold dispatch — the query-side analogue of
// stage6_search.py's fold(key, language). greekFold stays the default so
// grc (and any work whose language can't be resolved) is byte-identical to
// pre-Wave-2 behavior.
export type SourceLanguage = 'grc' | 'lat';

function sourceFold(input: string, lang: SourceLanguage): string {
  return lang === 'lat' ? latinFold(input) : greekFold(input);
}

// -- Posting-list helpers -------------------------------------------------

function grkPosting(idx: GrkIndex, term: string, lang: SourceLanguage): Set<number> {
  const wildcard = term.indexOf('*');
  if (wildcard === -1) {
    const fold = sourceFold(term, lang);
    return new Set((idx[fold] ?? []).map(([si]) => si));
  }
  // Prefix wildcard: fold the part before *, match all keys with that prefix
  const prefix = sourceFold(term.slice(0, wildcard), lang);
  const result = new Set<number>();
  for (const key of Object.keys(idx)) {
    if (key.startsWith(prefix)) {
      for (const [si] of idx[key]) result.add(si);
    }
  }
  return result;
}

function engPosting(idx: EngIndex, term: string): Set<string> {
  const keys = (posts: (number | [number, string])[]) => posts.map(p =>
    typeof p === 'number' ? `${p}\u0000` : `${p[0]}\u0000${p[1]}`);
  const word = term.toLowerCase().replace(/[^a-z'*]/g, '');
  if (!word || word === '*') return new Set(Object.values(idx).flatMap(keys));
  if (word.endsWith('*')) {
    const prefix = word.slice(0, -1);
    const result = new Set<string>();
    for (const key of Object.keys(idx)) {
      if (key.startsWith(prefix)) for (const pair of keys(idx[key])) result.add(pair);
    }
    return result;
  }
  return new Set(keys(idx[word] ?? []));
}

function intersect<T>(a: Set<T>, b: Set<T>): Set<T> {
  return new Set([...a].filter(x => b.has(x)));
}

function union<T>(a: Set<T>, b: Set<T>): Set<T> {
  return new Set([...a, ...b]);
}

// Char offsets of every English match in a segment's full text, tokenising
// exactly as the index does ([a-z']+ over the lowercased text) so a term hits
// whole tokens (and prefix* hits token starts). 'phrase' returns each phrase's
// start offset; 'all'/'any' return every matching token. One offset = one
// rendered occurrence, so repeats past the old 500-char cap now count and show.
function engMatchTerm(word: string, term: string): boolean {
  const c = term.toLowerCase().replace(/[^a-z'*]/g, '');
  if (!c || c === '*') return false;
  return c.endsWith('*') ? word.startsWith(c.slice(0, -1)) : word === c;
}
export function englishOccurrences(text: string, terms: string[], mode: SearchMode, forms = false): number[] {
  const matchers = terms.map(term => forms ? englishTermMatcher([term], true) : (word: string) => engMatchTerm(word, term));
  const low = text.toLowerCase();
  const re = /[a-z']+/g;
  const toks: { w: string; i: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(low)) !== null) toks.push({ w: m[0], i: m.index });
  if (mode === 'phrase' && terms.length > 1) {
    const out: number[] = [];
    for (let i = 0; i + terms.length <= toks.length; i++) {
      let ok = true;
      for (let j = 0; j < terms.length; j++) {
        if (!matchers[j](toks[i + j].w)) { ok = false; break; }
      }
      if (ok) out.push(toks[i].i);
    }
    return out;
  }
  return toks.filter(t => matchers.some(match => match(t.w))).map(t => t.i);
}

// English proximity uses token distances but returns character offsets for KWIC.
export function englishNearOccurrences(text: string, terms: string[], mode: SearchMode,
  near: NonNullable<AdvancedSearch['engNear']>, forms = false): number[] {
  const tokens = [...text.toLowerCase().matchAll(/[a-z']+/g)].map(m => ({ word: m[0], at: m.index! }));
  const runs = (query: string[], phrase: boolean): number[][] => {
    if (!query.length) return [];
    const tests = query.map(term => forms ? englishTermMatcher([term], true) : (word: string) => engMatchTerm(word, term));
    if (!phrase) return tokens.flatMap((t, i) => tests.some(test => test(t.word)) ? [[i]] : []);
    return tokens.flatMap((_, i) => i + query.length <= tokens.length && tests.every((test, j) => test(tokens[i + j].word))
      ? [query.map((_, j) => i + j)] : []);
  };
  const anchors = runs(terms, mode === 'phrase');
  const others = runs(near.term.trim().split(/\s+/).filter(Boolean), true);
  const window = Math.max(1, Math.min(Number.isFinite(near.window) ? near.window : COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX));
  const hits = new Set<number>();
  for (const a of anchors) for (const b of others) {
    if (a.some(i => b.includes(i))) continue;
    if (near.relation === 'before' && b[b.length - 1] >= a[0]) continue;
    if (near.relation === 'after' && b[0] <= a[a.length - 1]) continue;
    if (Math.abs(a[0] - b[0]) > window) continue;
    for (const i of [...a, ...b]) hits.add(tokens[i].at);
  }
  return [...hits].sort((a, b) => a - b);
}

// -- Public search API ----------------------------------------------------

export type SearchMode = 'all' | 'any' | 'phrase';
export type LangOp = 'and' | 'or';

export interface SearchResult {
  work: string;           // which work this hit belongs to
  meta: SegMeta;
  grkMatch: boolean;
  engMatch: boolean;
  grkPositions: number[]; // token positions in the segment where a Greek term matched
  engPositions: number[]; // char offsets in the segment's English where a term matched
  nearPositions?: number[];
  grammar?: { values: Record<string, string[]>; certain: boolean }[];
  slotId?: string;
  englishText?: string;
  // The Greek edition whose indexes this hit came from; absent for the
  // reference (TLG) text. Its meta.column is in that edition's numbering.
  ed?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  // Work ids whose index failed to load. Empty when every selected play
  // searched. Astra lane A, F10: returned alongside hits so the UI can name
  // the skipped plays instead of looking complete.
  failed: string[];
  lemmata?: string[];
  unsupported?: string[];
}

// Positions of a single term across segments: seg_idx → [token positions].
function termPositions(idx: GrkIndex, term: string, lang: SourceLanguage): Map<number, number[]> {
  const m = new Map<number, number[]>();
  const add = (posts: [number, number][]) => {
    for (const [si, pos] of posts) {
      const arr = m.get(si);
      if (arr) arr.push(pos);
      else m.set(si, [pos]);
    }
  };
  const wildcard = term.indexOf('*');
  if (wildcard === -1) {
    add(idx[sourceFold(term, lang)] ?? []);
  } else {
    const prefix = sourceFold(term.slice(0, wildcard), lang);
    for (const key of Object.keys(idx)) if (key.startsWith(prefix)) add(idx[key]);
  }
  return m;
}

// For each segment in `hits`, the token positions to highlight in a KWIC snippet.
function greekPositions(
  idx: GrkIndex,
  options: string[][],
  mode: SearchMode,
  hits: Set<number>,
  lang: SourceLanguage,
): Map<number, number[]> {
  const out = new Map<number, number[]>();
  if (mode === 'phrase' && options.length > 1) {
    for (const si of hits) {
      const at = options.map(group => new Set(group.flatMap(t => termPositions(idx, t, lang).get(si) ?? [])));
      const ps: number[] = [];
      for (const start of at[0]) {
        if (at.every((positions, n) => positions.has(start + n))) {
          for (let n = 0; n < at.length; n++) ps.push(start + n);
        }
      }
      out.set(si, ps);
    }
  } else {
    for (const t of options.flat()) {
      for (const [si, ps] of termPositions(idx, t, lang)) {
        if (!hits.has(si)) continue;
        const arr = out.get(si);
        if (arr) arr.push(...ps);
        else out.set(si, [...ps]);
      }
    }
  }
  for (const [si, ps] of out) out.set(si, [...new Set(ps)].sort((a, b) => a - b));
  return out;
}

// Search one work, returning hits tagged with that work. `lang` is the
// WORK's source language (Work.language from the registry, resolved by the
// caller) — it picks the fold function for the Greek/Latin query box, not
// to be confused with `matchMode` (lemma vs form) or `langOp` (AND/OR
// against the English box).
async function searchWork(
  work: string,
  grkTerms: string[],
  engTerms: string[],
  grkMode: SearchMode,
  engMode: SearchMode,
  langOp: LangOp,
  matchMode: MatchMode,
  lang: SourceLanguage,
  resolved: string[][],
  ed?: string,
  advanced?: AdvancedSearch,
  indexes?: QueryIndexes,
  greekOverride?: SearchResult[],
): Promise<SearchResult[]> {
  // Fetch only what this query needs: meta always; the lemma OR form Greek
  // index iff there are Greek terms; the English index iff there are English
  // terms. Kick them off together, then await.
  const metaP = loadIndex<SegMeta[]>(work, 'meta.json', ed);
  const grkP: Promise<GrkIndex | null> = grkTerms.length && !greekOverride
    ? (!ed && lang === 'grc' && indexes ? indexes.greek(work) : loadIndex<GrkIndex>(work, matchMode === 'form' ? 'form.json' : 'lemma.json', ed))
    : Promise.resolve(null);
  const engP: Promise<EngIndex | null> = engTerms.length
    ? (indexes ? indexes.english(work) : loadIndex<EngIndex>(work, 'english.json'))
    : Promise.resolve(null);
  const [meta, grkIdx, engIdx] = await Promise.all([metaP, grkP, engP]);

  const override = greekOverride ? new Map(greekOverride.map(r => [r.meta.id, r])) : null;
  let grkHits: Set<number> | null = override ? new Set(meta.flatMap((m, i) => override.has(m.id) ? [i] : [])) : null;
  let engHits: Set<string> | null = null;

  if (grkTerms.length > 0 && grkIdx) {
    const postings = resolved.map(options => options.reduce(
      (set, t) => union(set, grkPosting(grkIdx, t, lang)), new Set<number>()));
    if (grkMode === 'any') {
      grkHits = postings.reduce(union);
    } else {
      grkHits = postings.reduce(intersect);
      if (grkMode === 'phrase' && grkTerms.length > 1) {
        grkHits = new Set([...grkHits].filter(si => {
          const at = resolved.map(options => new Set(options.flatMap(t => termPositions(grkIdx, t, lang).get(si) ?? [])));
          return [...at[0]].some(start => at.every((positions, n) => positions.has(start + n)));
        }));
      }
    }
  }

  if (engTerms.length > 0 && engIdx) {
    const postings = engTerms.map(t => (advanced?.engForms ? englishForms(t.toLowerCase().replace(/[^a-z'*]/g, '')) : [t]).reduce((set, form) => union(set, engPosting(engIdx, form)), new Set<string>()));
    if (engMode === 'any') {
      engHits = postings.reduce(union);
    } else {
      engHits = postings.reduce(intersect);
      if (engMode === 'phrase' && engTerms.length > 1) {
        // Token-based phrase check on the FULL text (same routine that counts
        // occurrences), so a segment is a phrase hit iff it will render one.
        engHits = new Set([...engHits].filter(key => {
          const [raw, slot] = key.split('\u0000');
          const m = meta[Number(raw)];
          return englishOccurrences(m.english_slots?.[slot] ?? m.english_head, engTerms, 'phrase', advanced?.engForms).length > 0;
        }));
      }
    }
  }

  if (engHits && engIdx && advanced?.engNear?.term.trim()) {
    const near = advanced.engNear;
    const nearTerms = near.term.trim().split(/\s+/);
    const nearCandidates = nearTerms.map(t => (advanced.engForms ? englishForms(t.toLowerCase().replace(/[^a-z'*]/g, '')) : [t])
      .reduce((set, form) => union(set, engPosting(engIdx, form)), new Set<string>())).reduce(intersect);
    engHits = new Set([...intersect(engHits, nearCandidates)].filter(key => {
      const [raw, slot] = key.split('\u0000');
      const m = meta[Number(raw)];
      return englishNearOccurrences(m.english_slots?.[slot] ?? m.english_head, engTerms, engMode, near, advanced.engForms).length > 0;
    }));
  }

  const englishSegments = new Set([...(engHits ?? [])].map(key => Number(key.split('\u0000')[0])));
  const combined = grkHits !== null && engHits !== null
    ? langOp === 'and' ? intersect(grkHits, englishSegments) : union(grkHits, englishSegments)
    : grkHits ?? englishSegments;

  const grkPos = grkHits && grkIdx
    ? greekPositions(grkIdx, resolved, grkMode, grkHits, lang)
    : new Map<number, number[]>();

  return [...combined].sort((a, b) => a - b).flatMap(si => {
    const slotKeys = [...(engHits ?? [])].filter(k => Number(k.split('\u0000')[0]) === si);
    const selected = slotKeys.length ? slotKeys : [''];
    return selected.map((key, index) => {
      const slotId = key ? key.split('\u0000')[1] || undefined : undefined;
      const englishText = slotId ? meta[si].english_slots?.[slotId] ?? meta[si].english_head : meta[si].english_head;
      return {
        work,
        meta: meta[si],
        grkMatch: index === 0 && (grkHits?.has(si) ?? false),
        engMatch: !!key,
        grkPositions: override?.get(meta[si].id)?.grkPositions ?? grkPos.get(si) ?? [],
        ...(override?.get(meta[si].id)?.nearPositions ? { nearPositions: override.get(meta[si].id)!.nearPositions } : {}),
        ...(override?.get(meta[si].id)?.grammar ? { grammar: override.get(meta[si].id)!.grammar } : {}),
        // Each offset belongs to this translation's full text.
        engPositions: key ? (advanced?.engNear?.term.trim()
          ? englishNearOccurrences(englishText, engTerms, engMode, advanced.engNear, advanced.engForms)
          : englishOccurrences(englishText, engTerms, engMode, advanced?.engForms)) : [],
        ...(slotId ? { slotId, englishText } : {}),
        ...(ed ? { ed } : {}),
      };
    });
  });
}

// Unified search across one or more works. `matchMode` chooses the Greek index
// (lemma = all forms of a headword, form = the exact inflected token).
export async function search(
  grkQuery: string,
  engQuery: string,
  grkMode: SearchMode,
  engMode: SearchMode,
  langOp: LangOp,
  works: string[],
  matchMode: MatchMode = DEFAULT_MATCH_MODE,
  ed?: string,
  advanced?: AdvancedSearch,
): Promise<SearchResponse> {
  if (!grkQuery.trim() && !engQuery.trim() && !Object.keys(advanced?.shape ?? {}).length) return { results: [], failed: [] };
  if (!works.length) return { results: [], failed: [] };

  // Strip a leading '*' (Beta Code capital marker, e.g. *a)nqrwpos); the fold
  // form is caseless, and a leading wildcard would match everything anyway.
  const grkTerms = grkQuery.trim().split(/\s+/).filter(Boolean).map(t => t.replace(/^\*+/, ''));
  const engTerms = engQuery.trim().split(/\s+/).filter(Boolean);
  const resolvedPairs = matchMode === 'lemma' ? await Promise.all(grkTerms.map(async (term, i) => {
    const picked = advanced?.lemmaPick?.[i];
    return picked?.length ? picked.map(fold => [fold, displayLemma(fold)] as [string, string]) : (await lemmaTerms([term]))[0];
  })) : [];
  const resolved = matchMode === 'lemma' ? resolvedPairs.map(group => group.map(([fold]) => fold)) : grkTerms.map(t => [t]);

  const englishKeys = [...engTerms, ...(advanced?.engNear?.term.trim().split(/\s+/).filter(Boolean) ?? [])];
  const indexes = queryIndexes(matchMode, resolved.flat(), advanced?.engForms ? englishKeys.flatMap(t => englishForms(t.toLowerCase().replace(/[^a-z'*]/g, ''))) : englishKeys);
  const comboTerms = [...resolved.flat(), ...advanced?.near?.terms ?? []];
  const comboIndexes = advanced?.near && grkTerms.length ? {
    lemma: queryIndexes('lemma', comboTerms, [], true),
    form: queryIndexes('form', comboTerms, [], true),
  } : undefined;
  const unsupported = new Set<string>();

  // Bound how many works load at once, and let a single work's failed index
  // load drop just that work (logged) instead of rejecting the whole search.
  const failedSet = new Set<string>();
  const perWork = await pool(works, 8, async w => {
    try {
      // Work language drives which fold function the query side uses
      // (Blocker: previously every work's Greek/Latin box was folded with
      // greekFold regardless of the work's actual language, so a Latin
      // work's search silently never matched u/v or i/j variants). Default
      // to 'grc' for an unregistered work id (matches greekFold's prior
      // unconditional behavior, so existing Greek-only callers/tests are
      // unaffected).
      const lang: SourceLanguage = getWork(w)?.language ?? 'grc';
      // A Greek edition applies to a Greek-only query, and only to a play that
      // holds it. English search stays on the reference index, whose segments
      // differ from an edition's, so any query with English terms, and any play
      // without that edition, searches the reference as before.
      const useEd = ed && ed !== 'tlg' && !engTerms.length && getWork(w)?.greekEditions?.some(e => e.id === ed) ? ed : undefined;
      const heldEdition = ed && ed !== 'tlg' && getWork(w)?.greekEditions?.some(e => e.id === ed);
      if (heldEdition && (advanced?.near || advanced?.shape)) unsupported.add(w);
      let greekOverride: SearchResult[] | undefined;
      if (!heldEdition && grkTerms.length && advanced?.near) {
        const first: ComboSlot = grkTerms.length > 1
          ? { kind: 'phrase', terms: grkTerms, options: resolved, match: matchMode }
          : { kind: matchMode, terms: resolved.flat() };
        const near = advanced.near;
        greekOverride = await comboSearchWork(w, [first, near], {
          window: Math.max(1, Math.min(Number.isFinite(near.window) ? near.window : COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX)),
          unit: near.unit, ordered: near.ordered,
        }, comboIndexes);
      } else if (!heldEdition && !grkTerms.length && Object.keys(advanced?.shape ?? {}).length) {
        greekOverride = await grammarSearchWork(w, advanced!.shape!);
      }
      return await searchWork(w, grkTerms, engTerms, grkMode, engMode, langOp, matchMode, lang, resolved, useEd, advanced, indexes, greekOverride);
    } catch (err) {
      console.warn(`search: skipping ${w} —`, err);
      failedSet.add(w);
      return [] as SearchResult[];
    }
  });
  // If EVERY work failed to load (e.g. offline, or a transient window mid-deploy
  // when the index JSONs are briefly unavailable), surface it as an error to
  // retry — not as an empty result that reads as a misleading "No passages
  // found." A partial failure still returns what loaded, plus the skipped ids.
  if (failedSet.size === works.length) {
    throw new Error('Could not load the search index — check your connection and try again.');
  }
  return {
    results: perWork.flat(), failed: works.filter((w) => failedSet.has(w)),
    ...(advanced && unsupported.size ? { unsupported: works.filter(w => unsupported.has(w)) } : {}),
    ...(matchMode === 'lemma' && grkTerms.length
      ? { lemmata: [...new Set(resolvedPairs.flat().filter(([fold]) => !fold.includes('*')).map(([, display]) => display))] } : {}),
  };
}
