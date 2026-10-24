<script lang="ts">
  // The phrase index: every run of two to five words that recurs in the plays.
  // Logic ported from the Aristotle reader's Phrases.svelte (2026-10-24); the
  // layout is this site's B search layout (boxes left, controls right, then the
  // count and the list). DRAFT copy: John approves.
  import { onMount } from 'svelte';
  import {
    decodeOffsets,
    fetchEnglishSegments,
    fetchNgramOccurrences,
    fetchNgramShard,
    fetchSearchOffsets,
    type NgramRow,
    type NgramStream,
  } from '../lib/data';
  import { betaToGreek } from '../lib/betacode';
  import { greekFold } from '../lib/search';
  import { VARIANT_READING_CAP, lemmaOptions, lemmaReadings } from '../lib/search-advanced';
  import { WORKS, getWork, workPath } from '../lib/works';
  import { AUTHORS } from '../lib/authors';
  import { formatLocValue } from '../lib/citation';

  type SortMode = 'score' | 'frequency' | 'length' | 'alphabetical';

  interface PhraseItem { key: string; row: NgramRow; }

  // What the typed prefix resolves to: the shards to read and, in each, the key
  // prefixes that count as a match. One letter and one prefix for the surface
  // and English streams; for "any form", one prefix per reading of the typed
  // words, and those readings do not all live in the same shard.
  interface Plan {
    key: string;
    stream: NgramStream;
    byLetter: Array<{ letter: string; prefixes: string[] }>;
    readings: string[][];
    cappedFrom: number;
  }

  interface Citation { label: string; href: string; }
  interface WorkCitations { id: string; title: string; total: number; citations: Citation[]; error?: string; }
  interface PhraseDetails { loading: boolean; error: string; works: WorkCitations[]; }

  // The slice of offsets.json this page reads (pipeline stage 6).
  interface Offsets {
    token_count: number;
    seg_base_offset: number[];
    segments: { book: number; column: string; line_runs: [number, number, string?][]; refs?: string[] }[];
  }

  const DEFAULT_LETTER = 'k';
  // Real rows from the index, each found in many plays (built 2026-10-24).
  const EXAMPLES = [
    { greek: 'πρὸς θεῶν', gloss: 'by the gods' },
    { greek: 'ὦ τέκνον', gloss: 'my child' },
    { greek: 'νὴ Δία', gloss: 'by Zeus' },
    { greek: 'φεῦ φεῦ', gloss: 'alas, alas' },
  ];
  const ENGLISH_EXAMPLES = [
    { greek: 'tell me', gloss: '' },
    { greek: 'no longer', gloss: '' },
    { greek: 'son of', gloss: '' },
  ];
  // The fold letters, shown as Greek for the Greek lists.
  const BROWSE_LETTERS = 'abgdezhqiklmncoprstufxyw'.split('');

  // English builds its grammar from small words in fixed order, so "of the"
  // and "it is" outrank anything the plays say. The default view hides phrases
  // made only of these words; it changes no score, and a check shows them.
  const FUNCTION_WORDS = new Set(`a an the this that these those which who whom whose what
    and or but nor if then than as so because although though while whereas
    of in on at to for from by with without within into upon about against
    among between through during over under above below across along
    is are was were be been being am do does did done have has had having
    will would shall should may might can could must let
    it its he she they them their his her our your my we you i one
    not no nor never ever also too very much more most less least
    there here now when where how why some any all both each every other another same
    thou thee thy thine ye art hast hath dost doth shalt wilt`
    .split(/\s+/));

  function contentWords(phrase: string): number {
    let n = 0;
    for (const w of phrase.split(' ')) if (!FUNCTION_WORDS.has(w)) n++;
    return n;
  }

  // The shard a phrase lives in, by its first letter — the rule stage 8 used.
  function shardLetter(phrase: string): string {
    const first = phrase[0] ?? '';
    return first >= 'a' && first <= 'z' ? first : '_';
  }
  const PAGE_SIZE = 50;
  const CITATION_CAP = 40;
  const BASE_URL = import.meta.env.BASE_URL.replace(/\/$/, '');
  const WORK_ORDER = new Map(WORKS.map((work, index) => [work.id, index]));
  const countFormat = new Intl.NumberFormat('en-US');

  const AUTHOR_SCOPES = AUTHORS
    .map((a) => ({ id: a.id, name: a.name, ids: WORKS.filter((w) => w.author === a.id).map((w) => w.id) }))
    .filter((a) => a.ids.length > 0);

  let mounted = false;
  let stream: NgramStream = 'form';
  let prefix = '';
  let lengths: number[] = [2, 3, 4, 5];
  let minCount = 2;
  let selectedWorks: string[] = [];   // none = every play
  let worksOpen = false;
  let sort: SortMode = 'score';
  let hideCommon = true;
  let page = 0;

  let plan: Plan = { key: '', stream: 'form', byLetter: [], readings: [], cappedFrom: 0 };
  let planLoading = false;
  let requestedPlanKey = '';
  let planRequest = 0;

  let loadedShards: Array<Record<string, NgramRow>> = [];
  let loadedShardSignature = '';
  let shardLoading = false;
  let shardError = '';
  let requestedShardSignature = '';
  let shardRequest = 0;

  let requestedWorkSignature = '';
  let loadedWorkSignature = '';
  let matchingWorkPhrases: Set<string> | null = null;
  let workFilterLoading = false;
  let workFilterError = '';
  let workRequest = 0;

  let expanded = new Set<string>();
  let details: Record<string, PhraseDetails> = {};

  const offsetsCache = new Map<string, Promise<Offsets>>();

  // The index is keyed on accent-folded Beta Code, but nobody should have to
  // know that: fold whatever is typed, Greek or Latin, word by word.
  $: isEnglish = stream === 'english';
  $: isLemma = stream === 'lemma';
  $: normalizedPrefix = isEnglish
    ? prefix.trim().toLowerCase().replace(/[‘’ʼ]/g, "'").replace(/[^a-z' ]+/g, '').replace(/\s+/g, ' ')
    : prefix.trim().toLowerCase().split(/\s+/).map(greekFold).filter(Boolean).join(' ');
  $: letter = normalizedPrefix ? shardLetter(normalizedPrefix) : DEFAULT_LETTER;
  $: minimum = Number.isFinite(minCount) ? Math.max(2, Math.floor(minCount)) : 2;
  $: selectedLengthKey = [...lengths].sort((a, b) => a - b).join(',');
  $: selectedWorkKey = [...selectedWorks].sort().join(',');

  $: planKey = `${stream}|${normalizedPrefix}`;
  $: if (mounted && planKey !== requestedPlanKey) {
    void makePlan(planKey, stream, normalizedPrefix, letter);
  }

  // Nothing downstream may act on a plan that answers an older query.
  $: activePlan = plan.key === planKey ? plan : null;
  $: shardSignature = activePlan
    ? `${activePlan.stream}/${activePlan.byLetter.map((b) => b.letter).join(',')}`
    : '';

  $: if (mounted && shardSignature && shardSignature !== requestedShardSignature) {
    void loadShards(shardSignature, activePlan!);
  }

  $: scan = loadedShardSignature === shardSignature && activePlan
    ? scanShards(activePlan, loadedShards, lengths, minimum, isEnglish && hideCommon)
    : { rows: [] as PhraseItem[], matched: [] as string[] };
  $: localRows = scan.rows;

  // The play filter reads occurrence files, one per shard letter per length,
  // and only for the letters that produced rows.
  $: matchedLetters = [...new Set(localRows.map((item) => shardLetter(item.key)))].sort();
  $: workSignature = selectedWorks.length && matchedLetters.length
    ? `${stream}/${matchedLetters.join(',')}|${selectedLengthKey}|${selectedWorkKey}`
    : '';

  $: if (mounted && workSignature !== requestedWorkSignature) {
    void loadWorkFilter(workSignature, stream, [...matchedLetters], [...lengths], [...selectedWorks]);
  }

  $: filteredRows = selectedWorks.length === 0
    ? localRows
    : loadedWorkSignature === workSignature && matchingWorkPhrases
      ? localRows.filter((item) => matchingWorkPhrases?.has(item.key))
      : [];

  $: widened = activePlan?.readings.length ? activePlan : null;

  const READINGS_SHOWN = 6;
  $: matchedReadings = widened ? scan.matched.slice(0, READINGS_SHOWN).map((p) => betaToGreek(p)) : [];
  $: matchedRest = widened ? Math.max(0, scan.matched.length - READINGS_SHOWN) : 0;

  $: sortedRows = [...filteredRows].sort((a, b) => comparePhrases(a, b, sort));
  $: pageCount = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE));
  $: if (page >= pageCount) page = pageCount - 1;
  $: pageRows = sortedRows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  $: shownFrom = sortedRows.length ? page * PAGE_SIZE + 1 : 0;
  $: shownTo = Math.min((page + 1) * PAGE_SIZE, sortedRows.length);

  $: worksSummary = selectedWorks.length === 0
    ? `All ${WORKS.length} plays`
    : `${selectedWorks.length} play${selectedWorks.length === 1 ? '' : 's'}`;
  $: authorTicked = (ids: string[]) => selectedWorks.length > 0 && ids.every((id) => selectedWorks.includes(id));

  onMount(() => {
    const p = new URLSearchParams(window.location.search);
    const s = p.get('s');
    if (s === 'form' || s === 'lemma' || s === 'english') stream = s;
    prefix = p.get('p') ?? '';
    mounted = true;
  });

  // The list's state in the address, so a list can be shared.
  $: if (mounted) {
    const p = new URLSearchParams();
    if (stream !== 'form') p.set('s', stream);
    if (prefix.trim()) p.set('p', prefix.trim());
    const qs = p.toString();
    const next = `${window.location.pathname}${qs ? `?${qs}` : ''}`;
    if (next !== `${window.location.pathname}${window.location.search}`) history.replaceState(null, '', next);
  }

  function comparePhrases(a: PhraseItem, b: PhraseItem, mode: SortMode): number {
    if (mode === 'frequency') return b.row[1] - a.row[1] || b.row[2] - a.row[2] || a.key.localeCompare(b.key);
    if (mode === 'length') return a.row[0] - b.row[0] || b.row[2] - a.row[2] || a.key.localeCompare(b.key);
    if (mode === 'alphabetical') return a.key.localeCompare(b.key);
    return b.row[2] - a.row[2] || b.row[1] - a.row[1] || a.key.localeCompare(b.key);
  }

  function tickAuthor(ids: string[]) {
    selectedWorks = ids.every((id) => selectedWorks.includes(id))
      ? selectedWorks.filter((id) => !ids.includes(id))
      : [...new Set([...selectedWorks, ...ids])];
    page = 0;
  }
  function toggleWork(id: string) {
    selectedWorks = selectedWorks.includes(id) ? selectedWorks.filter((w) => w !== id) : [...selectedWorks, id];
    page = 0;
  }

  // A single letter is left alone: the letter links type into the same box,
  // and widening one letter would move the browse to another shard.
  function widenable(prefixText: string): boolean {
    return prefixText.length > 1;
  }

  /** Which shards to read for the typed prefix, and what counts as a match.
   *
   * The any-form list is keyed on headwords, so a phrase typed as it stands on
   * the page matches nothing literally. Resolve each typed word to the
   * headwords it can belong to and match every reading of the phrase; a word
   * the map does not know (a fragment still being typed) stands for itself.
   */
  async function makePlan(key: string, nextStream: NgramStream, prefixText: string, fallbackLetter: string) {
    const request = ++planRequest;
    requestedPlanKey = key;
    const literal: Plan = {
      key,
      stream: nextStream,
      byLetter: [{ letter: prefixText ? shardLetter(prefixText) : fallbackLetter, prefixes: prefixText ? [prefixText] : [] }],
      readings: [],
      cappedFrom: 0,
    };
    if (nextStream !== 'lemma' || !widenable(prefixText)) {
      plan = literal;
      planLoading = false;
      return;
    }
    planLoading = true;
    try {
      const terms = prefixText.split(' ');
      const options = await lemmaOptions(terms);
      if (request !== planRequest) return;
      if (!options || options.every((o) => !o.length)) { plan = literal; return; }
      const perTerm = terms.map((term, i) => (options[i].length ? options[i] : [term]));
      const { readings, total } = lemmaReadings(perTerm, VARIANT_READING_CAP);
      const byLetter = new Map<string, string[]>();
      for (const reading of readings) {
        const l = shardLetter(reading[0]);
        const prefixes = byLetter.get(l) ?? [];
        prefixes.push(reading.join(' '));
        byLetter.set(l, prefixes);
      }
      plan = {
        key,
        stream: nextStream,
        byLetter: [...byLetter].map(([l, prefixes]) => ({ letter: l, prefixes })),
        readings,
        cappedFrom: total > readings.length ? total : 0,
      };
    } catch {
      if (request !== planRequest) return;
      plan = literal;
    } finally {
      if (request === planRequest) planLoading = false;
    }
  }

  async function loadShards(signature: string, forPlan: Plan) {
    const request = ++shardRequest;
    requestedShardSignature = signature;
    shardLoading = true;
    shardError = '';
    page = 0;
    expanded = new Set();
    try {
      // A letter no phrase starts with has no shard: read it as empty.
      const next = await Promise.all(forPlan.byLetter.map((b) =>
        fetchNgramShard(forPlan.stream, b.letter).catch((err) => {
          if (/HTTP 404/.test(String(err))) return {} as Record<string, NgramRow>;
          throw err;
        })));
      if (request !== shardRequest) return;
      loadedShards = next;
      loadedShardSignature = signature;
    } catch {
      if (request !== shardRequest) return;
      loadedShards = [];
      loadedShardSignature = '';
      shardError = 'The phrase list could not be loaded.';
    } finally {
      if (request === shardRequest) shardLoading = false;
    }
  }

  /** The rows that pass every filter, and the readings that produced them. */
  function scanShards(
    forPlan: Plan,
    shards: Array<Record<string, NgramRow>>,
    keepLengths: number[],
    minimumCount: number,
    dropCommon: boolean,
  ): { rows: PhraseItem[]; matched: string[] } {
    const rows: PhraseItem[] = [];
    const seenMatch = new Set<string>();
    forPlan.byLetter.forEach(({ prefixes }, i) => {
      const shard = shards[i];
      if (!shard) return;
      for (const [key, row] of Object.entries(shard)) {
        let hit = '';
        if (prefixes.length) {
          for (const p of prefixes) if (key.startsWith(p)) { hit = p; break; }
          if (!hit) continue;
        }
        if (!keepLengths.includes(row[0])) continue;
        if (row[1] < minimumCount) continue;
        if (dropCommon && contentWords(key) < 2) continue;
        rows.push({ key, row });
        if (hit) seenMatch.add(hit);
      }
    });
    const matched = forPlan.readings.map((r) => r.join(' ')).filter((p) => seenMatch.has(p));
    return { rows, matched };
  }

  async function loadWorkFilter(signature: string, nextStream: NgramStream, nextLetters: string[], nextLengths: number[], works: string[]) {
    const request = ++workRequest;
    requestedWorkSignature = signature;
    loadedWorkSignature = '';
    matchingWorkPhrases = null;
    workFilterError = '';
    if (!signature) { workFilterLoading = false; return; }
    workFilterLoading = true;
    try {
      const occurrences = await Promise.all(nextLetters.flatMap((l) =>
        [...nextLengths].sort((a, b) => a - b).map((n) =>
          fetchNgramOccurrences(nextStream, l, n).catch((err) => {
            if (/HTTP 404/.test(String(err))) return {} as Record<string, Record<string, number[]>>;
            throw err;
          }))));
      if (request !== workRequest) return;
      const matches = new Set<string>();
      for (const occurrenceShard of occurrences) {
        for (const [phrase, byWork] of Object.entries(occurrenceShard)) {
          if (works.some((work) => work in byWork)) matches.add(phrase);
        }
      }
      matchingWorkPhrases = matches;
      loadedWorkSignature = signature;
      page = 0;
    } catch {
      if (request !== workRequest) return;
      workFilterError = 'The play filter could not be applied.';
    } finally {
      if (request === workRequest) workFilterLoading = false;
    }
  }

  function phraseId(item: PhraseItem): string {
    return `${stream}-${shardLetter(item.key)}-${item.row[0]}-${item.key.replace(/[^a-z0-9_-]+/g, '-')}`;
  }

  function togglePhrase(item: PhraseItem) {
    const id = phraseId(item);
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else {
      next.add(id);
      if (!details[id]) void loadPhraseDetails(id, item);
    }
    expanded = next;
  }

  function fetchWorkOffsets(work: string): Promise<Offsets> {
    const cached = offsetsCache.get(work);
    if (cached) return cached;
    const promise = fetchSearchOffsets(work) as Promise<Offsets>;
    promise.catch(() => { if (offsetsCache.get(work) === promise) offsetsCache.delete(work); });
    offsetsCache.set(work, promise);
    return promise;
  }

  // A global token offset -> the line it falls on: its book, segment column,
  // running number n (what the reader's loc= takes) and printed ref.
  function lineAt(offsets: Offsets, global: number): { book: number; column: string; n: number; ref: string } | null {
    if (global < 0 || global >= offsets.token_count) return null;
    const base = offsets.seg_base_offset;
    let lo = 0;
    let hi = base.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (base[mid] <= global) lo = mid; else hi = mid - 1;
    }
    const seg = offsets.segments[lo];
    let at = base[lo];
    for (let i = 0; i < seg.line_runs.length; i++) {
      const [n, count] = seg.line_runs[i];
      if (global < at + count) return { book: seg.book, column: seg.column, n, ref: seg.refs?.[i] ?? String(n) };
      at += count;
    }
    return null;
  }

  const lineHref = (work: string, book: number, column: string, n: number | null) =>
    `${BASE_URL}${workPath(work, book)}?loc=${formatLocValue(work, column, n)}`;

  async function pool<T>(items: T[], limit: number, fn: (item: T, index: number) => Promise<void>): Promise<void> {
    let next = 0;
    await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (next < items.length) { const i = next++; await fn(items[i], i); }
    }));
  }

  async function loadPhraseDetails(id: string, item: PhraseItem) {
    // The stream as it was when the phrase was opened: switching lists while
    // this loads must not resolve one list's offsets through another's.
    const forStream = stream;
    details = { ...details, [id]: { loading: true, error: '', works: [] } };
    try {
      const occurrenceShard = await fetchNgramOccurrences(forStream, shardLetter(item.key), item.row[0]);
      const byWork = occurrenceShard[item.key];
      if (!byWork) throw new Error('Phrase missing from its occurrence shard');
      const entries = Object.entries(byWork).sort(([a], [b]) =>
        (WORK_ORDER.get(a) ?? Number.MAX_SAFE_INTEGER) - (WORK_ORDER.get(b) ?? Number.MAX_SAFE_INTEGER));
      const groups: WorkCitations[] = entries.map(([work, deltas]) => ({
        id: work, title: getWork(work)?.title ?? work, total: deltas.length, citations: [],
      }));
      const englishSegments = forStream === 'english' ? await fetchEnglishSegments() : null;
      await pool(entries, 6, async ([work, deltas], index) => {
        try {
          let citations: Citation[];
          if (englishSegments) {
            // The translation is stored one passage per segment, so an English
            // offset resolves to the passage, cited by its first line.
            const segs = englishSegments[work] ?? [];
            citations = decodeOffsets(deltas)
              .map((global) => {
                let found: (typeof segs)[number] | null = null;
                for (const seg of segs) { if (seg.base > global) break; found = seg; }
                return found;
              })
              .filter((seg): seg is (typeof segs)[number] => seg !== null)
              .slice(0, CITATION_CAP)
              .map((seg) => ({ label: seg.column, href: lineHref(work, seg.book, seg.column, null) }));
          } else {
            const offsets = await fetchWorkOffsets(work);
            citations = decodeOffsets(deltas)
              .map((global) => lineAt(offsets, global))
              .filter((ref): ref is NonNullable<typeof ref> => ref !== null)
              .slice(0, CITATION_CAP)
              .map((ref) => ({ label: ref.ref, href: lineHref(work, ref.book, ref.ref, ref.n) }));
          }
          groups[index] = { ...groups[index], citations };
        } catch {
          groups[index] = { ...groups[index], error: 'The lines for this play could not be found.' };
        }
      });
      details = { ...details, [id]: { loading: false, error: '', works: groups } };
    } catch {
      details = { ...details, [id]: { loading: false, error: 'This phrase’s lines could not be loaded.', works: [] } };
    }
  }

  const letterLabel = (l: string) => (isEnglish ? l : betaToGreek(l));
</script>

<div class="phrases-page">
  <form class="phrase-form" on:submit|preventDefault>
    <div class="boxes">
      <label class="lab" for="phrase-prefix">Phrase starts with</label>
      <input
        id="phrase-prefix"
        class="fld"
        class:greek-input={!isEnglish}
        type="search"
        placeholder={isEnglish ? 'the gods' : 'ὦ τέκνον, or w teknon'}
        bind:value={prefix}
        on:input={() => (page = 0)}
        autocomplete="off"
        autocorrect="off"
        autocapitalize="none"
        spellcheck="false"
      />
      {#if widened && matchedReadings.length}
        <p class="note" aria-live="polite">
          Read as {#each matchedReadings as reading, i}<span lang="grc">{reading}</span>{i < matchedReadings.length - 1 ? ', ' : ''}{/each}{#if matchedRest} and {countFormat.format(matchedRest)} more{/if}.
          {#if widened.cappedFrom}The first {VARIANT_READING_CAP} of {countFormat.format(widened.cappedFrom)} readings were tried.{/if}
        </p>
      {/if}
      <p class="act">
        <a class="ln" href={`${BASE_URL}/search`}>Search</a>
        <a class="ln" href={`${BASE_URL}/search/how#phrases`}>How to search</a>
      </p>
    </div>

    <div class="ctrls">
      <p class="row">
        <span class="mn">Count</span>
        <span class="v"><select aria-label="Count phrases by" value={stream} on:change={(e) => { stream = e.currentTarget.value as NgramStream; page = 0; }}>
          <option value="form">Greek words as written</option>
          <option value="lemma">Greek words in any form</option>
          <option value="english">English, each play's main translation</option>
        </select><i aria-hidden="true">▾</i></span>
      </p>
      <p class="row">
        <span class="mn">Length</span>
        {#each [2, 3, 4, 5] as n}
          <label class="ck"><input type="checkbox" value={n} bind:group={lengths} on:change={() => (page = 0)} />{n} words</label>
        {/each}
      </p>
      <p class="row">
        <span class="mn">At least</span>
        <span class="v"><select aria-label="Minimum count" value={String(minimum)} on:change={(e) => { minCount = Number(e.currentTarget.value); page = 0; }}>
          {#each [2, 3, 5, 10, 20, 50] as n}<option value={String(n)}>{n} times</option>{/each}
        </select><i aria-hidden="true">▾</i></span>
      </p>
      <p class="row">
        <span class="mn">Order</span>
        <span class="v" title="Most distinctive: how much more often the phrase occurs than its words would by chance. It orders the list; it hides nothing."><select aria-label="Order" value={sort} on:change={(e) => { sort = e.currentTarget.value as SortMode; page = 0; }}>
          <option value="score">Most distinctive first</option>
          <option value="frequency">Commonest first</option>
          <option value="length">Shortest first</option>
          <option value="alphabetical">Alphabetical</option>
        </select><i aria-hidden="true">▾</i></span>
        {#if isEnglish}
          <label class="ck" title="Phrases such as “of the” and “it is”; this changes no count"><input type="checkbox" bind:checked={hideCommon} on:change={() => (page = 0)} />Hide phrases of small words only</label>
        {/if}
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
        <div class="choose" role="group" aria-label="Plays">
          {#each AUTHOR_SCOPES as a}
            <p class="who">{a.name}</p>
            <p class="plays">
              {#each a.ids as id}
                {@const w = getWork(id)}
                {#if w}<label class="ck"><input type="checkbox" checked={selectedWorks.includes(id)} on:change={() => toggleWork(id)} />{w.title}</label>{/if}
              {/each}
            </p>
          {/each}
          <p class="plays"><button type="button" class="ln" on:click={() => { selectedWorks = []; page = 0; }} disabled={!selectedWorks.length}>All plays</button></p>
        </div>
      {/if}
    </div>
  </form>

  <p class="letters" aria-label="Phrases beginning with">
    {#each BROWSE_LETTERS as l}
      <button type="button" class:on={normalizedPrefix === l} lang={isEnglish ? 'en' : 'grc'} on:click={() => { prefix = isEnglish ? l : betaToGreek(l); page = 0; }}>{letterLabel(l)}</button>
    {/each}
  </p>

  {#if !normalizedPrefix && (isEnglish ? ENGLISH_EXAMPLES : EXAMPLES).length}
    <p class="examples">
      <span class="mn">For example</span>
      {#each (isEnglish ? ENGLISH_EXAMPLES : EXAMPLES) as ex}
        <button type="button" class="ex" on:click={() => { prefix = ex.greek; page = 0; }}><span lang={isEnglish ? 'en' : 'grc'}>{ex.greek}</span>{#if ex.gloss} <small>{ex.gloss}</small>{/if}</button>
      {/each}
    </p>
  {/if}

  {#if planLoading}
    <p class="status" aria-live="polite">Looking up the forms of these words…</p>
  {:else if shardLoading || !activePlan}
    <p class="status" aria-live="polite">Loading the phrases…</p>
  {:else if shardError}
    <p class="status warn" role="alert">{shardError} <button type="button" class="ln" on:click={() => (requestedShardSignature = '')}>Try again</button></p>
  {:else if workFilterLoading}
    <p class="status" aria-live="polite">Choosing the plays’ phrases…</p>
  {:else if workFilterError}
    <p class="status warn" role="alert">{workFilterError} <button type="button" class="ln" on:click={() => (requestedWorkSignature = '')}>Try again</button></p>
  {:else if sortedRows.length === 0}
    <p class="status">No phrase recurs with these settings. Try fewer letters, a lower count, or more plays.</p>
  {:else}
    <p class="count" aria-live="polite">
      <span>{countFormat.format(sortedRows.length)} phrase{sortedRows.length === 1 ? '' : 's'}</span>
      {#if pageCount > 1}<span>showing {countFormat.format(shownFrom)}–{countFormat.format(shownTo)}</span>{/if}
    </p>
    <ul class="list">
      {#each pageRows as item (item.key)}
        {@const id = phraseId(item)}
        {@const isExpanded = expanded.has(id)}
        {@const itemDetails = details[id]}
        <li>
          <button
            id={`phrase-button-${id}`}
            type="button"
            class="phrase"
            aria-expanded={isExpanded}
            aria-controls={`phrase-details-${id}`}
            on:click={() => togglePhrase(item)}
          >
            <span class="ph" class:gk={!isEnglish} lang={isEnglish ? 'en' : 'grc'}>{isEnglish ? item.key : betaToGreek(item.key)}</span>
            <span class="nums">{countFormat.format(item.row[1])} times{item.row[3] > 1 ? ` in ${item.row[3]} plays` : ', one play'}</span>
          </button>
          {#if isExpanded}
            <div id={`phrase-details-${id}`} class="lines" role="region" aria-labelledby={`phrase-button-${id}`}>
              {#if itemDetails?.loading}
                <p class="status" aria-live="polite">Finding the lines…</p>
              {:else if itemDetails?.error}
                <p class="status warn" role="alert">{itemDetails.error}</p>
              {:else if itemDetails}
                {#each itemDetails.works as group}
                  <p class="play">
                    <span class="tt">{group.title}</span>
                    {#if group.error}
                      <span class="warn">{group.error}</span>
                    {:else}
                      {#each group.citations as citation}<a href={citation.href}>{citation.label}</a>{/each}
                      {#if group.citations.length < group.total}<span class="mn">and {countFormat.format(group.total - group.citations.length)} more</span>{/if}
                    {/if}
                  </p>
                {/each}
              {/if}
            </div>
          {/if}
        </li>
      {/each}
    </ul>
    {#if pageCount > 1}
      <nav class="pager" aria-label="Pages of phrases">
        <button type="button" class="ln" on:click={() => (page -= 1)} disabled={page === 0}>Previous</button>
        <span>Page {page + 1} of {pageCount}</span>
        <button type="button" class="ln" on:click={() => (page += 1)} disabled={page >= pageCount - 1}>Next</button>
      </nav>
    {/if}
  {/if}
</div>

<style>
  .phrases-page { max-width: 80rem; }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }

  /* The box at the left, the controls at the right, as on the search page. */
  .phrase-form {
    display: grid; grid-template-columns: minmax(18rem, 26rem) 1fr; gap: 1rem 3.5rem;
    max-width: 80rem; align-items: start; margin: 2rem 0 .4rem;
  }
  .boxes, .ctrls { min-width: 0; display: flex; flex-direction: column; gap: .55rem; }
  .lab { font: 400 1.05rem var(--font-ui); color: var(--mid); }
  .fld {
    font: 400 1.8rem/1.25 var(--font-english); color: var(--ink);
    background: none; border: 0; border-bottom: 1px solid var(--line); border-radius: 0;
    padding: 0 0 .15rem; width: 100%; appearance: none; -webkit-appearance: none;
  }
  .greek-input { font-family: var(--font-greek); }
  .fld::placeholder { color: var(--mid); font-style: italic; font-size: 1.4rem; }
  .fld:focus { outline: none; border-bottom-color: var(--clay-text); }
  .note { font: 400 .95rem var(--font-ui); color: var(--mid); margin: 0; }
  .note [lang="grc"] { font-family: var(--font-greek); color: var(--ink); }
  .act { display: flex; flex-wrap: wrap; gap: 1.4rem; align-items: baseline; margin: 1rem 0 0; font: 400 1rem var(--font-ui); }
  .ln { color: var(--mid); text-decoration: underline; text-underline-offset: 4px; font-family: var(--font-ui); }

  .row { display: flex; flex-wrap: wrap; gap: .3rem 1rem; align-items: baseline; margin: 0; font: 400 1rem var(--font-ui); color: var(--ink); }
  .mn { color: var(--mid); }
  .row > .mn:first-child { min-width: 4.6rem; }
  .v { position: relative; display: inline-flex; align-items: baseline; white-space: nowrap; max-width: 100%; min-width: 0; }
  .v select {
    appearance: none; -webkit-appearance: none; border: 0; background: none; padding: 0; margin: 0;
    font: inherit; color: var(--ink); cursor: pointer;
    text-decoration: underline; text-decoration-color: var(--clay-text); text-underline-offset: 4px;
    field-sizing: content; min-width: 0; max-width: 100%; text-overflow: ellipsis;
  }
  .v select:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; }
  .v i { font-style: normal; font-size: .7em; color: var(--clay-text); margin-left: .2em; pointer-events: none; }
  .ck { position: relative; color: var(--mid); white-space: nowrap; cursor: pointer; }
  .ck input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
  .ck::before { content: "☐ "; }
  .ck:has(input:checked) { color: var(--ink); }
  .ck:has(input:checked)::before { content: "☑ "; color: var(--clay-text); }
  .ck:has(input:focus-visible) { outline: 2px solid var(--clay); outline-offset: 2px; }
  .sum { color: var(--ink); }
  .choose { display: grid; grid-template-columns: max-content 1fr; gap: .4rem 1rem; align-items: baseline; margin: .2rem 0 0 5.6rem; }
  .choose .who { font: 400 1.05rem var(--font-english); color: var(--ink); margin: 0; }
  .choose .plays { display: flex; flex-wrap: wrap; gap: .25rem 1rem; margin: 0; font: 400 .95rem var(--font-ui); }
  .choose .plays:last-child { grid-column: 2; }

  /* The letters wrap; nothing scrolls sideways. */
  .letters { display: flex; flex-wrap: wrap; gap: .2rem .9rem; margin: 2rem 0 0; font: 400 1.15rem var(--font-greek); }
  .letters button { color: var(--mid); }
  .letters button:hover, .letters button.on { color: var(--clay-text); text-decoration: underline; text-underline-offset: 4px; }
  .examples { display: flex; flex-wrap: wrap; gap: .3rem 1.4rem; align-items: baseline; margin: 1rem 0 0; font: 400 1rem var(--font-ui); }
  .ex { color: var(--ink); text-decoration: underline; text-decoration-color: var(--clay-text); text-underline-offset: 4px; }
  .ex [lang="grc"] { font-family: var(--font-greek); font-size: 1.08rem; }
  .ex small { color: var(--mid); font-size: .9rem; }

  .count { display: flex; flex-wrap: wrap; gap: .3rem 1.2rem; margin: 2.2rem 0 .4rem; font: 400 1.05rem var(--font-ui); color: var(--mid); }
  .status { font: 400 .95rem var(--font-ui); color: var(--mid); margin: 2rem 0 0; }
  .warn { color: var(--error); }
  .list { list-style: none; margin: 0; padding: 0; max-width: 50rem; }
  .phrase { display: flex; flex-wrap: wrap; align-items: baseline; gap: .2rem 1rem; width: 100%; text-align: left; padding: .35rem 0; }
  .phrase .ph { font: 400 1.25rem/1.35 var(--font-english); color: var(--ink); }
  .phrase .ph.gk { font-family: var(--font-greek); }
  .phrase .nums { font: 400 .92rem var(--font-ui); color: var(--mid); }
  .phrase[aria-expanded="true"] .ph { color: var(--clay-text); }
  .phrase:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; }
  .lines { padding: 0 0 .8rem 1.4rem; }
  .play { display: flex; flex-wrap: wrap; gap: .15rem .7rem; align-items: baseline; margin: .25rem 0; font: 400 .92rem var(--font-ui); }
  .play .tt { font: 400 1.05rem var(--font-english); color: var(--ink); margin-right: .3rem; }
  .play a { color: var(--clay-text); text-decoration: none; font-variant-numeric: tabular-nums; }
  .play a:hover { text-decoration: underline; }
  .pager { display: flex; gap: 1.2rem; align-items: baseline; margin: 1rem 0; font: 400 .95rem var(--font-ui); color: var(--mid); }

  @media (max-width: 700px) {
    .phrase-form { display: flex; flex-direction: column; gap: .55rem; margin-top: 1.2rem; }
    .boxes { display: contents; }
    .ctrls { order: 2; margin-top: .6rem; }
    .act { order: 3; }
    .fld { font-size: 1.4rem; }
    .row { font-size: .95rem; gap: .25rem .8rem; }
    .choose { grid-template-columns: 1fr; margin-left: 0; }
    .choose .plays:last-child { grid-column: 1; }
    .lines { padding-left: .6rem; }
  }
</style>
