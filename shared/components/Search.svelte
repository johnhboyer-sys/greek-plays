<script lang="ts">
  import { tick, onMount } from 'svelte';
  import { search, type SearchMode, type LangOp, type MatchMode, type SearchResult } from '../lib/search';
  import { fetchBook, fetchChapters, fetchSections, readerHref, type Segment, type GreekLine, type ChapterRef, type SectionRef, type TranslationCredit } from '../lib/data';
  import { highlightPrefixMatches } from '../lib/text';
  import { editionPicker } from '../lib/edition-picker';
  import { WORKS, getWork, workPath, WORK_ORDER } from '../lib/works';
  import { getAuthor, AUTHORS } from '../lib/authors';
  import { formatCite, formatLocValue, schemeFor, groupUnitNoun } from '../lib/citation';

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
  let searchedLemmata: string[] = [];
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
  interface SearchCtx { grkQuery: string; engQuery: string; engTerms: string[]; grkAccentTerms: string[]; }
  let searchCtx: SearchCtx = { grkQuery: '', engQuery: '', engTerms: [], grkAccentTerms: [] };

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
    return (r.grkMatch ? r.grkPositions.length : 0) + (r.engMatch ? r.engPositions.length : 0);
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
        for (const pos of r.grkPositions) {
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
        // One instance per occurrence in this translation's full text.
        for (const off of r.engPositions) {
          const text = r.englishText ?? seg.english?.text ?? '';
          const sourceLine = englishLineAt(seg, off, text);
          if (!sourceLine) continue;
          const playLine = schemeFor(r.work).id === 'play-line';
          const column = playLine ? sourceLine.ref ?? seg.column : seg.column;
          const ch = lookup(seg.column, sourceLine.n);
          add(r.work, r.meta.book, ch, {
            lang: 'eng', column, line: sourceLine.n,
            ref: playLine ? formatCite(r.work, column, sourceLine.n) : seg.column,
            html: englishKwicAt(text, off, ctx.engTerms),
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

  async function renderPage(i: number) {
    pageIdx = i;
    pageLoading = true;
    pageError = '';
    try {
      const { groups: g, failed } = await buildGroups(pages[i] ?? [], searchCtx);
      groups = g;
      if (failed.length) {
        pageError = `${failed.length} passage source${failed.length === 1 ? '' : 's'} on this page didn’t load — some hits may be missing.`;
      }
    } catch (err) {
      pageError = String(err);
      groups = [];
    } finally {
      pageLoading = false;
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
  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    const g = params.get('g');
    const en = params.get('e') ?? params.get('q');
    if (g) grkQuery = g;
    if (en) engQuery = en;
    if (g || en) doSearch();
  });

  async function doSearch(e?: Event) {
    e?.preventDefault();
    if (!grkQuery.trim() && !engQuery.trim()) return;
    loading = true;
    error = '';
    pageError = '';
    csvNote = '';
    failedWorks = [];
    searched = false;
    try {
      const works = WORKS.map(w => w.id).filter(id => selectedWorks.has(id));
      // Snapshot the submitted query for all deferred (per-page / CSV) rendering.
      searchCtx = {
        grkQuery: grkQuery.trim(),
        engQuery: engQuery.trim(),
        engTerms: engQuery.trim().split(/\s+/).filter(Boolean),
        grkAccentTerms: accentSensitive
          ? grkQuery.trim().split(/\s+/).filter(Boolean).map(accentNorm)
          : [],
      };
      const { results, failed, lemmata } = await search(grkQuery, engQuery, grkMode, engMode, langOp, works, matchMode, greekEd);
      searchedLemmata = lemmata ?? [];
      resultEds = new Map(results.filter((r) => r.ed).map((r) => [r.work, r.ed!]));
      resultPlays = new Set(results.map((r) => r.work)).size;
      failedWorks = failed;
      totalInstances = results.reduce((n, r) => n + instCount(r), 0);
      pages = paginate(results);
      searched = true;
      if (pages.length) await renderPage(0);
      else { groups = []; pageIdx = 0; }
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      loading = false;
    }
  }

  // A play's Greek hit shows its whole verse line, the match marked (UI pass
  // 2, spec §8.1: "the lines under it, each with its number ... and the
  // matched word marked").
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
  function englishKwicAt(text: string, pos: number, terms: string[]): string {
    if (!text) return '';
    const earliest = pos >= 0 && pos < text.length ? pos : 0;
    let start = Math.max(0, earliest - ENG_WINDOW);
    let end = Math.min(text.length, earliest + ENG_WINDOW);
    if (start > 0) {
      const sp = text.indexOf(' ', start);
      if (sp >= 0 && sp < earliest) start = sp + 1;
    }
    if (end < text.length) {
      const sp = text.lastIndexOf(' ', end);
      if (sp > earliest) end = sp;
    }
    let html = highlightEnglish(text.slice(start, end), terms);
    if (start > 0) html = '… ' + html;
    if (end < text.length) html = html + ' …';
    return html;
  }

  function highlightEnglish(text: string, terms: string[]): string {
    return highlightPrefixMatches(text, terms);
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
</script>

<!-- UI pass 2, direction B (docs/redesign/HANDOFF-ui-pass2-build.md §8.1): the
     two boxes at the left, Greek over English, searched together; every control
     to their right, one row each (John, 2026-10-20: "Put all the controls to the
     right of search boxes"); the plays head their hits, each hit a whole line.
     Only what this engine answers is shown: the Near and Shape rows and the
     phrase index wait for step 2, the port of the Aristotle reader's search. -->
<main class="search-page">
  <form class="search-form" on:submit={doSearch} novalidate>
    <div class="boxes">
      <label class="lab" for="grk-input">Greek</label>
      <input
        id="grk-input"
        class="fld greek-input"
        lang="grc"
        type="search"
        placeholder="ξίφος, or xifos, fron*"
        bind:value={grkQuery}
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
        <span class="mn">* wildcard · Beta Code works</span>
      </p>
      {#if searchedLemmata.length}
        <p class="row lsj"><span class="mn">LSJ</span>{#each searchedLemmata as lemma}<span class="lem" lang="grc">{lemma}</span>{/each}</p>
      {/if}
      <p class="row gap">
        <span class="mn">English</span>
        <span class="v"><select aria-label="English words" value={engMode} on:change={(e) => (engMode = e.currentTarget.value as SearchMode)}>{#each MODE_OPTS as opt}<option value={opt.v}>{opt.l}</option>{/each}</select><i aria-hidden="true">▾</i></span>
        <span class="mn">in every translation</span>
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

  {#if error}
    <p class="search-error">{error}</p>
  {:else if searched}
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
  .lab:first-child { margin-top: 0; }
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
  .lsj .lem { font: 400 1.08rem var(--font-greek); color: var(--ink); }
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
