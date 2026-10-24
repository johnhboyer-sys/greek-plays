<script lang="ts">
  import { onMount } from 'svelte';
  import Reader from './Reader.svelte';
  import Plate from './Plate.svelte';
  import { fetchBook, fetchConcordance, type BookData } from '../lib/data';
  import { editionPlace, type Concordance } from '../lib/edition-place';
  import { getWork } from '../lib/works';
  import { assignSpeakerSlots } from '../lib/speaker-colors';
  import { playSigla } from '../lib/speakers';
  import { lastPrintedRef } from '../lib/citation';
  import { loadEdition, changeEdition, defaultEdition, comparePair, type EditionState, type ReaderView, type Pair } from '../lib/edition-state';
  import { takeBook } from '../lib/book-payload';

  export let work: string;
  export let bookNum: number;
  export let bookData: BookData | null = null;
  // The page's book by id, in place of bookData (shared/lib/book-payload.ts).
  export let bookId: string | null = null;
  export let serverEdition: string;
  export let chapterTitles: Record<string, string> = {};
  export let speakerRoster: string[] = [];
  export let authorName: string;
  // The drama site draws its own play opening (app Playbill.astro) above this.
  export let plate = true;
  const meta = getWork(work)!;
  const defaultTrans = meta.defaultTranslation ?? meta.translations.find(t => t.slot === 'english')?.id ?? meta.translations[0]?.id ?? '';
  let state: EditionState = { ed: serverEdition, trans: defaultTrans, view: 'both' };
  let shownBook = (bookData ?? (bookId ? takeBook(bookId) : null)) as BookData;
  let anchor: string | null = null;
  let pending = false;
  let generation = 0;
  // Reader reads initialView/initialTranslation once, at mount. It first mounts
  // with the defaults (the server-rendered pair), so when the reader's own
  // ?view=/?trans=/saved choice resolves to something else on the same edition,
  // remount once with the resolved values (a changed edition remounts anyway).
  let epoch = 0;

  // `place`: the ref to write as ?loc= (after an edition switch); the URL's own
  // ?loc= and hash read in the numbering of ?ed=, and a bare ?loc= reads as TLG
  // (plan 4.1 rule 4), so ?ed= stays wherever a place is in the URL and the
  // edition is not one that reading gives back. The reader's own scrolling
  // swaps ?loc= for a hash (Reader.svelte updateHash), so ?ed= stays whenever
  // the hash rule would need it as well.
  function syncUrl(place: string | null = null) {
    const url = new URL(location.href);
    if (place) { url.searchParams.set('loc', place); url.hash = ''; }
    const own = defaultEdition(meta, state.trans, state.pair);
    const loc = url.searchParams.has('loc');
    const omit = loc || url.hash ? state.ed === 'tlg' && own === 'tlg' : state.ed === own;
    if (omit) url.searchParams.delete('ed');
    else url.searchParams.set('ed', state.ed);
    history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }
  // `from`: the edition `loc` is printed in. On load it is the shown edition's own
  // numbering (?loc= reads in the numbering of ?ed=), so `from` is null: no mapping.
  async function show(next: EditionState, loc: string | null = null, from: string | null = state.ed, first = false) {
    const old = from ?? next.ed;
    let placed: string | null = null;
    if (state.ed !== next.ed) {
      pending = true;
      const id = ++generation;
      try {
        const data = await fetchBook(work, bookNum, next.ed);
        let oldMap: Concordance = {};
        let newMap: Concordance = {};
        // The concordance outranks the same printed ref (edition-place.ts), so load what
        // the rule needs whether or not the new book has the ref: edition -> tlg the
        // source edition's, tlg -> edition the target's, edition -> edition both (tlg's
        // is empty; fetchConcordance caches). A failed load means "same ref, else
        // nearest lower", never a failed switch.
        if (loc && old !== next.ed) {
          const load = (ed: string) => ed === 'tlg' ? Promise.resolve({}) : fetchConcordance(work, ed).catch(() => ({}));
          [oldMap, newMap] = await Promise.all([load(old), load(next.ed)]);
        }
        if (id === generation) {
          anchor = old === next.ed ? loc : editionPlace(loc, old, next.ed, data, oldMap, newMap);
          shownBook = data;
          state = next;
          if (old !== next.ed) placed = anchor;
        }
      } catch {
        // A failed load keeps the shown edition and its text (Codex review,
        // 2026-10-24: the hold below never lifted and the page stayed blank).
      } finally { if (id === generation) pending = false; }
    } else {
      // A later change on the shown edition supersedes a fetch still loading.
      ++generation;
      pending = false;
      const differs = first && (next.view !== state.view || next.trans !== state.trans);
      state = next;
      if (differs) epoch++;
    }
    document.documentElement.removeAttribute('data-ed-pending');
    syncUrl(placed);
  }
  onMount(() => {
    const params = new URLSearchParams(location.search);
    const valid = new Set(meta.translations.map(t => t.id));
    const stored = (key: string) => { try { return localStorage.getItem(key); } catch { return null; } };
    let trans = params.get('trans') ?? stored(`reader-trans-${work}`) ?? defaultTrans;
    if (!valid.has(trans) && trans !== 'compare') trans = defaultTrans;
    let view = params.get('view') ?? stored('reader-view') ?? 'both';
    if (!['both', 'english', 'greek'].includes(view)) view = 'both';
    const saved = (side: 'l' | 'r') => stored(`reader-cmp${side}-${work}`);
    const pair = trans === 'compare' ? comparePair(meta, [saved('l'), saved('r')]) : undefined;
    const next = loadEdition(meta, { trans, view: view as ReaderView, ed: params.get('ed'), loc: params.get('loc'), pair });
    anchor = params.get('loc');
    void show(next, anchor, null, true);
  });
  function changed(event: CustomEvent<{ trans: string; view: ReaderView; loc: string | null; ed?: string; pair?: Pair }>) {
    const next = changeEdition(meta, state, event.detail);
    void show(next, event.detail.loc || anchor);
  }
  $: castRoster = shownBook.speakerRoster?.length ? shownBook.speakerRoster : speakerRoster;
  $: slots = assignSpeakerSlots(speakerRoster.length ? speakerRoster : castRoster);
  $: sigla = playSigla((shownBook.segments ?? []).flatMap(seg => seg.speakers ?? []));
  $: persons = castRoster.map(name => ({ name, slot: slots.get(name) ?? 0, siglum: sigla.get(name) ?? null }));
  $: shownSource = (() => {
    const source = meta.greekEditions?.find(e => e.id === state.ed);
    return source && state.ed !== 'tlg'
      ? source.full + (source.licence === 'cc-by-sa-4.0' ? ' · Perseus Digital Library, CC BY-SA 4.0' : '')
      : meta.greekSource.full;
  })();
</script>

{#if plate && meta.citation?.scheme === 'play-line'}
  <Plate greekTitle={meta.greekTitle ?? null} title={meta.title} {authorName}
    argument={meta.argument ?? null} synopsis={meta.synopsis ?? null} production={meta.production ?? null}
    greekSource={shownSource} translations={meta.translations.filter(t => t.id === state.trans).map(t => t.name)}
    copyAbbr={meta.citation?.copyAbbr ?? null} lastLine={lastPrintedRef(shownBook.segments ?? [])}
    {persons} startHref={`#col-${shownBook.segments?.[0]?.column ?? '1'}`} />
{/if}
{#if pending}<div class="ed-pending" role="status" aria-label="Loading text">◌</div>{/if}
{#key `${state.ed}:${epoch}`}
  <!-- No style when not pending: the server's `visibility: visible` showed the
       default edition's text through the shell's data-ed-pending hold. -->
  <div style:visibility={pending ? 'hidden' : null}>
    <Reader {work} {bookNum} bookData={shownBook} {chapterTitles} {speakerRoster}
      edition={state.ed} initialLocation={anchor} initialTranslation={state.trans} initialView={state.view}
      on:editionChange={changed} />
  </div>
{/key}
