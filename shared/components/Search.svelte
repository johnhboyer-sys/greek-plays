<script lang="ts">
  import { tick, onMount } from 'svelte';
  import { search, greekFold, englishWords, type SearchMode, type LangOp, type MatchMode, type SearchResult, type AdvancedSearch } from '../lib/search';
  import { COMBO_WINDOW_DEFAULT, type SlotKind, type SlotRelation } from '../lib/search-advanced';
  import { decodeSearchUrl, encodeSearchUrl, hasSearch, type UrlSearch } from '../lib/search-url';
  import { fetchBook, fetchChapters, fetchSections, readerHref, dataRoot, fetchLemmaPickerShard, fetchLemmaGlosses, lemmaEntryHref, type Segment, type GreekLine, type ChapterRef, type SectionRef, type TranslationCredit } from '../lib/data';
  import { editionPicker } from '../lib/edition-picker';
  import { WORKS, getWork, workPath, WORK_ORDER } from '../lib/works';
  import { getAuthor, AUTHORS } from '../lib/authors';
  import { formatCite, formatLocValue, schemeFor, groupUnitNoun } from '../lib/citation';
  import { BETA_LETTERS, BETA_MARKS, BETA_EXAMPLES } from '../lib/beta-chart';
  import { liveGreek, betaToGreek } from '../lib/betacode';

  // Astra lane A, F10: display titles, comma-separated; Oxford comma before
  // the last when there are three or more.
  function failedPlaysPhrase(ids: string[]): string {
    const titles = ids.map((id) => getWork(id)?.title ?? id);
    if (titles.length < 3) return titles.join(', ');
    return `${titles.slice(0, -1).join(', ')}, and ${titles[titles.length - 1]}`;
  }

  // One match occurrence, located precisely enough to label and jump to.
  interface Instance {
    lang: 'grk' | 'eng';
    column: string;
    line: number;
    ref: string;       // e.g. "1097a15"
    html: string;      // KWIC snippet
    jumpUrl: string;
    documentOrder: number;
    // Present only for an English hit whose passage carries its own
    // per-passage translation credit (EnglishChunk.credit — a column_sources
    // override, e.g. Gorgias B11/B11a's CC BY-NC-ND Parnassos translations).
    // Finding 1 (Sol review): the search surface used to show and export this
    // licensed English with no attribution at all. Compact, not the full
    // on-screen citation — see formatSearchCredit below.
    credit?: string;
  }
  // All instances within one chapter, merged into a single (collapsible) card.
  interface ChapterGroup {
    key: string;
    work: string;
    book: number;
    chapter: string;
    bekker: string;
    order: number;     // chapter position within the book, for sorting
    workWide: boolean;
    instances: Instance[];
  }

  let grkQuery = '';
  let engQuery = '';
  // Greek and English each get an independent match mode (Change 5).
  let grkMode: SearchMode = 'all';
  let engMode: SearchMode = 'all';
  let langOp: LangOp = 'and';
  let matchMode: MatchMode = 'form';
  // Greek text to search (plan 4.5): the reference, or one of the editions the
  // registry lists, behind PUBLIC_EDITIONS=1. One choice per distinct edition id;
  // a play that lacks the chosen edition searches the reference.
  let greekEd = 'tlg';
  const editionChoices = import.meta.env.PUBLIC_EDITIONS === '1'
    ? [...new Map(WORKS.flatMap(w => (w.greekEditions ?? []).filter(e => e.id !== 'tlg')
        .map(e => [e.id, { id: e.id, label: e.short.replace(/\s*\(\d{4}\)$/, '') }] as const))).values()]
    : [];
  // ── Search step 2: the Aristotle reader's advanced search, in B's rows ──
  // English: "Any form of the word" lets each word match its plural and
  // possessive (man, men, man's), as the Aristotle reader's English does.
  let engForms = true;

  // LSJ: the headwords each typed Greek word can belong to, offered as checks
  // while the reader types (any form of the word only). One check per fold key:
  // the index is accent-folded, so headwords sharing a key cannot be split.
  interface LemmaCand { fold: string; heads: string[]; gloss: string; n: number; slug?: string; on: boolean }
  interface TermCands { term: string; cands: LemmaCand[] }
  let lemmaCands: TermCands[] = [];
  let lemmaRequest = 0;

  // Near: a second Greek term placed against the first (the Greek box).
  type NearKind = 'none' | 'grammatical' | 'form' | 'lemma';
  let nearKind: NearKind = 'none';
  let nearText = '';
  let nearRel: SlotRelation = 'near';
  let nearWindow = COMBO_WINDOW_DEFAULT;
  let nearUnit: 'words' | 'line' = 'words';
  let nearOrdered = false;
  const WINDOW_OPTS = [1, 2, 3, 5, 10, 15, 20, 30, 50];

  // Shape: the second term's grammar. The vocabulary is Morpheus's, nothing
  // inferred: there is no part-of-speech field, so "a verb form" only chooses
  // which categories are offered, and the parse decides what matches.
  type ShapeClass = 'verb' | 'noun' | 'word';
  let shapeClass: ShapeClass = 'verb';
  let shape: Record<string, string> = {};
  const SHAPE_CATS: Record<ShapeClass, { key: string; any: string; values: [string, string][] }[]> = {
    verb: [
      { key: 'tense', any: 'any tense', values: [['pres', 'present'], ['imperf', 'imperfect'], ['fut', 'future'], ['aor', 'aorist'], ['perf', 'perfect'], ['plup', 'pluperfect'], ['futperf', 'future perfect']] },
      { key: 'mood', any: 'any mood', values: [['ind', 'indicative'], ['subj', 'subjunctive'], ['opt', 'optative'], ['imperat', 'imperative'], ['inf', 'infinitive'], ['part', 'participle']] },
      { key: 'voice', any: 'any voice', values: [['act', 'active'], ['mid', 'middle'], ['pass', 'passive'], ['mp', 'middle or passive']] },
      { key: 'person', any: 'any person', values: [['1st', 'first person'], ['2nd', 'second person'], ['3rd', 'third person']] },
      { key: 'number', any: 'any number', values: [['sg', 'singular'], ['pl', 'plural'], ['dual', 'dual']] },
    ],
    noun: [
      { key: 'case', any: 'any case', values: [['nom', 'nominative'], ['gen', 'genitive'], ['dat', 'dative'], ['acc', 'accusative'], ['voc', 'vocative']] },
      { key: 'number', any: 'any number', values: [['sg', 'singular'], ['pl', 'plural'], ['dual', 'dual']] },
      { key: 'gender', any: 'any gender', values: [['masc', 'masculine'], ['fem', 'feminine'], ['neut', 'neuter']] },
      { key: 'degree', any: 'any degree', values: [['comp', 'comparative'], ['superl', 'superlative']] },
    ],
    word: [
      { key: 'marker', any: 'any class', values: [['adverb', 'adverb'], ['particle', 'particle'], ['prep', 'preposition'], ['conj', 'conjunction'], ['interrog', 'interrogative'], ['exclam', 'exclamation'], ['indecl', 'indeclinable'], ['numeral', 'numeral']] },
    ],
  };
  // A function, not a reactive value: a search reopened from the address runs
  // before reactive values catch up with the state it restored.
  const shapeQueryOf = (cls: ShapeClass, sh: Record<string, string>) =>
    Object.fromEntries(SHAPE_CATS[cls].filter(c => sh[c.key]).map(c => [c.key, sh[c.key]]));
  $: shapeQuery = shapeQueryOf(shapeClass, shape);

  // English near: a second English word, in the same translation.
  let engNearText = '';
  let engNearRel: SlotRelation = 'near';
  let engNearWindow = COMBO_WINDOW_DEFAULT;

  // The headwords a typed word can belong to (this repo's lemma-map shards).
  const lemmaMapCache = new Map<string, Promise<Record<string, (string | [string, string])[]>>>();
  function lemmaMapShard(letter: string) {
    let p = lemmaMapCache.get(letter);
    if (!p) {
      p = fetch(`${dataRoot()}/lemma-map/${letter}.json`).then(r => (r.ok ? r.json() : {}));
      p.catch(() => lemmaMapCache.delete(letter));
      lemmaMapCache.set(letter, p);
    }
    return p;
  }
  async function headFolds(term: string): Promise<string[]> {
    const fold = greekFold(term.replace(/^\*+/, ''));
    if (!fold || term.includes('*')) return [];
    const shard = await lemmaMapShard(/[a-z]/.test(fold[0]) ? fold[0] : '_');
    const heads = (shard[fold] ?? []).map(e => (typeof e === 'string' ? e : e[0]));
    return heads.length ? [...new Set(heads)] : [fold];
  }
  async function candidatesFor(term: string, keep: Map<string, boolean>): Promise<LemmaCand[]> {
    const folds = await headFolds(term);
    return Promise.all(folds.map(async fold => {
      let n = 0; let heads: string[] = [betaToGreek(fold)]; let slug: string | undefined;
      try {
        const choice = (await fetchLemmaPickerShard(/[a-z]/.test(fold[0]) ? fold[0] : '_'))[fold];
        if (choice) { n = choice.n; if (choice.c.length) heads = choice.c.map(c => c.h); slug = choice.c.find(c => c.s)?.s; }
      } catch { /* no picker data: the check still searches */ }
      const gloss = slug ? (await fetchLemmaGlosses(slug).catch(() => [] as string[]))[0] ?? '' : '';
      return { fold, heads, gloss, n, slug, on: keep.get(fold) ?? true };
    })).then(list => list.sort((a, b) => b.n - a.n));
  }
  let lemmaTimer: ReturnType<typeof setTimeout> | undefined;
  $: queueLemmaCands(matchMode === 'lemma' ? grkQuery : '');
  function queueLemmaCands(q: string) {
    clearTimeout(lemmaTimer);
    lemmaRequest++;   // a load for the old words must not land
    lemmaTimer = setTimeout(() => void loadLemmaCands(q), 250);
  }
  async function loadLemmaCands(q: string) {
    const id = ++lemmaRequest;
    const terms = q.trim().split(/\s+/).filter(Boolean);
    const keep = new Map(lemmaCands.flatMap(t => t.cands.map(c => [c.fold, c.on] as const)));
    const next = await Promise.all(terms.map(async term => ({ term, cands: await candidatesFor(term, keep).catch(() => []) })));
    if (id === lemmaRequest) lemmaCands = next;
  }
  function toggleCand(ti: number, fold: string) {
    const t = lemmaCands[ti];
    const c = t.cands.find(x => x.fold === fold);
    if (!c) return;
    // Keep at least one headword per word: none ticked would search nothing.
    if (c.on && t.cands.filter(x => x.on).length === 1) return;
    c.on = !c.on;
    lemmaCands = lemmaCands;
  }
  // The ticked folds per typed word, or nothing when every check is on (the
  // engine then resolves the word itself, exactly as before).
  // Candidates answer the words typed when they were loaded; picks from an
  // older query must never be sent with a newer one.
  function candsMatch(cands: TermCands[], q: string): boolean {
    return cands.map(t => t.term).join(' ') === q.trim().split(/\s+/).filter(Boolean).join(' ');
  }
  function lemmaPick(): string[][] | undefined {
    if (matchMode !== 'lemma' || !candsMatch(lemmaCands, grkQuery) || !lemmaCands.some(t => t.cands.some(c => !c.on))) return undefined;
    return lemmaCands.map(t => t.cands.filter(c => c.on).map(c => c.fold));
  }
  $: entryCand = lemmaCands.flatMap(t => t.cands).find(c => c.on && c.slug);

  async function nearSlot(): Promise<AdvancedSearch['near']> {
    if (nearKind === 'none') return undefined;
    const base = { relation: nearRel, window: nearWindow, unit: nearUnit, ordered: nearRel === 'near' && nearOrdered };
    if (nearKind === 'grammatical') {
      const query = shapeQueryOf(shapeClass, shape);
      return Object.keys(query).length ? { kind: 'grammatical', query, ...base } : undefined;
    }
    const words = nearText.trim().split(/\s+/).filter(Boolean);
    if (!words.length) return undefined;
    if (words.length > 1) return { kind: 'phrase' as SlotKind, terms: words, ...base };
    if (nearKind === 'form') return { kind: 'form', terms: words, ...base };
    const folds = await headFolds(words[0]);
    return { kind: 'lemma', terms: folds.length ? folds : [greekFold(words[0])], ...base };
  }
  let resultPlays = 0;                    // plays with a hit, for the count line
  // Which works to search. Default: all. Selected in the collapsible panel below.
  let selectedWorks = new Set<string>(WORKS.map(w => w.id));
  let worksOpen = false;  // is the works "Refine" panel expanded?
  let groups: ChapterGroup[] = [];        // chapter groups of the CURRENT page
  let totalInstances = 0;                 // across the whole result set (all pages)
  let loading = false;                    // running the index search
  let searched = false;
  let error = '';
  let failedWorks: string[] = [];

  // Pagination. search() returns the complete hit list (index-only); we render
  // it a page at a time, snapping page breaks to whole books so a chapter never
  // splits across pages — and so only the current page's books/chapters are
  // fetched. That keeps the request burst tiny regardless of how broad the
  // query is, instead of loading every result's book at once.
  const PAGE_TARGET = 40;                 // ~instances per page (whole books)
  let pages: SearchResult[][] = [];       // each page's slice of the result set
  let pageIdx = 0;
  let pageLoading = false;                // fetching the current page's books
  let pageError = '';                     // partial-load notice for this page
  let csvBusy = false;
  let csvNote = '';

  // Immutable snapshot of the SUBMITTED query. Pagination and CSV build snippets
  // and jump-links after the search completes, so they must use the query that
  // produced the results — not whatever is currently typed in the boxes (a user
  // can edit the inputs without re-submitting, then page/retry/export).
  interface SearchCtx { grkQuery: string; engQuery: string; engTerms: string[]; engForms: boolean; engMode: SearchMode; engBoxWords: number; engNearWords: number; near: boolean; grkAccentTerms: string[]; }
  let searchCtx: SearchCtx = { grkQuery: '', engQuery: '', engTerms: [], engForms: false, engMode: 'all', engBoxWords: 1, engNearWords: 1, near: false, grkAccentTerms: [] };
  let unsupportedWorks: string[] = [];

  // ── Accent-sensitive Greek matching ────────────────────────────────────────
  // The indexes are accent-folded (λόγος and λογός share a key), which is the
  // right default and stays the default. The toggle offers strict matching as
  // an instance-level post-filter: the index still finds the folded hits, then
  // each matched surface token must carry the query's exact diacritics. Strict
  // semantics, stated on the control: a query typed WITHOUT accents then only
  // matches genuinely unaccented tokens.
  let accentSensitive = false;
  // NFC + lowercase + final-sigma normalisation, diacritics KEPT.
  const accentNorm = (s: string) => s.normalize('NFC').toLowerCase().replace(/ς/g, 'σ');
  function accentTokenMatch(token: string, terms: string[]): boolean {
    const t = accentNorm(token);
    return terms.some(q =>
      q.endsWith('*') ? t.startsWith(q.slice(0, -1)) : t === q);
  }

  // Shared option list for the per-language mode selectors.
  const MODE_OPTS: { v: SearchMode; l: string }[] = [
    { v: 'all', l: 'All words' },
    { v: 'any', l: 'Any of them' },
    { v: 'phrase', l: 'Exact phrase' },
  ];

  function toggleWork(id: string) {
    if (selectedWorks.has(id)) { if (selectedWorks.size > 1) selectedWorks.delete(id); }
    else selectedWorks.add(id);
    selectedWorks = selectedWorks; // reactivity
  }

  // "Select all" reflects the true all-selected state: deselecting any single
  // work flips it off automatically (no fire-and-forget flag). Toggling it on
  // selects every work; toggling it off clears the selection.
  $: allSelected = selectedWorks.size === WORKS.length;
  function selectAll() { selectedWorks = new Set(WORKS.map(w => w.id)); }

  function selectOnly(ids: string[]) { selectedWorks = new Set(ids); }
  function addGroup(ids: string[]) {
    for (const id of ids) selectedWorks.add(id);
    selectedWorks = selectedWorks;
  }

  // The Greek text a play's hits come from, for its heading: the edition the
  // engine searched (it takes one only for a Greek-only query, in a play that
  // holds it), else the play's reference text ("Smyth 1926").
  let resultEds = new Map<string, string>();
  function greekTextOf(work: string): string {
    const w = getWork(work);
    if (!w) return '';
    const ed = w.greekEditions?.find((e) => e.id === resultEds.get(work));
    const short = ed?.short ?? w.greekSource.short;
    return short.replace(/\s*\((?:[^)]*?,\s*)?(\d{4})\)\s*$/, ' $1');
  }

  // Compact summary of the plays searched (UI pass 2: "All 44 plays").
  $: worksSummary = allSelected
    ? `All ${WORKS.length} plays`
    : selectedWorks.size === 0
      ? 'No play chosen'
      : `${selectedWorks.size} play${selectedWorks.size === 1 ? '' : 's'}`;

  // The In row's author checks (UI pass 2): none ticked is every play; a tick
  // narrows the search to that author's plays, more ticks add theirs.
  const AUTHOR_SCOPES = AUTHORS
    .map((a) => ({ id: a.id, name: a.name, ids: WORKS.filter((w) => w.author === a.id).map((w) => w.id) }))
    .filter((a) => a.ids.length > 0);
  $: authorTicked = (ids: string[]) => !allSelected && ids.every((id) => selectedWorks.has(id));
  function tickAuthor(ids: string[]) {
    if (allSelected) { selectOnly(ids); return; }
    if (ids.every((id) => selectedWorks.has(id))) {
      const rest = [...selectedWorks].filter((id) => !ids.includes(id));
      selectedWorks = rest.length ? new Set(rest) : new Set(WORKS.map((w) => w.id));
      return;
    }
    addGroup(ids);
  }

  // Results grouped Work → Book → chapter groups, in corpus then numeric order.
  $: groupsByWork = (() => {
    const byWork = new Map<string, Map<number, ChapterGroup[]>>();
    for (const g of groups) {
      const books = byWork.get(g.work) ?? byWork.set(g.work, new Map()).get(g.work)!;
      (books.get(g.book) ?? books.set(g.book, []).get(g.book)!).push(g);
    }
    return [...byWork.entries()]
      .sort((a, b) => (WORK_ORDER.get(a[0]) ?? 0) - (WORK_ORDER.get(b[0]) ?? 0))
      .map(([work, books]) => ({
        work,
        books: [...books.entries()].sort((a, b) => a[0] - b[0]),
      }));
  })();

  // Run `fn` over `items` with at most `limit` in flight (bounds the concurrent
  // fetch burst that can make Safari drop requests with "Load failed").
  async function pool<T>(items: T[], limit: number, fn: (item: T) => Promise<void>): Promise<void> {
    let next = 0;
    const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (next < items.length) await fn(items[next++]);
    });
    await Promise.all(workers);
  }

  // Map a hit's (column, line) to the chapter it falls in, for one book.
  // Chapters are ordered by document position; pick the last whose start is
  // at or before the hit.
  function chapterLookup(bookData: { segments: Segment[] }, chapters: ChapterRef[]) {
    const colIdx = new Map<string, number>();
    bookData.segments.forEach((s, i) => { if (!colIdx.has(s.column)) colIdx.set(s.column, i); });
    const chs = chapters
      .map((c, i) => ({ ...c, ci: colIdx.get(c.column) ?? 0, ln: parseInt(c.line), order: i }))
      .sort((a, b) => a.ci - b.ci || a.ln - b.ln);
    return (column: string, line: number): { chapter: string; bekker: string; order: number; workWide: boolean } => {
      // Defensive: never return undefined (callers deref .chapter). If the
      // chapter list is empty, group the hit under a placeholder rather than
      // throwing and collapsing the whole page.
      if (!chs.length) return { chapter: '', bekker: '', order: 0, workWide: true };
      const ci = colIdx.get(column) ?? 0;
      let found = chs[0];
      for (const c of chs) {
        if (c.ci < ci || (c.ci === ci && c.ln <= line)) found = c;
        else break;
      }
      return { ...found, workWide: false };
    };
  }

  // Stephanus works (all of Plato) ship an EMPTY chapters.json — they're cited by
  // page+section, so the outline lives in sections.json instead. Adapt a book's
  // section outline into the ChapterRef shape chapterLookup/buildGroups expect,
  // grouping hits by Stephanus page: one "chapter" per page, anchored at its
  // first section column, with the page's section columns as the displayed span
  // (e.g. page 2 → anchor "2a", range "2a–2e"). Without this the group builder
  // treats every book as unloadable and renders zero results (the reported bug:
  // "N pages of results, but none of them will load").
  // `flat` (the `section` scheme, Epictetus' Enchiridion): the column IS the
  // whole chapter number ("5", "10"), so the page label is the column itself —
  // the Stephanus last-char strip below would collapse chapters 10–19 all
  // into the label "1".
  function sectionsToChapters(secs: Record<string, SectionRef[]>, flat = false): Record<string, ChapterRef[]> {
    const out: Record<string, ChapterRef[]> = {};
    for (const [book, sections] of Object.entries(secs)) {
      const byPage = new Map<number, { anchor: string; cols: string[] }>();
      for (const s of sections) {
        let e = byPage.get(s.page);
        if (!e) { e = { anchor: s.column, cols: [] }; byPage.set(s.page, e); }
        e.cols.push(s.column);
      }
      out[book] = [...byPage.values()].map((e) => ({
        chapter: flat
          ? e.cols[0]                                   // flat: whole column ("10")
          // Page label: strip a genuine trailing letter suffix ("2a" → "2",
          // dk's "B84a" → "B84") — never a blind last-character slice, which
          // used to truncate dk's un-suffixed columns too ("B10" → "B1",
          // stripping a digit rather than a letter — the reported bug: a
          // group header reading "Chapter B1" beside the real hit "B10").
          : e.cols[0].replace(/[a-zA-Z]$/, '') || e.cols[0],
        column: e.anchor,
        line: '0',
        bekker: e.cols.length > 1 ? `${e.cols[0]}–${e.cols[e.cols.length - 1]}` : e.cols[0],
      }));
    }
    return out;
  }

  // Load a work's grouping outline: section-scheme works (stephanus,
  // book-section, flat section) from sections.json, everyone else from
  // chapters.json. Both resolve to the ChapterRef shape. See
  // CitationScheme.hasSections.
  function fetchOutline(work: string): Promise<Record<string, ChapterRef[]>> {
    const s = schemeFor(work);
    return s.hasSections
      ? fetchSections(work).then((secs) => sectionsToChapters(secs, s.id === 'section'))
      : fetchChapters(work);
  }

  // Heading word for a result group, keyed to the work's citation scheme —
  // "Section 2" for a book-section work (Plato's stephanus scheme gets
  // "Page"), "Chapter 5" for a Bekker/Busse work, no word at all for a dk
  // work (a fragment/testimonium column already reads as the citation — see
  // groupUnitNoun's doc comment in citation.ts).
  function groupUnitLabel(work: string): string {
    return groupUnitNoun(work);
  }

  // The result group's top-level heading word — "Book" for every scheme
  // except letter, where the grouping IS the letter (Seneca's Epistulae
  // Morales has no book level above the letter). Mirrors ReaderShell.astro's
  // own `bookNoun`/citation-copy.ts's `tocGroupNoun` (finding 2, Sol review:
  // this shared component can't import the app-only citation-copy.ts, so it
  // keeps its own copy of the same one-line rule).
  function bookGroupLabel(work: string): string {
    return schemeFor(work).id === 'letter' ? 'Letter' : 'Book';
  }

  // Source line containing the token at index `pos` within a segment.
  function lineOfPosition(seg: Segment, pos: number): GreekLine | null {
    let count = 0;
    for (const line of seg.greek) {
      if (pos < count + line.tokens.length) return line;
      count += line.tokens.length;
    }
    return seg.greek[seg.greek.length - 1] ?? null;
  }

  // Approximate Bekker line of an English match at char offset `pos` (for
  // chapter grouping and the jump target), by proportion through the segment.
  function englishLineAt(seg: Segment, pos: number, text = seg.english?.text ?? ''): GreekLine | null {
    const lines = seg.greek;
    if (!lines.length) return null;
    if (pos < 0 || !text.length) return lines[0] ?? null;
    const idx = Math.min(lines.length - 1, Math.floor(pos / Math.max(1, text.length) * lines.length));
    return lines[idx] ?? null;
  }

  // Instances a result contributes (mirrors how `buildGroups` adds them): one
  // per Greek match position, plus one per English match occurrence. Lets us
  // count the total and lay out pages from the index alone, before any book is
  // fetched (engPositions come from the full English text in meta).
  function instCount(r: SearchResult): number {
    // A near hit counts once, as it is shown: one row per hit.
    const grk = r.nearHits ? r.nearHits.length : r.grkPositions.length;
    return (r.grkMatch ? grk : 0) + (r.engMatch ? r.engPositions.length : 0);
  }

  // Build the chapter groups for a slice of results: load the books + chapters
  // they touch (bounded concurrency), then assemble and sort. A failed book or
  // chapter fetch is evicted (see data.ts) and its work:book key collected in
  // `failed` — NOT swallowed as a successful empty result — so the caller can
  // show an incomplete-results notice and offer a retry.
  async function buildGroups(results: SearchResult[], ctx: SearchCtx): Promise<{ groups: ChapterGroup[]; failed: string[] }> {
    // An edition hit's book (and its segment ids) come from that edition's data.
    const pairKey = (r: SearchResult) => `${r.work}:${r.meta.book}${r.ed ? `:${r.ed}` : ''}`;
    const wbPairs = [...new Set(results.map(pairKey))];
    const workSet = [...new Set(results.map(r => r.work))];
    const failed: string[] = [];

    const chaptersByWork = new Map<string, Record<string, ChapterRef[]>>();
    await pool(workSet, 8, async w => {
      try { chaptersByWork.set(w, await fetchOutline(w)); }
      catch (err) { console.warn(`search: outline failed for ${w} —`, err); failed.push(w); }
    });
    const segMap = new Map<string, Segment>();             // key: work:segId

    const lookups = new Map<string, ReturnType<typeof chapterLookup>>(); // key: work:book
    await pool(wbPairs, 8, async pair => {
      const [w, bStr, pairEd] = pair.split(':');
      const b = Number(bStr);
      // If the work's chapters never loaded we can't group its hits — mark the
      // pair failed and skip (don't feed an empty list into chapterLookup),
      // so the page shows the partial-results notice instead of crashing.
      const outline = chaptersByWork.get(w);
      let chapters = outline?.[String(b)];
      // Plays have no chapter level. Their valid empty chapters.json still
      // represents one book-wide result group.
      if (!chapters && b === 1 && outline && Object.keys(outline).length === 0
        && schemeFor(w).id === 'play-line') chapters = [];
      if (!chapters) { failed.push(pair); return; }
      try {
        const data = await fetchBook(w, b, pairEd);
        for (const s of data.segments) segMap.set(`${w}:${pairEd ?? ''}:${s.id}`, s);
        lookups.set(pair, chapterLookup(data, chapters));
      } catch (err) { console.warn(`search: book failed for ${pair} —`, err); failed.push(pair); }
    });

    const gmap = new Map<string, ChapterGroup>();
    const add = (work: string, book: number, ch: { chapter: string; bekker: string; order: number; workWide: boolean }, inst: Omit<Instance, 'documentOrder'>) => {
      const key = ch.workWide ? `${work}:whole-work` : `${work}:${book}:${ch.chapter}`;
      let g = gmap.get(key);
      if (!g) { g = { key, work, book, chapter: ch.chapter, bekker: ch.bekker, order: ch.order, workWide: ch.workWide, instances: [] }; gmap.set(key, g); }
      g.instances.push({ ...inst, documentOrder: documentOrder++ });
    };
    let documentOrder = 0;

    // Carry the SUBMITTED queries so the reader can highlight them; loc scrolls
    // to the line. Use the snapshot (ctx), not live input state.
    const qs = new URLSearchParams();
    if (ctx.grkQuery) qs.set('hlg', ctx.grkQuery);
    if (ctx.engQuery) qs.set('hle', ctx.engQuery);
    const base = qs.toString();
    const root = import.meta.env.BASE_URL.replace(/\/$/, '');
    // The `?loc=` value composes through the work's citation scheme:
    // "1094a:15" (bekker — byte-identical), "17a" (stephanus — no :line, since
    // Plato has no user-facing lines). See shared/lib/citation.ts.
    const jumpFor = (work: string, book: number, column: string, line: number, slotId?: string, ed?: string) => {
      if (ed) {
        // An edition hit's column is in that edition's numbering: readerHref
        // keeps `ed=` beside `loc=` so the reader lands on the line searched.
        // `view=greek` shows the Greek column (a saved English-only view would
        // hide the line) and is the view that carries the edition picker.
        const url = new URL(readerHref(work, { book, loc: formatLocValue(work, column, line), ed, trans: slotId, view: 'greek' }), 'https://reader.invalid');
        for (const [key, value] of qs) url.searchParams.append(key, value);
        return `${root}${url.pathname}${url.search}`;
      }
      return `${root}${workPath(work, book)}?${base}${base ? '&' : ''}loc=${formatLocValue(work, column, line)}` +
        (slotId ? `&trans=${encodeURIComponent(slotId)}` : '');
    };

    for (const r of results) {
      const seg = segMap.get(`${r.work}:${r.ed ?? ''}:${r.meta.id}`);
      const lookup = lookups.get(pairKey(r));
      if (!seg || !lookup) continue;
      if (r.grkMatch) {
        // Flattened surface tokens, for the accent post-filter (positions are
        // token indices — the same flattening greekKwic uses).
        const toks: string[] = [];
        if (ctx.grkAccentTerms.length) {
          for (const line of seg.greek) for (const tok of line.tokens) toks.push(tok.t);
        }
        // A near search: one hit per run of the Greek box's words, kept only if
        // every word of the run passes the accent test, the other terms marked
        // with it (and their line shown when it is another, even in the next
        // or previous passage).
        for (const hit of r.nearHits ?? []) {
          const run = hit.span;
          if (ctx.grkAccentTerms.length && !Array.from({ length: run }, (_, j) => j)
            .every(j => accentTokenMatch(toks[hit.pos + j] ?? '', run > 1 ? [ctx.grkAccentTerms[j] ?? ''] : ctx.grkAccentTerms))) continue;
          const sourceLine = lineOfPosition(seg, hit.pos);
          if (!sourceLine) continue;
          // The partners that answered this hit, in this passage or another.
          const here = hit.partners.filter(p => p.segId === r.meta.id).map(p => p.pos);
          const awayBySeg = new Map<string, { seg: Segment; positions: number[]; after: boolean }>();
          for (const p of hit.partners) {
            if (p.segId === r.meta.id) continue;
            const sg = segMap.get(`${r.work}:${r.ed ?? ''}:${p.segId}`);
            if (!sg) continue;
            const entry = awayBySeg.get(p.segId) ?? { seg: sg, positions: [], after: !p.before };
            entry.positions.push(p.pos);
            awayBySeg.set(p.segId, entry);
          }
          const away = [...awayBySeg.values()];
          const column = sourceLine.ref ?? seg.column;
          const ch = lookup(seg.column, sourceLine.n);
          add(r.work, r.meta.book, ch, { lang: 'grk', column, line: sourceLine.n, ref: formatCite(r.work, column, sourceLine.n), html: nearKwic(seg, hit.pos, run, here, away), jumpUrl: jumpFor(r.work, r.meta.book, column, sourceLine.n, undefined, r.ed) });
        }
        for (const pos of r.nearHits ? [] : r.grkPositions) {
          if (ctx.grkAccentTerms.length
            && !accentTokenMatch(toks[pos] ?? '', ctx.grkAccentTerms)) continue;
          const sourceLine = lineOfPosition(seg, pos);
          if (!sourceLine) continue;
          const column = schemeFor(r.work).id === 'play-line'
            ? sourceLine.ref ?? seg.column
            : seg.column;
          const ch = lookup(seg.column, sourceLine.n);
          add(r.work, r.meta.book, ch, { lang: 'grk', column, line: sourceLine.n, ref: formatCite(r.work, column, sourceLine.n), html: schemeFor(r.work).id === 'play-line' ? lineKwic(seg, pos) : greekKwic(seg, [pos]), jumpUrl: jumpFor(r.work, r.meta.book, column, sourceLine.n, undefined, r.ed) });
        }
      }
      if (r.engMatch) {
        // One instance per occurrence in this translation's full text (an
        // English near hit: one per occurrence of the English box's words that
        // has the near word close by; both are marked).
        const engText = r.englishText ?? seg.english?.text ?? '';
        const spans = matchedSpans(engText, r, ctx);
        for (const off of r.engPositions) {
          const text = engText;
          const sourceLine = englishLineAt(seg, off, text);
          if (!sourceLine) continue;
          const playLine = schemeFor(r.work).id === 'play-line';
          const column = playLine ? sourceLine.ref ?? seg.column : seg.column;
          const ch = lookup(seg.column, sourceLine.n);
          add(r.work, r.meta.book, ch, {
            lang: 'eng', column, line: sourceLine.n,
            ref: playLine ? formatCite(r.work, column, sourceLine.n) : seg.column,
            html: englishKwicAt(text, off, spans, hitRange(text, off, ctx, r.engNearPositions)),
            jumpUrl: jumpFor(r.work, r.meta.book, column, sourceLine.n, r.slotId),
            credit: [getWork(r.work)?.translations.find(t => t.id === r.slotId)?.short,
              (!r.slotId || r.slotId === getWork(r.work)?.translations.find(t => t.slot === 'english')?.id)
                && seg.english?.credit ? formatSearchCredit(seg.english.credit) : undefined]
              .filter(Boolean).join(' · ') || undefined,
          });
        }
      }
    }

    for (const g of gmap.values()) {
      g.instances.sort(schemeFor(g.work).id === 'play-line'
        ? (a, b) => a.documentOrder - b.documentOrder
        : bekkerCmp);
    }
    const out = [...gmap.values()].sort((a, b) =>
      ((WORK_ORDER.get(a.work) ?? 0) - (WORK_ORDER.get(b.work) ?? 0)) || a.book - b.book || a.order - b.order);
    return { groups: out, failed: [...new Set(failed)] };
  }

  // Split the full result set into pages of whole books (~PAGE_TARGET instances
  // each). Ordered by home-page work order then book; a stable sort keeps each
  // book's hits in document order. Whole books per page ⇒ no chapter splits and
  // only a handful of books fetched per page.
  function paginate(results: SearchResult[]): SearchResult[][] {
    const sorted = [...results].sort((a, b) =>
      ((WORK_ORDER.get(a.work) ?? 0) - (WORK_ORDER.get(b.work) ?? 0)) || (a.meta.book - b.meta.book));
    const blocks: { results: SearchResult[]; count: number }[] = [];
    let key = '';
    for (const r of sorted) {
      const k = `${r.work}:${r.meta.book}`;
      if (k !== key) { blocks.push({ results: [], count: 0 }); key = k; }
      const blk = blocks[blocks.length - 1];
      blk.results.push(r); blk.count += instCount(r);
    }
    const out: SearchResult[][] = [];
    let page: SearchResult[] = []; let count = 0;
    for (const blk of blocks) {
      if (page.length && count + blk.count > PAGE_TARGET) { out.push(page); page = []; count = 0; }
      page.push(...blk.results); count += blk.count;
    }
    if (page.length) out.push(page);
    return out;
  }

  // Each search and page render takes a number; a slower, older one that
  // finishes late drops its results (Codex review, 2026-10-24).
  let runId = 0;
  let searchRun = 0;
  async function renderPage(i: number) {
    const id = ++runId;
    pageIdx = i;
    pageLoading = true;
    pageError = '';
    try {
      const { groups: g, failed } = await buildGroups(pages[i] ?? [], searchCtx);
      if (id !== runId) return;
      groups = g;
      if (failed.length) {
        pageError = `${failed.length} passage source${failed.length === 1 ? '' : 's'} on this page didn’t load — some hits may be missing.`;
      }
    } catch (err) {
      if (id !== runId) return;
      pageError = String(err);
      groups = [];
    } finally {
      if (id === runId) pageLoading = false;
    }
  }

  function goPage(i: number) {
    if (i < 0 || i >= pages.length || i === pageIdx || pageLoading) return;
    renderPage(i);
    if (typeof document !== 'undefined') {
      document.querySelector('.result-bar')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // The command palette (and any external link) can hand off a query via
  // ?g= (Greek) / ?e= (English): prefill and run it on mount. ?q= is the
  // generic term our SearchAction structured data advertises to search
  // engines (sitelinks searchbox) — route it to English, unless an explicit
  // ?e= is also present.
  // The address holds the whole search (search-url.ts), so a search can be
  // shared, bookmarked and stepped through with Back. ?g=, ?e= and ?q= (the
  // palette's and search engines' handoffs) decode into the same state; a ?q=
  // in Greek script goes to the Greek box.
  const ALL_WORK_IDS = WORKS.map(w => w.id);
  function applyUrl(u: UrlSearch) {
    grkQuery = u.grk; engQuery = u.eng; grkMode = u.grkMode; engMode = u.engMode;
    matchMode = u.matchMode; accentSensitive = u.accent; langOp = u.langOp; engForms = u.engForms;
    selectedWorks = new Set(u.works);
    greekEd = editionChoices.some(e => e.id === u.ed) ? u.ed : 'tlg';
    const n = u.near;
    nearKind = !n ? 'none' : n.kind === 'grammatical' ? 'grammatical' : n.kind === 'lemma' ? 'lemma' : 'form';
    nearText = n && n.kind !== 'grammatical' && n.kind !== 'lemma' ? (n.terms ?? []).join(' ') : n?.kind === 'lemma' ? (u.nearText ?? betaToGreek(n.terms?.[0] ?? '')) : '';
    nearRel = n?.relation ?? 'near'; nearWindow = n?.window ?? COMBO_WINDOW_DEFAULT;
    nearUnit = n?.unit ?? 'words'; nearOrdered = n?.ordered ?? false;
    if (n?.query) {
      shape = { ...n.query };
      shapeClass = (Object.keys(n.query) as string[]).some(k => ['tense', 'mood', 'voice', 'person'].includes(k)) ? 'verb'
        : 'marker' in n.query ? 'word' : 'noun';
    }
    engNearText = u.engNear?.term ?? ''; engNearRel = u.engNear?.relation ?? 'near';
    engNearWindow = u.engNear?.window ?? COMBO_WINDOW_DEFAULT;
    pendingPick = u.lemmaPick ? { query: u.grk, picks: u.lemmaPick } : undefined;
  }
  // Picks from a shared address, applied once the LSJ row has its candidates.
  // They belong to the words they were saved with: typing other words first
  // discards them.
  let pendingPick: { query: string; picks: string[][] } | undefined;
  const words = (q: string) => q.trim().split(/\s+/).filter(Boolean).join(' ');
  $: if (pendingPick && words(pendingPick.query) !== words(grkQuery)) pendingPick = undefined;
  $: if (pendingPick && lemmaCands.length && candsMatch(lemmaCands, pendingPick.query)) {
    const picks = pendingPick.picks;
    lemmaCands = lemmaCands.map((t, i) => ({ ...t, cands: t.cands.map(c => ({ ...c, on: picks[i]?.length ? picks[i].includes(c.fold) : true })) }));
    pendingPick = undefined;
  }
  onMount(() => {
    const u = decodeSearchUrl(window.location.search, ALL_WORK_IDS);
    applyUrl(u);
    if (hasSearch(u)) doSearch(undefined, u.lemmaPick, 'replace');
    const onPop = () => {
      const v = decodeSearchUrl(window.location.search, ALL_WORK_IDS);
      applyUrl(v);
      if (hasSearch(v)) doSearch(undefined, v.lemmaPick, 'none');
      else clearSearch();
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  });

  // history: 'push' for a search the reader ran, 'replace' to normalise the
  // address a page opened with, 'none' for a search Back or Forward restored.
  async function doSearch(e?: Event, picks?: string[][], history_: 'push' | 'replace' | 'none' = 'push') {
    e?.preventDefault();
    if (!grkQuery.trim() && !engQuery.trim()) return;
    const id = ++searchRun;
    runId++;   // a page still loading for an older search must not land
    loading = true;
    error = '';
    pageError = '';
    csvNote = '';
    failedWorks = [];
    unsupportedWorks = [];
    searched = false;
    // Every input is read now, before the first await: a Back or a new search
    // during the lookups below must not mix its state into this one.
    const q = {
      grk: grkQuery, eng: engQuery, grkMode, engMode, matchMode, accent: accentSensitive, langOp, engForms, ed: greekEd,
      works: WORKS.map(w => w.id).filter(w => selectedWorks.has(w)),
      nearText: nearText.trim(),
      engNear: engQuery.trim() && engNearText.trim()
        ? { term: engNearText.trim(), relation: engNearRel, window: engNearWindow } : undefined,
      pick: picks ?? lemmaPick(),
    };
    const nearP = q.grk.trim() ? nearSlot() : Promise.resolve(undefined);
    try {
      const near = await nearP;
      if (id !== searchRun) return;
      const advanced: AdvancedSearch = { engForms: q.engForms, ...(q.pick ? { lemmaPick: q.pick } : {}), ...(near ? { near } : {}), ...(q.engNear ? { engNear: q.engNear } : {}) };
      // The address holds the search, so it can be shared and reopened.
      const url: UrlSearch = {
        grk: q.grk, eng: q.eng, grkMode: q.grkMode, engMode: q.engMode, matchMode: q.matchMode, accent: q.accent,
        langOp: q.langOp, engForms: q.engForms, works: q.works, ed: q.ed, ...advanced,
        ...(near?.kind === 'lemma' ? { nearText: q.nearText } : {}),
      };
      const qs = encodeSearchUrl(url, ALL_WORK_IDS);
      if (history_ !== 'none' && qs !== window.location.search.replace(/^\?/, '')) {
        const next = `${window.location.pathname}${qs ? `?${qs}` : ''}`;
        if (history_ === 'push') history.pushState(null, '', next);
        else history.replaceState(null, '', next);
      }
      const grkWords = q.grk.trim().split(/\s+/).filter(Boolean);
      // Snapshot the submitted query for all deferred (per-page / CSV) rendering.
      searchCtx = {
        grkQuery: q.grk.trim(),
        engQuery: q.eng.trim(),
        engTerms: [...q.eng.trim().split(/\s+/), ...(q.engNear ? q.engNear.term.split(/\s+/) : [])].filter(Boolean),
        engForms: q.engForms,
        engMode: q.engMode,
        engBoxWords: Math.max(1, q.eng.trim().split(/\s+/).filter(Boolean).length),
        engNearWords: q.engNear ? Math.max(1, q.engNear.term.split(/\s+/).filter(Boolean).length) : 1,
        near: !!near,
        grkAccentTerms: q.accent
          // Beta Code terms compare as Greek; a trailing * stays a wildcard.
          ? grkWords.map(t => { const w = t.length > 1 && t.endsWith('*'); return accentNorm(betaToGreek(w ? t.slice(0, -1) : t)) + (w ? '*' : ''); })
          : [],
      };
      const { results, failed, unsupported } = await search(q.grk, q.eng, q.grkMode, q.engMode, q.langOp, q.works, q.matchMode, q.ed, advanced);
      if (id !== searchRun) return;
      resultEds = new Map(results.filter((r) => r.ed).map((r) => [r.work, r.ed!]));
      resultPlays = new Set(results.map((r) => r.work)).size;
      failedWorks = failed;
      unsupportedWorks = unsupported ?? [];
      totalInstances = results.reduce((n, r) => n + instCount(r), 0);
      pages = paginate(results);
      searched = true;
      if (pages.length) await renderPage(0);
      else { groups = []; pageIdx = 0; }
    } catch (err) {
      if (id === searchRun) error = err instanceof Error ? err.message : String(err);
    } finally {
      if (id === searchRun) loading = false;
    }
  }

  // Back to an address with no search: clear the results, and let nothing
  // still running land on the page.
  function clearSearch() {
    searchRun++; runId++;
    loading = false; searched = false; error = ''; pageError = ''; csvNote = '';
    pages = []; groups = []; pageIdx = 0; totalInstances = 0; failedWorks = []; unsupportedWorks = [];
  }

  // A play's Greek hit shows its whole verse line, the match marked (UI pass
  // 2, spec §8.1: "the lines under it, each with its number ... and the
  // matched word marked").
  // A near hit: the line of the run starting at `pos`, its words and the other
  // terms marked, then the line of the nearest other term when it stands on
  // another line, or (`away`) in the passage before or after.
  function nearKwic(seg: Segment, pos: number, run: number, others: number[], away: { seg: Segment; positions: number[]; after: boolean }[] = []): string {
    const linesOf = (sg: Segment) => {
      const out: { line: GreekLine; start: number }[] = [];
      let start = 0;
      for (const line of sg.greek) { out.push({ line, start }); start += line.tokens.length; }
      return out;
    };
    const render = (l: { line: GreekLine; start: number }, marked: Set<number>) => l.line.tokens
      .map((tok, k) => (marked.has(l.start + k) ? `<mark>${esc(tok.t)}</mark>` : esc(tok.t))).join(' ');
    const lines = linesOf(seg);
    const lineOf = (p: number) => lines.findIndex(l => p >= l.start && p < l.start + l.line.tokens.length);
    const marked = new Set([...Array.from({ length: run }, (_, j) => pos + j), ...others]);
    const home = lineOf(pos);
    if (home < 0) return greekKwic(seg, [pos]);
    const inLine = (p: number) => p >= lines[home].start && p < lines[home].start + lines[home].line.tokens.length;
    const parts = [home];
    if (!others.some(inLine)) {
      const nearest = others.slice().sort((a, b) => Math.abs(a - pos) - Math.abs(b - pos))[0];
      const at = nearest === undefined ? -1 : lineOf(nearest);
      if (at >= 0) parts.push(at);
    }
    const html = parts.sort((a, b) => a - b).map(i => render(lines[i], marked));
    // Partners in another passage: every line they stand on, all marked.
    for (const a of away) {
      const marks = new Set(a.positions);
      const awayHtml = linesOf(a.seg)
        .filter(x => a.positions.some(p => p >= x.start && p < x.start + x.line.tokens.length))
        .map(x => render(x, marks));
      if (a.after) html.push(...awayHtml); else html.unshift(...awayHtml);
    }
    return html.join(' <span class="sep">/</span> ');
  }

  function lineKwic(seg: Segment, pos: number): string {
    let start = 0;
    for (const line of seg.greek) {
      if (pos < start + line.tokens.length) {
        return line.tokens.map((tok, i) => (i === pos - start ? `<mark>${esc(tok.t)}</mark>` : esc(tok.t))).join(' ');
      }
      start += line.tokens.length;
    }
    return greekKwic(seg, [pos]);
  }

  // Greek keyword-in-context: a window of surface tokens around the match,
  // with the matched token(s) highlighted. Positions come from the index.
  const GRK_WINDOW = 8;
  function greekKwic(seg: Segment, positions: number[]): string {
    const toks: string[] = [];
    for (const line of seg.greek) for (const tok of line.tokens) toks.push(tok.t);
    if (!positions.length) {
      const head = toks.slice(0, 2 * GRK_WINDOW + 1);
      return esc(head.join(' ')) + (toks.length > head.length ? ' …' : '');
    }
    const posSet = new Set(positions);
    const center = positions[0];
    const start = Math.max(0, center - GRK_WINDOW);
    const end = Math.min(toks.length, center + GRK_WINDOW + 1);
    const win = [];
    for (let i = start; i < end; i++) {
      const w = esc(toks[i]);
      win.push(posSet.has(i) ? `<mark>${w}</mark>` : w);
    }
    let html = win.join(' ');
    if (start > 0) html = '… ' + html;
    if (end < toks.length) html = html + ' …';
    return html;
  }

  // English keyword-in-context: a character window around the match at char
  // offset `pos` in the full chunk text, with all query terms highlighted.
  const ENG_WINDOW = 140;
  // The words a hit really matched, as [start, end) spans of the text: each
  // run of the English box's words (one word, or the whole phrase), and each
  // near word's run. Matching words outside a hit are left unmarked.
  function matchedSpans(text: string, r: SearchResult, ctx: SearchCtx): [number, number][] {
    const words = englishWords(text);
    const at = new Map(words.map((w, i) => [w.start, i]));
    const out: [number, number][] = [];
    const add = (starts: number[], run: number) => {
      for (const s of starts) {
        const i = at.get(s);
        if (i === undefined) continue;
        for (const w of words.slice(i, i + run)) out.push([w.start, w.end]);
      }
    };
    add(r.engPositions, ctx.engMode === 'phrase' ? ctx.engBoxWords : 1);
    add(r.engNearPositions ?? [], ctx.engNearWords);
    return out;
  }

  // The stretch a row must show whole: its own run (a phrase may be long) and,
  // for a near hit, the nearest near word's run, however far off it stands.
  function hitRange(text: string, off: number, ctx: SearchCtx, partners?: number[]): [number, number] {
    const words = englishWords(text);
    const at = new Map(words.map((w, i) => [w.start, i]));
    const runEnd = (s: number, run: number) => words[(at.get(s) ?? -1) + run - 1]?.end ?? s;
    let from = off;
    let to = runEnd(off, ctx.engMode === 'phrase' ? ctx.engBoxWords : 1);
    if (partners?.length) {
      const p = partners.reduce((best, x) => (Math.abs(x - off) < Math.abs(best - off) ? x : best));
      from = Math.min(from, p);
      to = Math.max(to, runEnd(p, ctx.engNearWords));
    }
    return [from, to];
  }

  function englishKwicAt(text: string, pos: number, spans: [number, number][], range: [number, number] = [pos, pos]): string {
    if (!text) return '';
    const earliest = range[0] >= 0 && range[0] < text.length ? range[0] : 0;
    const latest = Math.min(text.length, Math.max(earliest, range[1]));
    let start = Math.max(0, earliest - ENG_WINDOW);
    let end = Math.min(text.length, latest + ENG_WINDOW);
    if (start > 0) {
      const sp = text.indexOf(' ', start);
      if (sp >= 0 && sp < earliest) start = sp + 1;
    }
    if (end < text.length) {
      const sp = text.lastIndexOf(' ', end);
      if (sp > latest) end = sp;
    }
    let html = markSpans(text, start, end, spans);
    if (start > 0) html = '… ' + html;
    if (end < text.length) html = html + ' …';
    return html;
  }

  // The text from start to end, escaped, with the given spans marked.
  function markSpans(text: string, start: number, end: number, spans: [number, number][]): string {
    let out = '';
    let at = start;
    for (const [a, b] of [...spans].sort((x, y) => x[0] - y[0])) {
      if (b <= at || a >= end) continue;
      const from = Math.max(a, at);
      out += esc(text.slice(at, from)) + '<mark>' + esc(text.slice(from, Math.min(b, end))) + '</mark>';
      at = Math.min(b, end);
    }
    return out + esc(text.slice(at, end));
  }

  // Compact attribution for a search hit (finding 1, Sol review): a search
  // result is not the place for the reading page's full citation line, but a
  // licensed passage's translator and licence must still name themselves
  // wherever the text appears — the licence's attribution term is not
  // satisfied by a credit shown only on the reading page. Plain text (used
  // on-screen beside the snippet and in the CSV export alike).
  function formatSearchCredit(credit: TranslationCredit): string {
    return `Tr. ${credit.translator} (${credit.year})${credit.licence ? ` — ${credit.licence.name}` : ''}.`;
  }

  function esc(s: string): string {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Bekker order within a chapter: page number, then column half (a < b), then
  // line. Sorting by line alone mis-orders hits that span two columns of one
  // chapter (e.g. 1097b3 before 1097a15). Works for grk and eng instances alike.
  function bekkerCmp(a: Instance, b: Instance): number {
    const pa = parseInt(a.column, 10) || 0;
    const pb = parseInt(b.column, 10) || 0;
    if (pa !== pb) return pa - pb;
    const ha = a.column.slice(-1), hb = b.column.slice(-1);
    if (ha !== hb) return ha < hb ? -1 : 1;
    return a.line - b.line;
  }

  // --- CSV export (the FULL result set, every page) ------------------------
  function stripHtml(html: string): string {
    return html
      .replace(/<[^>]*>/g, '')
      .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
      .trim();
  }
  function csvCell(v: string): string {
    return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  }
  async function exportCsv() {
    if (csvBusy) return;
    csvBusy = true;
    csvNote = '';
    try {
      // Export every result, not just the current page — so build groups over
      // the whole set (loads any not-yet-fetched books on demand, bounded +
      // retried). If some book truly can't load, the CSV omits those rows and
      // we say so rather than silently shipping a short file.
      const { groups: allGroups, failed } = await buildGroups(pages.flat(), searchCtx);
      const origin = typeof location !== 'undefined' ? location.origin : '';
      // URL comes BEFORE the free-text Snippet (and Snippet is the LAST column)
      // on purpose. The snippet holds prose full of commas; we RFC-quote it, but
      // iPad Excel / Numbers don't reliably honour the quoting, so those commas
      // split the row — and since each snippet has a different comma count, the
      // URL landed in a different column on every row and stopped being clickable
      // (reported by a user). With the URL ahead of it, the link always sits in
      // one fixed, comma-free column; only the trailing snippet can spill, which
      // is harmless. A compliant parser reads all seven columns either way.
      // The 4th column's header word: exported results can span several
      // works with different citation schemes, so this used to hardcode
      // "Chapter" — wrong for a book-section/dk/letter work's rows
      // (REVIEW-CHECKLIST item 34). Use the shared unit noun when every
      // exported work agrees on one; a mixed-scheme export (or an all-dk
      // export, which has no noun) falls back to the neutral "Reference".
      const chapterHeaders = new Set(allGroups.map((g) => groupUnitLabel(g.work)).filter(Boolean));
      const chapterHeader = chapterHeaders.size === 1 ? [...chapterHeaders][0] : 'Reference';
      // Same rationale as chapterHeader above: an export spanning a letter
      // work (Seneca) alongside book works would mislabel the letter column
      // "Book" (finding 2, Sol review) — use "Book" only when every exported
      // work agrees; a mixed export falls back to the neutral "Book/Letter".
      const bookHeaders = new Set(allGroups.map((g) => bookGroupLabel(g.work)));
      const bookHeader = bookHeaders.size === 1 ? [...bookHeaders][0] : 'Book/Letter';
      // 'Attribution' sits before the free-text Snippet, same rationale as
      // URL's fixed position above — a column that's usually empty (only a
      // credited passage fills it) stays put rather than shifting the
      // trailing Snippet's column index around. Finding 1 (Sol review): a
      // credited hit's translator/licence used to have no way to travel with
      // the exported row at all.
      const rows: string[][] = [['Work', bookHeader, chapterHeader, 'Citation', 'Language', 'URL', 'Attribution', 'Snippet']];
      for (const g of allGroups) {
        const w = getWork(g.work);
        const workTitle = w?.title ?? g.work;
        const book = w?.bookLabels[g.book - 1] ?? String(g.book);
        for (const inst of g.instances) {
          rows.push([
            workTitle, String(book), g.chapter, inst.ref,
            inst.lang === 'grk' ? 'Greek' : 'English',
            origin + inst.jumpUrl,
            inst.credit ?? '',
            stripHtml(inst.html),
          ]);
        }
      }
      const csv = rows.map(r => r.map(csvCell).join(',')).join('\r\n');
      // Prepend a UTF-8 BOM so Excel renders Greek correctly.
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `drama-search-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      if (failed.length) {
        csvNote = `Exported, but ${failed.length} passage source${failed.length === 1 ? '' : 's'} couldn’t load — the CSV may be missing some rows. Try again to retry those.`;
      }
    } catch (err) {
      csvNote = `Export failed: ${String(err)}`;
    } finally {
      csvBusy = false;
    }
  }

  function onEnter(e: KeyboardEvent) {
    if (e.key === 'Enter') doSearch();
  }

  // "β Beta Code": with the toggle on, the Greek box turns Beta Code into
  // Greek as you type (lo/gos → λόγος), caret kept, as Grammata's /words box
  // does (grammar-site src/pages/words.astro). Off on every visit: a toggle
  // that outlived the visit would quietly turn the next query Greek.
  let betaMode = false;
  let grkInput: HTMLInputElement;

  function toggleBeta() {
    betaMode = !betaMode;
    if (betaMode && grkQuery) grkQuery = liveGreek(grkQuery);
    grkInput?.focus();
  }

  // Grok review: an IME or a phone keyboard that composes whole words
  // (Gboard) is converted when the word is committed, never mid-composition;
  // an undo or redo is left as it restores.
  function onGreekInput(e: Event) {
    const ie = e as InputEvent;
    if (ie.isComposing || ie.inputType === 'historyUndo' || ie.inputType === 'historyRedo') return;
    convertGreekBox(e.currentTarget as HTMLInputElement);
  }

  function convertGreekBox(el: HTMLInputElement) {
    if (!betaMode) return;
    const raw = el.value;
    const converted = liveGreek(raw);
    if (converted === raw) return;
    let caret = liveGreek(raw.slice(0, el.selectionStart ?? raw.length)).length;
    // A mark typed after the caret joins the letter before it; where the two
    // do not precompose, step past the mark rather than split them.
    while (caret < converted.length && /\p{M}/u.test(converted[caret])) caret++;
    el.value = converted;
    grkQuery = converted;
    el.setSelectionRange(caret, caret);
  }

  // "Type Greek": the Beta Code chart in a dialog over the search, as the
  // Aristotle reader's search opens it from beside its Greek box (John,
  // 2026-10-23). The same chart is the How to search page's second half.
  let showHelp = false;
  let helpModal: HTMLDivElement;
  let helpTrigger: HTMLElement | null = null;

  async function openHelp(e?: MouseEvent) {
    helpTrigger = e?.currentTarget instanceof HTMLElement
      ? e.currentTarget
      : document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    showHelp = true;
    await tick();
    helpModal?.focus();
  }

  function closeHelp() {
    showHelp = false;
    helpTrigger?.focus();
    helpTrigger = null;
  }

  function helpFocusableEls(): HTMLElement[] {
    return helpModal
      ? Array.from(helpModal.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        )).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1)
      : [];
  }

  function onHelpKey(e: KeyboardEvent) {
    if (!showHelp) return;
    if (e.key === 'Escape') {
      // Not also the search box's own Escape, which clears the query.
      e.preventDefault();
      closeHelp();
      return;
    }
    if (e.key !== 'Tab') return;
    const els = helpFocusableEls();
    if (els.length === 0) {
      e.preventDefault();
      helpModal?.focus();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    // The dialog opens with focus on itself, which is in neither end of the
    // list: from there (or from anywhere outside it) Tab goes to the first
    // control and Shift+Tab to the last, never out behind the backdrop.
    const active = document.activeElement;
    const inside = active instanceof HTMLElement && active !== helpModal && helpModal.contains(active);
    if (e.shiftKey && (!inside || active === first)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (!inside || active === last)) {
      e.preventDefault();
      first.focus();
    }
  }
</script>

<svelte:window on:keydown={onHelpKey} />

<!-- UI pass 2, direction B (docs/redesign/HANDOFF-ui-pass2-build.md §8.1): the
     two boxes at the left, Greek over English, searched together; every control
     to their right, one row each (John, 2026-10-20: "Put all the controls to the
     right of search boxes"); the plays head their hits, each hit a whole line.
     Search step 2 (2026-10-24) adds the Aristotle reader's advanced search in
     these rows: the LSJ checks, Near and Shape for the Greek, English forms
     and English near, the phrase index, and the search kept in the address. -->
<main class="search-page">
  <form class="search-form" on:submit={doSearch} novalidate>
    <div class="boxes">
      <p class="lab-row"><label class="lab" for="grk-input">Greek</label><span class="lab-acts"><button type="button" class="tog" aria-pressed={betaMode} on:click={toggleBeta} title="Type Beta Code, see Greek: lo/gos becomes λόγος as you type"><span lang="grc">β</span> Beta Code</button><button type="button" class="ln" on:click={openHelp} aria-haspopup="dialog">Type Greek</button></span></p>
      <input
        id="grk-input"
        class="fld greek-input"
        lang="grc"
        type="search"
        placeholder="ξίφος, or xifos, fron*"
        bind:value={grkQuery}
        bind:this={grkInput}
        on:input={onGreekInput}
        on:compositionend={(e) => convertGreekBox(e.currentTarget)}
        on:keydown={onEnter}
        autocomplete="off"
        autocorrect="off"
        autocapitalize="none"
        spellcheck="false"
      />
      <label class="lab" for="eng-input">English</label>
      <input
        id="eng-input"
        class="fld"
        type="search"
        placeholder="a word or phrase"
        bind:value={engQuery}
        on:keydown={onEnter}
        autocomplete="off"
      />
      <p class="act">
        <button type="submit" class="go search-btn" disabled={loading}>{loading ? 'Searching…' : 'Search'}</button>
        <a class="ln" href={`${import.meta.env.BASE_URL.replace(/\/$/, '')}/search/phrases`}>Phrase index</a>
        <a class="ln" href={`${import.meta.env.BASE_URL.replace(/\/$/, '')}/search/how`}>How to search</a>
      </p>
    </div>

    <div class="ctrls">
      <p class="row">
        <span class="mn">Greek</span>
        <!-- Each picker reads select.value on change (not bind:value, whose
             :checked lookup the test DOM does not support). -->
        <span class="v"><select aria-label="Greek words" value={grkMode} on:change={(e) => (grkMode = e.currentTarget.value as SearchMode)}>{#each MODE_OPTS as opt}<option value={opt.v}>{opt.l}</option>{/each}</select><i aria-hidden="true">▾</i></span>
        <span class="v" title="Any form of the word matches every inflected form of its headword; Only as typed matches the word only as written"><select aria-label="Greek forms" value={matchMode} on:change={(e) => (matchMode = e.currentTarget.value as MatchMode)}><option value="lemma">Any form of the word</option><option value="form">Only as typed</option></select><i aria-hidden="true">▾</i></span>
        <span class="v" title="Accents matter: λόγος and λογός become different queries, and a query typed without accents then matches only unaccented words"><select aria-label="Greek accents" value={String(accentSensitive)} on:change={(e) => (accentSensitive = e.currentTarget.value === 'true')}><option value="false">Accents ignored</option><option value="true">Accents matter</option></select><i aria-hidden="true">▾</i></span>
        {#if editionChoices.length}
          <span class="v" title="An edition applies to Greek-only searches, in the plays that hold it"><select aria-label="Greek text to search" value={greekEd} on:change={(e) => (greekEd = e.currentTarget.value)}><option value="tlg">Each play's main text</option>{#each editionChoices as e}<option value={e.id}>{e.label}</option>{/each}</select><i aria-hidden="true">▾</i></span>
        {/if}
        <span class="mn">* wildcard · <button type="button" class="ln" on:click={openHelp} aria-haspopup="dialog">Beta Code</button> works</span>
      </p>
      {#if matchMode === 'lemma' && lemmaCands.some(t => t.cands.length)}
        <!-- The headwords each typed word can belong to; untick one to leave it out. -->
        <p class="row lsj">
          <span class="mn">LSJ</span>
          {#each lemmaCands as t, ti}
            {#each t.cands as c (c.fold)}
              <label class="ck lem" title={c.n ? `${c.n.toLocaleString('en-US')} times in the plays` : undefined}><input type="checkbox" checked={c.on} on:change={() => toggleCand(ti, c.fold)} /><span lang="grc">{c.heads.join(', ')}</span>{#if c.gloss}<span class="gl">{` — ${c.gloss}`}</span>{/if}</label>
            {/each}
          {/each}
          {#if entryCand?.slug}<a class="ln" href={lemmaEntryHref(import.meta.env.BASE_URL.replace(/\/$/, ''), 'grc', entryCand.slug)}>LSJ entry</a>{/if}
        </p>
      {/if}
      <p class="row">
        <span class="mn">Near</span>
        <span class="v"><select aria-label="Near the Greek: what" value={nearKind} on:change={(e) => (nearKind = e.currentTarget.value as NearKind)}><option value="none">nothing else</option><option value="grammatical">a grammatical shape</option><option value="lemma">any form of a word</option><option value="form">a word as typed</option></select><i aria-hidden="true">▾</i></span>
        {#if nearKind === 'form' || nearKind === 'lemma'}
          <input class="fld-sm greek-input" lang="grc" type="search" aria-label="The near word" placeholder="θεός" bind:value={nearText} on:keydown={onEnter} autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false" />
        {/if}
        {#if nearKind !== 'none'}
          <span class="v"><select aria-label="Where it stands" value={nearRel} on:change={(e) => (nearRel = e.currentTarget.value as SlotRelation)}><option value="near">near</option><option value="before">before</option><option value="after">after</option></select><i aria-hidden="true">▾</i></span>
          <span class="mn">it,</span>
          {#if nearUnit === 'words'}
            <span class="mn">within</span>
            <span class="v"><select aria-label="Within how many words" value={String(nearWindow)} on:change={(e) => (nearWindow = Number(e.currentTarget.value))}>{#each WINDOW_OPTS as n}<option value={String(n)}>{n}</option>{/each}</select><i aria-hidden="true">▾</i></span>
          {/if}
          <span class="v"><select aria-label="Words or line" value={nearUnit} on:change={(e) => (nearUnit = e.currentTarget.value as 'words' | 'line')}><option value="words">words</option><option value="line">on the same line</option></select><i aria-hidden="true">▾</i></span>
          {#if nearRel === 'near'}<label class="ck"><input type="checkbox" bind:checked={nearOrdered} />In this order</label>{/if}
          {#if grkQuery.trim().split(/\s+/).length > 1}<span class="mn">searched as one phrase</span>{/if}
        {/if}
      </p>
      {#if nearKind === 'grammatical'}
        <p class="row">
          <span class="mn">Shape</span>
          <span class="v"><select aria-label="Kind of word" value={shapeClass} on:change={(e) => { shapeClass = e.currentTarget.value as ShapeClass; shape = {}; }}><option value="verb">a verb form</option><option value="noun">a noun or adjective form</option><option value="word">a word class</option></select><i aria-hidden="true">▾</i></span>
          {#each SHAPE_CATS[shapeClass] as cat (cat.key)}
            <span class="v"><select aria-label={cat.key} value={shape[cat.key] ?? ''} on:change={(e) => (shape = { ...shape, [cat.key]: e.currentTarget.value })}><option value="">{cat.any}</option>{#each cat.values as [v, l]}<option value={v}>{l}</option>{/each}</select><i aria-hidden="true">▾</i></span>
          {/each}
          {#if !Object.keys(shapeQuery).length}<span class="mn">choose at least one</span>{/if}
        </p>
      {/if}
      <p class="row gap">
        <span class="mn">English</span>
        <span class="v"><select aria-label="English words" value={engMode} on:change={(e) => (engMode = e.currentTarget.value as SearchMode)}>{#each MODE_OPTS as opt}<option value={opt.v}>{opt.l}</option>{/each}</select><i aria-hidden="true">▾</i></span>
        <span class="v" title="Any form also finds plurals and possessives: man, men, man’s"><select aria-label="English forms" value={String(engForms)} on:change={(e) => (engForms = e.currentTarget.value === 'true')}><option value="true">Any form of the word</option><option value="false">Only as typed</option></select><i aria-hidden="true">▾</i></span>
        <span class="mn">in every translation</span>
      </p>
      <p class="row">
        <span class="mn">Near</span>
        <input class="fld-sm" type="search" aria-label="Another English word" placeholder="another word" bind:value={engNearText} on:keydown={onEnter} autocomplete="off" />
        {#if engNearText.trim()}
          <span class="v"><select aria-label="Where the English word stands" value={engNearRel} on:change={(e) => (engNearRel = e.currentTarget.value as SlotRelation)}><option value="near">near</option><option value="before">before</option><option value="after">after</option></select><i aria-hidden="true">▾</i></span>
          <span class="mn">it, within</span>
          <span class="v"><select aria-label="Within how many English words" value={String(engNearWindow)} on:change={(e) => (engNearWindow = Number(e.currentTarget.value))}>{#each WINDOW_OPTS as n}<option value={String(n)}>{n}</option>{/each}</select><i aria-hidden="true">▾</i></span>
          <span class="mn">words</span>
        {/if}
      </p>
      <p class="row gap">
        <span class="mn">Together</span>
        <span class="v"><select aria-label="Greek and English together" value={langOp} on:change={(e) => (langOp = e.currentTarget.value as LangOp)}><option value="and">Lines where both the Greek and the English match</option><option value="or">Lines where the Greek or the English matches</option></select><i aria-hidden="true">▾</i></span>
      </p>
      <div class="row">
        <span class="mn">In</span>
        <span class="sum">{worksSummary}</span>
        {#each AUTHOR_SCOPES as a}
          <label class="ck"><input type="checkbox" checked={authorTicked(a.ids)} on:change={() => tickAuthor(a.ids)} />{a.name} {a.ids.length}</label>
        {/each}
        <button type="button" class="ln" aria-expanded={worksOpen} on:click={() => (worksOpen = !worksOpen)}>choose plays</button>
      </div>
      {#if worksOpen}
        <div class="choose" role="group" aria-label="Plays to search">
          {#each AUTHOR_SCOPES as a}
            <p class="who">{a.name}</p>
            <p class="plays">
              {#each a.ids as id}
                {@const w = getWork(id)}
                {#if w}<label class="ck"><input type="checkbox" checked={selectedWorks.has(id)} on:change={() => toggleWork(id)} />{w.title}</label>{/if}
              {/each}
            </p>
          {/each}
          <p class="plays"><button type="button" class="ln" on:click={selectAll} disabled={allSelected}>All plays</button></p>
        </div>
      {/if}
    </div>
  </form>

  {#if showHelp}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div class="help-backdrop" on:click={closeHelp}>
      <div
        class="help-modal"
        bind:this={helpModal}
        role="dialog"
        aria-modal="true"
        aria-label="How to type Greek"
        tabindex="-1"
        on:click|stopPropagation
      >
        <!-- DRAFT copy: John approves. -->
        <div class="help-head">
          <h2>How to type Greek</h2>
          <button type="button" class="help-close" on:click={closeHelp} aria-label="Close">×</button>
        </div>
        <p class="help-intro">The Greek box takes Greek letters or Beta Code, Greek typed in Latin letters. Turn on β Beta Code to see Greek as you type; Shift gives a capital. One key for each letter:</p>
        <ul class="beta-grid">
          {#each BETA_LETTERS as L}
            <li><code>{L.beta}</code><span class="gk" lang="grc">{L.greek}</span><span class="nm">{L.name}</span></li>
          {/each}
        </ul>
        <h3>Accents and breathings (optional)</h3>
        <p class="help-sub">Type the mark after the vowel:</p>
        <ul class="mark-list">
          {#each BETA_MARKS as M}
            <li><code>{M.beta}</code><span class="gk" lang="grc">{M.example}</span><span class="nm">{M.name}</span></li>
          {/each}
        </ul>
        <h3>Examples</h3>
        <ul class="mark-list">
          {#each BETA_EXAMPLES as E}
            <li><code>{E.beta}</code><span class="gk" lang="grc">{E.greek}</span></li>
          {/each}
        </ul>
        <p class="help-foot"><code>h</code> is η and <code>w</code> is ω; <code>e</code> and <code>o</code> are ε and ο. <a class="ln" href={`${import.meta.env.BASE_URL.replace(/\/$/, '')}/search/how`}>How to search</a></p>
      </div>
    </div>
  {/if}

  {#if error}
    <p class="search-error">{error}</p>
  {:else if searched}
    {#if unsupportedWorks.length}
      <p class="search-note warn">Near uses each play’s main Greek text. These plays were searched in the chosen edition without Near: {failedPlaysPhrase(unsupportedWorks)}.</p>
    {/if}
    {#if failedWorks.length}
      <p class="search-note warn">
        Some plays could not be searched: {failedPlaysPhrase(failedWorks)}.
        <button type="button" class="ln retry-btn" on:click={doSearch} disabled={loading}>Retry</button>
      </p>
    {/if}
    <p class="count result-bar">
      <span class="result-count">{totalInstances === 0
        ? 'No passages found.'
        : `${totalInstances} line${totalInstances === 1 ? '' : 's'} in ${resultPlays} play${resultPlays === 1 ? '' : 's'}` +
          (searchCtx.grkAccentTerms.length ? ' before accent filtering' : '') +
          (pages.length > 1 ? ` · page ${pageIdx + 1} of ${pages.length}` : '')}</span>
      {#if totalInstances > 0}
        <button type="button" class="ln export-btn" on:click={exportCsv} disabled={csvBusy}>{csvBusy ? 'Preparing CSV…' : 'Export as CSV'}</button>
      {/if}
    </p>
    {#if csvNote}
      <p class="search-note">{csvNote}</p>
    {/if}

    {#if pages.length > 1}
      <nav class="pager" aria-label="Result pages">
        <button type="button" class="ln" on:click={() => goPage(pageIdx - 1)} disabled={pageIdx === 0 || pageLoading}>‹ Previous</button>
        <span class="pager-status">{pageLoading ? 'Loading…' : `Page ${pageIdx + 1} of ${pages.length}`}</span>
        <button type="button" class="ln" on:click={() => goPage(pageIdx + 1)} disabled={pageIdx >= pages.length - 1 || pageLoading}>Next ›</button>
      </nav>
    {/if}

    {#if pageError}
      <p class="search-note warn">
        {pageError}
        <button type="button" class="ln retry-btn" on:click={() => renderPage(pageIdx)} disabled={pageLoading}>Retry</button>
      </p>
    {/if}

    {#each groupsByWork as wg}
      {@const w = getWork(wg.work)}
      {@const lines = wg.books.reduce((n, [, gs]) => n + gs.reduce((m, g) => m + g.instances.length, 0), 0)}
      {@const grk = wg.books.some(([, gs]) => gs.some((g) => g.instances.some((i) => i.lang === 'grk')))}
      <section class="grp">
        <h2>
          <span class="tt">{w?.title ?? wg.work}</span>
          <span class="who">{[getAuthor(w?.author ?? '')?.name, grk ? greekTextOf(wg.work) : '', `${lines} line${lines === 1 ? '' : 's'}`].filter(Boolean).join(' · ')}</span>
        </h2>
        {#each wg.books as [book, bookGroups]}
          {#if schemeFor(wg.work).id !== 'play-line'}<p class="book book-name">{bookGroupLabel(wg.work)} {w?.bookLabels[book - 1] ?? book}</p>{/if}
          <ul>
            {#each bookGroups as g (g.key)}
              {@const unit = groupUnitLabel(wg.work)}
              <!-- A work with chapters or sections keeps their label over its
                   hits; a play has none (its group is the whole play). -->
              {#if !g.workWide}<li class="chap"><span class="group-label">{unit ? `${unit} ${g.chapter}` : g.chapter}</span>{#if g.bekker}<span class="group-bekker">{g.bekker}</span>{/if}</li>{/if}
              {#each g.instances as inst}
                <li class="instance">
                  <a class="ref num inst-ref" href={inst.jumpUrl} target="_blank" rel="noopener" title="Open in the reader (new tab)">{inst.ref}</a>
                  <span class="snip inst-snippet" class:greek={inst.lang === 'grk'} lang={inst.lang === 'grk' ? 'grc' : 'en'}>
                    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                    {@html inst.html}
                    <!-- Compact per-passage credit (finding 1, Sol review). -->
                    {#if inst.credit}<span class="inst-credit">{inst.credit}</span>{/if}
                  </span>
                </li>
              {/each}
            {/each}
          </ul>
        {/each}
      </section>
    {/each}

    {#if pages.length > 1}
      <nav class="pager pager-bottom" aria-label="Result pages">
        <button type="button" class="ln" on:click={() => goPage(pageIdx - 1)} disabled={pageIdx === 0 || pageLoading}>‹ Previous</button>
        <span class="pager-status">{pageLoading ? 'Loading…' : `Page ${pageIdx + 1} of ${pages.length}`}</span>
        <button type="button" class="ln" on:click={() => goPage(pageIdx + 1)} disabled={pageIdx >= pages.length - 1 || pageLoading}>Next ›</button>
      </nav>
    {/if}
  {/if}
</main>

<style>
  .search-page { max-width: 80rem; }
  .search-page :global(mark) { background: var(--hit); color: inherit; padding: 0 .08em; }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }

  /* The boxes at the left, every control at the right (§8.1). */
  .search-form {
    display: grid; grid-template-columns: minmax(18rem, 26rem) 1fr; gap: 1rem 3.5rem;
    max-width: 80rem; align-items: start; margin: 2rem 0 .4rem;
  }
  .boxes, .ctrls { min-width: 0; display: flex; flex-direction: column; gap: .55rem; }
  .lab { font: 400 1.05rem var(--font-ui); color: var(--mid); margin-top: .4rem; }
  .lab:first-child, .lab-row:first-child { margin-top: 0; }
  .lab-row { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin: 0; align-self: stretch; }
  .lab-row .lab { margin-top: 0; }
  .lab-acts { display: flex; flex-wrap: wrap; gap: .2rem 1.2rem; align-items: baseline; justify-content: flex-end; }
  .lab-row .ln, .tog { font: 400 .95rem var(--font-ui); }
  /* The toggle reads as one of B's checks: ☐ in mid, ☑ in ink with the box in the clay. */
  .tog { color: var(--mid); white-space: nowrap; }
  /* The box is decoration: aria-pressed carries the state, so the alt text is empty. */
  .tog::before { content: "☐ "; content: "☐ " / ""; }
  .tog[aria-pressed="true"] { color: var(--ink); }
  .tog[aria-pressed="true"]::before { content: "☑ "; content: "☑ " / ""; color: var(--clay-text); }
  .tog span { font-family: var(--font-greek); }
  .tog:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; }
  .fld {
    font: 400 1.8rem/1.25 var(--font-english); color: var(--ink);
    background: none; border: 0; border-bottom: 1px solid var(--line); border-radius: 0;
    padding: 0 0 .15rem; width: 100%; appearance: none; -webkit-appearance: none;
  }
  .greek-input { font-family: var(--font-greek); }
  .fld::placeholder { color: var(--mid); font-style: italic; font-size: 1.4rem; }
  .fld:focus { outline: none; border-bottom-color: var(--clay-text); }
  .act { display: flex; flex-wrap: wrap; gap: 1.4rem; align-items: baseline; margin: 1rem 0 0; font: 400 1rem var(--font-ui); }
  .go { font: 500 1.1rem var(--font-ui); color: var(--clay-text); }
  .ln { color: var(--mid); text-decoration: underline; text-underline-offset: 4px; font-family: var(--font-ui); }

  .row { display: flex; flex-wrap: wrap; gap: .3rem 1rem; align-items: baseline; margin: 0; font: 400 1rem var(--font-ui); color: var(--ink); }
  .row.gap { margin-top: .6rem; }
  .mn { color: var(--mid); }
  .row > .mn:first-child { min-width: 4.6rem; }
  /* A picker: the word in ink, underlined in the clay, a clay ▾. */
  /* Bounded by the row, so a long choice on a narrow phone ends in an
     ellipsis rather than pushing the page sideways. */
  .v { position: relative; display: inline-flex; align-items: baseline; white-space: nowrap; max-width: 100%; min-width: 0; }
  .v select {
    appearance: none; -webkit-appearance: none; border: 0; background: none; padding: 0; margin: 0;
    font: inherit; color: var(--ink); cursor: pointer;
    text-decoration: underline; text-decoration-color: var(--clay-text); text-underline-offset: 4px;
    field-sizing: content; min-width: 0; max-width: 100%; text-overflow: ellipsis;
  }
  .v select:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; }
  .v i { font-style: normal; font-size: .7em; color: var(--clay-text); margin-left: .2em; pointer-events: none; }
  /* A check: ☐ word in mid, ☑ word in ink with the box in the clay. */
  .ck { position: relative; color: var(--mid); white-space: nowrap; cursor: pointer; }
  .ck input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
  .ck::before { content: "☐ "; }
  .ck:has(input:checked) { color: var(--ink); }
  .ck:has(input:checked)::before { content: "☑ "; color: var(--clay-text); }
  .ck:has(input:focus-visible) { outline: 2px solid var(--clay); outline-offset: 2px; }
  .sum { color: var(--ink); }
  .lsj .lem span[lang="grc"] { font: 400 1.08rem var(--font-greek); }
  .lsj .gl { color: var(--mid); }
  /* A long gloss wraps inside its check rather than pushing the page sideways. */
  .lsj .ck { white-space: normal; max-width: 100%; }
  /* A word typed into a row: the boxes' underline, smaller. */
  .fld-sm {
    font: 400 1.08rem var(--font-english); color: var(--ink); background: none; border: 0;
    border-bottom: 1px solid var(--line); border-radius: 0; padding: 0 0 .05rem; width: 9rem; max-width: 100%;
    appearance: none; -webkit-appearance: none;
  }
  .fld-sm.greek-input { font-family: var(--font-greek); }
  .fld-sm::placeholder { color: var(--mid); font-style: italic; }
  .fld-sm:focus { outline: none; border-bottom-color: var(--clay-text); }
  .search-page :global(.sep) { color: var(--mid); }
  .choose { display: grid; grid-template-columns: max-content 1fr; gap: .4rem 1rem; align-items: baseline; margin: .2rem 0 0 5.6rem; }
  .choose .who { font: 400 1.05rem var(--font-english); color: var(--ink); margin: 0; }
  .choose .plays { display: flex; flex-wrap: wrap; gap: .25rem 1rem; margin: 0; font: 400 .95rem var(--font-ui); }
  .choose .plays:last-child { grid-column: 2; }

  /* The count, then one group per play, each hit a line with its number. */
  .count { display: flex; flex-wrap: wrap; gap: .3rem 1.2rem; margin: 2.2rem 0 .2rem; font: 400 1.05rem var(--font-ui); color: var(--mid); }
  .search-note, .search-error { font: 400 .95rem var(--font-ui); color: var(--mid); margin: 1rem 0 0; }
  .search-error, .warn { color: var(--error); }
  .pager { display: flex; gap: 1.2rem; align-items: baseline; margin: 1rem 0; font: 400 .95rem var(--font-ui); color: var(--mid); }
  .grp { margin: 1.3rem 0 1.8rem; }
  .grp h2 { display: flex; flex-wrap: wrap; align-items: baseline; gap: .3rem 1rem; margin: 0 0 .4rem; font-weight: 400; }
  .grp .tt { font: 400 1.6rem/1.1 var(--font-english); color: var(--ink); }
  .grp .who { font: 400 .95rem var(--font-ui); color: var(--mid); }
  .grp .book { font: 400 .95rem var(--font-ui); color: var(--mid); margin: .4rem 0 0; }
  .chap { display: flex; flex-wrap: wrap; gap: .2rem .8rem; padding: .6rem 0 .1rem; font: 400 .95rem var(--font-ui); color: var(--mid); }
  .chap .group-label { color: var(--ink); }
  .grp ul { list-style: none; margin: 0; padding: 0; }
  .instance { display: grid; grid-template-columns: 4rem 1fr; gap: 1rem; padding: .3rem 0; font: 400 1.12rem/1.5 var(--font-english); max-width: 50rem; }
  .instance .ref {
    font: 400 .88rem var(--font-ui); color: var(--clay-text); text-align: right; padding-top: .4em;
    text-decoration: none; font-variant-numeric: tabular-nums;
  }
  .instance .ref:hover { text-decoration: underline; }
  .snip.greek { font-family: var(--font-greek); }
  .inst-credit { display: block; font: 400 .85rem var(--font-ui); color: var(--mid); }

  /* "Type Greek": the reader's Help dialog (HelpButton.svelte), holding the
     How to search page's chart. */
  .help-backdrop {
    position: fixed; inset: 0; z-index: 50; overflow-y: auto;
    display: flex; align-items: flex-start; justify-content: center;
    padding: 2rem 1rem; background: rgba(0, 0, 0, 0.4);
    animation: backdrop-in 0.18s ease-out;
  }
  .help-modal {
    width: 100%; max-width: 36rem; padding: 1.25rem 1.5rem 1.75rem;
    background: var(--popup-bg); color: var(--ink); border-radius: 8px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
    font: 400 1rem/1.5 var(--font-ui);
    animation: modal-in 0.2s cubic-bezier(0.2, 0, 0, 1);
  }
  @keyframes backdrop-in { from { opacity: 0; } to { opacity: 1; } }
  @keyframes modal-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @media (prefers-reduced-motion: reduce) { .help-backdrop, .help-modal { animation: none; } }
  .help-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: .5rem; }
  .help-head h2 { font: 400 1.6rem/1.2 var(--font-english); margin: 0; }
  .help-close { font-size: 1.6rem; line-height: 1; color: var(--mid); padding: 0 .25rem; }
  .help-close:hover { color: var(--ink); }
  .help-intro, .help-sub, .help-foot { margin: .4rem 0; color: var(--ink); text-wrap: pretty; }
  .help-modal h3 { font: 400 1rem var(--font-ui); color: var(--mid); margin: 1.2rem 0 .3rem; }
  .help-modal ul { list-style: none; margin: .4rem 0; padding: 0; }
  .help-modal li { display: flex; gap: .6rem; align-items: baseline; padding: .1rem 0; }
  .help-modal code { font: 400 .95rem ui-monospace, Menlo, monospace; }
  .help-modal li code { min-width: 1.4rem; color: var(--clay-text); }
  .help-modal .gk { font-family: var(--font-greek); font-size: 1.08rem; }
  .help-modal .nm { font-size: .9rem; color: var(--mid); }
  .beta-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); gap: 0 1.2rem; }
  .help-foot { margin-top: 1rem; padding-top: .75rem; border-top: 1px solid var(--hair); }
  .help-foot .ln { margin-left: .4rem; }

  /* Phone: one column, the boxes, the controls, then Search (§8.1). */
  @media (max-width: 700px) {
    .search-form { display: flex; flex-direction: column; gap: .55rem; margin-top: 1.2rem; }
    .boxes { display: contents; }
    .ctrls { order: 2; margin-top: .6rem; }
    .act { order: 3; }
    .fld { font-size: 1.4rem; }
    .row { font-size: .95rem; gap: .25rem .8rem; }
    .choose { grid-template-columns: 1fr; margin-left: 0; }
    .choose .plays:last-child { grid-column: 1; }
    .grp h2 .tt { font-size: 1.35rem; }
    .instance { grid-template-columns: 3rem 1fr; gap: .6rem; font-size: 1.05rem; }
  }
</style>
