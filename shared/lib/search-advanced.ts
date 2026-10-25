// Reference-text grammar, proximity, phrase variants, and corpus shard lookups.
import { ROOT, loadIndex, pool, greekFold, englishWords, englishQueryWord, type GrkIndex, type EngIndex,
  type SegMeta, type SearchResult, type SearchResponse } from './search';
import { memoAsyncBy } from './memo';
type SearchOutcome = SearchResponse;
const shared = memoAsyncBy<string, unknown>(url => fetch(url).then(r => {
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}));
function loadShared<T>(path: string): Promise<T> { return shared(`${ROOT()}/${path}`) as Promise<T>; }
export function loadOffsets(work: string): Promise<Offsets> { return loadIndex(work, 'offsets.json'); }
function loadBinary(work: string, file: string): Promise<ArrayBuffer> { return loadIndex(work, file); }
export interface Offsets {
  token_count: number;
  seg_base_offset: number[];
  segments: { book: number; column: string; line_runs: ([number, number] | [number, number, string])[] }[];
  book_bounds: { book: number; start: number }[];
}

export type Reading = Record<string, string[]>;

export interface GrammarDict {
  token_count: number;
  width: number;               // bytes per column entry
  categories: string[];
  reserved: { unkeyed: number; unanalysed: number };
  sigs: Reading[][];
}

export type GrammarQuery = Record<string, string>;

type CompiledPattern = { exact: string } | { test: (key: string) => boolean; prefix: string };

function compilePattern(
  term: string,
  fold: (s: string) => string,
): CompiledPattern | null {
  const input = fold === greekFold ? term.replace(/^\*+/, '') : term;
  let pattern = '';
  for (const ch of input) {
    pattern += ch === '*' || ch === '?' ? ch : fold(ch);
  }
  if (!pattern) return null;

  if (!pattern.includes('*') && !pattern.includes('?')) {
    return { exact: pattern };
  }

  if (pattern.endsWith('*')
    && !pattern.slice(0, -1).includes('*')
    && !pattern.includes('?')) {
    const prefix = pattern.slice(0, -1);
    return { test: key => key.startsWith(prefix), prefix };
  }

  const pieces: string[] = [];
  for (const ch of pattern) {
    if (ch === '*') pieces.push("[a-z']*");
    else if (ch === '?') pieces.push("[a-z']");
    else pieces.push(ch);
  }
  const regex = new RegExp(`^${pieces.join('')}$`);
  return { test: key => regex.test(key), prefix: pattern.slice(0, pattern.search(/[*?]/)) };
}

const EN_IRREGULAR = new Map<string, string>([
  ['child', 'children'], ['foot', 'feet'], ['tooth', 'teeth'], ['goose', 'geese'],
  ['mouse', 'mice'], ['ox', 'oxen'], ['life', 'lives'], ['wife', 'wives'],
  ['knife', 'knives'], ['half', 'halves'], ['self', 'selves'], ['leaf', 'leaves'],
  ['wolf', 'wolves'], ['calf', 'calves'], ['thief', 'thieves'], ['genus', 'genera'],
  ['phenomenon', 'phenomena'], ['criterion', 'criteria'], ['basis', 'bases'],
  ['hypothesis', 'hypotheses'], ['analysis', 'analyses'], ['thesis', 'theses'],
  ['crisis', 'crises'], ['axis', 'axes'],
].flatMap(([one, many]) => [[one, many], [many, one]]));

const EN_NOT_PLURAL = new Set([
  'news', 'means', 'politics', 'ethics', 'physics', 'mathematics', 'economics', 'species', 'series',
]);

const EN_NOT_NOUN = new Set(['these', 'those']);

export function englishSingulars(w: string): string[] {
  const out = [w];
  if (EN_NOT_PLURAL.has(w)) return out;
  if (w.endsWith('ies')) out.push(`${w.slice(0, -3)}y`, w.slice(0, -1));
  else if (/(?:s|x|z|ch|sh|o)es$/.test(w)) out.push(w.slice(0, -2), w.slice(0, -1));
  else if (/[^siu']s$/.test(w)) out.push(w.slice(0, -1));
  if (w.endsWith('men')) out.push(`${w.slice(0, -3)}man`);
  const irregular = EN_IRREGULAR.get(w);
  if (irregular) out.push(irregular);
  return out.filter(s => (s.length >= 3 || EN_IRREGULAR.has(s)) && !EN_NOT_NOUN.has(s));
}

export function englishPlurals(w: string): string[] {
  const out: string[] = [];
  if (/(?:s|x|z|sh)$/.test(w)) out.push(`${w}es`);
  else if (w.endsWith('ch')) out.push(`${w}es`, `${w}s`);
  else {
    out.push(`${w}s`);
    if (w.endsWith('o')) out.push(`${w}es`);
    if (/[^aeiou]y$/.test(w)) out.push(`${w.slice(0, -1)}ies`);
  }
  if (w.endsWith('man')) out.push(`${w.slice(0, -3)}men`);
  const irregular = EN_IRREGULAR.get(w);
  if (irregular) out.push(irregular);
  return [w, `${w}'s`, ...out
    .filter(f => !EN_NOT_PLURAL.has(f))
    .flatMap(f => (f.endsWith('s') ? [f] : [f, `${f}'s`]))];
}

/** Every form "any form" looks up for one word as the index keys it (folded,
 * lowercase), the word itself first. A wildcard term is its own only form. */
export function englishForms(word: string): string[] {
  if (/[*?]/.test(word)) return [word];
  const bare = word.endsWith("'s") ? word.slice(0, -2) : word.endsWith("'") ? word.slice(0, -1) : word;
  if ((bare.length < 3 && !EN_IRREGULAR.has(bare)) || EN_NOT_NOUN.has(bare)) return [word];
  const forms = new Set([word]);
  for (const one of englishSingulars(bare)) for (const f of englishPlurals(one)) {
    forms.add(f);
    // This corpus keeps the apostrophe in plural possessives as an index key.
    if (f.endsWith('s') && !f.endsWith("'s")) forms.add(`${f}'`);
  }
  return [...forms];
}

/** True for a word (as englishWords() gives it) that the typed term matches,
 * by the same rule the index lookup uses; with `forms`, any form of it. */
export function englishTermMatcher(terms: string[], forms = false): (word: string) => boolean {
  const tests = terms.map(t => {
    if (t === '*') return () => true;
    const pattern = compilePattern(englishQueryWord(t), s => s.toLowerCase().replace(/[^a-z']/g, ''));
    if (!pattern) return () => false;
    if (!('exact' in pattern)) return pattern.test;
    if (!forms) return (w: string) => w === pattern.exact;
    const all = new Set(englishForms(pattern.exact));
    return (w: string) => all.has(w);
  });
  return word => tests.some(test => test(word));
}

function termPositions(
  idx: GrkIndex,
  term: string,
  fold: (s: string) => string = greekFold,
): Map<number, number[]> {
  const m = new Map<number, number[]>();
  const add = (posts: [number, number][]) => {
    for (const [si, pos] of posts) {
      const arr = m.get(si);
      if (arr) arr.push(pos);
      else m.set(si, [pos]);
    }
  };
  const pattern = compilePattern(term, fold);
  if (!pattern) return m;
  if ('exact' in pattern) {
    add(idx[pattern.exact] ?? []);
  } else {
    for (const key of Object.keys(idx)) if (pattern.test(key)) add(idx[key]);
  }
  return m;
}

function phraseStarts(
  idx: GrkIndex,
  terms: string[][],
  fold: (s: string) => string = greekFold,
): Map<number, number[]> {
  const out = new Map<number, number[]>();
  const perTerm = terms.map(alts => {
    if (alts.length === 1) return termPositions(idx, alts[0], fold);
    const merged = new Map<number, number[]>();
    for (const alt of alts) {
      for (const [si, ps] of termPositions(idx, alt, fold)) {
        const arr = merged.get(si);
        if (arr) arr.push(...ps);
        else merged.set(si, [...ps]);
      }
    }
    return merged;
  });
  const first = perTerm[0];
  if (!first) return out;
  for (const [si, firstPositions] of first) {
    const rest = perTerm.slice(1).map(m => new Set(m.get(si) ?? []));
    if (rest.some(s => s.size === 0)) continue;
    const starts = [...new Set(firstPositions)]
      .filter(p => rest.every((s, j) => s.has(p + j + 1)))
      .sort((a, b) => a - b);
    if (starts.length) out.set(si, starts);
  }
  return out;
}

type Stream = 'lemma' | 'form' | 'english';
interface ShardListing { streams: Partial<Record<Stream, { shards: string[]; sources: Record<string, string> }>> }
type ShardPosts = (number | [number, number | string])[];
type Shard = Record<string, Record<string, ShardPosts>>;
type Slice = Map<string, Record<string, ShardPosts>>;

/** The shard a word is filed under. Mirror of stage9's shard_name(); a shared
 * fixture pins the two, since a word looked up under another name than it was
 * filed under is simply not found. */
export function shardName(word: string): string {
  let out = '';
  for (let i = 0; i < 2; i++) {
    const c = word[i] ?? '';
    out += c >= 'a' && c <= 'z' ? c : '_';
  }
  return out;
}

export function shardsFor(pattern: CompiledPattern, listed: string[]): string[] {
  const literal = 'exact' in pattern ? pattern.exact : pattern.prefix;
  const fixed = 'exact' in pattern ? 2 : Math.min(literal.length, 2);
  const want = shardName(literal).slice(0, fixed);
  return listed.filter(name => name.slice(0, fixed) === want);
}

export async function shardSlice(stream: Stream, listed: string[], patterns: CompiledPattern[]): Promise<Slice> {
  const names = [...new Set(patterns.flatMap(p => shardsFor(p, listed)))];
  const shards = await pool(names, 8, name => loadShared<Shard>(`search-shards/${stream}/${name}.json`));
  const slice: Slice = new Map();
  for (const shard of shards) {
    for (const key of Object.keys(shard)) {
      if (patterns.some(p => ('exact' in p ? p.exact === key : p.test(key)))) slice.set(key, shard[key]);
    }
  }
  return slice;
}

export interface QueryIndexes {
  greek(work: string): Promise<GrkIndex>;
  english(work: string): Promise<EngIndex>;
}
function indexPattern(term: string, english: boolean): CompiledPattern | null {
  if (english) {
    const word = englishQueryWord(term);
    if (!word || word === '*') return { prefix: '', test: () => true };
    return word.endsWith('*') ? { prefix: word.slice(0, -1), test: k => k.startsWith(word.slice(0, -1)) } : { exact: word };
  }
  const star = term.indexOf('*');
  if (star < 0) return { exact: greekFold(term) };
  const prefix = greekFold(term.slice(0, star));
  return { prefix, test: k => k.startsWith(prefix) };
}
export function queryIndexes(greekStream: 'lemma' | 'form', grkTerms: string[], engTerms: string[], fullPatterns = false): QueryIndexes {
  let listing: Promise<ShardListing | null> | undefined;
  const getListing = () => listing ??= fetch(`${ROOT()}/search-shards/index.json`).then(r => r.ok ? r.json() as Promise<ShardListing> : null).catch(() => null);
  const slices = new Map<Stream, Promise<Slice>>();
  const index = async (stream: Stream, work: string, terms: string[]): Promise<unknown> => {
    const entry = (await getListing())?.streams?.[stream];
    if (!entry || !Object.hasOwn(entry.sources, work)) return loadIndex(work, `${stream}.json`);
    let slice = slices.get(stream);
    if (!slice) {
      const patterns = terms.map(t => fullPatterns && stream !== 'english' ? compilePattern(t, greekFold) : indexPattern(t, stream === 'english')).filter((p): p is CompiledPattern => p !== null);
      slice = shardSlice(stream, entry.shards, patterns);
      slices.set(stream, slice);
    }
    const idx: Record<string, unknown> = Object.create(null);
    for (const [key, bySource] of await slice) if (Object.hasOwn(bySource, work)) idx[key] = bySource[work];
    if (stream === 'english' && terms.some(t => !('exact' in indexPattern(t, true)!))) {
      // Stage 6 inserts words in text order. Keep that order for wildcard
      // unions: it also sets the order of translations in the old results.
      const ordered: Record<string, unknown> = Object.create(null);
      const meta = await loadIndex<SegMeta[]>(work, 'meta.json');
      for (const segment of meta) for (const text of [segment.english_head, ...Object.values(segment.english_slots ?? {})]) {
        for (const { word } of englishWords(text)) {
          if (Object.hasOwn(idx, word)) ordered[word] = idx[word];
        }
      }
      return Object.assign(ordered, idx);
    }
    return idx;
  };
  return {
    greek: work => index(greekStream, work, grkTerms) as Promise<GrkIndex>,
    english: work => index('english', work, engTerms) as Promise<EngIndex>,
  };
}

export interface OffsetRef { seg_idx: number; pos: number; book: number; column: string; line: number; sub?: string }

export function offsetRef(offsets: Offsets, global: number): OffsetRef | null {
  const base = offsets.seg_base_offset;
  if (!base.length || global < 0 || global >= offsets.token_count) return null;
  const [seg_idx, pos] = locate(base, global);
  const seg = offsets.segments[seg_idx];
  if (!seg) return null;
  let left = pos;
  for (const [line, count, sub] of seg.line_runs) {
    if (left < count) {
      return { seg_idx, pos, book: seg.book, column: seg.column, line, ...(sub ? { sub } : {}) };
    }
    left -= count;
  }
  return null;
}


export function readingSatisfies(reading: Reading, query: GrammarQuery): boolean {
  for (const category in query) {
    if (!reading[category]?.includes(query[category])) return false;
  }
  return true;
}

export function compileQuery(dict: GrammarDict, query: GrammarQuery) {
  const matches = new Map<number, { values: Record<string, string[]>; certain: boolean }>();
  dict.sigs.forEach((readings, id) => {
    if (!readings.length || !readings.some(r => readingSatisfies(r, query))) return;
    const values: Record<string, string[]> = {};
    for (const category in query) {
      const licensed = new Set<string>();
      for (const reading of readings) for (const v of reading[category] ?? []) licensed.add(v);
      values[category] = [...licensed].sort();
    }
    const certain =
      readings.every(r => readingSatisfies(r, query)) &&
      Object.values(values).every(v => v.length === 1);
    matches.set(id, { values, certain });
  });
  return matches;
}

export function locate(base: number[], global: number): [number, number] {
  let lo = 0;
  let hi = base.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (base[mid] <= global) lo = mid;
    else hi = mid - 1;
  }
  return [lo, global - base[lo]];
}

export async function grammarSearchWork(work: string, query: GrammarQuery): Promise<SearchResult[]> {
  const [meta, offsets, dict] = await Promise.all([
    loadIndex<SegMeta[]>(work, 'meta.json'),
    loadIndex<Offsets>(work, 'offsets.json'),
    loadIndex<GrammarDict>(work, 'grammar-dict.json'),
  ]);
  if (dict.token_count !== offsets.token_count) {
    throw new Error(`${work}: grammar/offsets built from different runs`);
  }
  const wanted = compileQuery(dict, query);
  if (!wanted.size) return [];

  const buffer = await loadBinary(work, 'grammar-col.bin');
  const column = dict.width === 4 ? new Uint32Array(buffer) : new Uint16Array(buffer);
  if (column.length !== offsets.token_count) {
    throw new Error(`${work}: grammar column length does not match token count`);
  }

  const bySeg = new Map<number, SearchResult>();
  for (let global = 0; global < column.length; global++) {
    const hit = wanted.get(column[global]);
    if (!hit) continue;
    const [si, pos] = locate(offsets.seg_base_offset, global);
    let result = bySeg.get(si);
    if (!result) {
      result = {
        work,
        meta: meta[si],
        grkMatch: true,
        engMatch: false,
        grkPositions: [],
        engPositions: [],
        grammar: [],
      };
      bySeg.set(si, result);
    }
    result.grkPositions.push(pos);
    result.grammar!.push(hit);
  }
  return [...bySeg.keys()].sort((a, b) => a - b).map(si => bySeg.get(si)!);
}

export async function searchGrammar(
  query: GrammarQuery,
  works: string[],
): Promise<SearchOutcome> {
  if (!Object.keys(query).length || !works.length) {
    return { results: [], failed: [] };
  }
  const failed: string[] = [];
  const perWork = await pool(works, 8, async w => {
    try {
      return await grammarSearchWork(w, query);
    } catch (err) {
      console.warn(`searchGrammar: skipping ${w} —`, err);
      failed.push(w);
      return [] as SearchResult[];
    }
  });
  if (failed.length === works.length) {
    throw new Error('Could not load the grammar index — check your connection and try again.');
  }
  return { results: perWork.flat(), failed };
}


export const VARIANT_READING_CAP = 64;

export interface VariantOutcome extends SearchOutcome {
  readings: string[][];        // the lemma readings actually tried
  productive: string[][];      // those that matched anything
  cappedFrom: number;          // 0 unless the fan-out was truncated
}

/** The headwords each folded word can belong to, one list per word.
 *
 * `null` means the corpus map itself could not be loaded: there is nothing to
 * widen with, and a caller should fall back to matching what was typed rather
 * than report an empty corpus. A word the map does not record yields an empty
 * list, which callers read differently — the phrase search takes it as nothing
 * to widen, the phrase index falls back to that one word as typed.
 */
export async function lemmaOptions(folds: string[]): Promise<string[][] | null> {
  const perTerm: string[][] = [];
  for (const fold of folds) {
    const letter = /^[a-z]/.test(fold) ? fold[0] : '_';
    try {
      const shard = await loadShared<Record<string, (string | [string, string])[]>>(`lemma-map/${letter}.json`);
      perTerm.push(Object.hasOwn(shard, fold) ? shard[fold].map(e => typeof e === 'string' ? e : e[0]) : []);
    } catch {
      return null;
    }
  }
  return perTerm;
}

export function lemmaReadings(perTerm: string[][], cap: number): { readings: string[][]; total: number } {
  let total = 1;
  for (const options of perTerm) total *= Math.max(options.length, 1);
  let readings: string[][] = [[]];
  for (const options of perTerm) {
    const next: string[][] = [];
    for (const so_far of readings) {
      for (const option of options) {
        if (next.length >= cap) break;
        next.push([...so_far, option]);
      }
    }
    readings = next;
  }
  return { readings, total };
}

export async function searchPhraseVariants(
  grkQuery: string,
  works: string[],
): Promise<VariantOutcome> {
  const terms = grkQuery.trim().split(/\s+/).filter(Boolean).map(t => t.replace(/^\*+/, ''));
  const empty: VariantOutcome = {
    results: [], failed: [], readings: [], productive: [], cappedFrom: 0,
  };
  if (terms.length < 2 || !works.length) return empty;

  const folds = terms.map(t => greekFold(t));
  if (folds.some(f => !f)) return empty;
  const perTerm = await lemmaOptions(folds);
  if (!perTerm) return empty;   // without the map there is nothing to widen with
  if (perTerm.some(options => !options.length)) return empty;

  const { readings, total } = lemmaReadings(perTerm, VARIANT_READING_CAP);
  const cappedFrom = total > readings.length ? total : 0;

  const failed: string[] = [];
  const productiveKeys = new Set<string>();
  const indexes = queryIndexes('lemma', [...new Set(readings.flat())], []);
  const perWork = await pool(works, 8, async work => {
    try {
      const idx = await indexes.greek(work);
      const bySeg = new Map<number, Set<number>>();
      for (const reading of readings) {
        const starts = phraseStarts(idx, reading.map(t => [t]));
        if (starts.size) productiveKeys.add(reading.join(' '));
        for (const [si, positions] of starts) {
          let seen = bySeg.get(si);
          if (!seen) { seen = new Set(); bySeg.set(si, seen); }
          for (const start of positions) {
            for (let k = 0; k < reading.length; k++) seen.add(start + k);
          }
        }
      }
      if (!bySeg.size) return [] as SearchResult[];
      const meta = await loadIndex<SegMeta[]>(work, 'meta.json');
      return [...bySeg.keys()].sort((a, b) => a - b).map(si => ({
        work,
        meta: meta[si],
        grkMatch: true,
        engMatch: false,
        grkPositions: [...bySeg.get(si)!].sort((a, b) => a - b),
        engPositions: [],
      } as SearchResult));
    } catch (err) {
      console.warn(`searchPhraseVariants: skipping ${work} —`, err);
      failed.push(work);
      return [] as SearchResult[];
    }
  });
  if (failed.length === works.length) {
    throw new Error('Could not load the search index — check your connection and try again.');
  }
  return {
    results: perWork.flat(),
    failed,
    readings,
    productive: readings.filter(r => productiveKeys.has(r.join(' '))),
    cappedFrom,
  };
}


export type SlotKind = 'phrase' | 'form' | 'lemma' | 'grammatical';

export type SlotRelation = 'near' | 'before' | 'after';

export interface ComboSlot {
  kind: SlotKind;
  terms?: string[];
  options?: string[][];
  match?: 'lemma' | 'form';
  query?: GrammarQuery;
  relation?: SlotRelation;
}

export type WindowUnit = 'words' | 'line';

export interface ComboOptions {
  window: number;          // words; ignored for the line unit
  unit: WindowUnit;
  ordered: boolean;        // slots must appear in the order given
}

export interface SlotHit { start: number; span: number; certain: boolean; values?: Record<string, string[]> }

export const COMBO_WINDOW_DEFAULT = 10;
export const COMBO_WINDOW_MAX = 50;

export function slotHits(
  slot: ComboSlot,
  base: number[],
  lemmaIdx: GrkIndex | null,
  formIdx: GrkIndex | null,
  dict: GrammarDict | null,
  column: Uint16Array | Uint32Array | null,
): SlotHit[] {
  const out: SlotHit[] = [];
  if (slot.kind === 'grammatical') {
    if (!dict || !column || !slot.query) return out;
    const wanted = compileQuery(dict, slot.query);
    if (!wanted.size) return out;
    for (let g = 0; g < column.length; g++) {
      const hit = wanted.get(column[g]);
      if (hit) out.push({ start: g, span: 1, certain: hit.certain, values: hit.values });
    }
    return out;
  }

  const terms = slot.terms ?? slot.options?.map(p => p[0] ?? '') ?? [];
  if (!terms.length) return out;
  const idx = slot.kind === 'lemma' || slot.match === 'lemma' ? lemmaIdx : formIdx;
  if (!idx) return out;

  if (slot.kind === 'phrase') {
    for (const [si, starts] of phraseStarts(idx, slot.options ?? terms.map(t => [t]))) {
      for (const p of starts) out.push({ start: base[si] + p, span: terms.length, certain: true });
    }
    return out;
  }
  for (const term of terms) {
    for (const [si, positions] of termPositions(idx, term)) {
      for (const p of positions) out.push({ start: base[si] + p, span: 1, certain: true });
    }
  }
  return out;
}

export function unitRange(starts: number[], global: number, total: number): [number, number] {
  let lo = 0;
  let hi = starts.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (starts[mid] <= global) lo = mid;
    else hi = mid - 1;
  }
  return [starts[lo] ?? 0, lo + 1 < starts.length ? starts[lo + 1] : total];
}

export function lowerBound(hits: SlotHit[], target: number): number {
  let lo = 0;
  let hi = hits.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (hits[mid].start < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function lineStarts(offsets: Offsets): number[] {
  const out: number[] = [];
  offsets.segments.forEach((seg, i) => {
    let at = offsets.seg_base_offset[i];
    for (const [, count] of seg.line_runs) { out.push(at); at += count; }
  });
  return out;
}

export interface ComboHit {
  work: string;
  seg_idx: number;
  pos: number;             // token position of the leftmost slot, within its segment
  global: number;
  positions: number[];     // every matched token position in that segment
  certain: boolean;        // false if ANY slot rested on an ambiguous parse
  values?: Record<string, string[]>;
}

export function comboWindows(
  perSlot: SlotHit[][],
  opts: ComboOptions,
  offsets: Offsets,
  relations: SlotRelation[] = [],
  identities: string[] = [],
): { start: number; end: number; hits: SlotHit[] }[] {
  if (!perSlot.length || perSlot.some(h => !h.length)) return [];
  const sorted = perSlot.map(h => [...h].sort((a, b) => a.start - b.start));
  const total = offsets.token_count;
  const bookStarts = offsets.book_bounds.map(b => b.start);
  const lines = opts.unit === 'line' ? lineStarts(offsets) : null;

  const structural = (at: number): [number, number] => {
    let lo = 0;
    let hi = total;
    const clamp = ([s, e]: [number, number]) => { if (s > lo) lo = s; if (e < hi) hi = e; };
    clamp(unitRange(bookStarts, at, total));                       // never cross a book
    if (opts.unit === 'line' && lines) clamp(unitRange(lines, at, total));
    return [lo, hi];
  };

  const out: { start: number; end: number; hits: SlotHit[] }[] = [];
  for (const anchor of sorted[0]) {
    const [unitLo, unitHi] = structural(anchor.start);
    if (anchor.start + anchor.span > unitHi) continue;   // the anchor's own run must fit

    const reach = opts.unit === 'words' ? opts.window : total;
    const lo = Math.max(unitLo, anchor.start - reach);
    const hi = Math.min(unitHi, anchor.start + reach + 1);
    const feasible: SlotHit[][] = [[anchor]];
    let possible = true;
    for (let s = 1; s < sorted.length && possible; s++) {
      const relation = relations[s] ?? 'near';
      const from = relation === 'after' ? Math.max(lo, anchor.start + anchor.span) : lo;
      const to = relation === 'before' ? Math.min(hi, anchor.start + 1) : hi;
      const picks: SlotHit[] = [];
      for (let i = lowerBound(sorted[s], from); i < sorted[s].length; i++) {
        const h = sorted[s][i];
        if (h.start >= to) break;
        if (h.start + h.span > unitHi) continue;
        if (relation === 'before' && h.start + h.span > anchor.start) continue;
        picks.push(h);
      }
      if (!picks.length) possible = false;
      else feasible.push(picks);
    }
    if (!possible) continue;

    const starts = new Set<number>([anchor.start]);
    for (const picks of feasible) for (const h of picks) {
      if (h.start <= anchor.start) starts.add(h.start);
    }
    let chosen: SlotHit[] | null = null;
    for (const s0 of [...starts].sort((a, b) => a - b)) {
      if (opts.unit === 'words' && anchor.start - s0 > opts.window) continue;
      const limit = opts.unit === 'words' ? s0 + opts.window : unitHi;
      const take: SlotHit[] = [anchor];
      let cursor = anchor.start + anchor.span;   // for the whole-query order lock
      let ok = true;
      const used = new Map<string, Set<number>>();
      const claim = (s: number, at: number): boolean => {
        const id = identities[s];
        if (!id) return true;
        let taken = used.get(id);
        if (!taken) { taken = new Set(); used.set(id, taken); }
        if (taken.has(at)) return false;
        taken.add(at);
        return true;
      };
      claim(0, anchor.start);
      for (let s = 1; s < feasible.length; s++) {
        const relation = relations[s] ?? 'near';
        const from = opts.ordered ? Math.max(s0, cursor) : s0;
        const window = feasible[s].filter(h => h.start >= from && h.start <= limit);
        const ordered = relation === 'before' ? [...window].reverse() : window;
        const pick = ordered.find(h => claim(s, h.start));
        if (!pick) { ok = false; break; }
        take.push(pick);
        cursor = pick.start + pick.span;
      }
      if (ok) { chosen = take; break; }
    }
    if (!chosen) continue;
    out.push({
      start: Math.min(...chosen.map(h => h.start)),
      end: Math.max(...chosen.map(h => h.start + h.span - 1)),
      hits: chosen,
    });
  }
  return out;
}

function comboIndexes(slots: ComboSlot[]): { lemma: QueryIndexes; form: QueryIndexes } {
  return {
    lemma: queryIndexes('lemma', slots.filter(s => s.kind === 'lemma' || s.match === 'lemma').flatMap(s => s.options?.flat() ?? s.terms ?? []), [], true),
    form: queryIndexes('form', slots.filter(s => s.kind === 'form' || (s.kind === 'phrase' && s.match !== 'lemma')).flatMap(s => s.options?.flat() ?? s.terms ?? []), [], true),
  };
}

export async function comboSearchWork(
  work: string,
  slots: ComboSlot[],
  opts: ComboOptions,
  indexes = comboIndexes(slots),
): Promise<SearchResult[]> {
  const needLemma = slots.some(s => s.kind === 'lemma' || (s.kind === 'phrase' && s.match === 'lemma'));
  const needForm = slots.some(s => s.kind === 'form' || (s.kind === 'phrase' && s.match !== 'lemma'));
  const needGrammar = slots.some(s => s.kind === 'grammatical');

  const [meta, offsets, lemmaIdx, formIdx, dict] = await Promise.all([
    loadIndex<SegMeta[]>(work, 'meta.json'),
    loadIndex<Offsets>(work, 'offsets.json'),
    needLemma ? indexes.lemma.greek(work) : Promise.resolve(null),
    needForm ? indexes.form.greek(work) : Promise.resolve(null),
    needGrammar ? loadIndex<GrammarDict>(work, 'grammar-dict.json') : Promise.resolve(null),
  ]);
  let column: Uint16Array | Uint32Array | null = null;
  if (dict) {
    if (dict.token_count !== offsets.token_count) {
      throw new Error(`${work}: grammar/offsets built from different runs`);
    }
    const buffer = await loadBinary(work, 'grammar-col.bin');
    column = dict.width === 4 ? new Uint32Array(buffer) : new Uint16Array(buffer);
    if (column.length !== offsets.token_count) {
      throw new Error(`${work}: grammar column length does not match token count`);
    }
  }

  const base = offsets.seg_base_offset;
  const perSlot = slots.map(s => slotHits(s, base, lemmaIdx, formIdx, dict, column));
  const slotIds = slots.map(s => JSON.stringify([
    s.kind, s.match, s.options,
    s.terms ? (s.kind === 'phrase' ? s.terms : [...s.terms].sort()) : null,
    s.query ? Object.fromEntries(Object.entries(s.query).sort(([a], [b]) => a.localeCompare(b))) : null,
  ]));
  const duplicated = new Set(slotIds.filter((id, i) => slotIds.indexOf(id) !== i));
  const windows = comboWindows(
    perSlot, opts, offsets,
    slots.map(s => s.relation ?? 'near'),
    slotIds.map(id => (duplicated.has(id) ? id : '')),
  );

  const bySeg = new Map<number, SearchResult>();
  const resultAt = (si: number): SearchResult => {
    let result = bySeg.get(si);
    if (!result) {
      result = { work, meta: meta[si], grkMatch: true, engMatch: false,
        grkPositions: [], nearPositions: [], engPositions: [], grammar: [], nearHits: [] };
      bySeg.set(si, result);
    }
    return result;
  };
  // Each window as the reader sees it: the first term's run, filed under the
  // passage it starts in, with the other terms that answered it, wherever they
  // stand (the merged position lists below cannot say which word answered which).
  const hitByStart = new Map<number, NonNullable<SearchResult['nearHits']>[number]>();
  for (const w of windows) {
    const anchor = w.hits[0];
    if (!anchor) continue;
    const [asi, apos] = locate(base, anchor.start);
    let hit = hitByStart.get(anchor.start);
    if (!hit) {
      hit = { pos: apos, span: anchor.span, partners: [] };
      hitByStart.set(anchor.start, hit);
      resultAt(asi).nearHits!.push(hit);
    }
    for (const h of w.hits.slice(1)) for (let k = 0; k < h.span; k++) {
      const [psi, ppos] = locate(base, h.start + k);
      const segId = meta[psi].id;
      if (!hit.partners.some(p => p.segId === segId && p.pos === ppos)) {
        hit.partners.push({ segId, pos: ppos, before: h.start + k < anchor.start });
      }
    }
  }
  for (const w of windows) for (const [slot, h] of w.hits.entries()) {
    for (let k = 0; k < h.span; k++) {
      const [si, pos] = locate(base, h.start + k);
      const result = resultAt(si);
      const positions = slot === 0 ? result.grkPositions : result.nearPositions!;
      const previous = positions.indexOf(pos);
      const info = { values: h.values ?? {}, certain: h.certain };
      if (previous < 0) {
        positions.push(pos);
        if (slot !== 0) result.grammar!.push(info);
      } else if (slot !== 0 && h.values) {
        const old = result.grammar![previous];
        for (const [key, values] of Object.entries(h.values)) old.values[key] = [...new Set([...(old.values[key] ?? []), ...values])].sort();
        old.certain = old.certain && h.certain;
      }
    }
  }
  for (const result of bySeg.values()) {
    result.grkPositions.sort((a, b) => a - b);
    const order = result.nearPositions!.map((p, i) => [p, i] as const).sort((a, b) => a[0] - b[0]);
    result.nearPositions = order.map(([p]) => p);
    result.grammar = order.map(([, i]) => result.grammar![i]);
    result.nearHits!.sort((a, b) => a.pos - b.pos);
  }
  return [...bySeg.keys()].sort((a, b) => a - b).map(si => bySeg.get(si)!);
}

export async function searchCombo(
  slots: ComboSlot[],
  opts: ComboOptions,
  works: string[],
): Promise<SearchOutcome> {
  const usable = slots.filter(s =>
    s.kind === 'grammatical' ? Object.keys(s.query ?? {}).length : (s.terms ?? s.options ?? []).length);
  if (usable.length < 2 || !works.length) return { results: [], failed: [] };

  const bounded: ComboOptions = {
    ...opts,
    window: Math.max(1, Math.min(Number.isFinite(opts.window) ? opts.window : COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX)),
  };
  const indexes = comboIndexes(usable);
  const failed: string[] = [];
  const perWork = await pool(works, 8, async w => {
    try {
      return await comboSearchWork(w, usable, bounded, indexes);
    } catch (err) {
      console.warn(`searchCombo: skipping ${w} —`, err);
      failed.push(w);
      return [] as SearchResult[];
    }
  });
  if (failed.length === works.length) {
    throw new Error('Could not load the search index — check your connection and try again.');
  }

  return { results: perWork.flat(), failed };
}
