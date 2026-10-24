// Search state for links and browser history. Defaults follow Search.svelte.
import { DEFAULT_MATCH_MODE, type AdvancedSearch, type LangOp, type MatchMode, type SearchMode } from './search';
import { COMBO_WINDOW_DEFAULT, COMBO_WINDOW_MAX, type GrammarQuery, type SlotKind, type SlotRelation } from './search-advanced';

export interface UrlSearch extends AdvancedSearch {
  grk: string;
  eng: string;
  grkMode: SearchMode;
  engMode: SearchMode;
  matchMode: MatchMode;
  accent: boolean;
  langOp: LangOp;
  engForms: boolean;
  works: string[];
  ed: string;
}

export const emptyUrlSearch = (allWorks: string[]): UrlSearch => ({
  grk: '', eng: '', grkMode: 'all', engMode: 'all', matchMode: DEFAULT_MATCH_MODE,
  accent: false, langOp: 'and', engForms: false, works: [...allWorks], ed: 'tlg',
});

export const hasSearch = (s: UrlSearch): boolean => !!(s.grk.trim() || s.eng.trim() || Object.keys(s.shape ?? {}).length);

export function encodeSearchUrl(s: UrlSearch, allWorks: string[]): string {
  if (!hasSearch(s)) return '';
  const p = new URLSearchParams();
  if (s.grk.trim()) p.set('g', s.grk.trim());
  if (s.eng.trim()) p.set('e', s.eng.trim());
  if (s.grkMode !== 'all') p.set('gm', s.grkMode);
  if (s.engMode !== 'all') p.set('em', s.engMode);
  if (s.matchMode !== DEFAULT_MATCH_MODE) p.set('m', s.matchMode);
  if (s.accent) p.set('acc', '1');
  if (s.langOp !== 'and') p.set('op', s.langOp);
  if (s.engForms) p.set('ef', '1');
  if (s.ed && s.ed !== 'tlg') p.set('ed', s.ed);
  const chosen = new Set(s.works);
  if (allWorks.some(w => !chosen.has(w))) {
    const inside = allWorks.filter(w => chosen.has(w)).join(',');
    const outside = allWorks.filter(w => !chosen.has(w)).join(',');
    p.set('w', inside && outside.length + 1 < inside.length ? `-${outside}` : inside);
  }
  for (const key of ['lemmaPick', 'near', 'shape', 'engNear'] as const) {
    if (s[key] !== undefined) p.set(key, JSON.stringify(s[key]));
  }
  return p.toString();
}

const modes = ['all', 'any', 'phrase'] as const;
const kinds: SlotKind[] = ['lemma', 'form', 'phrase', 'grammatical'];
const relations: SlotRelation[] = ['near', 'before', 'after'];
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const strings = (v: unknown): string[] => Array.isArray(v) ? v.filter((s): s is string => typeof s === 'string' && !!s.trim()).map(s => s.trim()) : [];
function grammar(v: unknown): GrammarQuery | undefined {
  if (!record(v)) return;
  const pairs = Object.entries(v).filter(([k, x]) => /^[a-z][a-z_]*$/i.test(k) && typeof x === 'string' && /^[a-z0-9_-]+$/i.test(x));
  return pairs.length ? Object.fromEntries(pairs) as GrammarQuery : undefined;
}
const windowSize = (v: unknown) => typeof v === 'number' && Number.isFinite(v)
  ? Math.max(1, Math.min(Math.trunc(v), COMBO_WINDOW_MAX)) : COMBO_WINDOW_DEFAULT;
const relation = (v: unknown): SlotRelation => relations.includes(v as SlotRelation) ? v as SlotRelation : 'near';

export function decodeSearchUrl(search: string | URLSearchParams, allWorks: string[]): UrlSearch {
  const p = typeof search === 'string' ? new URLSearchParams(search) : search;
  const s = emptyUrlSearch(allWorks);
  s.grk = (p.get('g') ?? '').trim();
  s.eng = (p.get('e') ?? '').trim();
  const q = (p.get('q') ?? '').trim();
  if (q && !p.has('g') && !p.has('e')) {
    if (/(?=\p{L})\p{Script=Greek}/u.test(q)) s.grk = q;
    else s.eng = q;
  }
  const gm = p.get('gm'), em = p.get('em');
  if (modes.includes(gm as SearchMode)) s.grkMode = gm as SearchMode;
  if (modes.includes(em as SearchMode)) s.engMode = em as SearchMode;
  if (p.get('m') === 'lemma' || p.get('m') === 'form') s.matchMode = p.get('m') as MatchMode;
  s.accent = p.get('acc') === '1';
  s.langOp = p.get('op') === 'or' ? 'or' : 'and';
  s.engForms = p.get('ef') === '1';
  const ed = p.get('ed');
  if (ed && /^[a-z0-9_-]+$/i.test(ed)) s.ed = ed;
  const w = p.get('w');
  if (w !== null) {
    const named = new Set(w.replace(/^-/, '').split(',').map(x => x.trim()));
    s.works = allWorks.filter(id => w.startsWith('-') ? !named.has(id) : named.has(id));
  }
  const json = (key: string): unknown => { try { return JSON.parse(p.get(key) ?? 'null'); } catch { return null; } };
  const picked = json('lemmaPick');
  if (Array.isArray(picked)) s.lemmaPick = picked.map(strings);
  const shape = grammar(json('shape'));
  if (shape) s.shape = shape;
  const near = json('near');
  if (record(near) && kinds.includes(near.kind as SlotKind)) {
    const terms = strings(near.terms), query = grammar(near.query);
    if (near.kind === 'grammatical' ? !!query : !!terms.length) s.near = {
      kind: near.kind as SlotKind, ...(terms.length ? { terms } : {}), ...(query ? { query } : {}),
      relation: relation(near.relation), window: windowSize(near.window), unit: near.unit === 'line' ? 'line' : 'words', ordered: near.ordered === true,
    };
  }
  const en = json('engNear');
  if (record(en) && typeof en.term === 'string' && en.term.trim()) s.engNear = {
    term: en.term.trim(), relation: relation(en.relation), window: windowSize(en.window),
  };
  return s;
}
