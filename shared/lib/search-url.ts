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
  // The near word as typed, when a lemma near term holds its resolved headwords.
  nearText?: string;
  // The same for each further Near term, by position in nearMore.
  nearMoreText?: string[];
  // The ticked headwords of a "lemma" Near term, by row (0 = the first term),
  // where some were unticked: nf, nf2, nf3 as folds joined by "."
  nearPicks?: (string[] | null)[];
}

export const emptyUrlSearch = (allWorks: string[]): UrlSearch => ({
  grk: '', eng: '', grkMode: 'all', engMode: 'all', matchMode: DEFAULT_MATCH_MODE,
  accent: false, langOp: 'and', engForms: true, works: [...allWorks], ed: 'tlg',
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
  if (!s.engForms) p.set('ef', '0');
  if (s.ed && s.ed !== 'tlg') p.set('ed', s.ed);
  const chosen = new Set(s.works);
  if (allWorks.some(w => !chosen.has(w))) {
    const inside = allWorks.filter(w => chosen.has(w)).join(',');
    const outside = allWorks.filter(w => !chosen.has(w)).join(',');
    p.set('w', inside && outside.length + 1 < inside.length ? `-${outside}` : inside);
  }
  // Short, readable parameters rather than JSON, so a shared link stays short:
  // lp=polis.polew~qeos (ticked headwords, per typed word); n=g|l|f|p (near
  // kind) with nt (its words), nr=b|a, nw, nu=l, no=1, ng=mood.opt~tense.aor;
  // sh (a shape alone, same form as ng); en, enr, enw (English near).
  if (s.lemmaPick) p.set('lp', s.lemmaPick.map(folds => folds.join('.')).join('~'));
  if (s.near) {
    p.set('n', KIND_CODE[s.near.kind]);
    if (s.near.kind === 'grammatical') p.set('ng', encodeGrammar(s.near.query ?? {}));
    else p.set('nt', (s.near.kind === 'lemma' && s.nearText?.trim()) || (s.near.terms ?? []).join(' '));
    if (s.nearPicks?.[0]?.length) p.set('nf', s.nearPicks[0].join('.'));
    if (s.near.relation !== 'near') p.set('nr', s.near.relation[0]);
    if (s.near.unit === 'line' ? s.near.window !== 0 : s.near.window !== COMBO_WINDOW_DEFAULT) p.set('nw', String(s.near.window));
    if (s.near.unit === 'line') p.set('nu', 'l');
    if (s.near.ordered) p.set('no', '1');
  }
  // Further terms: n2/nt2/nr2/ng2, n3/…, each placed against the first word.
  (s.near ? s.nearMore ?? [] : []).slice(0, MAX_NEAR_MORE).forEach((t, i) => {
    const k = i + 2;
    p.set(`n${k}`, KIND_CODE[t.kind]);
    if (t.kind === 'grammatical') p.set(`ng${k}`, encodeGrammar(t.query ?? {}));
    else p.set(`nt${k}`, (t.kind === 'lemma' && s.nearMoreText?.[i]?.trim()) || (t.terms ?? []).join(' '));
    if (s.nearPicks?.[i + 1]?.length) p.set(`nf${k}`, s.nearPicks[i + 1]!.join('.'));
    if (t.relation !== 'near') p.set(`nr${k}`, t.relation[0]);
  });
  if (s.shape) p.set('sh', encodeGrammar(s.shape));
  if (s.engNear) {
    p.set('en', s.engNear.term);
    if (s.engNear.relation !== 'near') p.set('enr', s.engNear.relation[0]);
    if (s.engNear.window !== COMBO_WINDOW_DEFAULT) p.set('enw', String(s.engNear.window));
  }
  return p.toString();
}

// At most three Near terms in all: the first and two more.
export const MAX_NEAR_MORE = 2;
const KIND_CODE: Record<SlotKind, string> = { grammatical: 'g', lemma: 'l', form: 'f', phrase: 'p' };
// Maps, not objects: a key like "constructor" must find nothing.
const CODE_KIND = new Map<string, SlotKind>([['g', 'grammatical'], ['l', 'lemma'], ['f', 'form'], ['p', 'phrase']]);
const RELATION_CODE = new Map<string, SlotRelation>([['n', 'near'], ['b', 'before'], ['a', 'after']]);
// The categories the grammar index holds (pipeline stage 6's _FEATURES).
const GRAMMAR_KEYS = new Set(['case', 'number', 'gender', 'person', 'tense', 'mood', 'voice', 'degree', 'marker']);
const encodeGrammar = (q: GrammarQuery) => Object.entries(q).map(([k, v]) => `${k}.${v}`).join('~');
function decodeGrammar(v: string | null): GrammarQuery | undefined {
  if (!v) return;
  const pairs = v.split('~').map(pair => pair.split('.'))
    .filter(parts => parts.length === 2 && GRAMMAR_KEYS.has(parts[0]) && /^[a-z0-9_]+$/i.test(parts[1]));
  return pairs.length ? Object.fromEntries(pairs) as GrammarQuery : undefined;
}
const modes = ['all', 'any', 'phrase'] as const;
const windowSize = (v: unknown) => typeof v === 'number' && Number.isFinite(v)
  ? Math.max(1, Math.min(Math.trunc(v), COMBO_WINDOW_MAX)) : COMBO_WINDOW_DEFAULT;

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
  s.engForms = p.get('ef') !== '0';
  const ed = p.get('ed');
  if (ed && /^[a-z0-9_-]+$/i.test(ed)) s.ed = ed;
  const w = p.get('w');
  if (w !== null) {
    const named = new Set(w.replace(/^-/, '').split(',').map(x => x.trim()));
    s.works = allWorks.filter(id => w.startsWith('-') ? !named.has(id) : named.has(id));
  }
  const lp = p.get('lp');
  if (lp !== null) s.lemmaPick = lp.split('~').map(t => t.split('.').map(f => f.trim()).filter(f => /^[a-z']+$/.test(f)));
  const shape = decodeGrammar(p.get('sh'));
  if (shape) s.shape = shape;
  const kind = CODE_KIND.get(p.get('n') ?? '');
  if (kind) {
    const query = decodeGrammar(p.get('ng'));
    const text = (p.get('nt') ?? '').trim();
    const terms = text.split(/\s+/).filter(Boolean);
    if (kind === 'grammatical' ? !!query : !!terms.length) {
      s.near = {
        kind, ...(kind === 'grammatical' ? { query } : { terms }),
        relation: RELATION_CODE.get(p.get('nr') ?? 'n') ?? 'near',
        window: p.get('nu') === 'l'
          ? Math.max(0, Math.min(Math.trunc(Number(p.get('nw') ?? 0)) || 0, 10))
          : windowSize(Number(p.get('nw') ?? COMBO_WINDOW_DEFAULT)),
        unit: p.get('nu') === 'l' ? 'line' : 'words', ordered: p.get('no') === '1',
      };
      if (kind === 'lemma') s.nearText = text;
      const folds = (k: string) => (p.get(k) ?? '').split('.').filter(f => /^[a-z']+$/.test(f));
      const picks: (string[] | null)[] = [folds('nf').length && kind === 'lemma' ? folds('nf') : null];
      const more: NonNullable<UrlSearch['nearMore']> = [];
      const moreText: string[] = [];
      for (let k = 2; k < 2 + MAX_NEAR_MORE; k++) {
        const mk = CODE_KIND.get(p.get(`n${k}`) ?? '');
        if (!mk) break;
        const mq = decodeGrammar(p.get(`ng${k}`));
        const mt = (p.get(`nt${k}`) ?? '').trim();
        const mterms = mt.split(/\s+/).filter(Boolean);
        if (mk === 'grammatical' ? !mq : !mterms.length) break;
        more.push({ kind: mk, ...(mk === 'grammatical' ? { query: mq } : { terms: mterms }),
          relation: RELATION_CODE.get(p.get(`nr${k}`) ?? 'n') ?? 'near' });
        moreText.push(mk === 'lemma' ? mt : '');
        picks.push(mk === 'lemma' && folds(`nf${k}`).length ? folds(`nf${k}`) : null);
      }
      if (more.length) {
        s.nearMore = more;
        if (moreText.some(Boolean)) s.nearMoreText = moreText;
      }
      if (picks.some(Boolean)) s.nearPicks = picks.slice(0, 1 + more.length);
    }
  }
  const en = (p.get('en') ?? '').trim();
  if (en) s.engNear = {
    term: en, relation: RELATION_CODE.get(p.get('enr') ?? 'n') ?? 'near',
    window: windowSize(Number(p.get('enw') ?? COMBO_WINDOW_DEFAULT)),
  };
  return s;
}
