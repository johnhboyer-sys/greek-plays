<script lang="ts">
  import { onMount } from 'svelte';
  import Reader from './Reader.svelte';
  import Plate from './Plate.svelte';
  import { fetchBook, fetchConcordance, type BookData } from '../lib/data';
  import { editionPlace, hasRef, type Concordance } from '../lib/edition-place';
  import { getWork } from '../lib/works';
  import { assignSpeakerSlots } from '../lib/speaker-colors';
  import { playSigla } from '../lib/speakers';
  import { lastPrintedRef } from '../lib/citation';
  import { loadEdition, changeEdition, ownEdition, type EditionState, type ReaderView } from '../lib/edition-state';

  export let work: string;
  export let bookNum: number;
  export let bookData: BookData;
  export let serverEdition: string;
  export let chapterTitles: Record<string, string> = {};
  export let speakerRoster: string[] = [];
  export let authorName: string;
  const meta = getWork(work)!;
  const defaultTrans = meta.defaultTranslation ?? meta.translations.find(t => t.slot === 'english')?.id ?? meta.translations[0]?.id ?? '';
  let state: EditionState = { ed: serverEdition, trans: defaultTrans, view: 'both' };
  let shownBook = bookData;
  let anchor: string | null = null;
  let pending = false;
  let generation = 0;

  // `place`: the ref to write as ?loc= (after an edition switch); the URL's own
  // ?loc= and hash read in the numbering of ?ed=, and a bare ?loc= reads as TLG
  // (plan 4.1 rule 4), so ?ed= stays wherever a place is in the URL and the
  // edition is not one that reading gives back.
  function syncUrl(place: string | null = null) {
    const url = new URL(location.href);
    if (place) { url.searchParams.set('loc', place); url.hash = ''; }
    const own = ownEdition(meta, state.trans);
    const loc = url.searchParams.has('loc');
    const omit = loc ? state.ed === 'tlg' : url.hash ? state.ed === 'tlg' && own === 'tlg' : state.ed === own;
    if (omit) url.searchParams.delete('ed');
    else url.searchParams.set('ed', state.ed);
    history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }
  // `from`: the edition `loc` is printed in. On load it is the shown edition's own
  // numbering (?loc= reads in the numbering of ?ed=), so `from` is null: no mapping.
  async function show(next: EditionState, loc: string | null = null, from: string | null = state.ed) {
    const old = from ?? next.ed;
    let placed: string | null = null;
    if (state.ed !== next.ed) {
      pending = true;
      const id = ++generation;
      try {
        const data = await fetchBook(work, bookNum, next.ed);
        let oldMap: Concordance = {};
        let newMap: Concordance = {};
        // A concordance is only worth a fetch when the new edition lacks the ref,
        // and a missing one means "nearest lower", never a failed switch.
        if (loc && old !== next.ed && !hasRef(loc, data)) {
          const load = (ed: string) => ed === 'tlg' ? Promise.resolve({}) : fetchConcordance(work, ed).catch(() => ({}));
          [oldMap, newMap] = await Promise.all([load(old), load(next.ed)]);
        }
        if (id === generation) {
          anchor = old === next.ed ? loc : editionPlace(loc, old, next.ed, data, oldMap, newMap);
          shownBook = data;
          state = next;
          if (old !== next.ed) placed = anchor;
        }
      } finally { if (id === generation) pending = false; }
    } else state = next;
    document.documentElement.removeAttribute('data-ed-pending');
    syncUrl(placed);
  }
  onMount(() => {
    const params = new URLSearchParams(location.search);
    const valid = new Set(meta.translations.map(t => t.id));
    let trans = params.get('trans') ?? localStorage.getItem(`reader-trans-${work}`) ?? defaultTrans;
    if (!valid.has(trans) && trans !== 'compare') trans = defaultTrans;
    let view = params.get('view') ?? localStorage.getItem('reader-view') ?? 'both';
    if (!['both', 'english', 'greek'].includes(view)) view = 'both';
    const next = loadEdition(meta, { trans, view: view as ReaderView, ed: params.get('ed'), loc: params.get('loc') });
    anchor = params.get('loc');
    void show(next, anchor, null);
  });
  function changed(event: CustomEvent<{ trans: string; view: ReaderView; loc: string | null }>) {
    const next = changeEdition(meta, state, event.detail);
    void show(next, event.detail.loc ?? anchor);
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

{#if meta.citation?.scheme === 'play-line'}
  <Plate greekTitle={meta.greekTitle ?? null} title={meta.title} {authorName}
    argument={meta.argument ?? null} synopsis={meta.synopsis ?? null} production={meta.production ?? null}
    greekSource={shownSource} translations={meta.translations.filter(t => t.id === state.trans).map(t => t.name)}
    copyAbbr={meta.citation?.copyAbbr ?? null} lastLine={lastPrintedRef(shownBook.segments ?? [])}
    {persons} startHref={`#col-${shownBook.segments?.[0]?.column ?? '1'}`} />
{/if}
{#if pending}<div class="ed-pending" role="status" aria-label="Loading text">◌</div>{/if}
{#key state.ed}
  <div style:visibility={pending ? 'hidden' : 'visible'}>
    <Reader {work} {bookNum} bookData={shownBook} {chapterTitles} {speakerRoster}
      edition={state.ed} initialLocation={anchor} initialTranslation={state.trans} initialView={state.view}
      on:editionChange={changed} />
  </div>
{/key}
